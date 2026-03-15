# Enable PostgreSQL pg_trgm extension for trigram similarity (typo-tolerant search).
# No-op when not using PostgreSQL.

from django.db import connection, migrations


def enable_pg_trgm(apps, schema_editor):
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0004_replace_featured_image_url_with_file_upload"),
    ]

    operations = [
        migrations.RunPython(enable_pg_trgm, noop),
    ]
