# Generated migration: add views_count and bookmarks_count to Item

from django.db import migrations, models, connection


def backfill_views_bookmarks_count(apps, schema_editor):
    """Backfill views_count and bookmarks_count from ItemView and Bookmark."""
    if connection.vendor == 'postgresql':
        schema_editor.execute("""
            UPDATE smart_blog_item i SET views_count = (
                SELECT COUNT(*) FROM smart_blog_itemview v
                WHERE v.item_id = i.id AND v.user_id IS NOT NULL
            );
        """)
        schema_editor.execute("""
            UPDATE smart_blog_item i SET bookmarks_count = (
                SELECT COUNT(*) FROM smart_blog_bookmark b WHERE b.item_id = i.id
            );
        """)
    elif connection.vendor == 'sqlite':
        schema_editor.execute("""
            UPDATE smart_blog_item SET views_count = (
                SELECT COUNT(*) FROM smart_blog_itemview
                WHERE smart_blog_itemview.item_id = smart_blog_item.id
                AND smart_blog_itemview.user_id IS NOT NULL
            );
        """)
        schema_editor.execute("""
            UPDATE smart_blog_item SET bookmarks_count = (
                SELECT COUNT(*) FROM smart_blog_bookmark
                WHERE smart_blog_bookmark.item_id = smart_blog_item.id
            );
        """)


class Migration(migrations.Migration):
    dependencies = [
        ('smart_blog', '0026_alter_category_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='views_count',
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AddField(
            model_name='item',
            name='bookmarks_count',
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.RunPython(backfill_views_bookmarks_count, migrations.RunPython.noop),
    ]
