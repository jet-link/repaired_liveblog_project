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

    def has_add_permission(self, request):
        return not HomePageContent.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HomeQuickLink)
class HomeQuickLinkAdmin(admin.ModelAdmin):
    list_display = ('label', 'url', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('label', 'url')