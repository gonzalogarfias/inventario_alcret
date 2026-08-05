import json

import pytest
from django.urls import reverse

from apps.auditoria.models import AuditLog
from apps.finanzas.models import Factura


@pytest.mark.django_db
class TestFinanzasViews:
    def test_dashboard_requiere_login(self, client):
        response = client.get(reverse("finanzas_dashboard"))
        assert response.status_code == 302

    def test_dashboard_autenticado(self, authenticated_client):
        response = authenticated_client.get(reverse("finanzas_dashboard"))
        assert response.status_code == 200
        assert "facturas_recientes" in response.context

    def test_upload_requiere_login(self, client):
        response = client.get(reverse("factura_upload"))
        assert response.status_code == 302

    def test_upload_get(self, authenticated_client):
        response = authenticated_client.get(reverse("factura_upload"))
        assert response.status_code == 200

    def test_upload_post(self, authenticated_client, producto, almacen, usuario_admin):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.inventario.models import Movimiento
        mov = Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA, producto=producto,
            almacen=almacen, cantidad=10, realizada_por=usuario_admin,
        )
        archivo = SimpleUploadedFile("factura.pdf", b"%PDF-1.4 test content", content_type="application/pdf")
        response = authenticated_client.post(reverse("factura_upload"), {
            "tipo": Factura.Tipo.COMPRA,
            "numero": "TEST-001",
            "proveedor_cliente": "Test SA",
            "monto": "500.00",
            "fecha": "2026-07-01",
            "movimiento": mov.pk,
            "observaciones": "Test",
            "archivo": archivo,
        }, follow=True)
        assert Factura.objects.filter(numero="TEST-001").exists()
        assert response.status_code == 200

    def test_upload_movimiento_label_legible(self, authenticated_client, producto, almacen, usuario_admin):
        from apps.finanzas.forms import FacturaForm
        from apps.inventario.models import Movimiento
        mov = Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA, producto=producto,
            almacen=almacen, cantidad=10, realizada_por=usuario_admin,
        )
        form = FacturaForm(user=usuario_admin)
        campo = form.fields["movimiento"]
        assert producto.nombre in campo.label_from_instance(mov)
        assert producto.sku in campo.label_from_instance(mov)
        assert almacen.nombre in campo.label_from_instance(mov)
        assert "Entrada" in campo.label_from_instance(mov)


    def test_upload_rechaza_pdf_con_cabecera_invalida(self, authenticated_client, producto, almacen, usuario_admin):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.inventario.models import Movimiento
        mov = Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA, producto=producto,
            almacen=almacen, cantidad=10, realizada_por=usuario_admin,
        )
        archivo = SimpleUploadedFile("factura.pdf", b"no es pdf", content_type="application/pdf")
        authenticated_client.post(reverse("factura_upload"), {
            "tipo": Factura.Tipo.COMPRA,
            "numero": "BAD-PDF",
            "proveedor_cliente": "Test SA",
            "monto": "500.00",
            "fecha": "2026-07-01",
            "movimiento": mov.pk,
            "observaciones": "Test",
            "archivo": archivo,
        })
        assert not Factura.objects.filter(numero="BAD-PDF").exists()

    def test_upload_vendedor_no_puede_subir_compra(self, client_vendedor, producto, almacen, usuario_admin):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.inventario.models import Movimiento
        mov = Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA, producto=producto,
            almacen=almacen, cantidad=10, realizada_por=usuario_admin,
        )
        archivo = SimpleUploadedFile("factura.pdf", b"%PDF-1.4 test content", content_type="application/pdf")
        client_vendedor.post(reverse("factura_upload"), {
            "tipo": Factura.Tipo.COMPRA,
            "numero": "VEN-COMPRA",
            "proveedor_cliente": "Test SA",
            "monto": "500.00",
            "fecha": "2026-07-01",
            "movimiento": mov.pk,
            "observaciones": "Test",
            "archivo": archivo,
        })
        assert not Factura.objects.filter(numero="VEN-COMPRA").exists()

    def test_upload_registra_evento_especifico_de_auditoria(self, authenticated_client, producto, almacen, usuario_admin):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.inventario.models import Movimiento
        mov = Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA, producto=producto,
            almacen=almacen, cantidad=10, realizada_por=usuario_admin,
        )
        archivo = SimpleUploadedFile("factura.pdf", b"%PDF-1.4 test content", content_type="application/pdf")
        authenticated_client.post(reverse("factura_upload"), {
            "tipo": Factura.Tipo.COMPRA,
            "numero": "AUD-FACT",
            "proveedor_cliente": "Test SA",
            "monto": "500.00",
            "fecha": "2026-07-01",
            "movimiento": mov.pk,
            "observaciones": "Test",
            "archivo": archivo,
        })
        assert AuditLog.objects.filter(evento=AuditLog.Evento.FACTURA_SUBIDA).exists()

    def test_datos_finanzas_api(self, authenticated_client, producto, almacen, usuario_admin):
        from apps.inventario.models import Movimiento
        Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA, producto=producto,
            almacen=almacen, cantidad=100, realizada_por=usuario_admin,
        )
        response = authenticated_client.get(reverse("datos_finanzas"))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert "labels" in data
        assert "compras" in data
        assert "ventas" in data
        assert "valor_inventario" in data

    def test_datos_finanzas_devuelve_error_json_si_falla(self, authenticated_client, monkeypatch):
        import apps.finanzas.views as views
        monkeypatch.setattr(views, "_calcular_datos_finanzas", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        response = authenticated_client.get(reverse("datos_finanzas"))
        assert response.status_code == 500
        data = json.loads(response.content)
        assert "error" in data


@pytest.mark.django_db
class TestFacturaArchivo:
    def _crear_factura(self, producto, almacen, usuario_admin):
        from datetime import date

        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.inventario.models import Movimiento
        mov = Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA, producto=producto,
            almacen=almacen, cantidad=10, realizada_por=usuario_admin,
        )
        archivo = SimpleUploadedFile("factura.pdf", b"%PDF-1.4 contenido", content_type="application/pdf")
        return Factura.objects.create(
            tipo=Factura.Tipo.COMPRA,
            numero="ARCH-001",
            proveedor_cliente="Test SA",
            monto="500.00",
            fecha=date(2026, 7, 1),
            movimiento=mov,
            archivo=archivo,
            subido_por=usuario_admin,
        )

    def test_archivo_requiere_login(self, client, producto, almacen, usuario_admin):
        factura = self._crear_factura(producto, almacen, usuario_admin)
        response = client.get(reverse("factura_archivo", args=[factura.pk]))
        assert response.status_code == 302

    def test_archivo_acceso_admin(self, authenticated_client, producto, almacen, usuario_admin):
        factura = self._crear_factura(producto, almacen, usuario_admin)
        response = authenticated_client.get(reverse("factura_archivo", args=[factura.pk]))
        assert response.status_code == 200
        contenido = b"".join(response.streaming_content)
        assert b"%PDF-1.4 contenido" in contenido

    def test_archivo_acceso_otros_roles(self, client_vendedor, client_almacenista, producto, almacen, usuario_admin):
        factura = self._crear_factura(producto, almacen, usuario_admin)
        assert client_vendedor.get(reverse("factura_archivo", args=[factura.pk])).status_code == 302
        assert client_almacenista.get(reverse("factura_archivo", args=[factura.pk])).status_code == 200

    def test_archivo_inexistente_404(self, authenticated_client):
        import uuid
        response = authenticated_client.get(reverse("factura_archivo", args=[uuid.uuid4()]))
        assert response.status_code == 404
