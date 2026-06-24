from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("usuarios/", views.usuario_list, name="usuario_list"),
    path("usuarios/nuevo/", views.usuario_create, name="usuario_create"),
    path("usuarios/<uuid:pk>/editar/", views.usuario_update, name="usuario_update"),
]
