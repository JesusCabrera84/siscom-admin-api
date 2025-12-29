# API de Organizaciones

## Descripción

Endpoints para gestionar **organizaciones** en el sistema. Una organización (tabla `clients`) representa una empresa u entidad de negocio que utiliza el sistema de rastreo GPS.

> **Nota Conceptual**: En el código y base de datos, la tabla se llama `clients`, pero a nivel de negocio representa una **Organización**. Ver [Modelo Organizacional](../guides/organizational-model.md) para detalles completos.

---

## Conceptos Clave

### Organización vs Cliente

| Término Técnico | Término de Negocio | Descripción |
|-----------------|-------------------|-------------|
| `client` | **Organización** | Empresa que contrata servicios |
| `client_id` | `organization_id` | Identificador de la organización |

### Suscripciones Múltiples

Una organización puede tener **múltiples suscripciones**:

```
Organización "Transportes XYZ"
├── Suscripción 1 (ACTIVE, Plan Enterprise, actual)
├── Suscripción 2 (EXPIRED, Plan Básico, 2023)
└── Suscripción 3 (CANCELLED, Plan Pro, Q1 2024)
```

> ⚠️ **Importante**: El campo `active_subscription_id` existe por compatibilidad pero NO debe usarse como fuente de verdad. Las suscripciones activas se calculan dinámicamente.

---

## Endpoints

### 1. Crear Organización (Registro)

**POST** `/api/v1/clients/`

Crea una nueva organización con un usuario propietario (owner) asociado. Este es el endpoint de registro público.

#### Request Body

```json
{
  "name": "Transportes XYZ",
  "email": "admin@transportesxyz.com",
  "password": "Password123!"
}
```

#### Validaciones

- El email no debe estar registrado en el sistema
- El nombre de la organización debe ser único
- La contraseña debe cumplir requisitos de seguridad (AWS Cognito)

#### Response 201 Created

```json
{
  "id": "456e4567-e89b-12d3-a456-426614174000",
  "name": "Transportes XYZ",
  "status": "PENDING",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 400 | `"Ya existe un usuario con este correo electrónico."` |
| 400 | `"Ya existe un cliente con este nombre."` |
| 422 | Error de validación (contraseña débil, email inválido, etc.) |

#### Proceso Interno

```
1. Crear Organization (status=PENDING)
   ↓
2. Crear User (email_verified=false, is_master=true)
   ↓
3. Crear Organization_User (role=owner)
   ↓
4. Generar token de verificación con password_temp
   ↓
5. Enviar email de verificación
   ↓
6. Usuario debe verificar email para activar cuenta
```

#### Nota sobre Contraseña Temporal

La contraseña proporcionada se guarda temporalmente en el token de verificación (`password_temp`):
- Se reutiliza en todos los reenvíos de verificación
- Solo se usa internamente para crear el usuario en AWS Cognito
- Nunca se envía por correo electrónico
- Se elimina permanentemente después de la verificación exitosa

---

### 2. Obtener Organización Actual

**GET** `/api/v1/clients/`

Obtiene la información de la organización del usuario autenticado, incluyendo sus suscripciones.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
{
  "id": "456e4567-e89b-12d3-a456-426614174000",
  "name": "Transportes XYZ",
  "status": "ACTIVE",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T15:45:00Z"
}
```

> **Nota de Evolución**: Este endpoint debería expandirse para incluir suscripciones y capabilities efectivas. Ver estructura esperada más adelante.

#### Errores Posibles

| Código | Detalle |
|--------|---------|
| 401 | Token no proporcionado o inválido |
| 404 | `"Cliente no encontrado"` |

---

### 3. Obtener Organización Actual (Versión Extendida - Esperada)

**GET** `/api/v1/clients/me`

> **Estado**: Endpoint esperado para implementación futura

Este endpoint debería devolver información completa de la organización:

#### Response Esperado

