"""Detail views: item_detail, item_comments, comment_thread."""
from datetime import timedelta

from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.http import Http404, HttpResponsePermanentRedirect, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from smart_blog.forms import CommentForm
from smart_blog.models import (
    Bookmark,
    Category,
    Comment,
    CommentLike,
    Item,
    ItemImage,
    ItemVideo,
    ItemView,
    Like,
    ViewEvent,
)
from smart_blog.selectors import has_user_reported_item
from smart_blog.services.report_limits import can_user_report
from smart_blog.utils import breadcrumb, build_breadcrumbs

DETAIL_COMMENT_PREVIEW_LIMIT = 10


def _comments_querysets_for_item(request, item):
    """Root comments + prefetch reply trees (same shape as historical item_detail)."""
    if request.user.is_authenticated:
        likes_subq = CommentLike.objects.filter(
            comment=OuterRef('pk'),
            user=request.user
        )
    else:
        likes_subq = CommentLike.objects.none()

    main_comments_qs = (
        Comment.objects
        .filter(item=item, parent__isnull=True, is_draft=False)
        .annotate(
            user_liked=Exists(likes_subq),
            likes_count=Count('likes', distinct=True),
            replies_count=Count('replies', filter=Q(replies__is_draft=False), distinct=True),
            reports_count=Count('reports', distinct=True),
        )
        .order_by('-created')
    )

    replies_qs = (
        Comment.objects
        .filter(parent__isnull=False, is_draft=False)
        .annotate(
            user_liked=Exists(likes_subq),
            likes_count=Count('likes', distinct=True),
            reports_count=Count('reports', distinct=True),
        )
        .order_by('-created')
    )

    comments = main_comments_qs.prefetch_related(
        Prefetch('replies', queryset=replies_qs),
        Prefetch('replies__replies', queryset=replies_qs),
        Prefetch('replies__replies__replies', queryset=replies_qs),
        Prefetch('replies__replies__replies__replies', queryset=replies_qs),
    )
    return comments


def register_item_view(request, item):
    ViewEvent.objects.create(item=item)

    if request.user.is_authenticated:
        ItemView.objects.get_or_create(
            item=item,
            user=request.user
        )
    else:
        if not request.session.session_key:
            request.session.create()

        ItemView.objects.get_or_create(
            item=item,
            user=None,
            session_key=request.session.session_key,
            defaults={
                "ip_address": request.META.get("REMOTE_ADDR")
            }
        )


