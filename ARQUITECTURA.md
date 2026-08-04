# ARQUITECTURA DEL SISTEMA — Inventario PWA
> Documento de contexto persistente para agentes de desarrollo.
> Versión 1.0 — Leer completo antes de generar cualquier código.

---

## Propósito de este documento

Este archivo define el esqueleto técnico del proyecto. Ningún agente debe modificar decisiones de arquitectura sin justificación explícita. Si una tarea parece requerir salirse de esta estructura, el agente debe pausar y consultar antes de proceder.

---

## Stack tecnológico — decisiones fijas

| Capa | Tecnología | Justificación |
|---|---|---|
| Backend | Django 4.2+ (LTS) | ORM, auth, permisos, admin nativos. Sin REST frameworks externos salvo DRF para la integración con CRM |
| Frontend | Alpine.js 3.x | Reactividad declarativa en templates Django. Sin SPA, sin build step |
| Tooling | Ruff + isort + pytest | Configuración unificada en pyproject.toml |
| Base de datos | PostgreSQL 15+ | Transacciones ACID obligatorias para movimientos de inventario |
| Caché / cola | Redis + Celery | Tareas asíncronas (correos, sync CRM, reportes) |
| Estilos | Tailwind CSS (CLI compilado) | Compilación estática vía `npm run build:css` → `static/css/tailwind.css`. Sin CDN en runtime |
| Despliegue | Gunicorn + Nginx | Separación de responsabilidades. Nginx sirve estáticos y termina TLS |
| PWA | Service Worker + Manifest | Caché offline de vistas de solo lectura. Push notifications futuro |

**Regla de oro:** No agregar librerías externas sin actualizar este documento y justificar el motivo.

| Librería adicional | Justificación |
|---|---|
| Chart.js 4.x (CDN) | Visualización de KPIs y gráficos en dashboard y finanzas. Sin build step, CDN compatible con Alpine.js |
| openpyxl | Exportación de reportes a Excel nativo (.xlsx) para distribución a stakeholders |

---

## Arquitectura por capas

```
┌─────────────────────────────────────────────────────────┐
│  CAPA 1 — Cliente PWA                                   │
│  Alpine.js · Service Worker · JWT en HttpOnly   │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS / TLS 1.2+
┌────────────────────▼────────────────────────────────────┐
│  CAPA 2 — Seguridad (middleware stack)                  │
│  Autenticación · RBAC · Rate limiting · CSP headers     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  CAPA 3 — Django Core                                   │
│  Views/API · Serializers · Middleware · Signals         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  CAPA 4 — Módulos funcionales                           │
│  inventario · auditoria · metricas · usuarios · alertas · finanzas │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼──────────────────┐  ┌─────────────┐
│  CAPA 5 — Datos                       │◄►│  CRM externo│
│  PostgreSQL · Redis · Audit log       │  │  REST+HMAC  │
└───────────────────────────────────────┘  └─────────────┘
```

---

## Estructura de directorios — obligatoria

```
proyecto/
├── config/                  # Configuración Django (settings, urls, wsgi)
│   ├── settings/
│   │   ├── base.py          # Settings comunes
│   │   ├── development.py   # DEBUG=True, SQLite permitido solo aquí
│   │   ├── production.py    # Sin DEBUG, vars desde entorno
│   │   └── test_pg.py       # Tests contra PostgreSQL (pytest --ds=...)
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   ├── usuarios/            # Modelo de usuario custom, roles, RBAC
│   ├── inventario/          # Productos, entradas, salidas, ajustes
│   ├── auditoria/           # AuditLog inmutable, señales
│   ├── metricas/            # KPIs, dashboards, reportes
│   ├── integracion/         # Webhooks CRM, cola de sync, rotación de claves
│   ├── alertas/             # Alertas de stock bajo, configuración de umbrales
│   ├── finanzas/            # Facturas COMPRA/VENTA, dashboard financiero, subida de PDF/XML
│   └── shared/              # Middleware, servicios compartidos, value objects
│
├── templates/               # Templates Django globales
│   ├── base.html            # Layout principal con Alpine.js
│   ├── components/          # Fragmentos reutilizables
│   └── finanzas/            # Dashboard financiero y formulario de subida de facturas
│
├── static/
│   ├── js/                  # Alpine.js components y service worker
│   └── css/                 # Tailwind output
│
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
├── pyproject.toml           # Configuración de Ruff, isort, pytest
└── ARQUITECTURA.md          # Este archivo — fuente de verdad
```

