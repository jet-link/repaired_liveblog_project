"""Pre-computed trending metrics for templates (reads TrendingItem, no live DB queries)."""
from django import template

from smart_blog.models import TrendingItem

register = template.Library()


@register.simple_tag
def trending_live_metrics(item):
    """Return dict of trending stats from the pre-computed TrendingItem row."""
    try:
        t = TrendingItem.objects.get(item=item)
    except TrendingItem.DoesNotExist:
        return {
            "views_24h": 0, "likes_24h": 0, "comments_24h": 0,
            "views_last_hour": 0, "likes_1h": 0, "comments_1h": 0,
        }
    return {
        "views_24h": t.views_24h,
        "likes_24h": t.likes_24h,
        "comments_24h": t.comments_24h,
        "views_last_hour": t.views_last_hour,
        "likes_1h": t.likes_1h,
        "comments_1h": t.comments_1h,
    }
