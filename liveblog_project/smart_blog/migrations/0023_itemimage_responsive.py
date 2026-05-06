# Generated migration for ItemImage responsive images

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smart_blog', '0022_rename_searchhist_user_created_idx_smart_blog__user_id_a7c3f4_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemimage',
            name='image_thumbnail',
            field=models.ImageField(blank=True, null=True, upload_to='items/'),
        ),
        migrations.AddField(
            model_name='itemimage',
            name='image_medium',
            field=models.ImageField(blank=True, null=True, upload_to='items/'),
        ),
        migrations.AddField(
            model_name='itemimage',
            name='width',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='itemimage',
            name='height',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
