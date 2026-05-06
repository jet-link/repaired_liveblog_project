"""Admin panel template tags."""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def _get_trust_score(user):
    try:
        return getattr(user.profile, 'trust_score', 10.0)
    except Exception:
        return 10.0


def _trust_score_badge_class(score):
    if score >= 8:
        return 'admin-badge-success'
    if score >= 5:
        return 'admin-badge-pending'
    if score >= 3:
        return 'admin-badge-warning'
    return 'admin-badge-danger'


@register.simple_tag
def trust_score_badge(user):
    """Output a span with trust score and badge class."""
    score = _get_trust_score(user)
    cls = _trust_score_badge_class(score)
    return mark_safe(f'<span class="admin-badge {cls}">{score:.1f}</span>')
