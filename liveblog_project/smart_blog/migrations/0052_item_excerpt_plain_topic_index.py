# Generated manually — list performance: persisted excerpt + topic listing index

from django.db import migrations, models
from django.utils.html import strip_tags


def _plain_excerpt(html_text, length=600):
    if not html_text:
        return ""
    plain = strip_tags(html_text)
    plain = plain.replace("\xa0", " ").replace("&nbsp;", " ")
    plain = plain.strip()
    if len(plain) <= length:
        return plain
    cut = plain[:length].rsplit(" ", 1)[0]
    return cut + " …"


def backfill_excerpt_plain(apps, schema_editor):
    Item = apps.get_model("smart_blog", "Item")
    for row in Item.objects.iterator(chunk_size=200):
        ex = _plain_excerpt(row.text or "")
        if (row.excerpt_plain or "") != ex:
            Item.objects.filter(pk=row.pk).update(excerpt_plain=ex)


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0051_itemimage_gallery_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="excerpt_plain",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Plain excerpt for list cards (synced from text on save).",
                max_length=620,
            ),
        ),
        migrations.AddIndex(
            model_name="item",
            index=models.Index(
                fields=["is_published", "category", "-published_date"],
                name="smart_blog__topic_li_idx",
            ),
        ),
        migrations.RunPython(backfill_excerpt_plain, migrations.RunPython.noop),
    ]
