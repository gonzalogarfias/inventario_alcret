from django.urls import path
from . import views

urlpatterns = [
    path("auditoria/", views.auditlog_list, name="auditlog_list"),
    path("exportar/auditoria/csv/", views.exportar_auditoria_csv, name="exportar_auditoria_csv"),
    path("exportar/auditoria/excel/", views.exportar_auditoria_excel, name="exportar_auditoria_excel"),
]
