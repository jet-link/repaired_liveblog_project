from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Tag,
    Category,
    Item,
    ItemImage,
    Comment,
    CommentLike,
    Like,
    ItemView,
    Bookmark,
    ContentReport,
    Notification,
    SearchHistory,
    PostRepost,
    ItemStatsHourly,
    TrendingItem,
)
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('tag_name', 'slug')
    search_fields = ('tag_name', 'slug')
    prepopulated_fields = {"slug": ("tag_name",)}

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "description")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "published_date", "is_published", "likes_count", "views_count", "bookmarks_count", "reposts_count")
    list_filter = ("is_published", "category", "published_date")
    search_fields = ("title", "text")
    filter_horizontal = ("tags",)
    fields = ("author", "title", "text", "category", "tags", "slug", "likes_count", "views_count", "bookmarks_count", "reposts_count",
              "published_date", "edited", "is_published")

@admin.register(ItemImage)
class ItemImageAdmin(admin.ModelAdmin):
    list_display = ("item", "uploaded_at")

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("item", "author", "created")
    actions = ["delete_selected"]

admin.site.register(CommentLike)
admin.site.register(Like)
admin.site.register(ItemView)
admin.site.register(Bookmark)
admin.site.register(Notification)


@admin.register(PostRepost)
class PostRepostAdmin(admin.ModelAdmin):
    list_display = ('item', 'platform', 'user', 'ip_address', 'created_at')
    list_filter = ('platform', 'created_at')
    search_fields = ('item__title', 'ip_address')
    readonly_fields = ('item', 'user', 'ip_address', 'platform', 'user_agent', 'created_at')
    ordering = ('-created_at',)


@admin.register(ItemStatsHourly)
class ItemStatsHourlyAdmin(admin.ModelAdmin):
    list_display = ("item", "hour_start", "views", "likes", "comments")
    list_filter = ("hour_start",)
    ordering = ("-hour_start",)
    raw_id_fields = ("item",)


@admin.register(TrendingItem)
class TrendingItemAdmin(admin.ModelAdmin):
    list_display = (
        "item",
        "trend_score",
        "views_24h",
        "likes_24h",
        "comments_24h",
        "growth_rate",
        "views_last_hour",
        "likes_1h",
        "comments_1h",
        "updated_at",
    )
    ordering = ("-trend_score",)
    raw_id_fields = ("item",)
    readonly_fields = ("updated_at",)


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "search_query", "results_count", "was_clicked", "created_at")
    list_filter = ("was_clicked", "created_at")
    search_fields = ("search_query",)
    ordering = ("-created_at",)
@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display = ("reason", "status", "reporter", "item_link", "comment_link", "created_at", "updated_at")
    list_filter = ("reason", "status", "created_at")
    readonly_fields = ("item_link", "comment_link", "created_at", "updated_at")
    fields = ("reporter", "item", "item_link", "comment", "comment_link", "reason", "details", "status", "created_at", "updated_at")

    def item_link(self, obj):
        if not obj.item:
            return "-"
        url = obj.item.get_absolute_url()
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.item.title)
    item_link.short_description = "Item link"

    def comment_link(self, obj):
        if not obj.comment:
            return "-"
        url = obj.comment.get_comment_url()
        return format_html('<a href="{}" target="_blank">Comment #{}</a>', url, obj.comment.pk)
    comment_link.short_description = "Comment link"

