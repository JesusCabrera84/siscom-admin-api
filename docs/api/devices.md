# API de Dispositivos

## Descripción

Endpoints para gestionar el ciclo de vida completo de dispositivos GPS/IoT con seguimiento de estados, historial de eventos y trazabilidad administrativa.

---

## Modelo de Datos

### Device

```json
{
  "device_id": "123456789012345",
  "brand": "Queclink",
  "model": "GV300",
  "firmware_version": "1.2.3",
  "client_id": "456e4567-e89b-12d3-a456-426614174000",
  "status": "asignado",
  "installed_in_unit_id": "789e4567-e89b-12d3-a456-426614174000",
  "last_comm_at": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-15T08:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "last_assignment_at": "2024-01-15T09:00:00Z",
  "notes": "Dispositivo en óptimas condiciones"
}
```

### DeviceEvent

```json
{
  "id": "abc12345-e89b-12d3-a456-426614174000",
  "device_id": "123456789012345",
  "event_type": "asignado",
  "old_status": "entregado",
  "new_status": "asignado",
  "performed_by": "def45678-e89b-12d3-a456-426614174000",
  "event_details": "Dispositivo asignado a unidad ABC-123",
  "created_at": "2024-01-15T09:00:00Z"
}
```

---

## Estados del Dispositivo

El campo `status` representa el estado actual del dispositivo en su ciclo de vida:

| Estado | Descripción | `client_id` | Puede asignarse |
|--------|-------------|-------------|-----------------|
| `nuevo` | Recién ingresado al inventario | NULL | No |
| `preparado` | Asignado a un cliente, listo para envío | Asignado | No |
| `enviado` | En camino al cliente | Asignado | No |
| `entregado` | Recibido y confirmado por cliente | Asignado | Sí |
| `asignado` | Instalado en una unidad | Asignado | No |
| `devuelto` | Devuelto al inventario | NULL | Sí |
| `inactivo` | Baja definitiva, fuera de uso | Asignado | No |

---

## Reglas de Negocio

### Por Evento

| Evento | Regla | Acción |
|--------|-------|--------|
| Registrar nuevo dispositivo | `status='nuevo'` y sin cliente asignado | Insertar registro en `devices` |
| Preparar dispositivo | Cambiar `status='preparado'` y asignar `client_id` | `PATCH /devices/{device_id}/status` |
| Enviar dispositivo | Cambiar `status='enviado'`, debe estar en estado `preparado` | `PATCH /devices/{device_id}/status` |
| Confirmar entrega | `status='entregado'`, actualizar `client_id` | Cliente o maestro lo valida |
| Asignar a unidad | `status='asignado'`, actualizar `last_assignment_at` | Se crea relación con unidad |
| Devolución | `status='devuelto'`, quitar `client_id` | Puede reintegrarse al inventario |
| Baja definitiva | `status='inactivo'` | No puede reasignarse |
| Eliminación | ❌ **Prohibida** | Trigger impide `DELETE` |

### Consideraciones Importantes

- ✅ **SIEMPRE** registrar eventos administrativos para trazabilidad
- ✅ Mantener `client_id = NULL` hasta que se realice el envío
- ✅ Actualizar `last_assignment_at` cada vez que el dispositivo se asigne a una unidad
- ✅ Sincronizar `status='asignado'` con la existencia de una fila activa en unidades
- ✅ `firmware_version` puede actualizarse y genera un evento `firmware_actualizado`
- ❌ **NUNCA** eliminar registros de dispositivos (usar estados y bitácora)

---

## Endpoints

### 1. Crear Dispositivo (Registrar en Inventario)

**POST** `/api/v1/devices/`

Registra un nuevo dispositivo en el inventario con estado `nuevo` y sin cliente asignado.

#### Headers

```
Authorization: Bearer <admin_token>
```

#### Request Body

```json
{
  "device_id": "123456789012345",
  "brand": "Queclink",
  "model": "GV300",
  "firmware_version": "1.2.3",
  "notes": "Lote 2024-01"
}
```

#### Validaciones

- `device_id`: Único, 10-50 caracteres (IMEI, serial, etc)
- `brand`: Obligatorio, máximo 100 caracteres
- `model`: Obligatorio, máximo 100 caracteres
- `firmware_version`: Opcional
- `notes`: Opcional

