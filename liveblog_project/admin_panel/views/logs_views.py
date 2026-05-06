"""Logs view - placeholder for future log viewer."""
from django.shortcuts import render

from admin_panel.decorators import admin_required


@admin_required
def logs_view(request):
    """Placeholder for system logs (future: AI moderation, activity log)."""
    return render(request, 'admin/logs/logs_placeholder.html')