```json
{
  "organization": {
    "id": "456e4567-e89b-12d3-a456-426614174000",
    "name": "Transportes XYZ",
    "status": "ACTIVE",
    "created_at": "2024-01-15T10:30:00Z"
  },
  "subscriptions": {
    "active": [
      {
        "id": "789e4567-e89b-12d3-a456-426614174001",
        "plan": {
          "id": "plan-uuid",
          "name": "Plan Enterprise"
        },
        "status": "ACTIVE",
        "started_at": "2024-01-01T00:00:00Z",
        "expires_at": "2025-01-01T00:00:00Z",
        "auto_renew": true
      }
    ],
    "history": [
      {
        "id": "old-sub-uuid",
        "plan": {
          "id": "old-plan-uuid",
          "name": "Plan Básico"
        },
        "status": "EXPIRED",
        "started_at": "2023-01-01T00:00:00Z",
        "expires_at": "2024-01-01T00:00:00Z"
      }
    ]
  },
  "effective_capabilities": {
    "max_devices": 100,
    "max_geofences": 50,
    "max_users": 25,
    "history_days": 365,
    "ai_features": true,
    "analytics_tools": true
  },
  "current_user": {
    "id": "user-uuid",
    "email": "admin@transportesxyz.com",
    "role": "owner"
  }
}
```

---

## Estados de la Organización

### PENDING

- Organización recién creada
- Email no verificado
- No puede iniciar sesión
- Esperando confirmación de email

### ACTIVE

- Email verificado
- Usuario propietario creado en Cognito
- Puede iniciar sesión y usar el sistema
- Suscripciones y capabilities activas

### SUSPENDED

- Organización suspendida administrativamente
- No puede acceder al sistema
- Datos preservados
- Puede reactivarse desde API interna

### DELETED

- Organización eliminada lógicamente
- No puede acceder al sistema
- Datos marcados como eliminados

---

## Flujo de Registro Completo

### 1. Registro Inicial

```
Usuario → POST /api/v1/clients/
        ↓
  Organización creada (PENDING)
        ↓
  Usuario owner creado (sin cognito_sub)
        ↓
  Organization_User creado (role=owner)
        ↓
  Token de verificación generado con password_temp
        ↓
  Email enviado con link de verificación
```

### 2. Verificación de Email

```
Usuario → Clic en link del email
        ↓
  POST /api/v1/auth/verify-email?token=...
        ↓
  Usuario creado en AWS Cognito
        ↓
  Contraseña establecida desde password_temp
        ↓
  Organization.status = ACTIVE
        ↓
  password_temp eliminado permanentemente
        ↓
  Usuario puede hacer login con su contraseña
```

### 3. Email No Recibido (Reenvío)

```
Usuario → POST /api/v1/auth/resend-verification
        ↓
  Sistema busca password_temp del token previo
        ↓
  Nuevo token generado con el MISMO password_temp
        ↓
  Tokens anteriores invalidados
        ↓
  Nuevo email enviado
```

**Ventaja del Sistema de Reenvío:**
- El usuario puede solicitar reenvío 1, 10 o 100 veces
- La contraseña siempre será la misma (la que eligió al registrarse)
- No hay riesgo de inconsistencias
- Funciona incluso si los tokens expiran

---

## Arquitectura Multi-tenant

### Aislamiento de Datos

- Cada organización tiene acceso solo a sus propios datos
- Todos los modelos tienen `client_id` como foreign key
- Las consultas automáticamente filtran por `client_id`

### Identificación de la Organización

```
Token JWT → cognito_sub extraído
          ↓
  Usuario buscado por cognito_sub
          ↓
  organization_id (client_id) extraído del usuario
          ↓
  Todas las consultas filtradas por organization_id
```

### Ventajas

- **Aislamiento**: Los datos están completamente separados
- **Seguridad**: Imposible acceder a datos de otras organizaciones
- **Escalabilidad**: Fácil agregar nuevas organizaciones
- **Simplicidad**: Una sola base de datos para todos

---

## Relaciones de la Organización

Una organización tiene:

```
Organization
├── Users (uno o más usuarios, al menos uno owner)
│   └── Organization_Users (roles específicos)
├── Subscriptions (MÚLTIPLES suscripciones)
├── Devices (dispositivos GPS)
├── Units (vehículos/activos)
├── Orders (historial de compras)
├── Payments (historial de pagos)
└── Capability_Overrides (ajustes específicos de límites)
```

---

## Sistema de Suscripciones

