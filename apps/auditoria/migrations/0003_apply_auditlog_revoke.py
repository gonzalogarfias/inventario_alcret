from django.db import migrations
from django.db.utils import ProgrammingError


def apply_revoke(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        try:
            schema_editor.execute("REVOKE UPDATE, DELETE ON auditoria_auditlog FROM app_user;")
        except ProgrammingError:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ("auditoria", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(apply_revoke, reverse_code=migrations.RunPython.noop),
    ]
