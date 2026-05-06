"""Helpers for admin_panel."""
from django.shortcuts import redirect
from django.urls import reverse


def redirect_preserve_query(request, url_name, **reverse_kwargs):
    """
    Redirect to a named admin_panel URL, keeping the request query string
    (pagination, filters, sort).
    """
    if reverse_kwargs:
        url = reverse(f'admin_panel:{url_name}', kwargs=reverse_kwargs)
    else:
        url = reverse(f'admin_panel:{url_name}')
    qs = request.GET.urlencode()
    if qs:
        url += '?' + qs
    return redirect(url)
