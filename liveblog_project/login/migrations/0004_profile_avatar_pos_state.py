from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("login", "0003_alter_profile_avatar_file"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="profile",
                    name="avatar_pos_x",
                    field=models.FloatField(default=0.0),
                ),
                migrations.AddField(
                    model_name="profile",
                    name="avatar_pos_y",
                    field=models.FloatField(default=0.0),
                ),
            ],
            database_operations=[],
        ),
    ]
