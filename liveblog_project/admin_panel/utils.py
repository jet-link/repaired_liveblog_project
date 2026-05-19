"""Helpers for admin_panel."""
from django.shortcuts import redirect, render
from django.urls import reverse


def admin_form_error_response(request, template, context):
    """Re-render admin form after validation failure (forms use data-turbo=\"false\")."""
    return render(request, template, context)


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
