from django.conf import settings
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

