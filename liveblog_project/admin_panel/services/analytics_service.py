"""Analytics service for admin dashboard."""
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate

from smart_blog.models import Item, Comment
from django.contrib.auth import get_user_model

User = get_user_model()

ACTIVITY_CHART_CACHE_KEY = "admin:activity_chart:v1:{days}"
ACTIVITY_CHART_TTL = 120
ANALYTICS_PAGE_CACHE_KEY = "admin:analytics:dashboard:v1"
ANALYTICS_PAGE_TTL = 120


def get_activity_chart_data(days=14):
    """Daily activity (posts, comments, users). Cached briefly to cut DB load."""
    key = ACTIVITY_CHART_CACHE_KEY.format(days=days)
    cached = cache.get(key)
    if cached is not None:
        return cached
    data = _compute_activity_chart_data(days)
    cache.set(key, data, ACTIVITY_CHART_TTL)
    return data


def _compute_activity_chart_data(days=14):
    """Get daily activity (posts, comments, users) for chart."""
    _tz = timezone.get_current_timezone()
    since = timezone.now() - timezone.timedelta(days=days)
    # Posts per day (bucket by local calendar day — matches TIME_ZONE)
    posts = Item.objects.filter(published_date__gte=since).annotate(
        date=TruncDate('published_date', tzinfo=_tz)
    ).values('date').annotate(count=Count('pk')).order_by('date')
    posts_map = {str(p['date']): p['count'] for p in posts}

    # Comments per day
    comments = Comment.objects.filter(created__gte=since).annotate(
        date=TruncDate('created', tzinfo=_tz)
    ).values('date').annotate(count=Count('pk')).order_by('date')
    comments_map = {str(c['date']): c['count'] for c in comments}

    # Users per day (use _base_manager to include all, including inactive)
    users = User._base_manager.filter(date_joined__gte=since).annotate(
        date=TruncDate('date_joined', tzinfo=_tz)
    ).values('date').annotate(count=Count('pk')).order_by('date')
    users_map = {str(u['date']): u['count'] for u in users}

    labels = []
    posts_data = []
    comments_data = []
    users_data = []
    anchor = timezone.localdate()
    for i in range(days):
        d = anchor - timezone.timedelta(days=days - 1 - i)
        labels.append(d.isoformat())
        posts_data.append(posts_map.get(str(d), 0))
        comments_data.append(comments_map.get(str(d), 0))
        users_data.append(users_map.get(str(d), 0))

    return {
        'labels': labels,
        'posts': posts_data,
        'comments': comments_data,
        'users': users_data,
    }


def get_analytics_page_context():
    """Bundle analytics list view queries; cached for ANALYTICS_PAGE_TTL seconds."""
    cached = cache.get(ANALYTICS_PAGE_CACHE_KEY)
    if cached is not None:
        return cached
    ctx = {
        'top_posts': get_top_posts_by_popularity(limit=20),
        'views_growth': get_views_growth(days=30),
        'users_growth': get_users_growth(days=30),
        'comments_growth': get_comments_growth(days=30),
    }
    cache.set(ANALYTICS_PAGE_CACHE_KEY, ctx, ANALYTICS_PAGE_TTL)
    return ctx


def get_post_activity_chart_data(item, days=14):
    """Per-post activity: views, likes, comments per day for chart."""
    from smart_blog.models import ItemView, Like

    _tz = timezone.get_current_timezone()
    since = timezone.now() - timezone.timedelta(days=days)
    labels = []
    views_data = []
    likes_data = []
    comments_data = []

    # Views per day (ItemView)
    views_qs = ItemView.objects.filter(item=item, viewed_at__gte=since).annotate(
        date=TruncDate('viewed_at', tzinfo=_tz)
    ).values('date').annotate(count=Count('pk')).order_by('date')
    views_map = {str(v['date']): v['count'] for v in views_qs}

    # Likes per day
    likes_qs = Like.objects.filter(item=item, created_at__gte=since).annotate(
        date=TruncDate('created_at', tzinfo=_tz)
    ).values('date').annotate(count=Count('pk')).order_by('date')
    likes_map = {str(l['date']): l['count'] for l in likes_qs}

    # Comments per day
    comments_qs = Comment.objects.filter(item=item, created__gte=since).annotate(
        date=TruncDate('created', tzinfo=_tz)
    ).values('date').annotate(count=Count('pk')).order_by('date')
    comments_map = {str(c['date']): c['count'] for c in comments_qs}

    anchor = timezone.localdate()
    for i in range(days):
        d = anchor - timezone.timedelta(days=days - 1 - i)
        labels.append(d.isoformat())
        views_data.append(views_map.get(str(d), 0))
        likes_data.append(likes_map.get(str(d), 0))
        comments_data.append(comments_map.get(str(d), 0))

    return {
        'labels': labels,
        'views': views_data,
        'likes': likes_data,
        'comments': comments_data,
    }


def get_top_posts_by_popularity(limit=20):
    """Top posts by popularity (views, likes, comments, reposts)."""
    from django.db.models import Q
    return list(
        Item.objects.filter(is_published=True)
        .select_related('author', 'category')
        .annotate(comments_count=Count('comments', filter=Q(comments__parent__isnull=True), distinct=True))
        .order_by('-views_count', '-likes_count', '-reposts_count')[:limit]
    )


def _growth_data(model, date_field, days, date_attr='date'):
    """Helper for growth data."""
    since = timezone.now() - timezone.timedelta(days=days)
    qs = model.objects.filter(**{f'{date_field}__gte': since}).annotate(
        **{date_attr: TruncDate(date_field)}
    ).values(date_attr).annotate(count=Count('pk')).order_by(date_attr)
    return list(qs)


def get_views_growth(days=30):
    """Views growth - new views per day from ItemView."""
    from smart_blog.models import ItemView
    since = timezone.now() - timezone.timedelta(days=days)
    return list(
        ItemView.objects.filter(viewed_at__gte=since)
        .annotate(date=TruncDate('viewed_at'))
        .values('date')
        .annotate(count=Count('pk'))
        .order_by('date')
    )


def get_users_growth(days=30):
    """New users per day."""
    return _growth_data(User, 'date_joined', days, 'date')


def get_comments_growth(days=30):
    """Comments per day."""
    return _growth_data(Comment, 'created', days, 'date')
