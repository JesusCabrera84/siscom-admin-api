# 📘 SISCOM Admin API - Documentación Completa

## 🎯 Descripción General

**SISCOM Admin API** es una API REST multi-tenant para la gestión integral de sistemas de rastreo GPS/IoT. Permite a múltiples clientes administrar dispositivos de rastreo, vehículos/unidades, usuarios, planes de servicio y facturación de manera completamente aislada.

### Características Principales

- 🏢 **Multi-tenant**: Cada cliente tiene sus datos completamente aislados
- 🔐 **Autenticación AWS Cognito**: Sistema robusto de autenticación con JWT
- 📱 **Gestión de Dispositivos GPS**: Inventario y seguimiento completo de dispositivos
- 🚗 **Gestión de Unidades/Vehículos**: Organización de flotas con permisos granulares
- 👥 **Sistema de Usuarios**: Usuarios maestros y usuarios con permisos específicos
- 💳 **Facturación Completa**: Órdenes, pagos y suscripciones mensuales/anuales
- 📧 **Notificaciones por Email**: Sistema integrado con AWS SES
- 📊 **Auditoría**: Registro completo de eventos en dispositivos

---

## 🏗️ Arquitectura

### Stack Tecnológico

- **Framework**: FastAPI 0.109.0
- **Base de Datos**: PostgreSQL 16
- **ORM**: SQLAlchemy 2.x / SQLModel
- **Autenticación**: AWS Cognito
- **Emails**: AWS SES con templates Jinja2
- **Deployment**: Docker + GitHub Actions CI/CD
- **Documentación Interactiva**: Swagger UI / ReDoc

### URL Base

```
Desarrollo: http://localhost:8100
Producción: https://api.tudominio.com
```

### Versionado

Todas las rutas de la API están bajo el prefijo `/api/v1`

```
http://localhost:8100/api/v1/...
```

---

## 🔐 Autenticación

La API utiliza **AWS Cognito** con tokens JWT Bearer.

