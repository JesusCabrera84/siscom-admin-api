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
  "mensaje": "Estoy interesado en sus servicios...",
  "recaptcha_token": "03AGdBq24PBCd9QF..."
}
```

**Campos:**

- `nombre` (string, requerido): Nombre de la persona que envía el mensaje
- `correo_electronico` (string, opcional): Email de contacto (debe ser un email válido)
- `telefono` (string, opcional): Teléfono de contacto
- `mensaje` (string, requerido): Contenido del mensaje
- `recaptcha_token` (string, opcional): Token de Google reCAPTCHA v3 para verificación anti-spam

**Validaciones:**

- Al menos uno de `correo_electronico` o `telefono` debe estar presente (no pueden estar ambos vacíos)
- `nombre` y `mensaje` son obligatorios y no pueden estar vacíos
- Si `RECAPTCHA_SECRET_KEY` está configurada en el servidor, el `recaptcha_token` es requerido
- El token debe ser válido y tener un score >= 0.5

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

**Otros errores posibles:**

```json
{
  "detail": "Token de reCAPTCHA requerido pero no proporcionado"
}
```

```json
{
  "detail": "reCAPTCHA inválido. Por favor intenta nuevamente."
}
```

```json
{
  "detail": "Verificación de seguridad fallida. Por favor intenta nuevamente o contacta al administrador."
}
```

#### Response Error (500 Internal Server Error)

```json
{
  "detail": "No se pudo enviar el mensaje de contacto. Por favor intente más tarde."
}
```

#### Response Error (503 Service Unavailable)

```json
{
  "detail": "El servicio de contacto no está configurado. Por favor contacte al administrador."
}
```

## Configuración

### Variables de Entorno

Para que el endpoint funcione correctamente, debes configurar las siguientes variables de entorno en tu archivo `.env`:

```bash
# Email donde se reciben los mensajes de contacto
CONTACT_EMAIL=contacto@geminislabs.com

# Google reCAPTCHA v3 - Secret key (opcional pero recomendado)
RECAPTCHA_SECRET_KEY=6Lxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

- `CONTACT_EMAIL`: Dirección de correo que recibirá todos los mensajes de contacto enviados desde el formulario
- `RECAPTCHA_SECRET_KEY`: Secret key de Google reCAPTCHA v3 para protección anti-spam (opcional, pero **muy recomendado** en producción)

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

## Google reCAPTCHA v3

### ¿Qué es reCAPTCHA v3?

Este endpoint está protegido con Google reCAPTCHA v3 para prevenir spam y bots. A diferencia de reCAPTCHA v2, **no requiere interacción del usuario** (no hay checkbox ni desafíos).

reCAPTCHA v3 analiza el comportamiento del usuario y asigna un **score** de 0.0 a 1.0:
- **1.0**: Muy probablemente humano
- **0.5**: Umbral requerido
- **0.0**: Muy probablemente bot

### ¿Cómo obtener el token?

**Para React/Next.js:**

1. Instalar la librería:
```bash
npm install react-google-recaptcha-v3
```

2. Configurar el Provider:
```tsx
import { GoogleReCaptchaProvider } from 'react-google-recaptcha-v3';

<GoogleReCaptchaProvider reCaptchaKey="TU_SITE_KEY_PUBLICA">
  <App />
</GoogleReCaptchaProvider>
```

3. Generar el token en tu formulario:
```tsx
import { useGoogleReCaptcha } from 'react-google-recaptcha-v3';

function ContactForm() {
  const { executeRecaptcha } = useGoogleReCaptcha();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Generar token
    const recaptchaToken = await executeRecaptcha('contact_form');
    
    // Enviar con el token
    const response = await fetch('/api/v1/contact/send-message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nombre: formData.nombre,
        correo_electronico: formData.email,
        telefono: formData.telefono,
        mensaje: formData.mensaje,
        recaptcha_token: recaptchaToken, // ← Token de reCAPTCHA
      }),
    });
  };
}
```

**Para JavaScript Vanilla:**

```html
<script src="https://www.google.com/recaptcha/api.js?render=TU_SITE_KEY_PUBLICA"></script>

<script>
function handleSubmit() {
  grecaptcha.ready(function() {
    grecaptcha.execute('TU_SITE_KEY_PUBLICA', {action: 'contact_form'})
      .then(function(token) {
        // Enviar con el token
        fetch('/api/v1/contact/send-message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            nombre: '...',
            correo_electronico: '...',
            mensaje: '...',
            recaptcha_token: token
          })
        });
      });
  });
}
</script>
```

### Modo Desarrollo

Si `RECAPTCHA_SECRET_KEY` **NO** está configurada en el servidor, el endpoint funcionará sin validar reCAPTCHA (solo para desarrollo/testing). En producción, **siempre debes configurar** esta variable.

## Ejemplo de Uso

### cURL

**Con reCAPTCHA:**

