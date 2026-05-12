import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mindset', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MindsetFollow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'follower',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='mindset_following',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'followee',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='mindset_followers',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.AddIndex(
            model_name='mindsetfollow',
            index=models.Index(fields=['follower', '-created_at'], name='mindset_mfo_followe_4af80e_idx'),
        ),
        migrations.AddIndex(
            model_name='mindsetfollow',
            index=models.Index(fields=['followee', '-created_at'], name='mindset_mfo_followe_ed3c41_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='mindsetfollow',
            unique_together={('follower', 'followee')},
        ),
    ]
