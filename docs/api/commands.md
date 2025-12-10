# API de Comandos

## Descripción

Endpoints para gestionar comandos enviados a dispositivos GPS/IoT. Permite crear comandos, consultar su estado y obtener el historial de comandos por dispositivo.

---

## Modelo de Datos

### Command

```json
{
  "command_id": "42bfcefb-4aa3-4866-b12b-7fa34b87f923",
  "template_id": "abc12345-e89b-12d3-a456-426614174000",
  "command": "AT+LOCATION",
  "media": "sms",
  "request_user_id": "def45678-e89b-12d3-a456-426614174000",
  "device_id": "353451234567890",
  "requested_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "status": "delivered",
  "metadata": {
    "source_id": "mobile_app",
    "response_raw": "OK"
  }
}
```

---

## Estados del Comando

El campo `status` representa el estado actual del comando en su ciclo de vida:

| Estado      | Descripción                                          |
| ----------- | ---------------------------------------------------- |
| `pending`   | Comando creado, pendiente de envío                   |
| `sent`      | Comando enviado al dispositivo                       |
| `delivered` | Comando entregado/confirmado por el dispositivo      |
| `failed`    | Comando falló en el envío o ejecución                |

---

## Campos del Modelo

| Campo            | Tipo      | Requerido | Descripción                                      |
| ---------------- | --------- | --------- | ------------------------------------------------ |
| `command_id`     | UUID      | Auto      | Identificador único del comando (generado)       |
| `template_id`    | UUID      | No        | Referencia al template de comando usado          |
| `command`        | TEXT      | Sí        | El comando a enviar al dispositivo               |
| `media`          | TEXT      | Sí        | Medio de comunicación (sms, tcp, etc.)           |
| `request_user_id`| UUID      | Auto      | Usuario que creó el comando (del token)          |
| `device_id`      | TEXT      | Sí        | ID del dispositivo destino                       |
| `requested_at`   | TIMESTAMP | Auto      | Fecha/hora de creación del comando               |
| `updated_at`     | TIMESTAMP | Auto      | Fecha/hora de última actualización               |
| `status`         | TEXT      | Auto      | Estado actual del comando                        |
| `metadata`       | JSONB     | No        | Datos adicionales (source_id, response_raw, etc.)|

---

## Endpoints

### 1. Crear Comando

**POST** `/api/v1/commands`

Crea un nuevo comando para enviar a un dispositivo. El comando se crea con estado `pending`.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "command": "AT+LOCATION",
  "media": "sms",
  "device_id": "353451234567890",
  "template_id": "abc12345-e89b-12d3-a456-426614174000",
  "metadata": {
    "source_id": "mobile_app"
  }
}
```

#### Campos del Request

| Campo         | Tipo   | Requerido | Descripción                                |
| ------------- | ------ | --------- | ------------------------------------------ |
| `command`     | string | Sí        | El comando a enviar al dispositivo         |
| `media`       | string | Sí        | Medio de comunicación (sms, tcp, etc.)     |
| `device_id`   | string | Sí        | ID del dispositivo destino                 |
| `template_id` | UUID   | No        | ID del template de comando (opcional)      |
| `metadata`    | object | No        | Datos adicionales del comando (opcional)   |

#### Validaciones

- El `device_id` debe existir en la tabla de dispositivos
- El usuario debe estar autenticado (se obtiene `request_user_id` del token)

#### Response 201 Created

```json
{
  "command_id": "42bfcefb-4aa3-4866-b12b-7fa34b87f923",
  "status": "pending"
}
```

#### Errores

| Código | Descripción                           |
| ------ | ------------------------------------- |
| 401    | No autorizado (token inválido)        |
| 404    | Dispositivo no encontrado             |
| 422    | Datos de entrada inválidos            |

---

### 2. Listar Comandos por Dispositivo

**GET** `/api/v1/commands/device/{device_id}`

Obtiene todos los comandos enviados a un dispositivo específico, con soporte para filtrado y paginación.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

| Parámetro   | Tipo   | Descripción                      |
| ----------- | ------ | -------------------------------- |
| `device_id` | string | ID del dispositivo a consultar   |

#### Query Parameters

| Parámetro       | Tipo   | Default | Descripción                                           |
| --------------- | ------ | ------- | ----------------------------------------------------- |
| `status_filter` | string | -       | Filtrar por estado (pending, sent, delivered, failed) |
| `limit`         | int    | 50      | Límite de resultados (1-500)                          |
| `offset`        | int    | 0       | Offset para paginación                                |

#### Response 200 OK

```json
{
  "commands": [
    {
      "command_id": "42bfcefb-4aa3-4866-b12b-7fa34b87f923",
      "template_id": "abc12345-e89b-12d3-a456-426614174000",
      "command": "AT+LOCATION",
      "media": "sms",
      "request_user_id": "def45678-e89b-12d3-a456-426614174000",
      "device_id": "353451234567890",
      "requested_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:35:00Z",
      "status": "delivered",
      "metadata": {
        "source_id": "mobile_app",
        "response_raw": "OK"
      }
    },
    {
      "command_id": "53cfdefb-5bb4-5977-c23c-8gb45c98g034",
      "template_id": null,
      "command": "AT+RESTART",
      "media": "tcp",
      "request_user_id": "def45678-e89b-12d3-a456-426614174000",
      "device_id": "353451234567890",
      "requested_at": "2024-01-14T15:00:00Z",
      "updated_at": "2024-01-14T15:00:00Z",
      "status": "pending",
      "metadata": null
    }
  ],
  "total": 25
}
```

#### Ejemplos

```bash
# Todos los comandos de un dispositivo
GET /api/v1/commands/device/353451234567890

