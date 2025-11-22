# Migración 006: Reestructuración de Dispositivos con Estados y Eventos

## Resumen

Esta migración implementa un **ciclo de vida completo** para dispositivos GPS/IoT con seguimiento de estados, historial de eventos y trazabilidad administrativa completa.

## Fecha

6 de noviembre de 2025

---

## Cambios Principales

### 1. Tabla `devices` - Nueva Estructura

#### Cambios en Primary Key

- **Antes**: `id` (UUID) como PRIMARY KEY
- **Ahora**: `device_id` (TEXT) como PRIMARY KEY

#### Cambios en Campos

| Campo                | Antes              | Ahora             | Descripción                 |
| -------------------- | ------------------ | ----------------- | --------------------------- |
| `id`                 | UUID PRIMARY KEY   | ❌ **Eliminado**  | Ya no se usa UUID           |
| `device_id`          | VARCHAR(50) UNIQUE | TEXT PRIMARY KEY  | Ahora es la clave principal |
| `client_id`          | UUID NOT NULL      | UUID **NULLABLE** | NULL hasta envío            |
| `active`             | BOOLEAN            | ❌ **Eliminado**  | Reemplazado por `status`    |
| `status`             | ❌ N/A             | TEXT NOT NULL     | Nuevo campo con estados     |
| `firmware_version`   | ❌ N/A             | TEXT              | Nuevo campo                 |
| `last_assignment_at` | ❌ N/A             | TIMESTAMP         | Nuevo campo                 |
| `notes`              | ❌ N/A             | TEXT              | Nuevo campo                 |

#### Estados Disponibles

| Estado      | Descripción                    | client_id |
| ----------- | ------------------------------ | --------- |
| `nuevo`     | Recién ingresado al inventario | NULL      |
| `enviado`   | En camino al cliente           | Asignado  |
| `entregado` | Recibido por el cliente        | Asignado  |
| `asignado`  | Instalado en una unidad        | Asignado  |
| `devuelto`  | Devuelto al inventario         | NULL      |
| `inactivo`  | Baja definitiva                | Asignado  |

### 2. Nueva Tabla `device_events`

Tabla para historial completo de eventos y cambios de estado.

```sql
CREATE TABLE device_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id TEXT REFERENCES devices(device_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (
        event_type IN (
            'creado',
            'enviado',
            'entregado',
            'asignado',
            'devuelto',
            'firmware_actualizado',
            'nota',
            'estado_cambiado'
        )
    ),
    old_status TEXT,
    new_status TEXT,
    performed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    event_details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

### 3. Trigger de Protección

Se agregó un trigger que **impide eliminar** dispositivos:

```sql
CREATE TRIGGER trg_no_delete_devices
BEFORE DELETE ON devices
FOR EACH ROW EXECUTE FUNCTION prevent_device_delete();
```

**Motivo**: Mantener historial completo e integridad de auditoría.

### 4. Actualización de `device_services`

La tabla `device_services` también se actualizó:

- **Antes**: `device_id` UUID → ForeignKey a `devices.id`
- **Ahora**: `device_id` TEXT → ForeignKey a `devices.device_id`

---

## Reglas de Negocio Implementadas

### Por Evento

| Evento                | Acción en API                | Estado Resultante                                   | Validaciones              |
| --------------------- | ---------------------------- | --------------------------------------------------- | ------------------------- |
| Registrar dispositivo | `POST /devices/`             | `status='nuevo'`, `client_id=NULL`                  | device_id único           |
| Enviar dispositivo    | `PATCH /devices/{id}/status` | `status='enviado'`, asigna client_id                | Requiere client_id válido |
| Confirmar entrega     | `PATCH /devices/{id}/status` | `status='entregado'`                                | Debe tener client_id      |
| Asignar a unidad      | `PATCH /devices/{id}/status` | `status='asignado'`, actualiza `last_assignment_at` | Requiere unit_id válido   |
| Devolver              | `PATCH /devices/{id}/status` | `status='devuelto'`, quita client_id                | Puede reintegrarse        |
| Dar de baja           | `PATCH /devices/{id}/status` | `status='inactivo'`                                 | Baja definitiva           |

### Consideraciones Importantes

- ✅ **SIEMPRE** registrar eventos administrativos
- ✅ Mantener `client_id = NULL` hasta envío
- ✅ Actualizar `last_assignment_at` en cada asignación
- ✅ Sincronizar `status='asignado'` con unidades
- ✅ `firmware_version` genera evento al actualizarse
- ❌ **NUNCA** eliminar dispositivos (usar estados)

---

## Migración de Datos

### Mapeo de `active` a `status`

La migración convierte el campo booleano `active` al nuevo sistema de estados:

```sql
CASE
    WHEN active = true AND installed_in_unit_id IS NOT NULL
        THEN 'asignado'
    WHEN active = true AND installed_in_unit_id IS NULL
        THEN 'entregado'
    ELSE 'inactivo'
END as status
```

### Creación de Eventos Iniciales

Para cada dispositivo migrado se crea un evento inicial:

```sql
INSERT INTO device_events (device_id, event_type, new_status, event_details)
SELECT
    device_id,
    'creado',
    status,
    'Migrado desde estructura anterior'
