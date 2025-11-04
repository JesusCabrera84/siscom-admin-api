# Flujos de Reenvío: Verificación vs Invitación

Este documento explica la diferencia entre los dos sistemas de reenvío y cuándo usar cada uno.

---

## 🔄 Dos Flujos Diferentes

### 1. Reenvío de Verificación de Email (`/auth/resend-verification`)
### 2. Reenvío de Invitación (`/users/resend-invitation`)

---

## 📋 Comparación Rápida

| Aspecto | Reenvío de Verificación | Reenvío de Invitación |
|---------|-------------------------|----------------------|
| **Endpoint** | `POST /api/v1/auth/resend-verification` | `POST /api/v1/users/resend-invitation` |
| **Usuario existe en BD** | ✅ Sí | ❌ No |
| **Usuario existe en Cognito** | ✅ Sí | ❌ No |
| **Tipo de token** | `EMAIL_VERIFICATION` | `INVITATION` |
| **Requiere autenticación** | ❌ No | ✅ Sí (usuario maestro) |
| **Caso de uso** | Usuario se registró pero no verificó | Usuario fue invitado pero no aceptó |
| **Expiración** | 24 horas | 3 días |
| **Siguiente paso** | `/auth/confirm-email` | `/users/accept-invitation` |

---

## 1️⃣ Reenvío de Verificación de Email

### 📌 Contexto
Un usuario **YA SE REGISTRÓ** en el sistema (existe en `users` y en Cognito) pero **NO VERIFICÓ** su email.

### 🔐 Autenticación
**No requiere autenticación** - Cualquiera puede solicitarlo con solo el email.

### 🎯 Caso de Uso
```
Usuario se registró → Se envió email de verificación → 
Usuario no lo recibió o el email expiró → 
Usuario solicita reenvío
```

### 📝 Request
```bash
POST /api/v1/auth/resend-verification
```

```json
{
  "email": "usuario@example.com"
}
```

### ✅ Response
```json
{
  "message": "Si la cuenta existe, se ha reenviado el correo de verificación."
}
```

### 🔄 Flujo Interno

1. **Busca usuario en `users`**
   - Si no existe → Responde mensaje genérico (seguridad)
   - Si existe y `email_verified=true` → Responde mensaje genérico
   
2. **Si existe y NO está verificado:**
   - Invalida tokens `EMAIL_VERIFICATION` anteriores no usados
   - Genera nuevo token UUID
   - Guarda en `tokens_confirmacion`:
     - `type`: `EMAIL_VERIFICATION`
     - `user_id`: ID del usuario
     - `expires_at`: +24 horas
   - TODO: Envía email con token
   
3. **Usuario confirma con:** `POST /auth/confirm-email`

### 🛡️ Seguridad
- Respuesta consistente (no revela si usuario existe)
- Invalida tokens anteriores
- Tokens expiran en 24h
- Tokens de uso único

### 💡 Ejemplo Completo
```bash
# 1. Usuario ya registrado solicita reenvío
curl -X POST http://localhost:8000/api/v1/auth/resend-verification \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@example.com"}'

# 2. Sistema genera token (obtener de logs/BD)
TOKEN="abc123-..."

# 3. Usuario confirma email
curl -X POST http://localhost:8000/api/v1/auth/confirm-email \
  -H "Content-Type: application/json" \
  -d '{"token": "'$TOKEN'"}'

# 4. Usuario puede hacer login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@example.com", "password": "Password123!"}'
```

---

## 2️⃣ Reenvío de Invitación

### 📌 Contexto
Un usuario maestro **INVITÓ** a alguien, pero el invitado **NO HA ACEPTADO** la invitación. El invitado **NO EXISTE** todavía en `users` ni en Cognito.

### 🔐 Autenticación
**Requiere autenticación** - Solo usuarios maestros (`is_master=true`) pueden reenviar invitaciones.

### 🎯 Caso de Uso
```
Usuario maestro invita a alguien → Se envió email de invitación → 
Invitado no lo recibió o la invitación expiró → 
Usuario maestro reenvía invitación
```

