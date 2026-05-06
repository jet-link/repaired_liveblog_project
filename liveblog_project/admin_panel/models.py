"""Admin panel models."""
from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model

User = get_user_model()


class DeletedUserLog(models.Model):
    """Queue of users marked for deletion from the Users list; account row kept until purged here."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='deleted_queue_entry',
        null=True,
        blank=True,
    )
    username = models.CharField(max_length=150)
    deleted_at = models.DateTimeField(auto_now_add=True)
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_users_log',
    )

    class Meta:
        ordering = ('-deleted_at',)
        verbose_name = 'Deleted user log'
        verbose_name_plural = 'Deleted user logs'

    def __str__(self):
        return f'{self.username} (deleted at {self.deleted_at})'


class ForbiddenWord(models.Model):
    """Banned word for content moderation."""
    REASON_OBSCENITY = 'obscenity'
    REASON_SPAM = 'spam'
    REASON_HARASSMENT = 'harassment'
    REASON_ABUSE = 'abuse'
    REASON_OTHER = 'other'

    REASON_CHOICES = [
        (REASON_OBSCENITY, 'Obscenity'),
        (REASON_SPAM, 'Spam'),
        (REASON_HARASSMENT, 'Harassment'),
        (REASON_ABUSE, 'Abuse'),
        (REASON_OTHER, 'Other'),
    ]

    word = models.CharField(max_length=255, db_index=True)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES, default=REASON_OBSCENITY)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('word',)
        verbose_name = 'Forbidden word'
        verbose_name_plural = 'Forbidden words'

    def __str__(self):
        return f'{self.word} ({self.reason})'


class ForbiddenPattern(models.Model):
    """Regex pattern for content moderation (obfuscation, spam)."""
    REASON_OBSCENITY = 'obscenity'
    REASON_SPAM = 'spam'
    REASON_HARASSMENT = 'harassment'
    REASON_ABUSE = 'abuse'
    REASON_OTHER = 'other'

    REASON_CHOICES = [
        (REASON_OBSCENITY, 'Obscenity'),
        (REASON_SPAM, 'Spam'),
        (REASON_HARASSMENT, 'Harassment'),
        (REASON_ABUSE, 'Abuse'),
        (REASON_OTHER, 'Other'),
    ]

    pattern = models.CharField(max_length=500)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES, default=REASON_SPAM)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('reason',)
        verbose_name = 'Forbidden pattern'
        verbose_name_plural = 'Forbidden patterns'

    def __str__(self):
        return f'{self.pattern[:50]}... ({self.reason})'


class AnalysisRun(models.Model):
    """Tracks content analysis runs: progress, logs."""
    SCHEDULE_NOW = 'now'
    SCHEDULE_HOURLY = 'hourly'
    SCHEDULE_DAILY = 'daily'

    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'

    schedule = models.CharField(max_length=20, default=SCHEDULE_NOW)
    status = models.CharField(max_length=20, default=STATUS_RUNNING)
    progress = models.PositiveSmallIntegerField(default=0)
    log_lines = models.JSONField(default=list)
    started_at = models.DateTimeField(auto_now_add=True)
    started_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analysis_runs',
    )
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-started_at',)
        verbose_name = 'Analysis run'
        verbose_name_plural = 'Analysis runs'

    def __str__(self):
        return f'AnalysisRun #{self.pk} ({self.status})'


class ContentViolation(models.Model):
    """Detected content violation (post or comment)."""
    TYPE_POST = 'post'
    TYPE_COMMENT = 'comment'

    STATUS_PENDING = 'pending'
    STATUS_CHECKED = 'checked'
    STATUS_IGNORED = 'ignored'
    # "Cleared" = admin visually hid the row from the default Violations list. Persisted in DB
    # so it survives page reloads. The record is NOT deleted; viewable under ?status=cleared.
    STATUS_CLEARED = 'cleared'

    REASON_OBSCENITY = 'obscenity'
    REASON_SPAM = 'spam'
    REASON_HARASSMENT = 'harassment'
    REASON_ABUSE = 'abuse'
    REASON_OTHER = 'other'

    REASON_CHOICES = [
        (REASON_OBSCENITY, 'Obscenity'),
        (REASON_SPAM, 'Spam'),
        (REASON_HARASSMENT, 'Harassment'),
        (REASON_ABUSE, 'Abuse'),
        (REASON_OTHER, 'Other'),
    ]

    content_type = models.CharField(max_length=10)
    item = models.ForeignKey(
        'smart_blog.Item',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='content_violations',
    )
    comment = models.ForeignKey(
        'smart_blog.Comment',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='content_violations',
    )
    status = models.CharField(max_length=20, default=STATUS_PENDING)
    reason = models.CharField(max_length=30)
    severity = models.CharField(max_length=20, default='medium')
    confidence = models.FloatField(default=1.0)
    detected_word = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    # Filled when post/comment is deleted from Violations UI: preserves author + preview in Bucket
    snapshot_author = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='violation_snapshots',
    )
    target_preview = models.CharField(max_length=500, blank=True, default='')
    analysis_run = models.ForeignKey(
        AnalysisRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='violations',
    )

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Content violation'
        verbose_name_plural = 'Content violations'
        constraints = [
            models.UniqueConstraint(
                fields=['item'],
                condition=Q(item__isnull=False, deleted_at__isnull=True),
                name='uq_violation_item',
            ),
            models.UniqueConstraint(
                fields=['comment'],
                condition=Q(comment__isnull=False, deleted_at__isnull=True),
                name='uq_violation_comment',
            ),
        ]

    REASON_DEFAULT_RATING = {
        'abuse': 0.92,
        'harassment': 0.88,
        'obscenity': 0.87,
        'spam': 0.75,
        'other': 0.80,
    }

    REASON_TO_SEVERITY = {
        'spam': 'low',
        'obscenity': 'medium',
        'other': 'medium',
        'abuse': 'high',
        'harassment': 'high',
    }

    @classmethod
    def get_severity_from_reason(cls, reason):
        return cls.REASON_TO_SEVERITY.get(reason, 'medium')

    @classmethod
    def get_confidence_from_detected(cls, detected_word, reason):
        """Extract confidence from AI:...=0.85 format, else use default for reason."""
        word = (detected_word or '').strip()
        if word.startswith('AI:'):
            parts = word[3:].split('=')
            if len(parts) >= 2:
                try:
                    return max(0.0, min(1.0, float(parts[1])))
                except (ValueError, TypeError):
                    pass
        return cls.REASON_DEFAULT_RATING.get(reason, 0.80)

    def get_rating_display(self):
        """For Rating column: always show numeric score (0.00-1.00) for any violation."""
        word = (self.detected_word or '').strip()
        if word.startswith('AI:'):
            parts = word[3:].split('=')
            if len(parts) >= 2:
                try:
                    score = float(parts[1])
                    return f'{max(0, min(1, score)):.2f}'
                except (ValueError, TypeError):
                    pass
        return f'{self.REASON_DEFAULT_RATING.get(self.reason, 0.80):.2f}'

    def __str__(self):
        target = self.item or self.comment
        return f'Violation({self.reason}) for {target}'
