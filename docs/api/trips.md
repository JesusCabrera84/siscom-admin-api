# 🚗 API de Trips - Documentación Completa

## 📋 Descripción General

La API de Trips proporciona acceso de **solo lectura** a los datos de viajes (trips) generados por el servicio `siscom-trips`. Los endpoints permiten consultar información detallada sobre los viajes realizados por los dispositivos GPS asignados a las unidades.

### Características Principales

- 📖 **Solo Lectura**: Todos los endpoints son de solo lectura (GET)
- 🔐 **Multi-tenant**: Los usuarios solo pueden ver trips de su cliente
- 👥 **Permisos Granulares**: 
  - Usuario maestro: puede ver todos los trips del cliente
  - Usuario regular: solo trips de unidades asignadas en `user_units`
- 📅 **Filtros de Fecha**: Filtros obligatorios para optimizar consultas en Timescale
- 🔄 **Paginación con Cursor**: Paginación eficiente para grandes volúmenes de datos
- ⚡ **Expansiones Opcionales**: Incluir alertas, puntos GPS y eventos bajo demanda

---

## 🎯 Endpoints Implementados

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/v1/trips` | Lista todos los trips con filtros opcionales |
| `GET` | `/api/v1/trips/{trip_id}` | Detalle de un trip con expansiones |
| `GET` | `/api/v1/devices/{device_id}/trips` | Trips de un dispositivo (fechas obligatorias) |
| `GET` | `/api/v1/units/{unit_id}/trips` | Trips de una unidad (fechas obligatorias) |

---

## 📡 Endpoints Detallados

### 1. Lista de Todos los Trips

**`GET /api/v1/trips`**

Lista todos los trips accesibles para el usuario autenticado.

#### Parámetros de Query

| Parámetro | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `unit_id` | UUID | No | - | Filtrar por unidad específica |
| `device_id` | String | No | - | Filtrar por dispositivo específico |
| `start_date` | DateTime | No | - | Fecha de inicio del rango (ISO 8601) |
| `end_date` | DateTime | No | - | Fecha de fin del rango (ISO 8601) |
| `limit` | Integer | No | 50 | Límite de resultados (1-500) |
| `cursor` | DateTime | No | - | Cursor para paginación |
| `include_alerts` | Boolean | No | false | Incluir alertas del trip |
| `include_points` | Boolean | No | false | Incluir puntos GPS del trip |
| `include_events` | Boolean | No | false | Incluir eventos del trip |

#### Ejemplo de Request

```bash
curl -X GET "http://localhost:8000/api/v1/trips?start_date=2025-11-01T00:00:00Z&end_date=2025-11-30T23:59:59Z&limit=10" \
  -H "Authorization: Bearer ${TOKEN}"
```

#### Ejemplo de Response

```json
{
  "trips": [
    {
      "trip_id": "550e8400-e29b-41d4-a716-446655440000",
      "device_id": "864537040123456",
      "start_timestamp": "2025-11-29T08:00:00Z",
      "end_timestamp": "2025-11-29T09:30:00Z",
      "duration_minutes": 90.0,
      "start_lat": 19.4326,
      "start_lon": -99.1332,
      "end_lat": 19.4978,
      "end_lon": -99.1269,
      "distance_km": 12.5
    }
  ],
  "total": 1,
  "limit": 10,
  "cursor": "2025-11-29T08:00:00Z",
  "has_more": false
}
```

---

### 2. Detalle de un Trip

**`GET /api/v1/trips/{trip_id}`**

Obtiene el detalle completo de un trip específico con expansiones opcionales.

#### Parámetros de Path

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `trip_id` | UUID | ID del trip a consultar |

#### Parámetros de Query

| Parámetro | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `include_alerts` | Boolean | No | true | Incluir alertas del trip |
| `include_points` | Boolean | No | false | Incluir puntos GPS del trip |
| `include_events` | Boolean | No | false | Incluir eventos del trip |

#### Ejemplo de Request

```bash
curl -X GET "http://localhost:8000/api/v1/trips/550e8400-e29b-41d4-a716-446655440000?include_alerts=true&include_points=true" \
  -H "Authorization: Bearer ${TOKEN}"
