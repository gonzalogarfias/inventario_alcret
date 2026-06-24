from django.db import migrations


def apply_revoke(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("REVOKE UPDATE, DELETE ON auditoria_auditlog FROM app_user;")


class Migration(migrations.Migration):

    dependencies = [
        ("auditoria", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(apply_revoke, reverse_code=migrations.RunPython.noop),
    ]
