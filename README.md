# ALCRET — Sistema de Gestión de Inventario

Sistema web para gestión de inventarios con control de stock, movimientos, usuarios y auditoría.

## Stack

- **Backend:** Django 4.2 + Django REST Framework
- **Frontend:** Tailwind CSS (CDN), Alpine.js, Chart.js
- **Base de datos:** SQLite (desarrollo) / PostgreSQL (producción)
- **Seguridad:** django-axes (rate limiting), Argon2, django-guardian
- **PWA:** Service Worker + Manifest para instalación en dispositivos

## Funcionalidades

- Productos, categorías, almacenes y movimientos (entrada/salida/ajuste)
- Control de stock mínimo y alertas
- Dashboard con gráficos de stock y movimientos
- Usuarios con roles (ADMIN, VENDEDOR, ALMACENISTA)
- Auditoría de eventos (login, password reset, CRUD)
- Exportación CSV/Excel
- Diseño responsivo con bottom nav en móvil y sidebar en desktop

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

## Tests

```bash
pytest apps/ -v
```

## Usuarios de prueba

| Email | Contraseña | Rol |
|-------|-----------|-----|
| admin@test.com | Admin123! | ADMIN |
| vendedor@test.com | Vendedor123! | VENDEDOR |
| almacen@test.com | Almacen123! | ALMACENISTA |

## Licencia

Uso interno — ALCRET
