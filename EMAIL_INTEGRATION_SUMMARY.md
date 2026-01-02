# Resumen de Integración de Emails con AWS SES

## Cambios Implementados

### 1. Servicio de Notificaciones (`app/services/notifications.py`)

Se implementó un servicio completo de notificaciones por email usando AWS SES:

#### Métodos implementados:

- **`send_verification_email(to: str, token: str) -> bool`**
  - Envía correo de verificación cuando un nuevo cliente se registra
  - Template: `verification_email.html`
  - URL: `{FRONTEND_URL}/verify-email?token={token}`

- **`send_invitation_email(to: str, token: str, full_name: Optional[str] = None) -> bool`**
  - Envía correo de invitación cuando un usuario maestro invita a otro usuario
  - Template: `invitation.html`
  - URL: `{FRONTEND_URL}/accept-invitation?token={token}`

- **`send_password_reset_email(to: str, token: str) -> bool`**
  - Envía correo de restablecimiento de contraseña
  - Template: `password_reset.html`
  - URL: `{FRONTEND_URL}/reset-password?token={token}`

#### Características:

- ✅ Usa Jinja2 para renderizar templates HTML
- ✅ Manejo de errores robusto con try/catch
- ✅ Logging detallado de éxitos y errores
- ✅ Retorna `True` si el email se envió correctamente, `False` en caso contrario
- ✅ No requiere AWS credentials si el IAM Role de EC2 tiene permisos

### 2. Configuración (`app/core/config.py`)

Se agregaron 3 nuevas variables de entorno:

```python
# AWS SES - Email configuration
SES_FROM_EMAIL: str              # Email verificado en AWS SES
SES_REGION: Optional[str]        # Región de SES (opcional, usa COGNITO_REGION por defecto)

# Frontend URL
FRONTEND_URL: str                # URL base del frontend para construir links
```

### 3. Templates HTML (`app/templates/`)

Los 3 templates ya existían, pero ahora se usan correctamente:

- `verification_email.html` - Email de verificación
- `invitation.html` - Email de invitación
- `password_reset.html` - Email de reset de contraseña

Cada template recibe las siguientes variables:

- `subject`: Asunto del correo
- `title`: Título principal
- `message`: Mensaje descriptivo
- `action_url`: URL completa con el token

### 4. Integración en Endpoints

Se completaron todos los TODOs de envío de email en los siguientes archivos:

#### `app/api/v1/endpoints/accounts.py`

- ✅ **Línea 89-91**: `create_client()` - Envía email de verificación al crear un nuevo cliente

#### `app/api/v1/endpoints/auth.py`

- ✅ **Línea 220-225**: `forgot_password()` - Envía email de reset de contraseña
- ✅ **Línea 537-542**: `resend_verification()` - Reenvía email de verificación

#### `app/api/v1/endpoints/users.py`

- ✅ **Línea 127-130**: `invite_user()` - Envía email de invitación
- ✅ **Línea 374-379**: `resend_invitation()` - Reenvía email de invitación

### 5. Dependencias (`requirements.txt`)

Se agregó:

```
jinja2==3.1.3
```

### 6. Archivos de Deployment

Se actualizaron los archivos de configuración de Docker y CI/CD:

- ✅ **`docker-compose.yml`**: Agregadas las 3 nuevas variables de entorno para desarrollo
- ✅ **`docker-compose.prod.yml`**: Agregadas las 3 nuevas variables de entorno para producción
- ✅ **`.github/workflows/deploy.yml`**: Actualizado el pipeline de CI/CD para incluir:
  - Variables en el step "Deploy to EC2"
  - Variables en el campo `envs`
  - Variables en el archivo `.env` generado en el servidor

### 7. Documentación

Se crearon/actualizaron los siguientes archivos:

- ✅ **`docs/guides/email-configuration.md`**: Guía completa de configuración de AWS SES
  - Requisitos previos
  - Variables de entorno
  - Permisos IAM
  - Verificación de emails en SES
  - Tipos de emails
  - Troubleshooting
  - Mejores prácticas

