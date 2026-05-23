from django.contrib import admin

from .models import (
    Hashtag,
    Reply,
    ReplyImage,
    ReplyLike,
    ReplyRepost,
    Theme,
    ThemeImage,
    ThemeLike,
    ThemeRepost,
)


@admin.register(Hashtag)
class HashtagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'themes_count', 'created_at')
    search_fields = ('name', 'slug')
    readonly_fields = ('themes_count', 'created_at')


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'preview_short', 'replies_count', 'likes_count', 'reposts_count', 'created_at')
    list_filter = ('is_deleted', 'created_at')
    search_fields = ('author__username', 'body_text')
    readonly_fields = ('replies_count', 'likes_count', 'reposts_count', 'created_at', 'updated_at')

    def preview_short(self, obj):
        return (obj.body_text or '')[:60]
    preview_short.short_description = 'Body'


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('id', 'theme', 'author', 'parent', 'replies_count', 'likes_count', 'reposts_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('author__username', 'body')
    readonly_fields = ('replies_count', 'likes_count', 'reposts_count', 'created_at', 'updated_at')


admin.site.register(ThemeLike)
admin.site.register(ThemeRepost)
admin.site.register(ReplyLike)
admin.site.register(ReplyRepost)
admin.site.register(ThemeImage)
admin.site.register(ReplyImage)
