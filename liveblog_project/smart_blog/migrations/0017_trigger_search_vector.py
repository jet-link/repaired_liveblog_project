# Replace GENERATED column with trigger — Django ORM cannot INSERT into generated columns
from django.db import migrations, connection


def trigger_forward(apps, schema_editor):
    if connection.vendor != 'postgresql':
        return
    # 1. Drop index and generated column
    schema_editor.execute("DROP INDEX IF EXISTS smart_blog_item_search_vector_gin;")
    schema_editor.execute("ALTER TABLE smart_blog_item DROP COLUMN IF EXISTS search_vector;")
    # 2. Add regular nullable tsvector column (Django can omit it in INSERT)
    schema_editor.execute("""
        ALTER TABLE smart_blog_item
        ADD COLUMN search_vector tsvector NULL;
    """)
    # 3. Create trigger function
    schema_editor.execute("""
        CREATE OR REPLACE FUNCTION smart_blog_item_search_vector_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('simple', coalesce(NEW.title, '')), 'A') ||
                setweight(
                    to_tsvector('simple', coalesce(
                        regexp_replace(NEW.text, '<[^>]+>', ' ', 'g'),
                        ''
                    )),
                    'B'
                );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    # 4. Create trigger
    schema_editor.execute("""
        DROP TRIGGER IF EXISTS smart_blog_item_search_vector_update ON smart_blog_item;
        CREATE TRIGGER smart_blog_item_search_vector_update
        BEFORE INSERT OR UPDATE OF title, text
        ON smart_blog_item
        FOR EACH ROW
        EXECUTE PROCEDURE smart_blog_item_search_vector_trigger();
    """)
    # 5. Backfill existing rows
    schema_editor.execute("""
        UPDATE smart_blog_item SET
            search_vector = setweight(to_tsvector('simple', coalesce(title, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(regexp_replace(text, '<[^>]+>', ' ', 'g'), '')), 'B')
        WHERE search_vector IS NULL;
    """)
    # 6. Create GIN index
    schema_editor.execute("""
        CREATE INDEX IF NOT EXISTS smart_blog_item_search_vector_gin
        ON smart_blog_item USING GIN (search_vector);
    """)


def trigger_reverse(apps, schema_editor):
    if connection.vendor != 'postgresql':
        return
    schema_editor.execute("DROP TRIGGER IF EXISTS smart_blog_item_search_vector_update ON smart_blog_item;")
    schema_editor.execute("DROP FUNCTION IF EXISTS smart_blog_item_search_vector_trigger();")
    schema_editor.execute("DROP INDEX IF EXISTS smart_blog_item_search_vector_gin;")
    schema_editor.execute("ALTER TABLE smart_blog_item DROP COLUMN IF EXISTS search_vector;")
    # Recreate generated column (for full reverse)
    schema_editor.execute("""
        ALTER TABLE smart_blog_item
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('simple', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('simple', coalesce(regexp_replace(text, '<[^>]+>', ' ', 'g'), '')), 'B')
        ) STORED;
    """)
    schema_editor.execute("""
        CREATE INDEX IF NOT EXISTS smart_blog_item_search_vector_gin
        ON smart_blog_item USING GIN (search_vector);
    """)


class Migration(migrations.Migration):
    dependencies = [('smart_blog', '0016_item_search_vector_fts')]
    operations = [migrations.RunPython(trigger_forward, trigger_reverse)]
