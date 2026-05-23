"""Add ThemeImage (up to 3 per theme) and ReplyImage (0 or 1 per reply).

Both store three pre-rendered WebP variants (``image_thumbnail`` ~300w,
``image_medium`` ~800w, ``image`` ~large) so feed pages can ship the
smallest variant that fits the slot via ``srcset`` and stay light.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mindset', '0003_rename_mindset_mfo_followe_4af80e_idx_mindset_min_followe_854851_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ThemeImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='mindset/themes/%Y/%m/%d/')),
                ('image_thumbnail', models.ImageField(blank=True, null=True, upload_to='mindset/themes/')),
                ('image_medium', models.ImageField(blank=True, null=True, upload_to='mindset/themes/')),
                ('width', models.PositiveIntegerField(blank=True, null=True)),
                ('height', models.PositiveIntegerField(blank=True, null=True)),
                ('sort_order', models.PositiveSmallIntegerField(db_index=True, default=0)),
                (
                    'orientation_kind',
                    models.CharField(
                        choices=[
                            ('landscape', 'Landscape'),
                            ('portrait', 'Portrait'),
                            ('wide', 'Ultra-wide'),
                            ('square', 'Square'),
                        ],
                        default='landscape',
                        max_length=16,
                    ),
                ),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                (
                    'theme',
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name='images',
                        to='mindset.theme',
                    ),
                ),
            ],
            options={
                'ordering': ('sort_order', 'pk'),
            },
        ),
        migrations.CreateModel(
            name='ReplyImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='mindset/replies/%Y/%m/%d/')),
                ('image_thumbnail', models.ImageField(blank=True, null=True, upload_to='mindset/replies/')),
                ('image_medium', models.ImageField(blank=True, null=True, upload_to='mindset/replies/')),
                ('width', models.PositiveIntegerField(blank=True, null=True)),
                ('height', models.PositiveIntegerField(blank=True, null=True)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                (
                    'reply',
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        related_name='image',
                        to='mindset.reply',
                    ),
                ),
            ],
        ),
    ]