### Obtener Token de Acceso

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "usuario@ejemplo.com",
  "password": "tu_password"
}
```

**Respuesta:**
```json
{
  "user": {
    "id": "uuid",
    "email": "usuario@ejemplo.com",
    "full_name": "Usuario Ejemplo",
    "is_master": true,
    "email_verified": true
  },
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "id_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Usar el Token

Incluye el `access_token` en el header de todas las peticiones autenticadas:

```http
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 📚 Endpoints por Categoría

### 📋 Índice de Endpoints

1. [**Autenticación** (`/auth`)](#1-autenticación-auth) - Login, logout, recuperación de contraseña
2. [**Clientes** (`/clients`)](#2-clientes-clients) - Registro y gestión de clientes
3. [**Usuarios** (`/users`)](#3-usuarios-users) - Invitaciones y gestión de usuarios
4. [**Dispositivos** (`/devices`)](#4-dispositivos-devices) - Inventario y gestión de GPS
5. [**Eventos de Dispositivos** (`/device-events`)](#5-eventos-de-dispositivos-device-events) - Historial de eventos
6. [**Unidades/Vehículos** (`/units`)](#6-unidades-units) - Gestión de flotas
7. [**Asignación Unidad-Dispositivo** (`/unit-devices`)](#7-asignación-unidad-dispositivo-unit-devices) - Instalaciones
8. [**Asignación Usuario-Unidad** (`/user-units`)](#8-asignación-usuario-unidad-user-units) - Permisos por unidad
9. [**Servicios** (`/services`)](#9-servicios-services) - Activación de servicios de rastreo
10. [**Planes** (`/plans`)](#10-planes-plans) - Catálogo de planes disponibles
11. [**Órdenes** (`/orders`)](#11-órdenes-orders) - Pedidos de hardware
12. [**Pagos** (`/payments`)](#12-pagos-payments) - Gestión de pagos

---

## 1. Autenticación (`/auth`)

### 🔓 Endpoints Públicos (No requieren autenticación)

#### `POST /api/v1/auth/login`
**Iniciar sesión**

Autentica a un usuario y retorna tokens de acceso.

**Request:**
```json
{
  "email": "usuario@ejemplo.com",
  "password": "Password123!"
}
```

**Response:** `200 OK`
```json
{
  "user": { ... },
  "access_token": "...",
  "id_token": "...",
  "refresh_token": "...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

---

#### `POST /api/v1/auth/forgot-password`
**Solicitar restablecimiento de contraseña**

Genera un token y envía un email con el enlace de recuperación.

**Request:**
```json
{
  "email": "usuario@ejemplo.com"
}
```

**Response:** `200 OK`
```json
{
  "message": "Se ha enviado un código de verificación al correo registrado."
}
```

**Email enviado:** Link a `{FRONTEND_URL}/reset-password?token={token}`

---

#### `POST /api/v1/auth/reset-password`
**Restablecer contraseña con token**

Usa el token recibido por email para establecer una nueva contraseña.

**Request:**
```json
{
  "token": "uuid-token-from-email",
  "new_password": "NuevaPassword123!"
}
```

**Response:** `200 OK`
```json
{
  "message": "Contraseña restablecida exitosamente. Ahora puede iniciar sesión con su nueva contraseña."
}
```

---

#### `POST /api/v1/auth/resend-verification`
**Reenviar email de verificación**

Reenvía el correo de verificación a usuarios no verificados.

**Request:**
```json
{
  "email": "usuario@ejemplo.com"
}
```

**Response:** `200 OK`
```json
{
  "message": "Si la cuenta existe, se ha reenviado el correo de verificación."
}
```

---

#### `POST /api/v1/auth/confirm-email`
**Confirmar email con token**

Verifica el email del usuario usando el token enviado por correo.

**Request:**
```json
{
  "token": "uuid-token-from-email"
}
```

**Response:** `200 OK`
```json
{
  "message": "Email verificado exitosamente. Ahora puede iniciar sesión."
}
```

---

### 🔒 Endpoints Autenticados

#### `POST /api/v1/auth/logout`
**Cerrar sesión**

Invalida todos los tokens del usuario.

**Headers:** `Authorization: Bearer {access_token}`

**Response:** `200 OK`
```json
{
  "message": "Sesión cerrada exitosamente."
}
```

---

#### `PATCH /api/v1/auth/password`
**Cambiar contraseña (usuario autenticado)**

Permite al usuario cambiar su contraseña proporcionando la actual.

**Headers:** `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "old_password": "PasswordActual123!",
  "new_password": "NuevaPassword123!"
}
```

**Response:** `200 OK`
```json
{
  "message": "Contraseña actualizada exitosamente."
}
```

---

## 2. Clientes (`/clients`)

### 🔓 Público

#### `POST /api/v1/clients/`
**Registrar nuevo cliente**

Crea un nuevo cliente con su usuario maestro. Envía email de verificación.

**Request:**
```json
{
  "name": "Mi Empresa S.A.",
  "email": "admin@miempresa.com",
  "password": "Password123!"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "name": "Mi Empresa S.A.",
  "status": "PENDING",
  "created_at": "2024-11-08T10:00:00Z"
}
```

**Email enviado:** Link a `{FRONTEND_URL}/verify-email?token={token}`

**Nota:** El cliente y usuario quedan en estado `PENDING` hasta verificar el email.

---

#### `POST /api/v1/clients/verify-email`
**Verificar email del cliente**

Verifica el email y activa el cliente y usuario maestro.

**Query Parameters:**
- `token` (string): Token de verificación recibido por email

**Response:** `200 OK`
```json
{
  "message": "Email verificado exitosamente. Tu cuenta ha sido activada.",
  "email": "admin@miempresa.com",
  "client_id": "uuid"
}
```

---

### 🔒 Autenticados

#### `GET /api/v1/clients/`
**Obtener información del cliente autenticado**

**Headers:** `Authorization: Bearer {access_token}`

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "name": "Mi Empresa S.A.",
  "status": "ACTIVE",
  "created_at": "2024-11-08T10:00:00Z",
  "updated_at": "2024-11-08T10:05:00Z"
}
```

---

## 3. Usuarios (`/users`)

### 🔒 Todos requieren autenticación

#### `GET /api/v1/users/`
**Listar todos los usuarios del cliente**

**Headers:** `Authorization: Bearer {access_token}`

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "email": "admin@miempresa.com",
    "full_name": "Administrador Principal",
    "is_master": true,
    "email_verified": true,
    "last_login_at": "2024-11-08T10:00:00Z",
    "created_at": "2024-11-08T09:00:00Z"
  },
  {
    "id": "uuid",
    "email": "usuario@miempresa.com",
    "full_name": "Usuario Regular",
    "is_master": false,
    "email_verified": true,
    "last_login_at": "2024-11-08T11:00:00Z",
    "created_at": "2024-11-08T09:30:00Z"
  }
]
```

---

#### `GET /api/v1/users/me`
**Obtener información del usuario actual**

**Headers:** `Authorization: Bearer {access_token}`

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "email": "admin@miempresa.com",
  "full_name": "Administrador Principal",
  "is_master": true,
  "email_verified": true,
  "client_id": "uuid",
  "last_login_at": "2024-11-08T10:00:00Z",
  "created_at": "2024-11-08T09:00:00Z"
}
```

---

#### `POST /api/v1/users/invite`
**Invitar nuevo usuario** (Solo usuarios maestros)

Envía una invitación por email para que un nuevo usuario se registre.

**Headers:** `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "email": "nuevousuario@miempresa.com",
  "full_name": "Nuevo Usuario"
}
```

**Response:** `201 Created`
```json
{
  "detail": "Invitación enviada a nuevousuario@miempresa.com",
  "expires_at": "2024-11-11T10:00:00Z"
}
```

**Email enviado:** Link a `{FRONTEND_URL}/accept-invitation?token={token}`

**Errores:**
- `403 Forbidden`: Si el usuario no es maestro
- `400 Bad Request`: Si el email ya está registrado o tiene invitación pendiente

---

#### `POST /api/v1/users/accept-invitation`
**Aceptar invitación** (Público)

El usuario invitado usa el token para crear su cuenta.

**Request:**
```json
{
  "token": "uuid-token-from-email",
  "password": "Password123!"
}
```

**Response:** `201 Created`
```json
{
  "detail": "Usuario creado exitosamente.",
  "user": {
    "id": "uuid",
    "email": "nuevousuario@miempresa.com",
    "full_name": "Nuevo Usuario",
    "is_master": false,
    "email_verified": true
  }
}
```

---

#### `POST /api/v1/users/resend-invitation`
**Reenviar invitación** (Solo usuarios maestros)

Reenvía una invitación a un email que no ha aceptado.

**Headers:** `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "email": "nuevousuario@miempresa.com"
}
```

**Response:** `200 OK`
```json
{
  "message": "Invitación reenviada a nuevousuario@miempresa.com",
  "expires_at": "2024-11-11T10:00:00Z"
}
```

---

## 4. Dispositivos (`/devices`)

Gestión del inventario de dispositivos GPS.

### 🔒 Todos requieren autenticación

#### `POST /api/v1/devices/`
**Registrar nuevo dispositivo**

Agrega un dispositivo al inventario con estado "nuevo".

**Headers:** `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "device_id": "IMEI123456789",
  "brand": "Teltonika",
  "model": "FMB120",
  "firmware_version": "03.28.07",
  "notes": "Dispositivo para instalación en vehículo comercial"
}
```

**Response:** `201 Created`
```json
{
  "device_id": "IMEI123456789",
  "brand": "Teltonika",
  "model": "FMB120",
  "firmware_version": "03.28.07",
  "status": "nuevo",
  "active": false,
  "client_id": null,
  "notes": "Dispositivo para instalación en vehículo comercial",
  "created_at": "2024-11-08T10:00:00Z"
}
```

**Estados del dispositivo:**
- `nuevo`: Recién registrado, sin asignar
- `asignado`: Asignado a un cliente
- `instalado`: Instalado en una unidad
- `activo`: Con servicio activo
- `suspendido`: Servicio suspendido por falta de pago
- `desinstalado`: Desinstalado de la unidad
- `inactivo`: Sin servicio
- `baja`: Dado de baja del sistema

---

#### `GET /api/v1/devices/`
**Listar dispositivos del cliente**

Lista todos los dispositivos asignados al cliente autenticado.

**Headers:** `Authorization: Bearer {access_token}`

**Query Parameters (opcionales):**
- `status` (string): Filtrar por estado (nuevo, asignado, instalado, activo, etc.)
- `active` (boolean): Filtrar por estado de servicio activo

**Response:** `200 OK`
```json
[
  {
    "device_id": "IMEI123456789",
    "brand": "Teltonika",
    "model": "FMB120",
    "firmware_version": "03.28.07",
    "status": "activo",
    "active": true,
    "client_id": "uuid",
    "notes": null,
    "created_at": "2024-11-08T10:00:00Z",
    "updated_at": "2024-11-08T12:00:00Z"
  }
]
```

---

#### `GET /api/v1/devices/{device_id}`
**Obtener detalles de un dispositivo**

**Headers:** `Authorization: Bearer {access_token}`

**Response:** `200 OK`
```json
{
  "device_id": "IMEI123456789",
  "brand": "Teltonika",
  "model": "FMB120",
  "firmware_version": "03.28.07",
  "status": "instalado",
  "active": false,
  "client_id": "uuid",
  "notes": "Instalado en camioneta Toyota Hilux",
  "created_at": "2024-11-08T10:00:00Z",
  "updated_at": "2024-11-08T11:30:00Z"
}
```

---

#### `PATCH /api/v1/devices/{device_id}`
**Actualizar dispositivo**

Actualiza información del dispositivo (firmware, notas, etc.).

**Headers:** `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "firmware_version": "03.28.08",
  "notes": "Firmware actualizado remotamente"
}
```

**Response:** `200 OK`
```json
{
  "device_id": "IMEI123456789",
  "brand": "Teltonika",
  "model": "FMB120",
  "firmware_version": "03.28.08",
  "status": "activo",
  "active": true,
  "client_id": "uuid",
  "notes": "Firmware actualizado remotamente",
  "updated_at": "2024-11-08T14:00:00Z"
}
```

---

#### `PATCH /api/v1/devices/{device_id}/status`
**Cambiar estado del dispositivo**

Actualiza el estado operativo del dispositivo.

**Headers:** `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "new_status": "suspendido",
  "reason": "Falta de pago del servicio mensual"
}
```

**Response:** `200 OK`
```json
{
  "device_id": "IMEI123456789",
  "old_status": "activo",
  "new_status": "suspendido",
  "updated_at": "2024-11-08T15:00:00Z"
}
```

---

#### `DELETE /api/v1/devices/{device_id}`
**Eliminar dispositivo** (Soft delete)

Marca el dispositivo como dado de baja.

**Headers:** `Authorization: Bearer {access_token}`

**Response:** `200 OK`
```json
{
  "message": "Dispositivo IMEI123456789 dado de baja exitosamente"
}
```

---

## 5. Eventos de Dispositivos (`/device-events`)

Historial de auditoría de todos los cambios en dispositivos.

### 🔒 Todos requieren autenticación

#### `GET /api/v1/device-events/`
**Listar eventos de dispositivos**

**Headers:** `Authorization: Bearer {access_token}`

**Query Parameters (opcionales):**
- `device_id` (string): Filtrar por dispositivo específico
- `event_type` (string): Filtrar por tipo de evento
- `limit` (int, default=100): Límite de resultados

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "device_id": "IMEI123456789",
    "event_type": "creado",
    "old_status": null,
    "new_status": "nuevo",
    "performed_by": "uuid-user",
    "event_details": "Dispositivo Teltonika FMB120 registrado en inventario",
    "timestamp": "2024-11-08T10:00:00Z"
  },
  {
    "id": "uuid",
    "device_id": "IMEI123456789",
    "event_type": "asignado",
    "old_status": "nuevo",
    "new_status": "asignado",
    "performed_by": "uuid-user",
    "event_details": "Dispositivo asignado al cliente Mi Empresa S.A.",
    "timestamp": "2024-11-08T10:30:00Z"
  }
]
```