#### Response 201 Created

```json
{
  "device_id": "123456789012345",
  "brand": "Queclink",
  "model": "GV300",
  "firmware_version": "1.2.3",
  "client_id": null,
  "status": "nuevo",
  "installed_in_unit_id": null,
  "last_comm_at": null,
  "created_at": "2024-01-15T08:00:00Z",
  "updated_at": "2024-01-15T08:00:00Z",
  "last_assignment_at": null,
  "notes": "Lote 2024-01"
}
```

**Evento generado**: `creado` con `new_status='nuevo'`

---

### 2. Listar Todos los Dispositivos

**GET** `/api/v1/devices/`

Lista todos los dispositivos del inventario con filtros opcionales.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Query Parameters

- `status_filter` (opcional): Filtrar por estado específico (`nuevo`, `enviado`, `entregado`, `asignado`, `devuelto`, `inactivo`)
- `client_id` (opcional): Filtrar por cliente específico
- `brand` (opcional): Buscar por marca (búsqueda parcial)

#### Response 200 OK

```json
[
  {
    "device_id": "123456789012345",
    "brand": "Queclink",
    "model": "GV300",
    "firmware_version": "1.2.3",
    "client_id": "456e4567-e89b-12d3-a456-426614174000",
    "status": "asignado",
    "installed_in_unit_id": "789e4567-e89b-12d3-a456-426614174000",
    "last_comm_at": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-15T08:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "last_assignment_at": "2024-01-15T09:00:00Z",
    "notes": "Dispositivo en óptimas condiciones"
  }
]
```

#### Ejemplos

```bash
# Todos los dispositivos
GET /api/v1/devices/

# Solo dispositivos nuevos
GET /api/v1/devices/?status_filter=nuevo

# Dispositivos de un cliente específico
GET /api/v1/devices/?client_id=456e4567-e89b-12d3-a456-426614174000

# Dispositivos por marca
GET /api/v1/devices/?brand=Queclink
```

---

### 3. Listar Mis Dispositivos (Cliente)

**GET** `/api/v1/devices/my-devices`

Lista todos los dispositivos del cliente autenticado.

#### Headers

```
Authorization: Bearer <client_token>
```

#### Query Parameters

- `status_filter` (opcional): Filtrar por estado

#### Response 200 OK

```json
[
  {
    "device_id": "123456789012345",
    "brand": "Queclink",
    "model": "GV300",
    "firmware_version": "1.2.3",
    "client_id": "456e4567-e89b-12d3-a456-426614174000",
    "status": "asignado",
    "installed_in_unit_id": "789e4567-e89b-12d3-a456-426614174000",
    "last_comm_at": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-15T08:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "last_assignment_at": "2024-01-15T09:00:00Z",
    "notes": null
  }
]
```

---

### 4. Listar Dispositivos No Asignados

**GET** `/api/v1/devices/unassigned`

Lista dispositivos del cliente que NO están instalados en ninguna unidad.  
Solo incluye dispositivos con estado `preparado`, `enviado`, `entregado` o `devuelto`.

#### Headers

```
Authorization: Bearer <client_token>
```

#### Response 200 OK

```json
[
  {
    "device_id": "987654321098765",
    "brand": "Teltonika",
    "model": "FMB920",
    "firmware_version": "1.0.5",
    "client_id": "456e4567-e89b-12d3-a456-426614174000",
    "status": "entregado",
    "installed_in_unit_id": null,
    "last_comm_at": null,
    "created_at": "2024-01-15T08:00:00Z",
    "updated_at": "2024-01-15T08:00:00Z",
    "last_assignment_at": null,
    "notes": null
  }
]
```

---

### 5. Obtener Dispositivo Específico

**GET** `/api/v1/devices/{device_id}`

Obtiene el detalle completo de un dispositivo.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

- `device_id`: Identificador único del dispositivo (IMEI, serial, etc)

#### Response 200 OK

