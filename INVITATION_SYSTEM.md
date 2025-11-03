# Sistema de Invitaciones de Usuarios

Este documento describe la implementación del sistema de invitaciones para usuarios en el sistema SISCOM.

## Descripción General

El sistema permite que usuarios maestros (`is_master=True`) puedan invitar a otros usuarios a unirse a su organización (cliente). El proceso consta de dos pasos:

1. **Invitación**: Un usuario maestro envía una invitación por email
2. **Aceptación**: El usuario invitado acepta la invitación y crea su cuenta

## Endpoints Implementados

### 1. POST `/api/v1/users/invite`

Permite a un usuario maestro enviar una invitación a un nuevo usuario.

#### Autenticación
✅ Requiere autenticación (Bearer token)

#### Request Body
```json
{
  "email": "invitado@ejemplo.com",
  "full_name": "Juan Pérez"
}
```

#### Validaciones
- ✅ El usuario autenticado debe ser maestro (`is_master=True`)
- ✅ El email no debe estar ya registrado en la tabla `users`
- ✅ No debe existir una invitación pendiente (no usada y no expirada) para ese email

#### Response (201 Created)
```json
{
  "detail": "Invitación enviada a invitado@ejemplo.com",
  "expires_at": "2025-11-05T23:59:00"
}
```

#### Errores Comunes
- `403 Forbidden`: El usuario no es maestro
- `400 Bad Request`: Ya existe un usuario con ese email o una invitación pendiente

#### Proceso Interno
1. Verifica que el usuario autenticado sea maestro
2. Verifica que el email no esté registrado
3. Verifica que no exista una invitación pendiente
4. Genera un token único de invitación
5. Crea registro en `tokens_confirmacion` con:
   - `token`: Token aleatorio seguro
   - `client_id`: Del usuario maestro que invita
   - `email`: Del usuario invitado
   - `full_name`: Del usuario invitado
   - `expires_at`: Fecha actual + 3 días
   - `used`: False
   - `type`: `"invitation"`
6. **TODO**: Enviar email con URL de invitación
7. Responde con confirmación

---

### 2. POST `/api/v1/users/accept-invitation`

Permite a un usuario invitado aceptar la invitación y crear su cuenta.

#### Autenticación
❌ No requiere autenticación (el usuario aún no existe)

#### Request Body
```json
{
  "token": "abc123-def456-ghi789",
  "password": "MiPassword123!"
}
```

#### Validaciones del Token
- ✅ El token debe existir
- ✅ El token no debe estar usado (`used=False`)
- ✅ El token no debe estar expirado (`expires_at > now()`)
- ✅ El tipo debe ser `"invitation"`

#### Validaciones Adicionales
- ✅ El email del token no debe estar registrado (doble verificación)
- ✅ La contraseña debe cumplir los requisitos de seguridad

#### Response (201 Created)
```json
{
  "detail": "Usuario creado exitosamente.",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "client_id": "223e4567-e89b-12d3-a456-426614174000",
    "email": "invitado@ejemplo.com",
    "full_name": "Juan Pérez",
    "is_master": false,
    "email_verified": true,
    "cognito_sub": "us-east-1:12345678-1234-1234-1234-123456789012",
    "created_at": "2025-11-02T22:00:00Z",
    "updated_at": "2025-11-02T22:00:00Z"
  }
}
```

#### Errores Comunes
- `400 Bad Request`: Token inválido, usado o expirado
- `400 Bad Request`: El usuario ya existe
- `500 Internal Server Error`: Error al crear usuario en Cognito

#### Proceso Interno
1. Busca y valida el token de invitación
2. Extrae `email`, `full_name` y `client_id` del token
3. Verifica que el usuario no exista (doble validación)
4. Crea usuario en AWS Cognito:
   - Con `email_verified=true` (ya viene de invitación)
   - Con la contraseña proporcionada
   - Obtiene `cognito_sub`
5. Crea registro en tabla `users`:
   - `email`: Del token
   - `full_name`: Del token
   - `client_id`: Del token (mismo cliente del maestro)
   - `is_master`: False
   - `email_verified`: True
   - `cognito_sub`: De Cognito
6. Marca el token como usado (`used=True`)
7. Asocia el `user_id` creado al token
8. Responde con información del usuario creado

---

## Cambios en la Base de Datos

### Modelo `TokenConfirmacion`

Se agregaron campos para soportar invitaciones:

```python
class TokenConfirmacion(SQLModel, table=True):
    # ... campos existentes ...
    
    # Nuevos campos
    user_id: UUID | None  # Ahora es nullable
    email: str | None  # Email del invitado
    full_name: str | None  # Nombre del invitado
    client_id: UUID | None  # Cliente del maestro que invita
```