```bash
curl -X POST "https://api.tudominio.com/api/v1/contact/send-message" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan Pérez",
    "correo_electronico": "juan@example.com",
    "telefono": "+52 123 456 7890",
    "mensaje": "Estoy interesado en sus servicios de monitoreo vehicular",
    "recaptcha_token": "03AGdBq24PBCd9QF..."
  }'
```

**Sin reCAPTCHA (solo si el servidor no tiene RECAPTCHA_SECRET_KEY configurada):**

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

### JavaScript (Fetch con reCAPTCHA)

```javascript
// Generar token de reCAPTCHA
grecaptcha.ready(function() {
  grecaptcha.execute('TU_SITE_KEY_PUBLICA', {action: 'contact_form'})
    .then(async function(recaptchaToken) {
      // Enviar formulario con el token
      const response = await fetch('https://api.tudominio.com/api/v1/contact/send-message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          nombre: 'Juan Pérez',
          correo_electronico: 'juan@example.com',
          telefono: '+52 123 456 7890',
          mensaje: 'Estoy interesado en sus servicios de monitoreo vehicular',
          recaptcha_token: recaptchaToken
        })
      });

      const data = await response.json();
      
      if (data.success) {
        console.log('✅ Mensaje enviado:', data.message);
      } else {
        console.error('❌ Error:', data.detail);
      }
    });
});
```

### Python (requests con reCAPTCHA)

```python
import requests

url = "https://api.tudominio.com/api/v1/contact/send-message"

# Nota: El token de reCAPTCHA debe ser generado desde el frontend
# Este es solo un ejemplo de cómo enviar el request
payload = {
    "nombre": "Juan Pérez",
    "correo_electronico": "juan@example.com",
    "telefono": "+52 123 456 7890",
    "mensaje": "Estoy interesado en sus servicios de monitoreo vehicular",
    "recaptcha_token": "03AGdBq24PBCd9QF..."  # Token del frontend
}

response = requests.post(url, json=payload)
data = response.json()

if response.status_code == 200:
    print("✅ Éxito:", data['message'])
else:
    print("❌ Error:", data['detail'])
```

## Medidas de Seguridad

### 🛡️ Protecciones Implementadas

1. **Google reCAPTCHA v3**: Protección anti-spam basada en análisis de comportamiento (sin interacción del usuario)
2. **Limitación de tamaño del body**: Máximo 50KB para prevenir ataques DoS
3. **Sanitización de HTML**: Todos los campos de texto son escapados para prevenir XSS
4. **Validación de campos**: 
   - Nombre: Máximo 200 caracteres
   - Mensaje: Máximo 5000 caracteres
   - Teléfono: Solo caracteres válidos (números, +, -, paréntesis)
   - Email: Validación de formato estricta

### ⚠️ Notas Importantes

- Este endpoint **NO requiere autenticación** ya que es público para uso desde el formulario de contacto del sitio web
- **Recomendación**: Siempre incluye el `recaptcha_token` en producción para evitar spam
- Se recomienda implementar rate limiting adicional en el servidor web (nginx/apache) para mayor protección
- En desarrollo, el endpoint funciona sin reCAPTCHA si no está configurado `RECAPTCHA_SECRET_KEY`

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
2. ✅ Variable `RECAPTCHA_SECRET_KEY` configurada (opcional pero recomendado)
3. ✅ Email verificado en AWS SES
4. ✅ Permisos IAM correctos para SES
5. ✅ Revisar logs de la aplicación
6. ✅ Revisar carpeta de spam
7. ✅ Verificar métricas de SES en AWS Console

### Error: "Token de reCAPTCHA requerido"

**Causa**: El servidor tiene `RECAPTCHA_SECRET_KEY` configurada pero no se envió el token

**Solución**: 
1. Verifica que el frontend esté generando el token de reCAPTCHA
2. Verifica que el token se esté enviando en el campo `recaptcha_token`
3. Usa las herramientas de desarrollo del navegador para inspeccionar el request

### Error: "reCAPTCHA inválido"

**Causa**: El token es inválido, expiró o tiene un score bajo

**Solución**:
1. Los tokens expiran después de ~2 minutos - genera un nuevo token para cada envío
2. No reutilices tokens entre diferentes formularios
3. Verifica que la Site Key del frontend coincida con la Secret Key del backend
4. Si el score es bajo (<0.5), puede ser que el usuario esté usando herramientas automatizadas

### Error: "Verificación de seguridad fallida"

**Causa**: El score de reCAPTCHA es menor a 0.5 (posible bot)

**Solución**:
1. Intenta desde un navegador diferente
2. Asegúrate de que JavaScript esté habilitado
3. No uses herramientas de automatización (Selenium, Puppeteer) sin configuración especial
4. Contacta al administrador si el problema persiste

## Referencias

- [Documentación completa de reCAPTCHA](../guides/recaptcha-setup.md)
- [Documentación de seguridad del endpoint](../security/contact-endpoint-security.md)
- [Google reCAPTCHA v3](https://developers.google.com/recaptcha/docs/v3)

