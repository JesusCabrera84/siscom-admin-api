# API de Eventos de Dispositivos

## Descripción

Endpoints para consultar el historial completo de eventos de dispositivos GPS. Los eventos representan todas las acciones administrativas realizadas sobre un dispositivo (creación, cambios de estado, asignaciones, desasignaciones, etc.).

Este es el registro de auditoría para la trazabilidad de cada dispositivo.

---

## Endpoints

### 1. Obtener Historial de Eventos de un Dispositivo

**GET** `/api/v1/device-events/{device_id}`

Retorna el historial completo de eventos de un dispositivo específico en orden cronológico descendente (del más reciente al más antiguo).

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `device_id` | string | IMEI del dispositivo (15 dígitos) |

#### Response 200 OK

```json
[
  {
    "id": "abc12345-e89b-12d3-a456-426614174000",
    "device_id": "123456789012345",
    "event_type": "status_change",
    "old_status": "disponible",
    "new_status": "asignado",
    "performed_by": "789e4567-e89b-12d3-a456-426614174000",
    "event_details": "Dispositivo asignado a unidad VH-001",
    "created_at": "2024-02-04T10:30:00Z"
  },
  {
    "id": "def67890-e89b-12d3-a456-426614174000",
    "device_id": "123456789012345",
    "event_type": "created",
    "old_status": null,
    "new_status": "disponible",
    "performed_by": "789e4567-e89b-12d3-a456-426614174000",
    "event_details": "Dispositivo creado en inventario",
    "created_at": "2024-02-01T08:00:00Z"
  }
]
```

#### Tipos de Eventos

| Tipo | Descripción |
|------|-------------|
| `created` | Dispositivo creado en el sistema |
| `status_change` | Cambio de estado del dispositivo |
| `assigned` | Dispositivo asignado a una unidad |
| `unassigned` | Dispositivo desasignado de una unidad |
| `updated` | Información del dispositivo actualizada |
| `sim_attached` | Tarjeta SIM asociada al dispositivo |
| `sim_detached` | Tarjeta SIM desvinculada del dispositivo |
| `notes_updated` | Notas del dispositivo actualizadas |

#### Estados de Dispositivos

| Estado | Descripción |
|--------|-------------|
| `disponible` | Dispositivo en inventario, listo para asignar |
| `asignado` | Dispositivo asignado a una unidad/vehículo |
| `en_mantenimiento` | Dispositivo en reparación o mantenimiento |
| `baja` | Dispositivo dado de baja permanentemente |

#### Errores

**404 Not Found**
```json
{
  "detail": "Dispositivo no encontrado"
}
```

**401 Unauthorized**
```json
{
  "detail": "No autenticado"
}
```

---

## Casos de Uso

### 1. Auditoría de Dispositivo

Obtener el historial completo de un dispositivo para auditoría:

```bash
curl -X GET "https://api.tudominio.com/api/v1/device-events/123456789012345" \
  -H "Authorization: Bearer <access_token>"
```

### 2. Verificar Última Asignación

Consultar cuándo y quién asignó el dispositivo por última vez:

```bash
curl -X GET "https://api.tudominio.com/api/v1/device-events/123456789012345" \
  -H "Authorization: Bearer <access_token>"
```

Luego filtrar en el cliente por `event_type: "assigned"` y tomar el más reciente.

### 3. Trazabilidad de Cambios de Estado

Rastrear todos los cambios de estado del dispositivo:

```bash
curl -X GET "https://api.tudominio.com/api/v1/device-events/123456789012345" \
  -H "Authorization: Bearer <access_token>"
```

Filtrar por `event_type: "status_change"` para ver la evolución de estados.

---

## Notas Técnicas

### Relación con Otros Endpoints

- Los eventos se crean automáticamente cuando se realizan operaciones en `/api/v1/devices/`
- El campo `performed_by` referencia al usuario que realizó la acción
- Los eventos son **inmutables** - no pueden editarse ni eliminarse

### Ordenamiento

Los eventos siempre se devuelven ordenados del más reciente al más antiguo (`created_at DESC`).

### Paginación

Actualmente este endpoint **no implementa paginación**. Si un dispositivo tiene muchos eventos, se devolverán todos. Considere implementar paginación en futuras versiones si los registros crecen significativamente.

### Permisos

- Requiere autenticación con token JWT de Cognito
- El usuario debe tener acceso a la organización propietaria del dispositivo
- No hay restricciones específicas de roles - cualquier miembro de la organización puede consultar eventos

---

## Modelo de Datos

### DeviceEvent

```json
{
  "id": "uuid",
  "device_id": "string (15 chars)",
  "event_type": "string",
  "old_status": "string | null",
  "new_status": "string | null",
  "performed_by": "uuid | null",
  "event_details": "string | null",
  "created_at": "datetime"
}
```

#### Campos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID | Identificador único del evento |
| `device_id` | string | IMEI del dispositivo (15 dígitos) |
| `event_type` | string | Tipo de evento (ver tabla de tipos) |
| `old_status` | string/null | Estado anterior (solo para status_change) |
| `new_status` | string/null | Estado nuevo (solo para status_change) |
| `performed_by` | UUID/null | ID del usuario que realizó la acción |
| `event_details` | string/null | Descripción adicional del evento |
| `created_at` | datetime | Fecha y hora del evento (ISO 8601) |

---

## Referencias

- [API de Dispositivos](./devices.md) - Gestión de dispositivos
- [API de Units](./units.md) - Asignación de dispositivos a unidades
- [Modelo Organizacional](../guides/organizational-model.md) - Permisos y roles
