from django.contrib import admin
from pages.models import FAQItem, HomePageContent, HomeQuickLink


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ('question', 'order', 'is_active')
    list_editable = ('order', 'is_active')


@admin.register(HomePageContent)
class HomePageContentAdmin(admin.ModelAdmin):
    """Singleton: only row pk=1."""

    list_display = ('__str__', 'updated_at')
    readonly_fields = ('updated_at', 'updated_by')
    fieldsets = (
        ('SEO & Hero', {
            'fields': (
                'browser_title',
                'meta_description',
                'hero_h1',
                'hero_lede',
                'hero_featured_item',
            ),
        }),
        ('Primary CTA', {
            'fields': ('cta_primary_label', 'cta_primary_url'),
        }),
        ('Sections', {
            'fields': (
                'show_quick_links',
                'show_in_trend',
                'show_mindset_live',
                'show_explore_topics',
            ),
        }),
        ('Audit', {
            'fields': ('updated_at', 'updated_by'),
        }),
    )

    def has_add_permission(self, request):
        return not HomePageContent.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HomeQuickLink)
class HomeQuickLinkAdmin(admin.ModelAdmin):
    list_display = ('label', 'url', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('label', 'url')