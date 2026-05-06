"""Comment views: add_comment, edit_comment, delete_comment, toggle_comment_like."""
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Exists, OuterRef, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from smart_blog.forms import CommentForm
from smart_blog.models import Comment, CommentLike, Item, Notification
from smart_blog.utils import count_convert

EDITABLE_HOURS = 24


@login_required
@require_POST
def add_comment(request, slug):
    if not request.user.is_superuser:
        shadow_banned = getattr(getattr(request.user, 'profile', None), 'shadow_banned', False)
        if shadow_banned:
            return JsonResponse({
                "success": False,
                "error": "You have been shadow banned. Improve your trust score to restore access."
            }, status=403)
    item = get_object_or_404(Item, slug=slug)
    parent_id = request.POST.get("parent_id")
    if not parent_id:
        cooldown_key = f'comment_cooldown_{item.pk}'
        now_ts = timezone.now().timestamp()
        last_ts = request.session.get(cooldown_key)
        cooldown_sec = 30
        if last_ts and (now_ts - float(last_ts)) < cooldown_sec:
            remaining = int(cooldown_sec - (now_ts - float(last_ts)))
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Please wait {remaining} seconds before commenting again."
                },
                status=429
            )
    form = CommentForm(request.POST)

    if not form.is_valid():
        return JsonResponse(
            {"success": False, "errors": form.errors},
            status=400
        )
    text = form.cleaned_data.get('text', '')

    parent = None
    if parent_id:
        parent = Comment.objects.filter(
            pk=parent_id,
            item=item
        ).first()

    comment = form.save(commit=False)
    comment.text = text
    comment.author = request.user
    comment.item = item
    comment.parent = parent
    comment.save()
    if not parent_id:
        request.session[cooldown_key] = now_ts
    if parent and parent.author and parent.author != request.user:
        Notification.objects.create(
            recipient=parent.author,
            actor=request.user,
            notif_type=Notification.TYPE_REPLY,
            item=item,
            parent_comment=parent,
            reply_comment=comment,
        )
        from smart_blog.context_processors import invalidate_notifications_cache
        invalidate_notifications_cache(parent.author.pk)
    comment = (
        Comment.objects.filter(pk=comment.pk)
        .annotate(
            replies_count=Count('replies', filter=Q(replies__is_draft=False), distinct=True),
            user_liked=Exists(
                CommentLike.objects.filter(comment=OuterRef('pk'), user=request.user)
            ),
            likes_count=Count('likes', distinct=True),
            reports_count=Count('reports', distinct=True),
        )
        .get(pk=comment.pk)
    )

    html = render_to_string(
        "includes/_comments.html",
        {
            "comment": comment,
            "user": request.user,
            "report_rate_limited": False,
        },
        request=request
    )

    return JsonResponse({
        "success": True,
        "comment_html": html,
        "comments_count": Comment.objects.filter(
            item=item,
            parent__isnull=True,
            is_draft=False
        ).count()
    })


@login_required
@require_POST
def edit_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)

    if request.user != comment.author and not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    if not request.user.is_superuser:
        shadow_banned = getattr(getattr(request.user, 'profile', None), 'shadow_banned', False)
        if shadow_banned:
            return JsonResponse({
                'success': False,
                'error': 'You have been shadow banned. Improve your trust score to restore access.'
            }, status=403)

    editable_until = comment.created + timedelta(hours=EDITABLE_HOURS)
    if timezone.now() > editable_until and not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Editing period expired.'}, status=403)

    form = CommentForm(request.POST, instance=comment)
    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    form.save()

    comment = (
        Comment.objects.filter(pk=comment.pk)
        .annotate(
            user_liked=Exists(
                CommentLike.objects.filter(comment=OuterRef('pk'), user=request.user)
            ),
            likes_count=Count('likes', distinct=True),
            reports_count=Count('reports', distinct=True),
        )
        .get(pk=comment.pk)
    )

    html = render_to_string("includes/_comments.html", {
        "comment": comment, "user": request.user,
        "report_rate_limited": False,
    })
    total_comments = Comment.objects.filter(item=comment.item, is_draft=False).count()
    return JsonResponse({'success': True, 'comment_html': html, 'comment_id': comment.pk, 'total_comments': total_comments})


@login_required
@require_POST
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)

    if request.user != comment.author and not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    parent_id = comment.parent_id
    comment.delete()

    return JsonResponse({
        "success": True,
        "comment_id": pk,
        "parent_id": parent_id,
        "comments_count": Comment.objects.filter(
            item=comment.item,
            parent__isnull=True,
            is_draft=False
        ).count()
    })


@require_POST
@login_required
def toggle_comment_like(request, pk):
    comment = get_object_or_404(Comment, pk=pk)

    user = request.user
    like_qs = CommentLike.objects.filter(comment=comment, user=user)
    if like_qs.exists():
        like_qs.delete()
        liked = False
        notif_filter = {
            "recipient": comment.author,
            "actor": request.user,
            "notif_type": Notification.TYPE_COMMENT_LIKE,
            "item": comment.item,
        }
        if comment.parent_id:
            Notification.objects.filter(**notif_filter, reply_comment=comment).delete()
        else:
            Notification.objects.filter(**notif_filter, parent_comment=comment).delete()
        if comment.author:
            from smart_blog.context_processors import invalidate_notifications_cache
            invalidate_notifications_cache(comment.author.pk)
    else:
        CommentLike.objects.create(comment=comment, user=user)
        liked = True
        if comment.author and comment.author != request.user:
            from smart_blog.notification_utils import upsert_comment_like_notification
            if comment.parent_id:
                upsert_comment_like_notification(
                    recipient=comment.author,
                    actor=request.user,
                    item=comment.item,
                    reply_comment=comment,
                    parent_comment=None,
                )
            else:
                upsert_comment_like_notification(
                    recipient=comment.author,
                    actor=request.user,
                    item=comment.item,
                    parent_comment=comment,
                    reply_comment=None,
                )
            from smart_blog.context_processors import invalidate_notifications_cache
            invalidate_notifications_cache(comment.author.pk)

    likes_count = CommentLike.objects.filter(comment=comment).count()
    return JsonResponse({
        "success": True,
        "comment_id": comment.pk,
        "liked": liked,
        "likes_count": count_convert(likes_count),
    })
