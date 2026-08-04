"""Comando para poblar el sistema con datos de demostración.

Crea usuarios, categorías, productos, almacenes, movimientos de los
últimos 30 días, facturas, alertas, configuración de métricas y
entradas de integración CRM para poder explorar la aplicación como si
estuviera en funcionamiento.

Es idempotente: si ya existen productos, no duplica datos salvo que se
use --force para borrar todo primero.

Uso:
    python manage.py seed_demo
    python manage.py seed_demo --force
"""

import hashlib
import random
from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string

from apps.inventario.models import Almacen, Categoria, Movimiento, Producto, Stock
from apps.usuarios.models import Usuario

PASSWORD = "Alcret2026!Demo"


class Command(BaseCommand):
    help = "Puebla la base de datos con datos de demostración."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Borra los datos existentes antes de sembrar.",
        )

    def handle(self, **options):
        if options["force"]:
            self._limpiar()

        if Producto.objects.exists():
            self.stdout.write(self.style.WARNING("Ya existen productos; se omite el seed. Usa --force para regenerar."))
            return

        with transaction.atomic():
            admin, vendedor, almacenista = self._crear_usuarios()
            categorias = self._crear_categorias()
            almacenes = self._crear_almacenes()
            productos = self._crear_productos(categorias)
            self._crear_movimientos(productos, almacenes, admin)
            self._crear_facturas(admin)
            self._crear_metricas()
            self._crear_integracion()

        self.stdout.write(self.style.SUCCESS("\n=== SEED COMPLETADO ==="))
        self.stdout.write(f"Admin:      admin@demo.com / {PASSWORD}")
        self.stdout.write(f"Vendedor:   vendedor@demo.com / {PASSWORD}")
        self.stdout.write(f"Almacenista: almacen@demo.com / {PASSWORD}")

    # ------------------------------------------------------------------ #
    # Limpieza
    # ------------------------------------------------------------------ #

    def _limpiar(self):
        from apps.alertas.models import Alerta, AlertaConfig
        from apps.auditoria.models import AuditLog
        from apps.finanzas.models import Factura
        from apps.integracion.models import ClaveCRM, SyncLog, WebhookCRM
        from apps.metricas.models import DashboardConfig, ReporteProgramado

        for model in [
            Factura,
            Movimiento,
            Stock,
            ReporteProgramado,
            DashboardConfig,
            Alerta,
            AlertaConfig,
            SyncLog,
            WebhookCRM,
            ClaveCRM,
            AuditLog,
            Producto,
            Categoria,
            Almacen,
            Usuario,
        ]:
            model.objects.all().delete()
        self.stdout.write("Datos previos eliminados.")

    # ------------------------------------------------------------------ #
    # Usuarios
    # ------------------------------------------------------------------ #

    def _crear_usuarios(self):
        from django.contrib.auth.models import Permission

        admin, _ = Usuario.objects.get_or_create(
            email="admin@demo.com",
            defaults={
                "nombre": "Administrador Demo",
                "rol": Usuario.Rol.ADMINISTRADOR,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin.set_password(PASSWORD)
        admin.save()

        perms = Permission.objects.filter(
            codename__in=[
                "puede_gestionar_usuarios",
                "puede_ajustar_stock",
                "puede_ver_auditoria_completa",
                "puede_configurar_crm",
            ]
        )
        admin.user_permissions.add(*perms)

        vendedor, _ = Usuario.objects.get_or_create(
            email="vendedor@demo.com",
            defaults={
                "nombre": "Vendedor Demo",
                "rol": Usuario.Rol.VENDEDOR,
            },
        )
        vendedor.set_password(PASSWORD)
        vendedor.save()

        almacenista, _ = Usuario.objects.get_or_create(
            email="almacen@demo.com",
            defaults={
                "nombre": "Almacenista Demo",
                "rol": Usuario.Rol.ALMACENISTA,
            },
        )
        almacenista.set_password(PASSWORD)
        almacenista.save()

        self.stdout.write(f"Usuarios: admin={admin.email}, vendedor={vendedor.email}, almacenista={almacenista.email}")
        return admin, vendedor, almacenista

    # ------------------------------------------------------------------ #
    # Catálogo
    # ------------------------------------------------------------------ #

    def _crear_categorias(self):
        datos = [
            ("Electrónica", "Componentes y dispositivos electrónicos"),
            ("Ferretería", "Herramientas y materiales"),
            ("Oficina", "Insumos de oficina"),
            ("Limpieza", "Productos de limpieza"),
        ]
        categorias = []
        for nombre, desc in datos:
            cat, _ = Categoria.objects.get_or_create(
                nombre=nombre, defaults={"descripcion": desc}
            )
            categorias.append(cat)
        self.stdout.write(f"Categorías: {[c.nombre for c in categorias]}")
        return categorias

    def _crear_almacenes(self):
        datos = [
            ("Almacén Central", "Av. Principal 1234, Ciudad"),
            ("Depósito Norte", "Ruta 9 km 32, Zona Industrial"),
        ]
        almacenes = []
        for nombre, ubicacion in datos:
            alm, _ = Almacen.objects.get_or_create(
                nombre=nombre, defaults={"ubicacion": ubicacion}
            )
            almacenes.append(alm)
        self.stdout.write(f"Almacenes: {[a.nombre for a in almacenes]}")
        return almacenes

    def _crear_productos(self, categorias):
        from django.db.models import Sum

        catalogo = [
            # (sku, nombre, categoria_idx, precio, costo, stock_minimo, stock_inicial)
            ("EL-001", "Router WiFi 6", 0, Decimal("120.00"), Decimal("80.00"), 5, 40),
            ("EL-002", "Cámara IP 4K", 0, Decimal("250.00"), Decimal("160.00"), 3, 20),
            ("EL-003", "Switch 8 puertos", 0, Decimal("85.00"), Decimal("55.00"), 4, 30),
            ("FE-001", "Taladro percutor", 1, Decimal("95.00"), Decimal("62.00"), 6, 15),
            ("FE-002", "Caja de herramientas", 1, Decimal("45.00"), Decimal("28.00"), 8, 25),
            ("OF-001", "Resma papel A4", 2, Decimal("8.00"), Decimal("5.50"), 20, 100),
            ("OF-002", "Tóner impresora", 2, Decimal("120.00"), Decimal("85.00"), 4, 12),
            ("OF-003", "Cuaderno A5", 2, Decimal("3.50"), Decimal("2.00"), 30, 80),
            ("LI-001", "Detergente 5L", 3, Decimal("22.00"), Decimal("14.00"), 10, 50),
            ("LI-002", "Alcohol al 70% 1L", 3, Decimal("5.00"), Decimal("3.20"), 25, 60),
        ]

        productos = []
        for sku, nombre, idx, precio, costo, minimo, inicial in catalogo:
            prod, _ = Producto.objects.get_or_create(
                sku=sku,
                defaults={
                    "nombre": nombre,
                    "categoria": categorias[idx],
                    "precio_venta": precio,
                    "costo_promedio": costo,
                    "stock_minimo": minimo,
                },
            )
            stock_actual = (
                prod.stocks.aggregate(total=Sum("cantidad"))["total"] or 0
            )
            if stock_actual == 0:
                Stock.objects.create(
                    producto=prod,
                    almacen=Almacen.objects.first(),
                    cantidad=Decimal(inicial),
                )
            productos.append(prod)
        self.stdout.write(f"Productos: {len(productos)} creados")
        return productos

    # ------------------------------------------------------------------ #
    # Movimientos
    # ------------------------------------------------------------------ #

    def _crear_movimientos(self, productos, almacenes, admin):
        from apps.inventario.services import registrar_movimiento

        hoy = timezone.now().date()
        rng = random.Random(42)  # determinista para reproducibilidad

        # El stock inicial ya existe; generamos movimientos de los últimos
        # 30 días para alimentar los gráficos del dashboard.
        disponible = {
            (prod.pk, alm.pk): (
                prod.stocks.get(almacen=alm).cantidad
                if prod.stocks.filter(almacen=alm).exists()
                else 0
            )
            for prod in productos
            for alm in almacenes
        }

        for prod in productos:
            movimientos = rng.randint(3, 6)
            for _ in range(movimientos):
                almacen = rng.choice(almacenes)
                disponible_alm = disponible[(prod.pk, almacen.pk)]
                es_entrada = disponible_alm <= 0 or rng.random() < 0.55
                tipo = Movimiento.Tipo.ENTRADA if es_entrada else Movimiento.Tipo.SALIDA

                if tipo == Movimiento.Tipo.ENTRADA:
                    cantidad = Decimal(rng.randint(2, 20))
                else:
                    cantidad = Decimal(rng.randint(1, min(10, int(disponible_alm))))

                dias_atras = rng.randint(1, 30)
                costo = prod.costo_promedio

                m = registrar_movimiento(
                    tipo=tipo,
                    producto=prod,
                    almacen=almacen,
                    cantidad=cantidad,
                    realizada_por=admin,
                    costo_unitario=costo if tipo == Movimiento.Tipo.ENTRADA else None,
                    motivo="Seed de demostración",
                )
                disponible[(prod.pk, almacen.pk)] += (
                    cantidad if tipo == Movimiento.Tipo.ENTRADA else -cantidad
                )
                # Retro-datar para poblar las series temporales
                fecha = timezone.make_aware(
                    timezone.datetime.combine(hoy - timedelta(days=dias_atras), timezone.datetime.min.time())
                )
                Movimiento.objects.filter(pk=m.pk).update(created_at=fecha)

        self.stdout.write(f"Movimientos: {Movimiento.objects.count()} creados")

    # ------------------------------------------------------------------ #
    # Facturas
    # ------------------------------------------------------------------ #

    def _crear_facturas(self, admin):
        from apps.finanzas.models import Factura

        hoy = timezone.now().date()
        rng = random.Random(7)

        facturas_creadas = 0
        for i in range(10):
            tipo = Factura.Tipo.COMPRA if i % 2 == 0 else Factura.Tipo.VENTA
            monto = Decimal(rng.randint(5000, 80000))
            nombre = f"Factura {i + 1:03d}.pdf"
            contenido = ContentFile(
                b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                b"%%EOF\n",
                name=nombre,
            )
            factura = Factura(
                tipo=tipo,
                numero=f"F{i + 1:04d}",
                proveedor_cliente="Proveedor Demo S.A." if tipo == Factura.Tipo.COMPRA else "Cliente Demo SRL",
                monto=monto,
                fecha=hoy - timedelta(days=rng.randint(1, 30)),
                archivo=contenido,
                observaciones="Factura de demostración",
                subido_por=admin,
            )
            factura.save()
            facturas_creadas += 1

        self.stdout.write(f"Facturas: {facturas_creadas} creadas")

    # ------------------------------------------------------------------ #
    # Métricas
    # ------------------------------------------------------------------ #

    def _crear_metricas(self):
        from apps.metricas.models import DashboardConfig, ReporteProgramado

        DashboardConfig.objects.get_or_create(
            nombre="Dashboard principal",
            defaults={
                "descripcion": "Configuración por defecto del dashboard de métricas",
                "config": {"charts": ["stock", "movimientos", "facturas"]},
            },
        )
        ReporteProgramado.objects.get_or_create(
            nombre="Reporte semanal de inventario",
            defaults={
                "tipo": "PDF",
                "cron_expresion": "0 9 * * 1",
                "destinatarios": ["admin@demo.com"],
            },
        )
        self.stdout.write("Métricas: dashboard + reporte programado creados")

    # ------------------------------------------------------------------ #
    # Integración CRM
    # ------------------------------------------------------------------ #

    def _crear_integracion(self):
        from apps.integracion.models import ClaveCRM, SyncLog, WebhookCRM

        WebhookCRM.objects.get_or_create(
            evento="PRODUCTO_CREADO",
            defaults={"url_destino": "https://crm.ejemplo.com/webhook/inventario"},
        )
        SyncLog.objects.get_or_create(
            evento="PRODUCTO_CREADO",
            defaults={
                "estado": "ENVIADO",
                "payload": {"sku": "EL-001", "estado": "ok"},
                "respuesta": {"status": 200},
            },
        )
        secreto = get_random_string(48)
        ClaveCRM.objects.get_or_create(
            clave_publica=hashlib.sha256(f"pub-{secreto}".encode()).hexdigest(),
            defaults={
                "hash_clave": hashlib.sha256(secreto.encode()).hexdigest(),
                "expira_en": timezone.now() + timedelta(days=365),
            },
        )
        self.stdout.write("Integración CRM: webhook + sync log + clave creados")
