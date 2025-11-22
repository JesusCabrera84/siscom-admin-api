# Configuración de Emails con AWS SES

Este documento describe cómo configurar el sistema de notificaciones por email usando AWS SES.

## Requisitos previos

1. **AWS SES configurado**: Debes tener un email verificado en AWS SES
2. **IAM Role con permisos SES**: Si tu aplicación corre en EC2, el rol IAM debe tener permisos de `ses:SendEmail`
3. **Frontend desplegado**: Necesitas la URL base de tu aplicación frontend

## Variables de entorno requeridas

Agrega las siguientes variables a tu archivo `.env`:

```bash
# AWS SES - Email Configuration
# Email verificado en AWS SES (debe estar verificado en la consola de SES)
SES_FROM_EMAIL=noreply@tudominio.com

# Región de SES (opcional, si no se especifica usa COGNITO_REGION)
SES_REGION=us-east-1

# Frontend URL - Para construir URLs de acción en emails
# URL base de tu aplicación frontend (sin trailing slash)
FRONTEND_URL=https://app.tudominio.com
```

## Permisos IAM necesarios

Si tu aplicación corre en EC2, asegúrate de que el IAM Role tenga esta política:

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

## Verificar email en AWS SES

### Para entorno de sandbox (desarrollo):

1. Ve a AWS SES Console
2. Navega a "Verified identities"
3. Haz clic en "Create identity"
4. Selecciona "Email address"
5. Ingresa el email que usarás como remitente (ej: `noreply@tudominio.com`)
6. Verifica el email haciendo clic en el enlace que recibirás

**Nota**: En sandbox mode, también necesitas verificar los emails de destino.

### Para producción:

1. Solicita mover tu cuenta de SES fuera del sandbox:
   - Ve a AWS SES Console
   - En el menú lateral, selecciona "Account dashboard"
   - Haz clic en "Request production access"
   - Completa el formulario explicando tu caso de uso

2. Verifica tu dominio completo:
   - Ve a "Verified identities"
   - Crea una identidad de tipo "Domain"
   - Sigue las instrucciones para agregar los registros DNS necesarios

## Tipos de emails que se envían

El sistema envía 3 tipos de emails:

### 1. Verificación de email (registro de nuevos clientes)

**Template**: `app/templates/verification_email.html`

**Se envía cuando**:

- Un nuevo cliente se registra en el sistema

**Rutas del frontend esperadas**:

- `{FRONTEND_URL}/verify-email?token={token}`

### 2. Invitación de usuarios

**Template**: `app/templates/invitation.html`

**Se envía cuando**:

- Un usuario maestro invita a un nuevo usuario
- Se reenvía una invitación

**Rutas del frontend esperadas**:

- `{FRONTEND_URL}/accept-invitation?token={token}`

### 3. Restablecimiento de contraseña

**Template**: `app/templates/password_reset.html`

**Se envía cuando**:

- Un usuario solicita restablecer su contraseña

**Rutas del frontend esperadas**:

- `{FRONTEND_URL}/reset-password?token={token}`

## Personalización de templates

Los templates HTML están en `app/templates/` y usan Jinja2. Cada template recibe las siguientes variables:

- `subject`: Asunto del correo
- `title`: Título principal del mensaje
- `message`: Mensaje descriptivo
- `action_url`: URL completa con el token para la acción

Puedes personalizar el diseño editando los archivos HTML en `app/templates/`.

## Instalación de dependencias

Asegúrate de instalar jinja2:

```bash
pip install -r requirements.txt
```

## Pruebas

Para probar el envío de emails en desarrollo:

### 1. Verificar configuración

```bash
# Verifica que las variables estén configuradas
echo $SES_FROM_EMAIL
echo $FRONTEND_URL
```

### 2. Probar registro de cliente

```bash
curl -X POST http://localhost:8000/api/v1/clients/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Client",
    "email": "test@example.com",
    "password": "TestPass123!"
  }'
```

### 3. Verificar logs

Busca en los logs del servidor:

```
[EMAIL] Correo enviado a test@example.com - MessageId: xxx
```

O errores:

```
[EMAIL ERROR] No se pudo enviar correo a test@example.com: [error]
```

## Troubleshooting

### Error: "Email address is not verified"

**Solución**: Verifica el email remitente en la consola de AWS SES.

### Error: "MessageRejected"

**Solución**:

- Si estás en sandbox mode, verifica también el email del destinatario
- Revisa los límites de envío de tu cuenta SES

### Error: "AccessDenied"

**Solución**: Verifica que el IAM Role tenga los permisos de SES necesarios.

### Los emails no llegan

**Checklist**:

1. ✅ Email remitente verificado en SES
2. ✅ Si estás en sandbox, email destino también verificado
3. ✅ Variable `SES_FROM_EMAIL` configurada correctamente
4. ✅ Permisos IAM correctos
5. ✅ Revisa la carpeta de spam del destinatario
6. ✅ Verifica los logs de la aplicación

## Monitoreo

### Ver métricas en AWS SES

1. Ve a AWS SES Console
2. Selecciona "Sending statistics"
3. Revisa:
   - Emails enviados
   - Bounces
   - Complaints
   - Delivery rate

### Logs de la aplicación

Los logs incluyen:

- `[EMAIL]`: Email enviado correctamente
- `[EMAIL ERROR]`: Error al enviar email
- `[WARNING]`: Email no pudo ser enviado pero la operación continuó

## Mejores prácticas

1. **Producción**: Mueve tu cuenta fuera del sandbox de SES
2. **Dominio verificado**: Verifica tu dominio completo en lugar de emails individuales
3. **Monitoreo**: Configura alarmas de CloudWatch para bounces y complaints
4. **Templates**: Mantén los templates simples y mobile-friendly
5. **Testing**: Siempre prueba en sandbox antes de mover a producción
6. **SPF/DKIM**: Configura correctamente SPF y DKIM para mejor deliverability

## Referencias

- [AWS SES Documentation](https://docs.aws.amazon.com/ses/)
- [Moving out of SES Sandbox](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)
- [SES Sending Authorization](https://docs.aws.amazon.com/ses/latest/dg/sending-authorization.html)
