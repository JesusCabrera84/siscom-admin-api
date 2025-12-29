# API de Capabilities

## Descripción

Endpoints para consultar y validar las **capabilities** (límites y features) de una organización. Las capabilities determinan qué puede hacer una organización y cuántos recursos puede tener.

> **Concepto Clave**: Las capabilities se resuelven con la regla: `organization_override ?? plan_capability ?? default`

---

## Sistema de Capabilities

### ¿Qué son las Capabilities?

Las capabilities son atributos configurables que determinan:

- **Límites**: Número máximo de recursos (dispositivos, geocercas, usuarios)
- **Features**: Funcionalidades habilitadas (IA, analytics, API access)

### Regla de Resolución (Regla de Oro)

```
organization_capability_override     (si existe y no expirado)
         ??
plan_capability                      (del plan de suscripción activa principal)
         ??
default_capability                   (valor por defecto del sistema)
```

### Implementación Técnica

**Módulo centralizado:** `app/services/capabilities.py`

El servicio de capabilities usa internamente `subscription_query.get_active_plan_id()` para determinar el plan de la suscripción activa principal. Esto garantiza que la misma regla de "suscripción activa" se aplique en todo el sistema.

```python
# USO EN EL CÓDIGO
from app.services.capabilities import CapabilityService

# Obtener límite numérico
max_devices = CapabilityService.get_limit(db, client_id, "max_devices")

# Verificar feature booleano
has_ai = CapabilityService.has_capability(db, client_id, "ai_features")

# Validar antes de crear un recurso
if not CapabilityService.validate_limit(db, client_id, "max_geofences", current_count):
    raise HTTPException(403, "Límite de geocercas alcanzado")
```

### Ejemplo de Resolución

```
Organización: Transportes XYZ
Plan: Pro (max_geofences = 20)
Override: max_geofences = 100 (promoción especial)

Capability Efectiva: 100 (el override gana)
```

---

## Endpoints

### 1. Obtener Resumen de Capabilities

**GET** `/api/v1/capabilities/`

Obtiene todas las capabilities efectivas de la organización, agrupadas en límites y features.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
{
  "limits": {
    "max_devices": 50,
    "max_geofences": 100,
    "max_users": 10,
    "history_days": 90
  },
  "features": {
    "ai_features": true,
    "analytics_tools": true,
    "api_access": true,
    "real_time_tracking": true,
    "alerts_enabled": true,
    "reports_enabled": true
  }
}
```

---

### 2. Obtener Capability Específica

**GET** `/api/v1/capabilities/{capability_code}`

Obtiene el valor y fuente de una capability específica.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

| Parámetro | Descripción |
|-----------|-------------|
| `capability_code` | Código de la capability (ej: `max_devices`) |

#### Response 200 OK

```json
{
  "code": "max_devices",
  "value": 100,
  "source": "organization",
  "plan_id": null,
  "expires_at": "2024-12-31T23:59:59Z"
}
```

#### Campo `source`

| Valor | Descripción |
|-------|-------------|
| `organization` | Override específico de la organización |
| `plan` | Valor del plan activo |
| `default` | Valor por defecto del sistema |

---

### 3. Validar Límite

**POST** `/api/v1/capabilities/validate-limit`

Verifica si se puede agregar un elemento más sin exceder el límite.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "capability_code": "max_devices",
  "current_count": 8
}
```

#### Response 200 OK

```json
{
  "can_add": true,
  "current_count": 8,
  "limit": 10,
  "remaining": 2
}
```

#### Casos de Respuesta

**Puede agregar:**
```json
{
  "can_add": true,
  "current_count": 8,
  "limit": 10,
  "remaining": 2
}
```

**No puede agregar (límite alcanzado):**
```json
{
  "can_add": false,
  "current_count": 10,
  "limit": 10,
  "remaining": 0
}
```

**Ilimitado:**
```json
{
  "can_add": true,
  "current_count": 100,
  "limit": 0,
  "remaining": -1
}
```

---

### 4. Verificar Feature

**GET** `/api/v1/capabilities/check/{capability_code}`

Verifica rápidamente si una capability booleana está habilitada.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
{
  "capability": "ai_features",
  "enabled": true
}
```

---

## Capabilities Disponibles

### Límites (Tipo numérico)

| Código | Descripción | Default |
|--------|-------------|---------|
| `max_devices` | Número máximo de dispositivos | 1 |
| `max_geofences` | Número máximo de geocercas | 5 |
| `max_users` | Número máximo de usuarios | 3 |
| `history_days` | Días de historial de ubicaciones | 7 |

### Features (Tipo booleano)

| Código | Descripción | Default |
|--------|-------------|---------|
| `ai_features` | Acceso a funciones de IA | `false` |
| `analytics_tools` | Herramientas de analytics | `false` |
| `api_access` | Acceso a API de integración | `false` |
| `real_time_tracking` | Rastreo en tiempo real | `true` |
| `alerts_enabled` | Sistema de alertas | `true` |
| `reports_enabled` | Generación de reportes | `true` |

---

## Uso en Validaciones

### Antes de Crear Recursos

```python
# Ejemplo: Validar antes de crear un dispositivo
from app.services.capabilities import CapabilityService

