## Nuevo Flujo de Verificación de Email para Clientes

## 🎯 Objetivo

Eliminar el uso de `password_hash` en la base de datos y usar únicamente AWS Cognito para autenticación. El usuario maestro se crea en estado `UNCONFIRMED` hasta que verifique su email.

## 🔄 Flujo Completo

### 1. Creación de Cliente (POST /api/v1/clients/)

```bash
curl --location 'http://localhost:8000/api/v1/clients/' \
--header 'Content-Type: application/json' \
--data-raw '{
  "name": "Mi Empresa",
  "email": "admin@miempresa.com",
  "password": "MiPassword123!"
}'
```

**Lo que sucede:**

1. ✅ Se crea el cliente con `status=PENDING`
2. ✅ Se crea el usuario maestro en BD sin `password_hash` y sin `cognito_sub`
3. ✅ Se genera un token de verificación
4. ✅ La contraseña se guarda **temporalmente** en `tokens_confirmacion.password_temp`
5. ⏳ Se envía email con link de verificación (pendiente de implementar)

**Estado en BD:**
- `clients.status` = `PENDING`
- `users.email_verified` = `false`
- `users.cognito_sub` = `null`
- `users.password_hash` = `null`
- `tokens_confirmacion.password_temp` = `"MiPassword123!"` (temporal)

**Estado en Cognito:**
- ❌ El usuario NO existe todavía en Cognito

### 2. Verificación de Email (POST /api/v1/clients/verify-email)

```bash
curl --location 'http://localhost:8000/api/v1/clients/verify-email' \
--header 'Content-Type: application/json' \
--data-raw '{
  "token": "abc123..."
}'
```

**Lo que sucede:**

1. ✅ Se valida el token (no usado, no expirado)
2. ✅ Se crea el usuario en Cognito con `email_verified=true`
3. ✅ Se establece la contraseña permanente en Cognito
4. ✅ El usuario queda en estado `CONFIRMED` en Cognito
5. ✅ Se actualiza `users.cognito_sub` en BD
6. ✅ Se actualiza `users.email_verified = true` en BD
7. ✅ Se actualiza `clients.status = ACTIVE`
8. ✅ Se marca el token como usado
9. ✅ Se limpia `password_temp` por seguridad

**Estado final en BD:**
- `clients.status` = `ACTIVE`
- `users.email_verified` = `true`
- `users.cognito_sub` = `"447884b8-b021-7088-b8d6-a58720bcc93c"`
- `users.password_hash` = `null` (no se usa)
- `tokens_confirmacion.used` = `true`
- `tokens_confirmacion.password_temp` = `null` (limpiado)

**Estado en Cognito:**
- ✅ Usuario existe
- ✅ Estado: `CONFIRMED`
- ✅ `email_verified` = `true`
- ✅ Contraseña establecida como permanente

### 3. Login (POST /api/v1/auth/login)

```bash
curl --location 'http://localhost:8000/api/v1/auth/login' \
--header 'Content-Type: application/json' \
--data-raw '{
  "email": "admin@miempresa.com",
  "password": "MiPassword123!"
}'
```

**Validaciones:**

1. ✅ Usuario existe en BD
2. ✅ `email_verified = true` en BD
3. ✅ Usuario existe y está `CONFIRMED` en Cognito
4. ✅ Contraseña correcta en Cognito
5. ✅ Se actualiza `last_login_at`
6. ✅ Se retorna usuario + tokens

## 🗄️ Cambios en la Base de Datos

### Migración 004

**Ejecutar:**
```bash
source .venv/bin/activate
python scripts/apply_migration_004.py
```

O con SQL directo:
```bash
psql -d siscom_admin -f scripts/apply_004_migration.sql
```

**Cambios:**
1. `users.password_hash` → nullable (antes NOT NULL)
2. `tokens_confirmacion.password_temp` → nuevo campo VARCHAR(255) nullable

## 📝 Modelo TokenConfirmacion Actualizado

