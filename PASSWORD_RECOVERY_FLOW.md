# Sistema de Recuperación de Contraseña

## Descripción General

Este documento describe el sistema de recuperación de contraseña implementado en la API. El sistema permite a los usuarios que olvidaron su contraseña solicitar un restablecimiento sin necesidad de estar autenticados.

## Características Principales

- ✅ No usa `forgot_password` de Cognito
- ✅ Genera tokens únicos (UUID) gestionados por nosotros
- ✅ Almacena tokens en la tabla `tokens_confirmacion` con tipo `PASSWORD_RESET`
- ✅ Tokens con expiración de 1 hora
- ✅ Usa `AdminSetUserPassword` de Cognito para aplicar la nueva contraseña
- ⏳ Envío de correo (pendiente de implementar servicio de notificaciones)

## Flujo de Recuperación de Contraseña

### 1. Solicitud de Recuperación (`POST /api/v1/auth/forgot-password`)

**Endpoint:** `POST /api/v1/auth/forgot-password`

**Request:**
```json
{
  "email": "usuario@example.com"
}
```

**Response:** `200 OK`
```json
{
  "message": "Se ha enviado un código de verificación al correo registrado."
}
```

**Proceso interno:**

1. **Validación del usuario:**
   - Busca el usuario en la base de datos por email
   - Si no existe, registra el intento en logs pero retorna el mismo mensaje de éxito (seguridad)

2. **Generación del token:**
   - Genera un UUID único
   - Guarda el token en `tokens_confirmacion`:
     - `type`: `PASSWORD_RESET`
     - `user_id`: ID del usuario
     - `email`: Email del usuario
     - `expires_at`: Fecha de expiración (1 hora desde la creación)
     - `used`: `false`

3. **TODO - Envío del correo:**
   - Actualmente solo registra en logs
   - Cuando se implemente el servicio de notificaciones, enviará un correo con:
     - Token de recuperación
     - Link directo a la página de restablecimiento
     - Instrucciones para el usuario
     - Tiempo de expiración

4. **Respuesta:**
   - Siempre retorna el mismo mensaje de éxito
   - No revela si el email existe o no (medida de seguridad)

**Notas de Seguridad:**
- El endpoint siempre retorna el mismo mensaje, independientemente de si el usuario existe
- Esto previene la enumeración de usuarios válidos en el sistema
- Los intentos con emails no registrados se registran en logs para monitoreo

---

### 2. Restablecimiento de Contraseña (`POST /api/v1/auth/reset-password`)

**Endpoint:** `POST /api/v1/auth/reset-password`

**Request:**
```json
{
  "token": "abc123-def456-ghi789",
  "new_password": "NuevaPassword123!"
}
```

**Response:** `200 OK`
```json
{
  "message": "Contraseña restablecida exitosamente. Ahora puede iniciar sesión con su nueva contraseña."
}
```

**Proceso interno:**

1. **Validación del token:**
   - Busca el token en `tokens_confirmacion`
   - Verifica que el tipo sea `PASSWORD_RESET`
   - Si no existe, retorna error `400 Bad Request`

2. **Verificación de expiración:**
   - Compara `expires_at` con la fecha/hora actual
   - Si expiró, retorna error `400 Bad Request` con mensaje indicando que solicite uno nuevo

3. **Verificación de uso:**
   - Verifica que `used` sea `false`
   - Si ya fue usado, retorna error `400 Bad Request`

4. **Validación del usuario:**
   - Busca el usuario asociado por `user_id`
   - Si no existe, retorna error `404 Not Found`

5. **Actualización de contraseña en Cognito:**
   - Llama a `admin_set_user_password` de AWS Cognito
   - Parámetros:
     - `UserPoolId`: ID del User Pool
     - `Username`: Email del usuario
     - `Password`: Nueva contraseña
     - `Permanent`: `True` (la contraseña no es temporal)
   - Maneja errores específicos de Cognito:
     - `UserNotFoundException`: Usuario no encontrado en Cognito
     - `InvalidPasswordException`: Contraseña no cumple con los requisitos
     - `InvalidParameterException`: Parámetros inválidos

6. **Marcado del token como usado:**
   - Actualiza `used = true` en el registro del token
   - Previene la reutilización del mismo token

7. **Respuesta:**
   - Retorna mensaje de éxito indicando que puede iniciar sesión

**Códigos de Error:**

- `400 Bad Request`:
  - Token inválido
  - Token expirado
  - Token ya usado
  - Contraseña inválida

- `404 Not Found`:
  - Usuario no encontrado en la base de datos
  - Usuario no encontrado en Cognito

- `500 Internal Server Error`:
  - Error al actualizar la contraseña en Cognito

---

### 3. Login Normal (`POST /api/v1/auth/login`)

Después de restablecer la contraseña, el usuario puede autenticarse normalmente:

**Endpoint:** `POST /api/v1/auth/login`

**Request:**
```json
{
  "email": "usuario@example.com",
  "password": "NuevaPassword123!"
}
```

