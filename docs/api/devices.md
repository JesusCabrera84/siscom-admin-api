# API de Dispositivos

## Descripción

Endpoints para gestionar dispositivos GPS/IoT del cliente. Incluye registro, consulta y gestión de dispositivos.

---

## Endpoints

### 1. Listar Dispositivos

**GET** `/api/v1/devices/`

Lista todos los dispositivos del cliente autenticado, con opción de filtrar por estado.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Query Parameters

- `active` (opcional): `true` o `false` para filtrar por estado activo/inactivo

#### Response 200 OK

```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "client_id": "456e4567-e89b-12d3-a456-426614174000",
    "serial_number": "GPS-2024-001",
    "model": "TK103",
    "imei": "353451234567890",
    "active": true,
    "installed_in_unit_id": "789e4567-e89b-12d3-a456-426614174000",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

#### Ejemplos

```bash
# Listar todos los dispositivos
GET /api/v1/devices/

# Solo dispositivos activos
GET /api/v1/devices/?active=true

# Solo dispositivos inactivos
GET /api/v1/devices/?active=false
```

---

### 2. Listar Dispositivos No Asignados

**GET** `/api/v1/devices/unassigned`

Lista dispositivos que no están instalados en ninguna unidad (vehículo).

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "client_id": "456e4567-e89b-12d3-a456-426614174000",
    "serial_number": "GPS-2024-002",
    "model": "TK103",
    "imei": "353451234567891",
    "active": false,
    "installed_in_unit_id": null,
    "created_at": "2024-01-15T11:00:00Z"
  }
]
```

---

### 3. Obtener Dispositivo Específico

**GET** `/api/v1/devices/{device_id}`

Obtiene el detalle de un dispositivo específico.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

- `device_id`: UUID del dispositivo

#### Response 200 OK

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "client_id": "456e4567-e89b-12d3-a456-426614174000",
  "serial_number": "GPS-2024-001",
  "model": "TK103",
  "imei": "353451234567890",
  "active": true,
  "installed_in_unit_id": "789e4567-e89b-12d3-a456-426614174000",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### Errores

- **404 Not Found**: Dispositivo no encontrado o no pertenece al cliente

---

### 4. Crear Dispositivo

**POST** `/api/v1/devices/`

Registra un nuevo dispositivo GPS para el cliente.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "serial_number": "GPS-2024-003",
  "model": "TK103",
  "imei": "353451234567892"
}
```

#### Validaciones

- El `serial_number` debe ser único en el sistema
- El `imei` debe ser único y tener 15 dígitos
- El `model` es obligatorio

#### Response 201 Created

```json
{
  "id": "abc12345-e89b-12d3-a456-426614174000",
  "client_id": "456e4567-e89b-12d3-a456-426614174000",
  "serial_number": "GPS-2024-003",
  "model": "TK103",
  "imei": "353451234567892",
  "active": false,
  "installed_in_unit_id": null,
  "created_at": "2024-01-16T09:15:00Z"
}
```

---

## Estados del Dispositivo

### Campo `active`

- **`true`**: Dispositivo tiene un servicio activo
- **`false`**: Dispositivo sin servicio activo o nunca activado

El campo `active` se actualiza automáticamente cuando:
- Se activa un servicio → `active = true`
- Se cancela el último servicio activo → `active = false`

---

## Relaciones del Dispositivo

### Unit (Unidad/Vehículo)

- Campo: `installed_in_unit_id`
- Un dispositivo puede estar instalado en una unidad (vehículo)
- `null` = dispositivo no instalado aún

### Device Services (Servicios)

- Un dispositivo puede tener múltiples servicios a lo largo del tiempo
- Solo puede tener UN servicio ACTIVE simultáneamente
- Historial completo de activaciones/cancelaciones

### Installations (Instalaciones)

- Historial de todas las instalaciones del dispositivo
- Incluye fecha de instalación y desinstalación
- Permite rastrear en qué unidades estuvo el dispositivo

---

## Ciclo de Vida del Dispositivo

### 1. Adquisición

```
Cliente → POST /api/v1/orders/ (compra dispositivos)
        ↓
  Dispositivos creados automáticamente
        ↓
  Estado: active=false, installed_in_unit_id=null
```

### 2. Registro Manual

```
Cliente → POST /api/v1/devices/ (registra dispositivo existente)
        ↓
  Dispositivo creado
        ↓
  Estado: active=false, installed_in_unit_id=null
```

### 3. Instalación

```
Cliente → Instala físicamente el dispositivo en vehículo
        ↓
  (Actualizar installed_in_unit_id manualmente o via endpoint)
        ↓
  Estado: active=false, installed_in_unit_id=<unit_id>
```

### 4. Activación de Servicio

```
Cliente → POST /api/v1/services/activate
        ↓
  Servicio creado y activado
        ↓
  Estado: active=true, installed_in_unit_id=<unit_id>
```

### 5. Cancelación de Servicio

```
Cliente → PATCH /api/v1/services/{service_id}/cancel
        ↓
  Servicio cancelado
        ↓
  Estado: active=false, installed_in_unit_id=<unit_id>
```

---

## Validaciones Importantes

### IMEI

- Debe tener exactamente 15 dígitos
- Debe ser único en todo el sistema
- Es el identificador oficial del dispositivo GSM/GPS

### Serial Number

- Identificador interno del dispositivo
- Debe ser único en todo el sistema
- Puede incluir letras y números

### Modelo

- Identifica el tipo de hardware GPS
- Ejemplos: TK103, TK303, GT06, etc.
- Usado para determinar protocolo de comunicación

---

## Consultas Útiles

### Dispositivos Activos con Servicio

```bash
GET /api/v1/devices/?active=true
```

### Dispositivos Sin Instalar

```bash
GET /api/v1/devices/unassigned
```

### Dispositivos Inactivos

```bash
GET /api/v1/devices/?active=false
```

---

## Consideraciones de Seguridad

### Multi-tenant

- Todos los dispositivos están aislados por `client_id`
- Un cliente solo puede ver sus propios dispositivos
- No es posible transferir dispositivos entre clientes

### Validación de Ownership

- Cada endpoint valida automáticamente que el dispositivo pertenezca al cliente
- El `client_id` se extrae del token JWT
- 404 si el dispositivo no existe o no pertenece al cliente

---

## Integración con Otros Módulos

### Servicios

```
Dispositivo → Activa servicio → Device.active = true
          → Cancela servicio → Device.active = false
```

### Órdenes

```
Orden → Contiene dispositivos como items
     → Dispositivos creados automáticamente al confirmar orden
```

### Unidades

```
Unit → device_installations → Dispositivo
                           → Historial de instalaciones
```

---

## Notas Adicionales

### Hardware Físico vs Registro Digital

- El dispositivo físico existe antes del registro digital
- El registro digital permite rastrear y gestionar el dispositivo
- Un dispositivo puede estar físicamente instalado pero no activado digitalmente

### Activación vs Instalación

- **Instalación**: Dispositivo físicamente montado en el vehículo
- **Activación**: Servicio mensual/anual pagado y activo
- Un dispositivo puede estar instalado sin estar activo (sin servicio pagado)