- ✅ **`docs/guides/github-actions-email-setup.md`**: Guía para configurar variables en GitHub Actions
  - Cómo agregar variables de repositorio
  - Verificación de configuración
  - Troubleshooting de deployment
  - Comandos útiles

- ✅ **`README.md`**: Actualizado con las nuevas variables de entorno y referencia a la guía

## Variables de Entorno Requeridas

Agrega estas variables a tu archivo `.env`:

```bash
# AWS SES - Email Configuration
SES_FROM_EMAIL=noreply@tudominio.com
SES_REGION=us-east-1  # Opcional, usa COGNITO_REGION por defecto

# Frontend URL
FRONTEND_URL=https://app.tudominio.com
```

## Permisos IAM Necesarios

Si tu aplicación corre en EC2, el IAM Role necesita:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ses:SendEmail", "ses:SendRawEmail"],
      "Resource": "*"
    }
  ]
}
```

## Pasos para Poner en Producción

### 1. Verificar Email en AWS SES

```bash
# Ir a AWS SES Console → Verified identities → Create identity
# Tipo: Email address
# Email: noreply@tudominio.com
# Verificar haciendo clic en el link que recibirás
```

### 2. Configurar Variables en GitHub Actions

**IMPORTANTE**: Si usas GitHub Actions para deployment automático, primero configura las variables en GitHub:

```bash
# Ir a tu repositorio en GitHub
# Settings → Secrets and variables → Actions → Variables
# Agregar las siguientes variables de repositorio:

SES_FROM_EMAIL = noreply@tudominio.com
SES_REGION = us-east-1
FRONTEND_URL = https://app.tudominio.com
```

📖 Ver guía detallada: [GitHub Actions Email Setup](docs/guides/github-actions-email-setup.md)

### 3. Configurar Variables de Entorno (si deployment manual)

```bash
# Agregar al archivo .env de producción en el servidor EC2
SES_FROM_EMAIL=noreply@tudominio.com
SES_REGION=us-east-1
FRONTEND_URL=https://app.tudominio.com
```

### 4. Verificar Permisos IAM

```bash
# Asegurarse de que el IAM Role de EC2 tenga permisos de SES
aws iam get-role-policy --role-name YourEC2Role --policy-name SESSendEmail
```

### 5. Deployment

**Opción A - Con GitHub Actions (Recomendado)**:

```bash
# Hacer push a master
git add .
git commit -m "feat: Integración de emails con AWS SES"
git push origin master

# El workflow se ejecutará automáticamente
# Monitorear en: https://github.com/tu-usuario/tu-repo/actions
```

**Opción B - Manual**:

```bash
# En el servidor EC2
cd siscom-admin-api
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

### 6. Verificar Deployment

```bash
# Conectarse al servidor EC2
ssh usuario@ec2-ip

# Verificar que las variables están configuradas
docker exec siscom-admin-api env | grep -E "SES|FRONTEND"

# Verificar logs
docker logs siscom-admin-api --tail 50
```

### 7. Probar Envío de Emails

```bash
# Registrar un nuevo cliente
curl -X POST https://api.tudominio.com/api/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Client",
    "email": "test@example.com",
    "password": "TestPass123!"
  }'

# Verificar logs
docker logs siscom-admin-api --tail 100 | grep EMAIL
# Debería mostrar: [EMAIL] Correo enviado a test@example.com - MessageId: xxx
```

## Flujo de Emails

### 1. Registro de Cliente

```
Usuario → POST /api/v1/auth/register
       → Se crea cliente y usuario en DB (status PENDING)
       → Se genera token de verificación
       → ✉️ Email de verificación enviado
       → Usuario hace clic en link del email
       → POST /api/v1/auth/verify-email?token={token}
       → Usuario creado en Cognito
       → Cliente y usuario activados
```

### 2. Invitación de Usuario

```
Usuario Maestro → POST /api/v1/users/invite
               → Se genera token de invitación
               → ✉️ Email de invitación enviado
               → Usuario invitado hace clic en link
               → POST /api/v1/users/accept-invitation
               → Usuario creado en Cognito
               → Usuario creado en DB
```

### 3. Reset de Contraseña