**Regla:** Cada app en `apps/` es un módulo autónomo. No importar modelos entre apps directamente — usar señales o servicios en `apps/shared/services.py`.

---

## Modelo de usuarios y roles — RBAC

### Modelo custom (obligatorio, no usar User de Django directamente)

```python
# apps/usuarios/models.py
class Usuario(AbstractBaseUser, PermissionsMixin):
    email         = EmailField(unique=True)          # login por email, no username
    nombre        = CharField(max_length=150)
    rol           = CharField(choices=ROL_CHOICES)
    activo        = BooleanField(default=True)
    fecha_creacion = DateTimeField(auto_now_add=True)
    ultimo_acceso  = DateTimeField(null=True)
    intentos_fallidos = IntegerField(default=0)      # para bloqueo progresivo
    bloqueado_hasta   = DateTimeField(null=True)     # NIST AC-7

    USERNAME_FIELD = 'email'
```

### Matriz de permisos por rol

| Acción | Administrador | Vendedor | Almacenista |
|---|---|---|---|
| Ver stock completo | ✅ | ✅ | ✅ |
| Registrar entrada | ✅ | ❌ | ✅ |
| Registrar salida | ✅ | ✅ | ✅ |
| Hacer ajuste / merma | ✅ | ❌ | ❌ |
| Ver auditoría completa | ✅ | ❌ | ❌ |
| Ver métricas y KPIs | ✅ | ✅ parcial | ❌ |
| Gestionar usuarios | ✅ | ❌ | ❌ |
| Exportar reportes | ✅ | ✅ | ✅ |
| Configurar integración CRM | ✅ | ❌ | ❌ |
| Ver dashboard finanzas | ✅ | ✅ | ✅ |
| Subir factura COMPRA | ✅ | ❌ | ✅ |
| Subir factura VENTA | ✅ | ✅ | ❌ |

**Implementación:** Usar `django-guardian` para permisos a nivel de objeto cuando se necesite granularidad por producto o almacén. Los permisos de rol se validan en cada view con el decorador `@permission_required` o mixin `PermissionRequiredMixin`.

---

## Arquitectura de seguridad — controles NIST SP 800-53

### Controles implementados y su ubicación en código

| Control NIST | Descripción | Dónde se implementa |
|---|---|---|---|
| `AC-2` | Gestión de cuentas | `apps/usuarios/` — ciclo de vida completo |
| `AC-3` | Enforcement de acceso | `_check_movimiento_permission` en `apps/inventario/views.py` + `PermissionRequiredMixin` + `@permission_required` en vistas de usuario y exportaciones |
| `AC-7` | Bloqueo por intentos fallidos | `django-axes` + campo `bloqueado_hasta` en Usuario |
| `AC-12` | Terminación de sesión | `django.contrib.sessions` + `invalidar_sesiones_usuario()` al cambiar password (vista admin `UsuarioUpdateView` y `AuditPasswordResetConfirmView`) |
| `AU-2` | Eventos auditables | `apps/auditoria/` — lista de eventos definida abajo |
| `AU-9` | Protección del audit log | Tabla PostgreSQL con solo INSERT (sin UPDATE/DELETE) + `PermissionError` en ORM |
| `AU-12` | Generación de registros | Señales Django en cada operación de inventario + auditoría de login fallidos |
| `IA-2` | Identificación y autenticación | Login por email + `AuditPasswordResetForm` que valida `activo=True` |
| `IA-5(1)` | Política de contraseñas | `AUTH_PASSWORD_VALIDATORS` + `django-pwned-passwords` + mínimo 12 caracteres |
| `SC-8` | Confidencialidad en tránsito | TLS 1.2+ obligatorio, `EMAIL_USE_TLS = True` |
| `SC-13` | Criptografía aprobada | `Argon2` para hashes, `secrets` para tokens, AES-256 en reposo |
| `SC-23` | Autenticidad de sesión | `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE=Strict`, cierre al cerrar navegador |
| `SC-23(1)` | Content Security Policy | `SecurityHeadersMiddleware` en `apps/shared/middleware.py` — CSP permite CDN de Alpine.js/Chart.js (cdn.jsdelivr.net) y Google Fonts (fonts.googleapis.com, fonts.gstatic.com), `'unsafe-inline'` y `'unsafe-eval'` para Alpine.js, `frame-ancestors 'none'`, `base-uri 'self'` |
| `SI-10` | Validación de entradas | Validadores Django en todos los serializers y forms + `csrf_middleware` presente + `SECURE_CONTENT_TYPE_NOSNIFF` |

