# Integración CRM — Contrato técnico de conexión

> **App:** `apps/integracion`
> **Propósito:** Puente entre el sistema de inventario ALCRET y un CRM externo.
> **Flujo actual:** **Unidireccional** — ALCRET **publica eventos** hacia el webhook del CRM mediante tareas asíncronas (Celery) firmadas con **HMAC-SHA256**.
> **Versión de contrato:** 1.0 — `version: 1` en cada evento.
> **Audiencia:** desarrolladores del sistema CRM que consumirá los eventos.

---

## 1. Resumen ejecutivo

ALCRET notifica al CRM cada vez que ocurre un cambio relevante: un movimiento de inventario, la creación o edición de un cliente, o la creación de una cotización. El envío es **asíncrono**, no bloquea la operación de inventario, y queda registrado en la tabla `SyncLog` para auditoría y depuración.

**Regla de oro:** este contrato define *estados* (snapshots), no *deltas*. El CRM debe **reemplazar** valores, nunca sumar o restar sobre los que ya tiene. Combinado con la deduplicación por `evento_id`, esto garantiza que los reintentos o mensajes duplicados **no corrompan los datos** del CRM.

```
Movimiento de stock / Cliente / Cotización
        │
        ▼
signals.publicar_movimiento_al_crm / publicar_cliente_al_crm / publicar_cotizacion_al_crm
        │  (solo si CRM_WEBHOOK_URL está configurado)
        │  encolan "stock.actualizado", "cliente.creado|actualizado", "cotizacion.creada"
        ▼
tasks.enviar_evento_crm               (Celery, hasta 3 reintentos con backoff)
        │  POST con headers: X-Signature (HMAC-SHA256), X-Timestamp
        │  body: {version, evento_id, evento, payload, timestamp}
        ▼
SyncLog                              (PENDIENTE → ENVIADO / FALLIDO)
```

---

## 2. Requisitos previos (lado ALCRET)

Para que los eventos se emitan, el `.env` del servidor ALCRET debe tener:

```
CRM_WEBHOOK_URL=https://tu-crm.com/webhook/inventario
CRM_HMAC_SECRET=<secreto-compartido-identico-en-ambos-lados>
```

**Comportamiento según configuración:**

| Configuración | Comportamiento |
|---|---|
| Sin `CRM_WEBHOOK_URL` | Las señales hacen `skip`. No se envía nada. |
| `CRM_WEBHOOK_URL` sin `CRM_HMAC_SECRET` | La tarea registra `FALLIDO`. |
| Ambos configurados | Envío completo con firma HMAC. |

> Los valores también están disponibles en Django: `settings.CRM_WEBHOOK_URL`, `settings.CRM_HMAC_SECRET` (`config/settings/base.py:248-249`).

**Infraestructura requerida:** Redis (broker Celery) y un worker Celery corriendo. Sin worker, los eventos quedan encolados pero **no** llegan al CRM.

---

## 3. Contrato HTTP del webhook

### 3.1 Request

- **Método:** `POST`
- **URL:** la configurada en `CRM_WEBHOOK_URL`
- **`Content-Type`:** `application/json`
- **Headers requeridos:**
  - `X-Signature`: HMAC-SHA256 del **cuerpo crudo** (bytes exactos tal como se enviaron), en hexadecimal.
  - `X-Timestamp`: fecha ISO 8601 UTC del envío (idéntica a `body.timestamp`).

### 3.2 Body

```json
{
  "version": 1,
  "evento_id": "1e6a3c46-...-uuid-unico-del-synclog",
  "evento": "stock.actualizado",
  "payload": {
    "movimiento_id": "uuid-del-movimiento",
    "almacen_id": "uuid-del-almacen",
    "almacen_codigo": "Almacen Central",
    "almacen_nombre": "Almacen Central",
    "almacen_ubicacion": "Monterrey, NL",
    "producto_id": "uuid-del-producto",
    "producto_sku": "KW-T680-001",
    "producto_vin": "3HHDMABN7RL000001",
    "sku_o_vin": "3HHDMABN7RL000001",
    "nombre_unidad": "Kenworth T680 2024",
    "cantidad_disponible": "3",
    "cantidad_movimiento": "-1",
    "tipo_movimiento": "SALIDA",
    "motivo": "Venta a Transportes del Norte",
    "costo_unitario": null,
    "realizada_por_email": "almacen@alcret.com",
    "realizada_por_nombre": "María López",
    "fecha_movimiento": "2026-08-07T17:57:00+00:00"
  },
  "timestamp": "2026-08-07T17:57:00+00:00"
}
```