### Principio Fundamental

> Una organización puede tener **múltiples suscripciones** simultáneamente o a lo largo del tiempo.

### Estados de Suscripción

| Estado | Descripción |
|--------|-------------|
| `ACTIVE` | Suscripción vigente |
| `TRIAL` | Período de prueba |
| `EXPIRED` | Vencida por tiempo |
| `CANCELLED` | Cancelada manualmente |

### Cálculo de Suscripción Activa

```python
# Enfoque CORRECTO
active_subscriptions = subscriptions.filter(
    client_id=org_id, 
    status__in=['ACTIVE', 'TRIAL']
)

# Enfoque INCORRECTO (deprecado)
# NO usar: client.active_subscription_id
```

### Ejemplo de Organización con Múltiples Suscripciones

```json
{
  "organization_id": "org-uuid",
  "subscriptions": [
    {
      "id": "sub-1",
      "plan_name": "Plan Enterprise",
      "status": "ACTIVE",
      "purpose": "Flota principal"
    },
    {
      "id": "sub-2", 
      "plan_name": "Plan Básico",
      "status": "ACTIVE",
      "purpose": "Proyecto piloto"
    },
    {
      "id": "sub-3",
      "plan_name": "Plan Pro",
      "status": "EXPIRED",
      "purpose": "Contrato anterior"
    }
  ]
}
```

---

## Sistema de Capabilities

### Resolución de Capabilities Efectivas

Las capabilities de una organización se resuelven con la siguiente prioridad:

```
organization_capability_override
        ??
plan_capability (del plan activo)
        ??
default_capability
```

### Ejemplo de Resolución

```
Organización: Transportes XYZ
Plan: Enterprise (max_geofences = 50)
Override: max_geofences = 100

Capability Efectiva: max_geofences = 100 (override gana)
```

### Uso en Validaciones

```python
# Antes de crear una geocerca
effective_cap = get_effective_capability(org_id, "max_geofences")
current_count = count_geofences(org_id)

if current_count >= effective_cap:
    raise HTTPException(
        status_code=403,
        detail="Has alcanzado el límite de geocercas de tu plan"
    )
```

---

## Notas de Seguridad

### Creación de Organización

- Endpoint público (no requiere autenticación)
- Rate limiting recomendado
- Validación de email para evitar spam
- La contraseña se guarda temporalmente solo durante el proceso de verificación
- El `password_temp` se elimina permanentemente después de la verificación exitosa

### Verificación de Email

- Los endpoints de verificación están en `/api/v1/auth/`:
  - `POST /api/v1/auth/resend-verification` - Reenviar verificación
  - `POST /api/v1/auth/verify-email?token=...` - Verificar email
- El sistema reutiliza `password_temp` en reenvíos para garantizar consistencia
- Los tokens expiran en 24 horas pero pueden reenviarse indefinidamente
- La contraseña nunca se envía por correo, solo se usa internamente

### Acceso a Datos

- Siempre se valida el `organization_id` del token
- No es posible cambiar el `organization_id` de un usuario
- Los endpoints automáticamente filtran por organización

### Usuario Propietario (Owner)

- Se crea automáticamente con la organización
- `is_master=True` y `role=owner`
- Tiene permisos totales sobre la organización
- Puede transferir ownership a otro usuario
- No puede eliminarse sin eliminar la organización

---

## Migración de Terminología

### Mapeo de Términos

Para mantener compatibilidad mientras se actualiza la documentación:

| Término Antiguo | Término Nuevo | Contexto |
|-----------------|---------------|----------|
| Cliente | Organización | Negocio |
| `client_id` | `organization_id` | API (conceptual) |
| `is_master` | `role: owner/admin` | Roles |
| `active_subscription_id` | Suscripciones activas | Suscripciones |

### Endpoints Afectados

| Endpoint Actual | Significado Real |
|-----------------|------------------|
| `POST /api/v1/clients/` | Crear organización |
| `GET /api/v1/clients/` | Obtener mi organización |
| `GET /api/v1/internal/clients` | Listar todas las organizaciones |

---

**Última actualización**: Diciembre 2025  
**Referencia**: [Modelo Organizacional](../guides/organizational-model.md)