### Configuración de seguridad base — settings/base.py

```python
# Contraseñas
PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher"]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "...MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "...CommonPasswordValidator"},
    {"NAME": "apps.shared.validators.PwnedPasswordValidator"},  # HIBP k-anonymity (red, fail-safe)
]
PASSWORD_RESET_TIMEOUT = 900  # 15 minutos — NIST IA-5(1)(d)

# Sesiones
SESSION_COOKIE_HTTPONLY  = True
SESSION_COOKIE_SECURE    = True   # Solo en producción
SESSION_COOKIE_SAMESITE  = "Strict"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CSRF y headers
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE   = True
SECURE_BROWSER_XSS_FILTER       = True
SECURE_CONTENT_TYPE_NOSNIFF      = True
X_FRAME_OPTIONS                  = "DENY"
SECURE_HSTS_SECONDS              = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS   = True

# Rate limiting (django-axes)
AXES_FAILURE_LIMIT       = 5
AXES_COOLOFF_TIME        = 1   # hora
AXES_LOCKOUT_PARAMETERS  = ["ip_address", "username"]
```

### Middleware de seguridad — apps/shared/middleware.py

```python
class SecurityHeadersMiddleware:
    """Agrega headers de seguridad a toda respuesta HTTP.

    - Content-Security-Policy: restringe fuentes de scripts, estilos e imágenes
    - X-Content-Type-Options: previene MIME sniffing
    - X-Frame-Options: previene clickjacking
    - Referrer-Policy: control de referencias
    - Permissions-Policy: restringe APIs del navegador
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "img-src 'self' data:; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self';"
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
```

### Invalidación de sesiones — apps/shared/middleware.py

```python
def invalidar_sesiones_usuario(user_id):
    """Borra todas las sesiones activas de un usuario (NIST AC-12).

    Se llama desde:
      - UsuarioUpdateView   (admin cambia password de otro usuario)
      - AuditPasswordResetConfirmView (usuario completa reset de password)
    """
    from django.contrib.sessions.models import Session
    from django.contrib.auth import get_user_model
    User = get_user_model()
    sessions = Session.objects.filter(
        expire_date__gte=timezone.now()
    ).prefetch_related("session_key")
    for session in sessions:
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) == str(user_id):
            session.delete()
```

### Registro en MIDDLEWARE — config/settings/base.py

```python
MIDDLEWARE = [
    # ... Django built-in middlewares ...
    "apps.shared.middleware.SecurityHeadersMiddleware",  # CSP y otros headers
]
```

---

## Flujo de recuperación de contraseña

El flujo usa vistas personalizadas en `apps/auditoria/auth_views.py` que extienden las nativas de Django:

| Vista nativa | Vista personalizada | Cambio clave |
|---|---|---|
| `PasswordResetForm` | `AuditPasswordResetForm` | Usa `activo=True` en lugar de `is_active` (modelo personalizado sin ese campo). Crea `AuditLog.PASSWORD_RESET` al enviar el correo. |
| `PasswordResetConfirmView` | `AuditPasswordResetConfirmView` | Llama a `invalidar_sesiones_usuario()` **antes** de cambiar la contraseña. Crea `AuditLog.PASSWORD_RESET` al completar. |

