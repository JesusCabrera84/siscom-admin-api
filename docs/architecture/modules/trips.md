# Módulo: Trips

## 📌 Descripción

Consulta de viajes y telemetría de dispositivos GPS.
Permite listar y ver detalles de trips con alertas, puntos GPS y eventos.

---

## 👤 Actor

- Usuario autenticado via Cognito (aplican permisos por unidad)
- Servicio interno via PASETO (service="gac", role="NEXUS_ADMIN" - acceso total)

---

## 🔌 APIs Consumidas

### 🔹 PostgreSQL (Base de datos)

| Tabla | Operación | Uso |
|-------|-----------|-----|
| `trips` | SELECT | Listar y obtener trips |
| `trip_points` | SELECT | Puntos GPS del trip |
| `trip_alerts` | SELECT | Alertas generadas durante el trip |
| `trip_events` | SELECT | Eventos del trip |
| `units` | SELECT | Información de unidades |
| `unit_devices` | SELECT | Relación unidad-dispositivo |
| `user_units` | SELECT | Permisos de usuario sobre unidades |
| `users` | SELECT | Información del usuario autenticado |

---

## 🔁 Flujo funcional

### Listar Trips (`GET /trips`)

```
1. Valida autenticación (Cognito o PASETO)
2. Si es Cognito:
   a. Obtiene usuario de BD
   b. Calcula dispositivos accesibles:
      - Master: todos los dispositivos del cliente
      - Normal: solo dispositivos de unidades asignadas
   c. Filtra trips por dispositivos accesibles
3. Si es PASETO: acceso total sin filtros de permisos
4. Aplica filtros opcionales:
   - unit_id: trips de una unidad específica
   - device_id: trips de un dispositivo específico
   - day + tz: trips de un día específico (filtra por end_time)
   - start_date/end_date: rango de fechas (filtra por start_time)
5. Aplica cursor de paginación
6. Opcionalmente incluye: alerts, points, events
7. Retorna lista con total, has_more, cursor
```

### Obtener Trip (`GET /trips/{trip_id}`)

```
1. Valida autenticación
2. Busca trip por UUID
3. Si es Cognito: verifica acceso al dispositivo del trip
4. Obtiene información de la unidad asignada al dispositivo
5. Carga expansiones solicitadas (alerts, points, events)
6. Retorna detalle completo del trip
```

---

## ⚠️ Consideraciones

- Este módulo soporta **autenticación dual** (Cognito/PASETO)
- Los permisos solo aplican para autenticación Cognito
- Usuarios PASETO tienen acceso completo (sin restricciones)
- El parámetro `day` toma precedencia sobre `start_date`/`end_date`
- Los puntos GPS (`include_points=true`) pueden generar respuestas muy grandes
- El filtro por `day` usa la zona horaria especificada (default: UTC)

---

## 🔐 Autenticación Dual

| Tipo | Validación | Permisos |
|------|------------|----------|
| **Cognito** | JWT válido | Basados en user_units |
| **PASETO** | service="gac", role="NEXUS_ADMIN" | Acceso total |

### Permisos Cognito

| Tipo de Usuario | Acceso |
|-----------------|--------|
| **Master** | Todos los trips de dispositivos del cliente |
| **Normal** | Solo trips de dispositivos de unidades asignadas |

---

## 📊 Filtros de Fecha

### Opción 1: Por Día Específico

```
GET /trips?day=2025-12-03&tz=America/Mexico_City
```

- Filtra por `end_time` dentro del día especificado
- La zona horaria define inicio/fin del día
- Útil para reportes diarios

### Opción 2: Por Rango

```
GET /trips?start_date=2025-12-01T00:00:00Z&end_date=2025-12-31T23:59:59Z
```

- Filtra por `start_time` dentro del rango
- Fechas en formato ISO 8601

---

## 📊 Expansiones

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `include_alerts` | `false` | Incluir alertas del trip |
| `include_points` | `false` | Incluir puntos GPS (¡puede ser muy grande!) |
| `include_events` | `false` | Incluir eventos del trip |

---

## 📊 Estructura de Respuesta

### Trip Básico

```json
{
  "trip_id": "uuid",
  "device_id": "ABC123",
  "start_timestamp": "2025-12-03T08:00:00Z",
  "end_timestamp": "2025-12-03T09:30:00Z",
  "duration_minutes": 90.0,
  "start_lat": 19.4326,
  "start_lon": -99.1332,
  "end_lat": 19.5000,
  "end_lon": -99.2000,
  "distance_km": 15.5
}
```

### Trip Detalle

```json
{
  "trip_id": "uuid",
  "device_id": "ABC123",
  "start_timestamp": "...",
  "end_timestamp": "...",
  "duration_minutes": 90.0,
  "distance_km": 15.5,
  "unit_id": "uuid",
  "unit_name": "Camioneta 01",
  "alerts": [...],
  "points": [...],
  "events": [...]
}
```

---

## 📊 Paginación

La paginación usa cursor basado en timestamp:

```json
{
  "trips": [...],
  "total": 150,
  "limit": 50,
  "cursor": "2025-12-03T09:30:00Z",
  "has_more": true
}
```

Para obtener la siguiente página:
```
GET /trips?cursor=2025-12-03T09:30:00Z
```

---

## 🧭 Relación C4 (preview)

- **Container:** SISCOM Admin API (FastAPI)
- **Consumes:** PostgreSQL
- **Consumed by:** Web App, Mobile App, GAC Service (via PASETO)
- **Related:** Units module, Devices module


