import uuid

from django.db import models
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save


DEFAULT_AVATAR = 'img/no_image.svg'


def avatar_upload_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'jpg'
    return f'profile_avatars/user_{instance.user_id}/{uuid.uuid4().hex[:12]}.{ext}'


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    avatar_url = models.URLField(
        blank=True,
        null=True,
        help_text="Optional URL to avatar image"
    )

    avatar_file = models.ImageField(
        upload_to=avatar_upload_path,
        blank=True,
        null=True
    )

    avatar_pos_x = models.FloatField(default=0.0)
    avatar_pos_y = models.FloatField(default=0.0)

    # Trust Score (0-10)
    trust_score = models.FloatField(default=10.0, db_index=True)
    last_violation_at = models.DateTimeField(null=True, blank=True)
    can_post = models.BooleanField(default=True)
    shadow_banned = models.BooleanField(default=False)
    trust_banned = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Account auto-deactivated because trust score fell below site threshold.',
    )

    public_username = models.BooleanField(default=True)
    public_first_name = models.BooleanField(default=True)
    public_last_name = models.BooleanField(default=True)
    public_email = models.BooleanField(default=True)

    def __str__(self):
        return f'Profile: {self.user.username}'

    def get_avatar(self):
        if self.avatar_file:
            return self.avatar_file.url
        if self.avatar_url:
            return self.avatar_url
        return DEFAULT_AVATAR

    def set_avatar_file(self, new_file):
        if not new_file:
            return
        self.avatar_file = new_file


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        try:
            instance.profile  # noqa: B018 -- just access to check existence
        except Profile.DoesNotExist:
            Profile.objects.create(user=instance)