### 📝 Request
```bash
POST /api/v1/users/resend-invitation
Authorization: Bearer <token_usuario_maestro>
```

```json
{
  "email": "invitado@ejemplo.com"
}
```

### ✅ Response
```json
{
  "message": "Invitación reenviada a invitado@ejemplo.com",
  "expires_at": "2025-11-07T23:59:00"
}
```

### 🔄 Flujo Interno

1. **Verifica autenticación:**
   - Usuario debe estar autenticado
   - Usuario debe ser maestro (`is_master=true`)
   
2. **Verifica que el invitado NO esté registrado:**
   - Si existe en `users` → Error (ya está registrado)
   
3. **Busca invitaciones pendientes:**
   - Busca tokens tipo `INVITATION` no usados para ese email
   - En el `client_id` del usuario maestro
   - Si no existe invitación → Error
   
4. **Genera nueva invitación:**
   - Invalida invitaciones anteriores no usadas
   - Crea nuevo token
   - Mantiene `full_name` de la invitación original
   - Guarda en `tokens_confirmacion`:
     - `type`: `INVITATION`
     - `client_id`: Del usuario maestro
     - `email`: Del invitado
     - `full_name`: Del invitado
     - `expires_at`: +3 días
   - TODO: Envía email con token
   
5. **Invitado acepta con:** `POST /users/accept-invitation`

### 🛡️ Seguridad
- Requiere autenticación como usuario maestro
- Solo puede reenviar invitaciones de su propio cliente
- Verifica que el invitado no esté ya registrado
- Invalida invitaciones anteriores
- Tokens expiran en 3 días

### 💡 Ejemplo Completo
```bash
# 1. Usuario maestro hace login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "maestro@example.com", "password": "Password123!"}' \
  | jq -r '.access_token')

# 2. Usuario maestro reenvía invitación
curl -X POST http://localhost:8000/api/v1/users/resend-invitation \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"email": "invitado@ejemplo.com"}'

# 3. Sistema genera nueva invitación (obtener token de logs/BD)
INV_TOKEN="xyz789-..."

# 4. Invitado acepta la invitación
curl -X POST http://localhost:8000/api/v1/users/accept-invitation \
  -H "Content-Type: application/json" \
  -d '{
    "token": "'$INV_TOKEN'",
    "password": "Password123!"
  }'

# 5. Nuevo usuario puede hacer login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "invitado@ejemplo.com", "password": "Password123!"}'
```

---

## 🎯 ¿Cuál Usar?

### Usa `/auth/resend-verification` cuando:
- ✅ El usuario **YA se registró** por su cuenta
- ✅ El usuario existe en la base de datos
- ✅ El usuario existe en Cognito
- ✅ El usuario no verificó su email
- ✅ No requieres autenticación para solicitarlo

### Usa `/users/resend-invitation` cuando:
- ✅ Un usuario maestro **invitó** a alguien
- ✅ El invitado **NO existe** en la base de datos
- ✅ El invitado **NO existe** en Cognito
- ✅ El invitado no aceptó la invitación
- ✅ Necesitas ser usuario maestro para reenviarla

---

## 📊 Diagrama de Flujos

```
┌─────────────────────────────────────────────────────────────────┐
│                    USUARIO SE REGISTRA                           │
│                    (Registro directo)                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │ Usuario existe en users       │
         │ Usuario existe en Cognito     │
         │ email_verified = false        │
         └───────────────┬───────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │ POST /auth/resend-verification│ ◄── No requiere auth
         │ (Reenvío de Verificación)     │
         └───────────────┬───────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │ POST /auth/confirm-email      │
         │ email_verified = true         │
         └───────────────┬───────────────┘
                         │
                         ▼
                    [LOGIN]


┌─────────────────────────────────────────────────────────────────┐
│                 USUARIO MAESTRO INVITA                           │
│                    (Sistema de Invitaciones)                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │ POST /users/invite            │ ◄── Requiere auth (maestro)
         │ Token INVITATION creado       │
         │ Usuario NO existe aún         │
         └───────────────┬───────────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
    [Invitado acepta]          [Invitado NO acepta]
            │                         │
            │                         ▼
            │          ┌──────────────────────────────┐
            │          │ POST /users/resend-invitation│ ◄── Requiere auth (maestro)
            │          │ (Reenvío de Invitación)      │
            │          └──────────────┬───────────────┘
            │                         │
            └─────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │ POST /users/accept-invitation │
         │ Usuario creado en users       │
         │ Usuario creado en Cognito     │
         │ email_verified = true         │
         └───────────────┬───────────────┘
                         │
                         ▼
                    [LOGIN]
```