def item_detail(request, slug):
    slug = (slug or '').strip()
    item = get_object_or_404(Item.objects.filter(is_published=True), slug=slug)

    if request.GET.get("focus_comment"):
        params = request.GET.urlencode()
        target = reverse("smart_blog:post_comments", kwargs={"slug": slug})
        return HttpResponseRedirect(f"{target}?{params}" if params else target)

    register_item_view(request, item)

    item = (
        Item.objects
        .with_counters()
        .select_related("category", "author", "author__profile")
        .annotate(reports_count=Count('reports', distinct=True))
        .prefetch_related(
            Prefetch(
                "images",
                queryset=ItemImage.objects.all().order_by("sort_order", "pk"),
            ),
            Prefetch(
                "videos",
                queryset=ItemVideo.objects.all().order_by("sort_order", "pk"),
            ),
        )
        .get(pk=item.pk)
    )

    user_liked = (
        Like.objects.filter(item=item, user=request.user).exists()
        if request.user.is_authenticated else False
    )

    user_bookmarked = (
        Bookmark.objects.filter(item=item, user=request.user).exists()
        if request.user.is_authenticated else False
    )

    user_reported_item = has_user_reported_item(request.user, item)
    allowed, _ = can_user_report(request.user) if request.user.is_authenticated else (False, None)
    report_rate_limited = not allowed

    liked_users = (
        Like.objects
        .filter(item=item)
        .select_related('user', 'user__profile')
        .exclude(user__isnull=True)
        .order_by('-created_at')
    )

    editable_until = (item.published_date or item.created) + timedelta(hours=24)
    is_editable = timezone.now() <= editable_until

    source = request.GET.get("from")
    source_user = request.GET.get("user")
    source_section = request.GET.get("section")
    source_url = request.GET.get("source_url")
    source_query = request.GET.get("query")
    source_tag = request.GET.get("tag")
    source_tag_slug = request.GET.get("tag_slug")
    source_category_slug = (request.GET.get("category_slug") or "").strip()

    safe_source_url = None
    if source_url and url_has_allowed_host_and_scheme(
        url=source_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        safe_source_url = source_url

    source_user = (source_user or '').strip()
    source_section = (source_section or '').strip().lower()

    if source == "profile" and source_user and source_section == "created":
        breadcrumbs = build_breadcrumbs(
            breadcrumb(source_user, reverse("login_app:profile", kwargs={"username": source_user})),
            breadcrumb("Created", reverse("login_app:profile-section", kwargs={"username": source_user, "section": "created"})),
            breadcrumb(item.title, None),
        )
    elif source == "profile" and source_user:
        breadcrumbs = build_breadcrumbs(
            breadcrumb(source_user, reverse("login_app:profile", kwargs={"username": source_user})),
            breadcrumb(item.title, None),
        )
    elif source == "items_list":
        breadcrumbs = build_breadcrumbs(
            breadcrumb("BraiNews", safe_source_url or reverse("smart_blog:items_list")),
            breadcrumb(item.title, None),
        )
    elif source == "trending":
        breadcrumbs = build_breadcrumbs(
            breadcrumb("In trend", safe_source_url or reverse("smart_blog:trending_list")),
            breadcrumb(item.title, None),
        )
    elif source == "for_you":
        # For-you feed is the BraiNews filter, not a separate hub; trail always returns to BraiNews.
        breadcrumbs = build_breadcrumbs(
            breadcrumb("BraiNews", reverse("smart_blog:items_list")),
            breadcrumb(item.title, None),
        )
    elif source == "popular":
        breadcrumbs = build_breadcrumbs(
            breadcrumb("Popular posts", safe_source_url or reverse("smart_blog:items_popular")),
            breadcrumb(item.title, None),
        )
    elif source in ("category", "topic") and source_category_slug:
        topic_src = safe_source_url or reverse(
            "smart_blog:topic_detail", kwargs={"slug": source_category_slug}
        )
        cat_row = Category.objects.filter(slug=source_category_slug).values("name").first()
        crumb_label = cat_row["name"] if cat_row else source_category_slug
        breadcrumbs = build_breadcrumbs(
            breadcrumb(crumb_label, topic_src),
            breadcrumb(item.title, None),
        )
    elif source == "search" and source_query:
        from urllib.parse import urlencode
        search_url = safe_source_url or (reverse("global_search") + "?" + urlencode({"q": source_query}))
        breadcrumbs = build_breadcrumbs(
            breadcrumb(f"Found - {source_query}", search_url),
            breadcrumb(item.title, None),
        )
    elif source == "tag" and source_tag:
        tag_url = safe_source_url
        if not tag_url and source_tag_slug:
            tag_url = reverse("smart_blog:tag_list", kwargs={"slug": source_tag_slug})
        if not tag_url:
            tag_url = reverse("smart_blog:items_list")
        breadcrumbs = build_breadcrumbs(
            breadcrumb(source_tag, tag_url),
            breadcrumb(item.title, None),
        )
    elif source == "home":
        breadcrumbs = build_breadcrumbs(
            breadcrumb("brainstorm.news", safe_source_url or "/"),
            breadcrumb(item.title, None),
        )
    else:
        breadcrumbs = build_breadcrumbs(
            breadcrumb("BraiNews", reverse("smart_blog:items_list")),
            breadcrumb(item.title, None),
        )

    has_comments = (
        Comment.objects.filter(item=item, parent__isnull=True, is_draft=False).exists()
    )

    if has_comments:
        comments_qs = _comments_querysets_for_item(request, item)
        detail_comments_preview = list(comments_qs[:DETAIL_COMMENT_PREVIEW_LIMIT])
    else:
        detail_comments_preview = []

    return render(request, "smart_blog/item_detail.html", {
        "item": item,
        "form": CommentForm(),
        "user_liked": user_liked,
        "user_bookmarked": user_bookmarked,
        "user_reported_item": user_reported_item,
        "report_rate_limited": report_rate_limited,
        "liked_users": liked_users,
        "editable_until_iso": editable_until.isoformat(),
        "is_editable": is_editable,
        "breadcrumbs": breadcrumbs,
        "has_comments": has_comments,
        "detail_comments_preview": detail_comments_preview,
        "detail_comment_preview_limit": DETAIL_COMMENT_PREVIEW_LIMIT,
    })


def item_comments(request, slug):
    slug = (slug or '').strip()
    item = get_object_or_404(Item.objects.filter(is_published=True), slug=slug)

    item = (
        Item.objects
        .with_counters()
        .select_related("category", "author", "author__profile")
        .annotate(reports_count=Count('reports', distinct=True))
        .prefetch_related(
            Prefetch(
                "images",
                queryset=ItemImage.objects.all().order_by("sort_order", "pk"),
            ),
            Prefetch(
                "videos",
                queryset=ItemVideo.objects.all().order_by("sort_order", "pk"),
            ),
        )
        .get(pk=item.pk)
    )

    comments = _comments_querysets_for_item(request, item)
    allowed, _ = can_user_report(request.user) if request.user.is_authenticated else (False, None)
    report_rate_limited = not allowed

    breadcrumbs = build_breadcrumbs(
        breadcrumb("brainstorm.news", "/"),
        breadcrumb(item.title, item.get_absolute_url()),
        breadcrumb("Comments", None),
    )

    return render(request, "smart_blog/item_comments.html", {
        "item": item,
        "comments": comments,
        "report_rate_limited": report_rate_limited,
        "breadcrumbs": breadcrumbs,
    })


def comment_thread_blog_redirect(request, pk):
    """Legacy /blog/comment/<pk>/thread/ → /post/<slug>/comment/<pk>/thread/."""
    comment = get_object_or_404(
        Comment.objects.filter(is_draft=False).select_related("item"),
        pk=pk,
    )
    item = comment.item
    if not item.is_published:
        raise Http404
    url = reverse("smart_blog:comment_thread", kwargs={"slug": item.slug, "pk": pk})
    return HttpResponsePermanentRedirect(url)


def comment_thread(request, slug, pk):
    slug = (slug or "").strip()
    comment = get_object_or_404(Comment.objects.filter(is_draft=False), pk=pk)
    item = comment.item
    if not item.is_published or (item.slug or "").strip() != slug:
        raise Http404

    if request.user.is_authenticated:
        thread_likes_subq = CommentLike.objects.filter(
            comment=OuterRef('pk'),
            user=request.user
        )
    else:
        thread_likes_subq = CommentLike.objects.none()

    replies_qs = Comment.objects.filter(is_draft=False).annotate(
        user_liked=Exists(thread_likes_subq),
        likes_count=Count('likes', distinct=True),
        reports_count=Count('reports', distinct=True),
    ).order_by('-created')
    comment = (
        Comment.objects
        .filter(pk=comment.pk)
        .annotate(
            user_liked=Exists(thread_likes_subq),
            likes_count=Count('likes', distinct=True),
            reports_count=Count('reports', distinct=True),
        )
        .prefetch_related(
            Prefetch('replies', queryset=replies_qs),
            Prefetch('replies__replies', queryset=replies_qs),
            Prefetch('replies__replies__replies', queryset=replies_qs),
            Prefetch('replies__replies__replies__replies', queryset=replies_qs),
        )
        .get()
    )

    allowed, _ = can_user_report(request.user) if request.user.is_authenticated else (False, None)
    report_rate_limited = not allowed

    if comment.parent_id:
        thread_back_url = reverse(
            "smart_blog:comment_thread",
            kwargs={"slug": comment.item.slug, "pk": comment.parent_id},
        )
    else:
        thread_back_url = comment.item.get_comments_absolute_url()

    return render(request, "smart_blog/comment_thread.html", {
        "comment": comment,
        "item": comment.item,
        "report_rate_limited": report_rate_limited,
        "thread_back_url": thread_back_url,
    })
