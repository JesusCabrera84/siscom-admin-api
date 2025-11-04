# 🚀 Quick Start - Recuperación de Contraseña

Guía rápida para empezar a usar el sistema de recuperación de contraseña.

---

## ⚡ Inicio Rápido (3 pasos)

### 1️⃣ Solicitar recuperación
```bash
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@example.com"}'
```

**Respuesta:**
```json
{
  "message": "Se ha enviado un código de verificación al correo registrado."
}
```

---

### 2️⃣ Obtener el token

**Desde logs:**
```bash
docker-compose logs api | grep "PASSWORD RESET"
```

**Desde base de datos:**
```bash
docker-compose exec db psql -U postgres -d siscom_db -c \
  "SELECT token FROM tokens_confirmacion WHERE type='password_reset' ORDER BY created_at DESC LIMIT 1;"
```

---

### 3️⃣ Restablecer contraseña
```bash
curl -X POST http://localhost:8000/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "TU_TOKEN_AQUI",
    "new_password": "NuevaPassword123!"
  }'
```

**Respuesta:**
```json
{
  "message": "Contraseña restablecida exitosamente. Ahora puede iniciar sesión con su nueva contraseña."
}
```

---

### ✅ Iniciar sesión
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@example.com",
    "password": "NuevaPassword123!"
  }'
```

---

## 🧪 Script de Prueba Automático

```bash
# Dar permisos de ejecución (solo la primera vez)
chmod +x test_password_recovery.sh

# Ejecutar
./test_password_recovery.sh usuario@example.com
```

---

## 📋 Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/auth/forgot-password` | Solicitar recuperación |
| POST | `/api/v1/auth/reset-password` | Restablecer contraseña |
| POST | `/api/v1/auth/login` | Iniciar sesión |

---

## ✅ Validación de Contraseñas

Las contraseñas deben tener:
- ✅ Mínimo 8 caracteres
- ✅ Una mayúscula (A-Z)
- ✅ Una minúscula (a-z)
- ✅ Un número (0-9)
- ✅ Un carácter especial (!@#$%^&*...)

**Ejemplos válidos:**
- `Password123!`
- `MiClave99#`
- `NuevaPwd2025!`

---

## 🔍 Solución Rápida de Problemas

| Error | Causa | Solución |
|-------|-------|----------|
| Token inválido | Token incorrecto | Verificar token en BD/logs |
| Token expirado | > 1 hora | Solicitar nuevo token |
| Token ya usado | Reutilización | Solicitar nuevo token |
| Contraseña inválida | No cumple requisitos | Usar contraseña segura |

---

## 📚 Documentación Completa

Para más detalles, consulta:

- **Flujo técnico completo:** `PASSWORD_RECOVERY_FLOW.md`
- **Resumen ejecutivo:** `RESUMEN_RECUPERACION_PASSWORD.md`
- **Ejemplos Postman:** `POSTMAN_EXAMPLES_PASSWORD_RECOVERY.md`
- **Registro de cambios:** `CHANGELOG_PASSWORD_RECOVERY.md`

---

## ⚠️ Importante

### TODO: Servicio de Correos
El envío de correos está pendiente de implementar. Actualmente:
- ✅ Los tokens se generan y guardan correctamente
- ✅ Los tokens se pueden obtener de logs o BD
- ⏳ Los correos no se envían (TODO)

Cuando el servicio de notificaciones esté listo, los usuarios recibirán el token automáticamente por email.

---

## 🎯 Estado Actual

| Característica | Estado |
|----------------|--------|
| Endpoint forgot-password | ✅ Funcional |
| Endpoint reset-password | ✅ Funcional |
| Generación de tokens | ✅ Funcional |
| Validación de tokens | ✅ Funcional |
| Integración con Cognito | ✅ Funcional |
| Envío de correos | ⏳ Pendiente |

---

**¡Listo para usar!** 🎉

Para comenzar, ejecuta:
```bash
./test_password_recovery.sh tu-email@example.com
```

