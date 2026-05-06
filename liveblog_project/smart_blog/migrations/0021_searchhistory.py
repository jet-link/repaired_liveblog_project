# Generated manually for SearchHistory model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('smart_blog', '0020_merge_20260216_2105'),
    ]

    operations = [
        migrations.CreateModel(
            name='SearchHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('search_query', models.CharField(max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('results_count', models.PositiveIntegerField(default=0)),
                ('search_filters', models.JSONField(blank=True, default=dict)),
                ('was_clicked', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='search_history', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Search history',
                'verbose_name_plural': 'Search history',
                'ordering': ('-created_at',),
            },
        ),
        migrations.AddIndex(
            model_name='searchhistory',
            index=models.Index(fields=['user', '-created_at'], name='searchhist_user_created_idx'),
        ),
    ]