```json
{
  "device_id": "123456789012345",
  "brand": "Queclink",
  "model": "GV300",
  "firmware_version": "1.2.3",
  "client_id": "456e4567-e89b-12d3-a456-426614174000",
  "status": "asignado",
  "installed_in_unit_id": "789e4567-e89b-12d3-a456-426614174000",
  "last_comm_at": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-15T08:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "last_assignment_at": "2024-01-15T09:00:00Z",
  "notes": "Dispositivo en óptimas condiciones"
}
```

#### Errores

- **404 Not Found**: Dispositivo no encontrado

---

### 6. Actualizar Información del Dispositivo

**PATCH** `/api/v1/devices/{device_id}`

Actualiza información básica del dispositivo (marca, modelo, firmware, notas).

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

- `device_id`: Identificador único del dispositivo

#### Request Body

```json
{
  "brand": "Queclink",
  "model": "GV300W",
  "firmware_version": "1.3.0",
  "notes": "Actualizado a nueva versión"
}
```

Todos los campos son opcionales. Solo se actualizan los campos proporcionados.

#### Response 200 OK

```json
{
  "device_id": "123456789012345",
  "brand": "Queclink",
  "model": "GV300W",
  "firmware_version": "1.3.0",
  "client_id": "456e4567-e89b-12d3-a456-426614174000",
  "status": "asignado",
  "installed_in_unit_id": "789e4567-e89b-12d3-a456-426614174000",
  "last_comm_at": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-15T08:00:00Z",
  "updated_at": "2024-01-16T11:00:00Z",
  "last_assignment_at": "2024-01-15T09:00:00Z",
  "notes": "Actualizado a nueva versión"
}
```

**Evento generado**: Si se actualiza `firmware_version`, se crea evento `firmware_actualizado`

---

### 7. Cambiar Estado del Dispositivo

**PATCH** `/api/v1/devices/{device_id}/status`

Actualiza el estado del dispositivo siguiendo las reglas de negocio.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

- `device_id`: Identificador único del dispositivo

#### Request Body

##### Preparar Dispositivo (`nuevo` → `preparado`)

```json
{
  "new_status": "preparado",
  "client_id": "456e4567-e89b-12d3-a456-426614174000",
  "notes": "Dispositivo asignado y listo para envío"
}
```

**Validaciones**:
- Requiere `client_id` válido
- El cliente debe existir en el sistema

##### Enviar Dispositivo (`preparado` → `enviado`)

```json
{
  "new_status": "enviado",
  "notes": "Enviado via FedEx - Tracking: 1234567890"
}
```

**Validaciones**:
- El dispositivo debe estar en estado `preparado`

##### Confirmar Entrega (`enviado` → `entregado`)

```json
{
  "new_status": "entregado",
  "notes": "Recibido por Juan Pérez"
}
```

**Validaciones**:
- El dispositivo debe tener `client_id` asignado

##### Asignar a Unidad (`entregado` → `asignado`)

```json
{
  "new_status": "asignado",
  "unit_id": "789e4567-e89b-12d3-a456-426614174000",
  "notes": "Instalado en camión ABC-123"
}
```

**Validaciones**:
- Requiere `unit_id` válido
- La unidad debe pertenecer al cliente del dispositivo
- Actualiza `installed_in_unit_id` y `last_assignment_at`

##### Devolver Dispositivo (`cualquier estado` → `devuelto`)

```json
{
  "new_status": "devuelto",
  "notes": "Dispositivo devuelto por cliente, funciona correctamente"
}
```

**Efecto**:
- Quita `client_id` (vuelve a NULL)
- Quita `installed_in_unit_id` (vuelve a NULL)
- Puede reintegrarse al inventario

##### Dar de Baja (`cualquier estado` → `inactivo`)

```json
{
  "new_status": "inactivo",
  "notes": "Dispositivo dañado, no reparable"
}
```

**Efecto**:
- Baja definitiva
- No puede reasignarse

#### Response 200 OK

```json
{
  "device_id": "123456789012345",
  "brand": "Queclink",
  "model": "GV300",
  "firmware_version": "1.2.3",
  "client_id": "456e4567-e89b-12d3-a456-426614174000",
  "status": "asignado",
  "installed_in_unit_id": "789e4567-e89b-12d3-a456-426614174000",
  "last_comm_at": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-15T08:00:00Z",
  "updated_at": "2024-01-16T11:00:00Z",
  "last_assignment_at": "2024-01-16T11:00:00Z",
  "notes": "Instalado en camión ABC-123"
}
```