```python
class TokenConfirmacion(SQLModel, table=True):
    id: UUID
    token: str
    expires_at: datetime
    used: bool
    type: TokenType
    user_id: UUID | None
    email: str | None
    full_name: str | None
    client_id: UUID | None
    password_temp: str | None  # ← NUEVO: contraseña temporal
    created_at: datetime
```

## 🔐 Seguridad

### ✅ Ventajas

1. **No hay contraseñas en BD**: Solo en Cognito
2. **Contraseña temporal protegida**: 
   - Solo existe durante el proceso de verificación
   - Se limpia inmediatamente después de usarla
   - Expira con el token (1 hora por defecto)
3. **Estado explícito**: El usuario no puede logear hasta verificar email
4. **Auditable**: Todo queda registrado en `tokens_confirmacion`

### ⚠️ Consideraciones

1. La contraseña está en texto plano en `password_temp` durante el proceso de verificación
2. El token de verificación es sensible (quien lo tenga puede crear la cuenta)
3. Se debe enviar el token por email seguro (HTTPS, TLS)

## 🧪 Pruebas

### Prueba Completa

```bash
# 1. Crear cliente
RESPONSE=$(curl -s -X POST 'http://localhost:8000/api/v1/clients/' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Test Company",
    "email": "test@example.com",
    "password": "TestPass123!"
  }')

echo "Cliente creado: $RESPONSE"

# 2. Obtener el token de la base de datos
# psql -d siscom_admin -c "SELECT token FROM tokens_confirmacion WHERE used = false ORDER BY created_at DESC LIMIT 1;"

# 3. Verificar email
curl -X POST 'http://localhost:8000/api/v1/clients/verify-email' \
  -H 'Content-Type: application/json' \
  -d '{
    "token": "TOKEN_AQUI"
  }'

# 4. Login
curl -X POST 'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }'
```

### Verificar Estados

```bash
# En BD
psql -d siscom_admin -c "
SELECT 
    u.email,
    u.email_verified,
    u.cognito_sub IS NOT NULL as has_cognito_sub,
    u.password_hash IS NULL as password_hash_null,
    c.status as client_status
FROM users u
JOIN clients c ON u.client_id = c.id
WHERE u.email = 'test@example.com';
"

# En Cognito
source .venv/bin/activate
python scripts/diagnose_cognito_user.py test@example.com
```

## 🔄 Comparación: Antes vs Ahora

### ❌ Flujo Anterior

1. Crear cliente → Se crea usuario en Cognito inmediatamente
2. Guardar `password_hash` en BD
3. Usuario puede logear antes de verificar email

### ✅ Flujo Nuevo

1. Crear cliente → Usuario NO se crea en Cognito
2. Guardar contraseña temporal en token
3. Verificar email → Ahora sí se crea en Cognito
4. Usuario solo puede logear después de verificar

## 📋 Checklist de Migración

- [ ] Aplicar migración 004
- [ ] Reiniciar servidor API
- [ ] Probar creación de cliente nuevo
- [ ] Verificar que no se crea en Cognito inmediatamente
- [ ] Probar flujo de verificación completo
- [ ] Verificar que después de verificar sí se crea en Cognito
- [ ] Probar login exitoso
- [ ] Probar que login falla si no está verificado

## 🚀 Próximos Pasos

1. ✅ Aplicar migración 004
2. ✅ Probar flujo completo
3. ⏳ Implementar envío de email de verificación
4. ⏳ Implementar frontend de verificación
5. ⏳ Agregar resend verification email
6. ⏳ Agregar límite de intentos de verificación

## 📞 Soporte

Si encuentras problemas:

```bash
# Diagnóstico de usuario en BD
python scripts/check_user_in_db.py usuario@example.com

# Diagnóstico de usuario en Cognito
python scripts/diagnose_cognito_user.py usuario@example.com

# Verificar tokens pendientes
psql -d siscom_admin -c "SELECT * FROM tokens_confirmacion WHERE used = false;"
```

