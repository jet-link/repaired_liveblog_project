# Generated manually for homepage layout flags and hero featured item.

import django.db.models.deletion
from django.db import migrations, models


def seed_home_footer_defaults(apps, schema_editor):
    HomePageContent = apps.get_model("pages", "HomePageContent")
    row = HomePageContent.objects.filter(pk=1).first()
    if not row:
        return
    if (getattr(row, "cta_footer_title", "") or "").strip():
        return
    HomePageContent.objects.filter(pk=1).update(
        cta_footer_title="Have something to say? Share your ideas with the community.",
        cta_footer_label="Create Post",
        cta_footer_url="/item/create/",
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0006_alter_contactspagecontent_email_address"),
        ("smart_blog", "0056_item_excerpt_plain_850"),
    ]

    operations = [
        migrations.AddField(
            model_name="homepagecontent",
            name="hero_featured_item",
            field=models.ForeignKey(
                blank=True,
                help_text="Large card on the right side of the hero. If empty, the first In Trend or latest post is used.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="smart_blog.item",
            ),
        ),
        migrations.AddField(
            model_name="homepagecontent",
            name="show_in_trend",
            field=models.BooleanField(
                default=True,
                help_text='Show the "In Trend" section (trending posts).',
            ),
        ),
        migrations.AddField(
            model_name="homepagecontent",
            name="show_for_you_section",
            field=models.BooleanField(
                default=True,
                help_text='Show the "For You" block. Guests see a sign-in prompt; signed-in users see recommendations.',
            ),
        ),
        migrations.AddField(
            model_name="homepagecontent",
            name="show_explore_topics",
            field=models.BooleanField(
                default=True,
                help_text='Show "Explore Topics" (top categories by post count).',
            ),
        ),
        migrations.AddField(
            model_name="homepagecontent",
            name="show_latest_brainews",
            field=models.BooleanField(
                default=True,
                help_text='Show latest BraiNews posts and "View all" link.',
            ),
        ),
        migrations.AddField(
            model_name="homepagecontent",
            name="show_bottom_cta",
            field=models.BooleanField(
                default=True,
                help_text="Show optional bottom call-to-action banner.",
            ),
        ),
        migrations.AddField(
            model_name="homepagecontent",
            name="cta_footer_title",
            field=models.CharField(
                blank=True,
                help_text="Bottom CTA heading (e.g. Have something to say?).",
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name="homepagecontent",
            name="cta_footer_label",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="homepagecontent",
            name="cta_footer_url",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.RunPython(seed_home_footer_defaults, noop_reverse),
    ]
