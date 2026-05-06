"""Search views: search_view, api_search_history_*."""
from django.conf import settings
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from smart_blog.models import Item, SearchHistory
from smart_blog.search_utils import build_search_filter
from smart_blog.utils import breadcrumb, build_breadcrumbs
from smart_blog.feed_queryset import feed_list_optimizations
from smart_blog.views._helpers import annotate_user_bookmarked, annotate_user_liked

SEARCH_RESULTS_PER_PAGE = 40
SEARCH_SUGGEST_LIMIT = 10


@ratelimit(key='ip', rate=settings.RATELIMIT_SEARCH_SUGGEST_RATE, method='GET', block=False)
def api_search_suggest(request):
    """Lightweight FTS suggestions for the search overlay (titles + links only)."""
    if getattr(request, 'limited', False):
        return JsonResponse({'items': []}, status=429)
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'items': []})

    items_qs = Item.objects.filter(is_published=True)
    items_qs = build_search_filter(items_qs, q, True, True, True)
    rows = list(items_qs.values('title', 'slug')[:SEARCH_SUGGEST_LIMIT])
    items = [
        {'title': r['title'], 'url': reverse('smart_blog:post_detail', args=[r['slug']])}
        for r in rows
    ]
    return JsonResponse({'items': items})


@ratelimit(key='ip', rate=settings.RATELIMIT_SEARCH_RATE, method='GET', block=False)
def search_view(request):
    if getattr(request, 'limited', False):
        return render(request, 'errors/429.html', status=429)
    q = request.GET.get('q', '').strip()
    by_title = request.GET.get('by_title') in ('1', 'true', 'True')
    by_text  = request.GET.get('by_text')  in ('1', 'true', 'True')
    by_tags  = request.GET.get('by_tags')  in ('1', 'true', 'True')

    selected_fields = []
    if request.GET.get('by_title') in ('1','true','True'):
        selected_fields.append('title')
    if request.GET.get('by_text') in ('1','true','True'):
        selected_fields.append('text')
    if request.GET.get('by_tags') in ('1','true','True'):
        selected_fields.append('tag')

    if not selected_fields:
        selected_fields = ['title', 'text', 'tag']

    page_obj = None
    page_range = None
    results_total = 0
    pagination_base_qs = ''
    items = []

    if not q:
        items_qs = Item.objects.none()
    else:
        if not (by_title or by_text or by_tags):
            by_title = by_text = by_tags = True

        items_qs = feed_list_optimizations(
            Item.objects
            .with_counters()
            .select_related("category", "author", "author__profile")
            .filter(is_published=True)
            .prefetch_related("tags")
        )
        items_qs = build_search_filter(items_qs, q, by_title, by_text, by_tags)
        items_qs = annotate_user_liked(items_qs, request.user)
        items_qs = annotate_user_bookmarked(items_qs, request.user)
        if not items_qs.ordered:
            items_qs = items_qs.order_by('-published_date', '-pk')

        paginator = Paginator(items_qs, SEARCH_RESULTS_PER_PAGE)
        page_obj = paginator.get_page(request.GET.get('page'))
        page_range = paginator.get_elided_page_range(
            number=page_obj.number,
            on_each_side=1,
            on_ends=1
        )
        items = page_obj.object_list
        results_total = paginator.count

        params = request.GET.copy()
        params.pop('page', None)
        pagination_base_qs = params.urlencode()

    if q:
        breadcrumbs = build_breadcrumbs(
            breadcrumb("Search", reverse("global_search")),
            breadcrumb(q, None),
        )
        if request.user.is_authenticated:
            from smart_blog.tasks import save_search_history_record
            filters_dict = {
                'by_title': by_title, 'by_text': by_text, 'by_tags': by_tags
            }
            save_search_history_record(
                request.user.pk, q, results_total, filters_dict,
                bool(request.GET.get('from_history')),
            )
    else:
        breadcrumbs = build_breadcrumbs(
            breadcrumb("Search", None),
        )

    return render(request, 'smart_blog/search_results.html', {
        'items': items,
        'query': q,
        'selected_fields': selected_fields,
        'breadcrumbs': breadcrumbs,
        'page_obj': page_obj,
        'page_range': page_range,
        'results_total': results_total,
        'pagination_base_qs': pagination_base_qs,
    })


@ratelimit(key='ip', rate=settings.RATELIMIT_SEARCH_HISTORY_RATE, method='GET', block=False)
def api_search_history_list(request):
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'rate_limited', 'items': []}, status=429)
    if not request.user.is_authenticated:
        return JsonResponse({'items': []})
    items = list(
        SearchHistory.objects.filter(user=request.user).order_by('-created_at')[:25].values(
            'id', 'search_query', 'created_at', 'results_count', 'search_filters', 'was_clicked'
        )
    )
    for it in items:
        it['created_at'] = it['created_at'].isoformat()
    return JsonResponse({'items': items})


@ratelimit(key='ip', rate=settings.RATELIMIT_SEARCH_HISTORY_RATE, method='POST', block=False)
@require_POST
def api_search_history_clicked(request, pk):
    if getattr(request, 'limited', False):
        return JsonResponse({'ok': False, 'error': 'rate_limited'}, status=429)
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False}, status=403)
    try:
        rec = SearchHistory.objects.get(pk=pk, user=request.user)
        rec.was_clicked = True
        rec.save(update_fields=['was_clicked'])
        return JsonResponse({'ok': True})
    except SearchHistory.DoesNotExist:
        return JsonResponse({'ok': False}, status=404)


@ratelimit(key='ip', rate=settings.RATELIMIT_SEARCH_HISTORY_RATE, method='POST', block=False)
@require_POST
def api_search_history_clear(request):
    if getattr(request, 'limited', False):
        return JsonResponse({'ok': False, 'error': 'rate_limited'}, status=429)
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False}, status=403)
    SearchHistory.objects.filter(user=request.user).delete()
    return JsonResponse({'ok': True})


@ratelimit(key='ip', rate=settings.RATELIMIT_SEARCH_HISTORY_RATE, method='POST', block=False)
@require_POST
def api_search_history_delete(request, pk):
    if getattr(request, 'limited', False):
        return JsonResponse({'ok': False, 'error': 'rate_limited'}, status=429)
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False}, status=403)
    try:
        rec = SearchHistory.objects.get(pk=pk, user=request.user)
        rec.delete()
        return JsonResponse({'ok': True})
    except SearchHistory.DoesNotExist:
        return JsonResponse({'ok': False}, status=404)
