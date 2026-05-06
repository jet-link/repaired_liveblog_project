# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smart_blog', '0029_rename_smart_blog__item_id_2c8ea4_idx_smart_blog__item_id_4f2924_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='is_draft',
            field=models.BooleanField(default=False),
        ),
    ]
