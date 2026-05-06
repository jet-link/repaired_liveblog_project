"""Admin: sitemap statistics (public index, not admin URLs)."""
from django.contrib.sites.models import Site
from django.shortcuts import render
from django.urls import reverse

from admin_panel.decorators import admin_required
from admin_panel.services.sitemap_service import get_sitemap_summary
from smart_blog.sitemaps import SITEMAP_SECTION_LABELS

_EXPECTED_NEWS_DOMAINS = frozenset({"brainstorm.news", "www.brainstorm.news"})


@admin_required
def sitemap_stats_view(request):
    summary = get_sitemap_summary()
    sitemap_public_url = request.build_absolute_uri("/sitemap.xml")
    robots_url = request.build_absolute_uri("/robots.txt")
    html_sitemap_url = request.build_absolute_uri(reverse("pages:sitemap_page"))
    site = Site.objects.get_current()
    domain_lower = (site.domain or "").strip().lower().rstrip(".")
    site_domain_expected = domain_lower in _EXPECTED_NEWS_DOMAINS

    context = {
        "summary": summary,
        "sitemap_public_url": sitemap_public_url,
        "robots_url": robots_url,
        "html_sitemap_url": html_sitemap_url,
        "site_current": site,
        "site_domain_expected": site_domain_expected,
        "sitemap_section_labels": SITEMAP_SECTION_LABELS,
    }
    return render(request, "admin/analytics/sitemap_stats.html", context)
