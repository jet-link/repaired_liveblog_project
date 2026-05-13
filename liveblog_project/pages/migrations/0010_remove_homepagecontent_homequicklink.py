"""Remove HomePageContent / HomeQuickLink models — the public home page is now BraiNews (smart_blog:items_list)."""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0009_homepagecontent_minimalist'),
    ]

    operations = [
        migrations.DeleteModel(name='HomeQuickLink'),
        migrations.DeleteModel(name='HomePageContent'),
    ]
