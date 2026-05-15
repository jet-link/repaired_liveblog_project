import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mindset", "0003_rename_mindset_mfo_followe_4af80e_idx_mindset_min_followe_854851_idx_and_more"),
        ("smart_blog", "0060_item_body_pin_hybrid_render"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="mindset_reply",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notifications",
                to="mindset.reply",
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="mindset_theme",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notifications",
                to="mindset.theme",
            ),
        ),
    ]
