# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0038_itemstatshourly_trendingitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="trendingitem",
            name="likes_1h",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="trendingitem",
            name="comments_1h",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