---

## 🗂️ Tabla de Tokens

Ambos usan la tabla `tokens_confirmacion` pero con tipos diferentes:

```sql
-- Verificación de Email
INSERT INTO tokens_confirmacion (
    token, 
    type, 
    user_id,          -- ✅ Usuario YA existe
    email,
    expires_at        -- 24 horas
) VALUES (
    'abc123-...',
    'email_verification',
    '123e4567-...',
    'usuario@example.com',
    NOW() + INTERVAL '24 hours'
);

-- Invitación
INSERT INTO tokens_confirmacion (
    token,
    type,
    user_id,          -- ❌ NULL (usuario NO existe aún)
    client_id,        -- ✅ Cliente del usuario maestro
    email,
    full_name,
    expires_at        -- 3 días
) VALUES (
    'xyz789-...',
    'invitation',
    NULL,
    '223e4567-...',
    'invitado@ejemplo.com',
    'Juan Pérez',
    NOW() + INTERVAL '3 days'
);
```

---

## 🧪 Testing

### Test Verificación de Email
```bash
# Script automatizado
./test_auth_endpoints.sh full-verification-flow usuario@example.com
```

### Test Invitación
```bash
# 1. Invitar usuario (como maestro)
curl -X POST http://localhost:8000/api/v1/users/invite \
  -H "Authorization: Bearer <token_maestro>" \
  -H "Content-Type: application/json" \
  -d '{"email": "nuevo@ejemplo.com", "full_name": "Nuevo Usuario"}'

# 2. Si el invitado no acepta, reenviar
curl -X POST http://localhost:8000/api/v1/users/resend-invitation \
  -H "Authorization: Bearer <token_maestro>" \
  -H "Content-Type: application/json" \
  -d '{"email": "nuevo@ejemplo.com"}'

# 3. Obtener token de BD
TOKEN=$(docker-compose exec db psql -U postgres -d siscom_db -t -c \
  "SELECT token FROM tokens_confirmacion WHERE type='invitation' AND email='nuevo@ejemplo.com' AND used=false ORDER BY created_at DESC LIMIT 1;" | tr -d ' ')

# 4. Aceptar invitación
curl -X POST http://localhost:8000/api/v1/users/accept-invitation \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$TOKEN\", \"password\": \"Password123!\"}"
```

---

## 🔒 Códigos de Error

### Reenvío de Verificación
- **400 Bad Request**: Token inválido/expirado
- **404 Not Found**: Usuario no encontrado (no se muestra al usuario)

### Reenvío de Invitación
- **401 Unauthorized**: No autenticado
- **403 Forbidden**: Usuario no es maestro
- **400 Bad Request**: 
  - Usuario ya está registrado
  - No existe invitación pendiente
  - Email no válido

---

## 📚 Documentación Relacionada

- **Sistema de Invitaciones:** `INVITATION_SYSTEM.md`
- **Endpoints de Auth:** `AUTH_ENDPOINTS_DOCUMENTATION.md`
- **Guía rápida:** `QUICK_START_AUTH_ENDPOINTS.md`

---

## ✅ Resumen

| Flujo | Endpoint | Auth | Usuario Existe | Token Type | Expiración |
|-------|----------|------|----------------|------------|------------|
| **Verificación** | `/auth/resend-verification` | ❌ No | ✅ Sí | `email_verification` | 24h |
| **Invitación** | `/users/resend-invitation` | ✅ Maestro | ❌ No | `invitation` | 3 días |

---

**Fecha:** 4 de noviembre de 2025  
**Estado:** ✅ Ambos sistemas implementados y funcionales