**Tipos de eventos:**
- `creado`: Dispositivo registrado
- `asignado`: Asignado a cliente
- `instalado`: Instalado en unidad
- `desinstalado`: Desinstalado de unidad
- `activado`: Servicio activado
- `suspendido`: Servicio suspendido
- `actualizado`: Información actualizada
- `dado_de_baja`: Dispositivo eliminado

---

## 6. Unidades (`/units`)

Gestión de vehículos, maquinaria o cualquier unidad rastreable.

### 🔒 Todos requieren autenticación

#### `POST /api/v1/units/`
**Crear nueva unidad**

**Headers:** `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "name": "Camioneta #01",
  "type": "vehiculo",
  "identifier": "ABC-123",
  "brand": "Toyota",
  "model": "Hilux",
  "year": 2023,
  "color": "Blanco",
  "notes": "Camioneta para distribución zona norte"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "client_id": "uuid",
  "name": "Camioneta #01",
  "type": "vehiculo",
  "identifier": "ABC-123",
  "brand": "Toyota",
  "model": "Hilux",
  "year": 2023,
  "color": "Blanco",
  "notes": "Camioneta para distribución zona norte",
  "created_at": "2024-11-08T10:00:00Z",
  "updated_at": "2024-11-08T10:00:00Z",
  "deleted_at": null
}
```

