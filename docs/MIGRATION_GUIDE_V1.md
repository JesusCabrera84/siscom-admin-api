# Guía de Migración - FASE 1: Alineación Backend con DDL

## Resumen de Cambios Realizados

Esta guía documenta los cambios realizados en la FASE 1 de la migración
para alinear el backend (ORM models, services, endpoints) con el modelo conceptual:

```
Account (raíz comercial) 1 ──< Organization (raíz operativa) *
```

## Modelo Conceptual

```
┌─────────────────────────────────────────────────────────────┐
│                      ACCOUNT                                 │
│  - Raíz comercial                                           │
│  - Billing, facturación                                     │
│  - Existe desde el primer registro                          │
│  - Relación con: payments                                   │
└─────────────────────────┬───────────────────────────────────┘
                          │ 1:N
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    ORGANIZATION                              │
│  - Raíz operativa                                           │
│  - Permisos, uso diario                                     │
│  - Pertenece a Account                                      │
│  - Relación con: users, devices, units, subscriptions,      │
│    orders, organization_users, organization_capabilities    │
└─────────────────────────────────────────────────────────────┘
```

## Cambios en Modelos ORM

### Nuevos Modelos

| Archivo | Clase | Descripción |
|---------|-------|-------------|
| `app/models/account.py` | `Account` | Raíz comercial del cliente |

### Modelos Renombrados

| Antes | Después | Archivo |
|-------|---------|---------|
| `Client` | `Organization` | `app/models/organization.py` |
| `ClientStatus` | `OrganizationStatus` | `app/models/organization.py` |

### Modelos Actualizados (client_id → organization_id)

| Modelo | Campo Viejo | Campo Nuevo | FK |
|--------|-------------|-------------|-----|
| `Organization` | - | `account_id` | `accounts.id` |
| `User` | `client_id` | `organization_id` | `organizations.id` |
| `Device` | `client_id` | `organization_id` | `organizations.id` |
| `Unit` | `client_id` | `organization_id` | `organizations.id` |
| `Subscription` | `client_id` | `organization_id` | `organizations.id` |
| `OrganizationUser` | `client_id` | `organization_id` | `organizations.id` |
| `OrganizationCapability` | `client_id` | `organization_id` | `organizations.id` |
| `Invitation` | `client_id` | `organization_id` | `organizations.id` |
| `TokenConfirmacion` | `client_id` | `organization_id` | `organizations.id` |
| `Order` | `client_id` | `organization_id` | `organizations.id` |

### Modelo Especial (Payment)

| Modelo | Campo | FK | Nota |
|--------|-------|-----|------|
| `Payment` | `account_id` | `accounts.id` | Pagos pertenecen a Account, no Organization |

### Modelos Eliminados

| Modelo | Razón |
|--------|-------|
| `DeviceInstallation` | No existe en DDL, redundante con `unit_devices` |

### Modelos Marcados como LEGACY

| Modelo | Archivo | Nota |
|--------|---------|------|
| `DeviceService` | `app/models/device_service.py` | No eliminar, endpoints `/services/*` dependen de él |

## Aliases de Compatibilidad

Se mantienen aliases para no romper código existente:

```python
# En app/models/__init__.py
Client = Organization  # DEPRECATED
ClientStatus = OrganizationStatus  # DEPRECATED

# En modelos individuales
@property
def client_id(self):
    """DEPRECATED: Usar organization_id"""
    return self.organization_id
```

## Migraciones DDL Requeridas

### PASO 1: Crear tabla `accounts` (si no existe)

```sql
-- Verificar si existe
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'accounts'
);

-- Si no existe, crear
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    billing_email TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### PASO 2: Renombrar tabla `clients` → `organizations` (si aplica)

```sql
-- Solo si la tabla se llama 'clients'
ALTER TABLE clients RENAME TO organizations;
```

### PASO 3: Agregar `account_id` a `organizations`

```sql
-- Crear accounts para organizaciones existentes (1:1 por ahora)
INSERT INTO accounts (id, name, status, billing_email, created_at, updated_at)
SELECT id, name, status, billing_email, created_at, updated_at
FROM organizations;

-- Agregar columna
ALTER TABLE organizations 
ADD COLUMN account_id UUID REFERENCES accounts(id) ON DELETE CASCADE;

-- Actualizar con el mismo ID (1:1)
UPDATE organizations SET account_id = id;

-- Hacer NOT NULL
ALTER TABLE organizations ALTER COLUMN account_id SET NOT NULL;
```

### PASO 4: Actualizar FK de `subscriptions`

```sql
-- Si la columna se llama account_id y debe apuntar a organizations
ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_account_id_fkey;

ALTER TABLE subscriptions 
RENAME COLUMN account_id TO organization_id;

ALTER TABLE subscriptions 
ADD CONSTRAINT subscriptions_organization_id_fkey 
FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;
```

### PASO 5: Actualizar FK de `payments`

```sql
-- Si payments.client_id debe ser payments.account_id
ALTER TABLE payments 
RENAME COLUMN client_id TO account_id;

ALTER TABLE payments DROP CONSTRAINT IF EXISTS payments_client_id_fkey;

ALTER TABLE payments 
ADD CONSTRAINT payments_account_id_fkey 
FOREIGN KEY (account_id) REFERENCES accounts(id);
```

### PASO 6: Crear índices

```sql
CREATE INDEX IF NOT EXISTS idx_organizations_account_id ON organizations(account_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_organization_id ON subscriptions(organization_id);
CREATE INDEX IF NOT EXISTS idx_payments_account_id ON payments(account_id);
```

## Servicios Actualizados

| Servicio | Cambios |
|----------|---------|
| `OrganizationService` | Parámetros `client_id` → `organization_id` |
| `CapabilityService` | Parámetros `client_id` → `organization_id` |
| `subscription_query` | Parámetros `client_id` → `organization_id` |

## API Dependencies Actualizadas

| Dependencia | Antes | Después |
|-------------|-------|---------|
| `AuthResult.client_id` | campo | `organization_id` (con alias `client_id` DEPRECATED) |
| `resolve_current_client()` | función | `resolve_current_organization()` (alias DEPRECATED) |
| `get_current_client_id()` | función | `get_current_organization_id()` (alias DEPRECATED) |

## Validación Post-Migración

### Verificar integridad

```sql
-- Verificar que todas las organizations tienen account_id
SELECT COUNT(*) FROM organizations WHERE account_id IS NULL;

-- Verificar que todas las subscriptions tienen organization_id
SELECT COUNT(*) FROM subscriptions WHERE organization_id IS NULL;

-- Verificar FKs
SELECT 
    tc.constraint_name, 
    tc.table_name, 
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_name IN ('organizations', 'subscriptions', 'payments', 'users', 'devices', 'units');
```

## Próximos Pasos (FASE 2)

1. **Actualizar endpoints** que usen `client_id` en rutas o parámetros
2. **Actualizar tests** con los nuevos nombres
3. **Crear endpoint de onboarding** que cree Account + Organization + User
4. **Deprecar is_master** con warnings en logs
5. **Preparar para Stripe** - Account tendrá stripe_customer_id

## Notas Importantes

- ⚠️ Los aliases de compatibilidad (`Client`, `client_id`) se eliminarán en la próxima versión mayor
- ⚠️ `DeviceService` no se debe usar en código nuevo - usar `Subscription`
- ✅ Las migraciones DDL se pueden ejecutar gradualmente
- ✅ El backend es backwards-compatible con el DDL existente gracias a los aliases

