from django.apps import AppConfig


class IntegracionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integracion"
    label = "integracion"

    def ready(self):
        import apps.integracion.signals