**Tipos de unidad comunes:**
- `vehiculo`: Automóviles, camionetas, camiones
- `maquinaria`: Grúas, excavadoras, etc.
- `contenedor`: Contenedores de carga
- `persona`: Para rastreo personal
- `otro`: Otros tipos

---

#### `GET /api/v1/units/`
**Listar unidades**

Lista las unidades según los permisos del usuario:
- **Usuario maestro**: Ve todas las unidades del cliente
- **Usuario regular**: Solo ve las unidades asignadas a él

**Headers:** `Authorization: Bearer {access_token}`

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "client_id": "uuid",
    "name": "Camioneta #01",
    "type": "vehiculo",
    "identifier": "ABC-123",
    "brand": "Toyota",
    "model": "Hilux",
    "year": 2023,
    "color": "Blanco",
    "created_at": "2024-11-08T10:00:00Z"
  }
]
```

---

#### `GET /api/v1/units/{unit_id}`
**Obtener detalles de unidad con dispositivos y usuarios**

Incluye dispositivos asignados y usuarios con acceso.

**Headers:** `Authorization: Bearer {access_token}`

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "name": "Camioneta #01",
  "type": "vehiculo",
  "identifier": "ABC-123",
  "brand": "Toyota",
  "model": "Hilux",
  "year": 2023,
  "devices": [
    {
      "device_id": "IMEI123456789",
      "brand": "Teltonika",
      "model": "FMB120",
      "status": "activo",
      "installed_at": "2024-11-08T11:00:00Z"
    }
  ],
  "assigned_users": [
    {
      "user_id": "uuid",
      "email": "conductor@miempresa.com",
      "full_name": "Juan Pérez",
      "role": "viewer",
      "assigned_at": "2024-11-08T10:30:00Z"
    }
  ]
}
```

---

#### `PATCH /api/v1/units/{unit_id}`
**Actualizar unidad**

**Headers:** `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "name": "Camioneta #01 (Renovada)",
  "color": "Gris",
  "notes": "Se cambió el color del vehículo"
}
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "name": "Camioneta #01 (Renovada)",
  "color": "Gris",
  "notes": "Se cambió el color del vehículo",
  "updated_at": "2024-11-08T12:00:00Z"
}
```

---

#### `DELETE /api/v1/units/{unit_id}`
**Eliminar unidad** (Soft delete)

Marca la unidad como eliminada. Solo usuarios maestros o con rol "admin" en la unidad.

**Headers:** `Authorization: Bearer {access_token}`

**Response:** `200 OK`
```json
{
  "message": "Unidad Camioneta #01 eliminada exitosamente"
}
```

---

## 7. Asignación Unidad-Dispositivo (`/unit-devices`)

Gestión de instalaciones de dispositivos en unidades.

### 🔒 Todos requieren autenticación

#### `POST /api/v1/unit-devices/assign`
**Instalar dispositivo en unidad**

Asigna un dispositivo GPS a una unidad/vehículo.

