# API - Perfiles de Unidades

Endpoints para administrar perfiles de unidades (unit_profile + vehicle_profile).

## ✨ Actualización Unificada

El endpoint **PATCH /units/{unit_id}/profile** ahora soporta actualización unificada de ambos perfiles (universal + vehículo) en una sola llamada, con **upsert automático** del perfil de vehículo.

---

## 🔑 Autenticación

Todos los endpoints requieren:

```bash
Authorization: Bearer <access_token>
```

---

## 📖 Modelo de Datos

### Unit Profile (Universal)

Información común a todas las unidades:

- `unit_type` - Tipo de unidad (vehicle, asset, container, person, equipment)
- `icon_type` - Tipo de ícono para mostrar
- `description` - Descripción del perfil
- `brand` - Marca
- `model` - Modelo
- `color` - Color
- `year` - Año de fabricación

### Vehicle Profile (Específico)

Información adicional solo para vehículos (`unit_type = "vehicle"`):

- `plate` - Placa del vehículo
- `vin` - VIN (Vehicle Identification Number)
- `fuel_type` - Tipo de combustible
- `passengers` - Capacidad de pasajeros

---

## 📍 Endpoints Principales

### 1. Obtener Perfil de Unidad

```http
GET /api/v1/units/{unit_id}/profile
```

**Descripción:**
Obtiene el perfil completo de una unidad (universal + vehículo si aplica).

**Permisos:**
- Cualquier usuario con acceso a la unidad

**Respuesta exitosa (200):**

```json
{
  "unit_id": "abc12345-e89b-12d3-a456-426614174000",
  "unit_type": "vehicle",
  "icon_type": "truck",
  "description": "Camión de carga pesada",
  "brand": "Ford",
  "model": "F-350",
  "color": "Rojo",
  "year": 2020,
  "vehicle": {
    "unit_id": "abc12345-e89b-12d3-a456-426614174000",
    "plate": "ABC-123",
    "vin": "1FDUF3GT5GED12345",
    "fuel_type": "Diesel",
    "passengers": 5,
    "created_at": "2025-11-15T10:30:00Z",
    "updated_at": "2025-11-15T10:30:00Z"
  }
}
```

**Caso especial:**
Si `unit_type ≠ "vehicle"`, el campo `vehicle` será `null`.

---

### 2. ⭐ Actualizar Perfil Unificado (RECOMENDADO)

```http
PATCH /api/v1/units/{unit_id}/profile
```

**Descripción:**
Actualiza el perfil de la unidad de forma unificada. Puede actualizar campos universales y de vehículo en una sola llamada.

**✨ Características:**
- ✅ Acepta campos de `unit_profile` y `vehicle_profile` en el mismo body
- ✅ Hace **upsert automático** del `vehicle_profile` si se envían campos de vehículo
- ✅ Ignora campos de vehículo si `unit_type ≠ "vehicle"`
- ✅ Actualización parcial (solo campos enviados)
- ✅ Siempre retorna el perfil completo

**Permisos:**
- Usuario maestro, o
- Usuario con rol `editor` o `admin`

**Body (JSON) - Todos los campos son opcionales:**

```json
{
  "icon_type": "truck",
  "description": "Camión de carga pesada",
  "brand": "Ford",
  "model": "F-350",
  "color": "Rojo",
  "year": 2020,
  "plate": "ABC-123",
  "vin": "1FDUF3GT5GED12345",
  "fuel_type": "Diesel",
  "passengers": 5
}
```

**Respuesta exitosa (200):**

```json
{
  "unit_id": "abc12345-e89b-12d3-a456-426614174000",
  "unit_type": "vehicle",
  "icon_type": "truck",
  "description": "Camión de carga pesada",
  "brand": "Ford",
  "model": "F-350",
  "color": "Rojo",
  "year": 2020,
  "vehicle": {
    "unit_id": "abc12345-e89b-12d3-a456-426614174000",
    "plate": "ABC-123",
    "vin": "1FDUF3GT5GED12345",
    "fuel_type": "Diesel",
    "passengers": 5,
    "created_at": "2025-11-28T10:30:00Z",
    "updated_at": "2025-11-28T15:45:00Z"
  }
}
```

**Ejemplos de uso:**

```bash
# Ejemplo 1: Actualizar solo campos universales
curl -X PATCH "http://localhost:8000/api/v1/units/{unit_id}/profile" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "brand": "Ford",
    "model": "F-350",
    "year": 2020
  }'

# Ejemplo 2: Actualizar solo campos de vehículo (crea vehicle_profile si no existe)
curl -X PATCH "http://localhost:8000/api/v1/units/{unit_id}/profile" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plate": "ABC-123",
    "fuel_type": "Diesel"
  }'

# Ejemplo 3: Actualizar ambos en una sola llamada (RECOMENDADO)
curl -X PATCH "http://localhost:8000/api/v1/units/{unit_id}/profile" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "icon_type": "truck",
    "brand": "Ford",
    "model": "F-350",
    "color": "Rojo",
    "year": 2020,
    "plate": "ABC-123",
    "vin": "1FDUF3GT5GED12345",
    "fuel_type": "Diesel",
    "passengers": 5
  }'
```

