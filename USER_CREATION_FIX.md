# Solución: Usuarios creados sin FORCE_CHANGE_PASSWORD

## 🎯 Problema Resuelto

Los usuarios creados ahora quedan en estado **CONFIRMED** desde el inicio, sin necesidad de cambiar contraseña (estado `FORCE_CHANGE_PASSWORD`).

## 🔧 Cambios Realizados

### 1. Endpoint de Creación de Usuario (`POST /api/v1/users/`)

**Archivo**: `app/api/v1/endpoints/users.py`

#### Cambios aplicados:

1. ✅ **Agregar `email_verified` como atributo al crear el usuario**:
   ```python
   UserAttributes=[
       {"Name": "email", "Value": user.email},
       {"Name": "email_verified", "Value": "true"},  # ← NUEVO
       {"Name": "name", "Value": user.name},
   ]
   ```

2. ✅ **Establecer contraseña permanente** (ya estaba, pero se mejoró el comentario):
   ```python
   cognito.admin_set_user_password(
       UserPoolId=settings.COGNITO_USER_POOL_ID,
       Username=user.email,
       Password=user.password,
       Permanent=True,  # ← Esto evita el estado FORCE_CHANGE_PASSWORD
   )
   ```

3. ✅ **Mejorar extracción del cognito_sub**:
   ```python
   cognito_sub = next(
       (attr["Value"] for attr in cognito_resp["User"]["Attributes"] if attr["Name"] == "sub"),
       None
   )
   ```

4. ✅ **Mejor manejo de errores**:
   ```python
   detail=f"Error en Cognito [{error_code}]: {e.response['Error'].get('Message', str(e))}"
   ```

### 2. Endpoint de Aceptar Invitación (`POST /api/v1/users/accept-invitation`)

Los mismos cambios fueron aplicados al endpoint de aceptar invitación para mantener consistencia.

## 📋 Por qué funcionaba antes

Cuando usas `admin_create_user` con `MessageAction="SUPPRESS"`, Cognito crea el usuario en un estado temporal. Aunque se establezca la contraseña con `Permanent=True`, si `email_verified` no está explícitamente en `true` desde la creación, el usuario puede quedar en estado `FORCE_CHANGE_PASSWORD`.

## ✅ Solución

Al agregar explícitamente `email_verified: true` en los atributos durante la creación del usuario, Cognito entiende que:
1. El email ya está verificado
2. La contraseña es permanente
3. El usuario debe quedar en estado `CONFIRMED`

## 🧪 Cómo Probar

### Opción 1: Crear un nuevo usuario

```bash
curl --location 'http://localhost:8000/api/v1/users/' \
--header 'Content-Type: application/json' \
--data-raw '{
  "email": "newuser@example.com",
  "name": "Nuevo Usuario",
  "password": "TestPass123!",
  "is_master": true,
  "client_id": "tu-client-id-aqui"
}'
```

### Opción 2: Inmediatamente después, hacer login

```bash
curl --location 'http://localhost:8000/api/v1/auth/login' \
--header 'Content-Type: application/json' \
--data-raw '{
  "email": "newuser@example.com",
  "password": "TestPass123!"
}'
```

**Resultado esperado**: Login exitoso (status 200) con tokens de acceso.

### Opción 3: Usar el script de prueba

```bash
chmod +x test_user_creation.sh
./test_user_creation.sh
```

Este script:
1. Crea un usuario nuevo
2. Espera 2 segundos
3. Intenta hacer login
4. Muestra si el proceso fue exitoso

## 🔍 Verificar Estado en Cognito

Si quieres verificar el estado de un usuario en Cognito:

```bash
source .venv/bin/activate
python scripts/diagnose_cognito_user.py usuario@example.com
```

Deberías ver:
```
✅ Usuario encontrado en Cognito
   - User Status: CONFIRMED  ← Debe ser CONFIRMED, no FORCE_CHANGE_PASSWORD
   ✅ email_verified: true
```

## 🛠️ Usuarios Existentes

Si tienes usuarios existentes en estado `FORCE_CHANGE_PASSWORD`, usa el script de reparación:

```bash
source .venv/bin/activate
python scripts/fix_cognito_user.py usuario@example.com 'NuevaContraseña123!'
```

Esto:
1. Confirma al usuario
2. Establece una contraseña permanente
3. Marca el email como verificado
4. Deja al usuario en estado `CONFIRMED`

## 📝 Notas Importantes

1. ✅ **Todos los nuevos usuarios** creados desde ahora quedarán en estado `CONFIRMED`
2. ✅ Los usuarios pueden hacer login **inmediatamente** después de ser creados
3. ✅ No necesitan cambiar su contraseña
4. ✅ El cambio aplica tanto a usuarios creados directamente como por invitación

## 🚀 Siguientes Pasos

1. Prueba crear un nuevo usuario
2. Verifica que puedas hacer login inmediatamente
3. Si tienes usuarios existentes con problemas, usa el script de reparación
4. Considera eliminar usuarios de prueba antiguos que estén en mal estado

## 🔒 Seguridad

Los cambios mantienen la seguridad porque:
- ✅ La contraseña sigue siendo validada según las políticas de Cognito
- ✅ El usuario aún debe autenticarse con credenciales válidas
- ✅ Los tokens de acceso siguen siendo necesarios para las operaciones
- ✅ Solo se marca `email_verified=true` para usuarios creados por administradores

La diferencia es que ahora el usuario **no necesita** hacer un cambio de contraseña inicial forzado.

