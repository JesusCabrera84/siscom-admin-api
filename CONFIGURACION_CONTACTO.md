# ⚙️ Configuración del Endpoint de Contacto

## 📋 Variable de Entorno Requerida

Para activar el endpoint de contacto, debes agregar la siguiente variable a tu archivo `.env`:

```bash
# Contact Email - Email donde se reciben los mensajes de contacto
CONTACT_EMAIL=contacto@geminislabs.com
```

## 🚀 Pasos para Configurar

### 1. Agregar la Variable al archivo .env

Abre tu archivo `.env` y agrega al final:

```bash
# Contact Email - Email donde se reciben los mensajes de contacto
CONTACT_EMAIL=contacto@geminislabs.com
```

### 2. Verificar el Email en AWS SES

Si estás en **sandbox mode** de AWS SES, necesitas verificar el email:

#### Opción A: Usando AWS CLI

```bash
aws ses verify-email-identity --email-address contacto@geminislabs.com --region us-east-1
```

Luego revisa tu bandeja de entrada y haz clic en el enlace de verificación.

#### Opción B: Usando la Consola de AWS

1. Ve a [AWS SES Console](https://console.aws.amazon.com/ses/)
2. En el menú lateral, selecciona **"Verified identities"**
3. Haz clic en **"Create identity"**
4. Selecciona **"Email address"**
5. Ingresa: `contacto@geminislabs.com`
6. Haz clic en **"Create identity"**
7. Revisa tu bandeja de entrada y haz clic en el enlace de verificación

### 3. Reiniciar la Aplicación

Después de agregar la variable al `.env`, reinicia tu servidor:

```bash
# Si estás en desarrollo
uvicorn app.main:app --reload

# O si usas el Makefile
make run
```

## ✅ Verificar la Configuración

### Prueba el Endpoint

Una vez configurado, prueba el endpoint con curl:

```bash
curl -X POST "http://localhost:8000/api/v1/contact/send-message" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Test User",
    "correo_electronico": "test@example.com",
    "telefono": "+52 123 456 7890",
    "mensaje": "Este es un mensaje de prueba"
  }'
```

**Respuesta esperada si está configurado correctamente:**

```json
{
  "success": true,
  "message": "Mensaje de contacto enviado exitosamente. Nos pondremos en contacto contigo pronto."
}
```

**Respuesta si NO está configurado:**

```json
{
  "detail": "El servicio de contacto no está configurado. Por favor contacte al administrador."
}
```

## 🔍 Verificar en los Logs

Si todo está bien, deberías ver en los logs:

```
[EMAIL] Correo enviado a contacto@geminislabs.com - MessageId: 0100018d...
```

## ⚠️ Troubleshooting

### Error: "Field required CONTACT_EMAIL"

**Causa**: No agregaste la variable al archivo `.env`

**Solución**: Agrega la línea `CONTACT_EMAIL=contacto@geminislabs.com` a tu `.env`

### Error: "El servicio de contacto no está configurado"

**Causa**: La variable está vacía o no se cargó correctamente

**Solución**: 
1. Verifica que la variable esté en el `.env`
2. Reinicia el servidor
3. Verifica que no haya espacios extra en el `.env`

### Error: "Email address is not verified"

**Causa**: El email no está verificado en AWS SES

**Solución**: Sigue los pasos de verificación en AWS SES (ver arriba)

### Los emails no llegan

**Checklist**:
1. ✅ Variable `CONTACT_EMAIL` en el `.env`
2. ✅ Email verificado en AWS SES
3. ✅ Permisos IAM correctos para SES
4. ✅ Revisa los logs del servidor
5. ✅ Revisa la carpeta de spam
6. ✅ Verifica métricas en AWS SES Console

## 📚 Documentación Adicional

Para más información sobre el endpoint, consulta:
- [Documentación del API de Contacto](docs/api/contact.md)
- [Configuración de Email con AWS SES](docs/guides/email-configuration.md)

## 🌐 Ejemplo de Uso en Producción

Si estás desplegando en producción, asegúrate de:

1. **Mover tu cuenta fuera del sandbox de AWS SES** (para no tener que verificar cada email)
2. **Usar variables de entorno seguras** (no hardcodear el email)
3. **Implementar rate limiting** en el nginx/servidor web
4. **Considerar agregar CAPTCHA** en el frontend para prevenir spam

### Variables de Entorno en Producción

Si usas Docker, agrega al `docker-compose.yml`:

```yaml
environment:
  - CONTACT_EMAIL=contacto@geminislabs.com
```

Si usas GitHub Actions o CI/CD, agrega como secret:

```yaml
env:
  CONTACT_EMAIL: ${{ secrets.CONTACT_EMAIL }}
```

## 📧 Email de Contacto Recomendado

Para uso profesional, se recomienda usar:
- `contacto@geminislabs.com` (español)
- `contact@geminislabs.com` (inglés)
- `info@geminislabs.com` (genérico)

**IMPORTANTE**: El email debe ser de un dominio que controles y debe estar verificado en AWS SES.