Reglas del flujo:

1. **Respuesta genérica siempre** — el sistema nunca confirma si el correo existe (`SC-8`, prevención de user enumeration)
2. **Token de un solo uso** — al usarse o al cambiar la contraseña, queda inválido automáticamente
3. **Expiración de 15 minutos** — `PASSWORD_RESET_TIMEOUT = 900`
4. **Correo cifrado** — SMTP con TLS, nunca port 25 sin cifrado
5. **Invalidar sesiones activas** — al confirmar el cambio, limpiar todas las sesiones del usuario vía `invalidar_sesiones_usuario()` ✅ Implementado
6. **Notificación de cambio** — enviar correo de confirmación al usuario (detección de compromiso, `AC-2`)
7. **Registrar en audit log** — evento `PASSWORD_RESET_REQUESTED` y `PASSWORD_RESET_COMPLETED` con IP y timestamp ✅ Implementado

---

## Audit log — diseño de tabla inmutable

```python
# apps/auditoria/models.py
class AuditLog(models.Model):
    EVENTOS = [
        ("ENTRADA",            "Entrada de inventario"),
        ("SALIDA",             "Salida de inventario"),
        ("AJUSTE",             "Ajuste / merma"),
        ("LOGIN_OK",           "Inicio de sesión exitoso"),
        ("LOGIN_FAIL",         "Intento de sesión fallido"),
        ("PASSWORD_RESET",     "Recuperación de contraseña"),
        ("PASSWORD_CHANGED",   "Contraseña cambiada"),
        ("USUARIO_CREADO",     "Usuario creado"),
        ("USUARIO_DESACTIVADO","Usuario desactivado"),
        ("PERMISO_CAMBIADO",   "Permiso modificado"),
        ("EXPORTACION",        "Exportación de datos"),
        ("SYNC_CRM",           "Sincronización con CRM"),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4)
    evento      = models.CharField(max_length=30, choices=EVENTOS)
    usuario     = models.ForeignKey(Usuario, null=True, on_delete=models.SET_NULL)
    ip_address  = models.GenericIPAddressField()
    timestamp   = models.DateTimeField(auto_now_add=True)   # inmutable
    datos       = models.JSONField()        # snapshot del estado anterior y nuevo
    hash_previo = models.CharField(max_length=64)  # encadenamiento para detección de tampering

    class Meta:
        ordering = ["-timestamp"]

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise PermissionError("AuditLog es inmutable.")  # NIST AU-9
        super().save(*args, **kwargs)
```

**En PostgreSQL** revocar UPDATE y DELETE a nivel de base de datos:
```sql
REVOKE UPDATE, DELETE ON auditoria_auditlog FROM app_user;
```

### Encadenamiento y verificación de integridad

- Al insertar, el `hash_previo` se calcula del último registro leído con `order_by("-timestamp", "-id")`, serializado con `pg_advisory_xact_lock` (clave `_AUDITLOG_CHAIN_LOCK_KEY`) para evitar bifurcaciones de la cadena bajo escrituras concurrentes. En SQLite la serialización de escritores la maneja la propia base de datos.
- `verificar_integridad()` busca el predecesor con la misma ordenación `(timestamp, id)`: `Q(timestamp__lt=...) | Q(timestamp=..., id__lt=...)`. Así, dos registros que compartan el mismo timestamp (mismo microsegundo) se desempatan por `id`, alineado con lo que vio `save()` al insertar.
- `verificar_cadena()` (classmethod) recorre toda la tabla ordenada por `("timestamp", "id")` y devuelve `{"valida", "total", "errores"}`.

---

## Integración con CRM

### Contrato de comunicación (a definir con el equipo CRM)

