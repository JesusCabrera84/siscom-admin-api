# Guía de Migración - Account/Organization Model v1

## Resumen de Fases

| Fase | Descripción | Estado |
|------|-------------|--------|
| **FASE 1** | Modelos ORM y Servicios | ✅ Completada |
| **FASE 2** | Endpoints y API | ✅ Completada |
| **FASE 3** | Tests y Documentación | ✅ Completada |
| **FASE 4** | Migraciones DDL | ✅ Completada |

---

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

---

## FASE 1: Modelos ORM y Servicios ✅

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

### Servicios Actualizados

| Servicio | Cambios |
|----------|---------|
| `OrganizationService` | Parámetros `client_id` → `organization_id` |
| `CapabilityService` | Parámetros `client_id` → `organization_id` |
| `subscription_query` | Parámetros `client_id` → `organization_id` |

### API Dependencies Actualizadas

| Dependencia | Antes | Después |
|-------------|-------|---------|
| `AuthResult.client_id` | campo | `organization_id` (alias `client_id` DEPRECATED) |
| `resolve_current_client()` | función | `resolve_current_organization()` (alias DEPRECATED) |
| `get_current_client_id()` | función | `get_current_organization_id()` (alias DEPRECATED) |

---

## FASE 2: Endpoints y API ✅

### Endpoints Actualizados

| Archivo | Cambios |
|---------|---------|
| `app/api/v1/endpoints/clients.py` | Crea Account + Organization en registro |
| `app/api/v1/endpoints/subscriptions.py` | `client_id` → `organization_id` |
| `app/api/v1/endpoints/capabilities.py` | `client_id` → `organization_id` |
| `app/api/v1/endpoints/devices.py` | `client_id` → `organization_id` |
| `app/api/v1/endpoints/units.py` | `client_id` → `organization_id` |
| `app/api/v1/endpoints/users.py` | `client_id` → `organization_id` |
| `app/api/v1/endpoints/services.py` | `client_id` → `organization_id` |
| `app/api/v1/endpoints/internal/clients.py` | `Organization`, `OrganizationStatus` |

### Schemas Actualizados

| Archivo | Cambios |
|---------|---------|
| `app/schemas/subscription.py` | `client_id` → `organization_id` |
| `app/schemas/account.py` | Nuevo schema para Account |

### Flujo de Onboarding Actualizado

```python
# POST /api/v1/clients/
# 1. Crear Account
new_account = Account(name=..., status=AccountStatus.ACTIVE)

# 2. Crear Organization vinculada
new_organization = Organization(
    name=...,
    status=OrganizationStatus.PENDING,
    account_id=new_account.id,
)

# 3. Crear User
new_user = User(
    organization_id=new_organization.id,
    email=...,
    is_master=True,
)

# 4. Crear OrganizationUser
org_user = OrganizationUser(
    organization_id=new_organization.id,
    user_id=new_user.id,
    role=OrganizationRole.OWNER,
)
```

---

## FASE 3: Tests y Documentación ✅

### Tests Actualizados

| Archivo | Cambios |
|---------|---------|
| `tests/conftest.py` | - Nuevo fixture `test_account_data` |
|                     | - Nuevo fixture `test_organization_data` |
|                     | - `Client` → `Organization` |
|                     | - `client_id` → `organization_id` |
|                     | - `get_current_client_id` → `get_current_organization_id` |
| `tests/test_devices.py` | `client_id` → `organization_id` en payloads y asserts |
| `tests/test_services.py` | Comentarios actualizados (LEGACY) |
| `tests/test_auth.py` | Comentarios actualizados |

### Documentación Actualizada

| Archivo | Cambios |
|---------|---------|
| `docs/api/clients.md` | Modelo Account/Organization, flujo de registro |
| `docs/api/subscriptions.md` | `client_id` → `organization_id` |
| `docs/api/accounts.md` | **NUEVO** - Documentación de Account |

---

## FASE 4: Migraciones DDL ✅

### Archivos de Migración Creados

| Archivo | Descripción |
|---------|-------------|
| `012_add_account_id_to_organizations.py` | Agrega `account_id` a organizations |
| `013_rename_subscriptions_account_id_to_organization_id.py` | Renombra `account_id` → `organization_id` en subscriptions |
| `014_rename_users_client_id_to_organization_id.py` | Renombra `client_id` → `organization_id` en users |

### Ejecutar Migraciones

```bash
# Ejecutar todas las migraciones pendientes
alembic upgrade head

# O ejecutar una por una
alembic upgrade 012_add_account_id_to_organizations
alembic upgrade 013_rename_subscriptions_account_id
alembic upgrade 014_rename_users_client_id
```

