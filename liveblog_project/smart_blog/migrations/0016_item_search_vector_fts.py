# PostgreSQL Full-Text Search: stored tsvector + GIN index
# Replaces on-the-fly SearchVector with precomputed column for O(1) lookup
from django.db import migrations, connection
from django.contrib.postgres.search import SearchVectorField


def add_search_vector_column(apps, schema_editor):
    if connection.vendor == 'postgresql':
        schema_editor.execute("DROP INDEX IF EXISTS smart_blog_item_fts_idx;")
        schema_editor.execute("""
        ALTER TABLE smart_blog_item
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('simple', coalesce(title, '')), 'A') ||
            setweight(
                to_tsvector('simple', coalesce(
                    regexp_replace(text, '<[^>]+>', ' ', 'g'),
                    ''
                )),
                'B'
            )
        ) STORED;
        """)
        schema_editor.execute("""
            CREATE INDEX IF NOT EXISTS smart_blog_item_search_vector_gin
            ON smart_blog_item USING GIN (search_vector);
        """)
    else:
        # SQLite etc: stub column so ORM doesn't fail (search uses icontains)
        schema_editor.execute("ALTER TABLE smart_blog_item ADD COLUMN search_vector TEXT NULL;")


def reverse_add_search_vector(apps, schema_editor):
    if connection.vendor == 'postgresql':
        schema_editor.execute("DROP INDEX IF EXISTS smart_blog_item_search_vector_gin;")
        schema_editor.execute("ALTER TABLE smart_blog_item DROP COLUMN IF EXISTS search_vector;")
    else:
        schema_editor.execute("ALTER TABLE smart_blog_item DROP COLUMN search_vector;")


class Migration(migrations.Migration):

    dependencies = [
        ('smart_blog', '0015_add_fts_index'),
    ]

    operations = [
        migrations.RunPython(add_search_vector_column, reverse_add_search_vector),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='item',
                    name='search_vector',
                    field=SearchVectorField(editable=False, null=True),
                ),
            ],
            database_operations=[],
        ),
    ]
