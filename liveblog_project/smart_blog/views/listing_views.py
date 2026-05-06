"""Listing views: items_list, items_filtered, tag_list, category_list."""
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Exists, OuterRef, Subquery
from django.http import HttpResponse, HttpResponseForbidden, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from urllib.parse import urlencode

from smart_blog.models import Bookmark, Item, Like, Tag
from smart_blog.public_listing_cache import get_anon_brainews_cache_version
from smart_blog.search_utils import build_search_filter
from smart_blog.utils import breadcrumb, build_breadcrumbs
from smart_blog.feed_queryset import feed_list_optimizations
from smart_blog.views._helpers import (
    annotate_feed_page_items,
    annotate_user_bookmarked,
    annotate_user_liked,
)

FILTER_AJAX_PAGE_SIZE = 20
_ANON_BRAINEWS_CACHE_TTL = 60


def _anon_brainews_cache_key(page_key: str) -> str:
    return f"anon_brainews_p{page_key}_v{get_anon_brainews_cache_version()}"


def items_list(request):
    page_number = request.GET.get('page')
    is_anon = not request.user.is_authenticated
    page_key = page_number or "1"

    if is_anon:
        cached = cache.get(_anon_brainews_cache_key(page_key))
        if cached is not None:
            return cached

    qs = feed_list_optimizations(
        Item.objects
        .filter(is_published=True)
        .with_counters()
        .select_related("category", "author", "author__profile")
        .order_by('-published_date')
    )
    qs = annotate_user_liked(qs, request.user)
    qs = annotate_user_bookmarked(qs, request.user)
    qs = qs.order_by('-published_date', '-pk')

    paginator = Paginator(qs, 40)
    page_obj = paginator.get_page(page_number)

    page_range = paginator.get_elided_page_range(
        number=page_obj.number,
        on_each_side=1,
        on_ends=1
    )

    breadcrumbs = build_breadcrumbs(
        breadcrumb("BraiNews", None),
    )

    response = render(request, "smart_blog/items_list.html", {
        "page_obj": page_obj,
        "page_range": page_range,
        "items": page_obj.object_list,
        "breadcrumbs": breadcrumbs,
    })

    if is_anon:
        cache.set(
            _anon_brainews_cache_key(page_key),
            response,
            _ANON_BRAINEWS_CACHE_TTL,
        )

    return response


