# API de Asignaciones Unidad-Dispositivo

## Descripción

Endpoints para gestionar las asignaciones de dispositivos GPS a unidades (vehículos, maquinaria, etc.). Este módulo controla qué dispositivos están instalados en qué unidades, mantiene un historial completo de asignaciones, y garantiza la integridad de los estados.

Cada asignación representa una instalación física del dispositivo en la unidad, con fechas de inicio (`assigned_at`) y fin (`unassigned_at`) para mantener trazabilidad completa.

---

## Endpoints

### 1. Listar Asignaciones Unidad-Dispositivo

**GET** `/api/v1/unit-devices/`

Lista todas las asignaciones de dispositivos a unidades del cliente autenticado.

#### Permisos Requeridos

- Usuario maestro del cliente

#### Headers

```
Authorization: Bearer <access_token>
```

#### Query Parameters (opcionales)

- `active_only` (boolean): Filtrar solo asignaciones activas. Default: `true`

#### Response 200 OK

**Con `active_only=true` (default):**

```json
[
  {
    "id": "xyz12345-e89b-12d3-a456-426614174000",
    "unit_id": "abc12345-e89b-12d3-a456-426614174000",
    "device_id": "864537040123456",
    "assigned_at": "2025-11-03T08:00:00Z",
    "unassigned_at": null
  },
  {
    "id": "def67890-e89b-12d3-a456-426614174000",
    "unit_id": "ghi12345-e89b-12d3-a456-426614174000",
    "device_id": "864537040789012",
    "assigned_at": "2025-11-15T10:30:00Z",
    "unassigned_at": null
  }
]
```

**Con `active_only=false`:**

Incluye también asignaciones históricas (con `unassigned_at` no nulo):

```json
[
  {
    "id": "xyz12345-e89b-12d3-a456-426614174000",
    "unit_id": "abc12345-e89b-12d3-a456-426614174000",
    "device_id": "864537040123456",
    "assigned_at": "2025-11-03T08:00:00Z",
    "unassigned_at": null
  },
  {
    "id": "old45678-e89b-12d3-a456-426614174000",
    "unit_id": "abc12345-e89b-12d3-a456-426614174000",
    "device_id": "864537040555555",
    "assigned_at": "2025-10-01T10:00:00Z",
    "unassigned_at": "2025-11-02T18:00:00Z"
  }
]
```

---

### 2. Crear Asignación Unidad-Dispositivo

**POST** `/api/v1/unit-devices/`

Asigna un dispositivo GPS a una unidad (representa la instalación física del dispositivo).

#### Permisos Requeridos

- Usuario maestro del cliente

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "unit_id": "abc12345-e89b-12d3-a456-426614174000",
  "device_id": "864537040123456"
}
```

**Campos:**
- `unit_id` (UUID, requerido): ID de la unidad donde se instalará el dispositivo
- `device_id` (string, requerido): ID del dispositivo GPS (IMEI)

#### Validaciones

- La unidad debe existir y pertenecer al cliente autenticado
- El dispositivo debe existir y pertenecer al cliente autenticado
- El dispositivo debe estar en estado `entregado` o `devuelto`
- No debe existir una asignación activa previa del mismo dispositivo

#### Efectos Secundarios

Cuando se crea una asignación:
1. Se crea el registro en `unit_devices`
2. El estado del dispositivo cambia a `asignado`
3. Se actualiza `device.last_assignment_at`
4. Se crea un evento en `device_events` para auditoría

#### Response 201 Created

```json
{
  "id": "xyz12345-e89b-12d3-a456-426614174000",
  "unit_id": "abc12345-e89b-12d3-a456-426614174000",
  "device_id": "864537040123456",
  "assigned_at": "2025-11-21T14:45:00Z",
  "unassigned_at": null
}
```

#### Errores Comunes

- **404 Not Found**: Unidad no encontrada o no pertenece a tu cliente
- **404 Not Found**: Dispositivo no encontrado o no pertenece a tu cliente
- **400 Bad Request**: El dispositivo debe estar en estado 'entregado' o 'devuelto' (estado actual: asignado)
- **400 Bad Request**: El dispositivo ya está asignado a una unidad activa

---

### 3. Obtener Detalle de Asignación

**GET** `/api/v1/unit-devices/{assignment_id}`

Obtiene información detallada de una asignación específica, incluyendo datos de la unidad y el dispositivo.

#### Permisos Requeridos

- Usuario maestro del cliente

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
{
  "id": "xyz12345-e89b-12d3-a456-426614174000",
  "unit_id": "abc12345-e89b-12d3-a456-426614174000",
  "device_id": "864537040123456",
  "assigned_at": "2025-11-03T08:00:00Z",
  "unassigned_at": null,
  "unit_name": "Camión #45",
  "device_brand": "Suntech",
  "device_model": "ST300",
  "device_status": "asignado"
}
```

