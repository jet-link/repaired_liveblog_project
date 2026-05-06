"""Analytics views."""
from django.shortcuts import render

from admin_panel.decorators import admin_required
from admin_panel.services.analytics_service import get_analytics_page_context


@admin_required
def analytics_view(request):
    """Analytics dashboard (top posts + growth series; context cached briefly)."""
    context = get_analytics_page_context()
    return render(request, "admin/analytics/analytics.html", context)