### 3.3 Campos del sobre (wrapper)

| Campo | Tipo | Descripción |
|---|---|---|
| `version` | int | Versión del esquema de este sobre. Actual: `1`. |
| `evento_id` | string UUID | **Identificador único del evento.** Se usa para deduplicación (ver sección 7). No cambia entre reintentos del mismo evento. |
| `evento` | string | Nombre del evento. Ver sección 10. |
| `payload` | object | Carga del evento. Esquema específico por evento. |
| `timestamp` | string ISO 8601 UTC | Momento en que ALCRET generó el envío. |

---

## 4. Verificación de la firma (obligatoria)

La firma se calcula sobre los **bytes exactos** del cuerpo recibido, con el secreto compartido. **Cualquier re-serialización o transformación del JSON rompe la validación.**

```python
import hmac
import hashlib

firma_recibida = request.headers.get("X-Signature")
firma_esperada = hmac.new(
    CRM_HMAC_SECRET.encode(),   # el secreto compartido
    request.body,               # el cuerpo crudo, tal como llegó (bytes)
    hashlib.sha256
).hexdigest()

if not hmac.compare_digest(firma_recibida, firma_esperada):
    raise PermissionError("Firma inválida")
```

**Reglas:**
- Usar siempre `hmac.compare_digest()` (nunca `==`), es inmune a timing attacks.
- Validar contra `request.body` (bytes crudos), no contra el JSON parseado y re-serializado.
- Nunca loguear ni almacenar el secreto en claro.

---

## 5. Ventana de tiempo y anti-replay

`X-Timestamp` y `body.timestamp` permiten detectar mensajes reenviados o alterados.

1. Comparar siempre en **UTC**.
2. Rechazar mensajes cuya fecha difiera más de **±5 minutos** del reloj del CRM (responder `403`). Esto elimina los replay attacks y evita aplicar datos viejos fuera de orden.

```python
from datetime import datetime, timedelta, timezone

ts = datetime.fromisoformat(body["timestamp"])
if abs((datetime.now(timezone.utc) - ts)) > timedelta(minutes=5):
    return 403
```

---

## 6. Respuesta esperada y reintentos

- **Cualquier código `2xx`** cuenta como éxito. ALCRET marca el `SyncLog` como `ENVIADO` y **no reintenta**.
- **No-2xx, timeout o error de red:** ALCRET reintenta hasta **3 veces** con backoff exponencial (máx 900s) y deja el `SyncLog` en `FALLIDO` con el detalle del error.
- Timeout de espera de respuesta: **30 segundos**.

**Recomendación de implementación (patrón "ack temprano"):** responder `2xx` de inmediato y procesar en segundo plano. Si el CRM procesa en línea y tarda más de 30s, ALCRET asumirá fallo y reenviará el mismo `evento_id`; la deduplicación (sección 7) hará que ese reenvío sea inocuo.

---

## 7. Idempotencia y deduplicación (clave anti-choque)

Los reintentos reenvían el **mismo** `evento_id`. El CRM **debe** guardar los `evento_id` ya procesados y, si recibe uno repetido, **responder `2xx` sin volver a aplicar los datos**.

```
if evento_id ya procesado:
    return 200   # no reprocesar, no mutar datos
```

Esto protege contra:
- Reintentos automáticos de Celery.
- Replays (sumado a la ventana de ±5 min).
- Entregas duplicadas por problemas de red.

---

## 8. Identidad de datos — cómo mapear sin chocar