**Campos adicionales:**
- `unit_name`: Nombre de la unidad
- `device_brand`: Marca del dispositivo
- `device_model`: Modelo del dispositivo
- `device_status`: Estado actual del dispositivo

#### Errores Comunes

- **404 Not Found**: Asignación no encontrada

---

### 4. Desasignar Dispositivo de Unidad

**DELETE** `/api/v1/unit-devices/{assignment_id}`

Desasigna un dispositivo de una unidad (representa la desinstalación física del dispositivo).

#### Permisos Requeridos

- Usuario maestro del cliente

#### Headers

```
Authorization: Bearer <access_token>
```

#### Validaciones

- La asignación debe existir y pertenecer al cliente
- La asignación debe estar activa (`unassigned_at` debe ser `null`)

#### Efectos Secundarios

Cuando se desasigna un dispositivo:
1. Se marca `unassigned_at` con la fecha/hora actual (no se elimina el registro)
2. El estado del dispositivo cambia a `entregado`
3. Se crea un evento en `device_events` para auditoría

#### Response 200 OK

```json
{
  "message": "Dispositivo desasignado exitosamente",
  "assignment_id": "xyz12345-e89b-12d3-a456-426614174000",
  "device_id": "864537040123456",
  "unassigned_at": "2025-11-21T14:50:00Z"
}
```

#### Notas

- Esta operación NO elimina el registro físicamente
- Solo marca `unassigned_at`, manteniendo el historial
- El dispositivo queda en estado `entregado` y puede reasignarse a otra unidad

#### Errores Comunes

- **404 Not Found**: Asignación no encontrada
- **404 Not Found**: Dispositivo no encontrado
- **400 Bad Request**: Esta asignación ya fue desactivada

---

## Estados del Dispositivo

Los dispositivos pasan por diferentes estados durante su ciclo de vida:

```
nuevo → entregado → asignado → entregado → devuelto
                        ↓
                     activo
                        ↓
                   suspendido
                        ↓
                    inactivo
```

### Estados Relevantes para Asignaciones

- **`entregado`**: Dispositivo entregado al cliente pero no instalado en ninguna unidad
- **`devuelto`**: Dispositivo que estaba instalado pero fue removido
- **`asignado`**: Dispositivo instalado en una unidad (tiene asignación activa)

### Transiciones Automáticas

- Al crear asignación: `entregado` → `asignado`
- Al desasignar: `asignado` → `entregado`

---

## Historial de Asignaciones

### Consultar Historial Completo

Para ver todas las asignaciones (activas e históricas):

```bash
GET /api/v1/unit-devices/?active_only=false
```

Esto permite:
- Auditar cuándo se instaló cada dispositivo
- Ver cuánto tiempo estuvo instalado
- Detectar dispositivos que se reasignaron frecuentemente

### Ejemplo de Historial

Una unidad que tuvo 3 dispositivos en su historia:

```json
[
  {
    "id": "assign-3",
    "unit_id": "camion-123",
    "device_id": "IMEI-789",
    "assigned_at": "2025-11-01T08:00:00Z",
    "unassigned_at": null  // Actual
  },
  {
    "id": "assign-2",
    "unit_id": "camion-123",
    "device_id": "IMEI-456",
    "assigned_at": "2025-09-15T10:00:00Z",
    "unassigned_at": "2025-10-31T17:00:00Z"  // Estuvo 1.5 meses
  },
  {
    "id": "assign-1",
    "unit_id": "camion-123",
    "device_id": "IMEI-123",
    "assigned_at": "2025-08-01T09:00:00Z",
    "unassigned_at": "2025-09-14T16:00:00Z"  // Estuvo 1.5 meses
  }
]
```

---

## Eventos de Dispositivos

Cada operación de asignación/desasignación genera eventos en la tabla `device_events` para mantener una auditoría completa.

### Ejemplo de Eventos Generados

#### Al Asignar

```json
{
  "event_type": "asignado",
  "device_id": "864537040123456",
  "old_status": "entregado",
  "new_status": "asignado",
  "performed_by": "master-user-uuid",
  "event_details": "Dispositivo asignado a unidad 'Camión #45'",
  "created_at": "2025-11-21T14:45:00Z"
}
```

#### Al Desasignar

```json
{
  "event_type": "estado_cambiado",
  "device_id": "864537040123456",
  "old_status": "asignado",
  "new_status": "entregado",
  "performed_by": "master-user-uuid",
  "event_details": "Dispositivo desasignado de unidad 'Camión #45'",
  "created_at": "2025-11-21T14:50:00Z"
}
```

---

## Casos de Uso

