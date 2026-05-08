"""Mindset models — Threads/Twitter-like discussions.

Theme is a top-level discussion post; Reply is a nested response.
Likes and Reposts are separate models so we can keep uniqueness per (target, user)
and signal-update denormalised counters cheaply.
"""
from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from smart_blog.utils import human_time_relative_youtube

EDITABLE_HOURS = 12


class Hashtag(models.Model):
    """#tag entity. ``slug`` is the canonical lookup key."""

    name = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(max_length=80, unique=True, db_index=True)
    themes_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-themes_count', 'name')

    def __str__(self) -> str:
        return f'#{self.name}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or self.name.lower()
        super().save(*args, **kwargs)


class Theme(models.Model):
    """Top-level discussion post."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mindset_themes',
    )
    body = models.TextField(help_text='Sanitised HTML (CKEditor input)')
    body_text = models.TextField(blank=True, help_text='Plain-text projection of body for previews/search.')
    hashtags = models.ManyToManyField(Hashtag, related_name='themes', blank=True)

    replies_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    reposts_count = models.PositiveIntegerField(default=0)

    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['author', '-created_at']),
        ]

    def __str__(self) -> str:
        return f'Theme #{self.pk} by {self.author_id}'

    @property
    def human_published(self) -> str:
        return human_time_relative_youtube(self.created_at)

    @property
    def editable_until(self):
        return self.created_at + timedelta(hours=EDITABLE_HOURS)

    @property
    def is_editable(self) -> bool:
        return timezone.now() <= self.editable_until

    @property
    def preview(self) -> str:
        text = (self.body_text or '').strip()
        if len(text) <= 80:
            return text
        return text[:77].rstrip() + '…'


class Reply(models.Model):
    """Nested response under a Theme. ``parent`` for second-level threading."""

    theme = models.ForeignKey(
        Theme,
        on_delete=models.CASCADE,
        related_name='replies',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mindset_replies',
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='children',
        null=True,
        blank=True,
    )
    body = models.TextField()

    replies_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    reposts_count = models.PositiveIntegerField(default=0)

    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('created_at',)
        indexes = [
            models.Index(fields=['theme', 'created_at']),
            models.Index(fields=['parent', 'created_at']),
        ]

    def __str__(self) -> str:
        return f'Reply #{self.pk} on theme {self.theme_id}'

    @property
    def human_published(self) -> str:
        return human_time_relative_youtube(self.created_at)

    @property
    def editable_until(self):
        return self.created_at + timedelta(hours=EDITABLE_HOURS)

    @property
    def is_editable(self) -> bool:
        return timezone.now() <= self.editable_until


class ThemeLike(models.Model):
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mindset_theme_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('theme', 'user')


class ThemeRepost(models.Model):
    """Twitter-style retweet — surfaces the theme in reposter's Mindset feed."""

    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name='reposts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mindset_theme_reposts')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('theme', 'user')
        ordering = ('-created_at',)


class ReplyLike(models.Model):
    reply = models.ForeignKey(Reply, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mindset_reply_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('reply', 'user')


class ReplyRepost(models.Model):
    reply = models.ForeignKey(Reply, on_delete=models.CASCADE, related_name='reposts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mindset_reply_reposts')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('reply', 'user')
        ordering = ('-created_at',)