Cada sistema tiene sus propios IDs. **Los UUID de ALCRET (`producto_id`, `almacen_id`) son internos y no deben usarse como llave maestra persistente** en el CRM: cambian si la base se migra, se clona un entorno o se restaura.

| Entidad | Llave canónica para el CRM | Regla |
|---|---|---|
| Producto | `payload.sku_o_vin` | Usar **VIN si existe, sino SKU**. Es el identificador de negocio estable. También se envían `producto_id`, `producto_sku` y `producto_vin` por separado. |
| Almacén | `payload.almacen_codigo` | Valor del campo `nombre` de ALCRET (único). Usarlo como llave natural; `almacen_id` es el UUID interno de referencia. |
| Cliente | `payload.cliente_id` o `payload.email` | `cliente_id` es el UUID interno estable. Si el CRM prefiere identidad por negocio, usar `email`. |
| Cotización | `payload.cotizacion_id` + `payload.folio` | `cotizacion_id` (UUID) y `folio` (único, humano) identifican de forma inequívoca cada cotización. |

**Consecuencia práctica:** si el CRM ya conoce un producto por `sku_o_vin`, debe **actualizarlo**, no crear duplicados.

---

## 9. Semántica y reglas de negocio (evitar choques de datos)

1. **`stock.actualizado` es un snapshot del estado, no un delta.** `cantidad_disponible` es el **total actual** disponible del producto en ese almacén tras el movimiento. El CRM debe **reemplazar** su valor, nunca sumar/restar. Si el CRM necesita el delta, debe calcularlo comparando con su último valor conocido — no aplicarlo.
2. **Los montos y cantidades viajan como strings** (`cantidad_disponible`: decimal normalizado, `monto`: 2 decimales). Evita errores de precisión de flotantes y de tipos. No parsear como `int`; parsear con precisión decimal.
3. **Siempre UTC.** Todos los `timestamp` y fechas son ISO 8601 en UTC. No usar la zona local del servidor para comparar.
4. **`version` de esquema.** Si el sobre o un payload cambia de forma incompatible, se incrementa `version`. El CRM debe **rechazar versiones desconocidas** (`422`) para no interpretar mal datos nuevos.
5. **Procesar en orden.** Para el mismo `sku_o_vin` (y almacén), procesar por `timestamp` y **descartar eventos más viejos** que el último aplicado.
6. **Campos vacíos.** `email`, `telefono`, `rfc`, `sku` pueden llegar vacíos (`""` o `null`). Tratarlos como "sin dato", no como valor inválido de negocio.

---

## 10. Esquemas de eventos

### 10.1 `stock.actualizado`

Emitido ante **todo movimiento de inventario** (entrada, salida o ajuste).

```json
{
  "evento": "stock.actualizado",
  "payload": {
    "movimiento_id": "uuid-del-movimiento",
    "almacen_id": "uuid-del-almacen",
    "almacen_codigo": "Almacen Central",
    "almacen_nombre": "Almacen Central",
    "almacen_ubicacion": "Monterrey, NL",
    "producto_id": "uuid-del-producto",
    "producto_sku": "KW-T680-001",
    "producto_vin": "3HHDMABN7RL000001",
    "sku_o_vin": "3HHDMABN7RL000001",
    "nombre_unidad": "Kenworth T680 2024",
    "cantidad_disponible": "3",
    "cantidad_movimiento": "-1",
    "tipo_movimiento": "SALIDA",
    "motivo": "Venta a Transportes del Norte",
    "costo_unitario": null,
    "realizada_por_email": "almacen@alcret.com",
    "realizada_por_nombre": "María López",
    "fecha_movimiento": "2026-08-07T17:57:00+00:00"
  }
}
```

