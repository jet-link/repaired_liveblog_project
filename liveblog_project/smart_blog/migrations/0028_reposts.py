# Reposts: reposts_count on Item, PostRepost model

from django.conf import settings
from django.db import migrations, models


def backfill_reposts_count(apps, schema_editor):
    """Backfill reposts_count from PostRepost (no-op for initial migration)."""
    Item = apps.get_model('smart_blog', 'Item')
    PostRepost = apps.get_model('smart_blog', 'PostRepost')
    from django.db.models import Count
    for item in Item.objects.annotate(c=Count('reposts')).filter(c__gt=0):
        item.reposts_count = item.c
        item.save(update_fields=['reposts_count'])


class Migration(migrations.Migration):

    dependencies = [
        ('smart_blog', '0027_add_views_bookmarks_count'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='reposts_count',
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.CreateModel(
            name='PostRepost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField(blank=True, db_index=True, null=True)),
                ('platform', models.CharField(
                    choices=[
                        ('telegram', 'Telegram'),
                        ('twitter', 'Twitter'),
                        ('facebook', 'Facebook'),
                        ('linkedin', 'LinkedIn'),
                        ('copy_link', 'Copy link'),
                        ('other', 'Other'),
                    ],
                    db_index=True,
                    max_length=20,
                )),
                ('user_agent', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('item', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='reposts', to='smart_blog.item')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='reposts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created_at',),
                'verbose_name': 'Post repost',
                'verbose_name_plural': 'Post reposts',
            },
        ),
        migrations.AddIndex(
            model_name='postrepost',
            index=models.Index(fields=['item', 'created_at'], name='smart_blog__item_id_2c8ea4_idx'),
        ),
        migrations.AddIndex(
            model_name='postrepost',
            index=models.Index(fields=['ip_address', 'created_at'], name='smart_blog__ip_addr_da32f1_idx'),
        ),
        migrations.RunPython(backfill_reposts_count, migrations.RunPython.noop),
    ]
