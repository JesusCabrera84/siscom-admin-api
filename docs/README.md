# Documentación SISCOM Admin API

Bienvenido a la documentación completa de la API administrativa de SISCOM.

---

## 📚 Guías de Inicio

Comienza aquí si eres nuevo en el proyecto:

- **[Guía Rápida](guides/quickstart.md)** - Configuración inicial y primeros pasos
- **[Configuración de Cognito](guides/cognito-setup.md)** - Setup de AWS Cognito para autenticación
- **[Arquitectura del Sistema](guides/architecture.md)** - Diseño y estructura del proyecto

---

## 🔌 Documentación de Endpoints

### Autenticación y Usuarios

- **[Autenticación](api/auth.md)** - Login, recuperación de contraseña, verificación de email
- **[Clientes](api/clients.md)** - Registro y gestión de organizaciones
- **[Usuarios](api/users.md)** - Invitaciones y gestión de usuarios

### Gestión de Dispositivos

- **[Dispositivos](api/devices.md)** - Registro y consulta de dispositivos GPS
- **[Servicios](api/services.md)** - Activación y gestión de suscripciones de rastreo
- **[Planes](api/plans.md)** - Catálogo de planes disponibles

### Comercial

- **[Órdenes](api/orders.md)** - Compra de dispositivos GPS
- **[Pagos](api/payments.md)** - Historial y gestión de pagos

---

## 🏗️ Arquitectura

### Flujo de Negocio

```
1. Registro de Cliente
   ↓
2. Verificación de Email
   ↓
3. Login y Obtención de Token
   ↓
4. Compra de Dispositivos (Orden + Pago)
   ↓
5. Instalación de Dispositivos en Vehículos
   ↓
6. Activación de Servicio (Suscripción)
   ↓
7. Rastreo Activo GPS
```

### Multi-tenant

- Cada cliente tiene datos completamente aislados
- El `client_id` se extrae automáticamente del token JWT
- Imposible acceder a datos de otros clientes

---

## 🔐 Autenticación

Todos los endpoints (excepto públicos) requieren token de AWS Cognito:

```bash
Authorization: Bearer <access_token>
```

### Obtener Token

```bash
POST /api/v1/auth/login
{
  "email": "usuario@ejemplo.com",
  "password": "MiPassword123!"
}
```

### Usar Token

```bash
GET /api/v1/devices/
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 📖 Endpoints Públicos

Estos endpoints **NO** requieren autenticación:

- `GET /` - Health check
- `GET /api/v1/plans/` - Listar planes
- `POST /api/v1/clients/` - Crear cliente (registro)
- `POST /api/v1/clients/confirm-email` - Confirmar email
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/forgot-password` - Recuperar contraseña
- `POST /api/v1/auth/reset-password` - Restablecer contraseña

---

## 🚀 Casos de Uso Comunes

### 1. Registrar Nueva Empresa

```bash
# 1. Crear cliente
POST /api/v1/clients/
{
  "name": "Transportes ABC",
  "email": "admin@abc.com",
  "password": "Password123!"
}

# 2. Verificar email (usar token del email)
POST /api/v1/clients/confirm-email
{
  "token": "..."
}

# 3. Login
POST /api/v1/auth/login
{
  "email": "admin@abc.com",
  "password": "Password123!"
}
```

### 2. Comprar y Activar Dispositivo

```bash
# 1. Ver planes disponibles
GET /api/v1/plans/

# 2. Crear orden de dispositivos
POST /api/v1/orders/
{
  "items": [...]
}

# 3. Registrar dispositivo
POST /api/v1/devices/
{
  "serial_number": "GPS-001",
  "model": "TK103",
  "imei": "353451234567890"
}

# 4. Activar servicio
POST /api/v1/services/activate
{
  "device_id": "...",
  "plan_id": "...",
  "subscription_type": "MONTHLY"
}
```

### 3. Invitar Usuario a la Organización

