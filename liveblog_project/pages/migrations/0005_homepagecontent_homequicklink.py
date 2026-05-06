# Generated manually for homepage admin-driven content.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_home_defaults(apps, schema_editor):
    HomePageContent = apps.get_model("pages", "HomePageContent")
    HomeQuickLink = apps.get_model("pages", "HomeQuickLink")
    if not HomePageContent.objects.filter(pk=1).exists():
        HomePageContent.objects.create(
            pk=1,
            browser_title="brainstorm.news",
            meta_description="News, stories, and community discussion on brainstorm.news.",
            hero_h1="brainstorm.news",
            hero_lede="Read BraiNews, explore topics, and follow what’s trending.",
            cta_primary_label="Open BraiNews",
            cta_primary_url="/blog/brainews/",
            cta_secondary_label="In trend",
            cta_secondary_url="/blog/brainews/trending/",
            trust_line="",
            trust_link_url="",
            show_quick_links=True,
            show_decorative_astronauts=False,
            content_strip_mode="popular",
            content_strip_limit=6,
            popular_min_likes=6,
            show_editor_picks=False,
            editor_pick_order_after_strip=False,
            cache_bump=0,
        )
    seed_links = [
        ("BraiNews", "/blog/brainews/", "fa-newspaper-o", 0),
        ("In trend", "/blog/brainews/trending/", "fa-fire", 1),
        ("Topics", "/blog/topics/", "fa-folder-o", 2),
        ("Search", "/search/", "fa-search", 3),
        ("For you", "/blog/for-you/", "fa-user", 4),
    ]
    for label, url, icon, order in seed_links:
        if not HomeQuickLink.objects.filter(url=url).exists():
            HomeQuickLink.objects.create(
                label=label, url=url, icon_class=icon, order=order, is_active=True
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0004_alter_contactspagecontent_email_address"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("smart_blog", "0044_category_pending_restore_item_ids"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomePageContent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("browser_title", models.CharField(default="brainstorm.news", max_length=120)),
                (
                    "meta_description",
                    models.CharField(
                        blank=True,
                        help_text="Meta description for search engines (plain text).",
                        max_length=320,
                    ),
                ),
                ("hero_h1", models.CharField(default="brainstorm.news", max_length=200)),
                ("hero_lede", models.TextField(blank=True)),
                ("cta_primary_label", models.CharField(blank=True, max_length=120)),
                ("cta_primary_url", models.CharField(blank=True, max_length=500)),
                ("cta_secondary_label", models.CharField(blank=True, max_length=120)),
                ("cta_secondary_url", models.CharField(blank=True, max_length=500)),
                ("trust_line", models.CharField(blank=True, max_length=255)),
                ("trust_link_url", models.CharField(blank=True, max_length=500)),
                ("show_quick_links", models.BooleanField(default=True)),
                (
                    "show_decorative_astronauts",
                    models.BooleanField(default=False, help_text="Show the optional astronauts decorative block."),
                ),
                (
                    "content_strip_mode",
                    models.CharField(
                        choices=[
                            ("popular", "Popular"),
                            ("trending", "In trend"),
                            ("none", "No strip (hero + quick links only)"),
                        ],
                        default="popular",
                        max_length=16,
                    ),
                ),
                ("content_strip_limit", models.PositiveSmallIntegerField(default=6)),
                ("popular_min_likes", models.PositiveSmallIntegerField(default=6)),
                ("show_editor_picks", models.BooleanField(default=False)),
                (
                    "editor_pick_order_after_strip",
                    models.BooleanField(
                        default=False,
                        help_text="If checked, editor picks appear below the main strip; otherwise above.",
                    ),
                ),
                (
                    "cache_bump",
                    models.PositiveIntegerField(
                        default=0,
                        editable=False,
                        help_text="Bumped on each content save to invalidate template cache.",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "editor_pick_1",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="smart_blog.item",
                    ),
                ),
                (
                    "editor_pick_2",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="smart_blog.item",
                    ),
                ),
                (
                    "editor_pick_3",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="smart_blog.item",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="home_page_edits",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Home page content",
                "verbose_name_plural": "Home page content",
            },
        ),
        migrations.CreateModel(
            name="HomeQuickLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=120)),
                (
                    "url",
                    models.CharField(
                        help_text="Path (e.g. /search/) or full https URL.",
                        max_length=500,
                    ),
                ),
                (
                    "icon_class",
                    models.CharField(
                        blank=True,
                        help_text="Font Awesome 4 class, e.g. fa-search",
                        max_length=80,
                    ),
                ),
                ("order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Home quick link",
                "verbose_name_plural": "Home quick links",
                "ordering": ["order", "pk"],
            },
        ),
        migrations.RunPython(seed_home_defaults, noop_reverse),
    ]
