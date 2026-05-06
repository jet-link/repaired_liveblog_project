# Generated manually for Trending MVP

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('smart_blog', '0037_contentreport_admin_hidden'),
    ]

    operations = [
        migrations.CreateModel(
            name='ItemStatsHourly',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hour_start', models.DateTimeField(db_index=True)),
                ('views', models.PositiveIntegerField(default=0)),
                ('likes', models.PositiveIntegerField(default=0)),
                ('comments', models.PositiveIntegerField(default=0)),
                (
                    'item',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='stats_hourly',
                        to='smart_blog.item',
                    ),
                ),
            ],
            options={
                'ordering': ('-hour_start',),
            },
        ),
        migrations.CreateModel(
            name='TrendingItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trend_score', models.FloatField(default=0)),
                ('views_24h', models.PositiveIntegerField(default=0)),
                ('likes_24h', models.PositiveIntegerField(default=0)),
                ('comments_24h', models.PositiveIntegerField(default=0)),
                ('growth_rate', models.FloatField(default=0)),
                ('views_last_hour', models.PositiveIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'item',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='trending',
                        to='smart_blog.item',
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name='itemstatshourly',
            constraint=models.UniqueConstraint(
                fields=('item', 'hour_start'),
                name='unique_item_stats_hourly_item_hour',
            ),
        ),
        migrations.AddIndex(
            model_name='itemstatshourly',
            index=models.Index(fields=['hour_start'], name='smart_blog__hour_st_0a0b8c_idx'),
        ),
        migrations.AddIndex(
            model_name='trendingitem',
            index=models.Index(fields=['trend_score'], name='smart_blog__trend_score_idx'),
        ),
        migrations.AddIndex(
            model_name='trendingitem',
            index=models.Index(fields=['growth_rate'], name='smart_blog__growth_rate_idx'),
        ),
    ]
