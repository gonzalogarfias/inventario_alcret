# Integración CRM — Documentación técnica

> **App:** `apps/integracion`
> **Propósito:** Puente entre el sistema de inventario ALCRET y un CRM externo.
> **Flujo actual:** Unidireccional — ALCRET **publica eventos** hacia el webhook del CRM mediante tareas asíncronas (Celery) firmadas con **HMAC-SHA256**.

---

## 1. Visión general

Cada vez que se registra un movimiento de inventario (entrada, salida o ajuste), el sistema emite un evento hacia el CRM. El envío es **asíncrono**, no bloquea la operación de inventario, y queda registrado en una bitácora (`SyncLog`) para auditoría y depuración.

```
Movimiento de stock / Cliente / Cotización creado o editado
        │
        ▼
signals.publicar_movimiento_al_crm / publicar_cliente_al_crm / publicar_cotizacion_al_crm
        │  (solo si CRM_WEBHOOK_URL está configurado)
        │  encolan "stock.actualizado", "cliente.creado/actualizado", "cotizacion.creada"
        ▼
tasks.enviar_evento_crm               (Celery, 3 reintentos con backoff)
        │  POST con headers: X-Signature (HMAC-SHA256), X-Timestamp
        ▼
SyncLog                              (PENDIENTE → ENVIADO / FALLIDO)
```

---

## 2. Estructura de la app

```
apps/integracion/
├── models.py        # WebhookCRM, SyncLog, ClaveCRM
├── services.py      # crm_configurado(), registrar_evento_auditoria()
├── signals.py       # publicar_movimiento_al_crm, registrar_rotacion_clave_crm
├── tasks.py         # enviar_evento_crm, verificar_expiracion_claves (Celery)
├── admin.py         # Admin de WebhookCRM y SyncLog (solo lectura)
├── urls.py          # VACÍO — no hay endpoints de entrada por ahora
├── management/commands/rotar_clave_crm.py
└── tests/           # test_tasks.py, test_signals.py, test_rotacion.py

# Señales de dominio que emiten eventos CRM (viven en sus apps):
apps/clientes/signals.py       # publicar_cliente_al_crm → cliente.creado / cliente.actualizado
apps/cotizaciones/signals.py   # publicar_cotizacion_al_crm → cotizacion.creada
```

---

## 3. Modelos (`models.py`)

### 3.1 `WebhookCRM`
Configuración de webhooks: qué evento va a qué URL.

| Campo | Tipo | Descripción |
|---|---|---|
| `evento` | CharField | Nombre del evento (ej. `PRODUCTO_CREADO`) |
| `url_destino` | URLField | URL del webhook del CRM |
| `activo` | BooleanField | Habilita/deshabilita el envío |
| `created_at` | DateTimeField | Fecha de creación |

> **Nota:** el modelo existe para registrar/administrar webhooks, pero el envío real hoy se controla por las variables de entorno `CRM_WEBHOOK_URL` y `CRM_HMAC_SECRET` (ver sección 4).

### 3.2 `SyncLog`
Bitácora inmutable de cada intento de envío. **Es la primera pantalla que hay que revisar al conectar.**

| Campo | Tipo | Descripción |
|---|---|---|
| `evento` | CharField | Nombre del evento enviado |
| `estado` | CharField | `PENDIENTE` / `ENVIADO` / `FALLIDO` |
| `payload` | JSONField | Cuerpo del evento |
| `respuesta` | JSONField | Respuesta del CRM (status + body) o error |
| `intentos` | IntegerField | Número de reintentos realizados |
| `created_at` / `updated_at` | DateTimeField | Trazabilidad |

En el admin se muestra de **solo lectura** (`has_change_permission=False`, `has_delete_permission=False`).

### 3.3 `ClaveCRM`
Claves API rotativas usadas para autenticación del lado del CRM.

