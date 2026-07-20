```mermaid
erDiagram
    Categoria ||--o{ Producto : "tiene"
    Producto ||--o{ Stock : "tiene"
    Almacen ||--o{ Stock : "tiene"
    Producto ||--o{ Movimiento : "registra"
    Almacen ||--o{ Movimiento : "origina"
    Usuario ||--o{ Movimiento : "realiza"
    Producto ||--o| AlertaConfig : "configura"
    Producto ||--o{ Alerta : "genera"
    Usuario ||--o{ AuditLog : "audita"

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
        fk categoria FK
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
        fk producto FK
        fk almacen FK
        decimal cantidad
        datetime updated_at
    }

    Movimiento {
        uuid id PK
        string tipo "ENTRADA | SALIDA | AJUSTE"
        fk producto FK
        fk almacen FK
        decimal cantidad
        decimal costo_unitario
        text motivo
        fk realizada_por FK
        datetime created_at
    }

    Usuario {
        uuid id PK
        string email UK
        string nombre
        string rol "ADMIN | VENDEDOR | ALMACENISTA"
        string password
        bool activo
        bool is_staff
        bool is_superuser
        datetime fecha_creacion
        datetime ultimo_acceso
        int intentos_fallidos
        datetime bloqueado_hasta
        m2m groups
        m2m user_permissions
    }

    AlertaConfig {
        uuid id PK
        fk producto FK UK
        int umbral_minimo
        bool activo
        datetime created_at
        datetime updated_at
    }

    Alerta {
        uuid id PK
        fk producto FK
        text mensaje
        string estado "PENDIENTE | VISTA | RESUELTA"
        datetime created_at
        datetime resuelta_en
    }

    AuditLog {
        uuid id PK
        string evento "12 tipos"
        fk usuario FK
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
        string estado "PENDIENTE | ENVIADO | FALLIDO"
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
        string tipo "EXCEL | PDF | CSV"
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
