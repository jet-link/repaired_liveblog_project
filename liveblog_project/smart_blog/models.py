# smart_blog/models.py
from django.db import models
from django.utils import timezone
from django.contrib.postgres.search import SearchVectorField
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.text import slugify
import html
import os
import re
import string
import random
from transliterate import translit
from datetime import timedelta
from django.utils.html import strip_tags
from django.db.models import Q, Count

from .utils import human_time_relative_youtube
from .image_utils import ORIENTATION_LANDSCAPE, compute_orientation_kind


User = get_user_model()

# Stored cap for feed/list excerpts; `item_feed_card` shows 500 chars on small screens, 850 on md+.
ITEM_LIST_EXCERPT_MAX_CHARS = 850


class BodyPinContentType(models.TextChoices):
    TEXT = "text", "Text"
    DOCX = "docx", "DOCX"
    PDF = "pdf", "PDF"


class ItemQuerySet(models.QuerySet):
    def with_counters(self):
        """Annotate comments_count. views_count and bookmarks_count use denormalized model fields."""
        return self.annotate(
            comments_count=Count(
                "comments",
                filter=Q(
                    comments__parent__isnull=True,
                    comments__is_draft=False,
                    comments__deleted_at__isnull=True,
                ),
                distinct=True,
            ),
        )


class ItemManager(models.Manager):
    def get_queryset(self):
        return ItemQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)

    def with_counters(self):
        return self.get_queryset().with_counters()


class TagManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class CategoryManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class CommentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    # Item IDs that had this category before soft-delete (FK cleared to show "No category").
    pending_restore_item_ids = models.JSONField(null=True, blank=True)

    objects = CategoryManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.strip()

        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("smart_blog:topic_detail", kwargs={"slug": self.slug})

    def soft_delete(self):
        """Soft-delete, snapshot posts that used this category, clear Item.category (public: No category)."""
        from django.apps import apps
        from django.utils import timezone

        Item = apps.get_model("smart_blog", "Item")
        ids = list(
            Item.all_objects.filter(category_id=self.pk).values_list("pk", flat=True)
        )
        self.deleted_at = timezone.now()
        self.pending_restore_item_ids = ids
        self.save(update_fields=["deleted_at", "pending_restore_item_ids"])
        if ids:
            Item.all_objects.filter(pk__in=ids).update(category=None)


