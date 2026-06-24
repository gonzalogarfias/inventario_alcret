from django.urls import path
from . import views

urlpatterns = [
    path("api/datos-dashboard/", views.datos_dashboard, name="datos_dashboard"),
]
