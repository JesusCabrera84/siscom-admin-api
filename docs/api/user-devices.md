# API de Dispositivos de Usuario (Push)

## Descripción

Endpoints para registrar y desactivar dispositivos móviles de usuario usados en notificaciones push con AWS SNS.

Este módulo no administra GPS/IoT del inventario; solo tokens de dispositivos móviles asociados a usuarios.

---

## Endpoints

### 1. Registrar Dispositivo de Usuario

**POST** `/api/v1/user-devices/register`

Registra o actualiza un `device_token` para el usuario autenticado.

- Si no existe, crea registro nuevo y endpoint SNS.
- Si existe, lo reasigna al usuario actual, lo reactiva y actualiza `last_seen_at`.
- Si el endpoint SNS es inválido, se recrea automáticamente.

#### Headers

```http
Authorization: Bearer <access_token>
```

#### Request Body (register)

```json
{
  "device_token": "abc123",
  "platform": "ios"
}
```

#### Campos

- `device_token` (string, requerido): token del dispositivo móvil.
- `platform` (string, requerido): plataforma del dispositivo. Valores válidos: `ios`, `android`.

#### Response 200 OK (register)

```json
{
  "device_token": "abc123",
  "platform": "ios",
  "endpoint_arn": "arn:aws:sns:us-east-1:123456789012:endpoint/APNS/app/...",
  "is_active": true,
  "last_seen_at": "2026-04-12T20:00:00Z"
}
```

#### Errores Comunes (register)

- **401 Unauthorized**: token inválido o ausente.
- **422 Unprocessable Entity**: payload inválido (ej. `platform` fuera de `ios|android`).
- **503 Service Unavailable**: no fue posible registrar en SNS (configuración AWS/SNS incompleta).

---

### 2. Desactivar Dispositivo de Usuario

**POST** `/api/v1/user-devices/deactivate`

Marca el dispositivo como inactivo (`is_active=false`) para el `device_token` enviado.

**Auth:** No requiere token en la implementación actual.

#### Request Body (deactivate)

```json
{
  "device_token": "abc123"
}
```

#### Response 200 OK (deactivate)

```json
{
  "message": "Dispositivo desactivado exitosamente",
  "device_token": "abc123",
  "is_active": false
}
```

#### Errores Comunes (deactivate)

- **404 Not Found**: `device_token` no encontrado.
- **422 Unprocessable Entity**: payload inválido.

---

## Modelo de Datos

### UserDevice

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "device_token": "abc123",
  "platform": "ios",
  "endpoint_arn": "arn:aws:sns:...",
  "is_active": true,
  "last_seen_at": "2026-04-12T20:00:00Z",
  "updated_at": "2026-04-12T20:00:00Z"
}
```

## Notas Técnicas

- El registro usa `device_token` como clave lógica para upsert.
- `register` actualiza `last_seen_at` en cada llamada exitosa.
- `deactivate` no elimina filas; realiza actualización de estado.
- La creación/recuperación de endpoint SNS se resuelve en servicio (`get_or_recreate_endpoint`).

---

## Flujo SNS (Creación y Actualización de Endpoints)

Este es el flujo completo que ejecuta `POST /api/v1/user-devices/register` para SNS:

1. Valida el payload (`device_token`, `platform`) con `platform` en `ios|android`.
2. Busca un registro existente en `user_devices` por `device_token`.
3. Si no existe, intenta reutilizar el último registro del mismo `user_id + platform` (caso típico de rotación de token en iOS).
4. Llama al servicio SNS `get_or_recreate_endpoint(device_token, platform, endpoint_arn)`:
  - Si `endpoint_arn` existe, intenta `set_endpoint_attributes` para actualizar `Token` y `Enabled=true`.
  - Si ese endpoint no existe o es inválido en AWS, lo recrea automáticamente.
  - Si `endpoint_arn` no existe, crea uno nuevo con `create_platform_endpoint`.
5. Guarda o actualiza el registro en `user_devices` con el `endpoint_arn` resultante.
6. Publica evento Kafka `UPSERT` con datos del dispositivo.
7. Si falla SNS (configuración o AWS), responde `503 Service Unavailable`.

### APNS vs GCM/FCM

No se decide por una lógica fija en código; se decide por el ARN configurado para cada plataforma:

- `platform=ios` usa `SNS_PLATFORM_APPLICATION_ARN_IOS`.
- `platform=android` usa `SNS_PLATFORM_APPLICATION_ARN_ANDROID`.

Por lo tanto:

- Si el ARN es `...:app/APNS/...` o `...:app/APNS_SANDBOX/...`, el endpoint se crea como APNS.
- Si el ARN es `...:app/GCM/...`, el endpoint se crea como GCM/FCM.

### Nota de configuración actual

En el entorno local actual, `SNS_PLATFORM_APPLICATION_ARN_IOS` apunta a `app/GCM/...`.
Con esa configuración, solicitudes con `platform=ios` intentarán registrar endpoint en GCM/FCM, no en APNS.

---

## Publicación de Eventos en Kafka

Al completar exitosamente las operaciones, se publica un evento en Kafka al tópico configurado por `KAFKA_USER_DEVICES_UPDATES_TOPIC` (default `user-devices-updates`). La **key** es el UUID de la fila (`user_devices.id`), no el token push.

Si el envío a Kafka falla, el endpoint **no falla**: se registra el error en logs y la respuesta HTTP se mantiene exitosa.

El payload usa el envelope de control-plane (`event_id`, `event_type`, `entity`, `organization_id`, `data`). **No** incluye `unit_id`: quién recibe el push lo resuelve `alert-distributor` con masters ∪ `user_units`.

### Evento para altas/cambios (`register`)

```json
{
  "event_id": "uuid",
  "event_type": "UPSERT",
  "entity": "user_device",
  "timestamp": "2026-09-03T18:04:00Z",
  "organization_id": "uuid",
  "data": {
    "id": "uuid",
    "user_id": "uuid",
    "device_token": "string",
    "platform": "ios",
    "endpoint_arn": "arn:aws:sns:us-east-1:123456789012:endpoint/APNS/app/...",
    "is_active": true,
    "updated_at": "2026-09-03T18:04:00Z"
  }
}
```

### Evento para desactivación (`deactivate`)

Mismo envelope con `"event_type": "DELETE"` y `"is_active": false`.

`endpoint_arn` se publica con el valor almacenado en `user_devices.endpoint_arn` al momento del evento.