```

#### Ejemplo de Response

```json
{
  "trip_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_id": "864537040123456",
  "start_timestamp": "2025-11-29T08:00:00Z",
  "end_timestamp": "2025-11-29T09:30:00Z",
  "duration_minutes": 90.0,
  "start_lat": 19.4326,
  "start_lon": -99.1332,
  "end_lat": 19.4978,
  "end_lon": -99.1269,
  "distance_km": 12.5,
  "unit_id": "abc12345-e89b-12d3-a456-426614174000",
  "unit_name": "Camión #45",
  "alerts": [
    {
      "timestamp": "2025-11-29T08:15:00Z",
      "type": "speeding",
      "lat": 19.4400,
      "lon": -99.1300,
      "severity": 2
    }
  ],
  "points": [
    {
      "timestamp": "2025-11-29T08:00:00Z",
      "lat": 19.4326,
      "lon": -99.1332,
      "speed": 0.0,
      "heading": 90.0
    }
  ],
  "events": null
}
```

---

### 3. Trips por Dispositivo

**`GET /api/v1/devices/{device_id}/trips`**

Obtiene los trips de un dispositivo específico en un rango de fechas.

⚠️ **IMPORTANTE**: Los parámetros `start_date` y `end_date` son **OBLIGATORIOS** para este endpoint.

#### Parámetros de Path

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `device_id` | String | ID del dispositivo (IMEI o serial) |

#### Parámetros de Query

| Parámetro | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `start_date` | DateTime | **Sí** | - | Fecha de inicio del rango (ISO 8601) |
| `end_date` | DateTime | **Sí** | - | Fecha de fin del rango (ISO 8601) |
| `limit` | Integer | No | 50 | Límite de resultados (1-500) |
| `cursor` | DateTime | No | - | Cursor para paginación |
| `include_alerts` | Boolean | No | false | Incluir alertas del trip |
| `include_points` | Boolean | No | false | Incluir puntos GPS del trip |
| `include_events` | Boolean | No | false | Incluir eventos del trip |

#### Ejemplo de Request

```bash
curl -X GET "http://localhost:8000/api/v1/devices/864537040123456/trips?start_date=2025-11-01T00:00:00Z&end_date=2025-11-30T23:59:59Z" \
  -H "Authorization: Bearer ${TOKEN}"
```

---

### 4. Trips por Unidad

**`GET /api/v1/units/{unit_id}/trips`**

Obtiene los trips de una unidad específica en un rango de fechas.

⚠️ **IMPORTANTE**: Los parámetros `start_date` y `end_date` son **OBLIGATORIOS** para este endpoint.

#### Parámetros de Path

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `unit_id` | UUID | ID de la unidad |

#### Parámetros de Query

| Parámetro | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `start_date` | DateTime | **Sí** | - | Fecha de inicio del rango (ISO 8601) |
| `end_date` | DateTime | **Sí** | - | Fecha de fin del rango (ISO 8601) |
| `limit` | Integer | No | 50 | Límite de resultados (1-500) |
| `cursor` | DateTime | No | - | Cursor para paginación |
| `include_alerts` | Boolean | No | false | Incluir alertas del trip |
| `include_points` | Boolean | No | false | Incluir puntos GPS del trip |
| `include_events` | Boolean | No | false | Incluir eventos del trip |

#### Ejemplo de Request

```bash
curl -X GET "http://localhost:8000/api/v1/units/abc12345-e89b-12d3-a456-426614174000/trips?start_date=2025-11-01T00:00:00Z&end_date=2025-11-30T23:59:59Z" \
  -H "Authorization: Bearer ${TOKEN}"
```

---

## 🔐 Permisos y Control de Acceso

### Usuario Maestro

Los usuarios con `is_master=true` tienen acceso completo a:
- ✅ Todos los trips de todas las unidades del cliente
- ✅ Todos los trips de todos los dispositivos del cliente
- ✅ Sin restricciones de visibilidad

### Usuario Regular

Los usuarios con `is_master=false` tienen acceso limitado a:
- ✅ Solo trips de unidades asignadas en `user_units`
- ✅ Solo trips de dispositivos asignados a esas unidades
- ❌ No pueden ver trips de unidades no asignadas

### Validación de Acceso

El sistema valida automáticamente:
1. Que el usuario esté autenticado (token válido)
2. Que el cliente del usuario coincida con el cliente del dispositivo
3. Que el usuario tenga permisos sobre la unidad (maestro o en `user_units`)

---

## 📊 Estructura de Datos

### Trip (Básico)

```typescript
{
  trip_id: UUID,              // ID único del viaje
  device_id: string,          // ID del dispositivo
  start_timestamp: datetime,  // Inicio del viaje
  end_timestamp: datetime,    // Fin del viaje
  duration_minutes: float,    // Duración en minutos (calculado)
  start_lat: float,           // Latitud de inicio
  start_lon: float,           // Longitud de inicio
  end_lat: float,             // Latitud de fin
  end_lon: float,             // Longitud de fin
  distance_km: float          // Distancia en kilómetros (calculado)
}
```

### TripDetail (Con Expansiones)

Incluye todos los campos de `Trip` más:

```typescript
{
  // ... campos de Trip
  unit_id: UUID | null,       // ID de la unidad asignada
  unit_name: string | null,   // Nombre de la unidad
  
  // Expansiones opcionales
  alerts: TripAlert[] | null,
  points: TripPoint[] | null,
  events: TripEvent[] | null
}
```

### TripAlert

```typescript
{
  timestamp: datetime,        // Timestamp de la alerta
  type: string,               // Tipo de alerta (speeding, harsh_braking, etc.)
  lat: float,                 // Latitud
  lon: float,                 // Longitud
  severity: int               // Severidad (1-5)
}
```

### TripPoint

```typescript
{
  timestamp: datetime,        // Timestamp del punto
  lat: float,                 // Latitud
  lon: float,                 // Longitud
  speed: float,               // Velocidad (km/h)
  heading: float              // Rumbo en grados (0-360)
}
```

### TripEvent

```typescript
{
  timestamp: datetime,        // Timestamp del evento
  event_type: string,         // Tipo de evento
  value: string | null        // Valor del evento
}
```

---

## 📄 Paginación

La API utiliza paginación basada en cursor para un rendimiento óptimo con grandes volúmenes de datos.

### Cómo Funciona

1. La primera request no incluye `cursor`
2. La respuesta incluye un campo `cursor` con el timestamp del último trip
3. Para obtener la siguiente página, envía el `cursor` en la siguiente request
4. El campo `has_more` indica si hay más resultados disponibles

### Ejemplo de Paginación

```bash
# Primera página
GET /api/v1/trips?limit=10

