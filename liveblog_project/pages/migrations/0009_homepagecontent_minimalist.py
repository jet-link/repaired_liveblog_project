"""Minimalist home page: drop unused hero/strip/decorative fields, add Mindset Live toggle."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0008_alter_homepagecontent_show_for_you_section'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='homepagecontent',
            name='cta_secondary_label',
        ),
        migrations.RemoveField(
            model_name='homepagecontent',
            name='cta_secondary_url',
        ),
        migrations.RemoveField(
            model_name='homepagecontent',
            name='trust_line',
        ),
        migrations.RemoveField(
            model_name='homepagecontent',
            name='trust_link_url',
        ),
        migrations.RemoveField(
            model_name='homepagecontent',
            name='show_decorative_astronauts',
        ),
        migrations.RemoveField(
            model_name='homepagecontent',
            name='content_strip_mode',
        ),
        migrations.RemoveField(
            model_name='homepagecontent',
            name='content_strip_limit',
        ),
        migrations.RemoveField(
            model_name='homepagecontent',
            name='popular_min_likes',
        ),
        migrations.AddField(
            model_name='homepagecontent',
            name='show_mindset_live',
            field=models.BooleanField(
                default=True,
                help_text='Show the "Mindset Live" preview section (3 themes).',
            ),
        ),
    ]