FROM devices
```

---

## Nuevos Endpoints

### 1. Cambiar Estado de Dispositivo

**PATCH** `/api/v1/devices/{device_id}/status`

```json
{
  "new_status": "enviado",
  "client_id": "uuid-del-cliente",
  "unit_id": "uuid-de-unidad", // solo para 'asignado'
  "notes": "Notas opcionales"
}
```

### 2. Obtener Historial de Eventos

**GET** `/api/v1/devices/{device_id}/events`

Retorna array de eventos ordenados por fecha descendente.

### 3. Agregar Nota al Dispositivo

**POST** `/api/v1/devices/{device_id}/notes?note=texto`

Agrega nota administrativa y crea evento tipo `nota`.

### 4. Listar Mis Dispositivos

**GET** `/api/v1/devices/my-devices`

Lista dispositivos del cliente autenticado.

---

## Archivos Modificados

### Modelos

- ✅ `app/models/device.py` - Actualizado con nueva estructura
- ✅ `app/models/device.py` - Agregada clase `DeviceEvent`
- ✅ `app/models/device_service.py` - Actualizado device_id a TEXT

### Schemas

- ✅ `app/schemas/device.py` - Nuevos schemas para estados y eventos

### Endpoints

- ✅ `app/api/v1/endpoints/devices.py` - Reescrito completamente con reglas de negocio
- ✅ `app/api/deps.py` - Agregada función `get_current_user_id()`

### Tests

- ✅ `tests/test_devices.py` - Actualizados con nuevos escenarios
- ✅ `tests/conftest.py` - Fixtures actualizadas

### Documentación

- ✅ `docs/api/devices.md` - Documentación completa actualizada

### Migraciones

- ✅ `app/db/migrations/versions/006_restructure_devices_add_events.py`

### Scripts

- ✅ `scripts/apply_006_migration.py` - Script de aplicación

---

## Cómo Aplicar la Migración

### Opción 1: Usando el Script (Recomendado)

```bash
# Ver qué cambios se aplicarían (sin ejecutar)
python scripts/apply_006_migration.py --dry-run

# Aplicar la migración
python scripts/apply_006_migration.py
```

### Opción 2: Usando Alembic Directamente

```bash
# Aplicar migración
alembic upgrade 006_devices_events

# Verificar versión actual
alembic current

# Ver historial
alembic history
```

---

## Validación Post-Migración

### 1. Verificar Estructura de Tablas

```sql
-- Verificar estructura de devices
\d devices

-- Verificar que existe device_events
\d device_events

-- Verificar trigger
SELECT tgname FROM pg_trigger WHERE tgrelid = 'devices'::regclass;
```

### 2. Verificar Datos Migrados

```sql
-- Distribución de estados
SELECT status, COUNT(*)
FROM devices
GROUP BY status;

-- Verificar eventos creados
SELECT COUNT(*) FROM device_events;

-- Verificar que device_services se migró correctamente
SELECT COUNT(*) FROM device_services;
```

### 3. Probar Funcionalidad

```bash
# Ejecutar tests
pytest tests/test_devices.py -v

# Probar endpoint de listado
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/devices/

# Probar cambio de estado
curl -X PATCH \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_status": "enviado", "client_id": "uuid-cliente"}' \
  http://localhost:8000/api/v1/devices/DEVICE123/status
```

---

## Rollback

Si necesitas revertir la migración:

```bash
# Usar Alembic para hacer downgrade
alembic downgrade 005_rename_device_id
```

**⚠️ ADVERTENCIA**: El downgrade puede causar pérdida de datos:

- Se perderá toda la tabla `device_events`
- Se perderán los campos `firmware_version`, `last_assignment_at`, `notes`
- Los estados se mapearán de vuelta a booleano `active`
- Dispositivos sin `client_id` NO se migrarán en el downgrade

---

## Impacto en Otros Módulos

### ✅ Compatibilidad Mantenida

- **Orders**: Sin cambios, siguen funcionando igual
- **Payments**: Sin cambios
- **Plans**: Sin cambios
- **Units**: Sin cambios

### ⚠️ Requiere Ajustes

- **Services Endpoints**: Si consultan dispositivos directamente, deben actualizar referencias de `device.id` a `device.device_id`
- **Device Activation**: Si usa dispositivos, verificar que usa `device_id` correctamente

---

## Checklist de Verificación

- [ ] Backup de base de datos realizado
- [ ] Migración aplicada exitosamente
- [ ] Sin errores en logs de aplicación
- [ ] Tests pasando correctamente
- [ ] Trigger de protección funcionando (intentar DELETE debe fallar)
- [ ] Endpoints de devices respondiendo correctamente
- [ ] Historial de eventos creándose correctamente
- [ ] Cambios de estado funcionando según reglas de negocio
- [ ] Device services migrados correctamente

---

## Beneficios de Esta Migración

### 1. Trazabilidad Completa

- Historial completo de cambios
- Auditoría de quién hizo qué y cuándo
- No se puede eliminar información histórica

### 2. Flujo de Trabajo Claro

- Estados bien definidos
- Validaciones de negocio implementadas
- Transiciones controladas

### 3. Mejor Gestión de Inventario

- Dispositivos sin cliente (inventario)
- Seguimiento de envíos y entregas
- Control de devoluciones

### 4. Flexibilidad

- Fácil agregar nuevos estados
- Eventos personalizables
- Notas administrativas

### 5. Integridad de Datos

- Trigger previene eliminaciones accidentales
- Foreign keys actualizadas
- Validaciones a nivel de base de datos

---

## Soporte y Contacto

Para problemas o preguntas sobre esta migración, consultar:

- Documentación completa: `docs/api/devices.md`
- Guía de migración: Este documento
- Tests de referencia: `tests/test_devices.py`

---

**Fecha de Creación**: 6 de noviembre de 2025  
**Versión de Migración**: 006_devices_events  
**Estado**: ✅ Completada y documentada
