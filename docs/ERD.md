```mermaid
erDiagram
    Categoria ||--o{ Producto : ""
    Producto ||--o{ Stock : ""
    Almacen ||--o{ Stock : ""
    Producto ||--o{ Movimiento : ""
    Almacen ||--o{ Movimiento : ""
    Usuario ||--o{ Movimiento : ""
    Producto ||--o| AlertaConfig : ""
    Producto ||--o{ Alerta : ""
    Usuario ||--o{ AuditLog : ""

    Categoria {
        uuid id PK
        string nombre UK
        text descripcion
        bool activo
        datetime created_at
    }

    Producto {
        uuid id PK
        string sku UK
        string nombre
        text descripcion
        uuid categoria_id FK
        decimal precio_venta
        decimal costo_promedio
        decimal stock_minimo
        bool activo
        datetime created_at
        datetime updated_at
    }

    Almacen {
        uuid id PK
        string nombre UK
        string ubicacion
        bool activo
        datetime created_at
    }

    Stock {
        uuid id PK
        uuid producto_id FK
        uuid almacen_id FK
        decimal cantidad
        datetime updated_at
    }

    Movimiento {
        uuid id PK
        string tipo
        uuid producto_id FK
        uuid almacen_id FK
        decimal cantidad
        decimal costo_unitario
        text motivo
        uuid realizada_por_id FK
        datetime created_at
    }

    Usuario {
        uuid id PK
        string email UK
        string nombre
        string rol
        string password
        bool activo
        bool is_staff
        bool is_superuser
        datetime fecha_creacion
        datetime ultimo_acceso
        int intentos_fallidos
        datetime bloqueado_hasta
    }

    AlertaConfig {
        uuid id PK
        uuid producto_id FK
        int umbral_minimo
        bool activo
        datetime created_at
        datetime updated_at
    }

    Alerta {
        uuid id PK
        uuid producto_id FK
        text mensaje
        string estado
        datetime created_at
        datetime resuelta_en
    }

    AuditLog {
        uuid id PK
        string evento
        uuid usuario_id FK
        string ip_address
        datetime timestamp
        json datos
        string hash_previo
    }

    WebhookCRM {
        uuid id PK
        string evento
        string url_destino
        bool activo
        datetime created_at
    }

    SyncLog {
        uuid id PK
        string evento
        string estado
        json payload
        json respuesta
        int intentos
        datetime created_at
        datetime updated_at
    }

    ClaveCRM {
        uuid id PK
        string clave_publica UK
        string hash_clave
        bool activa
        datetime creada_en
        datetime expira_en
        datetime rotada_en
    }

    DashboardConfig {
        uuid id PK
        string nombre
        text descripcion
        json config
        datetime created_at
        datetime updated_at
    }

    ReporteProgramado {
        uuid id PK
        string nombre
        string tipo
        string cron_expresion
        json destinatarios
        bool activo
        datetime created_at
    }
```

## Diagrama de Entidad-Relación

- **14 modelos** en 6 apps (inventario, usuarios, alertas, auditoria, integracion, metricas)
- Todas las PK son **UUID v4**
- Relaciones clave:
  - `Producto` ↔ `Stock` ↔ `Almacen` (inventario por almacén)
  - `Producto` → `Movimiento` ← `Almacen` / `Usuario` (trazabilidad)
  - `Producto` → `Alerta` (alertas automáticas de stock bajo)
  - `Usuario` → `AuditLog` (cadena de hash inmutables)
- Entidades standalone (sin FK): `WebhookCRM`, `SyncLog`, `ClaveCRM`, `DashboardConfig`, `ReporteProgramado`
