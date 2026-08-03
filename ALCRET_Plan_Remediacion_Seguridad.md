# ALCRET Inventario — Plan de Remediación de Seguridad y Calidad de Código

**Alcance revisado:** `usuarios`, `auditoria`, `inventario`, `metricas`, `shared`, `integracion`, `finanzas`, `config/settings`, `Dockerfile`, `nginx.conf`, `docker-compose`.
**Formato:** cada ítem incluye archivo(s) afectado, problema, riesgo, y fix concreto para que un agente pueda implementarlo sin ambigüedad.
**Orden:** las fases están pensadas para ejecutarse en secuencia. Dentro de cada fase, los ítems son independientes entre sí salvo que se indique lo contrario.

---

## Fase 0 — Bloqueantes (implementar antes que cualquier otra cosa)

Estos ítems pueden causar corrupción de datos, caída de producción, o dejar controles de seguridad ya existentes completamente inutilizados.

### 0.1 — Integridad de stock: `MovimientoCreateView` bypasea el path con lock
**Archivo:** `apps/inventario/views.py` (`MovimientoCreateView.form_valid`), `apps/inventario/services.py` (`registrar_movimiento`), `apps/inventario/signals.py` (`auditar_movimiento`)

**Problema:** Existen dos caminos para crear un `Movimiento`:
- `services.registrar_movimiento()`: correcto — usa `transaction.atomic()` + `select_for_update()` y valida stock suficiente *dentro* del lock.
- `views.MovimientoCreateView`: crea el `Movimiento` directo vía `CreateView`/`form.save()`. La validación de stock (`_validar_stock_suficiente`) lee `Stock` sin lock y fuera de transacción. El ajuste real ocurre en el signal `auditar_movimiento`, que sí bloquea la fila pero **no vuelve a validar** si el resultado queda negativo.

**Riesgo:** Dos SALIDAs concurrentes del mismo producto/almacén pueden leer el mismo stock disponible, ambas pasar el chequeo, y el signal aplicar ambas restas igual → `Stock.cantidad` negativo, a pesar del `MinValueValidator(0)` declarado (que no se ejecuta en `.save()` directo).

**Fix:**
1. Reescribir `MovimientoCreateView.form_valid()` para que, en vez de llamar a `super().form_valid(form)` directo, delegue la creación del `Movimiento` en `inventario.services.registrar_movimiento(...)` dentro de la misma vista, pasando los datos ya validados del form.
2. Eliminar la validación de stock duplicada y sin lock (`_validar_stock_suficiente`) — la validación autoritativa debe vivir solo en el servicio, bajo el lock.
3. Agregar test de concurrencia (dos threads/transacciones simulando SALIDA simultánea sobre el mismo `Stock`) que falle si el resultado puede quedar negativo.
4. Agregar `models.CheckConstraint(check=models.Q(cantidad__gte=0), name="stock_no_negativo")` en `Stock.Meta` como segunda capa de defensa a nivel de base de datos.

---

### 0.2 — Bypass total de RBAC de inventario vía Django Admin
**Archivo:** `apps/inventario/admin.py` (`MovimientoAdmin`)

**Problema:** A diferencia de `AuditLogAdmin` (que bloquea add/change/delete), `MovimientoAdmin` no restringe `has_add_permission`/`has_change_permission`. Cualquier usuario `is_staff` con permiso Django estándar sobre `Movimiento` puede crear movimientos desde `/admin/` saltándose la matriz de roles (`InventarioPermissionMixin`), la validación de stock suficiente, y el servicio con lock.

**Fix:** Decidir explícitamente una de dos:
- **(a)** Bloquear creación/edición de `Movimiento` desde el admin, igual que se hizo con `AuditLog` (`has_add_permission` → `False`, `has_change_permission` → `False`), forzando que todo movimiento pase por la vista/servicio con validaciones.
- **(b)** Si se necesita edición manual desde admin para casos excepcionales, sobrescribir `save_model()` en `MovimientoAdmin` para que invoque `services.registrar_movimiento()` en vez de guardar el objeto directo, preservando validación de stock y lock.

Recomendación: opción (a), es la más segura y consistente con el resto del proyecto.

---

