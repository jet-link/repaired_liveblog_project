# Backfill search_vector for Item rows where it is NULL (fixes search returning 0 for elon, yolo, etc.)
from django.db import migrations, connection


def backfill_null_search_vector(apps, schema_editor):
    if connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        UPDATE smart_blog_item i SET search_vector = (
            setweight(to_tsvector('simple', coalesce(i.title, '')), 'A') ||
            setweight(to_tsvector('simple', coalesce(regexp_replace(i.text, '<[^>]+>', ' ', 'g'), '')), 'B') ||
            setweight(to_tsvector('simple', coalesce(
                (SELECT string_agg(t.tag_name, ' ') FROM smart_blog_item_tags it
                 JOIN smart_blog_tag t ON t.id = it.tag_id
                 WHERE it.item_id = i.id),
                ''
            )), 'C')
        ) WHERE i.search_vector IS NULL
    """)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('smart_blog', '0035_alter_contentreport_status'),
    ]

    operations = [
        migrations.RunPython(backfill_null_search_vector, noop),
    ]
