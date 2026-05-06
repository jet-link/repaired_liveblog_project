from django.db import migrations
from django.utils.html import strip_tags


def _plain_excerpt(html_text, length=850):
    if not html_text:
        return ""
    plain = strip_tags(html_text)
    plain = plain.replace("\xa0", " ").replace("&nbsp;", " ")
    plain = plain.strip()
    if len(plain) <= length:
        return plain
    cut = plain[:length].rsplit(" ", 1)[0]
    return cut + " …"


def backfill_excerpt_850(apps, schema_editor):
    Item = apps.get_model("smart_blog", "Item")
    for row in Item.objects.iterator(chunk_size=200):
        ex = _plain_excerpt(row.text or "")
        if (row.excerpt_plain or "") != ex:
            Item.objects.filter(pk=row.pk).update(excerpt_plain=ex)


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0055_item_excerpt_plain_longer"),
    ]

    operations = [
        migrations.RunPython(backfill_excerpt_850, migrations.RunPython.noop),
    ]