class Tag(models.Model):
    tag_name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    # Item IDs that had this tag at soft-delete time (M2M rows may be cleared later by forms).
    pending_restore_item_ids = models.JSONField(null=True, blank=True)

    objects = TagManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self):
        return self.tag_name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('smart_blog:tag_list', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        # Match public tag entry style (lowercase); slugify lowercases anyway
        self.tag_name = (self.tag_name or '').strip().lower()
        # Автогенерация slug при сохранении (если не указан)
        if not self.slug:
            base = slugify(self.tag_name)
            slug_candidate = base or "tag"
            # Убедимся в уникальности: добавляем суффикс при необходимости
            counter = 0
            from django.db.models import Q
            while Tag.objects.filter(Q(slug=slug_candidate)).exclude(pk=self.pk).exists():
                counter += 1
                slug_candidate = f"{base}-{counter}"
            self.slug = slug_candidate
        super().save(*args, **kwargs)

    def soft_delete(self):
        """Soft-delete and remember post IDs so restore can re-link M2M."""
        from django.apps import apps
        from django.utils import timezone

        Item = apps.get_model("smart_blog", "Item")
        ids = list(
            Item.tags.through.objects.filter(tag_id=self.pk).values_list("item_id", flat=True)
        )
        self.deleted_at = timezone.now()
        self.pending_restore_item_ids = ids
        self.save(update_fields=["deleted_at", "pending_restore_item_ids"])

# Item model
class Item(models.Model):
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="items"
    )
    title = models.CharField(max_length=255)
    text = models.TextField()
    # Legacy Editor.js document; unused (posts use CKEditor HTML in `text`). Kept for DB compatibility.
    content_json = models.JSONField(default=dict, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )
    tags = models.ManyToManyField(Tag, related_name="items", blank=True)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    search_vector = SearchVectorField(editable=False, null=True)  # PostgreSQL FTS, filled by DB
    excerpt_plain = models.CharField(
        max_length=1300,
        blank=True,
        default="",
        help_text="Plain excerpt for list cards (synced from text on save).",
    )
    likes_count = models.PositiveIntegerField(default=0, db_index=True)  # Denormalized for Popular filter
    views_count = models.PositiveIntegerField(default=0, db_index=True)  # Denormalized, synced from ItemView (user not null)
    bookmarks_count = models.PositiveIntegerField(default=0, db_index=True)  # Denormalized, synced from Bookmark
    reposts_count = models.PositiveIntegerField(default=0, db_index=True)  # Denormalized, synced from PostRepost
    published_date = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    edited = models.BooleanField(default=False)
    body_sourced_from_document = models.BooleanField(
        default=False,
        help_text="True if post body HTML was first filled from a PDF/DOCX import on create.",
    )
    body_pin_original = models.FileField(
        upload_to="item_body_pins/%Y/%m/",
        blank=True,
        null=True,
        max_length=500,
        help_text="Original PDF/DOCX attached at create (shown on post detail).",
    )
    body_pin_plain_snapshot = models.TextField(
        blank=True,
        default="",
        help_text="Plain-text snapshot of the pinned document for faithful display (esp. DOCX).",
    )
    body_pin_content_type = models.CharField(
        max_length=20,
        choices=BodyPinContentType.choices,
        default=BodyPinContentType.TEXT,
        help_text="How to render pinned document on post detail (hybrid viewer / HTML).",
    )
    body_pin_content_html = models.TextField(
        blank=True,
        default="",
        help_text="Sanitized HTML from DOCX (pandoc); empty for PDF/text.",
    )
    is_published = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    objects = ItemManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ("-published_date",)
        indexes = [
            models.Index(fields=["is_published", "-published_date"]),
            models.Index(
                fields=["is_published", "category", "-published_date"],
                name="smart_blog__topic_li_idx",
            ),
        ]

    def __str__(self):
        return self.title

    @staticmethod
    def plain_excerpt_from_html(html_text, length=ITEM_LIST_EXCERPT_MAX_CHARS):
        if not html_text:
            return ""
        plain = strip_tags(html_text)
        plain = plain.replace("\xa0", " ").replace("&nbsp;", " ")
        plain = plain.strip()
        if len(plain) <= length:
            return plain
        return plain[:length].rsplit(" ", 1)[0] + " …"

    def short_text(self, length=ITEM_LIST_EXCERPT_MAX_CHARS):
        return Item.plain_excerpt_from_html(self.text or "", length)

    @property
    def list_excerpt(self):
        """Use persisted excerpt on list pages (avoids strip_tags per request)."""
        if self.excerpt_plain:
            return self.excerpt_plain
        return self.short_text()

    @property
    def body_pin_original_basename(self) -> str:
        if not self.body_pin_original or not self.body_pin_original.name:
            return ""
        return os.path.basename(self.body_pin_original.name)

    def _generate_base_slug(self):
        base = slugify(self.title, allow_unicode=False)
        if not base:
            # если slugify вернул пусто (например, только кириллица),
            # попытаемся транслитерировать (если установлена библиотека)
            if translit:
                base = slugify(translit(self.title, 'ru', reversed=True))
            else:
                # fallback: взять буквенно-цифровую часть title или random short suffix
                base = ''.join(ch for ch in self.title if ch.isalnum())[:50]
                if not base:
                    base = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return base

    def save(self, *args, **kwargs):
        if self.slug:
            self.slug = self.slug.strip()
        # Never allow empty slug for existing items (e.g. after admin clears it when switching to draft)
        if self.pk and (not self.slug or not self.slug.strip()):
            base_slug = self._generate_base_slug()
            slug_candidate = base_slug
            counter = 1
            while Item.all_objects.filter(slug=slug_candidate).exclude(pk=self.pk).exists():
                slug_candidate = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug_candidate

        if self.pk:
            try:
                previous = Item.objects.only('text', 'title').get(pk=self.pk)

                def _norm(s):
                    if s is None:
                        return ''
                    return re.sub(r'\s+', ' ', str(s).strip())

                # Если title изменился — перегенерируем slug
                if _norm(previous.title) != _norm(self.title):
                    base_slug = self._generate_base_slug()
                    slug_candidate = base_slug
                    counter = 1
                    while Item.all_objects.filter(slug=slug_candidate).exclude(pk=self.pk).exists():
                        slug_candidate = f"{base_slug}-{counter}"
                        counter += 1
                    self.slug = slug_candidate

                if _norm(previous.text) != _norm(self.text) or _norm(previous.title) != _norm(self.title):
                    self.edited = True
            except Item.DoesNotExist:
                pass
        elif not self.slug:
            # генерируем slug для новых объектов
            base_slug = self._generate_base_slug()
            slug_candidate = base_slug
            counter = 1
            while Item.all_objects.filter(slug=slug_candidate).exists():
                slug_candidate = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug_candidate

        excerpt_src = self.text or ""
        if not excerpt_src.strip() and self.body_pin_content_type == BodyPinContentType.DOCX:
            excerpt_src = self.body_pin_content_html or ""
        if not excerpt_src.strip() and self.body_pin_content_type == BodyPinContentType.PDF and (
            self.title or ""
        ).strip():
            excerpt_src = f"<p>{html.escape((self.title or '').strip())}</p>"

        self.excerpt_plain = Item.plain_excerpt_from_html(
            excerpt_src, length=ITEM_LIST_EXCERPT_MAX_CHARS
        )

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        # для удобства
        return reverse("smart_blog:post_detail", kwargs={"slug": self.slug})

    def get_comments_absolute_url(self):
        """Dedicated comments page for this post (all threads)."""
        return reverse("smart_blog:post_comments", kwargs={"slug": self.slug})

    EDITABLE_HOURS = 24  # или 1 день = 24 часа

    @property
    def editable_until(self):
        """Возвращает datetime, до которого можно редактировать/удалять."""
        return (self.published_date or self.created) + timedelta(hours=self.EDITABLE_HOURS)

    @property
    def is_editable(self):
        """True если текущее время <= editable_until."""
        now = timezone.now()
        return now <= self.editable_until

    @property
    def is_edited(self):
        return bool(self.edited)

    @property
    def human_published(self):
        ref = self.published_date or self.created
        return human_time_relative_youtube(ref)


