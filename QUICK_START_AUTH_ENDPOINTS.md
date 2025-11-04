# 🚀 Quick Start - Nuevos Endpoints de Autenticación

Guía rápida para usar los nuevos endpoints de autenticación.

---

## ⚡ 1. Cambiar Contraseña (Usuario Autenticado)

### Comando rápido:
```bash
./test_auth_endpoints.sh change-password usuario@example.com OldPwd123! NewPwd456!
```

### Manual con cURL:
```bash
# 1. Login (obtener token)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@example.com", "password": "OldPwd123!"}' \
  | jq -r '.access_token')

# 2. Cambiar contraseña
curl -X PATCH http://localhost:8000/api/v1/auth/password \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "old_password": "OldPwd123!",
    "new_password": "NewPwd456!"
  }'
```

**Respuesta esperada:**
```json
{
  "message": "Contraseña actualizada exitosamente."
}
```

---

## ⚡ 2. Reenviar Verificación de Email

### Comando rápido:
```bash
./test_auth_endpoints.sh resend-verification usuario@example.com
```

### Manual con cURL:
```bash
curl -X POST http://localhost:8000/api/v1/auth/resend-verification \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@example.com"}'
```

**Respuesta esperada:**
```json
{
  "message": "Si la cuenta existe, se ha reenviado el correo de verificación."
}
```

**Obtener token:**
```bash
# Desde logs
docker-compose logs api | grep "RESEND VERIFICATION"

# Desde BD
docker-compose exec db psql -U postgres -d siscom_db -c \
  "SELECT token FROM tokens_confirmacion 
   WHERE type='email_verification' AND used=false 
   ORDER BY created_at DESC LIMIT 1;"
```

---

## ⚡ 3. Confirmar Email

### Comando rápido:
```bash
./test_auth_endpoints.sh confirm-email TOKEN_AQUI
```

### Manual con cURL:
```bash
curl -X POST http://localhost:8000/api/v1/auth/confirm-email \
  -H "Content-Type: application/json" \
  -d '{"token": "abc123-def456-ghi789"}'
```

**Respuesta esperada:**
```json
{
  "message": "Email verificado exitosamente. Ahora puede iniciar sesión."
}
```

---

## ⚡ 4. Flujo Completo de Verificación

### Comando automatizado:
```bash
./test_auth_endpoints.sh full-verification-flow usuario@example.com
```

Este comando ejecuta automáticamente:
1. ✅ Reenvía verificación
2. ✅ Obtiene token de BD
3. ✅ Confirma email con token

---

## 📋 Resumen de Endpoints

| Endpoint | Método | Auth | Uso |
|----------|--------|------|-----|
| `/auth/password` | PATCH | ✅ Sí | Cambiar contraseña |
| `/auth/resend-verification` | POST | ❌ No | Reenviar verificación |
| `/auth/confirm-email` | POST | ❌ No | Confirmar email |

---

## ✅ Validación de Contraseñas

Nueva contraseña debe tener:
- ✅ Mínimo 8 caracteres
- ✅ Una mayúscula
- ✅ Una minúscula
- ✅ Un número
- ✅ Un carácter especial

**Ejemplos válidos:**
- `Password123!`
- `MiClave99#`
- `NuevoPwd2025!`

---

## 🔍 Solución Rápida de Problemas

| Error | Solución |
|-------|----------|
| "La contraseña actual es incorrecta" | Verificar contraseña actual |
| "Token de verificación inválido" | Obtener nuevo token de BD |
| "Token ha expirado" | Solicitar nuevo con resend-verification |
| "Token ya utilizado" | Solicitar nuevo con resend-verification |
| "Invalid token" (401) | Login nuevamente para obtener nuevo access_token |

---

## 🧪 Script de Prueba

Ver todos los comandos disponibles:
```bash
./test_auth_endpoints.sh help
```

**Comandos disponibles:**
- `change-password` - Cambiar contraseña
- `resend-verification` - Reenviar verificación
- `confirm-email` - Confirmar email
- `full-verification-flow` - Flujo completo automatizado

---

## 📚 Documentación Completa

Para más detalles:
- **Guía técnica:** `AUTH_ENDPOINTS_DOCUMENTATION.md`
- **Resumen ejecutivo:** `RESUMEN_AUTH_ENDPOINTS.md`

---

## ⚠️ Importante

### TODO: Servicio de Correos
- ✅ Tokens se generan correctamente
- ✅ Tokens se pueden obtener de logs/BD
- ⏳ Correos no se envían (pendiente)

Cuando el servicio esté listo, los tokens llegarán automáticamente por email.

---

## 🎯 Estados

| Funcionalidad | Estado |
|---------------|--------|
| PATCH /auth/password | ✅ Funcional |
| POST /auth/resend-verification | ✅ Funcional |
| POST /auth/confirm-email | ✅ Funcional |
| Envío de correos | ⏳ Pendiente |

---

**¡Listo para usar!** 🎉

Ejecuta:
```bash
./test_auth_endpoints.sh help
```