**Response:** `200 OK`
```json
{
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "usuario@example.com",
    "full_name": "Juan García",
    "is_master": true,
    "email_verified": true,
    "last_login_at": "2025-11-04T10:30:00Z"
  },
  "access_token": "eyJraWQiOiJ...",
  "id_token": "eyJraWQiOiJ...",
  "refresh_token": "eyJjdHkiOiJ...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

## Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────────┐
│                    USUARIO OLVIDA CONTRASEÑA                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. POST /api/v1/auth/forgot-password                           │
│     { "email": "usuario@example.com" }                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  API valida usuario y genera token UUID                         │
│  - Guarda en tokens_confirmacion                                │
│  - TODO: Envía correo con token                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Responde: "Se ha enviado un código de verificación..."         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  USUARIO RECIBE EMAIL CON TOKEN (cuando esté implementado)      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. POST /api/v1/auth/reset-password                            │
│     {                                                            │
│       "token": "abc123-...",                                    │
│       "new_password": "NuevaPassword123!"                       │
│     }                                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  API valida token y actualiza contraseña                        │
│  - Verifica token válido, no usado, no expirado                 │
│  - Llama a AdminSetUserPassword en Cognito                      │
│  - Marca token como usado                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Responde: "Contraseña restablecida exitosamente..."            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. POST /api/v1/auth/login                                     │
│     {                                                            │
│       "email": "usuario@example.com",                           │
│       "password": "NuevaPassword123!"                           │
│     }                                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Usuario autenticado exitosamente ✓                             │
└─────────────────────────────────────────────────────────────────┘
```

## Modelo de Datos

### Tabla: `tokens_confirmacion`

Los tokens de recuperación de contraseña se almacenan con los siguientes campos:

```python
{
    "id": UUID,                    # ID único del registro
    "token": str,                  # Token UUID generado
    "type": "PASSWORD_RESET",      # Tipo de token
    "user_id": UUID,               # ID del usuario
    "email": str,                  # Email del usuario
    "expires_at": datetime,        # Fecha de expiración (1 hora)
    "used": bool,                  # Si el token ya fue usado
    "created_at": datetime         # Fecha de creación
}
```

## Validaciones de Contraseña

La nueva contraseña debe cumplir con los siguientes requisitos (definidos en `app/utils/validators.py`):

- Mínimo 8 caracteres
- Al menos una letra mayúscula
- Al menos una letra minúscula
- Al menos un número
- Al menos un carácter especial (!@#$%^&*(),.?":{}|<>)

## Seguridad

### Medidas Implementadas:

1. **Respuesta consistente:** El endpoint `forgot-password` siempre retorna el mismo mensaje, sin revelar si el email existe

2. **Tokens únicos:** Cada token es un UUID único, imposible de adivinar

3. **Expiración:** Los tokens expiran en 1 hora

4. **Uso único:** Los tokens solo pueden usarse una vez

5. **Validación robusta:** Se verifica token, expiración, uso previo y usuario asociado

6. **Logs de auditoría:** Se registran todos los intentos para monitoreo

### Recomendaciones de Seguridad:

1. **Rate Limiting:** Implementar límite de solicitudes por IP/usuario para prevenir ataques de fuerza bruta

2. **Notificaciones:** Cuando se implemente el servicio de correo, notificar al usuario cuando se solicite recuperación

3. **HTTPS:** Asegurar que todos los endpoints se usen exclusivamente sobre HTTPS

4. **Monitoreo:** Revisar logs regularmente para detectar patrones sospechosos

## Pendientes (TODO)

1. **Servicio de Notificaciones:**
   - Implementar servicio de envío de correos
   - Crear plantilla HTML para el correo de recuperación
   - Incluir el token o un link directo

2. **Mejoras Opcionales:**
   - Rate limiting en los endpoints
   - Notificación adicional cuando la contraseña cambia
   - Interfaz web para el reset de contraseña
   - Historial de cambios de contraseña

## Pruebas

### Flujo Completo:

```bash
# 1. Solicitar recuperación
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@example.com"}'

# Respuesta:
# {
#   "message": "Se ha enviado un código de verificación al correo registrado."
# }

# 2. Obtener el token de los logs o base de datos
# (En producción, el usuario lo recibirá por email)

# 3. Restablecer contraseña
curl -X POST http://localhost:8000/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "abc123-def456-ghi789",
    "new_password": "NuevaPassword123!"
  }'

# Respuesta:
# {
#   "message": "Contraseña restablecida exitosamente. Ahora puede iniciar sesión con su nueva contraseña."
# }

# 4. Iniciar sesión con la nueva contraseña
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@example.com",
    "password": "NuevaPassword123!"
  }'

# Respuesta: Tokens de autenticación
```

## Relación con Otros Sistemas

### Sistema de Invitaciones

El sistema de recuperación de contraseña comparte la tabla `tokens_confirmacion` con el sistema de invitaciones, pero usa un tipo diferente:

- **Invitaciones:** `TokenType.INVITATION`
- **Recuperación de contraseña:** `TokenType.PASSWORD_RESET`

### AWS Cognito

La contraseña se actualiza directamente en Cognito usando `AdminSetUserPassword`, lo que permite:

- Establecer la contraseña como permanente
- Evitar el challenge de cambio de contraseña
- Permitir login inmediato después del reset

## Conclusión

El sistema de recuperación de contraseña está implementado y funcional. La única parte pendiente es el envío de correos, que se dejó marcada como TODO para implementar cuando esté listo el servicio de notificaciones.