**Headers:** `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "unit_id": "uuid",
  "device_id": "IMEI123456789",
  "notes": "Instalado debajo del tablero"
}
```

**Response:** `201 Created`
```json
{
  "unit_id": "uuid",
  "device_id": "IMEI123456789",
  "installed_at": "2024-11-08T11:00:00Z",
  "uninstalled_at": null,
  "notes": "Instalado debajo del tablero"
}
```

**Validaciones:**
- El dispositivo debe pertenecer al cliente
- El dispositivo no debe estar instalado en otra unidad actualmente
- El usuario debe tener permisos sobre la unidad

---

#### `POST /api/v1/unit-devices/uninstall`
**Desinstalar dispositivo de unidad**

Marca un dispositivo como desinstalado de una unidad.

**Headers:** `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "unit_id": "uuid",
  "device_id": "IMEI123456789",
  "notes": "Desinstalado para mantenimiento"
}
```

**Response:** `200 OK`
```json
{
  "unit_id": "uuid",
  "device_id": "IMEI123456789",
  "installed_at": "2024-11-08T11:00:00Z",
  "uninstalled_at": "2024-11-08T14:00:00Z",
  "notes": "Desinstalado para mantenimiento"
}
```

---

#### `GET /api/v1/unit-devices/history/{device_id}`
**Historial de instalaciones de un dispositivo**

**Headers:** `Authorization: Bearer {access_token}`

**Response:** `200 OK`
```json
[
  {
    "unit_id": "uuid",
    "unit_name": "Camioneta #01",
    "device_id": "IMEI123456789",
    "installed_at": "2024-10-01T10:00:00Z",
    "uninstalled_at": "2024-10-15T14:00:00Z",
    "notes": "Reubicado a otro vehículo"
  },
  {
    "unit_id": "uuid",
    "unit_name": "Camioneta #02",
    "device_id": "IMEI123456789",
    "installed_at": "2024-10-15T15:00:00Z",
    "uninstalled_at": null,
    "notes": "Instalación actual"
  }
]
```

---

## 8. Asignación Usuario-Unidad (`/user-units`)

Sistema de permisos granulares por unidad.

### 🔒 Todos requieren autenticación (maestro o admin de la unidad)

#### `POST /api/v1/user-units/assign`
**Asignar usuario a unidad**

Otorga permisos a un usuario sobre una unidad específica.

**Headers:** `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "unit_id": "uuid",
  "user_id": "uuid",
  "role": "viewer"
}
```

**Roles disponibles:**
- `viewer`: Solo puede ver la unidad
- `editor`: Puede ver y editar información
- `admin`: Puede ver, editar y gestionar permisos

**Response:** `201 Created`
```json
{
  "unit_id": "uuid",
  "user_id": "uuid",
  "role": "viewer",
  "assigned_at": "2024-11-08T10:00:00Z"
}
```

---

#### `DELETE /api/v1/user-units/unassign`
**Desasignar usuario de unidad**

Revoca los permisos de un usuario sobre una unidad.

**Headers:** `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "unit_id": "uuid",
  "user_id": "uuid"
}
```

**Response:** `200 OK`
```json
{
  "message": "Usuario desasignado de la unidad exitosamente"
}
```

---

#### `GET /api/v1/user-units/{unit_id}/users`
**Listar usuarios asignados a una unidad**

**Headers:** `Authorization: Bearer {access_token}`

**Response:** `200 OK`
```json
[
  {
    "user_id": "uuid",
    "email": "conductor@miempresa.com",
    "full_name": "Juan Pérez",
    "role": "viewer",
    "assigned_at": "2024-11-08T10:00:00Z"
  }
]
```

---

## 9. Servicios (`/services`)

Activación y gestión de servicios de rastreo.

### 🔒 Todos requieren autenticación

#### `POST /api/v1/services/activate`
**Activar servicio de rastreo**

Activa un servicio de rastreo para un dispositivo según un plan.

**Headers:** `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "device_id": "IMEI123456789",
  "plan_id": "uuid",
  "subscription_type": "monthly"
}
```

