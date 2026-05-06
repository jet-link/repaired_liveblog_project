# templatetags/counters.py
from django import template
from smart_blog.utils import count_convert

register = template.Library()

@register.filter
def human(value):
    try:
        return count_convert(int(value))
    except Exception:
        return "0"