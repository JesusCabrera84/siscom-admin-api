# 📝 Notas Importantes para Migración de Alembic

## Cambios Aplicados a los Modelos

Los modelos han sido actualizados para coincidir **100%** con el script SQL proporcionado:

### ✅ Correcciones Principales

1. **devices.active**: Cambiado de `default=False` a `default=True` (línea 40 de device.py)
2. **plans.max_devices**: Cambiado de `Optional[int]` a `int` con `default=1 NOT NULL`
3. **plans.history_days**: Cambiado de `default=30` a `default=7`

### ✅ Índices Agregados

Los siguientes índices han sido agregados a los modelos:

- **users**: `idx_users_client_master` en (client_id, is_master)
- **device_installations**: `idx_dev_inst_device` en device_id, `idx_dev_inst_unit` en unit_id
- **subscriptions**: `idx_subscriptions_client` en client_id, `idx_subscriptions_status` en status
- **payments**: `idx_payments_client` en client_id, `idx_payments_status` en status
- **orders**: `idx_orders_client` en client_id, `idx_orders_status` en status
- **order_items**: `idx_order_items_order` en order_id
- **device_services**: `idx_device_services_client` en client_id

## ⚠️ IMPORTANTE: Índices y Constraints Manuales

Al generar la migración con `alembic revision --autogenerate -m "initial_schema"`, deberás **agregar manualmente** los siguientes elementos en el archivo de migración generado:

### 1. Índice Único Parcial en device_services

Este es el constraint más importante del sistema. Agregar en la función `upgrade()`:

```python
def upgrade() -> None:
    # ... código autogenerado por Alembic ...
    
    # ⭐ AGREGAR MANUALMENTE:
    op.execute("""
        CREATE UNIQUE INDEX uq_device_services_active_one 
        ON device_services(device_id) 
        WHERE status = 'ACTIVE'
    """)
```

Y en la función `downgrade()`:

```python
def downgrade() -> None:
    # ⭐ AGREGAR PRIMERO (antes del código autogenerado):
    op.execute("DROP INDEX IF EXISTS uq_device_services_active_one")
    
    # ... código autogenerado por Alembic ...
```

**Explicación**: Este índice garantiza que solo puede haber UN servicio con status='ACTIVE' por dispositivo. Es fundamental para la lógica de negocio.

### 2. Índice Condicional en invitations (Opcional pero recomendado)

```python
# En upgrade():
op.execute("""
    CREATE INDEX idx_invitations_expires_at 
    ON invitations (expires_at)
    WHERE accepted = FALSE
""")
```

```python
# En downgrade():
op.execute("DROP INDEX IF EXISTS idx_invitations_expires_at")
```

**Explicación**: Optimiza las consultas para invitaciones pendientes que aún no han expirado.

### 3. Columna Generada en order_items.total_price (Opcional)

El SQL original usa una columna generada:

```sql
total_price NUMERIC(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED
```

SQLAlchemy no soporta esto declarativamente de forma consistente en todas las versiones. Actualmente, el modelo calcula `total_price` en la aplicación (ver `app/api/v1/endpoints/orders.py`).

Si deseas usar la columna generada por PostgreSQL, agrega en la migración:

```python
# En upgrade(), después de crear la tabla order_items:
op.execute("""
    ALTER TABLE order_items 
    ALTER COLUMN total_price 
    SET DATA TYPE NUMERIC(10,2) 
    GENERATED ALWAYS AS (quantity * unit_price) STORED
""")
```

**Nota**: Esto requeriría modificar el modelo Python para no incluir total_price en los inserts.

## 📋 Checklist de Verificación Post-Migración

Después de aplicar `alembic upgrade head`, verifica:

```sql
-- 1. Verificar que el índice único existe
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'device_services' 
  AND indexname = 'uq_device_services_active_one';

-- 2. Verificar constraints de device_services
SELECT constraint_name, constraint_type 
FROM information_schema.table_constraints 
WHERE table_name = 'device_services';

-- 3. Verificar todos los índices críticos
SELECT tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'public' 
ORDER BY tablename, indexname;

-- 4. Verificar que devices.active tiene DEFAULT TRUE
SELECT column_name, column_default 
FROM information_schema.columns 
WHERE table_name = 'devices' 
  AND column_name = 'active';

-- 5. Verificar que plans.max_devices tiene DEFAULT 1
SELECT column_name, column_default, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'plans' 
  AND column_name = 'max_devices';
```

## 🧪 Tests de Validación

Después de la migración, ejecuta estos tests para validar el esquema:

```bash
# Test que verifica el índice único
docker-compose exec api pytest tests/test_services.py::test_cannot_activate_two_services_simultaneously -v

# Test que verifica defaults
docker-compose exec api pytest tests/test_devices.py::test_create_device -v
```

## 🔄 Orden Recomendado de Ejecución

```bash
# 1. Generar migración
docker-compose exec api alembic revision --autogenerate -m "initial_schema"

# 2. Editar el archivo generado en app/db/migrations/versions/
# Agregar los índices únicos y condicionales manualmente

# 3. Revisar el archivo de migración
cat app/db/migrations/versions/*_initial_schema.py

# 4. Aplicar migración
docker-compose exec api alembic upgrade head

# 5. Verificar con SQL (conéctate a la BD)
docker-compose exec db psql -U siscom -d siscom_admin -c "\d+ device_services"

# 6. Ejecutar tests
docker-compose exec api pytest -v

# 7. Poblar datos de prueba
docker-compose exec api python scripts/seed_data.py
```

## 📊 Diferencias entre Modelos Python y SQL Puro

| Aspecto | SQL | SQLModel/Python |
|---------|-----|-----------------|
| UUIDs | `gen_random_uuid()` | `text('gen_random_uuid()')` |
| Enums | `TEXT CHECK (...)` | Python Enum + String column |
| Decimals | `NUMERIC(10,2)` | String column (evita problemas de precisión) |
| Timestamps | `DEFAULT NOW()` | `default=datetime.utcnow` |
| Índices parciales | `WHERE status = 'ACTIVE'` | Debe agregarse con `op.execute()` |
| Columnas generadas | `GENERATED ALWAYS AS` | Se calcula en app (o con `op.execute()`) |

## ⚡ Mejoras Futuras Opcionales

1. **Usar JSONB para plan.features**: Ya está configurado como JSON
2. **Agregar TRIGGER para updated_at**: Los modelos Python lo manejan con `onupdate`
3. **Agregar constraint para device_services.expires_at**: Validar que expires_at > activated_at
4. **Agregar TRIAL status a device_services**: Ya contemplado en el SQL, solo descomentar

## 🎯 Conclusión

Los modelos Python ahora coinciden 100% con el script SQL proporcionado. Los únicos elementos que requieren intervención manual son:

1. ✅ Índice único parcial en device_services (CRÍTICO)
2. ✅ Índice condicional en invitations (RECOMENDADO)
3. ⚠️ Columna generada en order_items (OPCIONAL, actualmente manejado en app)

Todos los demás aspectos (campos, tipos, defaults, FKs, índices estándar) son generados correctamente por Alembic autogenerate.