**Tipos de suscripción:**
- `monthly`: Pago mensual
- `annual`: Pago anual (usualmente con descuento)

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "client_id": "uuid",
  "device_id": "IMEI123456789",
  "plan_id": "uuid",
  "status": "ACTIVE",
  "start_date": "2024-11-08",
  "end_date": "2024-12-08",
  "next_billing_date": "2024-12-08",
  "subscription_type": "monthly",
  "price_at_activation": "299.00",
  "currency": "MXN",
  "created_at": "2024-11-08T10:00:00Z"
}
```

**Validaciones:**
- Solo puede haber UN servicio ACTIVE por dispositivo
- El dispositivo debe pertenecer al cliente
- El plan debe existir y estar activo

---

#### `POST /api/v1/services/confirm-payment`
**Confirmar pago de servicio**

Confirma el pago de un servicio (usualmente tras confirmación de pasarela de pago).

**Headers:** `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "device_service_id": "uuid",
  "payment_id": "uuid"
}
```

**Response:** `200 OK`
```json
{
  "message": "Pago confirmado exitosamente",
  "payment_id": "uuid",
  "status": "SUCCESS"
}
```

---

#### `GET /api/v1/services/active`
**Listar servicios activos**

Lista todos los servicios activos del cliente con detalles de dispositivo y plan.

**Headers:** `Authorization: Bearer {access_token}`

**Response:** `200 OK`
```json
[
  {
    "service_id": "uuid",
    "device_id": "IMEI123456789",
    "device_brand": "Teltonika",
    "device_model": "FMB120",
    "plan_name": "Plan Profesional",
    "plan_features": "Rastreo en tiempo real, reportes avanzados",
    "status": "ACTIVE",
    "start_date": "2024-11-08",
    "next_billing_date": "2024-12-08",
    "price": "299.00",
    "currency": "MXN"
  }
]
```

---

#### `POST /api/v1/services/cancel`
**Cancelar servicio**

Cancela un servicio activo.

**Headers:** `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "device_service_id": "uuid",
  "reason": "Cliente solicitó cancelación"
}
```

**Response:** `200 OK`
```json
{
  "message": "Servicio cancelado exitosamente",
  "service_id": "uuid",
  "status": "CANCELLED",
  "cancelled_at": "2024-11-08T15:00:00Z"
}
```

---

## 10. Planes (`/plans`)

Catálogo de planes de servicio disponibles.

### 🔓 Público (no requiere autenticación)

#### `GET /api/v1/plans/`
**Listar planes disponibles**

Obtiene el catálogo completo de planes.

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "name": "Plan Básico",
    "description": "Rastreo en tiempo real con ubicación precisa",
    "features": [
      "Rastreo en tiempo real",
      "Historial de 30 días",
      "Alertas básicas"
    ],
    "price_monthly": "199.00",
    "price_annual": "1990.00",
    "currency": "MXN",
    "is_active": true
  },
  {
    "id": "uuid",
    "name": "Plan Profesional",
    "description": "Todas las características del Plan Básico más reportes avanzados",
    "features": [
      "Rastreo en tiempo real",
      "Historial ilimitado",
      "Alertas avanzadas",
      "Reportes personalizados",
      "Geocercas ilimitadas"
    ],
    "price_monthly": "299.00",
    "price_annual": "2990.00",
    "currency": "MXN",
    "is_active": true
  }
]
```

---

## 11. Órdenes (`/orders`)

Gestión de pedidos de hardware.

### 🔒 Todos requieren autenticación

#### `POST /api/v1/orders/`
**Crear nuevo pedido**

Crea un pedido de hardware con sus items.

**Headers:** `Authorization: Bearer {access_token}`

**Request:**
```json
{
  "items": [
    {
      "device_id": "IMEI123456789",
      "item_type": "hardware",
      "description": "GPS Teltonika FMB120",
      "quantity": 2,
      "unit_price": "1500.00"
    },
    {
      "device_id": null,
      "item_type": "accessory",
      "description": "Antena externa",
      "quantity": 2,
      "unit_price": "250.00"
    }
  ]
}
```

**Tipos de item:**
- `hardware`: Dispositivos GPS
- `accessory`: Accesorios (antenas, cables, etc.)
- `service`: Servicios adicionales
- `installation`: Servicio de instalación

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "client_id": "uuid",
  "total_amount": "3500.00",
  "currency": "MXN",
  "status": "PENDING",
  "payment_id": "uuid",
  "created_at": "2024-11-08T10:00:00Z",
  "order_items": [
    {
      "id": "uuid",
      "device_id": "IMEI123456789",
      "item_type": "hardware",
      "description": "GPS Teltonika FMB120",
      "quantity": 2,
      "unit_price": "1500.00",
      "total_price": "3000.00"
    },
    {
      "id": "uuid",
      "device_id": null,
      "item_type": "accessory",
      "description": "Antena externa",
      "quantity": 2,
      "unit_price": "250.00",
      "total_price": "500.00"
    }
  ]
}
```

**Nota:** Se crea automáticamente un `payment` en estado `PENDING`.

---

#### `GET /api/v1/orders/`
**Listar pedidos del cliente**

**Headers:** `Authorization: Bearer {access_token}`

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "client_id": "uuid",
    "total_amount": "3500.00",
    "currency": "MXN",
    "status": "COMPLETED",
    "payment_id": "uuid",
    "created_at": "2024-11-08T10:00:00Z",
    "updated_at": "2024-11-08T11:00:00Z"
  }
]
```

**Estados de orden:**
- `PENDING`: Pendiente de pago
- `PROCESSING`: En procesamiento
- `COMPLETED`: Completada
- `CANCELLED`: Cancelada

---

#### `GET /api/v1/orders/{order_id}`
**Obtener detalles de un pedido**

Incluye todos los items del pedido.

