# Fix: 0004 used SeparateDatabaseAndState with empty database_operations,
# so avatar_pos_x/avatar_pos_y were never created in the database.
# This migration adds the columns via raw SQL — vendor-aware so it works
# on PostgreSQL (production) and SQLite (local dev).
from django.db import migrations


_PG_FORWARD = [
    "ALTER TABLE login_profile ADD COLUMN IF NOT EXISTS avatar_pos_x DOUBLE PRECISION NOT NULL DEFAULT 0.0;",
    "ALTER TABLE login_profile ADD COLUMN IF NOT EXISTS avatar_pos_y DOUBLE PRECISION NOT NULL DEFAULT 0.0;",
]
_PG_REVERSE = [
    "ALTER TABLE login_profile DROP COLUMN IF EXISTS avatar_pos_x;",
    "ALTER TABLE login_profile DROP COLUMN IF EXISTS avatar_pos_y;",
]

def _forward(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "postgresql":
        for stmt in _PG_FORWARD:
            schema_editor.execute(stmt)
        return
    if vendor == "sqlite":
        with schema_editor.connection.cursor() as cur:
            cur.execute("PRAGMA table_info(login_profile);")
            existing = {row[1] for row in cur.fetchall()}
        for col in ("avatar_pos_x", "avatar_pos_y"):
            if col not in existing:
                schema_editor.execute(
                    f"ALTER TABLE login_profile ADD COLUMN {col} REAL NOT NULL DEFAULT 0.0"
                )
        return
    # Other vendors: best-effort plain ALTERs (without IF NOT EXISTS).
    for col in ("avatar_pos_x", "avatar_pos_y"):
        schema_editor.execute(
            f"ALTER TABLE login_profile ADD COLUMN {col} DOUBLE PRECISION NOT NULL DEFAULT 0.0"
        )


def _reverse(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "postgresql":
        for stmt in _PG_REVERSE:
            schema_editor.execute(stmt)
        return
    # SQLite поддерживает DROP COLUMN с 3.35; для совместимости — best-effort.
    for col in ("avatar_pos_x", "avatar_pos_y"):
        try:
            schema_editor.execute(f"ALTER TABLE login_profile DROP COLUMN {col}")
        except Exception:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ("login", "0004_profile_avatar_pos_state"),
    ]

    operations = [
        migrations.RunPython(_forward, _reverse),
    ]