- **Protocolo:** REST sobre HTTPS
- **Autenticación entre sistemas:** HMAC-SHA256 en header `X-Signature`
- **Dirección:** Bidireccional con webhooks
- **Entrega garantizada:** Cola Celery con reintento exponencial (3 intentos, backoff 60s/300s/900s)

### Rotación de claves HMAC

El modelo `ClaveCRM` en `apps/integracion/models.py` gestiona el ciclo de vida de las claves HMAC:

| Campo | Tipo | Propósito |
|---|---|---|
| `clave_publica` | `CharField(unique=True)` | Identificador público de la clave |
| `hash_clave` | `CharField(max_length=128)` | SHA-256 del secreto (nunca se almacena el secreto en texto plano) |
| `activa` | `BooleanField(default=True)` | Clave en uso actualmente |
| `expira_en` | `DateTimeField` | Fecha de expiración |

**Regla:** Al crear una nueva clave activa, las anteriores se desactivan automáticamente. La rotación se registra en el AuditLog.

**Comando de gestión:** `python manage.py rotar_clave_crm --dias-expiracion 90`

**Tarea programada:** `verificar_expiracion_claves` (Celery Beat, cada 24h) desactiva claves vencidas y alerta sobre claves próximas a expirar.

### Eventos que el inventario publica al CRM

| Evento | Cuándo | Datos enviados |
|---|---|---|
| `stock.actualizado` | Toda entrada/salida/ajuste | producto_id, cantidad_nueva, almacen_id |
| `stock.bajo_minimo` | Al bajar del umbral | producto_id, cantidad_actual, umbral |
| `producto.creado` | Al crear producto | producto completo serializado |

### Eventos que el CRM envía al inventario

| Evento | Cuándo | Acción en inventario |
|---|---|---|
| `orden.confirmada` | Orden aprobada en CRM | Crear salida automática |
| `orden.cancelada` | Orden cancelada | Revertir reserva de stock |

---

---

## Módulo de alertas — apps/alertas

### Modelos

| Modelo | Propósito |
|---|---|
| `AlertaConfig` | Configuración de umbrales por producto (opcional, usa `stock_minimo` por defecto) |
| `Alerta` | Instancia de alerta generada (stock bajo), con estados PENDIENTE / VISTA / RESUELTA |

### Flujo

1. `Movimiento.post_save` → `auditar_movimiento()` (inventario) actualiza el stock y emite la señal custom `stock_actualizado` **después** de confirmar la actualización.
2. `apps/alertas/signals.py` escucha `stock_actualizado` y `verificar_stock_bajo()` lee `stock.cantidad` (valor final) vs `stock_minimo`.
3. Si el stock está por debajo del umbral, crea un registro `Alerta` con estado `PENDIENTE`.
4. El usuario puede ver las alertas en `/alertas/` y marcarlas como resueltas.

**Nota de diseño:** alertas NO escucha `post_save` de `Movimiento` directamente. Escuchar la señal custom `stock_actualizado` garantiza que el stock ya fue actualizado y evita depender del orden de carga de `INSTALLED_APPS` o de re-agregar stock en cada movimiento.

---

## Value Objects — apps/shared/value_objects.py

Objetos valor inmutables para conceptos de dominio:

| Objeto | Validación |
|---|---|
| `PrecioVenta` | Decimal positivo, máximo 999,999,999.99 |
| `CantidadStock` | Entero no negativo |
| `SKU` | Patrón `^[A-Z0-9]{3,20}(-[A-Z0-9]{1,10})?$` |
| `EmailAddress` | Validación de formato email |

---

## Service Layer

Cada app de negocio expone servicios en `services.py` que encapsulan lógica de dominio:

| Archivo | Servicios |
|---|---|
| `apps/inventario/services.py` | `registrar_movimiento()`, `stock_bajo_minimo()`, `get_o_crear_stock_bloqueado()` |
| `apps/integracion/services.py` | `registrar_evento_auditoria()`, `crm_configurado()` |
| `apps/shared/services.py` | `ejecutar_en_transaccion()`, `registrar_audit_log()` |
| `apps/finanzas/services.py` | (reservado para lógica de facturación y conciliación) |

