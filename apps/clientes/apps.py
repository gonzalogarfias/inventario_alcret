from django.apps import AppConfig


class ClientesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.clientes"
    label = "clientes"

    def ready(self):
        import apps.clientes.signals  # noqa: F401