# Solo comandos pendientes
GET /api/v1/commands/device/353451234567890?status_filter=pending

# Con paginación
GET /api/v1/commands/device/353451234567890?limit=10&offset=20

# Comandos fallidos
GET /api/v1/commands/device/353451234567890?status_filter=failed
```

#### Errores

| Código | Descripción                                                        |
| ------ | ------------------------------------------------------------------ |
| 400    | Estado inválido (status_filter no es pending/sent/delivered/failed)|
| 401    | No autorizado (token inválido)                                     |
| 404    | Dispositivo no encontrado                                          |

---

### 3. Obtener Comando por ID

**GET** `/api/v1/commands/{command_id}`

Obtiene el detalle completo de un comando específico por su UUID.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

| Parámetro    | Tipo | Descripción                  |
| ------------ | ---- | ---------------------------- |
| `command_id` | UUID | ID único del comando         |

#### Response 200 OK

```json
{
  "command_id": "42bfcefb-4aa3-4866-b12b-7fa34b87f923",
  "template_id": "abc12345-e89b-12d3-a456-426614174000",
  "command": "AT+LOCATION",
  "media": "sms",
  "request_user_id": "def45678-e89b-12d3-a456-426614174000",
  "device_id": "353451234567890",
  "requested_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "status": "delivered",
  "metadata": {
    "source_id": "mobile_app",
    "response_raw": "OK"
  }
}
```

#### Errores

| Código | Descripción                     |
| ------ | ------------------------------- |
| 401    | No autorizado (token inválido)  |
| 404    | Comando no encontrado           |

---

## Flujo de Uso Típico

```
1. CREAR COMANDO
   POST /api/v1/commands
   → status='pending', command_id=<uuid>

2. SISTEMA EXTERNO PROCESA
   (El servicio de mensajería actualiza el estado)
   → status='sent' cuando se envía
   → status='delivered' cuando se confirma
   → status='failed' si falla

3. CONSULTAR ESTADO
   GET /api/v1/commands/{command_id}
   → Ver estado actual y metadata

4. HISTORIAL POR DISPOSITIVO
   GET /api/v1/commands/device/{device_id}
   → Ver todos los comandos del dispositivo
```

---

## Ejemplos Completos

### Caso 1: Enviar Comando de Ubicación

```bash
# Crear comando
POST /api/v1/commands
Authorization: Bearer <token>
Content-Type: application/json

