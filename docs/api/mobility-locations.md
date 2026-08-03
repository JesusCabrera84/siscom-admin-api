# API de Ubicaciones de Movilidad

## Descripción

Endpoint para recibir ubicaciones de dispositivos de movilidad y publicarlas en Kafka.

El backend valida campos obligatorios del JSON, agrega `received_at` con la hora actual UTC y publica el mensaje enriquecido en el tópico configurado por `KAFKA_MOBILITY_TOPIC`.

---

## Autenticación

Ambos endpoints **requieren JWT**: `Authorization: Bearer <access_token>`.

Además del token, se valida que el `device_id` del payload **pertenezca al usuario autenticado** y esté activo:

| Situación | Respuesta |
| --- | --- |
| El `device_id` no existe **o** pertenece a otro usuario | `404 Not Found` — `"device_id no existe o no pertenece al usuario."` |
| El dispositivo existe y es tuyo, pero está desactivado (`is_active = false`) | `403 Forbidden` — `"El dispositivo está desactivado y no puede publicar ubicaciones."` |

> El caso "no existe" y el caso "es de otro usuario" devuelven **el mismo 404 a propósito**, para que el endpoint no funcione como oráculo de `device_id` válidos.

En el batch la validación se hace **una sola vez** sobre el `device_id` de nivel superior, no por cada punto.

> **Nota sobre el request sin header:** si no se envía `Authorization`, FastAPI responde
> `403 Forbidden` (`"Not authenticated"`), no `401`. Es el comportamiento por defecto de
> `HTTPBearer` y aplica a **todo el servicio**, no solo a estos endpoints — hay tests en
> `tests/test_auth.py` que esperan `401` y fallan por esto. Los clientes que disparan
> refresh de token con el `401` deben tenerlo en cuenta.

---

## Endpoint

### `POST /api/v1/mobility/locations`

#### Request Body

Campos obligatorios:

- `device_id` (uuid)
- `recorded_at` (datetime)
- `lat` (number)
- `lon` (number)

Campos opcionales:

- `accuracy_m` (number)
- `speed_mps` (number)
- `heading` (number)
- `altitude_m` (number)
- `battery_level` (number entre 0 y 100)
- `motion_state` (string)
- `h3_index` (string)
- `h3_resolution` (integer entre 0 y 15)

Ejemplo:

```json
{
  "device_id": "c7bb5f50-b8e6-4c7d-a0a2-c6fdb2b6f3f0",
  "recorded_at": "2026-05-31T02:15:20Z",
  "lat": 20.593212,
  "lon": -100.392188,
  "accuracy_m": 12.5,
  "speed_mps": 0.0,
  "heading": 180,
  "altitude_m": 1810,
  "battery_level": 82,
  "motion_state": "stopped",
  "h3_index": "8a2a1072b59ffff",
  "h3_resolution": 10
}
```

#### Response 202 Accepted

Retorna el payload publicado, enriquecido con `received_at`:

```json
{
  "device_id": "c7bb5f50-b8e6-4c7d-a0a2-c6fdb2b6f3f0",
  "recorded_at": "2026-05-31T02:15:20Z",
  "received_at": "2026-05-31T02:15:21Z",
  "lat": 20.593212,
  "lon": -100.392188,
  "accuracy_m": 12.5,
  "speed_mps": 0.0,
  "heading": 180,
  "altitude_m": 1810,
  "battery_level": 82,
  "motion_state": "stopped",
  "h3_index": "8a2a1072b59ffff",
  "h3_resolution": 10
}
```

---

### `POST /api/v1/mobility/locations/batch`

Publica un lote de ubicaciones para un mismo `device_id`.

#### Request Body

Campos obligatorios:

- `device_id` (uuid)
- `locations` (array con al menos un elemento)

Cada elemento en `locations`:

- Obligatorios: `recorded_at`, `lat`, `lon`
- Opcionales: `accuracy_m`, `speed_mps`, `heading`, `altitude_m`, `battery_level`, `motion_state`, `h3_index`, `h3_resolution`

Ejemplo:

```json
{
  "device_id": "c7bb5f50-b8e6-4c7d-a0a2-c6fdb2b6f3f0",
  "locations": [
    {
      "recorded_at": "2026-05-31T10:00:00Z",
      "lat": 20.593,
      "lon": -100.392,
      "accuracy_m": 12,
      "motion_state": "moving",
      "h3_index": "8a2a1072b59ffff",
      "h3_resolution": 10
    },
    {
      "recorded_at": "2026-05-31T10:05:00Z",
      "lat": 20.594,
      "lon": -100.391,
      "accuracy_m": 10
    }
  ]
}
```

#### Response 202 Accepted

Retorna `device_id` y el arreglo de ubicaciones publicadas, enriquecidas con `received_at`:

```json
{
  "device_id": "c7bb5f50-b8e6-4c7d-a0a2-c6fdb2b6f3f0",
  "locations": [
    {
      "recorded_at": "2026-05-31T10:00:00Z",
      "received_at": "2026-05-31T10:00:01Z",
      "lat": 20.593,
      "lon": -100.392,
      "accuracy_m": 12,
      "motion_state": "moving",
      "h3_index": "8a2a1072b59ffff",
      "h3_resolution": 10
    },
    {
      "recorded_at": "2026-05-31T10:05:00Z",
      "received_at": "2026-05-31T10:05:01Z",
      "lat": 20.594,
      "lon": -100.391,
      "accuracy_m": 10
    }
  ]
}
```

#### Errores comunes

- `401 Unauthorized`: el token es inválido o expiró.
- `403 Forbidden`: el dispositivo está desactivado, **o** falta por completo el header
  `Authorization` (comportamiento actual de `HTTPBearer` en todo el servicio; ver nota abajo).
- `404 Not Found`: el `device_id` no existe o no pertenece al usuario autenticado.
- `422 Unprocessable Entity`: faltan campos obligatorios o formato inválido.
- `503 Service Unavailable`: no se pudo publicar la ubicación en Kafka.