**Headers:** `Authorization: Bearer {access_token}`

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "client_id": "uuid",
  "total_amount": "3500.00",
  "currency": "MXN",
  "status": "COMPLETED",
  "payment_id": "uuid",
  "created_at": "2024-11-08T10:00:00Z",
  "order_items": [...]
}
```

---

## 12. Pagos (`/payments`)

Gestión de pagos del cliente.

### 🔒 Todos requieren autenticación

#### `GET /api/v1/payments/`
**Listar pagos del cliente**

**Headers:** `Authorization: Bearer {access_token}`

**Query Parameters (opcionales):**
- `status` (string): Filtrar por estado (PENDING, SUCCESS, FAILED, CANCELLED)

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "client_id": "uuid",
    "amount": "3500.00",
    "currency": "MXN",
    "status": "SUCCESS",
    "payment_method": "credit_card",
    "transaction_id": "TXN123456",
    "created_at": "2024-11-08T10:00:00Z",
    "updated_at": "2024-11-08T10:05:00Z"
  }
]
```

**Estados de pago:**
- `PENDING`: Pendiente de pago
- `SUCCESS`: Pagado exitosamente
- `FAILED`: Pago fallido
- `CANCELLED`: Cancelado

---

#### `GET /api/v1/payments/{payment_id}`
**Obtener detalles de un pago**

**Headers:** `Authorization: Bearer {access_token}`

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "client_id": "uuid",
  "amount": "3500.00",
  "currency": "MXN",
  "status": "SUCCESS",
  "payment_method": "credit_card",
  "transaction_id": "TXN123456",
  "payment_gateway": "stripe",
  "created_at": "2024-11-08T10:00:00Z",
  "updated_at": "2024-11-08T10:05:00Z"
}
```

---

## 🔄 Flujos de Negocio Principales

### Flujo 1: Onboarding de Nuevo Cliente

```mermaid
1. POST /clients/              → Registrar cliente
2. Email enviado               → Cliente verifica email
3. POST /clients/verify-email  → Activar cuenta
4. POST /auth/login            → Iniciar sesión
5. Cliente ahora puede usar la API
```

**Ejemplo práctico:**

```bash
# 1. Registrar cliente
curl -X POST http://localhost:8100/api/v1/clients/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mi Empresa S.A.",
    "email": "admin@miempresa.com",
    "password": "Password123!"
  }'

# 2. Cliente recibe email y hace clic en link
# 3. Frontend llama a verify-email con el token

# 4. Login
curl -X POST http://localhost:8100/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@miempresa.com",
    "password": "Password123!"
  }'
```

---

### Flujo 2: Agregar Dispositivo y Activar Servicio

```mermaid
1. POST /devices/              → Registrar dispositivo GPS
2. POST /units/                → Crear unidad/vehículo
3. POST /unit-devices/assign   → Instalar GPS en vehículo
4. GET  /plans/                → Ver planes disponibles
5. POST /services/activate     → Activar servicio de rastreo
6. Dispositivo ahora está rastreando
```

**Ejemplo práctico:**

```bash
# 1. Registrar dispositivo
curl -X POST http://localhost:8100/api/v1/devices/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "IMEI123456789",
    "brand": "Teltonika",
    "model": "FMB120",
    "firmware_version": "03.28.07"
  }'

# 2. Crear unidad
curl -X POST http://localhost:8100/api/v1/units/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Camioneta #01",
    "type": "vehiculo",
    "identifier": "ABC-123",
    "brand": "Toyota",
    "model": "Hilux"
  }'

# 3. Instalar GPS en vehículo
curl -X POST http://localhost:8100/api/v1/unit-devices/assign \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "unit_id": "{unit_uuid}",
    "device_id": "IMEI123456789"
  }'

# 4. Ver planes
curl -X GET http://localhost:8100/api/v1/plans/

# 5. Activar servicio
curl -X POST http://localhost:8100/api/v1/services/activate \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "IMEI123456789",
    "plan_id": "{plan_uuid}",
    "subscription_type": "monthly"
  }'
```

---

### Flujo 3: Invitar Usuario y Asignar Permisos

```mermaid
1. POST /users/invite           → Usuario maestro invita
2. Email enviado                → Nuevo usuario recibe invitación
3. POST /users/accept-invitation → Usuario acepta y crea cuenta
4. POST /user-units/assign      → Maestro asigna permisos sobre unidades
5. Usuario puede ver sus unidades asignadas
```

**Ejemplo práctico:**

```bash
# 1. Invitar usuario (como maestro)
curl -X POST http://localhost:8100/api/v1/users/invite \
  -H "Authorization: Bearer {token_maestro}" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "conductor@miempresa.com",
    "full_name": "Juan Pérez"
  }'

# 2. Usuario recibe email y hace clic en link
# 3. Frontend llama a accept-invitation

# 4. Asignar permisos sobre unidad
curl -X POST http://localhost:8100/api/v1/user-units/assign \
  -H "Authorization: Bearer {token_maestro}" \
  -H "Content-Type: application/json" \
  -d '{
    "unit_id": "{unit_uuid}",
    "user_id": "{user_uuid}",
    "role": "viewer"
  }'

# 5. Usuario puede listar sus unidades
curl -X GET http://localhost:8100/api/v1/units/ \
  -H "Authorization: Bearer {token_usuario}"
