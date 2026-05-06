# Hybrid document rendering: PDF vs DOCX HTML (pandoc).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0059_item_body_pin_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="body_pin_content_type",
            field=models.CharField(
                choices=[
                    ("text", "Text"),
                    ("docx", "DOCX"),
                    ("pdf", "PDF"),
                ],
                default="text",
                help_text="How to render pinned document on post detail (hybrid viewer / HTML).",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="item",
            name="body_pin_content_html",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Sanitized HTML from DOCX (pandoc); empty for PDF/text.",
            ),
        ),
    ]
