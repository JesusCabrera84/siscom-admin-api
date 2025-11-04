# API de Planes

## Descripción

Endpoints para gestionar y consultar planes de servicio disponibles. Los planes definen los precios y características de los servicios de rastreo.

---

## Endpoints

### 1. Listar Planes

**GET** `/api/v1/plans/`

Lista todos los planes de servicio disponibles.

#### Headers

**No requiere autenticación** (endpoint público)

#### Response 200 OK

```json
[
  {
    "id": "223e4567-e89b-12d3-a456-426614174000",
    "name": "Plan Básico",
    "description": "Rastreo GPS básico con actualizaciones cada 60 segundos",
    "monthly_price": 199.00,
    "yearly_price": 1990.00,
    "features": {
      "update_interval": 60,
      "historical_data": 30,
      "geofences": 5,
      "alerts": true
    },
    "active": true,
    "created_at": "2024-01-10T08:00:00Z"
  },
  {
    "id": "334e4567-e89b-12d3-a456-426614174000",
    "name": "Plan Premium",
    "description": "Rastreo GPS avanzado con actualizaciones cada 30 segundos",
    "monthly_price": 299.00,
    "yearly_price": 2990.00,
    "features": {
      "update_interval": 30,
      "historical_data": 90,
      "geofences": 20,
      "alerts": true,
      "priority_support": true,
      "custom_reports": true
    },
    "active": true,
    "created_at": "2024-01-10T08:00:00Z"
  }
]
```

---

## Estructura de un Plan

### Campos Principales

- **id**: UUID único del plan
- **name**: Nombre comercial del plan
- **description**: Descripción de características
- **monthly_price**: Precio mensual (decimal)
- **yearly_price**: Precio anual (decimal)
- **features**: JSON con características específicas
- **active**: Indica si el plan está disponible para nuevas suscripciones
- **created_at**: Fecha de creación

### Campo `features` (JSON)

Características típicas incluidas:

```json
{
  "update_interval": 30,        // Intervalo de actualización en segundos
  "historical_data": 90,        // Días de historial disponible
  "geofences": 20,              // Número máximo de geocercas
  "alerts": true,               // Alertas por email/SMS
  "priority_support": true,     // Soporte prioritario
  "custom_reports": true,       // Reportes personalizados
  "api_access": false           // Acceso a API para integración
}
```

---

## Tipos de Planes Comunes

### Plan Básico

- **Precio**: ~$199 MXN/mes
- **Actualización**: 60 segundos
- **Historial**: 30 días
- **Ideal para**: Flotas pequeñas, uso básico

### Plan Estándar

- **Precio**: ~$249 MXN/mes
- **Actualización**: 45 segundos
- **Historial**: 60 días
- **Ideal para**: Flotas medianas, uso regular

### Plan Premium

- **Precio**: ~$299 MXN/mes
- **Actualización**: 30 segundos
- **Historial**: 90 días
- **Ideal para**: Flotas grandes, uso intensivo

### Plan Empresarial

- **Precio**: Personalizado
- **Actualización**: 10-15 segundos
- **Historial**: Ilimitado
- **Ideal para**: Empresas grandes con requerimientos especiales

---

## Precios Anuales

Los planes anuales típicamente ofrecen descuento:

```
Descuento = ((monthly_price * 12) - yearly_price) / (monthly_price * 12) * 100

Ejemplo:
Monthly: $199 * 12 = $2,388
Yearly:  $1,990
Descuento: 16.7%
```

---

## Estado del Plan

### Campo `active`

- **`true`**: Plan disponible para nuevas suscripciones
- **`false`**: Plan descontinuado (servicios existentes continúan)

### Planes Descontinuados

```
Plan descontinuado → active = false
                   ↓
  No aparece en listado público
                   ↓
  Servicios existentes continúan funcionando
                   ↓
  No se pueden crear nuevos servicios con este plan
```

---

## Uso en Activación de Servicios

Al activar un servicio, se usa el plan seleccionado:

```bash
POST /api/v1/services/activate
{
  "device_id": "...",
  "plan_id": "223e4567-e89b-12d3-a456-426614174000",  # Plan Básico
  "subscription_type": "MONTHLY"
}
```

