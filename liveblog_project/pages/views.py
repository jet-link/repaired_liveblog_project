from django.http import Http404
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from django.views import View

from pages.services.faq_list import get_public_faq_items
from pages.services.home_context import build_home_page_context
from pages.services.sitemap_html import build_sitemap_page_context
from pages.static_pages import get_about_page_for_public, get_contacts_page_for_public


def home_page(request):
    context = build_home_page_context(request)
    return render(request, "pages/home.html", context)


home_view = home_page


class PageView(View):
    def get(self, request, slug, *args, **kwargs):
        if slug == "about":
            return render(
                request,
                "pages/about.html",
                {"about": get_about_page_for_public()},
            )
        if slug == "contacts":
            return render(
                request,
                "pages/contacts.html",
                {"contacts": get_contacts_page_for_public()},
            )
        template_name = f"pages/{slug}.html"
        try:
            return render(request, template_name, {})
        except TemplateDoesNotExist:
            raise Http404


class FAQView(View):
    def get(self, request):
        return render(
            request,
            "pages/faq.html",
            {"faq_items": get_public_faq_items()},
        )


def sitemap_page(request):
    context = build_sitemap_page_context(request)
    return render(request, "pages/sitemap.html", context)


def custom_404_view(request, exception):
    return render(request, "errors/404.html", status=404)


def custom_403_view(request, exception=None):
    return render(request, "errors/403.html", status=403)
