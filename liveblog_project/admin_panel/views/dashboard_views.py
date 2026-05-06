"""Dashboard view for admin panel."""
import json

from django.shortcuts import render
from django.utils import timezone

from admin_panel.decorators import admin_required
from admin_panel.services.analytics_service import get_activity_chart_data
from admin_panel.services.dashboard_stats import get_dashboard_summary


@admin_required
def dashboard_view(request):
    """Main dashboard at /admin/."""
    today = timezone.localdate()
    summary = get_dashboard_summary(today)
    activity_data = get_activity_chart_data(days=14)
    activity_json = json.dumps(activity_data)

    context = {
        **summary,
        "activity_data": activity_data,
        "activity_json": activity_json,
    }
    return render(request, "admin/dashboard/dashboard.html", context)