class ItemImage(models.Model):
    """Хранит одно изображение, связанное с публикацией.
       Поддерживает responsive: thumbnail (~300px), medium (~800px), large (~1600px).
       image — основное (large); image_thumbnail, image_medium — для списков и srcset."""
    ORIENTATION_CHOICES = (
        ("landscape", "Landscape"),
        ("portrait", "Portrait"),
        ("wide", "Ultra-wide"),
        ("square", "Square"),
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="items/%Y/%m/%d/")
    image_thumbnail = models.ImageField(upload_to="items/", blank=True, null=True)
    image_medium = models.ImageField(upload_to="items/", blank=True, null=True)
    external_url = models.URLField(max_length=500, blank=True, help_text="External CDN URL for the full image")
    width = models.PositiveIntegerField(blank=True, null=True)
    height = models.PositiveIntegerField(blank=True, null=True)
    sort_order = models.PositiveSmallIntegerField(default=0, db_index=True)
    caption = models.CharField(max_length=500, blank=True)
    orientation_kind = models.CharField(
        max_length=16,
        choices=ORIENTATION_CHOICES,
        default=ORIENTATION_LANDSCAPE,
    )
    alt_text = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "pk")

    def __str__(self):
        return f"Image for {self.item_id}"

    def save(self, *args, **kwargs):
        self.orientation_kind = compute_orientation_kind(self.width, self.height)
        super().save(*args, **kwargs)

    def get_url(self):
        """Prefer external CDN URL, fall back to local image."""
        if self.external_url:
            return self.external_url
        return self.image.url if self.image else ""

    def get_thumbnail_url(self):
        """URL для превью (списки, карточки). Fallback на image."""
        if self.image_thumbnail:
            return self.image_thumbnail.url
        return self.get_url()

    def get_medium_url(self):
        """URL для medium (srcset). Fallback на image."""
        if self.image_medium:
            return self.image_medium.url
        return self.get_url()

    def get_srcset(self):
        """Строка srcset для responsive img (thumbnail 300w, medium 800w, large 1600w)."""
        parts = []
        if self.image_thumbnail:
            parts.append(f"{self.image_thumbnail.url} 300w")
        if self.image_medium:
            parts.append(f"{self.image_medium.url} 800w")
        full_url = self.get_url()
        if full_url:
            parts.append(f"{full_url} {self.width or 1600}w")
        return ", ".join(parts) if parts else ""


