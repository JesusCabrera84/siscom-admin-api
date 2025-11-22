# Configuración de AWS Cognito

## Descripción

Esta guía explica cómo configurar AWS Cognito para usar con la API de SISCOM.

---

## 1. Crear User Pool

### Paso 1: Ir a AWS Cognito

1. Abre la consola de AWS
2. Busca "Cognito" en servicios
3. Clic en "User Pools"
4. Clic en "Create user pool"

### Paso 2: Configurar Sign-in

- **Sign-in options**: Email
- **User name requirements**: Email address
- Clic en "Next"

### Paso 3: Configurar Seguridad

- **Password policy**: Cognito defaults
  - Mínimo 8 caracteres
  - Requiere números
  - Requiere caracteres especiales
  - Requiere mayúsculas
  - Requiere minúsculas

- **Multi-factor authentication**: Optional (recomendado para producción)
- **User account recovery**: Email only
- Clic en "Next"

### Paso 4: Configurar Sign-up

- **Self-registration**: Disabled (nosotros creamos usuarios vía API)
- **Attribute verification**: Email
- **Required attributes**:
  - email (required)
  - name (optional)
- Clic en "Next"

### Paso 5: Configurar Email

#### Opción 1: Email de Cognito (desarrollo)

- **Email provider**: Send email with Cognito
- **Sender email address**: no-reply@verificationemail.com

#### Opción 2: SES (producción)

- **Email provider**: Send email with Amazon SES
- **SES Region**: us-east-1
- **FROM email address**: noreply@tudominio.com
- **FROM sender name**: SISCOM

- Clic en "Next"

### Paso 6: Integrar App

- **User pool name**: siscom-admin-users
- **App client name**: siscom-admin-api
- **Client secret**: Generate client secret ✅ (importante)
- **Authentication flows**:
  - ✅ ALLOW_USER_PASSWORD_AUTH
  - ✅ ALLOW_REFRESH_TOKEN_AUTH
- Clic en "Next"

### Paso 7: Revisar y Crear

- Revisar configuración
- Clic en "Create user pool"

---

## 2. Obtener Credenciales

Después de crear el User Pool, obtén:

### User Pool ID

1. Abre el User Pool creado
2. En la pestaña "General settings"
3. Copia el **User Pool ID** (ej: `us-east-1_XXXXXXXXX`)

### App Client ID

1. En el User Pool, ve a "App clients"
2. Copia el **App client id** (ej: `xxxxxxxxxxxxxxxxxxxxxxxxxx`)

### App Client Secret