**Evento generado**: Se crea evento con tipo igual al nuevo estado

#### Errores

- **400 Bad Request**: Estado inválido o falta parámetro requerido
- **404 Not Found**: Dispositivo, cliente o unidad no encontrados

---

### 8. Obtener Historial de Eventos

**GET** `/api/v1/devices/{device_id}/events`

Obtiene el historial completo de eventos de un dispositivo.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

- `device_id`: Identificador único del dispositivo

#### Response 200 OK

```json
[
  {
    "id": "abc12345-e89b-12d3-a456-426614174000",
    "device_id": "123456789012345",
    "event_type": "asignado",
    "old_status": "entregado",
    "new_status": "asignado",
    "performed_by": "def45678-e89b-12d3-a456-426614174000",
    "event_details": "Dispositivo asignado a unidad ABC-123",
    "created_at": "2024-01-15T09:00:00Z"
  },
  {
    "id": "def45678-e89b-12d3-a456-426614174000",
    "device_id": "123456789012345",
    "event_type": "entregado",
    "old_status": "enviado",
    "new_status": "entregado",
    "performed_by": "def45678-e89b-12d3-a456-426614174000",
    "event_details": "Dispositivo entregado y confirmado por el cliente",
    "created_at": "2024-01-14T15:30:00Z"
  },
  {
    "id": "ghi78901-e89b-12d3-a456-426614174000",
    "device_id": "123456789012345",
    "event_type": "enviado",
    "old_status": "nuevo",
    "new_status": "enviado",
    "performed_by": "def45678-e89b-12d3-a456-426614174000",
    "event_details": "Dispositivo enviado a cliente ACME Corp",
    "created_at": "2024-01-10T10:00:00Z"
  },
  {
    "id": "jkl01234-e89b-12d3-a456-426614174000",
    "device_id": "123456789012345",
    "event_type": "creado",
    "old_status": null,
    "new_status": "nuevo",
    "performed_by": "def45678-e89b-12d3-a456-426614174000",
    "event_details": "Dispositivo Queclink GV300 registrado en inventario",
    "created_at": "2024-01-10T08:00:00Z"
  }
]
```

---

### 9. Agregar Nota al Dispositivo

**POST** `/api/v1/devices/{device_id}/notes`

Agrega una nota administrativa al dispositivo y registra un evento.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

- `device_id`: Identificador único del dispositivo

#### Query Parameters

- `note`: La nota a agregar (string)

#### Request Example

```bash
POST /api/v1/devices/123456789012345/notes?note=Dispositivo%20revisado%20y%20funcionando%20correctamente
```

#### Response 200 OK

```json
{
  "device_id": "123456789012345",
  "brand": "Queclink",
  "model": "GV300",
  "firmware_version": "1.2.3",
  "client_id": "456e4567-e89b-12d3-a456-426614174000",
  "status": "asignado",
  "installed_in_unit_id": "789e4567-e89b-12d3-a456-426614174000",
  "last_comm_at": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-15T08:00:00Z",
  "updated_at": "2024-01-16T11:00:00Z",
  "last_assignment_at": "2024-01-15T09:00:00Z",
  "notes": "2024-01-16T11:00:00: Dispositivo revisado y funcionando correctamente"
}
```

**Evento generado**: `nota` con el contenido de la nota

---

## Tipos de Eventos

| Tipo | Descripción | Cuándo se genera |
|------|-------------|------------------|
| `creado` | Dispositivo registrado | Al crear dispositivo |
| `preparado` | Dispositivo preparado para envío | Al cambiar a estado `preparado` |
| `enviado` | Dispositivo enviado a cliente | Al cambiar a estado `enviado` |
| `entregado` | Dispositivo recibido | Al confirmar entrega |
| `asignado` | Dispositivo instalado en unidad | Al asignar a unidad |
| `devuelto` | Dispositivo devuelto | Al marcar como devuelto |
| `firmware_actualizado` | Actualización de firmware | Al actualizar `firmware_version` |
| `nota` | Nota administrativa | Al agregar nota |
| `estado_cambiado` | Cambio de estado genérico | En cambios no específicos |

