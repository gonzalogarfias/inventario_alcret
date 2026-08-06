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
            clientes = self._crear_clientes()
            self._crear_cotizaciones(clientes, productos, vendedor)
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
        from apps.clientes.models import Cliente
        from apps.cotizaciones.models import Cotizacion
        from apps.finanzas.models import Factura
        from apps.integracion.models import ClaveCRM, SyncLog, WebhookCRM
        from apps.metricas.models import DashboardConfig, ReporteProgramado

        for model in [
            Factura,
            Cotizacion,
            Cliente,
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
            ("Tractocamiones", "Tractocamiones de línea pesada"),
            ("Remolques", "Remolques, cajas secas y plataformas"),
            ("Refacciones", "Refacciones y consumibles"),
            ("Servicios", "Servicios de mantenimiento y operación"),
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
            # (sku, nombre, vin, categoria_idx, precio, costo, stock_minimo, stock_inicial)
            ("KW-T680-001", "Kenworth T680 2024", "3HHDMABN7RL000001",
             0, Decimal("1520000.00"), Decimal("1350000.00"), 1, 3),
            ("KW-T680-002", "Kenworth T680 2023", "3HHDMABN6RL000002",
             0, Decimal("1480000.00"), Decimal("1310000.00"), 1, 2),
            ("KW-W900-001", "Kenworth W900L 2024", "3HHDMABN7RL000003",
             0, Decimal("1650000.00"), Decimal("1460000.00"), 1, 2),
            ("KW-T800-001", "Kenworth T800 2023", "3HHDMABN6RL000004",
             0, Decimal("1440000.00"), Decimal("1280000.00"), 1, 3),
            ("PT-579-001", "Peterbilt 579 2024", "3HHDMABN7RL000005",
             0, Decimal("1580000.00"), Decimal("1400000.00"), 1, 2),
            ("PT-389-001", "Peterbilt 389 2023", "3HHDMABN6RL000006",
             0, Decimal("1620000.00"), Decimal("1430000.00"), 1, 2),
            ("REM-CS53-001", "Remolque Caja Seca 53 pies", "3HHDMABN7RL000007",
             1, Decimal("520000.00"), Decimal("450000.00"), 1, 4),
            ("REM-PL40-001", "Remolque Plataforma 40 pies", "3HHDMABN6RL000008",
             1, Decimal("480000.00"), Decimal("410000.00"), 1, 3),
            ("REF-ACE-001", "Aceite motor diésel 19L", "",
             2, Decimal("2800.00"), Decimal("2100.00"), 3, 15),
            ("SVC-INS-001", "Inspección mecánica anual", "",
             3, Decimal("3500.00"), Decimal("2200.00"), 1, 10),
        ]

        productos = []
        for sku, nombre, vin, idx, precio, costo, minimo, inicial in catalogo:
            prod, _ = Producto.objects.get_or_create(
                sku=sku,
                defaults={
                    "nombre": nombre,
                    "vin": vin,
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
    # Clientes
    # ------------------------------------------------------------------ #

    def _crear_clientes(self):
        from apps.clientes.models import Cliente

        datos = [
            ("Transportes del Norte S.A. de C.V.", "Juan Pérez",
             "juan.perez@transportesnorte.com", "+528112345678", "TNO900101ABC"),
            ("Grupo Logístico del Bajío", "María García",
             "maria.garcia@glb.com.mx", "+524441234567", "GLB850423HJK"),
            ("Carga Express S.R.L.", "Carlos López",
             "carlos.lopez@cargaexpress.mx", "+526612345678", "CEE920312QRT"),
            ("Fletes del Pacífico", "Ana Torres",
             "ana.torres@fletespacifico.com", "+523341234567", "FPT880505MNB"),
        ]
        clientes = []
        for empresa, nombre, email, telefono, rfc in datos:
            cliente, _ = Cliente.objects.get_or_create(
                email=email,
                defaults={
                    "empresa": empresa,
                    "nombre": nombre,
                    "telefono": telefono,
                    "rfc": rfc,
                },
            )
            clientes.append(cliente)
        self.stdout.write(f"Clientes: {len(clientes)} creados")
        return clientes

    # ------------------------------------------------------------------ #
    # Cotizaciones
    # ------------------------------------------------------------------ #

    def _crear_cotizaciones(self, clientes, productos, vendedor):
        from apps.cotizaciones.models import Cotizacion

        rng = random.Random(11)
        unidades = [p for p in productos if p.vin]
        creadas = 0
        for i, cliente in enumerate(clientes):
            for j in range(rng.randint(1, 3)):
                unidad = rng.choice(unidades)
                folio = f"COT-{creadas + 1:05d}"
                _, created = Cotizacion.objects.get_or_create(
                    folio=folio,
                    defaults={
                        "cliente": cliente,
                        "monto": unidad.precio_venta,
                        "esquema": rng.choice(
                            [Cotizacion.Esquema.CONTADO, Cotizacion.Esquema.CREDITO, Cotizacion.Esquema.ARRENDAMIENTO]
                        ),
                        "unidad_interes": unidad,
                        "vendedor": vendedor,
                        "estado": rng.choice(
                            [Cotizacion.Estado.ENVIADA, Cotizacion.Estado.ENVIADA, Cotizacion.Estado.GANADA]
                        ),
                    },
                )
                if created:
                    creadas += 1
        self.stdout.write(f"Cotizaciones: {creadas} creadas")

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