| Campo | Tipo | Descripción |
|---|---|---|
| `clave_publica` | CharField (64, unique) | Identificador público de la clave |
| `hash_clave` | CharField (128) | SHA-256 hex del secreto (nunca se guarda el secreto en claro) |
| `activa` | BooleanField | Solo una clave activa a la vez |
| `creada_en` | DateTimeField | Fecha de creación |
| `expira_en` | DateTimeField | Fecha de expiración |
| `rotada_en` | DateTimeField | Fecha en que fue reemplazada |

**Reglas:**
- Al crear una clave nueva con `activa=True`, la anterior se desactiva automáticamente (con `rotada_en`).
- `clean()` exige `expira_en` futuro y `hash_clave` en formato SHA-256 hex (64 caracteres).
- La rotación queda auditada en `AuditLog` con evento `SYNC_CRM`.

---

## 4. Configuración (variables de entorno)

En el `.env` del servidor:

```
CRM_WEBHOOK_URL=https://tu-crm.com/webhook/inventario
CRM_HMAC_SECRET=<secreto-compartido>
```

**Comportamiento según configuración:**
- Sin `CRM_WEBHOOK_URL` → las señales hacen `skip` y **no se envía nada**.
- Con `CRM_WEBHOOK_URL` pero sin `CRM_HMAC_SECRET` → la tarea registra `FALLIDO`.
- Con ambos → envío completo con firma HMAC.

También disponibles desde Django settings: `settings.CRM_WEBHOOK_URL`, `settings.CRM_HMAC_SECRET`.

---

## 5. Contrato del webhook (lo que debe exponer el CRM)

### 5.1 Request

- **Método:** `POST`
- **URL:** la configurada en `CRM_WEBHOOK_URL`
- **Content-Type:** `application/json`
- **Headers:**
  - `X-Signature`: HMAC-SHA256 del **cuerpo crudo** (bytes exactos), en hexadecimal
  - `X-Timestamp`: fecha ISO 8601 del envío

### 5.2 Body

Ejemplo con `stock.actualizado`:

```json
{
  "evento": "stock.actualizado",
  "payload": {
    "almacen_id": "uuid-del-almacen",
    "producto_id": "uuid-del-producto",
    "sku_o_vin": "3HHDMABN7RL000001",
    "nombre_unidad": "Kenworth T680 2024",
    "cantidad_disponible": "3",
    "tipo_movimiento": "ENTRADA"
  },
  "timestamp": "2026-08-04T17:57:00+00:00"
}
```

Otros eventos emitidos:

- `cliente.creado` / `cliente.actualizado` → payload `{empresa, nombre, email, telefono, rfc}`.
- `cotizacion.creada` → payload `{cliente_email, monto, esquema, unidad_interes, vendedor_email}`.

### 5.3 Cómo verificar la firma del lado del CRM

```python
import hmac
import hashlib

firma_recibida = request.headers.get("X-Signature")
firma_esperada = hmac.new(
    CRMHMAC_SECRET.encode(),      # el secreto compartido
    request.body,                 # el cuerpo crudo, tal como llegó
    hashlib.sha256
).hexdigest()

if not hmac.compare_digest(firma_recibida, firma_esperada):
    raise PermissionError("Firma inválida")
```

**Importante:** la firma se calcula sobre los **bytes del cuerpo tal como se recibieron** (no sobre JSON re-serializado). Cualquier transformación rompe la validación.

---

## 6. Tareas Celery (`tasks.py`)

### 6.1 `enviar_evento_crm(evento, payload)`

- Crea un `SyncLog` en `PENDIENTE`.
- Construye el body `{evento, payload, timestamp}` y la firma HMAC.
- Hace `POST` con timeout de 30s.
- **Éxito:** `SyncLog.estado = ENVIADO` y guarda la respuesta.
- **Fallo:** `SyncLog.estado = FALLIDO` y **reintenta hasta 3 veces** con backoff (máximo 900s).

### 6.2 `verificar_expiracion_claves()`

