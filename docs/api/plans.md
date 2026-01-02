# API de Planes

## Descripción

Endpoints **READ-ONLY** para consultar el catálogo de planes de servicio disponibles.

> **IMPORTANTE**: Los planes son **INFORMATIVOS**, no gobiernan la lógica del sistema.
> - La lógica de qué puede hacer una organización está en **capabilities**
> - La lógica de qué plan tiene una organización está en **subscriptions**

Ver también:
- [API de Capabilities](capabilities.md) - para ver qué puede hacer una organización
- [API de Subscriptions](subscriptions.md) - para ver suscripciones activas
- [API de Billing](billing.md) - para información de facturación

---

## Sistema de Capabilities

### ¿Qué son las Capabilities?

Las capabilities son atributos configurables que determinan:

- **Límites**: Número máximo de recursos (dispositivos, geocercas, usuarios)
- **Features**: Funcionalidades habilitadas (IA, analytics, reportes)
- **Acceso**: Permisos para usar ciertos endpoints o características

### Tipos de Capabilities

| Capability | Tipo | Descripción |
|------------|------|-------------|
| `max_devices` | Límite | Número máximo de dispositivos |
| `max_geofences` | Límite | Número máximo de geocercas |
| `max_users` | Límite | Número máximo de usuarios |
| `max_units` | Límite | Número máximo de unidades/vehículos |
| `history_days` | Límite | Días de historial de ubicaciones |
| `ai_features` | Feature | Acceso a análisis con IA |
| `analytics_tools` | Feature | Herramientas de analytics avanzado |
| `custom_reports` | Feature | Reportes personalizados |
| `api_access` | Feature | Acceso a API de integración |
| `priority_support` | Feature | Soporte prioritario |
| `real_time_alerts` | Feature | Alertas en tiempo real |
| `export_data` | Feature | Exportación de datos |

### Resolución de Capabilities (Regla de Oro)

Las capabilities efectivas de una organización se resuelven con la siguiente prioridad:

```
organization_capability_override     (si existe)
         ??
plan_capability                      (del plan activo)
         ??
default_capability                   (valor por defecto del sistema)
```

**Ejemplo:**
```
Plan Enterprise: max_geofences = 50
Organización Override: max_geofences = 100

Capability Efectiva: 100 (el override gana)
```

---

## Endpoints

### 1. Listar Planes

**GET** `/api/v1/plans/`

Lista todos los planes de servicio disponibles con sus capabilities, precios y opciones de facturación.

#### Headers

**No requiere autenticación** (endpoint público)

#### Response 200 OK

```json
{
  "plans": [
    {
      "id": "223e4567-e89b-12d3-a456-426614174000",
      "name": "Plan Básico",
      "code": "basic",
      "description": "Ideal para flotas pequeñas",
      "pricing": {
        "monthly": "299.00",
        "yearly": "2990.00",
        "yearly_savings_percent": 17
      },
      "billing_cycles": ["MONTHLY", "YEARLY"],
      "capabilities": {
        "max_devices": 10,
        "max_geofences": 20,
        "history_days": 30
      },
      "highlighted_features": [
        "Hasta 10 dispositivos",
        "20 geocercas",
        "30 días de historial"
      ],
      "is_popular": false,
      "created_at": "2024-01-10T08:00:00Z"
    },
    {
      "id": "334e4567-e89b-12d3-a456-426614174000",
      "name": "Plan Profesional",
      "code": "pro",
      "description": "Para flotas medianas con necesidades avanzadas",
      "pricing": {
        "monthly": "599.00",
        "yearly": "5990.00",
        "yearly_savings_percent": 17
      },
      "billing_cycles": ["MONTHLY", "YEARLY"],
      "capabilities": {
        "max_devices": 50,
        "max_geofences": 100,
        "max_users": 10,
        "history_days": 90,
        "ai_features": true,
        "analytics_tools": true
      },
      "highlighted_features": [
        "Hasta 50 dispositivos",
        "100 geocercas",
        "90 días de historial",
        "Funciones de IA incluidas",
        "Herramientas de analytics"
      ],
      "is_popular": true,
      "created_at": "2024-01-10T08:00:00Z"
    },
    {
      "id": "445e4567-e89b-12d3-a456-426614174000",
      "name": "Plan Enterprise",
      "code": "enterprise",
      "description": "Solución completa para flotas grandes",
      "pricing": {
        "monthly": "999.00",
        "yearly": "9990.00",
        "yearly_savings_percent": 17
      },
      "billing_cycles": ["MONTHLY", "YEARLY"],
      "capabilities": {
        "max_devices": 200,
        "max_geofences": 500,
        "max_users": 50,
        "history_days": 365,
        "ai_features": true,
        "analytics_tools": true,
        "api_access": true,
        "priority_support": true
      },
      "highlighted_features": [
        "Hasta 200 dispositivos",
        "500 geocercas",
        "365 días de historial",
        "Todas las funciones de IA",
        "Acceso a API",
        "Soporte prioritario"
      ],
      "is_popular": false,
      "created_at": "2024-01-10T08:00:00Z"
    }
  ],
  "total": 3
}
```