def items_filtered(request):
    """Returns filtered items HTML for BraiNews filter block (Liked/Bookmarked/Posted/For you)."""
    if not request.user.is_authenticated:
        return HttpResponseForbidden()
    filter_type = request.GET.get('filter', '').strip().lower()
    if filter_type not in ('liked', 'bookmarked', 'posted', 'for_you'):
        return HttpResponse('', content_type='text/html')

    if filter_type == 'for_you':
        from smart_blog.services.for_you_recommendations import (
            for_you_items_for_authenticated_user,
        )

        result = for_you_items_for_authenticated_user(request.user)
        paginator = Paginator(result.items, FILTER_AJAX_PAGE_SIZE)
        page_obj = paginator.get_page(request.GET.get("page"))
        items = annotate_feed_page_items(request.user, page_obj)
        empty_msg = 'Nothing to recommend yet'
        append_fragment = request.GET.get("append") == "1"
        listing_source_url = request.build_absolute_uri(
            reverse("smart_blog:items_list")
        )
        ctx = {
            "items": items,
            "user": request.user,
            "listing_source": "for_you",
            "listing_source_url": listing_source_url,
            "empty_msg": empty_msg,
            "filter_type": filter_type,
            "page_obj": page_obj,
            "paginator": paginator,
        }
        tmpl = (
            "includes/filtered_cards_append.html"
            if append_fragment
            else "includes/filtered_cards.html"
        )
        html = render_to_string(tmpl, ctx)
        return HttpResponse(html, content_type="text/html")
    qs = (
        Item.objects
        .with_counters()
        .filter(is_published=True)
        .order_by('-published_date')
    )
    tag_slug = request.GET.get('tag_slug', '').strip()
    search_q = request.GET.get('q', '').strip()
    if tag_slug:
        tag_obj = Tag.objects.filter(slug=tag_slug).first()
        if tag_obj:
            qs = qs.filter(tags=tag_obj)
    elif search_q:
        by_title = request.GET.get('by_title') in ('1', 'true', 'True')
        by_text = request.GET.get('by_text') in ('1', 'true', 'True')
        by_tags = request.GET.get('by_tags') in ('1', 'true', 'True')
        if not (by_title or by_text or by_tags):
            by_title = by_text = by_tags = True
        qs = build_search_filter(qs, search_q, by_title, by_text, by_tags)
    qs = annotate_user_liked(qs, request.user)
    qs = annotate_user_bookmarked(qs, request.user)
    if filter_type == 'liked':
        like_exists = Like.objects.filter(item=OuterRef('pk'), user=request.user)
        like_date_subq = Like.objects.filter(item=OuterRef('pk'), user=request.user).values('created_at')[:1]
        qs = qs.filter(Exists(like_exists)).annotate(
            user_like_date=Subquery(like_date_subq)
        ).order_by('-user_like_date', '-pk')
        empty_msg = 'Nothing was liked'
    elif filter_type == 'bookmarked':
        bookmark_exists = Bookmark.objects.filter(item=OuterRef('pk'), user=request.user)
        bookmark_date_subq = Bookmark.objects.filter(item=OuterRef('pk'), user=request.user).values('created_at')[:1]
        qs = qs.filter(Exists(bookmark_exists)).annotate(
            user_bookmark_date=Subquery(bookmark_date_subq)
        ).order_by('-user_bookmark_date', '-pk')
        empty_msg = 'Nothing was bookmarked'
    else:
        # posted — current user's published posts
        qs = qs.filter(author_id=request.user.pk).order_by('-published_date', '-pk')
        empty_msg = 'No posts yet'
    qs = feed_list_optimizations(
        qs.select_related("category", "author", "author__profile")
    )
    paginator = Paginator(qs, FILTER_AJAX_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    items = list(page_obj.object_list)

    append_fragment = request.GET.get("append") == "1"
    if search_q:
        listing_source = 'search'
        listing_query = search_q
        search_params = {'q': search_q}
        if request.GET.get('by_title'): search_params['by_title'] = request.GET.get('by_title')
        if request.GET.get('by_text'): search_params['by_text'] = request.GET.get('by_text')
        if request.GET.get('by_tags'): search_params['by_tags'] = request.GET.get('by_tags')
        listing_source_url = request.build_absolute_uri('/search/?' + urlencode(search_params))
    elif tag_slug:
        listing_source = 'tag'
        tag_obj = Tag.objects.filter(slug=tag_slug).first()
        listing_tag = tag_obj.tag_name if tag_obj else ''
        listing_tag_slug = tag_slug
        listing_source_url = request.build_absolute_uri(reverse('smart_blog:tag_list', kwargs={'slug': tag_slug}))
    else:
        listing_source = 'items_list'
        listing_query = listing_tag = listing_tag_slug = ''
        listing_source_url = request.build_absolute_uri(reverse('smart_blog:items_list'))
    ctx = {
        'items': items,
        'user': request.user,
        'listing_source': listing_source,
        'listing_source_url': listing_source_url,
        'empty_msg': empty_msg,
        'filter_type': filter_type,
        'page_obj': page_obj,
        'paginator': paginator,
    }
    if listing_source == 'search':
        ctx['listing_query'] = listing_query
    elif listing_source == 'tag':
        ctx['listing_tag'] = listing_tag
        ctx['listing_tag_slug'] = listing_tag_slug
    tmpl = (
        'includes/filtered_cards_append.html'
        if append_fragment
        else 'includes/filtered_cards.html'
    )
    html = render_to_string(tmpl, ctx)
    return HttpResponse(html, content_type='text/html')


def tag_list(request, slug):
    tag = get_object_or_404(Tag, slug=slug)

    qs = feed_list_optimizations(
        tag.items
        .filter(is_published=True)
        .with_counters()
        .select_related("category", "author", "author__profile")
        .order_by('-published_date')
    )
    qs = annotate_user_liked(qs, request.user)
    qs = annotate_user_bookmarked(qs, request.user)
    qs = qs.order_by('-published_date', '-pk')

    paginator = Paginator(qs, 40)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(
        number=page_obj.number,
        on_each_side=1,
        on_ends=1
    )

    breadcrumbs = build_breadcrumbs(
        breadcrumb(tag.tag_name, None),
    )

    return render(request, "smart_blog/tag_items_list.html", {
        "tag": tag,
        "page_obj": page_obj,
        "page_range": page_range,
        "items": page_obj.object_list,
        "breadcrumbs": breadcrumbs,
    })


def category_list(request, slug):
    """301: legacy /brainews/category/<slug>/ -> /topics/<slug>/"""
    return HttpResponsePermanentRedirect(
        reverse("smart_blog:topic_detail", kwargs={"slug": slug})
    )
