from django.apps import AppConfig


class CotizacionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cotizaciones"
    label = "cotizaciones"

    def ready(self):
        import apps.cotizaciones.signals  # noqa: F401
