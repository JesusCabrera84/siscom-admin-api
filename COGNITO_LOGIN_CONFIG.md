# Configuración de Cognito para Login

## Configuración Requerida en AWS Cognito User Pool

Para que el endpoint de login funcione correctamente, es necesario configurar el User Pool de Cognito:

### 1. Habilitar el flujo USER_PASSWORD_AUTH

En la consola de AWS Cognito:
1. Ve a tu User Pool
2. Selecciona la pestaña "App integration" (Integración de aplicaciones)
3. Selecciona tu App Client
4. En "Authentication flows" (Flujos de autenticación), asegúrate de tener habilitado:
   - ✅ **ALLOW_USER_PASSWORD_AUTH**
   - ✅ **ALLOW_REFRESH_TOKEN_AUTH** (para refrescar tokens)

### 2. Verificar que tienes configurado CLIENT_SECRET

El endpoint de login utiliza el `CLIENT_SECRET` para generar el `SECRET_HASH` requerido por Cognito.
Asegúrate de que:
- Tu App Client tiene un Client Secret generado
- El valor está configurado en tu archivo `.env` como `COGNITO_CLIENT_SECRET`

### 3. Variables de entorno requeridas

Asegúrate de tener las siguientes variables en tu archivo `.env`:

```env
COGNITO_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
COGNITO_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Endpoint de Login

### URL
```
POST /api/v1/auth/login
```

### Request Body
```json
{
  "email": "usuario@example.com",
  "password": "MiPassword123!"
}
```

### Response (200 OK)
```json
{
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "client_id": "223e4567-e89b-12d3-a456-426614174000",
    "email": "usuario@example.com",
    "full_name": "Juan García",
    "is_master": true,
    "email_verified": true,
    "last_login_at": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-10T08:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  },
  "access_token": "eyJraWQiOiJ...",
  "id_token": "eyJraWQiOiJ...",
  "refresh_token": "eyJjdHkiOiJ...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Códigos de Error

- **404 Not Found**: Usuario no encontrado
  ```json
  {
    "detail": "Usuario no encontrado"
  }
  ```

- **403 Forbidden**: Email no verificado
  ```json
  {
    "detail": "Email no verificado"
  }
  ```

- **401 Unauthorized**: Credenciales inválidas
  ```json
  {
    "detail": "Credenciales inválidas"
  }
  ```

## Uso de los Tokens

Los tokens retornados deben ser utilizados de la siguiente manera:

- **access_token**: Para autenticar las peticiones a la API. Incluir en el header:
  ```
  Authorization: Bearer {access_token}
  ```

- **id_token**: Contiene información del usuario codificada en JWT

- **refresh_token**: Para obtener un nuevo access_token cuando expire (expires_in segundos)

## Flujo de Autenticación

```
1. Usuario envía email y contraseña
   ↓
2. Sistema verifica que el usuario existe en BD
   ↓
3. Sistema verifica que email_verified = true
   ↓
4. Sistema autentica con Cognito
   ↓
5. Sistema actualiza last_login_at
   ↓
6. Sistema retorna información del usuario + tokens
```