El sistema:
1. Busca el plan por `plan_id`
2. Toma el precio según `subscription_type` (MONTHLY o YEARLY)
3. Crea el pago con ese monto
4. Activa el servicio con las características del plan

---

## Comparación de Planes

| Característica | Básico | Premium | Empresarial |
|---|---|---|---|
| Precio Mensual | $199 | $299 | Personalizado |
| Actualización | 60s | 30s | 10s |
| Historial | 30 días | 90 días | Ilimitado |
| Geocercas | 5 | 20 | Ilimitadas |
| Soporte | Estándar | Prioritario | Dedicado |
| Reportes | Básicos | Avanzados | Personalizados |

---

## Gestión de Planes (Admin)

**Nota**: Actualmente no hay endpoints para crear/actualizar planes. Se gestionan directamente en la base de datos.

### Crear Plan (SQL)

```sql
INSERT INTO plans (id, name, description, monthly_price, yearly_price, features, active)
VALUES (
  gen_random_uuid(),
  'Plan Básico',
  'Rastreo GPS básico',
  199.00,
  1990.00,
  '{"update_interval": 60, "historical_data": 30, "geofences": 5, "alerts": true}',
  true
);
```

### Descontinuar Plan (SQL)

```sql
UPDATE plans 
SET active = false 
WHERE id = '...';
```

---

## Consideraciones de Negocio

### Estrategia de Precios

- **Precio Base**: Costo del hardware + margen
- **Precio Servicio**: Costo operativo + margen + utilidad
- **Descuento Anual**: 10-20% para incentivar compromiso largo plazo

### Upselling

- Ofrecer plan superior cuando se alcancen límites
- Notificar características disponibles en planes superiores
- Trial de características premium por tiempo limitado

### Características como Límites

```python
# Ejemplo: Validar límite de geocercas
plan = get_plan(service.plan_id)
max_geofences = plan.features.get('geofences', 0)
current_geofences = count_geofences(client_id)

if current_geofences >= max_geofences:
    raise Exception("Has alcanzado el límite de geocercas de tu plan")
```

---

## Migración entre Planes

### Upgrade (subir de plan)

```
Cliente → Cancela servicio actual
        ↓
  Activa nuevo servicio con plan superior
        ↓
  Se cobra diferencia prorrateada (opcional)
```

### Downgrade (bajar de plan)

```
Cliente → Cancela servicio actual
        ↓
  Activa nuevo servicio con plan inferior
        ↓
  Sin reembolso por período restante
        ↓
  Nuevo precio aplica en siguiente ciclo
```

**Nota**: La lógica de migración con prorrateo debe implementarse según reglas de negocio.

---

## Ejemplo de Flujo Completo

### 1. Cliente Consulta Planes Disponibles

```bash
curl http://localhost:8000/api/v1/plans/
```

### 2. Cliente Selecciona Plan Premium

```json
{
  "id": "334e4567-e89b-12d3-a456-426614174000",
  "name": "Plan Premium",
  "monthly_price": 299.00,
  "yearly_price": 2990.00
}
```

### 3. Cliente Activa Servicio Mensual

```bash
curl -X POST http://localhost:8000/api/v1/services/activate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "...",
    "plan_id": "334e4567-e89b-12d3-a456-426614174000",
    "subscription_type": "MONTHLY"
  }'
```

### 4. Se Cobra $299.00 MXN Mensual

```json
{
  "payment": {
    "amount": 299.00,
    "description": "Plan Premium - Suscripción Mensual"
  }
}
```

---

## Mejores Prácticas

### Para Desarrolladores

- Siempre validar que `plan.active = true` antes de crear servicio
- Cachear lista de planes (cambian raramente)
- Validar límites de características según plan del cliente

### Para Administradores

- No eliminar planes, marcarlos como `active = false`
- Mantener precios competitivos con el mercado
- Actualizar características según feedback de clientes
- Documentar cambios en características de planes

### Para Cliente Final

- Mostrar comparación clara entre planes
- Destacar plan recomendado según uso
- Permitir cambio de plan fácilmente
- Ofrecer trial o demo de características premium