| Campo | Tipo | Semántica |
|---|---|---|
| `movimiento_id` | string UUID | Identificador interno del movimiento. |
| `almacen_id` | string UUID | Almacén afectado (interno ALCRET). |
| `almacen_codigo` | string | **Llave natural del almacén.** Valor único del campo `nombre`. |
| `almacen_nombre` | string | Nombre del almacén (igual a `almacen_codigo`). |
| `almacen_ubicacion` | string | Ubicación del almacén. Puede ser `""`. |
| `producto_id` | string UUID | Producto afectado (interno ALCRET). |
| `producto_sku` | string | SKU del producto. |
| `producto_vin` | string \| `null` | VIN del producto; `null` si no aplica. |
| `sku_o_vin` | string | **Llave canónica.** VIN si el producto lo tiene; si no, SKU. |
| `nombre_unidad` | string | Nombre del producto/unidad. |
| `cantidad_disponible` | string | **Total actual disponible** tras el movimiento (snapshot, no delta). Decimal normalizado. |
| `cantidad_movimiento` | string | Cantidad del movimiento **con signo** (negativa en `SALIDA`). Útil como referencia, no para acumular (ver regla de snapshot). |
| `tipo_movimiento` | enum string | `ENTRADA` \| `SALIDA` \| `AJUSTE`. |
| `motivo` | string | Motivo/observación del movimiento. Puede ser `""`. |
| `costo_unitario` | string \| `null` | Costo unitario del movimiento; `null` si no se registró. |
| `realizada_por_email` | string \| `null` | Email del usuario que realizó el movimiento. |
| `realizada_por_nombre` | string \| `null` | Nombre del usuario que realizó el movimiento. |
| `fecha_movimiento` | string ISO 8601 UTC | Momento en que se registró el movimiento. |

### 10.2 `cliente.creado` / `cliente.actualizado`

Emitido al crear o editar un cliente.

```json
{
  "evento": "cliente.creado",
  "payload": {
    "cliente_id": "uuid-del-cliente",
    "empresa": "ALCRET S.A.",
    "nombre": "Gonzalo García",
    "email": "gonzalo@alcret.com",
    "telefono": "555-1234",
    "rfc": "GAGJ850101AAA",
    "activo": true,
    "created_at": "2026-08-07T17:57:00+00:00",
    "updated_at": "2026-08-07T17:57:00+00:00"
  }
}
```

| Campo | Tipo | Semántica |
|---|---|---|
| `cliente_id` | string UUID | **Identificador interno estable del cliente.** Úsalo para mapear 1:1 contra el CRM. |
| `empresa` | string | Razón social o empresa. Puede ser `""`. |
| `nombre` | string | Nombre del contacto. |
| `email` | string | Llave natural alternativa. |
| `telefono` | string | Puede ser `""`. |
| `rfc` | string | Puede ser `""`. |
| `activo` | boolean | Si el cliente está activo en ALCRET. |
| `created_at` | string ISO 8601 UTC | Fecha de creación. |
| `updated_at` | string ISO 8601 UTC | Fecha de última modificación. |

Regla de negocio: es el **mismo** registro actualizado (mismo email) en `cliente.actualizado`. Si el CRM ya lo tiene, actualiza; si no, crea.

### 10.3 `cotizacion.creada`

Emitido al crear una cotización.

```json
{
  "evento": "cotizacion.creada",
  "payload": {
    "cotizacion_id": "uuid-de-la-cotizacion",
    "folio": "COT-00001",
    "cliente_id": "uuid-del-cliente",
    "cliente_email": "gonzalo@alcret.com",
    "cliente_nombre": "Gonzalo García",
    "cliente_empresa": "ALCRET S.A.",
    "monto": "1250000.00",
    "esquema": "CREDITO",
    "estado": "ENVIADA",
    "observaciones": "Entrega en 15 días",
    "unidad_interes_id": "uuid-de-la-unidad",
    "unidad_interes_sku": "KW-T680-001",
    "unidad_interes_vin": "3HHDMABN7RL000001",
    "unidad_interes": "3HHDMABN7RL000001",
    "unidad_interes_nombre": "Kenworth T680 2024",
    "vendedor_id": "uuid-del-vendedor",
    "vendedor_email": "ventas@alcret.com",
    "vendedor_nombre": "Pedro Ramírez",
    "created_at": "2026-08-07T17:57:00+00:00",
    "updated_at": "2026-08-07T17:57:00+00:00"
  }
}
```