### 0.3 — `IndexError` garantizado en el último reintento del webhook CRM
**Archivo:** `apps/integracion/tasks.py` (`enviar_evento_crm`)

**Problema:**
```python
backoff = [60, 300, 900][self.request.retries]
raise self.retry(exc=exc, countdown=backoff)
```
Con `max_retries=3`, en el último intento permitido `self.request.retries == 3`, e `[60, 300, 900][3]` lanza `IndexError` — la tarea muere con un error no relacionado al problema real (CRM caído) en vez de agotar reintentos prolijamente.

**Fix:**
```python
backoff = [60, 300, 900][min(self.request.retries, 2)]
```
O mejor, reemplazar la lista manual por el soporte nativo de Celery: `@shared_task(bind=True, max_retries=3, retry_backoff=True, retry_backoff_max=900)`.

---

### 0.4 — IP de origen falsificable en todo el sistema de auditoría y en el lockout de axes
**Archivo:** `apps/shared/middleware.py` (`get_current_request_ip`), `nginx.conf`

**Problema:** `nginx.conf` usa `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`, que **agrega** el valor recibido del cliente a la IP real (formato: `<XFF_del_cliente_si_lo_mandó>, <ip_real_vista_por_nginx>`). El código Django hace `xff.split(",")[0].strip()` — toma el **primer** valor, que es exactamente el que un atacante puede inventar libremente enviando su propio header `X-Forwarded-For`.

**Riesgo:**
- Todo el `AuditLog` (incluyendo `LOGIN_OK`/`LOGIN_FAIL`) puede tener `ip_address` falsificada.
- `AXES_LOCKOUT_PARAMETERS = ["ip_address", "username"]` puede evadirse rotando el header en cada intento de fuerza bruta.

**Fix:** `nginx.conf` ya manda `X-Real-IP: $remote_addr` (no falsificable por el cliente). Cambiar `get_current_request_ip()` para leer `HTTP_X_REAL_IP` como fuente primaria:
```python
def get_current_request_ip() -> str:
    request = getattr(_thread_local, "current_request", None)
    if not request:
        return "0.0.0.0"
    real_ip = request.META.get("HTTP_X_REAL_IP")
    if real_ip:
        return real_ip.strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")
```
Alternativa más robusta a largo plazo: `django-ipware`, que maneja correctamente el conteo de proxies confiables.

---

### 0.5 — Inyección de fórmulas CSV/Excel explotable sin autenticación
**Archivo:** `apps/auditoria/views.py` (`_generar_csv_auditoria`, `exportar_auditoria_excel`), `apps/auditoria/signals.py` (`registrar_login_fallido`)

**Problema:** `credentials.get("email", ...)` en un intento de login fallido se guarda tal cual en `AuditLog.datos`, sin validar formato. Un atacante no autenticado puede enviar como "email" algo como `=cmd|'/c calc'!A1`. Ese valor se vuelca sin sanitizar en las celdas de CSV/Excel cuando un admin exporta el log — ejecución de fórmula al abrir el archivo (CSV Injection, OWASP).

**Fix:** Crear una función de sanitización compartida y aplicarla a todo campo de texto libre antes de escribir en CSV/Excel:
```python
def sanitizar_celda(valor):
    s = str(valor)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s
```
Aplicar en `auditoria/views.py` (campo `datos`) y en `inventario/views.py` (campo `motivo` de `Movimiento`, ver ítem 1.2).

---

### 0.6 — Confirmar arquitectura real de TLS (posible cookie de sesión inútil o tráfico en texto plano)
**Archivo:** `nginx.conf`, `config/settings/ec2.py`

**Problema:** `nginx.conf` solo tiene `listen 80` — no hay bloque 443 ni `ssl_certificate`. `ec2.py` asume que "Nginx maneja SSL termination" y deja `SECURE_SSL_REDIRECT = False`, con `SESSION_COOKIE_SECURE = True`. Si no hay nada delante (ALB/CloudFront) haciendo terminación TLS real, el navegador **nunca enviará la cookie de sesión** sobre HTTP plano → login roto en producción, o peor, todo el tráfico (incluido login) viaja sin cifrar.