---

## 📍 Endpoints Secundarios (Compatibilidad)

Los siguientes endpoints se mantienen por compatibilidad, pero se recomienda usar el endpoint unificado PATCH /units/{unit_id}/profile.

### 3. Crear Perfil de Vehículo

```http
POST /api/v1/units/{unit_id}/profile/vehicle
```

**⚠️ NOTA:** Este endpoint se mantiene por compatibilidad. Se recomienda usar PATCH /units/{unit_id}/profile con campos de vehículo, que hace upsert automático.

**Body (JSON):**

```json
{
  "plate": "ABC-123",
  "vin": "1FDUF3GT5GED12345",
  "fuel_type": "Diesel",
  "passengers": 5
}
```

### 4. Actualizar Perfil de Vehículo

```http
PATCH /api/v1/units/{unit_id}/profile/vehicle
```

**⚠️ NOTA:** Este endpoint se mantiene por compatibilidad. Se recomienda usar PATCH /units/{unit_id}/profile con campos de vehículo.

**Body (JSON):**

```json
{
  "plate": "XYZ-789",
  "passengers": 7
}
```

---

## 🔄 Flujo de Trabajo Simplificado

### Flujo Recomendado del Frontend

```mermaid
graph TD
    A[Usuario abre detalle de unidad] --> B[GET /units/{id}/profile]
    B --> C[Mostrar formulario con todos los campos]
    C --> D[Usuario edita cualquier campo]
    D --> E[PATCH /units/{id}/profile con todos los campos editados]
    E --> F[Backend hace upsert automático]
    F --> G[Retorna perfil completo actualizado]
```

### Ejemplo de Código Frontend (JavaScript)

```javascript
// 1. Cargar perfil al abrir detalles
async function loadUnitProfile(unitId) {
  const response = await fetch(`/api/v1/units/${unitId}/profile`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return await response.json();
}

// 2. Guardar TODOS los cambios en una sola llamada (SIMPLIFICADO)
async function saveProfile(unitId, formData) {
  // formData puede contener cualquier combinación de campos
  const response = await fetch(`/api/v1/units/${unitId}/profile`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(formData)
  });
  
  return await response.json();
}

// Ejemplo de uso
const profile = await loadUnitProfile('abc-123');

// Editar algunos campos
const updates = {
  brand: 'KIA',
  model: 'Rio LX',
  color: 'Negro',
  year: 2020,
  plate: 'ABC-123',
  fuel_type: 'Gasolina',
  icon_type: 'car-01'
};

// Una sola llamada actualiza todo
const updatedProfile = await saveProfile('abc-123', updates);
```

---

## ✅ Validaciones y Reglas

### Permisos

| Acción | Maestro | Editor | Admin | Viewer |
|--------|---------|--------|-------|--------|
| GET profile | ✅ | ✅ | ✅ | ✅ |
| PATCH profile | ✅ | ✅ | ✅ | ❌ |
| POST vehicle | ✅ | ✅ | ✅ | ❌ |
| PATCH vehicle | ✅ | ✅ | ✅ | ❌ |

### Reglas de Negocio

1. **Creación automática:**
   - `unit_profile` se crea automáticamente al crear una unidad
   - `unit_type` por defecto es `"vehicle"`

2. **Upsert de Vehicle Profile:**
   - Si `unit_type = "vehicle"` y se envían campos de vehículo:
     * Si `vehicle_profile` NO existe → se crea automáticamente
     * Si `vehicle_profile` existe → se actualiza
   - Si `unit_type ≠ "vehicle"` → campos de vehículo se ignoran

3. **Actualización parcial:**
   - Todos los PATCH soportan actualización parcial
   - Solo los campos enviados se actualizan
   - Campos no enviados mantienen su valor actual

4. **Separación de campos:**
   - El backend separa automáticamente los campos según correspondan
   - No es necesario hacer llamadas separadas para cada tipo de perfil

---

## 🚨 Códigos de Error

| Código | Descripción |
|--------|-------------|
| `400` | Validación fallida o regla de negocio violada |
| `403` | Sin permisos para la operación |
| `404` | Unidad no encontrada |
| `500` | Error interno del servidor |

---

## 💡 Ventajas del Endpoint Unificado

✅ **Simplicidad:** Una sola llamada para actualizar todo
✅ **Upsert automático:** No necesitas verificar si vehicle_profile existe
✅ **Menos código:** El frontend no necesita lógica condicional
✅ **Transaccional:** Todos los cambios se guardan en una sola transacción
✅ **Flexible:** Puedes enviar solo los campos que cambiaron
✅ **Seguro:** El backend maneja automáticamente la lógica de tipos

---

## 📝 Notas Importantes

1. El `unit_profile` siempre existe después de crear una unidad
2. El `vehicle_profile` se crea automáticamente si envías campos de vehículo
3. Los campos de vehículo se ignoran si `unit_type ≠ "vehicle"`
4. La actualización es siempre parcial (solo campos enviados)
5. Los endpoints `/profile/vehicle` se mantienen por compatibilidad

---

**Última actualización:** Noviembre 2025

