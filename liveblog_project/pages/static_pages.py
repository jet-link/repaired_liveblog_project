"""Load singleton About / Contacts (backward-compatible names for admin & imports)."""
from pages.models import AboutPageContent, ContactsPageContent
from pages.services.static_content import (
    get_about_page_for_public,
    get_about_page_instance,
    get_contacts_page_for_public,
    get_contacts_page_instance,
)


def get_about_page() -> AboutPageContent:
    return get_about_page_instance()


def get_contacts_page() -> ContactsPageContent:
    return get_contacts_page_instance()


__all__ = [
    "get_about_page",
    "get_contacts_page",
    "get_about_page_for_public",
    "get_contacts_page_for_public",
]