**`get_o_crear_stock_bloqueado(producto, almacen)`** usa `select_for_update().get_or_create()` dentro de la señal de inventario. En PostgreSQL, `get_or_create` bajo `select_for_update` puede lanzar `IntegrityError` en condiciones de carrera; el helper reintenta una vez para volver a leer la fila recién creada.

**Señales entre apps:**

| Señal | Emisor | Consumidor | Propósito |
|---|---|---|---|
| `stock_actualizado` (custom) | `apps/inventario/signals.py` | `apps/alertas/signals.py` | Avisar que el stock ya fue actualizado y confirmado; emitida tras `auditar_movimiento()`. sender=`Movimiento`, kwargs: `stock`, `movimiento` |

---

## Testing

Suite con `pytest` (config en `pyproject.toml`). Los tests corren por defecto contra SQLite (settings `development`); la validación real contra PostgreSQL se hace con un settings dedicado.

```bash
# Suite completa en SQLite (rápida, default)
python -m pytest -q --no-header

# Suite completa contra PostgreSQL (validar concurrencia y features de PG)
docker compose up -d postgres
$env:DB_PASSWORD="..."  # u otras variables según tu .env
python -m pytest --ds=config.settings.test_pg -q --no-header

# Lint
python -m ruff check .
```

**Por qué correr contra PG:** los advisory locks (`pg_advisory_xact_lock`), `select_for_update` y el retry por `IntegrityError` de `get_o_crear_stock_bloqueado()` solo se ejercitan de verdad en PostgreSQL. La suite SQLite es el quick check diario; la suite PG es el gate previo a producción.

> **CSP en desarrollo:** la CSP usa `'unsafe-inline'` y `'unsafe-eval'` porque Tailwind (CDN play) y Alpine.js los requieren sin build step. Antes de producción, migrar a Tailwind compilado + Alpine empaquetado y **eliminar** `unsafe-inline`/`unsafe-eval` del `script-src` (NIST SC-23(1)).

---

## Reglas para agentes de desarrollo

Estas reglas son no negociables. Si una tarea viola alguna, el agente debe detenerse.

1. **No cambiar el modelo `Usuario`** sin actualizar la matriz de permisos en este documento.
2. **Todo movimiento de inventario** (entrada, salida, ajuste) debe disparar una señal que escriba al `AuditLog`. Sin excepciones.
3. **No usar `request.user.is_staff`** para verificar permisos — usar el campo `rol` y los permisos de `django-guardian`.
4. **No almacenar secretos en código** — usar variables de entorno. El archivo `.env` nunca se sube al repositorio.
5. **No desactivar `CSRF_COOKIE_SECURE`** en producción bajo ninguna circunstancia.
6. **Toda vista que reciba datos externos** (formularios, API, webhooks) debe tener validación explícita en el serializer o form. No confiar en datos del cliente.
7. **Los tokens de integración CRM** se rotan cada 90 días. Registrar la rotación en el audit log.
8. **No usar `print()` para debug en producción** — usar `logging` con nivel `WARNING` mínimo en producción.
9. **Las migraciones de base de datos** son irreversibles en producción. Toda migración debe revisarse manualmente antes de aplicarse.
10. **El `AuditLog` no se toca.** Ni para corregir errores. Un registro incorrecto se anula con un nuevo registro de tipo corrección — nunca editando el original.

---

## Dependencias clave — requirements/base.txt

```
Django>=4.2,<5.0
psycopg2-binary
django-axes              # bloqueo por intentos fallidos (AC-7)
django-guardian          # permisos a nivel de objeto
argon2-cffi              # hasher Argon2
celery                   # tareas asíncronas
redis                    # broker Celery + caché
djangorestframework      # solo para endpoints de integración CRM
openpyxl                 # exportación de reportes Excel
```

---

*Documento generado como contrato técnico del proyecto. Actualizar con cada decisión arquitectónica relevante.*
