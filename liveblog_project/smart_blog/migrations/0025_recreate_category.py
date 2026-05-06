# Recreate Category from scratch — drop existing table and create with new schema

import django.db.models.deletion
from django.db import migrations, models


def _drop_legacy_category(apps, schema_editor):
    """Только на PostgreSQL: убрать прежнюю Category-таблицу и orphaned FK-колонку.
    SQLite (локальный dev) проходит migrate с нуля — на нём этого делать не нужно
    и сам синтаксис (CASCADE / DROP COLUMN IF EXISTS) не поддерживается.
    """
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "DROP TABLE IF EXISTS smart_blog_category CASCADE; "
        "ALTER TABLE smart_blog_item DROP COLUMN IF EXISTS category_id;"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('smart_blog', '0024_like_commentlike_user_set_null'),
    ]

    operations = [
        # 1. Drop Category table + orphaned category_id (PostgreSQL keeps column after DROP TABLE CASCADE)
        migrations.RunPython(_drop_legacy_category, migrations.RunPython.noop),
        # 2. Create Category with new schema
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(max_length=120, unique=True)),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
                'ordering': ['name'],
            },
        ),
        # 4. Add category FK to Item
        migrations.AddField(
            model_name='item',
            name='category',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='items',
                to='smart_blog.category',
            ),
        ),
    ]
