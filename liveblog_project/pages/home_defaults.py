"""Default row values for HomePageContent pk=1 (data migration / get_or_create)."""

HOME_PAGE_DEFAULTS = {
    "browser_title": "brainstorm.news",
    "meta_description": "News, stories, and community discussion on brainstorm.news — BraiNews, trends, and topics.",
    "hero_h1": "Discover ideas that actually matter",
    "hero_lede": "Read BraiNews, explore topics, and stay ahead with meaningful content.",
    "cta_primary_label": "Explore",
    "cta_primary_url": "/topics/",
    "cta_secondary_label": "Read BraiNews",
    "cta_secondary_url": "/brainews/",
    "trust_line": "",
    "trust_link_url": "",
    "show_quick_links": True,
    "show_decorative_astronauts": False,
    "content_strip_mode": "popular",
    "content_strip_limit": 6,
    "popular_min_likes": 6,
    "show_editor_picks": False,
    "editor_pick_order_after_strip": False,
    "show_in_trend": True,
    "show_for_you_section": True,
    "show_explore_topics": True,
    "show_latest_brainews": True,
    "show_bottom_cta": True,
    "cta_footer_title": "Have something to say? Share your ideas with the community.",
    "cta_footer_label": "Create Post",
    "cta_footer_url": "/post/create/",
    "cache_bump": 0,
}

QUICK_LINK_SEED = [
    {"label": "BraiNews", "url": "/brainews/", "icon_class": "fa-newspaper-o", "order": 0},
    {"label": "In trend", "url": "/trending/", "icon_class": "fa-fire", "order": 1},
    {"label": "Topics", "url": "/topics/", "icon_class": "fa-folder-o", "order": 2},
    {"label": "Search", "url": "/search/", "icon_class": "fa-search", "order": 3},
]