- Tarea programada (Celery Beat, cada 24 h).
- Alerta (log) claves activas que expiran en menos de 7 días.
- Desactiva (`activa=False`, `rotada_en`) claves ya vencidas.

---

## 7. Señales (`signals.py`)

| Señal | Disparada por | Acción |
|---|---|---|
| `publicar_movimiento_al_crm` | `post_save` de `Movimiento` (solo `created`) | Encola `enviar_evento_crm` con evento `stock.actualizado` y payload `{almacen_id, producto_id, sku_o_vin, nombre_unidad, cantidad_disponible, tipo_movimiento}` (cantidad disponible actual del stock, VIN si existe sino SKU). Respeta `CRM_WEBHOOK_URL`. |
| `publicar_cliente_al_crm` | `post_save` de `Cliente` (en `apps.clientes`) | Encola `cliente.creado` o `cliente.actualizado` según sea creación o edición, con payload `{empresa, nombre, email, telefono, rfc}`. |
| `publicar_cotizacion_al_crm` | `post_save` de `Cotizacion` (en `apps.cotizaciones`) | Encola `cotizacion.creada` con payload `{cliente_email, monto, esquema, unidad_interes, vendedor_email}`. |
| `registrar_rotacion_clave_crm` | `post_save` de `ClaveCRM` (solo `created`) | Audita en `AuditLog` (evento `SYNC_CRM`) la rotación de clave. |

Las señales se registran en `apps.py` (`ready()` → `import apps.integracion.signals`).

---

## 8. Rotación de claves

Comando disponible:

```bash
python manage.py rotar_clave_crm --actualizar-env
```

- Genera un secreto nuevo (64 hex), lo activa y desactiva el anterior.
- Con `--actualizar-env` además reescribe `CRM_HMAC_SECRET` en el `.env`.
- Opcional: `--dias-expiracion N` (default 90).
- **Aviso:** guardar el secreto nuevo de forma segura; se muestra una sola vez en consola.

---

## 9. Monitoreo y depuración

1. **Admin** → `/admin/integracion/synclog/`: ver `estado`, `intentos` y `respuesta` de cada envío.
2. **Logs del worker Celery**: `docker compose -f docker-compose.prod.yml logs worker -f`.
3. **AuditLog**: las rotaciones de clave quedan en `/admin/auditoria/`.

---

## 10. Estado actual y pendientes

- ✅ **Envío de eventos** a webhook con firma HMAC-SHA256, reintentos y bitácora.
- ✅ **Eventos emitidos:** `stock.actualizado`, `cliente.creado`, `cliente.actualizado`, `cotizacion.creada`.
- ✅ **Rotación y expiración** de claves CRM.
- ✅ **Auditoría** de rotaciones.
- ⬜ **`urls.py` está vacío**: no hay endpoint de entrada para que el CRM llame a ALCRET. Si se necesita, habría que crear `views.py` + autenticación por `ClaveCRM`.
- ⬜ El payload de `stock.actualizado` incluye **IDs** (producto/almacén) + `sku_o_vin`/`nombre_unidad`; el CRM puede usar `sku_o_vin` para mapear contra su propia base.

---

## 11. Referencia rápida del flujo de conexión (para el desarrollador del CRM)

1. Proporcionar al proyecto la URL del webhook → se setea en `CRM_WEBHOOK_URL`.
2. Acordar un **secreto compartido** → se setea en `CRM_HMAC_SECRET` (mismo valor en ambos lados).
3. Exponer un `POST` en esa URL que:
   - valide `X-Signature` con HMAC-SHA256 del body (ver sección 5.3),
   - responda `2xx` en éxito (timeout 30s),
   - procese el evento `stock.actualizado`.
4. Verificar los envíos en `/admin/integracion/synclog/`.
5. Para pruebas en vivo, crear/editar un cliente (eventos `cliente.*`), una cotización (`cotizacion.creada`) o registrar un movimiento (`stock.actualizado`).
