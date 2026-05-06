"""Interaction views: toggle_like, toggle_bookmark, post_counters, api_repost."""
import json
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from smart_blog.models import Bookmark, Item, Like, Notification, PostRepost


@require_POST
@login_required
def toggle_like(request, slug):
    item = get_object_or_404(Item, slug=slug)

    like_qs = Like.objects.filter(item=item, user=request.user)

    if like_qs.exists():
        like_qs.delete()
        liked = False
        Notification.objects.filter(
            recipient=item.author,
            actor=request.user,
            notif_type=Notification.TYPE_ITEM_LIKE,
            item=item
        ).delete()
        if item.author:
            from smart_blog.context_processors import invalidate_notifications_cache
            invalidate_notifications_cache(item.author.pk)
    else:
        Like.objects.create(item=item, user=request.user)
        liked = True
        if item.author and item.author != request.user:
            from smart_blog.notification_utils import upsert_item_like_notification
            upsert_item_like_notification(
                recipient=item.author, actor=request.user, item=item
            )
            from smart_blog.context_processors import invalidate_notifications_cache
            invalidate_notifications_cache(item.author.pk)

    item.refresh_from_db()
    from smart_blog.services.for_you_recommendations import invalidate_foryou_cache
    invalidate_foryou_cache(request.user.pk)
    return JsonResponse({
        "success": True,
        "item_id": item.pk,
        "liked": liked,
        "likes_count": item.likes_count,
        "views_count": item.views_count,
    })


@require_POST
@login_required
def toggle_bookmark(request, slug):
    item = get_object_or_404(Item, slug=slug)
    user = request.user

    existing = Bookmark.objects.filter(user=user, item=item)

    if existing.exists():
        existing.delete()
        bookmarked = False
    else:
        Bookmark.objects.create(user=user, item=item)
        bookmarked = True

    item.refresh_from_db()
    from smart_blog.services.for_you_recommendations import invalidate_foryou_cache
    invalidate_foryou_cache(request.user.pk)
    return JsonResponse({
        "success": True,
        "item_id": item.pk,
        "bookmarked": bookmarked,
        "bookmarks_count": item.bookmarks_count,
        "views_count": item.views_count,
    })


@ratelimit(key='ip', rate=settings.RATELIMIT_ITEM_COUNTERS_RATE, method='GET', block=False)
def post_counters(request, post_id):
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'rate_limited'}, status=429)
    item = get_object_or_404(Item.objects.with_counters(), pk=post_id)
    return JsonResponse({
        "views": item.views_count,
        "likes": item.likes_count,
        "bookmarks": item.bookmarks_count,
        "comments": item.comments_count,
        "reposts": item.reposts_count,
    })


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


@ratelimit(key='ip', rate='30/m', method='POST', block=False)
@require_POST
def api_repost(request):
    """POST /api/repost — rate-limited per IP; body analytics see PostRepost."""
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'rate_limited'}, status=429)
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = request.POST.dict()
    post_id = data.get('post_id') or data.get('item_id')
    platform = (data.get('platform') or 'other').strip().lower()
    valid_platforms = ['telegram', 'twitter', 'facebook', 'linkedin', 'copy_link', 'other']
    if platform not in valid_platforms:
        return JsonResponse({'error': 'Invalid platform'}, status=400)
    if not post_id:
        return JsonResponse({'error': 'post_id required'}, status=400)
    try:
        post_id = int(post_id)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid post_id'}, status=400)

    item = get_object_or_404(Item.objects.filter(is_published=True), pk=post_id)
    ip = _get_client_ip(request)
    user = request.user if request.user.is_authenticated else None
    ua = (request.META.get('HTTP_USER_AGENT') or '')[:500]

    now = timezone.now()
    ip_window = timedelta(seconds=10)
    user_window = timedelta(seconds=5)
    copy_link_window = timedelta(seconds=15)

    if ip:
        recent_ip = PostRepost.objects.filter(
            item=item, ip_address=ip, created_at__gte=now - ip_window
        ).exists()
        if recent_ip:
            item.refresh_from_db()
            return JsonResponse({'reposts_count': item.reposts_count, 'rate_limited': True}, status=429)
    if user:
        recent_user = PostRepost.objects.filter(
            item=item, user=user, created_at__gte=now - user_window
        ).exists()
        if recent_user:
            item.refresh_from_db()
            return JsonResponse({'reposts_count': item.reposts_count, 'rate_limited': True}, status=429)
    if platform == PostRepost.PLATFORM_COPY_LINK and ip:
        recent_copy = PostRepost.objects.filter(
            item=item, platform=PostRepost.PLATFORM_COPY_LINK,
            ip_address=ip, created_at__gte=now - copy_link_window
        ).exists()
        if recent_copy:
            item.refresh_from_db()
            return JsonResponse({'reposts_count': item.reposts_count, 'rate_limited': True}, status=429)

    PostRepost.objects.create(
        item=item, user=user, ip_address=ip or None, platform=platform, user_agent=ua,
    )
    item.refresh_from_db()
    return JsonResponse({'reposts_count': item.reposts_count, 'success': True})
