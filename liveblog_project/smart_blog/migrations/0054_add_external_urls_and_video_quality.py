from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smart_blog', '0053_add_item_video'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemimage',
            name='external_url',
            field=models.URLField(blank=True, help_text='External CDN URL for the full image', max_length=500),
        ),
        migrations.AddField(
            model_name='itemvideo',
            name='external_url',
            field=models.URLField(blank=True, help_text='External CDN URL for original video', max_length=500),
        ),
        migrations.AddField(
            model_name='itemvideo',
            name='video_360p',
            field=models.URLField(blank=True, help_text='360p quality URL', max_length=500),
        ),
        migrations.AddField(
            model_name='itemvideo',
            name='video_480p',
            field=models.URLField(blank=True, help_text='480p quality URL', max_length=500),
        ),
        migrations.AddField(
            model_name='itemvideo',
            name='video_720p',
            field=models.URLField(blank=True, help_text='720p quality URL', max_length=500),
        ),
        migrations.AddField(
            model_name='itemvideo',
            name='video_1080p',
            field=models.URLField(blank=True, help_text='1080p HD quality URL', max_length=500),
        ),
    ]
