# Migración 005: Renombrar IMEI a Device ID

## Descripción

Esta migración renombra la columna `imei` a `device_id` en la tabla `devices`. Este cambio afecta:

- ✅ Modelo de datos (`Device`)
- ✅ Schemas de API (`DeviceBase`, `DeviceCreate`, `DeviceOut`)
- ✅ Endpoints de dispositivos y servicios
- ✅ Tests
- ✅ Scripts de seed data
- ✅ Documentación

## Cambios en Base de Datos

```sql
-- Eliminar índice antiguo
DROP INDEX IF EXISTS idx_devices_imei;

-- Renombrar columna
ALTER TABLE devices RENAME COLUMN imei TO device_id;

-- Crear nuevo índice
CREATE INDEX idx_devices_device_id ON devices(device_id);
```

## Aplicar la Migración

### Opción 1: Usando Alembic (Recomendado)

```bash
# Desde el directorio raíz del proyecto
alembic upgrade 005
```

### Opción 2: Usando el Script de Python

```bash
# Desde el directorio raíz del proyecto
python scripts/apply_005_migration.py
```

### Opción 3: SQL Directo

Si prefieres aplicar el SQL manualmente:

```bash
psql -U tu_usuario -d tu_database -f scripts/apply_005_migration.sql
```

## Verificar la Migración

Después de aplicar la migración, verifica que el cambio se realizó correctamente:

```sql
-- Verificar que la columna device_id existe
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'devices' 
  AND column_name = 'device_id';

-- Verificar que el índice existe
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'devices' 
  AND indexname = 'idx_devices_device_id';

-- Verificar que la columna antigua no existe
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'devices' 
  AND column_name = 'imei';
-- Debe retornar 0 filas
```

## Compatibilidad hacia atrás

Esta migración **NO es compatible hacia atrás**. Si necesitas revertir:

```bash
# Revertir con Alembic
alembic downgrade 004
```

## Impacto en el Sistema

### ⚠️ Aplicaciones que se deben actualizar

1. **API Backend**: Ya actualizado en este commit
2. **Frontend/Aplicaciones Cliente**: Deben actualizar todas las referencias de `imei` a `device_id`
3. **Integraciones Externas**: Cualquier sistema que consuma la API debe actualizar sus llamadas

### Endpoints Afectados

```bash
# Crear dispositivo
POST /api/v1/devices/
{
  "device_id": "353451234567890",  # Antes: "imei"
  "brand": "Queclink",
  "model": "GV300"
}

# Respuesta de listado de dispositivos
GET /api/v1/devices/
[
  {
    "id": "...",
    "device_id": "353451234567890",  # Antes: "imei"
    ...
  }
]

# Respuesta de servicios activos
GET /api/v1/services/active
[
  {
    "id": "...",
    "device_device_id": "353451234567890",  # Antes: "device_imei"
    ...
  }
]
```

## Datos Existentes

✅ **Todos los datos existentes se preservan**. La migración solo renombra la columna, no elimina ni modifica datos.

## Testing

Después de aplicar la migración, ejecuta los tests para verificar:

```bash
# Tests de dispositivos
pytest tests/test_devices.py -v

# Tests de servicios
pytest tests/test_services.py -v

# Todos los tests
pytest -v
```

## Rollback de Emergencia

Si encuentras problemas después de aplicar la migración:

```bash
# 1. Revertir la migración de base de datos
alembic downgrade 004

# 2. Revertir el código a la versión anterior
git revert HEAD

# 3. Reiniciar el servidor
```

## Orden de Despliegue Recomendado

Para minimizar el tiempo de inactividad:

1. **Aplicar migración de BD** (la columna mantiene los datos)
2. **Desplegar nueva versión del backend** (con código actualizado)
3. **Actualizar frontend/clientes** (para usar nuevo campo)

## Preguntas Frecuentes

### ¿Por qué renombrar de imei a device_id?

El término `device_id` es más genérico y permite flexibilidad para diferentes tipos de identificadores de dispositivos en el futuro.

### ¿Afecta el rendimiento?

No. El renombramiento de columnas es una operación DDL que no afecta el rendimiento. El índice se recrea correctamente.

### ¿Qué pasa con los datos existentes?

Todos los datos se preservan. Es solo un cambio de nombre de columna.

### ¿Necesito actualizar datos en la BD?

No. Solo necesitas aplicar la migración. El contenido de la columna permanece igual.

## Soporte

Si encuentras problemas con la migración, contacta al equipo de desarrollo o revisa los logs de Alembic:

```bash
# Ver historial de migraciones
alembic history

# Ver migración actual
alembic current

# Ver SQL que se ejecutará (sin aplicar)
alembic upgrade 005 --sql
```