```

---

### Flujo 4: Compra de Hardware

```mermaid
1. POST /orders/                → Crear pedido de hardware
2. Se genera payment PENDING    → Cliente recibe info de pago
3. Cliente paga                 → (Integración con pasarela)
4. POST /payments/confirm       → Confirmar pago
5. Order cambia a COMPLETED     → Dispositivos listos para envío
```

---

## 🚨 Códigos de Error Comunes

### Errores de Autenticación

| Código | Descripción |
|--------|-------------|
| `401 Unauthorized` | Token inválido o expirado |
| `403 Forbidden` | Email no verificado o permisos insuficientes |
| `404 Not Found` | Usuario no encontrado |

### Errores de Validación

| Código | Descripción |
|--------|-------------|
| `400 Bad Request` | Datos inválidos en la petición |
| `422 Unprocessable Entity` | Error de validación de campos |

### Errores de Negocio

| Código | Descripción |
|--------|-------------|
| `409 Conflict` | Ya existe un recurso con esos datos |
| `404 Not Found` | Recurso no encontrado |
| `403 Forbidden` | Operación no permitida |

**Ejemplo de respuesta de error:**

```json
{
  "detail": "Ya existe un dispositivo con este device_id"
}
```

---

## 📊 Documentación Interactiva

### Swagger UI

Accede a la documentación interactiva de Swagger:

```
http://localhost:8100/docs
```

Características:
- ✅ Probar endpoints directamente desde el navegador
- ✅ Ver todos los modelos de datos
- ✅ Autenticación integrada
- ✅ Ejemplos de request/response

### ReDoc

Documentación alternativa más limpia:

```
http://localhost:8100/redoc
```

---

## 🔧 Testing y Desarrollo

### Health Check

```bash
GET /health

Response:
{
  "status": "healthy",
  "service": "siscom-admin-api"
}
```

### Variables de Entorno Requeridas

Ver [README.md](README.md) para la lista completa de variables de entorno.

**Mínimas requeridas:**

```env
# Base de datos
DB_HOST=localhost
DB_PORT=5432
DB_USER=siscom
DB_PASSWORD=changeme
DB_NAME=siscom_admin

# AWS Cognito
COGNITO_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxx
COGNITO_CLIENT_SECRET=xxxxxxxxxxxxxxxxxx

# AWS SES (Emails)
SES_FROM_EMAIL=noreply@tudominio.com
SES_REGION=us-east-1

# Frontend
FRONTEND_URL=https://app.tudominio.com
```

---

## 📞 Soporte y Contacto

### Recursos Adicionales

- **Guías técnicas**: Ver carpeta `/docs/guides/`
- **Documentación de endpoints específicos**: Ver carpeta `/docs/api/`
- **Configuración de emails**: [email-configuration.md](docs/guides/email-configuration.md)
- **Setup de GitHub Actions**: [github-actions-email-setup.md](docs/guides/github-actions-email-setup.md)

### Repositorio

```
https://github.com/tu-usuario/siscom-admin-api
```

---

## 📜 Changelog

### Version 1.0.0 (2024-11-08)

**Nuevas características:**
- ✅ Sistema completo de autenticación con AWS Cognito
- ✅ Gestión multi-tenant de clientes
- ✅ Sistema de invitaciones con emails
- ✅ Gestión de dispositivos GPS con auditoría
- ✅ Sistema de unidades con permisos granulares
- ✅ Activación de servicios de rastreo
- ✅ Gestión de órdenes y pagos
- ✅ Integración con AWS SES para emails
- ✅ Deployment automatizado con GitHub Actions

**Documentación:**
- ✅ API Documentation completa
- ✅ Guías de configuración
- ✅ Ejemplos de uso

---

## 🎓 Mejores Prácticas

### Para Desarrolladores Frontend

1. **Guardar tokens de manera segura**: Usar localStorage o sessionStorage
2. **Manejar expiración de tokens**: Implementar refresh automático
3. **Validar permisos en UI**: Ocultar opciones según `is_master` y roles
4. **Mostrar feedback claro**: Mensajes de error user-friendly
5. **Implementar loading states**: Durante llamadas a la API

### Para Integraciones

1. **Rate limiting**: Respetar límites de peticiones
2. **Reintentos**: Implementar exponential backoff
3. **Webhooks**: Considerar webhooks para eventos (próximamente)
4. **Paginación**: Implementar paginación para listas grandes
5. **Caché**: Cachear respuestas de catálogos (planes, etc.)

---

## 🔒 Seguridad

### Headers de Seguridad

La API implementa:
- CORS configurado correctamente
- Headers de seguridad estándar
- Rate limiting (próximamente)
- Validación de entrada exhaustiva

### Recomendaciones

1. **HTTPS en producción**: Siempre usar HTTPS
2. **Rotación de secrets**: Rotar secrets periódicamente
3. **Logs**: Monitorear logs de acceso
4. **Backups**: Realizar backups regulares de la base de datos

---

**Última actualización**: 2024-11-08  
**Versión de la API**: 1.0.0  
**Mantenido por**: SISCOM Team

---

## 🙏 Agradecimientos

Construido con:
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [AWS Cognito](https://aws.amazon.com/cognito/)
- [AWS SES](https://aws.amazon.com/ses/)
- [PostgreSQL](https://www.postgresql.org/)

---

**¿Tienes preguntas?** Consulta la documentación adicional en `/docs/` o contacta al equipo de desarrollo.

