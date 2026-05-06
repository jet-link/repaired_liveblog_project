from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class FAQItem(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.question


class AboutPageContent(models.Model):
    """Singleton row (pk=1): public About page copy."""

    browser_title = models.CharField(max_length=120, default='About — brainstorm.org')
    title_h1 = models.CharField(max_length=200, default='brainstorm.org')
    lede = models.TextField(default='')
    mission_heading = models.CharField(max_length=200, default='Why we’re here')
    mission_item_1 = models.TextField(default='')
    mission_item_2 = models.TextField(default='')
    mission_item_3 = models.TextField(default='')
    facts_heading_hidden = models.CharField(
        max_length=120,
        default='At a glance',
        help_text='Screen-reader only (visually hidden on site).',
    )
    fact1_label = models.CharField(max_length=120, default='Format')
    fact1_value = models.TextField(default='')
    fact2_label = models.CharField(max_length=120, default='Language')
    fact2_value = models.TextField(default='')
    fact3_label = models.CharField(max_length=120, default='Audience')
    fact3_value = models.TextField(default='')
    cta_link_text = models.CharField(max_length=120, default='Contact us')
    cta_hint = models.CharField(max_length=255, default=' — collaboration and general feedback.')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='about_page_edits',
    )

    class Meta:
        verbose_name = 'About page content'
        verbose_name_plural = 'About page content'

    def __str__(self):
        return 'About page'


class ContactsPageContent(models.Model):
    """Singleton row (pk=1): public Contacts page copy."""

    browser_title = models.CharField(max_length=120, default='Contacts — brainstorm.org')
    title_h1 = models.CharField(max_length=200, default='Contacts')
    lede_before = models.CharField(max_length=255, default='We usually reply within ')
    lede_emphasis = models.CharField(max_length=120, default='1–2 business days')
    lede_after = models.TextField(default='')
    channels_heading = models.CharField(max_length=200, default='How to reach us')
    email_key = models.CharField(max_length=120, default='Email')
    email_address = models.CharField(max_length=255, default='discover@brainstorm.org')
    email_note = models.CharField(max_length=255, default='General questions and suggestions')
    community_key = models.CharField(max_length=120, default='Community')
    community_text = models.TextField(default='')
    no_section_heading = models.CharField(max_length=200, default='What we don’t handle')
    no_section_body = models.TextField(default='')
    footer_about_link_text = models.CharField(max_length=120, default='About')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='contacts_page_edits',
    )

    class Meta:
        verbose_name = 'Contacts page content'
        verbose_name_plural = 'Contacts page content'

    def __str__(self):
        return 'Contacts page'


class HomePageContent(models.Model):
    """Singleton row (pk=1): public home page copy and layout flags."""

    STRIP_POPULAR = "popular"
    STRIP_TRENDING = "trending"
    STRIP_NONE = "none"
    STRIP_CHOICES = [
        (STRIP_POPULAR, "Popular"),
        (STRIP_TRENDING, "In trend"),
        (STRIP_NONE, "No strip (hero + quick links only)"),
    ]

    browser_title = models.CharField(max_length=120, default="brainstorm.news")
    meta_description = models.CharField(
        max_length=320,
        blank=True,
        help_text="Meta description for search engines (plain text).",
    )
    hero_h1 = models.CharField(max_length=200, default="brainstorm.news")
    hero_lede = models.TextField(blank=True)
    cta_primary_label = models.CharField(max_length=120, blank=True)
    cta_primary_url = models.CharField(max_length=500, blank=True)
    cta_secondary_label = models.CharField(max_length=120, blank=True)
    cta_secondary_url = models.CharField(max_length=500, blank=True)
    trust_line = models.CharField(max_length=255, blank=True)
    trust_link_url = models.CharField(max_length=500, blank=True)
    show_quick_links = models.BooleanField(default=True)
    show_decorative_astronauts = models.BooleanField(
        default=False,
        help_text="Show the optional astronauts decorative block.",
    )
    content_strip_mode = models.CharField(
        max_length=16,
        choices=STRIP_CHOICES,
        default=STRIP_POPULAR,
    )
    content_strip_limit = models.PositiveSmallIntegerField(default=6)
    popular_min_likes = models.PositiveSmallIntegerField(default=6)
    show_editor_picks = models.BooleanField(default=False)
    editor_pick_order_after_strip = models.BooleanField(
        default=False,
        help_text="If checked, editor picks appear below the main strip; otherwise above.",
    )
    editor_pick_1 = models.ForeignKey(
        "smart_blog.Item",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    editor_pick_2 = models.ForeignKey(
        "smart_blog.Item",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    editor_pick_3 = models.ForeignKey(
        "smart_blog.Item",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    hero_featured_item = models.ForeignKey(
        "smart_blog.Item",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Large card on the right side of the hero. If empty, the first In Trend or latest post is used.",
    )
    show_in_trend = models.BooleanField(
        default=True,
        help_text='Show the "In Trend" section (trending posts).',
    )
    show_for_you_section = models.BooleanField(
        default=True,
        help_text='Show the "For You" block on the home page (signed-in users only; guests see a sign-in prompt).',
    )
    show_explore_topics = models.BooleanField(
        default=True,
        help_text='Show "Explore Topics" (top categories by post count).',
    )
    show_latest_brainews = models.BooleanField(
        default=True,
        help_text='Show latest BraiNews posts and "View all" link.',
    )
    show_bottom_cta = models.BooleanField(
        default=True,
        help_text="Show optional bottom call-to-action banner.",
    )
    cta_footer_title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Bottom CTA heading (e.g. Have something to say?).",
    )
    cta_footer_label = models.CharField(max_length=120, blank=True)
    cta_footer_url = models.CharField(max_length=500, blank=True)
    cache_bump = models.PositiveIntegerField(
        default=0,
        editable=False,
        help_text="Bumped on each content save to invalidate template cache.",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="home_page_edits",
    )

    class Meta:
        verbose_name = "Home page content"
        verbose_name_plural = "Home page content"

    def __str__(self):
        return "Home page"

    def clean(self):
        super().clean()
        lim = self.content_strip_limit
        if lim < 3 or lim > 12:
            raise ValidationError({"content_strip_limit": "Must be between 3 and 12."})
        if (self.cta_primary_label or "").strip() and not (self.cta_primary_url or "").strip():
            raise ValidationError(
                {"cta_primary_url": "URL is required when the primary button label is set."}
            )
        if (self.cta_secondary_label or "").strip() and not (self.cta_secondary_url or "").strip():
            raise ValidationError(
                {"cta_secondary_url": "URL is required when the secondary button label is set."}
            )
        if (self.trust_line or "").strip() and not (self.trust_link_url or "").strip():
            raise ValidationError(
                {"trust_link_url": "URL is required when the trust line is set."}
            )
        if (self.cta_footer_label or "").strip() and not (self.cta_footer_url or "").strip():
            raise ValidationError(
                {"cta_footer_url": "URL is required when the bottom CTA button label is set."}
            )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from django.db.models import F

        HomePageContent.objects.filter(pk=self.pk).update(cache_bump=F("cache_bump") + 1)


class HomeQuickLink(models.Model):
    label = models.CharField(max_length=120)
    url = models.CharField(
        max_length=500,
        help_text="Path (e.g. /search/) or full https URL.",
    )
    icon_class = models.CharField(
        max_length=80,
        blank=True,
        help_text="Font Awesome 4 class, e.g. fa-search",
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "Home quick link"
        verbose_name_plural = "Home quick links"

    def __str__(self):
        return self.label