---

## Protección de Datos

### Trigger: Impedir Eliminación

Un trigger en la base de datos **impide** eliminar dispositivos:

```sql
CREATE TRIGGER trg_no_delete_devices
BEFORE DELETE ON devices
FOR EACH ROW EXECUTE FUNCTION prevent_device_delete();
```

**Motivo**: Mantener historial completo e integridad de auditoría.

**Alternativa**: Usar estado `inactivo` para dar de baja dispositivos.

---

## Flujo Completo de Ciclo de Vida

```
1. REGISTRAR
   POST /devices/ → status='nuevo'
   
2. PREPARAR
   PATCH /devices/{id}/status → status='preparado', client_id=<cliente>
   
3. ENVIAR
   PATCH /devices/{id}/status → status='enviado'
   
4. CONFIRMAR ENTREGA
   PATCH /devices/{id}/status → status='entregado'
   
5. ASIGNAR A UNIDAD
   PATCH /devices/{id}/status → status='asignado', unit_id=<unidad>
   
6a. DEVOLVER (opcional)
    PATCH /devices/{id}/status → status='devuelto', client_id=NULL
    
6b. DAR DE BAJA (opcional)
    PATCH /devices/{id}/status → status='inactivo'
```

---

## Ejemplos Completos

### Caso 1: Nuevo Dispositivo a Cliente

```bash
# 1. Registrar dispositivo
POST /api/v1/devices/
{
  "device_id": "353451234567890",
  "brand": "Queclink",
  "model": "GV300",
  "firmware_version": "1.2.3"
}

# 2. Preparar para cliente
PATCH /api/v1/devices/353451234567890/status
{
  "new_status": "preparado",
  "client_id": "456e4567-e89b-12d3-a456-426614174000",
  "notes": "Dispositivo asignado y listo para envío"
}

# 3. Enviar al cliente
PATCH /api/v1/devices/353451234567890/status
{
  "new_status": "enviado",
  "notes": "Enviado via DHL - Tracking: ABC123"
}

# 4. Confirmar entrega
PATCH /api/v1/devices/353451234567890/status
{
  "new_status": "entregado",
  "notes": "Recibido por María González"
}

# 5. Asignar a unidad
PATCH /api/v1/devices/353451234567890/status
{
  "new_status": "asignado",
  "unit_id": "789e4567-e89b-12d3-a456-426614174000",
  "notes": "Instalado en camión XYZ-789"
}

# 6. Ver historial
GET /api/v1/devices/353451234567890/events
```

### Caso 2: Dispositivo Devuelto

```bash
# Cliente devuelve dispositivo
PATCH /api/v1/devices/353451234567890/status
{
  "new_status": "devuelto",
  "notes": "Cliente canceló servicio"
}

# El dispositivo queda disponible para reasignación
GET /api/v1/devices/?status_filter=devuelto
```

---

## Consideraciones de Seguridad

### Multi-tenant

- Validación de `client_id` en todas las operaciones
- Aislamiento de datos por cliente
- No es posible acceder a dispositivos de otros clientes

### Auditoría

- Todos los cambios registrados en `device_events`
- `performed_by` identifica quién realizó la acción
- Timestamps automáticos

### Integridad

- Relaciones con clientes y unidades validadas
- Estados controlados por CHECK constraints
- Eliminación bloqueada por trigger

---

## Consultas Útiles

```bash
# Dispositivos nuevos en inventario
GET /api/v1/devices/?status_filter=nuevo

# Dispositivos preparados para envío
GET /api/v1/devices/?status_filter=preparado

# Dispositivos en tránsito
GET /api/v1/devices/?status_filter=enviado

# Dispositivos de un cliente
GET /api/v1/devices/?client_id=456e4567-e89b-12d3-a456-426614174000

# Dispositivos activos (asignados)
GET /api/v1/devices/?status_filter=asignado

# Dispositivos disponibles para asignación (cliente específico)
GET /api/v1/devices/unassigned

# Historial completo de un dispositivo
GET /api/v1/devices/353451234567890/events
```
