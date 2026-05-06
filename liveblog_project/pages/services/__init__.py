"""Pages app: reusable context builders (home, FAQ, HTML sitemap, static copy)."""
from pages.services.faq_list import get_public_faq_items
from pages.services.home_context import build_home_page_context
from pages.services.sitemap_html import build_sitemap_page_context
from pages.services.static_content import (
    get_about_page_for_public,
    get_contacts_page_for_public,
)

__all__ = [
    "build_home_page_context",
    "build_sitemap_page_context",
    "get_about_page_for_public",
    "get_contacts_page_for_public",
    "get_public_faq_items",
]