class ItemVideo(models.Model):
    """Video attachment for a post. Max 3 per post."""
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="videos")
    video = models.FileField(upload_to="items/videos/%Y/%m/%d/")
    thumbnail = models.ImageField(upload_to="items/videos/thumbs/", blank=True, null=True)
    external_url = models.URLField(max_length=500, blank=True, help_text="External CDN URL for original video")
    video_360p = models.URLField(max_length=500, blank=True, help_text="360p quality URL")
    video_480p = models.URLField(max_length=500, blank=True, help_text="480p quality URL")
    video_720p = models.URLField(max_length=500, blank=True, help_text="720p quality URL")
    video_1080p = models.URLField(max_length=500, blank=True, help_text="1080p HD quality URL")
    sort_order = models.PositiveSmallIntegerField(default=0, db_index=True)
    caption = models.CharField(max_length=500, blank=True)
    duration = models.FloatField(null=True, blank=True, help_text="Duration in seconds")
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "pk")

    def __str__(self):
        return f"Video for {self.item_id}"

    def get_url(self):
        """Prefer external CDN URL, fall back to local video file."""
        if self.external_url:
            return self.external_url
        return self.video.url if self.video else ""

    def get_quality_sources(self):
        """Return dict of available quality URLs for the player."""
        sources = {}
        if self.video_1080p:
            sources[1080] = self.video_1080p
        if self.video_720p:
            sources[720] = self.video_720p
        if self.video_480p:
            sources[480] = self.video_480p
        if self.video_360p:
            sources[360] = self.video_360p
        return sources


class Comment(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="comments"
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='replies',
        on_delete=models.CASCADE
    )

    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    edited = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = CommentManager()
    all_objects = models.Manager()

    @property
    def human_published(self):
        return human_time_relative_youtube(self.created)

    class Meta:
        ordering = ("created",)
        indexes = [
            models.Index(fields=["item", "is_draft", "-created"]),
        ]

    def is_reply(self):
        return self.parent_id is not None

    def __str__(self):
        return f"Comment #{self.pk} on {self.item}"
    
    
    EDITABLE_HOURS = 24
    @property
    def editable_until(self):
        return self.created + timedelta(hours=self.EDITABLE_HOURS)

    @property
    def is_editable(self):
        return timezone.now() <= self.editable_until

    @property
    def is_edited(self):
        return bool(self.edited)

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                previous = Comment.objects.only('text').get(pk=self.pk)
                if previous.text != self.text:
                    self.edited = True
            except Comment.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def get_comment_url(self):
        """URL to view this comment: thread page for replies, item comments page for root."""
        anchor = f"#comment-anchor-{self.pk}"
        if self.parent_id:
            return (
                reverse(
                    "smart_blog:comment_thread",
                    kwargs={"slug": self.item.slug, "pk": self.parent_id},
                )
                + anchor
            )
        return self.item.get_comments_absolute_url() + anchor


class CommentLike(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="comment_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["comment", "user"], name="unique_comment_user_like")
        ]
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user or 'Vanished'} likes comment {self.comment_id}"
    
    


class Like(models.Model):
    """Лайк для самой публикации — один лайк от одного пользователя на одну публикацию."""
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["item", "user"], name="unique_item_user_like")
        ]
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user or 'Vanished'} likes {self.item}"
    
    
class ContentReport(models.Model):
    REASON_SPAM = "spam"
    REASON_ABUSE = "abuse"
    REASON_HARASSMENT = "harassment"
    REASON_COPYRIGHT = "copyright"
    REASON_OTHER = "other"

    REASON_CHOICES = [
        (REASON_SPAM, "Spam"),
        (REASON_ABUSE, "Abuse"),
        (REASON_HARASSMENT, "Harassment"),
        (REASON_COPYRIGHT, "Copyright"),
        (REASON_OTHER, "Other"),
    ]

    STATUS_OPEN = "open"
    STATUS_RESOLVED = "resolved"
    STATUS_IGNORED = "ignored"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Pending"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_IGNORED, "Ignored"),
    ]

    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, null=True, blank=True, related_name="reports")
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name="reports")
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    reasons = models.JSONField(default=list, blank=True)  # list of reason strings for multiple reasons
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    admin_hidden = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["reporter", "item"],
                condition=Q(item__isnull=False, deleted_at__isnull=True),
                name="unique_user_item_report",
            ),
            models.UniqueConstraint(
                fields=["reporter", "comment"],
                condition=Q(comment__isnull=False, deleted_at__isnull=True),
                name="unique_user_comment_report",
            ),
            models.CheckConstraint(
                check=(
                    Q(item__isnull=False, comment__isnull=True)
                    | Q(item__isnull=True, comment__isnull=False)
                ),
                name="report_target_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["item", "created_at"]),
            models.Index(fields=["comment", "created_at"]),
            models.Index(fields=["reporter", "created_at"]),
        ]

    def get_target(self):
        return self.item or self.comment

    def touch_updated(self):
        """Refresh updated_at to current time (triggers auto_now). Use when user changes report."""
        self.save(update_fields=["updated_at"])

    def is_item_report(self):
        return self.item_id is not None

    def is_comment_report(self):
        return self.comment_id is not None

    def get_reasons_display(self):
        """Return list of display labels for reasons (supports multiple)."""
        reasons = getattr(self, 'reasons', None)
        if not reasons or not isinstance(reasons, list):
            return [self.get_reason_display()] if self.reason else []
        labels = dict(self.REASON_CHOICES)
        return [labels.get(r, r) for r in reasons if r]

    def __str__(self):
        target = self.item or self.comment
        return f"Report({self.reason}) for {target}"



