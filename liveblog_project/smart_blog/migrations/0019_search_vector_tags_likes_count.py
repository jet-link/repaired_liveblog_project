# 1. Extend search_vector: title(A) + text(B) + tags(C), trigger on M2M changes
# 2. Add likes_count denormalized field + index
from django.db import migrations, connection, models


def pg_search_vector_tags(apps, schema_editor):
    if connection.vendor != 'postgresql':
        return
    schema_editor.execute("DROP TRIGGER IF EXISTS smart_blog_item_search_vector_update ON smart_blog_item;")
    schema_editor.execute("DROP FUNCTION IF EXISTS smart_blog_item_search_vector_trigger();")
    schema_editor.execute("""
        CREATE OR REPLACE FUNCTION smart_blog_item_search_vector_trigger()
        RETURNS TRIGGER AS $$
        DECLARE
            tag_text text;
        BEGIN
            SELECT coalesce(string_agg(t.tag_name, ' '), '') INTO tag_text
            FROM smart_blog_item_tags it
            JOIN smart_blog_tag t ON t.id = it.tag_id
            WHERE it.item_id = NEW.id;
            NEW.search_vector :=
                setweight(to_tsvector('simple', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(regexp_replace(NEW.text, '<[^>]+>', ' ', 'g'), '')), 'B') ||
                setweight(to_tsvector('simple', coalesce(tag_text, '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    schema_editor.execute("""
        CREATE TRIGGER smart_blog_item_search_vector_update
        BEFORE INSERT OR UPDATE OF title, text
        ON smart_blog_item
        FOR EACH ROW
        EXECUTE PROCEDURE smart_blog_item_search_vector_trigger();
    """)
    # Trigger on M2M table for tag changes
    schema_editor.execute("""
        CREATE OR REPLACE FUNCTION smart_blog_item_tags_search_vector_sync()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE smart_blog_item SET search_vector = (
                setweight(to_tsvector('simple', coalesce(title, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(regexp_replace(text, '<[^>]+>', ' ', 'g'), '')), 'B') ||
                setweight(to_tsvector('simple', coalesce(
                    (SELECT string_agg(t.tag_name, ' ') FROM smart_blog_item_tags it
                     JOIN smart_blog_tag t ON t.id = it.tag_id
                     WHERE it.item_id = smart_blog_item.id),
                    ''
                )), 'C')
            ) WHERE id = COALESCE(NEW.item_id, OLD.item_id);
            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
    """)
    schema_editor.execute("""
        DROP TRIGGER IF EXISTS smart_blog_item_tags_search_vector_trigger ON smart_blog_item_tags;
        CREATE TRIGGER smart_blog_item_tags_search_vector_trigger
        AFTER INSERT OR DELETE ON smart_blog_item_tags
        FOR EACH ROW
        EXECUTE PROCEDURE smart_blog_item_tags_search_vector_sync();
    """)
    # Backfill with tags
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
        );
    """)


def backfill_likes_count(apps, schema_editor):
    if connection.vendor == 'postgresql':
        schema_editor.execute("""
            UPDATE smart_blog_item i SET likes_count = (
                SELECT COUNT(*) FROM smart_blog_like l WHERE l.item_id = i.id
            );
        """)
    # SQLite: same
    elif connection.vendor == 'sqlite':
        schema_editor.execute("""
            UPDATE smart_blog_item SET likes_count = (
                SELECT COUNT(*) FROM smart_blog_like WHERE smart_blog_like.item_id = smart_blog_item.id
            );
        """)


def pg_search_vector_tags_reverse(apps, schema_editor):
    if connection.vendor != 'postgresql':
        return
    schema_editor.execute("DROP TRIGGER IF EXISTS smart_blog_item_tags_search_vector_trigger ON smart_blog_item_tags;")
    schema_editor.execute("DROP FUNCTION IF EXISTS smart_blog_item_tags_search_vector_sync();")
    schema_editor.execute("DROP TRIGGER IF EXISTS smart_blog_item_search_vector_update ON smart_blog_item;")
    schema_editor.execute("DROP FUNCTION IF EXISTS smart_blog_item_search_vector_trigger();")
    schema_editor.execute("""
        CREATE OR REPLACE FUNCTION smart_blog_item_search_vector_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('simple', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(regexp_replace(NEW.text, '<[^>]+>', ' ', 'g'), '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    schema_editor.execute("""
        CREATE TRIGGER smart_blog_item_search_vector_update
        BEFORE INSERT OR UPDATE OF title, text
        ON smart_blog_item
        FOR EACH ROW
        EXECUTE PROCEDURE smart_blog_item_search_vector_trigger();
    """)


class Migration(migrations.Migration):
    atomic = False  # Avoid "pending trigger events" when creating index
    dependencies = [('smart_blog', '0018_alter_notification_id_alter_notification_notif_type')]

    operations = [
        migrations.AddField(
            model_name='item',
            name='likes_count',
            field=models.PositiveIntegerField(default=0, db_index=True),
        ),
        migrations.RunPython(backfill_likes_count, migrations.RunPython.noop),
        migrations.RunPython(pg_search_vector_tags, pg_search_vector_tags_reverse),
    ]
