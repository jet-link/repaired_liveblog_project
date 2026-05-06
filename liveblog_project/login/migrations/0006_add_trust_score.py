# Generated for User Trust Score System

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("login", "0005_add_avatar_pos_columns"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="trust_score",
            field=models.FloatField(db_index=True, default=10.0),
        ),
        migrations.AddField(
            model_name="profile",
            name="last_violation_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="can_post",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="shadow_banned",
            field=models.BooleanField(default=False),
        ),
    ]