### Migración 012: organizations.account_id

```sql
-- Lo que hace la migración:
-- 1. Agrega columna account_id a organizations
-- 2. Crea accounts para organizations existentes (1:1)
-- 3. Establece FK organizations.account_id -> accounts.id
-- 4. Crea índice en organizations.account_id
```

### Migración 013: subscriptions.organization_id

```sql
-- Lo que hace la migración:
-- 1. Elimina FK confusa (account_id apuntaba a organizations)
-- 2. Renombra account_id -> organization_id
-- 3. Crea nueva FK correcta
-- 4. Crea índice
```

### Migración 014: users.organization_id

```sql
-- Lo que hace la migración:
-- 1. Elimina FK users_client_id_fkey
-- 2. Renombra client_id -> organization_id
-- 3. Crea nueva FK users_organization_id_fkey
-- 4. Actualiza índices
```

### SQL Manual (Alternativa)

Si prefieres ejecutar SQL manualmente:

#### PASO 1: Agregar account_id a organizations

```sql
-- Agregar columna
ALTER TABLE organizations 
ADD COLUMN account_id UUID;

-- Crear accounts para organizations existentes (1:1)
INSERT INTO accounts (id, name, status, billing_email, created_at, updated_at)
SELECT id, name, COALESCE(status, 'ACTIVE'), billing_email, 
       COALESCE(created_at, now()), COALESCE(updated_at, now())
FROM organizations
WHERE id NOT IN (SELECT id FROM accounts)
ON CONFLICT (id) DO NOTHING;

-- Actualizar account_id (1:1)
UPDATE organizations SET account_id = id WHERE account_id IS NULL;

-- Hacer NOT NULL y crear FK
ALTER TABLE organizations ALTER COLUMN account_id SET NOT NULL;
ALTER TABLE organizations ADD CONSTRAINT organizations_account_id_fkey 
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE;
CREATE INDEX idx_organizations_account_id ON organizations(account_id);
```

#### PASO 2: Renombrar subscriptions.account_id

```sql
-- Eliminar FK confusa
ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_organization_id_fkey;
ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_account_id_fkey;

-- Renombrar columna
ALTER TABLE subscriptions RENAME COLUMN account_id TO organization_id;

-- Crear FK correcta
ALTER TABLE subscriptions ADD CONSTRAINT subscriptions_organization_id_fkey 
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;
CREATE INDEX idx_subscriptions_organization_id ON subscriptions(organization_id);
```

#### PASO 3: Renombrar users.client_id

```sql
-- Eliminar FK y índice
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_client_id_fkey;
DROP INDEX IF EXISTS idx_users_client_master;

-- Renombrar columna
ALTER TABLE users RENAME COLUMN client_id TO organization_id;

-- Crear FK e índice
ALTER TABLE users ADD CONSTRAINT users_organization_id_fkey 
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;
CREATE INDEX idx_users_organization_master ON users(organization_id, is_master);

-- Actualizar comentario
COMMENT ON COLUMN users.organization_id IS 
    'Organization a la que pertenece el usuario. Ver organization_users para roles.';
```

---

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

---

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

# En app/api/deps.py
def get_current_client_id():  # DEPRECATED
    return get_current_organization_id()
```

---

## Notas Importantes

- ⚠️ Los aliases de compatibilidad (`Client`, `client_id`) se eliminarán en la próxima versión mayor
- ⚠️ `DeviceService` no se debe usar en código nuevo - usar `Subscription`
- ✅ Las migraciones DDL se pueden ejecutar gradualmente
- ✅ El backend es backwards-compatible con el DDL existente gracias a los aliases
- ✅ Tests actualizados y documentación completa

---

## Próximos Pasos

1. ✅ ~~**Ejecutar migraciones DDL** (FASE 4)~~ - Migraciones creadas
2. **Ejecutar `alembic upgrade head`** en cada ambiente
3. **Deprecar `is_master`** con warnings en logs
4. **Preparar para Stripe** - Account tendrá `stripe_customer_id`
5. **Implementar endpoint `/api/v1/accounts/me`**
6. **Eliminar aliases de compatibilidad** en próxima versión mayor

---

## Resumen de Cambios DDL

| Tabla | Columna | Antes | Después |
|-------|---------|-------|---------|
| `organizations` | `account_id` | No existía | FK → `accounts.id` |
| `subscriptions` | `organization_id` | `account_id` | Renombrado |
| `users` | `organization_id` | `client_id` | Renombrado |

---

**Última actualización**: Diciembre 2025