---

### 2. Obtener Plan por ID o Código

**GET** `/api/v1/plans/{plan_identifier}`

Obtiene información detallada de un plan específico por su UUID o código.

#### Headers

**No requiere autenticación** (endpoint público)

#### Path Parameters

| Parámetro | Descripción |
|-----------|-------------|
| `plan_identifier` | UUID del plan o código (ej: `pro`, `enterprise`) |

#### Ejemplos de Uso

```bash
# Por UUID
GET /api/v1/plans/334e4567-e89b-12d3-a456-426614174000

# Por código
GET /api/v1/plans/pro
```

#### Response 200 OK

```json
{
  "id": "334e4567-e89b-12d3-a456-426614174000",
  "name": "Plan Profesional",
  "code": "pro",
  "description": "Para flotas medianas con necesidades avanzadas",
  "pricing": {
    "monthly": "599.00",
    "yearly": "5990.00",
    "yearly_savings_percent": 17
  },
  "billing_cycles": ["MONTHLY", "YEARLY"],
  "capabilities": {
    "max_devices": 50,
    "max_geofences": 100,
    "max_users": 10,
    "history_days": 90,
    "ai_features": true,
    "analytics_tools": true
  },
  "highlighted_features": [
    "Hasta 50 dispositivos",
    "100 geocercas",
    "90 días de historial",
    "Funciones de IA incluidas"
  ],
  "is_popular": true,
  "created_at": "2024-01-10T08:00:00Z",
  "updated_at": "2024-01-10T08:00:00Z"
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 404 | `"Plan 'xyz' no encontrado"` |

---

## Estructura de un Plan

### Campos Principales

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID | Identificador único del plan |
| `name` | string | Nombre comercial del plan |
| `description` | string | Descripción de características |
| `price_monthly` | decimal | Precio mensual |
| `price_yearly` | decimal | Precio anual |
| `capabilities` | object | Capabilities del plan |
| `features_description` | array | Lista legible de características |
| `active` | boolean | Si está disponible para nuevas suscripciones |

### Campo `capabilities` (Estructura)

```json
{
  "max_devices": 50,        // Límite numérico
  "max_geofences": 20,      // Límite numérico
  "max_users": 10,          // Límite numérico
  "max_units": 50,          // Límite numérico
  "history_days": 90,       // Límite numérico
  "ai_features": false,     // Feature booleano
  "analytics_tools": true,  // Feature booleano
  "custom_reports": false,  // Feature booleano
  "api_access": false,      // Feature booleano
  "priority_support": false,// Feature booleano
  "real_time_alerts": true, // Feature booleano
  "export_data": true       // Feature booleano
}
```

---

## Comparación de Planes

| Capability | Básico | Pro | Enterprise |
|------------|:------:|:---:|:----------:|
| **Precio Mensual** | $199 | $349 | $599 |
| **Precio Anual** | $1,990 | $3,490 | $5,990 |
| **max_devices** | 10 | 50 | 200 |
| **max_geofences** | 5 | 20 | 100 |
| **max_users** | 3 | 10 | 50 |
| **history_days** | 30 | 90 | 365 |
| **ai_features** | ❌ | ❌ | ✅ |
| **analytics_tools** | ❌ | ✅ | ✅ |
| **custom_reports** | ❌ | ❌ | ✅ |
| **api_access** | ❌ | ❌ | ✅ |
| **priority_support** | ❌ | ❌ | ✅ |
| **real_time_alerts** | ✅ | ✅ | ✅ |
| **export_data** | ❌ | ✅ | ✅ |

---

## Validación de Capabilities

### Antes de Operaciones con Límites

El sistema debe validar capabilities antes de permitir operaciones que puedan exceder límites:

```
Ejemplo: Usuario intenta crear geocerca #21

1. GET effective_capabilities(org_id)
   → max_geofences = 20

2. COUNT geocercas actuales
   → current = 20

3. VALIDAR: 20 >= 20
   → RECHAZAR operación

4. RESPUESTA:
   HTTP 403 Forbidden
   {
     "detail": "Has alcanzado el límite de geocercas de tu plan",
     "capability": "max_geofences",
     "current": 20,
     "limit": 20,
     "upgrade_available": true
   }
```

### Endpoints que Deben Validar Capabilities

| Endpoint | Capability a Validar |
|----------|---------------------|
| `POST /api/v1/devices/` | `max_devices` |
| `POST /api/v1/units/` | `max_units` |
| `POST /api/v1/users/invite` | `max_users` |
| `POST /api/v1/geofences/` | `max_geofences` |
| `GET /api/v1/locations/history` | `history_days` |
| `GET /api/v1/analytics/...` | `analytics_tools` |
| `POST /api/v1/reports/custom` | `custom_reports` |
| `GET /api/v1/external/...` | `api_access` |

---

## Capability Overrides

### ¿Qué son los Overrides?

Los overrides son ajustes específicos para una organización que sobreescriben los valores del plan.

**Casos de uso:**
- Cliente negoció más dispositivos
- Promoción temporal
- Prueba de features premium
- Acuerdo enterprise personalizado

### Estructura de Override

```json
{
  "organization_id": "org-uuid",
  "capability": "max_geofences",
  "value": 100,
  "reason": "Upgrade especial por contrato enterprise",
  "applied_at": "2024-06-01T00:00:00Z",
  "expires_at": null,
  "applied_by": "admin@gac-web.internal"
}
```

### Ejemplo de Resolución con Override

```
Organización: Transportes XYZ
Plan Activo: Pro (max_geofences = 20)
Override: max_geofences = 50

