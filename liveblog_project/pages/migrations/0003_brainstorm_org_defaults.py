# Defaults: public brand brainstorm.org (Site domain set separately in Django admin).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0002_aboutpagecontent_contactspagecontent"),
    ]

    operations = [
        migrations.AlterField(
            model_name="aboutpagecontent",
            name="browser_title",
            field=models.CharField(default="About — brainstorm.org", max_length=120),
        ),
        migrations.AlterField(
            model_name="aboutpagecontent",
            name="title_h1",
            field=models.CharField(default="brainstorm.org", max_length=200),
        ),
        migrations.AlterField(
            model_name="contactspagecontent",
            name="browser_title",
            field=models.CharField(default="Contacts — brainstorm.org", max_length=120),
        ),
        migrations.AlterField(
            model_name="contactspagecontent",
            name="email_address",
            field=models.CharField(default="discover@brainstorm.org", max_length=255),
        ),
    ]