# Contar dispositivos actuales
current_count = db.query(Device).filter(
    Device.client_id == client_id
).count()

# Validar límite
if not CapabilityService.validate_limit(
    db, client_id, "max_devices", current_count
):
    raise HTTPException(
        status_code=403,
        detail="Has alcanzado el límite de dispositivos de tu plan"
    )
```

### Verificar Feature Antes de Usar

```python
# Ejemplo: Verificar si tiene acceso a IA
from app.services.capabilities import CapabilityService

if not CapabilityService.has_capability(db, client_id, "ai_features"):
    raise HTTPException(
        status_code=403,
        detail="Tu plan no incluye funciones de IA"
    )
```

---

## Overrides de Organización

### ¿Qué son los Overrides?

Los overrides son ajustes específicos para una organización que sobreescriben los valores del plan.

### Casos de Uso

- Cliente negoció más dispositivos
- Promoción temporal
- Prueba de features premium
- Acuerdo enterprise personalizado

### Estructura de Override

```json
{
  "client_id": "org-uuid",
  "capability_id": "cap-uuid",
  "value_int": 100,
  "value_bool": null,
  "value_text": null,
  "reason": "Promoción Q4 2024",
  "expires_at": "2024-12-31T23:59:59Z"
}
```

### Override con Expiración

Los overrides pueden tener fecha de expiración:

```
Override: max_devices = 100
expires_at: 2024-12-31T23:59:59Z

Antes de 2024-12-31:
  Capability Efectiva = 100 (override)

Después de 2024-12-31:
  Capability Efectiva = 50 (plan)
```

---

## Integración con Endpoints

### Endpoints que Deben Validar Límites

| Endpoint | Capability a Validar |
|----------|---------------------|
| `POST /api/v1/devices/` | `max_devices` |
| `POST /api/v1/units/` | `max_units` |
| `POST /api/v1/users/invite` | `max_users` |
| `POST /api/v1/geofences/` | `max_geofences` |

### Endpoints que Deben Verificar Features

| Endpoint | Capability a Verificar |
|----------|------------------------|
| `GET /api/v1/analytics/*` | `analytics_tools` |
| `POST /api/v1/ai/*` | `ai_features` |
| `GET /api/v1/external/*` | `api_access` |

---

## Ejemplos de Uso

### Consultar Todas las Capabilities

```bash
curl -X GET http://localhost:8000/api/v1/capabilities/ \
  -H "Authorization: Bearer <token>"
```

### Consultar Capability Específica

```bash
curl -X GET http://localhost:8000/api/v1/capabilities/max_devices \
  -H "Authorization: Bearer <token>"
```

### Validar Límite Antes de Crear

```bash
curl -X POST http://localhost:8000/api/v1/capabilities/validate-limit \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "capability_code": "max_devices",
    "current_count": 8
  }'
```

### Verificar si Tiene IA

```bash
curl -X GET http://localhost:8000/api/v1/capabilities/check/ai_features \
  -H "Authorization: Bearer <token>"
```

---

## Mejores Prácticas

### Para Backend

1. **Usar el servicio centralizado**: Siempre usar `CapabilityService` para resolver capabilities
2. **Validar antes de crear**: Verificar límites antes de operaciones de creación
3. **Cachear por sesión**: Las capabilities no cambian frecuentemente

### Para Frontend

1. **Consultar al inicio**: Obtener capabilities al cargar la aplicación
2. **Mostrar uso actual**: Indicar cuánto se ha usado vs límite
3. **Advertir cerca del límite**: Notificar cuando se acercan al límite
4. **Deshabilitar features no disponibles**: No mostrar opciones que el plan no incluye

---

## Servicio de Capabilities

El sistema incluye un servicio centralizado en `app/services/capabilities.py`:

```python
from app.services.capabilities import CapabilityService

# Obtener capability resuelta
cap = CapabilityService.get_capability(db, org_id, "max_devices")
# cap.value = 100
# cap.source = "organization"

# Verificar feature
has_ai = CapabilityService.has_capability(db, org_id, "ai_features")
# True o False

# Obtener límite
limit = CapabilityService.get_limit(db, org_id, "max_devices")
# 100

# Validar límite
can_add = CapabilityService.validate_limit(db, org_id, "max_devices", 95)
# True (95 < 100)

# Obtener resumen
summary = CapabilityService.get_capabilities_summary(db, org_id)
# {"limits": {...}, "features": {...}}
```

---

**Última actualización**: Diciembre 2025  
**Referencia**: [Modelo Organizacional](../guides/organizational-model.md)