```bash
# 1. Enviar invitación (solo usuario maestro)
POST /api/v1/users/invite
{
  "email": "usuario@abc.com",
  "full_name": "Juan Pérez"
}

# 2. Usuario acepta invitación (usa token del email)
POST /api/v1/users/accept-invitation
{
  "token": "...",
  "password": "Password123!"
}

# 3. Usuario hace login
POST /api/v1/auth/login
{
  "email": "usuario@abc.com",
  "password": "Password123!"
}
```

---

## 🗂️ Modelos de Datos Principales

### Client (Cliente/Organización)

```python
id: UUID
name: str
status: PENDING | ACTIVE | SUSPENDED
created_at: datetime
```

### User (Usuario)

```python
id: UUID
client_id: UUID
email: str
full_name: str
is_master: bool
email_verified: bool
cognito_sub: str
created_at: datetime
```

### Device (Dispositivo GPS)

```python
id: UUID
client_id: UUID
serial_number: str
model: str
imei: str
active: bool
installed_in_unit_id: UUID | None
created_at: datetime
```

### DeviceService (Servicio de Dispositivo)

```python
id: UUID
client_id: UUID
device_id: UUID
plan_id: UUID
subscription_type: MONTHLY | YEARLY
status: PENDING | ACTIVE | EXPIRED | CANCELLED
activated_at: datetime
expires_at: datetime
auto_renew: bool
payment_id: UUID
```

### Payment (Pago)

```python
id: UUID
client_id: UUID
amount: Decimal
status: PENDING | SUCCESS | FAILED | REFUNDED
payment_method: str
device_service_id: UUID | None
order_id: UUID | None
created_at: datetime
paid_at: datetime | None
```

---

## ⚙️ Configuración

### Variables de Entorno Requeridas

```bash
# Base de datos
DB_HOST=localhost
DB_PORT=5432
DB_USER=siscom
DB_PASSWORD=password
DB_NAME=siscom_admin

# AWS Cognito
AWS_REGION=us-east-1
COGNITO_USERPOOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
COGNITO_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
COGNITO_REGION=us-east-1

# API
PROJECT_NAME=SISCOM Admin API
```

---

## 🧪 Testing

### Scripts de Prueba

Los scripts de testing están en `scripts/testing/`:

- `test_auth_endpoints.sh` - Prueba flujos de autenticación
- `test_user_creation.sh` - Prueba creación de usuarios
- `test_password_recovery.sh` - Prueba recuperación de contraseña
- `test_invitation_resend.sh` - Prueba reenvío de invitaciones

---

## 📊 Documentación Interactiva

Una vez que la API esté corriendo:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🛠️ Desarrollo

### Ejecutar Localmente

```bash
# Con Docker
docker-compose up -d

# Sin Docker
uvicorn app.main:app --reload
```

### Ejecutar Tests

```bash
pytest -v
```

### Crear Migración

```bash
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
```

---

## 📞 Soporte

- **Email**: soporte@siscom.com
- **Documentación**: http://localhost:8000/docs
- **Repositorio**: [GitHub](https://github.com/...)

---

## 📝 Notas Importantes

### Seguridad

- Los tokens de acceso expiran en 1 hora
- Usar HTTPS en producción
- No compartir credenciales de Cognito
- Validar todos los inputs del usuario

### Límites y Restricciones

- Un dispositivo solo puede tener UN servicio ACTIVE simultáneamente
- Los seriales e IMEIs deben ser únicos en todo el sistema
- Los emails deben ser únicos por cliente

### Mejores Prácticas

- Siempre manejar errores 401 (token expirado)
- Implementar refresh token para renovar acceso
- Validar permisos de usuario (is_master) en frontend
- Mostrar mensajes de error claros al usuario

---

## 🔄 Actualizaciones

Ver [CHANGELOG](../CHANGELOG.md) para cambios recientes en la API.

---

**Última actualización**: Noviembre 2025