{
  "command": "AT+GTGPS",
  "media": "sms",
  "device_id": "353451234567890",
  "metadata": {
    "source_id": "web_dashboard",
    "priority": "high"
  }
}

# Respuesta
{
  "command_id": "42bfcefb-4aa3-4866-b12b-7fa34b87f923",
  "status": "pending"
}

# Verificar estado después
GET /api/v1/commands/42bfcefb-4aa3-4866-b12b-7fa34b87f923
```

### Caso 2: Consultar Historial de Comandos

```bash
# Ver últimos 10 comandos del dispositivo
GET /api/v1/commands/device/353451234567890?limit=10

# Ver solo comandos fallidos
GET /api/v1/commands/device/353451234567890?status_filter=failed

# Paginar resultados (página 3 de 10 elementos)
GET /api/v1/commands/device/353451234567890?limit=10&offset=20
```

### Caso 3: Comando con Template

```bash
# Crear comando usando un template predefinido
POST /api/v1/commands
{
  "command": "AT+GTOUT=gv300,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0$",
  "media": "tcp",
  "device_id": "353451234567890",
  "template_id": "abc12345-e89b-12d3-a456-426614174000",
  "metadata": {
    "template_name": "output_control",
    "output_number": 1
  }
}
```

---

## Estructura de Metadata

El campo `metadata` es flexible (JSONB) y puede contener información adicional según el caso de uso:

### Ejemplos de Metadata

```json
// Al crear el comando
{
  "source_id": "mobile_app",
  "priority": "high",
  "retry_count": 0
}

// Después de procesar
{
  "source_id": "mobile_app",
  "priority": "high",
  "retry_count": 2,
  "response_raw": "OK",
  "delivered_at": "2024-01-15T10:35:00Z",
  "delivery_channel": "sms_gateway"
}

// En caso de fallo
{
  "source_id": "mobile_app",
  "priority": "high",
  "retry_count": 3,
  "error_code": "DEVICE_OFFLINE",
  "error_message": "Device did not respond after 3 attempts",
  "last_attempt_at": "2024-01-15T10:45:00Z"
}
```

---

## Consideraciones de Seguridad

### Autenticación

- Todos los endpoints requieren token de Cognito válido
- El `request_user_id` se obtiene automáticamente del token autenticado
- No es posible crear comandos como otro usuario

### Auditoría

- Cada comando registra quién lo creó (`request_user_id`)
- Timestamps automáticos (`requested_at`, `updated_at`)
- El historial de comandos es inmutable (no se pueden eliminar)

### Validaciones

- El dispositivo debe existir en el sistema
- Los estados están controlados por CHECK constraint en la base de datos

---

## Consultas Útiles

```bash
# Comandos pendientes de un dispositivo
GET /api/v1/commands/device/353451234567890?status_filter=pending

# Comandos entregados exitosamente
GET /api/v1/commands/device/353451234567890?status_filter=delivered

# Comandos fallidos (para reintentar)
GET /api/v1/commands/device/353451234567890?status_filter=failed

# Últimos 100 comandos de un dispositivo
GET /api/v1/commands/device/353451234567890?limit=100

# Estado de un comando específico
GET /api/v1/commands/42bfcefb-4aa3-4866-b12b-7fa34b87f923
```

---

## Tabla SQL de Referencia

```sql
CREATE TABLE commands (
    command_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id     UUID REFERENCES command_templates(template_id),
    command         TEXT NOT NULL,
    media           TEXT NOT NULL,
    request_user_id UUID NOT NULL,
    device_id       TEXT NOT NULL REFERENCES devices(device_id),
    requested_at    TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    status          TEXT NOT NULL DEFAULT 'pending',
    metadata        JSONB,
    
    CONSTRAINT check_command_status 
        CHECK (status IN ('pending', 'sent', 'delivered', 'failed'))
);

-- Índices para optimización
CREATE INDEX idx_commands_device_id ON commands(device_id);
CREATE INDEX idx_commands_request_user_id ON commands(request_user_id);
CREATE INDEX idx_commands_status ON commands(status);
CREATE INDEX idx_commands_requested_at ON commands(requested_at);
```