GET effective_capabilities(org_id):
{
  "max_devices": 50,      // Del plan
  "max_geofences": 50,    // Override ✓
  "max_users": 10,        // Del plan
  "history_days": 90,     // Del plan
  ...
}
```

---

## Precios y Descuentos

### Descuento Anual

```
Descuento = ((price_monthly * 12) - price_yearly) / (price_monthly * 12) * 100

Ejemplo (Plan Pro):
Monthly: $349 * 12 = $4,188
Yearly:  $3,490
Descuento: 16.7%
```

### Estrategia de Precios

- **Precio Base**: Costo del hardware + margen
- **Precio Servicio**: Costo operativo + margen + utilidad
- **Descuento Anual**: 15-20% para incentivar compromiso largo plazo

---

## Estado del Plan

### Campo `active`

| Valor | Descripción |
|-------|-------------|
| `true` | Plan disponible para nuevas suscripciones |
| `false` | Plan descontinuado (servicios existentes continúan) |

### Planes Descontinuados

```
Plan descontinuado → active = false
                   ↓
  No aparece en listado público
                   ↓
  Suscripciones existentes continúan funcionando
                   ↓
  No se pueden crear nuevas suscripciones con este plan
                   ↓
  Se puede ofrecer migración a plan sucesor
```

---

## Uso en Activación de Servicios

Al activar un servicio, se usa el plan seleccionado:

```bash
POST /api/v1/services/activate
{
  "device_id": "...",
  "plan_id": "334e4567-e89b-12d3-a456-426614174000",
  "subscription_type": "MONTHLY"
}
```

El sistema:
1. Busca el plan por `plan_id`
2. Verifica que `plan.active = true`
3. Toma el precio según `subscription_type`
4. Crea el pago con ese monto
5. Crea la suscripción con las capabilities del plan
6. Activa el servicio

---

## Migración entre Planes

### Upgrade (subir de plan)

```
Organización → Selecciona plan superior
             ↓
  Sistema calcula diferencia prorrateada
             ↓
  Crea nueva suscripción con plan superior
             ↓
  Suscripción anterior marcada como UPGRADED
             ↓
  Nuevas capabilities efectivas inmediatamente
```

### Downgrade (bajar de plan)

```
Organización → Selecciona plan inferior
             ↓
  Sistema valida que uso actual no exceda nuevos límites
             ↓
  Si excede → Advertencia con recursos a eliminar
             ↓
  Crea nueva suscripción con plan inferior
             ↓
  Suscripción anterior se mantiene hasta expiración
             ↓
  Nuevas capabilities en siguiente ciclo de facturación
```

### Validación Pre-Downgrade

```json
{
  "current_usage": {
    "devices": 45,
    "geofences": 18,
    "users": 8
  },
  "new_plan_limits": {
    "max_devices": 10,
    "max_geofences": 5,
    "max_users": 3
  },
  "conflicts": [
    {
      "capability": "max_devices",
      "current": 45,
      "new_limit": 10,
      "action_required": "Eliminar 35 dispositivos"
    },
    {
      "capability": "max_geofences",
      "current": 18,
      "new_limit": 5,
      "action_required": "Eliminar 13 geocercas"
    }
  ],
  "can_downgrade": false
}
```

---

## Mejores Prácticas

### Para Desarrolladores

- Siempre validar `plan.active = true` antes de crear suscripción
- Usar función centralizada para resolver capabilities efectivas
- Cachear capabilities por sesión (no por request)
- Validar límites antes de operaciones de creación

### Para Administradores

- No eliminar planes, marcarlos como `active = false`
- Documentar razones de capability overrides
- Revisar overrides periódicamente
- Ofrecer migración a planes sucesores

### Para Frontend

- Mostrar comparación clara entre planes
- Destacar plan recomendado según uso actual
- Mostrar uso actual vs límites del plan
- Advertir cuando se acercan a límites
- Ofrecer upgrade cuando se alcanzan límites

---

## Ejemplo Completo

### 1. Consultar Planes

```bash
GET /api/v1/plans/
```

### 2. Seleccionar Plan y Activar

```bash
POST /api/v1/services/activate
{
  "device_id": "...",
  "plan_id": "334e4567-...",
  "subscription_type": "YEARLY"
}
```

### 3. Verificar Capabilities Efectivas

```bash
GET /api/v1/accounts/organization
# Respuesta incluye effective_capabilities
```

### 4. Intentar Operación que Excede Límite

```bash
POST /api/v1/geofences/
# Si excede max_geofences → HTTP 403
```

---

**Última actualización**: Diciembre 2025  
**Referencia**: [Modelo Organizacional](../guides/organizational-model.md)
