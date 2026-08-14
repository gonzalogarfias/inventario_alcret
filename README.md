# ALCRET — Sistema de Gestión de Inventario

Sistema web para gestión de inventarios con control de stock, movimientos, clientes, facturación, integración CRM/SRI, usuarios y auditoría.

## Stack

- **Backend:** Django 4.2 + Django REST Framework + Celery/Redis
- **Frontend:** Tailwind CSS (CLI), Alpine.js, Chart.js, PWA (Service Worker + Manifest)
- **Base de datos:** SQLite (desarrollo) / PostgreSQL (producción)
- **Seguridad:** django-axes (rate limiting), Argon2, django-guardian, auditoría de eventos

## Módulos

| App | Responsabilidad |
|-----|----------------|
| `inventario` | Productos, categorías, almacenes, movimientos y stock |
| `clientes` | Gestión de clientes |
| `cotizaciones` | Cotizaciones vinculadas a clientes |
| `finanzas` | Facturas de compra/venta con archivos adjuntos |
| `integracion` | Integración CRM externo y rotación de claves |
| `alertas` | Alertas de stock mínimo para usuarios |
| `auditoria` | Auditoría de eventos (login, password reset, CRUD) |
| `metricas` | Reportes programados y métricas |
| `usuarios` | Usuarios con roles (ADMIN, VENDEDOR, ALMACENISTA) |
| `shared` | Utilidades transversales (middleware, permisos, validaciones) |

## Funcionalidades

- Control de stock mínimo y alertas
- Dashboard con gráficos de stock y movimientos
- RBAC con roles y permisos por objeto (django-guardian)
- Auditoría de eventos y exportación CSV/Excel
- Facturas de compra/venta con adjuntos
- Integración con CRM y generación SRI
- Diseño responsivo con bottom nav en móvil y sidebar en desktop
- PWA instalable y offline-first

## Inicio rápido

```bash
# Clonar
git clone https://github.com/gonzalogarfias/inventario_alcret.git
cd inventario_alcret

# Crear environment
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements/development.txt

# Variables de entorno
cp .env.example .env
# Editar .env con DJANGO_SECRET_KEY y DB config

# Migrar y correr
python manage.py migrate
python manage.py runserver
```

## Compilar estilos (Tailwind)

```bash
npm install
npm run build:css   # genera static/css/tailwind.css (committeado)
```

## Tests

```bash
pytest apps/ -v
```

## Licencia

Uso interno — ALCRET