| Campo | Tipo | Semántica |
|---|---|---|
| `cotizacion_id` | string UUID | **Identificador interno estable de la cotización.** |
| `folio` | string | Folio único de la cotización (humano). |
| `cliente_id` | string UUID | Identificador interno del cliente. |
| `cliente_email` | string | Email del cliente. |
| `cliente_nombre` | string | Nombre del contacto. |
| `cliente_empresa` | string | Razón social del cliente. Puede ser `""`. |
| `monto` | string | Total con 2 decimales. |
| `esquema` | enum string | `CONTADO` \| `CREDITO` \| `ARRENDAMIENTO`. |
| `estado` | enum string | `ENVIADA` \| `GANADA` \| `PERDIDA`. |
| `observaciones` | string | Observaciones de la cotización. Puede ser `""`. |
| `unidad_interes_id` | string UUID | Identificador interno de la unidad cotizada. |
| `unidad_interes_sku` | string | SKU de la unidad. |
| `unidad_interes_vin` | string \| `null` | VIN de la unidad; `null` si no aplica. |
| `unidad_interes` | string | **Llave canónica de producto** (`vin` o `sku`). |
| `unidad_interes_nombre` | string | Nombre de la unidad. |
| `vendedor_id` | string UUID | Identificador interno del vendedor. |
| `vendedor_email` | string | Email del vendedor. |
| `vendedor_nombre` | string | Nombre del vendedor. |
| `created_at` | string ISO 8601 UTC | Fecha de creación. |
| `updated_at` | string ISO 8601 UTC | Fecha de última modificación. |

---

## 11. Estructura de la app

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

## 12. Modelos relevantes

### 12.1 `SyncLog` — bitácora de envíos (primera pantalla al conectar)

| Campo | Tipo | Descripción |
|---|---|---|
| `evento` | CharField | Nombre del evento enviado. |
| `estado` | CharField | `PENDIENTE` / `ENVIADO` / `FALLIDO`. |
| `payload` | JSONField | Cuerpo del evento. |
| `respuesta` | JSONField | Respuesta del CRM (status + body) o error. |
| `intentos` | IntegerField | Número de reintentos realizados. |
| `created_at` / `updated_at` | DateTimeField | Trazabilidad. |

En el admin es de **solo lectura** (`has_change_permission=False`, `has_delete_permission=False`).

### 12.2 `ClaveCRM` — rotación de claves HMAC

| Campo | Tipo | Descripción |
|---|---|---|
| `clave_publica` | CharField (64, unique) | Identificador público de la clave. |
| `hash_clave` | CharField (128) | SHA-256 hex del secreto (nunca se guarda en claro). |
| `activa` | BooleanField | Solo una clave activa a la vez. |
| `expira_en` | DateTimeField | Fecha de expiración. |
| `rotada_en` | DateTimeField | Fecha en que fue reemplazada. |

Reglas: al crear una clave nueva con `activa=True`, la anterior se desactiva automáticamente. La rotación queda auditada en `AuditLog` (evento `SYNC_CRM`).

> **Nota:** `WebhookCRM` existe para administrar webhooks, pero el envío real hoy se controla por las variables `CRM_WEBHOOK_URL` y `CRM_HMAC_SECRET`.

---

## 13. Tareas Celery

### 13.1 `enviar_evento_crm(evento, payload)`

1. Crea un `SyncLog` en `PENDIENTE`.
2. Construye el sobre `{version, evento_id, evento, payload, timestamp}` y firma el body con HMAC-SHA256.
3. Hace `POST` con timeout de 30s.
4. Éxito → `ENVIADO` (guarda la respuesta). Fallo → `FALLIDO` + hasta 3 reintentos con backoff (máx 900s).

### 13.2 `verificar_expiracion_claves()`

Tarea programada (Celery Beat, cada 24 h — `config/settings/base.py:261-266`). Alerta claves que expiran en menos de 7 días y desactiva las vencidas.

---

## 14. Señales (cuándo se emite cada evento)

