# Solución: Guardar password_hash en la Base de Datos

## 🎯 Problema Resuelto

Se corrigió el error `NotNullViolation` en la columna `password_hash` al crear usuarios. Ahora el sistema:
- ✅ Guarda la contraseña en AWS Cognito
- ✅ Guarda el hash de la contraseña en la base de datos

## 🔧 Cambios Realizados

### 1. Modificación del Endpoint `create_user`

**Archivo**: `app/api/v1/endpoints/users.py`

Se agregó el hasheo y guardado de la contraseña:

```python
new_user = User(
    email=user.email,
    full_name=user.name,
    cognito_sub=cognito_sub,
    is_master=user.is_master,
    client_id=user.client_id,
    password_hash=hash_password(user.password),  # ← NUEVO
)
```

### 2. Modificación del Endpoint `accept_invitation`

**Archivo**: `app/api/v1/endpoints/users.py`

Se agregó el hasheo y guardado de la contraseña:

```python
new_user = User(
    email=email,
    full_name=full_name or email,
    client_id=client_id,
    cognito_sub=cognito_sub,
    is_master=False,
    email_verified=True,
    password_hash=hash_password(data.password),  # ← NUEVO
)
```

### 3. Import Agregado

Se importó la función `hash_password`:

```python
from app.utils.security import generate_verification_token, hash_password
```

## 🔐 Seguridad

El sistema utiliza `passlib` con `bcrypt` para hashear contraseñas de forma segura:

- ✅ **Hasheo seguro**: Usa bcrypt con salt automático
- ✅ **No reversible**: Los hashes no pueden ser desencriptados
- ✅ **Doble almacenamiento**: En Cognito (para autenticación) y en BD (para respaldo)

## 🧪 Cómo Probar

### 1. Crear un nuevo usuario:

```bash
curl --location 'http://localhost:8000/api/v1/users/' \
--header 'Content-Type: application/json' \
--data-raw '{
  "email": "nuevo@example.com",
  "name": "Usuario Nuevo",
  "password": "TestPass123!",
  "is_master": true,
  "client_id": "tu-client-id"
}'
```

**Resultado esperado**: ✅ Usuario creado con `password_hash` guardado en BD

### 2. Aceptar una invitación:

```bash
curl --location 'http://localhost:8000/api/v1/users/accept-invitation' \
--header 'Content-Type: application/json' \
--data '{
  "password": "Soy1Password*",
  "token": "tu-token-de-invitacion"
}'
```

**Resultado esperado**: ✅ Usuario creado con `password_hash` guardado en BD

## 🛠️ Actualizar Usuarios Existentes

Si tienes usuarios existentes sin `password_hash`, ejecuta el script:

```bash
source .venv/bin/activate
python scripts/update_existing_users_password_hash.py
```

Este script:
1. Busca usuarios sin `password_hash`
2. Les asigna una contraseña temporal
3. Guarda el hash en la base de datos

La contraseña temporal es: `TempPass123!` (definida en `settings.DEFAULT_USER_PASSWORD`)

## 📋 Verificar que un Usuario Tiene password_hash

Puedes verificar usando el script de diagnóstico:

```bash
source .venv/bin/activate
python scripts/check_user_in_db.py usuario@example.com
```

Deberías ver que el usuario tiene `password_hash` no nulo.

## ⚙️ Flujo de Autenticación

Con estos cambios, el flujo es:

1. **Al crear usuario**:
   - Se crea en Cognito con contraseña
   - Se guarda en BD con `password_hash`

2. **Al hacer login**:
   - Se autentica con Cognito (usando la contraseña de Cognito)
   - Se actualiza `last_login_at` en BD

3. **Respaldo**:
   - Si Cognito falla, podrías implementar autenticación con el `password_hash` de BD
   - Útil para migración o disaster recovery

## 🔑 Funciones de Seguridad Disponibles

En `app/utils/security.py`:

```python
# Hashear una contraseña
hashed = hash_password("MiPassword123!")

# Verificar una contraseña
is_valid = verify_password("MiPassword123!", hashed)  # True o False
```

## 📝 Notas Importantes

1. ✅ **Nuevos usuarios**: Se crea automáticamente el `password_hash`
2. ✅ **Usuarios existentes**: Usa el script de actualización
3. ✅ **Cognito sigue siendo la fuente principal**: La autenticación se hace con Cognito
4. ✅ **BD como respaldo**: El `password_hash` está disponible si lo necesitas

## 🚀 Próximos Pasos

1. ✅ Prueba crear un nuevo usuario
2. ✅ Prueba aceptar una invitación
3. ⚠️  Si tienes usuarios existentes, ejecuta el script de actualización
4. ✅ Verifica que el login funciona correctamente

## 🔄 Resumen de la Solución

**Antes**: ❌ Error 500 - `password_hash` era NULL al crear usuarios

**Ahora**: ✅ El `password_hash` se genera y guarda automáticamente usando bcrypt