### Caso 1: Instalar un Dispositivo Nuevo

Un técnico instala un dispositivo GPS nuevo en un camión:

```bash
POST /api/v1/unit-devices/
{
  "unit_id": "camion-uuid",
  "device_id": "864537040123456"
}
```

Resultado:
- Dispositivo pasa de `entregado` → `asignado`
- Se crea registro en `unit_devices`
- Se genera evento de auditoría

---

### Caso 2: Reemplazar un Dispositivo Defectuoso

Un dispositivo está fallando y se necesita reemplazar por uno nuevo:

```bash
# Paso 1: Desasignar el dispositivo defectuoso
DELETE /api/v1/unit-devices/{old-assignment-id}

# Paso 2: Asignar el nuevo dispositivo
POST /api/v1/unit-devices/
{
  "unit_id": "camion-uuid",
  "device_id": "nuevo-imei"
}
```

Resultado:
- Dispositivo viejo: `asignado` → `entregado`
- Dispositivo nuevo: `entregado` → `asignado`
- Se mantiene historial completo

---

### Caso 3: Auditar Dispositivos Activos

Ver qué dispositivos están actualmente instalados en unidades:

```bash
GET /api/v1/unit-devices/?active_only=true
```

Útil para:
- Inventario de dispositivos en uso
- Planificación de mantenimientos
- Control de activos

---

### Caso 4: Historial de una Unidad

Ver todos los dispositivos que ha tenido una unidad:

```bash
GET /api/v1/unit-devices/?active_only=false
# Luego filtrar por unit_id en cliente
```

O usar el endpoint jerárquico:

```bash
GET /api/v1/units/{unit_id}
```

---

### Caso 5: Rastrear Movimientos de un Dispositivo

Ver en qué unidades ha estado instalado un dispositivo:

```bash
GET /api/v1/unit-devices/?active_only=false
# Luego filtrar por device_id en cliente
```

---

## Validaciones de Integridad

### Unicidad de Asignaciones Activas

- Un dispositivo solo puede estar asignado a UNA unidad a la vez
- El sistema valida que no exista otra asignación activa antes de crear una nueva
- Asignaciones históricas (con `unassigned_at`) no cuentan para esta validación

### Estados Válidos para Asignar

Solo se pueden asignar dispositivos en estados:
- `entregado`: Dispositivo disponible para instalar
- `devuelto`: Dispositivo que fue desinstalado y está listo para reinstalar

No se pueden asignar dispositivos en estados:
- `nuevo`: Aún no ha sido entregado al cliente
- `asignado`: Ya está instalado en otra unidad
- `activo`, `suspendido`, `inactivo`: Estados de servicio
- `baja`: Dispositivo dado de baja

---

## Alternativas: Endpoints Jerárquicos

También es posible gestionar asignaciones usando los endpoints jerárquicos de `/api/v1/units/`:

- `GET /api/v1/units/{unit_id}/device` - Ver dispositivo de una unidad
- `POST /api/v1/units/{unit_id}/device` - Asignar/reemplazar dispositivo
- `DELETE /api/v1/units/{unit_id}/device` - Desasignar dispositivo (no implementado directamente)

Estos endpoints son equivalentes pero organizados jerárquicamente. La elección depende del caso de uso:

- **Usar `/unit-devices/`** para gestión global de asignaciones
- **Usar `/units/{id}/device`** para gestión desde la perspectiva de una unidad específica

### Ventaja del Endpoint Jerárquico

El endpoint `POST /api/v1/units/{unit_id}/device` tiene lógica adicional:
- Reemplaza automáticamente si ya hay un dispositivo asignado
- No requiere desasignar manualmente el dispositivo anterior
- Simplifica el flujo para el cliente

---

## Notas Importantes

### Soft Delete vs Hard Delete

- Las desasignaciones NO eliminan registros físicamente
- Solo marcan `unassigned_at`, preservando el historial
- Esto permite auditorías y análisis históricos

### Multi-tenant

- Todas las operaciones están aisladas por `client_id`
- Solo se pueden asignar dispositivos a unidades del mismo cliente
- Las consultas solo retornan asignaciones del cliente autenticado

### Performance

- Los índices en `unit_id`, `device_id` y `unassigned_at` optimizan las consultas
- El filtro `active_only=true` es muy eficiente (usa índice parcial)
- Las respuestas detalladas incluyen JOINs optimizados

### Auditoría Completa

- Cada operación genera eventos en `device_events`
- Se registra quién realizó la operación (`performed_by`)
- Se mantiene historial completo de cambios de estado
- No se puede modificar el historial (inmutable)

### Seguridad

- Solo usuarios maestros pueden gestionar asignaciones
- No se permite modificar asignaciones de otros clientes
- Los UUIDs son no predecibles y seguros


