"""Category theme mapping for feed/trending card placeholders and pills."""
from django import template
from django.utils.text import slugify

register = template.Library()

# slug -> Font Awesome 4.7 icon class (full class name, site templates)
_CATEGORY_ICONS = {
    "technology": "fa-microchip",
    "science": "fa-flask",
    "finance": "fa-line-chart",
    "business": "fa-bar-chart",
    "entertainment": "fa-picture-o",
    "design": "fa-paint-brush",
    "nature": "fa-leaf",
    "qa": "fa-question",
    "medicine": "fa-medkit",
    "space": "fa-rocket",
    "advertising": "fa-bullhorn",
    "movie": "fa-film",
    "sport": "fa-futbol-o",
    "sports": "fa-futbol-o",
    "aviation": "fa-plane",
}

# slug -> Font Awesome 6 classes (admin panel loads FA6 from CDN)
_CATEGORY_ICONS_FA6 = {
    "technology": "fa-solid fa-microchip",
    "science": "fa-solid fa-flask",
    "finance": "fa-solid fa-chart-line",
    "business": "fa-solid fa-chart-bar",
    "entertainment": "fa-regular fa-image",
    "design": "fa-solid fa-paintbrush",
    "nature": "fa-solid fa-leaf",
    "qa": "fa-solid fa-circle-question",
    "medicine": "fa-solid fa-kit-medical",
    "space": "fa-solid fa-rocket",
    "advertising": "fa-solid fa-bullhorn",
    "movie": "fa-solid fa-film",
    "sport": "fa-solid fa-futbol",
    "sports": "fa-solid fa-futbol",
    "aviation": "fa-solid fa-plane",
}

_DEFAULT_ICON = "fa-tag"
_DEFAULT_ICON_FA6 = "fa-solid fa-tag"
_DEFAULT_SLUG = "default"


def _theme_for_slug(slug: str) -> dict:
    slug = (slug or "").strip().lower()
    if slug in _CATEGORY_ICONS:
        return {
            "slug": slug,
            "icon": _CATEGORY_ICONS[slug],
            "icon_admin": _CATEGORY_ICONS_FA6[slug],
        }
    return {"slug": _DEFAULT_SLUG, "icon": _DEFAULT_ICON, "icon_admin": _DEFAULT_ICON_FA6}


@register.simple_tag
def category_card_theme(category):
    """Return {slug, icon, name} for card placeholder and category pill styling."""
    if not category:
        return {"slug": _DEFAULT_SLUG, "icon": _DEFAULT_ICON, "icon_admin": _DEFAULT_ICON_FA6, "name": ""}
    slug = (getattr(category, "slug", None) or "").strip().lower()
    if not slug and getattr(category, "name", None):
        slug = slugify(category.name) or _DEFAULT_SLUG
    theme = _theme_for_slug(slug)
    return {
        "slug": theme["slug"],
        "icon": theme["icon"],
        "icon_admin": theme["icon_admin"],
        "name": getattr(category, "name", "") or "",
    }
