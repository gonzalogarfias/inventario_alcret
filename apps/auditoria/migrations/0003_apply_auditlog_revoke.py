from django.db import migrations


def apply_revoke(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='app_user'")
            if cursor.fetchone():
                cursor.execute("REVOKE UPDATE, DELETE ON auditoria_auditlog FROM app_user;")


class Migration(migrations.Migration):

    dependencies = [
        ("auditoria", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(apply_revoke, reverse_code=migrations.RunPython.noop),
    ]