**Fix (requiere decisión humana, no solo código):**
1. Confirmar si hay un Load Balancer/CloudFront delante de la instancia EC2 haciendo TLS termination.
2. Si sí: documentarlo explícitamente en `ARQUITECTURA.md` y en un comentario en `nginx.conf`/`ec2.py`.
3. Si no: agregar bloque `server { listen 443 ssl; ... }` a `nginx.conf` con certificado (Let's Encrypt/ACM), y solo entonces mantener `SESSION_COOKIE_SECURE = True`.
4. Eliminar el comentario en `ec2.py` que sugiere "cambiar a False temporalmente" — es una invitación a debilitar la seguridad bajo presión operativa en vez de resolver la causa raíz.

---

### 0.7 — Crash garantizado (500) al subir facturas como VENDEDOR o ALMACENISTA
**Archivo:** `apps/finanzas/forms.py` (`FacturaForm.__init__`)

**Problema:**
```python
if user_rol == Usuario.Rol.VENDEDOR:
    self.fields["tipo"].choices = [Factura.Tipo.VENTA]
elif user_rol == Usuario.Rol.ALMACENISTA:
    self.fields["tipo"].choices = [Factura.Tipo.COMPRA]
```
`choices` debe ser un iterable de tuplas `(valor, etiqueta)`. Acá se asigna una lista con un solo elemento que es el propio miembro del enum (un string). Cuando el widget `Select` intente iterar `for value, label in self.choices`, va a desempaquetar el string de 5 caracteres "VENTA"/"COMPRA" en dos variables → `ValueError: too many values to unpack`. El formulario de carga de facturas se rompe con un 500 para dos de los tres roles que tienen acceso al módulo.

**Fix:**
```python
if user_rol == Usuario.Rol.VENDEDOR:
    self.fields["tipo"].choices = [(Factura.Tipo.VENTA.value, Factura.Tipo.VENTA.label)]
elif user_rol == Usuario.Rol.ALMACENISTA:
    self.fields["tipo"].choices = [(Factura.Tipo.COMPRA.value, Factura.Tipo.COMPRA.label)]
```
Agregar un test que instancie `FacturaForm(user_rol=Usuario.Rol.VENDEDOR)` y renderice el widget (`str(form)`), para que este tipo de bug no vuelva a pasar desapercibido. Una vez corregido, verificar además que el POST de un `tipo` fuera de las choices permitidas sea rechazado por la validación estándar del `ChoiceField` (debería serlo automáticamente si las choices están bien restringidas, pero conviene un test explícito: un VENDEDOR posteando `tipo=COMPRA` manualmente por fuera del form debe recibir un error de validación).

---

### 0.8 — `valor_inventario` en el dashboard financiero no calcula un valor monetario
**Archivo:** `apps/finanzas/views.py` (`datos_finanzas`)

**Problema:**
```python
valor_inventario = (
    Stock.objects
    .annotate(valor=Sum("cantidad"))
    .aggregate(total=Sum("cantidad"))["total"] or 0
)
```
El `.annotate(valor=Sum("cantidad"))` no agrupa nada (no hay `.values()` antes), y el `.aggregate()` final suma directamente `cantidad` de todas las filas de `Stock` — es decir, el resultado es el **total de unidades físicas en inventario**, no un valor en dinero. El dashboard muestra este número bajo el label "valor_inventario" sin ningún error visible: es un bug silencioso que puede llevar a decisiones de negocio basadas en un dato que no significa lo que dice significar.

**Fix:**
```python
from django.db.models import F, ExpressionWrapper, DecimalField as DF

valor_inventario = Stock.objects.aggregate(
    total=Sum(
        F("cantidad") * F("producto__costo_promedio"),
        output_field=ExpressionWrapper(DF(max_digits=14, decimal_places=2), output_field=DF())
    )
)["total"] or 0
```
(Ajustar si el criterio de valuación de negocio debe ser `precio_venta` en vez de `costo_promedio` — confirmar con el dueño del producto qué métrica quieren mostrar: valor a costo vs. valor a precio de venta. Cualquiera de las dos es válida contablemente, pero hay que elegir una explícitamente y documentarla.)

---

## Fase 1 — Alta severidad

### 1.1 — CSP debilitado con directiva inexistente
**Archivo:** `apps/shared/middleware.py` (`SecurityHeadersMiddleware`)

**Problema:** `script-src 'self' 'unsafe-inline' 'unsafe-eval' ...` anula gran parte de la protección de CSP contra XSS. `require-sri-for script style;` no es soportado por ningún navegador moderno (removido del spec) — falsa sensación de seguridad.

**Fix:** Eliminar `require-sri-for`. Migrar `unsafe-inline`/`unsafe-eval` a nonces por request (`django-csp` soporta esto de forma nativa) o mover todo script/estilo inline a archivos estáticos versionados. Es un cambio incremental — puede hacerse endpoint por endpoint si hay mucho inline hoy.

### 1.2 — Inyección de fórmulas CSV/Excel en exports de inventario (mismo patrón que 0.5)
**Archivo:** `apps/inventario/views.py` (`_generar_csv_movimientos`, `exportar_movimientos_excel`)

**Problema:** El campo `motivo` (texto libre, escrito por Admin/Vendedor/Almacenista) se exporta sin sanitizar.

**Fix:** Reusar `sanitizar_celda()` del ítem 0.5.

### 1.3 — Exports de inventario sin control de permiso por rol
**Archivo:** `apps/inventario/views.py` (`exportar_productos_csv/excel`, `exportar_movimientos_csv/excel`)

**Problema:** Solo exigen `@login_required`. Cualquier usuario autenticado (incluido VENDEDOR) puede descargar el historial completo de movimientos, incluyendo `costo_unitario` — dato de margen que probablemente no debería ser visible para todos los roles.

**Fix:** Definir el permiso apropiado (ej. `inventario.puede_exportar_datos_completos` o reusar un criterio de rol como en `metricas/views.py`), y aplicarlo con `@permission_required` o filtrando columnas sensibles según `request.user.rol`.

### 1.4 — Sin rate limiting en endpoints DRF
**Archivo:** `config/settings/base.py` (`REST_FRAMEWORK`)

**Problema:** No hay `DEFAULT_THROTTLE_CLASSES`/`DEFAULT_THROTTLE_RATES`. `django-axes` protege el login por formulario, no necesariamente endpoints de API.

**Fix:**
```python
REST_FRAMEWORK = {
    ...
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"user": "1000/day", "anon": "100/day"},
}
```
Ajustar tasas según el uso real esperado del PWA.

### 1.5 — Contenedor corre como root
**Archivo:** `Dockerfile`

**Fix:** Agregar creación de usuario no-root y `USER` antes del `CMD`/`ENTRYPOINT`:
```dockerfile
RUN addgroup --system app && adduser --system --ingroup app app
USER app
```
Verificar que los volúmenes montados (`staticfiles`, etc.) tengan permisos compatibles.

### 1.6 — Subida de facturas sin validar extensión ni contenido real del archivo
**Archivo:** `apps/finanzas/models.py` (`Factura.archivo`)

**Problema:** `archivo = models.FileField(upload_to=upload_factura_path, help_text="PDF o XML de la factura")` — el `help_text` describe la intención, pero no hay ningún `FileExtensionValidator` ni validación de contenido (magic bytes). Cualquier usuario con acceso a `finanzas` (los 3 roles, ver ítem 2.24) puede subir cualquier tipo de archivo.

**Riesgo:** Si el archivo termina siendo servido con un `Content-Type` incorrecto (ver ítem 1.7), un `.html`/`.svg` subido como "factura" puede ejecutar JS en el navegador de quien lo abra (stored XSS). Además, sin límite de tipo, el bucket de storage puede terminar alojando binarios arbitrarios.

**Fix:**
```python
from django.core.validators import FileExtensionValidator

archivo = models.FileField(
    upload_to=upload_factura_path,
    validators=[FileExtensionValidator(allowed_extensions=["pdf", "xml"])],
    help_text="PDF o XML de la factura",
)
```
La validación de extensión es fácil de evadir (renombrar un `.html` a `.pdf`), así que además conviene validar el contenido real con `python-magic` en `FacturaForm.clean_archivo()`, comparando el MIME type detectado contra `application/pdf`/`text/xml`, y rechazar si no coincide.

### 1.7 — Confirmar cómo se sirven los archivos de `Factura.archivo` en producción
**Archivo:** `nginx.conf`, `config/settings/production.py`/`ec2.py` (MEDIA_URL/MEDIA_ROOT no vistos aún)

**Problema:** `nginx.conf` solo tiene un `location /static/`; no hay ningún `location /media/`. Si `MEDIA_URL` apunta a `/media/`, las requests caen en el `location /` genérico que proxea a Django — y Django, con `DEBUG=False`, no sirve archivos de media por defecto salvo que se configure explícitamente en `urls.py` (no visto en los archivos revisados) o se use un backend de storage externo (S3, etc.).

**Riesgo (dos escenarios, ambos malos, hay que determinar cuál aplica):**
- **(a)** Si Django efectivamente sirve los archivos sin pasar por `_check_roles`, cualquiera con la URL directa (`/media/facturas/...`) accede a documentos financieros sin autenticación — nada en el pipeline de archivos estáticos aplica el control de acceso que sí tiene la vista `finanzas_dashboard`.
- **(b)** Si no hay nada sirviendo `/media/` en absoluto, la funcionalidad de "ver factura subida" está simplemente rota en producción.

**Fix:** Confirmar el mecanismo real (¿S3? ¿nginx con `location /media/` que falta agregar? ¿vista Django dedicada?). Sea cual sea, los archivos de `Factura` deben servirse a través de una vista que aplique `_check_roles`/permiso equivalente antes de devolver el archivo (o, si es S3, usando URLs firmadas de corta duración), nunca como archivo estático públicamente alcanzable.

---

## Fase 2 — Severidad media

| # | Archivo | Problema | Fix |
|---|---------|----------|-----|
| 2.1 | `apps/usuarios/forms.py` | Docstring menciona validación "django-pwned-passwords" que no está instalada ni en `AUTH_PASSWORD_VALIDATORS` | Instalar y configurar el validador, o corregir el docstring para no afirmar una protección inexistente |
| 2.2 | `apps/inventario/views.py` | Docstring del módulo dice "Rate limiting en exports via django-ratelimit" — no hay ningún `@ratelimit` en el archivo | Implementar `django-ratelimit` en los 4 endpoints de export, o corregir el docstring |
| 2.3 | `apps/usuarios/views.py` (`UsuarioUpdateView`) | Bloquea auto-desactivación pero no auto-escalación de rol | Replicar la misma protección: si `original.pk == request.user.pk` y `"rol" in cambios`, rechazar el cambio |
| 2.4 | `apps/usuarios/models.py` | Campos `intentos_fallidos`/`bloqueado_hasta` no tienen incremento visible en el código revisado — posible duplicación no sincronizada con `django-axes` | Confirmar dónde se incrementan; si `axes` ya cubre el lockout, evaluar eliminar estos campos o documentarlos como redundancia intencional |
| 2.5 | `config/settings/base.py` | `CSRF_COOKIE_HTTPONLY = True` puede romper el patrón típico de leer el token CSRF vía JS/`document.cookie` en llamadas `fetch()` del PWA | Confirmar que el frontend usa `{% csrf_token %}`/meta tag en vez de leer la cookie; documentar el patrón esperado |
| 2.6 | `apps/auditoria/models.py` (`AuditLog.save`) | Lectura del "último registro" + cálculo de `hash_previo` sin lock ni transacción — dos inserts concurrentes pueden generar el mismo `hash_previo`, rompiendo la linealidad de la cadena | Envolver en `transaction.atomic()` con `select_for_update()` sobre el último registro, o usar un lock de aplicación (ej. Redis) para serializar escrituras de auditoría |
| 2.7 | `apps/auditoria/models.py` (`verificar_cadena`) | Carga toda la tabla en memoria sin paginar | Paginar en bloques (ej. `iterator(chunk_size=1000)`) y verificar por lotes |
| 2.8 | `apps/auditoria/views.py` (`exportar_auditoria_excel`) | Arma el `Workbook` completo en memoria, sin filtro de rango de fechas | Mover a tarea Celery que genere el archivo y entregue un link, o agregar filtro de fecha obligatorio |
| 2.9 | `apps/metricas/views.py` | Importa `AuditLog` directo, violando la regla de arquitectura documentada en `shared/services.py` | Reemplazar por `apps.shared.services.registrar_audit_log()` |
| 2.10 | `config/settings/base.py` | Sin `CACHES` explícito → `LocMemCache` por proceso; con 4 workers gunicorn, la caché de métricas no se comparte | Configurar `django-redis` como backend de caché usando la instancia Redis ya disponible |
| 2.11 | `apps/metricas/views.py` | `int(c["total"])` trunca decimales de stock sin redondeo | Usar `round()` explícito, o mantener `Decimal`/`float` y redondear en el frontend |
| 2.12 | `apps/metricas/models.py` (`ReporteProgramado`) | Campo `destinatarios` (lista de emails) sin validación de formato | Validar cada entrada con `apps.shared.value_objects.EmailAddress` dentro de `clean()` |
| 2.13 | `apps/metricas/models.py` (`_validar_cron`) | No valida rangos (ej. hora 0-23, minuto 0-59) | Migrar a `croniter` u otra librería estándar de validación cron |
| 2.14 | `apps/shared/middleware.py` (`SecurityHeadersMiddleware`) | Método `process_response` muerto que referencia `self.CSP_DIRECTIVES` (atributo inexistente) — no se ejecuta hoy pero es una trampa para refactors futuros | Eliminar el método completo |
| 2.15 | `apps/shared/middleware.py` (`CurrentRequestMiddleware`) | Patrón thread-local asume workers WSGI síncronos; se rompe con `gevent`/`eventlet`/ASGI | Documentar la restricción explícitamente en el docstring de la clase |
| 2.16 | `apps/integracion/models.py` (`WebhookCRM`) | Modelo completo (+ admin) sin ningún uso real — `tasks.py` siempre usa `settings.CRM_WEBHOOK_URL` fijo | Decidir: eliminar el modelo, o conectarlo (ver 2.17 antes de conectar) |
| 2.17 | `apps/integracion/models.py` (`WebhookCRM.url_destino`) | Si se conecta a futuro, riesgo de SSRF (metadata de instancia EC2, servicios internos) porque cualquier staff puede escribir la URL desde el admin | Antes de conectar: validar que la URL no apunte a rangos privados/loopback/metadata, o usar allowlist de dominios |
| 2.18 | `apps/integracion/` | Infraestructura de rotación de `ClaveCRM` completa pero sin endpoint receptor de webhooks entrantes (`urls.py` vacío) | Al construir el endpoint: usar `hmac.compare_digest()` para comparar firmas (nunca `==`), nunca loguear el secreto en texto plano |
| 2.19 | `apps/integracion/tasks.py` (`enviar_evento_crm`) | Firma HMAC sin timestamp/nonce → replay attack posible | Incluir `timestamp` en el payload firmado; el receptor futuro debe rechazar mensajes fuera de una ventana de tolerancia (ej. ±5 min) |
| 2.20 | `apps/integracion/models.py` (`SyncLog`) | Mutable/editable desde el admin, a diferencia de `AuditLog` | Si se usa como evidencia operativa, aplicar el mismo patrón de inmutabilidad (`has_change_permission`/`has_delete_permission` → `False`) |
| 2.21 | `apps/integracion/services.py` | `registrar_evento_auditoria()` no se usa en ningún lado, y también importa `AuditLog` directo violando la regla de arquitectura | Conectarla donde corresponda o eliminarla; si se usa, reemplazar por el servicio compartido |
| 2.22 | `apps/integracion/signals.py` (`publicar_movimiento_al_crm`) | Encola tarea Celery incluso si el CRM no está configurado, generando ruido de `SyncLog` en estado `FALLIDO` permanente | Agregar `if crm_configurado(): enviar_evento_crm.delay(...)` |
| 2.23 | `apps/finanzas/` | Sin ninguna entrada de `AuditLog` al crear/subir una `Factura` — único módulo de datos sensibles del proyecto sin auditoría; además `FacturaAdmin` permite editar/borrar facturas libremente desde `/admin/` sin registro | Llamar a `apps.shared.services.registrar_audit_log()` en `factura_upload`; evaluar agregar un `Evento.FACTURA_SUBIDA` al enum de `AuditLog`; restringir edición/borrado en `FacturaAdmin` o al menos auditarlos |
| 2.24 | `apps/finanzas/views.py` (`_check_roles`, `ROLES_FINANZAS`) | RBAC implementado como lista hardcodeada de roles comparada directo contra `request.user.rol`, en vez del sistema de permisos Django usado en el resto del proyecto (`PermissionRequiredMixin` + `usuarios.puede_*`); además `ROLES_FINANZAS` incluye los 3 roles existentes, por lo que en la práctica no restringe nada más allá de "estar autenticado" | Migrar a un permiso Django dedicado (ej. `finanzas.puede_gestionar_facturas`) consistente con el resto de la RBAC del proyecto |
| 2.25 | `apps/finanzas/views.py` (`datos_finanzas`) | `costo_promedio` se calcula iterando productos en Python (`for p in prods`) en vez de agregación en BD, y el promedio está sesgado: excluye productos con `costo_promedio` en 0/falsy del numerador pero los sigue contando en el denominador (`prods.count()`) | Reemplazar por `Producto.objects.filter(activo=True, costo_promedio__gt=0).aggregate(Avg("costo_promedio"))` |
| 2.26 | `apps/finanzas/forms.py` (`FacturaForm`) | El campo `movimiento` no filtra su queryset — cualquier usuario con acceso a `finanzas` puede vincular una factura a cualquier `Movimiento` del sistema, sin relación con su propia actividad, almacén, o rango de fechas razonable | Acotar el queryset en `__init__` (ej. últimos N días, o movimientos donde `realizada_por == request.user` si la regla de negocio lo amerita) |

---

## Fase 3 — Baja severidad / limpieza técnica

| # | Archivo | Problema | Fix |
|---|---------|----------|-----|
| 3.1 | `docker-compose.yml` | Atributo `version: "3.9"` deprecado (Compose v2 lo ignora con warning) | Eliminar la línea |
| 3.2 | `config/settings/base.py` | `TIME_ZONE = "America/Argentina/Buenos_Aires"` — confirmar si es la zona horaria correcta para la operación real del negocio | Ajustar si corresponde |
| 3.3 | `apps/inventario/models.py` (`Movimiento`) | Negación de `cantidad` para SALIDA duplicada entre `views.py` y `Movimiento.save()` | Dejar una sola fuente de verdad (recomendado: solo en el servicio de negocio, tras la refactorización del ítem 0.1) |
| 3.4 | Todo el proyecto | `logger.critical(...)` en fallos de auditoría no está conectado a alertas activas (Sentry/CloudWatch Alarm) | Conectar el logger a un sink con alertas, para no depender de revisión manual de logs |
| 3.5 | `apps/finanzas/views.py` (`datos_finanzas`) | Montos monetarios convertidos a `float` en la respuesta JSON (`float(valor_inventario)`, etc.) — riesgo menor de imprecisión de punto flotante en datos financieros | Serializar como string de `Decimal` y convertir a número en el frontend, o documentar que es solo para visualización en gráficos (no para cálculos contables) |

---

## Resumen ejecutivo para priorización

- **Fase 0 (8 ítems):** riesgo de corrupción de datos, caída de producción, o un dashboard financiero mostrando cifras sin sentido. Bloquea todo lo demás.
- **Fase 1 (7 ítems):** vulnerabilidades de seguridad explotables con impacto claro, sin riesgo inmediato de caída del sistema.
- **Fase 2 (26 ítems):** deuda técnica y gaps de seguridad de menor probabilidad/impacto, pero varios son fáciles de arreglar y varios son inconsistencias entre lo documentado y lo implementado (buena señal de que documentarlas ayuda a que no se repitan).
- **Fase 3 (5 ítems):** limpieza, no bloquea nada.

**Nota sobre `finanzas`:** es la app más nueva del proyecto y la única sin ningún registro en `AuditLog` — vale la pena que, al corregir la Fase 0, el agente también deje sentada la integración con `apps.shared.services.registrar_audit_log()` desde el vamos, en vez de agregarla después como parche (ítem 2.23).

**Sugerencia de orden de trabajo para el agente:** Fase 0 completa → tests de regresión sobre `inventario` y `integracion` → Fase 1 → Fase 2 (se puede paralelizar por app, ya que los ítems son mayormente independientes) → Fase 3.
