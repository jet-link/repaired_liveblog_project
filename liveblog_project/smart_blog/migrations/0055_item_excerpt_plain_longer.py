from django.db import migrations, models
from django.utils.html import strip_tags


def _plain_excerpt(html_text, length=1100):
    if not html_text:
        return ""
    plain = strip_tags(html_text)
    plain = plain.replace("\xa0", " ").replace("&nbsp;", " ")
    plain = plain.strip()
    if len(plain) <= length:
        return plain
    cut = plain[:length].rsplit(" ", 1)[0]
    return cut + " …"


def backfill_longer_excerpts(apps, schema_editor):
    Item = apps.get_model("smart_blog", "Item")
    for row in Item.objects.iterator(chunk_size=200):
        ex = _plain_excerpt(row.text or "")
        if (row.excerpt_plain or "") != ex:
            Item.objects.filter(pk=row.pk).update(excerpt_plain=ex)


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0054_add_external_urls_and_video_quality"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="excerpt_plain",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Plain excerpt for list cards (synced from text on save).",
                max_length=1300,
            ),
        ),
        migrations.RunPython(backfill_longer_excerpts, migrations.RunPython.noop),
    ]
