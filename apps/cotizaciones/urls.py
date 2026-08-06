from django.urls import path

from . import views

urlpatterns = [
    path("", views.cotizacion_list, name="cotizacion_list"),
    path("nueva/", views.cotizacion_create, name="cotizacion_create"),
    path("<uuid:pk>/editar/", views.cotizacion_update, name="cotizacion_update"),
]
