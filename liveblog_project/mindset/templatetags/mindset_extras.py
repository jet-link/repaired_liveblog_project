from django import template
from django.utils.safestring import mark_safe

from mindset.body_html import render_mindset_body

register = template.Library()


@register.filter(name='mindset_body')
def mindset_body(value):
    """Render Theme/Reply body as safe HTML (sanitised + URL/hashtag linkified)."""
    return mark_safe(render_mindset_body(value or ''))
