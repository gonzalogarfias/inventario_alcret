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
| Base de datos | PostgreSQL 15+ | Transacciones ACID obligatorias para movimientos de inventario |
| Caché / cola | Redis + Celery | Tareas asíncronas (correos, sync CRM, reportes) |
| Estilos | Tailwind CSS (CDN play) | Sin proceso de build en desarrollo. En producción: CLI de Tailwind |
| Despliegue | Gunicorn + Nginx | Separación de responsabilidades. Nginx sirve estáticos y termina TLS |
| PWA | Service Worker + Manifest | Caché offline de vistas de solo lectura. Push notifications futuro |

**Regla de oro:** No agregar librerías externas sin actualizar este documento y justificar el motivo.

| Librería adicional | Justificación |
|---|---|
| Chart.js 4.x (CDN) | Visualización de KPIs y gráficos en dashboard. Sin build step, CDN compatible con Alpine.js |
| openpyxl | Exportación de reportes a Excel nativo (.xlsx) para distribución a stakeholders |

---

## Arquitectura por capas

```
┌─────────────────────────────────────────────────────────┐
│  CAPA 1 — Cliente PWA                                   │
│  Alpine.js · HTMX · Service Worker · JWT en HttpOnly    │
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
│  inventario · auditoria · metricas · usuarios · alertas │
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
│   │   └── production.py    # Sin DEBUG, vars desde entorno
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   ├── usuarios/            # Modelo de usuario custom, roles, RBAC
│   ├── inventario/          # Productos, entradas, salidas, ajustes
│   ├── auditoria/           # AuditLog inmutable, señales
│   ├── metricas/            # KPIs, dashboards, reportes
│   └── integracion/         # Webhooks CRM, cola de sync
│
├── templates/               # Templates Django globales
│   ├── base.html            # Layout principal con Alpine.js
│   └── components/          # Fragmentos reutilizables (HTMX targets)
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

**Implementación:** Usar `django-guardian` para permisos a nivel de objeto cuando se necesite granularidad por producto o almacén. Los permisos de rol se validan en cada view con el decorador `@permission_required` o mixin `PermissionRequiredMixin`.

---

## Arquitectura de seguridad — controles NIST SP 800-53

### Controles implementados y su ubicación en código

| Control NIST | Descripción | Dónde se implementa |
|---|---|---|
| `AC-2` | Gestión de cuentas | `apps/usuarios/` — ciclo de vida completo |
| `AC-7` | Bloqueo por intentos fallidos | `django-axes` + campo `bloqueado_hasta` en Usuario |
| `AC-12` | Terminación de sesión | `django.contrib.sessions` + invalidar al cambiar contraseña |
| `AU-2` | Eventos auditables | `apps/auditoria/` — lista de eventos definida abajo |
| `AU-9` | Protección del audit log | Tabla PostgreSQL con solo INSERT (sin UPDATE/DELETE) |
| `AU-12` | Generación de registros | Señales Django en cada operación de inventario |
| `IA-2` | Identificación y autenticación | Login por email + MFA opcional para admin |
| `IA-5(1)` | Política de contraseñas | `AUTH_PASSWORD_VALIDATORS` + `django-pwned-passwords` |
| `SC-8` | Confidencialidad en tránsito | TLS 1.2+ obligatorio, `EMAIL_USE_TLS = True` |
| `SC-13` | Criptografía aprobada | `Argon2` para hashes, `secrets` para tokens, AES-256 en reposo |
| `SC-23` | Autenticidad de sesión | `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SECURE`, rotación de keys |
| `SI-10` | Validación de entradas | Validadores Django en todos los serializers y forms |

### Configuración de seguridad base — settings/base.py

```python
# Contraseñas
PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher"]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "...MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "...CommonPasswordValidator"},
    {"NAME": "django_pwned_passwords.password_validation.PwnedPasswordValidator"},
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

---

## Flujo de recuperación de contraseña

El flujo usa el `PasswordResetTokenGenerator` nativo de Django con las siguientes reglas estrictas:

1. **Respuesta genérica siempre** — el sistema nunca confirma si el correo existe (`SC-8`, prevención de user enumeration)
2. **Token de un solo uso** — al usarse o al cambiar la contraseña, queda inválido automáticamente
3. **Expiración de 15 minutos** — `PASSWORD_RESET_TIMEOUT = 900`
4. **Correo cifrado** — SMTP con TLS, nunca port 25 sin cifrado
5. **Invalidar sesiones activas** — al confirmar el cambio, limpiar todas las sesiones del usuario
6. **Notificación de cambio** — enviar correo de confirmación al usuario (detección de compromiso, `AC-2`)
7. **Registrar en audit log** — evento `PASSWORD_RESET_REQUESTED` y `PASSWORD_RESET_COMPLETED` con IP y timestamp

```python
# Señales que deben dispararse (apps/auditoria/signals.py)
# password_reset_requested  → IP, email, timestamp
# password_reset_completed  → IP, usuario_id, timestamp
# password_changed_by_admin → admin_id, usuario_id, timestamp
```

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

---

## Integración con CRM

### Contrato de comunicación (a definir con el equipo CRM)

- **Protocolo:** REST sobre HTTPS
- **Autenticación entre sistemas:** HMAC-SHA256 en header `X-Signature`
- **Dirección:** Bidireccional con webhooks
- **Entrega garantizada:** Cola Celery con reintento exponencial (3 intentos, backoff 60s/300s/900s)

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
# django-pwned-passwords   # (temporalmente fuera: incompatible con Django 4.2 — usar ugettext obsoleto. Revisar en próxima actualización)
argon2-cffi              # hasher Argon2
celery                   # tareas asíncronas
redis                    # broker Celery + caché
djangorestframework      # solo para endpoints de integración CRM
openpyxl                 # exportación de reportes Excel
```

---

*Documento generado como contrato técnico del proyecto. Actualizar con cada decisión arquitectónica relevante.*