# просмотр публикации
class ItemView(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="views")
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="item_views"
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # user
            models.UniqueConstraint(
                fields=["item", "user"],
                condition=Q(user__isnull=False),
                name="unique_item_user_view"
            ),
            # guest
            models.UniqueConstraint(
                fields=["item", "session_key"],
                condition=Q(user__isnull=True, session_key__isnull=False),
                name="unique_item_session_view"
            ),
        ]
        indexes = [
            models.Index(fields=["item", "viewed_at"]),
        ]
        ordering = ("-viewed_at",)


class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookmarks")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="bookmarked_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "item"], name="unique_user_item_bookmark")
        ]
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user} bookmarked {self.item}"


class SearchHistory(models.Model):
    """История поисковых запросов (только BraiNews). Макс 25 на пользователя."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="search_history"
    )
    search_query = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    results_count = models.PositiveIntegerField(default=0)
    search_filters = models.JSONField(default=dict, blank=True)
    was_clicked = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]
        verbose_name = "Search history"
        verbose_name_plural = "Search history"

    def __str__(self):
        return f"{self.user.username}: {self.search_query[:50]}"


class PostRepost(models.Model):
    """История репостов публикаций. Событие = нажатие Share, отправка в соцсеть, копирование ссылки."""
    PLATFORM_TELEGRAM = 'telegram'
    PLATFORM_TWITTER = 'twitter'
    PLATFORM_FACEBOOK = 'facebook'
    PLATFORM_LINKEDIN = 'linkedin'
    PLATFORM_COPY_LINK = 'copy_link'
    PLATFORM_OTHER = 'other'
    PLATFORM_CHOICES = [
        (PLATFORM_TELEGRAM, 'Telegram'),
        (PLATFORM_TWITTER, 'Twitter'),
        (PLATFORM_FACEBOOK, 'Facebook'),
        (PLATFORM_LINKEDIN, 'LinkedIn'),
        (PLATFORM_COPY_LINK, 'Copy link'),
        (PLATFORM_OTHER, 'Other'),
    ]
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='reposts')
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reposts',
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, db_index=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['item', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
        ]
        verbose_name = 'Post repost'
        verbose_name_plural = 'Post reposts'

    def __str__(self):
        return f'{self.item_id} repost via {self.platform}'


class Notification(models.Model):
    TYPE_REPLY = "reply"
    TYPE_ITEM_LIKE = "item_like"
    TYPE_COMMENT_LIKE = "comment_like"
    TYPE_FROM_ADMIN = "from_admin"

    TYPE_CHOICES = [
        (TYPE_REPLY, "Reply"),
        (TYPE_ITEM_LIKE, "Liked item"),
        (TYPE_COMMENT_LIKE, "Liked comment"),
        (TYPE_FROM_ADMIN, "From admin"),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_notifications")
    notif_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    admin_theme = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional subject for from_admin notifications",
    )
    admin_body = models.TextField(
        blank=True,
        help_text="Message body for from_admin notifications",
    )
    parent_comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="reply_notifications", null=True, blank=True)
    reply_comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True)
    is_read = models.BooleanField(default=False)
    cleared_from_inbox = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Hidden from the recipient inbox but kept for deduplication when likes/replies repeat.",
    )
    hidden_from_admin = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Hidden from the admin notifications table only; does not change recipient inbox.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["recipient", "cleared_from_inbox", "-created_at"]),
        ]

    def __str__(self):
        if self.notif_type == self.TYPE_FROM_ADMIN:
            return f"Admin notification for {self.recipient}"
        return f"Notification for {self.recipient} on {self.item}"

    @property
    def admin_reason_label(self):
        if self.notif_type == self.TYPE_FROM_ADMIN:
            return "From admin"
        if self.notif_type == self.TYPE_REPLY:
            return "Comment reply"
        if self.notif_type == self.TYPE_COMMENT_LIKE:
            return "Comment like"
        return "Post like"

    @property
    def human_added(self):
        created_at = timezone.localtime(self.created_at)
        now_local = timezone.localtime(timezone.now())
        delta_days = (now_local.date() - created_at.date()).days
        if delta_days == 0:
            return f"Today at {created_at.strftime('%H:%M')}"
        elif delta_days == 1:
            return f"Yesterday {created_at.strftime('%H:%M')}"
        elif 2 <= delta_days <= 5:
            return f"{delta_days} days ago at {created_at.strftime('%H:%M')}"
        else:
            return f"{created_at.strftime("%d.%m.%Y")} at {created_at.strftime('%H:%M')}"

    def get_absolute_url(self):
        if self.notif_type == self.TYPE_FROM_ADMIN:
            return reverse("login_app:notifications", kwargs={"username": self.recipient.username})

        def _item_comment_url(path, focus_pk, anchor_pk):
            sep = '&' if '?' in path else '?'
            return f"{path}{sep}focus_comment={focus_pk}#comment-anchor-{anchor_pk}"

        if self.reply_comment_id:
            reply = self.reply_comment
            if reply.parent_id:
                # If reply is directly under root, it's visible on the comments page.
                if reply.parent and reply.parent.parent_id is None:
                    return _item_comment_url(
                        self.item.get_comments_absolute_url(), reply.pk, reply.pk
                    )
                # Otherwise go to thread page for its parent.
                thread_url = reverse(
                    "smart_blog:comment_thread",
                    kwargs={"slug": self.item.slug, "pk": reply.parent_id},
                )
                return _item_comment_url(thread_url, reply.pk, reply.pk)
            return _item_comment_url(self.item.get_comments_absolute_url(), reply.pk, reply.pk)
        if self.parent_comment_id:
            pc = self.parent_comment.pk
            return _item_comment_url(self.item.get_comments_absolute_url(), pc, pc)
        return self.item.get_absolute_url()


class ItemStatsHourly(models.Model):
    """Aggregated views/likes/comments per item per calendar hour (TIME_ZONE-aware bucket)."""

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="stats_hourly")
    hour_start = models.DateTimeField(db_index=True)
    views = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    comments = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["item", "hour_start"],
                name="unique_item_stats_hourly_item_hour",
            ),
        ]
        indexes = [
            models.Index(fields=["hour_start"]),
        ]
        ordering = ("-hour_start",)

    def __str__(self):
        return f"ItemStatsHourly(item={self.item_id}, hour_start={self.hour_start})"


class TrendingItem(models.Model):
    """Materialized trending scores for published items (velocity ranking)."""

    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name="trending")
    trend_score = models.FloatField(default=0)
    views_24h = models.PositiveIntegerField(default=0)
    likes_24h = models.PositiveIntegerField(default=0)
    comments_24h = models.PositiveIntegerField(default=0)
    bookmarks_24h = models.PositiveIntegerField(default=0)
    reposts_24h = models.PositiveIntegerField(default=0)
    growth_rate = models.FloatField(default=0)
    views_last_hour = models.PositiveIntegerField(default=0)
    likes_1h = models.PositiveIntegerField(default=0)
    comments_1h = models.PositiveIntegerField(default=0)
    bookmarks_1h = models.PositiveIntegerField(default=0)
    reposts_1h = models.PositiveIntegerField(default=0)
    views_prev_hour = models.PositiveIntegerField(default=0)
    likes_prev_1h = models.PositiveIntegerField(default=0)
    comments_prev_1h = models.PositiveIntegerField(default=0)
    bookmarks_prev_1h = models.PositiveIntegerField(default=0)
    reposts_prev_1h = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["trend_score"]),
            models.Index(fields=["growth_rate"]),
        ]

    def __str__(self):
        return f"TrendingItem(item={self.item_id}, score={self.trend_score:.4f})"


class ViewEvent(models.Model):
    """Non-unique page-view event for trending velocity measurement.

    Unlike ItemView (unique per user/session), this records every page visit
    so trending can measure real traffic velocity in time windows.
    """

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="view_events")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["item", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"ViewEvent(item={self.item_id}, {self.created_at})"