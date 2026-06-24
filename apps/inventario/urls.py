from django.urls import path
from . import views

urlpatterns = [
    path("productos/", views.producto_list, name="producto_list"),
    path("productos/nuevo/", views.producto_create, name="producto_create"),
    path("productos/<uuid:pk>/", views.producto_detail, name="producto_detail"),
    path("productos/<uuid:pk>/editar/", views.producto_update, name="producto_update"),
    path("categorias/", views.categoria_list, name="categoria_list"),
    path("categorias/nuevo/", views.categoria_create, name="categoria_create"),
    path("categorias/<uuid:pk>/editar/", views.categoria_update, name="categoria_update"),
    path("almacenes/", views.almacen_list, name="almacen_list"),
    path("almacenes/nuevo/", views.almacen_create, name="almacen_create"),
    path("almacenes/<uuid:pk>/editar/", views.almacen_update, name="almacen_update"),
    path("movimientos/", views.movimiento_list, name="movimiento_list"),
    path("movimientos/nuevo/", views.movimiento_create, name="movimiento_create"),
    path("exportar/productos/csv/", views.exportar_productos_csv, name="exportar_productos_csv"),
    path("exportar/productos/excel/", views.exportar_productos_excel, name="exportar_productos_excel"),
    path("exportar/movimientos/csv/", views.exportar_movimientos_csv, name="exportar_movimientos_csv"),
    path("exportar/movimientos/excel/", views.exportar_movimientos_excel, name="exportar_movimientos_excel"),
]