| Señal | Disparada por | Evento emitido |
|---|---|---|
| `publicar_movimiento_al_crm` | `post_save` de `Movimiento` (solo `created`) | `stock.actualizado` |
| `publicar_cliente_al_crm` | `post_save` de `Cliente` | `cliente.creado` / `cliente.actualizado` |
| `publicar_cotizacion_al_crm` | `post_save` de `Cotizacion` | `cotizacion.creada` |
| `registrar_rotacion_clave_crm` | `post_save` de `ClaveCRM` (solo `created`) | Auditoría `SYNC_CRM` (no se envía al webhook) |

Las señales respetan `CRM_WEBHOOK_URL`: si no está configurada, hacen `skip`.

---

## 15. Monitoreo y depuración

1. **Admin** → `/admin/integracion/synclog/`: estado, intentos y respuesta de cada envío.
2. **Logs del worker Celery**: `docker compose -f docker-compose.prod.yml logs worker -f`.
3. **AuditLog**: rotaciones de clave en `/admin/auditoria/`.

---

## 16. Estado actual y pendientes

- ✅ Envío de eventos a webhook con firma HMAC-SHA256, sobre versionado, `evento_id` para idempotencia, reintentos y bitácora.
- ✅ Eventos emitidos: `stock.actualizado`, `cliente.creado`, `cliente.actualizado`, `cotizacion.creada`.
- ✅ Payloads completos: IDs internos (`movimiento_id`, `producto_id`, `almacen_id`, `cliente_id`, `cotizacion_id`, `vendedor_id`, `unidad_interes_id`), llaves de negocio (`sku_o_vin`, `almacen_codigo`, `folio`) y metadatos (fechas, usuarios, montos).
- ✅ Rotación y expiración de claves CRM. Auditoría de rotaciones.
- ⬜ **`urls.py` vacío**: no hay endpoint de entrada para que el CRM llame a ALCRET (flujo unidireccional). La arquitectura contempla futuro `orden.confirmada` / `orden.cancelada`.
- ⬜ `WebhookCRM` aún no participa en el envío (gobiernan las variables de entorno).
- ⬜ La señal de `stock.actualizado` toma el stock con `stocks.filter(almacen=...).first()`; con la constraint `unique_together` de `Stock` (producto+almacén) es seguro, pero se recomienda `get()` con manejo de `DoesNotExist` al tocar ese código.

---

## 17. Checklist de conexión (para el desarrollador del CRM)

- [ ] Acordar un **secreto compartido** → `CRM_HMAC_SECRET` (mismo valor en ambos lados).
- [ ] Proporcionar la **URL del webhook** → `CRM_WEBHOOK_URL`.
- [ ] Exponer `POST` en esa URL que:
  - valide `X-Signature` con HMAC-SHA256 del body crudo (`compare_digest`);
  - valide la ventana de ±5 min (`X-Timestamp` / `body.timestamp`);
  - deduplique por `evento_id` (responder `2xx` sin reprocesar repetidos);
  - responda `2xx` en menos de 30s (patrón ack temprano);
  - rechace `version` desconocido con `422`;
  - aplique `stock.actualizado` como **snapshot** (reemplazar, no sumar/restar).
- [ ] Mapear productos por `sku_o_vin` (o `producto_id`), almacenes por `almacen_codigo`, clientes por `cliente_id`/`email` y cotizaciones por `cotizacion_id`/`folio`.
- [ ] Verificar los envíos en `/admin/integracion/synclog/`.
- [ ] Pruebas en vivo: crear/editar un cliente (`cliente.*`), una cotización (`cotizacion.creada`) o registrar un movimiento (`stock.actualizado`).

---

## 18. Glosario

| Término | Definición |
|---|---|
| `evento_id` | Identificador único del evento; clave de deduplicación. |
| Snapshot | Valor de estado total en un momento dado; se reemplaza, no se acumula. |
| Llave canónica | Identificador de negocio estable para mapear entre sistemas (`sku_o_vin`, `email`). |
| Sobre (wrapper) | Campos comunes de todo evento: `version`, `evento_id`, `evento`, `payload`, `timestamp`. |
