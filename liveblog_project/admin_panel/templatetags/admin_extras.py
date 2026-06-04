"""Admin panel template tags."""
from django import template
from django.utils.safestring import mark_safe

from login.middleware import is_user_online

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


@register.simple_tag
def user_online_indicator(user):
    """Green/red dot for online status (static, no pulse — unlike admin-online-status__dot)."""
    if is_user_online(user):
        return mark_safe(
            '<span class="admin-user-online-dot admin-user-online-dot--online" '
            'role="img" aria-label="Online" title="Online"></span>'
        )
    return mark_safe(
        '<span class="admin-user-online-dot admin-user-online-dot--offline" '
        'role="img" aria-label="Offline" title="Offline"></span>'
    )