### Nuevo Tipo de Token

Se agregó el tipo `INVITATION` al enum `TokenType`:

```python
class TokenType(str, enum.Enum):
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    INVITATION = "invitation"  # ← Nuevo
```

### Migración de Base de Datos

Se creó la migración `003_add_invitation_fields_to_tokens.py` que:

1. Hace `user_id` nullable
2. Agrega columna `email`
3. Agrega columna `full_name`
4. Agrega columna `client_id` con FK a `clients`
5. Crea índice en `client_id`

**Para aplicar la migración:**
```bash
alembic upgrade head
```

---

## Schemas Agregados

### `UserInvite`
Request para invitar usuario:
```python
{
    "email": EmailStr,
    "full_name": str
}
```

### `UserInviteResponse`
Respuesta de invitación:
```python
{
    "detail": str,
    "expires_at": datetime
}
```

### `UserAcceptInvitation`
Request para aceptar invitación:
```python
{
    "token": str,
    "password": str
}
```

### `UserAcceptInvitationResponse`
Respuesta de aceptación:
```python
{
    "detail": str,
    "user": UserOut
}
```

---

## Flujo de Uso Completo

### 1. Usuario Maestro Invita
```bash
curl -X POST "http://localhost:8000/api/v1/users/invite" \
  -H "Authorization: Bearer {token_maestro}" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "nuevo@ejemplo.com",
    "full_name": "Nuevo Usuario"
  }'
```

**Respuesta:**
```json
{
  "detail": "Invitación enviada a nuevo@ejemplo.com",
  "expires_at": "2025-11-05T23:59:00"
}
```

### 2. Invitado Recibe Email con Token
El email debe contener un enlace como:
```
https://tu-app.com/accept-invitation?token={token_generado}
```

### 3. Invitado Acepta Invitación
```bash
curl -X POST "http://localhost:8000/api/v1/users/accept-invitation" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "abc123-def456-ghi789",
    "password": "MiPassword123!"
  }'
```

**Respuesta:**
```json
{
  "detail": "Usuario creado exitosamente.",
  "user": {
    "id": "...",
    "email": "nuevo@ejemplo.com",
    "full_name": "Nuevo Usuario",
    "is_master": false,
    "email_verified": true,
    "client_id": "...",
    "created_at": "2025-11-02T22:00:00Z",
    "updated_at": "2025-11-02T22:00:00Z"
  }
}
```

### 4. Usuario Ya Puede Iniciar Sesión
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "nuevo@ejemplo.com",
    "password": "MiPassword123!"
  }'
```

---

## Seguridad y Validaciones

### Tokens de Invitación
- ✅ Generados con `secrets.token_urlsafe(32)` (seguros)
- ✅ Únicos en la base de datos
- ✅ Expiran en 3 días
- ✅ Solo pueden usarse una vez
- ✅ Índice en columna `token` para búsquedas rápidas

### Permisos
- ✅ Solo usuarios maestros pueden invitar
- ✅ Los invitados siempre se crean como no-maestros
- ✅ Los invitados heredan el `client_id` del maestro

### Validaciones de Email
- ✅ Formato válido (EmailStr)
- ✅ No duplicados en tabla `users`
- ✅ No invitaciones pendientes duplicadas

### Contraseñas
- ✅ Mínimo 8 caracteres
- ✅ Validadas con `validate_password()`
- ✅ Almacenadas seguramente en Cognito

---

## Tareas Pendientes (TODO)

1. **Envío de Email de Invitación**
   - Implementar función `send_invitation_email()`
   - Integrar con servicio de email (SES, SendGrid, etc.)
   - Diseñar template del email
   - Incluir URL de aceptación con token

2. **Mejoras Opcionales**
   - Resend invitation (reenviar invitación)
   - Cancel invitation (cancelar invitación)
   - List pending invitations (listar invitaciones pendientes)
   - Email de bienvenida al aceptar invitación

---

## Archivos Modificados

1. **Modelos**
   - `app/models/token_confirmacion.py` - Campos de invitación

2. **Schemas**
   - `app/schemas/user.py` - Schemas de invitación

3. **Endpoints**
   - `app/api/v1/endpoints/users.py` - Endpoints `/invite` y `/accept-invitation`

4. **Migraciones**
   - `app/db/migrations/versions/003_add_invitation_fields_to_tokens.py`

---

## Testing

Para probar los endpoints, puedes usar los ejemplos de curl arriba o importar esta colección en Postman/Insomnia.

**Nota**: Recuerda aplicar la migración antes de probar:
```bash
alembic upgrade head
```

