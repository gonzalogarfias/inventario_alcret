from django.urls import path

from . import views

urlpatterns = [
    path("", views.cliente_list, name="cliente_list"),
    path("nuevo/", views.cliente_create, name="cliente_create"),
    path("<uuid:pk>/editar/", views.cliente_update, name="cliente_update"),
]
