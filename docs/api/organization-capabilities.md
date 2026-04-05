# API de Capabilities de Organización

## Descripción

Endpoints para gestionar **overrides** (personalizaciones) de capabilities a nivel de organización. Las capabilities definen límites y features que gobiernan el acceso y comportamiento del sistema.

### Sistema de Resolución de Capabilities

Las capabilities se resuelven en cascada con la siguiente prioridad:

```
organization_override → plan_capability → default_value
```

1. **organization_override**: Valor personalizado específico para la organización (estos endpoints)
2. **plan_capability**: Valor definido en el plan de suscripción activo
3. **default_value**: Valor por defecto del sistema

> **Nota**: Para consultar capabilities efectivas (ya resueltas), usar `/api/v1/capabilities`

---

## Endpoints

### 1. Listar Capabilities de una Organización

**GET** `/api/v1/organizations/{organization_id}/capabilities`

Lista todas las capabilities efectivas de una organización, indicando la fuente de cada valor.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `organization_id` | UUID | ID de la organización |

#### Response 200 OK

```json
{
  "capabilities": [
    {
      "code": "max_devices",
      "value": 100,
      "value_type": "int",
      "source": "organization",
      "plan_id": "abc12345-e89b-12d3-a456-426614174000",
      "expires_at": null,
      "is_override": true
    },
    {
      "code": "max_users",
      "value": 10,
      "value_type": "int",
      "source": "plan",
      "plan_id": "abc12345-e89b-12d3-a456-426614174000",
      "expires_at": null,
      "is_override": false
    },
    {
      "code": "feature_geofencing",
      "value": true,
      "value_type": "bool",
      "source": "default",
      "plan_id": null,
      "expires_at": null,
      "is_override": false
    }
  ],
  "total": 3,
  "overrides_count": 1
}
```

#### Campos de Respuesta

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `code` | string | Código identificador de la capability |
| `value` | any | Valor efectivo (int, bool o string según tipo) |
| `value_type` | string | Tipo de dato: `int`, `bool`, `text` |
| `source` | string | Origen: `organization`, `plan`, `default` |
| `plan_id` | UUID/null | ID del plan si la fuente es `plan` |
| `expires_at` | datetime/null | Fecha de expiración del override |
| `is_override` | boolean | `true` si es un override de organización |

#### Permisos

- Requiere rol: `member` o superior
- El usuario debe pertenecer al mismo Account que la organización

---

### 2. Crear o Actualizar Override de Capability

**POST** `/api/v1/organizations/{organization_id}/capabilities`

Crea o actualiza un override de capability para la organización. Si ya existe un override para el código especificado, se actualiza; si no, se crea uno nuevo.

#### Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### Path Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `organization_id` | UUID | ID de la organización |

#### Request Body

```json
{
  "capability_code": "max_devices",
  "value_int": 150,
  "value_bool": null,
  "value_text": null,
  "reason": "Cliente premium - aumento temporal por campaña Q1",
  "expires_at": "2024-03-31T23:59:59Z"
}
```

**Campos:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `capability_code` | string | Sí | Código de la capability a personalizar |
| `value_int` | int/null | Condicional | Valor entero (solo para capabilities tipo `int`) |
| `value_bool` | bool/null | Condicional | Valor booleano (solo para capabilities tipo `bool`) |
| `value_text` | string/null | Condicional | Valor texto (solo para capabilities tipo `text`) |
| `reason` | string/null | No | Justificación del override |
| `expires_at` | datetime/null | No | Fecha de expiración del override |

> **Importante**: Debe proporcionar exactamente UNO de los campos `value_int`, `value_bool` o `value_text` según el tipo de la capability.

#### Response 201 Created

```json
{
  "organization_id": "789e4567-e89b-12d3-a456-426614174000",
  "capability_id": "abc12345-e89b-12d3-a456-426614174000",
  "capability_code": "max_devices",
  "value": 150,
  "value_type": "int",
  "source": "organization",
  "reason": "Cliente premium - aumento temporal por campaña Q1",
  "expires_at": "2024-03-31T23:59:59Z"
}
```

#### Permisos

- Requiere rol: `owner`
- El usuario debe pertenecer al mismo Account que la organización

#### Errores

**400 Bad Request** - Tipo de valor incorrecto
```json
{
  "detail": "Debe proporcionar un valor (value_int, value_bool o value_text)"
}
```

**404 Not Found** - Capability no existe
```json
{
  "detail": "Capability 'max_devices' no encontrada"
}
```