Response:
{
  "trips": [...],
  "cursor": "2025-11-29T08:00:00Z",
  "has_more": true
}

# Segunda página
GET /api/v1/trips?limit=10&cursor=2025-11-29T08:00:00Z

Response:
{
  "trips": [...],
  "cursor": "2025-11-28T14:30:00Z",
  "has_more": false
}
```

---

## ⚡ Optimización y Mejores Prácticas

### 1. Usa Filtros de Fecha

```bash
# ✅ BUENO - Consulta optimizada
GET /api/v1/devices/864537040123456/trips?start_date=2025-11-01T00:00:00Z&end_date=2025-11-30T23:59:59Z

# ❌ MALO - Consulta sin filtros (no permitido en devices y units)
GET /api/v1/devices/864537040123456/trips
```

### 2. Expansiones Solo Cuando Sean Necesarias

```bash
# ✅ BUENO - Solo cargar lo necesario
GET /api/v1/trips/550e8400?include_alerts=true

# ❌ MALO - Cargar puntos GPS innecesariamente (puede ser muy grande)
GET /api/v1/trips?include_points=true
```

### 3. Paginación Adecuada

```bash
# ✅ BUENO - Límites razonables
GET /api/v1/trips?limit=50

# ❌ MALO - Límites muy grandes
GET /api/v1/trips?limit=500
```

---

## 🚨 Códigos de Error

| Código | Descripción |
|--------|-------------|
| `200` | ✅ Éxito |
| `401` | 🔒 No autenticado (token inválido o ausente) |
| `403` | 🚫 Sin permisos (usuario no tiene acceso al recurso) |
| `404` | ❓ Recurso no encontrado (trip, device o unit no existe) |
| `422` | ⚠️ Parámetros inválidos (fechas mal formadas, etc.) |
| `500` | ❌ Error interno del servidor |

### Ejemplos de Errores

#### 401 - No Autenticado

```json
{
  "detail": "Token inválido o ausente"
}
```

#### 403 - Sin Permisos

```json
{
  "detail": "No tienes acceso a este dispositivo"
}
```

#### 404 - No Encontrado

```json
{
  "detail": "Trip no encontrado"
}
```

#### 422 - Parámetros Inválidos

```json
{
  "detail": [
    {
      "loc": ["query", "start_date"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 🧪 Ejemplos de Testing

### Configuración Inicial

```bash
export API_BASE="http://localhost:8000"
export TOKEN="tu_token_jwt_aqui"
```

### Lista de Trips Básica

```bash
curl -X GET "${API_BASE}/api/v1/trips?limit=5" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json"
```

### Filtrado por Rango de Fechas

```bash
curl -X GET "${API_BASE}/api/v1/trips?start_date=2025-11-01T00:00:00Z&end_date=2025-11-30T23:59:59Z&limit=10" \
  -H "Authorization: Bearer ${TOKEN}"
```

### Trips de un Dispositivo

```bash
curl -X GET "${API_BASE}/api/v1/devices/864537040123456/trips?start_date=2025-11-01T00:00:00Z&end_date=2025-11-30T23:59:59Z" \
  -H "Authorization: Bearer ${TOKEN}"
```

### Trips de una Unidad

```bash
curl -X GET "${API_BASE}/api/v1/units/abc12345-e89b-12d3-a456-426614174000/trips?start_date=2025-11-01T00:00:00Z&end_date=2025-11-30T23:59:59Z" \
  -H "Authorization: Bearer ${TOKEN}"
```

### Detalle de Trip con Alertas

```bash
curl -X GET "${API_BASE}/api/v1/trips/550e8400-e29b-41d4-a716-446655440000?include_alerts=true" \
  -H "Authorization: Bearer ${TOKEN}"
```

### Paginación con Cursor

```bash
# Primera página
curl -X GET "${API_BASE}/api/v1/trips?limit=10" \
  -H "Authorization: Bearer ${TOKEN}"

# Segunda página (usando cursor de la respuesta)
curl -X GET "${API_BASE}/api/v1/trips?limit=10&cursor=2025-11-29T08:00:00Z" \
  -H "Authorization: Bearer ${TOKEN}"
```

---

## 📈 Casos de Uso Comunes

### 1. Dashboard de Viajes del Día

```bash
GET /api/v1/trips?start_date=2025-11-29T00:00:00Z&end_date=2025-11-29T23:59:59Z&limit=100
```

### 2. Historial de Viajes de un Vehículo

```bash
GET /api/v1/units/{unit_id}/trips?start_date=2025-11-01T00:00:00Z&end_date=2025-11-30T23:59:59Z
```

### 3. Análisis de Alertas de un Trip

```bash
GET /api/v1/trips/{trip_id}?include_alerts=true&include_events=true
```

### 4. Replay de Ruta (con puntos GPS)

```bash
GET /api/v1/trips/{trip_id}?include_points=true
```

### 5. Reporte Mensual de Dispositivo

```bash
GET /api/v1/devices/{device_id}/trips?start_date=2025-11-01T00:00:00Z&end_date=2025-11-30T23:59:59Z&limit=500
```

---

## 🗄️ SQL Queries de Referencia

### Verificar Existencia de Tablas

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('trips', 'trip_points', 'trip_alerts', 'trip_events')
ORDER BY table_name;
```

### Contar Trips por Dispositivo

```sql
SELECT 
    device_id,
    COUNT(*) as trip_count,
    MIN(start_time) as first_trip,
    MAX(start_time) as last_trip
FROM trips
GROUP BY device_id
ORDER BY trip_count DESC
LIMIT 10;
```

### Trips del Día Actual

```sql
SELECT 
    trip_id,
    device_id,
    start_time,
    end_time,
    EXTRACT(EPOCH FROM (end_time - start_time)) / 60 as duration_minutes,
    distance_meters / 1000.0 as distance_km
FROM trips
WHERE start_time >= CURRENT_DATE
  AND start_time < CURRENT_DATE + INTERVAL '1 day'
ORDER BY start_time DESC;
```

### Verificar Permisos de un Usuario

```sql
SELECT 
    usr.email,
    usr.is_master,
    usr.client_id,
    COUNT(DISTINCT u.id) as accessible_units,
    COUNT(DISTINCT ud.device_id) as accessible_devices
FROM users usr
LEFT JOIN user_units uu ON uu.user_id = usr.id
LEFT JOIN units u ON u.id = uu.unit_id OR (usr.is_master AND u.client_id = usr.client_id)
LEFT JOIN unit_devices ud ON ud.unit_id = u.id
WHERE usr.email = 'usuario@ejemplo.com'
GROUP BY usr.email, usr.is_master, usr.client_id;
```

---

## 📝 Notas Importantes

1. **Solo Lectura**: Todos los endpoints son de solo lectura. No hay operaciones de escritura.

2. **Datos Generados por siscom-trips**: Los datos de trips son generados por el servicio `siscom-trips`, no por esta API.

3. **Base de Datos Timescale**: Los datos se almacenan en una base de datos Timescale optimizada para series temporales.

4. **Fechas en UTC**: Todas las fechas deben enviarse y se retornan en formato UTC (ISO 8601).

5. **Paginación Eficiente**: La paginación basada en cursor es más eficiente que la paginación por offset/page para grandes volúmenes de datos.

6. **Expansiones Costosas**: Las expansiones `include_points` pueden retornar miles de registros. Úsalas con precaución.

7. **Multi-tenant Automático**: El sistema automáticamente filtra los datos por `client_id` del usuario autenticado.

---

## 📦 Archivos de Código

| Archivo | Descripción |
|---------|-------------|
| `app/models/trip.py` | Modelos SQLModel (Trip, TripPoint, TripAlert, TripEvent) |
| `app/schemas/trip.py` | Schemas Pydantic para responses |
| `app/api/v1/endpoints/trips.py` | Endpoints principales de trips |
| `app/api/v1/endpoints/devices.py` | Endpoint `/devices/{id}/trips` |
| `app/api/v1/endpoints/units.py` | Endpoint `/units/{id}/trips` |

---

## 🆘 Soporte

Para más información, consulta:
- 📘 Documentación completa de la API: `/docs` (Swagger UI)
- 📖 Documentación alternativa: `/redoc` (ReDoc)

---

**Última actualización**: 29 de noviembre de 2025  
**Versión**: 1.0
