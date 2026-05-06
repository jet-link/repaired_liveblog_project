"""Singleton home page settings (DB + defaults)."""
from pages.home_defaults import HOME_PAGE_DEFAULTS
from pages.models import HomePageContent


def get_home_page() -> HomePageContent:
    obj, _ = (
        HomePageContent.objects.select_related(
            "hero_featured_item",
            "editor_pick_1",
            "editor_pick_2",
            "editor_pick_3",
        ).get_or_create(pk=1, defaults=HOME_PAGE_DEFAULTS)
    )
    return obj
