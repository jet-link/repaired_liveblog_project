"""Views for vanished (deleted/banned) users."""
from django.core.paginator import Paginator
from django.shortcuts import render
from django.urls import reverse

from smart_blog.models import Item
from login.views._helpers import (
    _random_vanished_name,
    _safe_referer_url,
    _referer_breadcrumb_info,
    _vanished_items_qs,
    annotate_user_bookmarked,
    annotate_user_liked,
    apply_human_counts,
    build_breadcrumbs,
    breadcrumb,
)


def vanished_generic_view(request):
    """Page for author=None: avatar, Deleted user, item cards."""
    qs = _vanished_items_qs()
    qs = annotate_user_liked(qs, request.user)
    qs = annotate_user_bookmarked(qs, request.user)
    SECTION_LIMIT = 10
    created_items = list(qs[:SECTION_LIMIT])
    all_count = qs.count()
    apply_human_counts(created_items)

    vanished_name = _random_vanished_name()
    referer = _safe_referer_url(request)
    crumb_title, crumb_url = _referer_breadcrumb_info(request, referer)
    breadcrumbs = build_breadcrumbs(
        breadcrumb(crumb_title, crumb_url),
        breadcrumb(vanished_name, None),
    )
    context = {
        "created_items": created_items,
        "all_count": all_count,
        "view_all_url": reverse("login_app:vanished-created"),
        "listing_source": "vanished",
        "breadcrumbs": breadcrumbs,
        "vanished_display_name": vanished_name,
        "vanished_status": "deleted",
    }
    return render(request, "accounts/vanished.html", context)


def vanished_created_view(request):
    """Full paginated list of items by deleted users."""
    qs = _vanished_items_qs()
    qs = annotate_user_liked(qs, request.user)
    qs = annotate_user_bookmarked(qs, request.user)
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    page_range = paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1)
    apply_human_counts(page_obj)

    referer = _safe_referer_url(request)
    crumb_title, crumb_url = _referer_breadcrumb_info(request, referer)
    breadcrumbs = build_breadcrumbs(
        breadcrumb(crumb_title, crumb_url),
        breadcrumb("Deleted user", reverse("login_app:vanished")),
        breadcrumb("Created", None),
    )
    return render(request, "accounts/vanished_created.html", {
        "items": page_obj,
        "page_obj": page_obj,
        "page_range": page_range,
        "breadcrumbs": breadcrumbs,
    })


def user_not_found_view(request, user_obj, vanished_status="banned"):
    """Inactive user public page: banned or deleted-in-queue."""
    user_items_qs = (
        Item.objects
        .filter(is_published=True, author=user_obj)
        .with_counters()
        .order_by('-published_date')
        .prefetch_related("images")
    )
    user_items_qs = annotate_user_liked(user_items_qs, request.user)
    user_items_qs = annotate_user_bookmarked(user_items_qs, request.user)

    SECTION_LIMIT = 10
    created_items = list(user_items_qs[:SECTION_LIMIT])
    all_count = user_items_qs.count()
    apply_human_counts(created_items)

    view_all_url = reverse("login_app:profile-section", kwargs={
        "username": user_obj.username,
        "section": "created",
    })

    vanished_name = _random_vanished_name()
    referer = _safe_referer_url(request)
    crumb_title, crumb_url = _referer_breadcrumb_info(request, referer)
    breadcrumbs = build_breadcrumbs(
        breadcrumb(crumb_title, crumb_url),
        breadcrumb(vanished_name, None),
    )

    context = {
        "created_items": created_items,
        "all_count": all_count,
        "view_all_url": view_all_url,
        "listing_source": "profile",
        "listing_user": user_obj.username,
        "listing_section": "created",
        "breadcrumbs": breadcrumbs,
        "vanished_display_name": vanished_name,
        "vanished_status": vanished_status,
    }
    return render(request, "accounts/vanished.html", context)
