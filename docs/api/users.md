# API de Usuarios

## Descripción

Endpoints para gestionar usuarios dentro de un cliente (organización). Incluye funcionalidad de invitaciones para que usuarios maestros puedan agregar nuevos usuarios.

---

## Endpoints

### 1. Listar Usuarios

**GET** `/api/v1/users/`

Lista todos los usuarios del cliente autenticado.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "client_id": "456e4567-e89b-12d3-a456-426614174000",
    "email": "usuario@ejemplo.com",
    "full_name": "Juan Pérez",
    "is_master": true,
    "email_verified": true,
    "cognito_sub": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### 2. Obtener Usuario Actual

**GET** `/api/v1/users/me`

Obtiene la información del usuario actualmente autenticado.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "client_id": "456e4567-e89b-12d3-a456-426614174000",
  "email": "usuario@ejemplo.com",
  "full_name": "Juan Pérez",
  "is_master": true,
  "email_verified": true,
  "cognito_sub": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### 3. Invitar Usuario

**POST** `/api/v1/users/invite`

Permite a un usuario maestro enviar una invitación a un nuevo usuario para que se una al cliente.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "email": "invitado@ejemplo.com",
  "full_name": "María García"
}
```

#### Validaciones

- El usuario autenticado debe ser maestro (`is_master=True`)
- El email no debe estar ya registrado
- No debe existir una invitación pendiente para ese email

#### Response 201 Created

```json
{
  "message": "Invitación enviada exitosamente.",
  "email": "invitado@ejemplo.com",
  "expires_at": "2025-01-22T10:30:00Z"
}
```

#### Errores Comunes

- **403 Forbidden**: El usuario no es maestro
- **400 Bad Request**: Ya existe un usuario con ese email
- **400 Bad Request**: Ya existe una invitación pendiente

---

### 4. Aceptar Invitación

**POST** `/api/v1/users/accept-invitation`

Permite a un usuario invitado aceptar la invitación y crear su cuenta.

#### Request Body

```json
{
  "token": "abc123def456...",
  "password": "MiPassword123!"
}
```

#### Validaciones

- El token debe ser válido y no estar expirado
- El token no debe haber sido usado previamente
- La contraseña debe cumplir los requisitos de seguridad

#### Response 201 Created

```json
{
  "message": "Invitación aceptada exitosamente. Ya puedes iniciar sesión.",
  "email": "invitado@ejemplo.com",
  "user_id": "789e4567-e89b-12d3-a456-426614174000"
}
```

#### Proceso Interno

1. Valida el token de invitación
2. Crea el usuario en AWS Cognito con estado `CONFIRMED`
3. Actualiza el registro del usuario en la base de datos
4. Marca el token como usado
5. Envía email de bienvenida (opcional)

---

### 5. Reenviar Invitación

**POST** `/api/v1/users/resend-invitation`

Reenvía una invitación a un email que tiene una invitación pendiente.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "email": "invitado@ejemplo.com"
}
```

#### Validaciones

- El usuario autenticado debe ser maestro
- Debe existir una invitación pendiente para ese email
- La invitación puede estar expirada (se renovará)

#### Response 200 OK

```json
{
  "message": "Invitación reenviada exitosamente.",
  "email": "invitado@ejemplo.com",
  "new_expires_at": "2025-01-22T15:45:00Z"
}
```

---

## Roles de Usuario

### Usuario Maestro (`is_master=True`)

- Primer usuario creado al registrar un cliente
- Puede invitar a otros usuarios
- Puede reenviar invitaciones
- Tiene permisos completos sobre el cliente

### Usuario Regular (`is_master=False`)

- Usuario invitado por un maestro
- Puede gestionar dispositivos, servicios, órdenes
- No puede invitar a otros usuarios
- Comparte acceso a los datos del cliente

---

## Flujo de Invitación Completo

### 1. Envío de Invitación

```
Usuario Maestro → POST /api/v1/users/invite
                ↓
          Token generado
                ↓
          Email enviado con URL: https://app.ejemplo.com/accept-invitation?token=abc123...
```

### 2. Aceptación de Invitación

```
Usuario Invitado → Hace clic en el link del email
                 ↓
          Frontend muestra formulario de contraseña
                 ↓
          POST /api/v1/users/accept-invitation
                 ↓
          Usuario creado en Cognito y BD
                 ↓
          Usuario puede hacer login
```

### 3. Invitación Expirada

```
Usuario Maestro → POST /api/v1/users/resend-invitation
                ↓
          Token renovado (7 días más)
                ↓
          Nuevo email enviado
```

---

## Notas Importantes

### Expiración de Tokens

- Las invitaciones expiran en 7 días por defecto
- Los tokens usados no pueden reutilizarse
- Una invitación puede reenviarse múltiples veces

### Multi-tenant

- Cada usuario pertenece a un único cliente
- Los usuarios solo ven datos de su propio cliente
- El `client_id` se extrae automáticamente del token JWT

### Seguridad

- Solo usuarios maestros pueden invitar
- Las invitaciones no pueden modificar el `client_id`
- Los tokens son UUID únicos y no predecibles