**403 Forbidden** - Sin acceso a la organización
```json
{
  "detail": "No tienes acceso a esta organización"
}
```

---

### 3. Eliminar Override de Capability

**DELETE** `/api/v1/organizations/{organization_id}/capabilities/{capability_code}`

Elimina un override de capability de la organización. Al eliminar el override, la organización volverá a usar el valor del plan activo o el valor por defecto.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Path Parameters

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `organization_id` | UUID | ID de la organización |
| `capability_code` | string | Código de la capability |

#### Response 204 No Content

Sin cuerpo de respuesta.

#### Permisos

- Requiere rol: `owner`
- El usuario debe pertenecer al mismo Account que la organización

#### Errores

**404 Not Found** - Override no existe
```json
{
  "detail": "Override de capability 'max_devices' no encontrado"
}
```

**403 Forbidden** - Sin permisos
```json
{
  "detail": "Requiere rol owner"
}
```

---

## Casos de Uso

### 1. Aumentar Límites Temporalmente

Otorgar más dispositivos a una organización durante una promoción:

```bash
curl -X POST "https://api.tudominio.com/api/v1/organizations/789e4567-e89b-12d3-a456-426614174000/capabilities" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "capability_code": "max_devices",
    "value_int": 200,
    "reason": "Promoción verano 2024",
    "expires_at": "2024-08-31T23:59:59Z"
  }'
```

### 2. Habilitar Feature Premium

Activar una característica premium para una organización específica:

```bash
curl -X POST "https://api.tudominio.com/api/v1/organizations/789e4567-e89b-12d3-a456-426614174000/capabilities" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "capability_code": "feature_advanced_analytics",
    "value_bool": true,
    "reason": "Cliente beta tester"
  }'
```

### 3. Auditar Overrides de Organización

Consultar todas las personalizaciones activas:

```bash
curl -X GET "https://api.tudominio.com/api/v1/organizations/789e4567-e89b-12d3-a456-426614174000/capabilities" \
  -H "Authorization: Bearer <access_token>"
```

Filtrar en el cliente por `is_override: true` para ver solo las personalizaciones.

### 4. Restaurar Valor del Plan

Eliminar un override para que vuelva al valor del plan:

```bash
curl -X DELETE "https://api.tudominio.com/api/v1/organizations/789e4567-e89b-12d3-a456-426614174000/capabilities/max_devices" \
  -H "Authorization: Bearer <access_token>"
```

---

## Capabilities Comunes

### Límites (int)

| Código | Descripción | Default |
|--------|-------------|---------|
| `max_devices` | Máximo de dispositivos activos | 10 |
| `max_users` | Máximo de usuarios en la organización | 5 |
| `max_units` | Máximo de unidades/vehículos | 10 |
| `max_geofences` | Máximo de geocercas | 5 |

### Features (bool)

| Código | Descripción | Default |
|--------|-------------|---------|
| `feature_geofencing` | Activar geocercas | false |
| `feature_reports` | Activar reportes avanzados | false |
| `feature_api_access` | Acceso a API externa | false |
| `feature_multiuser` | Soporte multi-usuario | true |

### Configuraciones (text)

| Código | Descripción | Default |
|--------|-------------|---------|
| `storage_tier` | Nivel de almacenamiento | "standard" |
| `support_level` | Nivel de soporte | "basic" |

---

## Notas Técnicas

### Auditoría

Todos los cambios en organization capabilities se registran en el sistema de auditoría con:
- Usuario que realizó la acción
- Valor anterior y nuevo
- Razón del cambio
- IP y User-Agent

### Expiración Automática

Los overrides con `expires_at` configurado **NO se eliminan automáticamente**. El sistema simplemente ignora el valor cuando ha expirado y usa el siguiente en la cascada (plan → default).

Para limpiar overrides expirados periódicamente, considere implementar una tarea programada.

### Validaciones

- El sistema valida que el `capability_code` exista
- El tipo de valor debe coincidir con el `value_type` de la capability
- Solo se puede proporcionar uno de los campos `value_*`

### Relación con Planes

Los overrides de organización **tienen prioridad sobre los valores del plan**. Esto permite:
- Conceder excepciones a organizaciones específicas
- Realizar pruebas beta con features no disponibles en planes estándar
- Manejar casos especiales de negocio

---

## Referencias

- [API de Capabilities](./capabilities.md) - Consultar capabilities efectivas
- [API de Planes](./plans.md) - Gestión de planes y sus capabilities
- [Modelo Organizacional](../guides/organizational-model.md) - Arquitectura de permisos
