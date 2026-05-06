# Generated manually — preserve likes when user is deleted (SET_NULL)

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smart_blog', '0023_itemimage_responsive'),
    ]

    operations = [
        migrations.AlterField(
            model_name='commentlike',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='comment_likes', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='like',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='likes', to=settings.AUTH_USER_MODEL),
        ),
    ]