```
Usuario → POST /api/v1/auth/forgot-password
       → Se genera token de reset
       → ✉️ Email de reset enviado
       → Usuario hace clic en link
       → POST /api/v1/auth/reset-password
       → Contraseña actualizada en Cognito
```

## Monitoreo

### Logs de la Aplicación

Los logs incluyen información detallada:

```
[EMAIL] Correo enviado a user@example.com - MessageId: xxx
[EMAIL ERROR] No se pudo enviar correo a user@example.com: [Error details]
[WARNING] No se pudo enviar el correo de verificación a user@example.com
```

### Métricas de AWS SES

Ir a AWS SES Console → Sending statistics:

- Emails enviados
- Bounces
- Complaints
- Delivery rate

## Troubleshooting

### ❌ Error: "Email address is not verified"

**Causa**: El email remitente no está verificado en AWS SES

**Solución**:

```bash
# Verificar el email en AWS SES Console
aws ses verify-email-identity --email-address noreply@tudominio.com
```

### ❌ Error: "MessageRejected"

**Causa**: Cuenta en sandbox mode y el email destino no está verificado

**Solución**:

- Verificar también el email de destino en SES Console
- O solicitar mover la cuenta fuera del sandbox

### ❌ Error: "AccessDenied"

**Causa**: IAM Role sin permisos de SES

**Solución**:

```bash
# Agregar política de SES al IAM Role
aws iam put-role-policy \
  --role-name YourEC2Role \
  --policy-name SESSendEmail \
  --policy-document file://ses-policy.json
```

### ❌ Los emails no llegan

**Checklist**:

1. ✅ Email remitente verificado
2. ✅ Variables de entorno configuradas
3. ✅ Permisos IAM correctos
4. ✅ Revisar logs de la aplicación
5. ✅ Revisar carpeta de spam
6. ✅ Verificar métricas de SES

## Próximos Pasos (Opcionales)

### Para mejorar el sistema de emails:

1. **Mover cuenta fuera del sandbox**
   - Solicitar acceso de producción en AWS SES
   - Permitirá enviar a cualquier email sin verificación previa

2. **Verificar dominio completo**
   - En lugar de verificar emails individuales
   - Configurar SPF, DKIM, DMARC

3. **Agregar templates dinámicos**
   - Logos personalizados por cliente
   - Colores de marca
   - Footer con información de contacto

4. **Implementar cola de emails**
   - Usar AWS SQS para envíos asíncronos
   - Reintentos automáticos en caso de fallo

5. **Monitoreo avanzado**
   - Alarmas de CloudWatch para bounces
   - Dashboard de métricas de email
   - Alertas de errores

## Referencias

- [Documentación AWS SES](https://docs.aws.amazon.com/ses/)
- [Guía de configuración](docs/guides/email-configuration.md)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) (para envíos asíncronos)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)

---

## Resumen Técnico

| Componente               | Estado                   | Archivo                                     |
| ------------------------ | ------------------------ | ------------------------------------------- |
| Servicio de emails       | ✅ Completo              | `app/services/notifications.py`             |
| Configuración            | ✅ Completo              | `app/core/config.py`                        |
| Templates HTML           | ✅ Existentes y usándose | `app/templates/*.html`                      |
| Integración en endpoints | ✅ Completo              | `app/api/v1/endpoints/*.py`                 |
| Dependencias             | ✅ Actualizado           | `requirements.txt`                          |
| Docker Compose Dev       | ✅ Actualizado           | `docker-compose.yml`                        |
| Docker Compose Prod      | ✅ Actualizado           | `docker-compose.prod.yml`                   |
| GitHub Actions CI/CD     | ✅ Actualizado           | `.github/workflows/deploy.yml`              |
| Documentación AWS SES    | ✅ Completo              | `docs/guides/email-configuration.md`        |
| Documentación GitHub     | ✅ Completo              | `docs/guides/github-actions-email-setup.md` |
| README                   | ✅ Actualizado           | `README.md`                                 |
| Tests                    | ⏳ Pendiente             | -                                           |

---

**Fecha**: 2025-11-08
**Autor**: Claude AI Assistant
**Versión**: 1.0
