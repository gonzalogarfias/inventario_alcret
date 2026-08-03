from django.urls import path

from . import views

urlpatterns = [
    path("finanzas/", views.finanzas_dashboard, name="finanzas_dashboard"),
    path("finanzas/subir/", views.factura_upload, name="factura_upload"),
    path("finanzas/api/datos/", views.datos_finanzas, name="datos_finanzas"),
    path("finanzas/facturas/<uuid:pk>/archivo/", views.factura_archivo, name="factura_archivo"),
]
