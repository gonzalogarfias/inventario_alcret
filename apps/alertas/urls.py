from django.urls import path

from . import views

urlpatterns = [
    path("", views.alerta_list, name="alerta_list"),
    path("<uuid:pk>/resolver/", views.alerta_resolve, name="alerta_resolve"),
]