1. En "App clients", clic en "Show Details"
2. Copia el **App client secret** (ej: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

---

## 3. Configurar Variables de Entorno

Actualiza tu archivo `.env`:

```bash
# AWS Cognito
AWS_REGION=us-east-1
COGNITO_USERPOOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
COGNITO_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
COGNITO_REGION=us-east-1
```

---

## 4. Configurar Plantillas de Email

### Email de Verificación

1. En User Pool, ve a "Message customizations"
2. Selecciona "Verification type": Code
3. Personaliza el mensaje:

**Subject:**

```
Verifica tu cuenta en SISCOM
```

**Message:**

```
Hola,

Gracias por registrarte en SISCOM.

Tu código de verificación es: {####}

Este código expirará en 24 horas.

Si no solicitaste este registro, ignora este email.

Saludos,
Equipo SISCOM
```

### Email de Recuperación de Contraseña

**Subject:**

```
Recuperación de contraseña - SISCOM
```

**Message:**

```
Hola,

Recibimos una solicitud para restablecer tu contraseña.

Tu código de verificación es: {####}

Este código expirará en 1 hora.

Si no solicitaste este cambio, ignora este email.

Saludos,
Equipo SISCOM
```

---

## 5. Configurar Políticas de Contraseña

### Requisitos Recomendados

```
Minimum length: 8
Require numbers: Yes
Require special characters: Yes
Require uppercase: Yes
Require lowercase: Yes
```

### Validación en el Frontend

```javascript
function validatePassword(password) {
  const minLength = 8;
  const hasUpperCase = /[A-Z]/.test(password);
  const hasLowerCase = /[a-z]/.test(password);
  const hasNumbers = /\d/.test(password);
  const hasSpecialChar = /[!@#$%^&*]/.test(password);

  return (
    password.length >= minLength &&
    hasUpperCase &&
    hasLowerCase &&
    hasNumbers &&
    hasSpecialChar
  );
}
```

---

## 6. Configurar Atributos Personalizados

### Atributos Estándar Utilizados

- **email** (required): Email del usuario
- **name** (optional): Nombre completo
- **email_verified**: Verificación de email

### Atributos Personalizados (opcional)

Si necesitas agregar más información:

1. Ve a "Attributes"
2. Clic en "Add custom attribute"
3. Ejemplos:
   - `client_id` (String)
   - `role` (String)

**Nota**: Los atributos personalizados no pueden modificarse después de crear el User Pool.

---

## 7. Configurar Lambda Triggers (opcional)

### Pre-signup

Validar email o dominio antes de registro:

```javascript
exports.handler = async (event) => {
  const email = event.request.userAttributes.email;

  // Bloquear emails temporales
  const blockedDomains = ["tempmail.com", "10minutemail.com"];
  const domain = email.split("@")[1];

  if (blockedDomains.includes(domain)) {
    throw new Error("Email domain not allowed");
  }

  return event;
};
```

### Post-confirmation

Enviar notificación al admin cuando nuevo usuario se registre:

```javascript
exports.handler = async (event) => {
  const email = event.request.userAttributes.email;

  // Enviar notificación
  await sendNotification({
    subject: "Nuevo usuario registrado",
    body: `Usuario ${email} se ha registrado exitosamente`,
  });

  return event;
};
```

---

## 8. Seguridad Adicional

### MFA (Multi-Factor Authentication)

1. En User Pool, ve a "MFA and verifications"
2. Selecciona "Optional" para MFA
3. Métodos disponibles:
   - SMS
   - TOTP (Google Authenticator)

### Bloqueo de Cuentas

```
Advanced security: Enabled
Account takeover prevention: Audit only (o Block)
Adaptive authentication: Medium (o High)
```

---

## 9. Monitoreo

### CloudWatch Logs

1. Habilitar logs en Cognito
2. Ver eventos:
   - Sign in attempts
   - Sign up events
   - Password changes
   - Token issuance

### Métricas Útiles

- Total de usuarios
- Usuarios activos (últimos 30 días)
- Intentos fallidos de login
- Tokens emitidos

---

## 10. Pruebas

### Crear Usuario de Prueba Manualmente

```bash
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username test@ejemplo.com \
  --user-attributes Name=email,Value=test@ejemplo.com \
  --temporary-password "TempPassword123!" \
  --message-action SUPPRESS
```

### Establecer Contraseña Permanente

```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username test@ejemplo.com \
  --password "MyPassword123!" \
  --permanent
```

### Verificar Email Manualmente

```bash
aws cognito-idp admin-update-user-attributes \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username test@ejemplo.com \
  --user-attributes Name=email_verified,Value=true
```

---

## 11. Migración de Usuarios (opcional)

Si tienes usuarios existentes en otro sistema:

### Lambda de Migración

```javascript
exports.handler = async (event) => {
  const email = event.userName;
  const password = event.request.password;

  // Validar contra sistema antiguo
  const isValid = await validateInOldSystem(email, password);

  if (isValid) {
    event.response.userAttributes = {
      email: email,
      email_verified: "true",
    };
    event.response.finalUserStatus = "CONFIRMED";
    event.response.messageAction = "SUPPRESS";
  } else {
    throw new Error("Invalid credentials");
  }

  return event;
};
```

---

## 12. Costos

### Tier Gratuito

- 50,000 MAU (Monthly Active Users) gratis
- Incluye funciones básicas de MFA

### Costos Adicionales

- $0.0055 por MAU para 50,001-100,000 usuarios
- Ver precios actualizados en AWS Pricing

---

## Troubleshooting

### Error: "User pool client does not exist"

- Verifica el `COGNITO_CLIENT_ID` en `.env`
- Verifica que el App Client esté activo

### Error: "Invalid client secret"

- Verifica el `COGNITO_CLIENT_SECRET` en `.env`
- Regenera el secret si es necesario

### Error: "User is not confirmed"

- El usuario debe verificar su email primero
- O usar `admin-confirm-sign-up` en AWS CLI

---

## Recursos Adicionales

- [Documentación oficial de Cognito](https://docs.aws.amazon.com/cognito/)
- [Boto3 Cognito Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp.html)
- [JWT Debugger](https://jwt.io/) para inspeccionar tokens
