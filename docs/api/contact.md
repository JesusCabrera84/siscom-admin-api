# API de Contacto

Este documento describe el endpoint de contacto que permite a los usuarios enviar mensajes desde el frontend.

## Endpoint

### POST `/api/v1/contact/send-message`

Envía un mensaje de contacto a la dirección de correo configurada.

#### Request Body

```json
{
  "nombre": "Juan Pérez",
  "correo_electronico": "juan@example.com",
  "telefono": "+52 123 456 7890",
  "mensaje": "Estoy interesado en sus servicios..."
}
```

**Campos:**

- `nombre` (string, requerido): Nombre de la persona que envía el mensaje
- `correo_electronico` (string, opcional): Email de contacto (debe ser un email válido)
- `telefono` (string, opcional): Teléfono de contacto
- `mensaje` (string, requerido): Contenido del mensaje

**Validaciones:**

- Al menos uno de `correo_electronico` o `telefono` debe estar presente (no pueden estar ambos vacíos)
- `nombre` y `mensaje` son obligatorios y no pueden estar vacíos

#### Response Success (200 OK)

```json
{
  "success": true,
  "message": "Mensaje de contacto enviado exitosamente. Nos pondremos en contacto contigo pronto."
}
```

#### Response Error (400 Bad Request)

```json
{
  "detail": "Debe proporcionar al menos un correo electrónico o un teléfono"
}
```

#### Response Error (500 Internal Server Error)

```json
{
  "detail": "No se pudo enviar el mensaje de contacto. Por favor intente más tarde."
}
```

## Configuración

### Variables de Entorno

Para que el endpoint funcione correctamente, debes configurar la siguiente variable de entorno en tu archivo `.env`:

```bash
# Email donde se reciben los mensajes de contacto
CONTACT_EMAIL=contacto@geminislabs.com
```

Esta dirección de correo recibirá todos los mensajes de contacto enviados desde el formulario de la página web.

### Permisos AWS SES

El endpoint utiliza AWS SES para enviar correos, por lo que la dirección `CONTACT_EMAIL` debe:

1. Estar verificada en AWS SES (si estás en sandbox mode)
2. Cumplir con las políticas de SES (si estás en producción)

Para verificar un email en AWS SES:

```bash
# Usando AWS CLI
aws ses verify-email-identity --email-address contacto@geminislabs.com
```

O desde la consola de AWS:
1. Ve a AWS SES Console
2. Navega a "Verified identities"
3. Haz clic en "Create identity"
4. Selecciona "Email address"
5. Ingresa el email y verifica haciendo clic en el enlace que recibirás

## Formato del Email

Cuando se envía un mensaje de contacto, el email que se recibe contiene:

- **Asunto**: `Nuevo mensaje de contacto desde la página web - [Nombre]`
- **Contenido**:
  - Nombre del contacto
  - Correo electrónico
  - Teléfono
  - Mensaje completo

El template utilizado es `contact_message.html` ubicado en `app/templates/`.

## Ejemplo de Uso

### cURL

```bash
curl -X POST "https://api.tudominio.com/api/v1/contact/send-message" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan Pérez",
    "correo_electronico": "juan@example.com",
    "telefono": "+52 123 456 7890",
    "mensaje": "Estoy interesado en sus servicios de monitoreo vehicular"
  }'
```

### JavaScript (Fetch)

```javascript
const response = await fetch('https://api.tudominio.com/api/v1/contact/send-message', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    nombre: 'Juan Pérez',
    correo_electronico: 'juan@example.com',
    telefono: '+52 123 456 7890',
    mensaje: 'Estoy interesado en sus servicios de monitoreo vehicular'
  })
});

const data = await response.json();
console.log(data);
```

### Python (requests)

```python
import requests

url = "https://api.tudominio.com/api/v1/contact/send-message"
payload = {
    "nombre": "Juan Pérez",
    "correo_electronico": "juan@example.com",
    "telefono": "+52 123 456 7890",
    "mensaje": "Estoy interesado en sus servicios de monitoreo vehicular"
}

response = requests.post(url, json=payload)
print(response.json())
```

## Notas de Seguridad

- Este endpoint **NO requiere autenticación** ya que es público para uso desde el formulario de contacto del sitio web
- Se recomienda implementar rate limiting en el servidor web (nginx/apache) para prevenir abuso
- Considera implementar CAPTCHA en el frontend para prevenir spam

## Logs

El servicio registra información sobre los emails enviados:

```
[EMAIL] Correo enviado a contacto@geminislabs.com - MessageId: 0100018d...
```

En caso de error:

```
[EMAIL ERROR] No se pudo enviar correo a contacto@geminislabs.com: [Error details]
[CONTACT ERROR] Error inesperado al procesar mensaje de contacto: ...
```

## Troubleshooting

### Error: "Email address is not verified"

**Causa**: El email `CONTACT_EMAIL` no está verificado en AWS SES

**Solución**: Verifica el email en la consola de AWS SES

### Error: "MessageRejected"

**Causa**: Cuenta en sandbox mode y límites de envío alcanzados

**Solución**: 
- Solicita mover tu cuenta fuera del sandbox de AWS SES
- Revisa los límites de envío en la consola de SES

### Los emails no llegan

**Checklist**:
1. ✅ Variable `CONTACT_EMAIL` configurada en `.env`
2. ✅ Email verificado en AWS SES
3. ✅ Permisos IAM correctos para SES
4. ✅ Revisar logs de la aplicación
5. ✅ Revisar carpeta de spam
6. ✅ Verificar métricas de SES en AWS Console

