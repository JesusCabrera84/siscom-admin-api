# Configuración de Google reCAPTCHA v3

Esta guía te ayudará a configurar Google reCAPTCHA v3 para proteger el endpoint de contacto contra bots y spam.

## 📋 ¿Qué es reCAPTCHA v3?

reCAPTCHA v3 es una tecnología de Google que analiza el comportamiento del usuario en tu sitio web y asigna un **score** (puntuación) de 0.0 a 1.0:

- **1.0**: Muy probablemente humano
- **0.5**: Neutro (umbral recomendado)
- **0.0**: Muy probablemente bot

A diferencia de reCAPTCHA v2, **no requiere interacción del usuario** (no hay checkbox ni desafíos).

## 🚀 Pasos para Configurar

### 1. Obtener las Claves de reCAPTCHA

1. Ve a [Google reCAPTCHA Admin Console](https://www.google.com/recaptcha/admin/create)
2. Inicia sesión con tu cuenta de Google
3. Completa el formulario:

```
Label: SISCOM Contact Form
reCAPTCHA type: reCAPTCHA v3
Domains: 
  - localhost (para desarrollo)
  - tudominio.com (para producción)
  
Accept reCAPTCHA Terms of Service: ✓
```

4. Haz clic en **Submit**
5. Guarda ambas claves:
   - **Site Key** (pública - va en el frontend)
   - **Secret Key** (privada - va en el backend)

### 2. Configurar el Backend

#### Desarrollo Local

Agrega la clave secreta a tu archivo `.env`:

```bash
# Google reCAPTCHA v3 - Secret key para validación de formularios
RECAPTCHA_SECRET_KEY=6LexampleSecretKeyxxxxxxxxxxxxxxxxxxxxxx
```

**Nota**: Si no configuras esta variable, el backend **NO validará** reCAPTCHA (solo en desarrollo).

#### Producción - GitHub Actions

1. Ve a tu repositorio en GitHub
2. Navega a: **Settings** → **Secrets and variables** → **Actions**
3. En la pestaña **Secrets**, haz clic en **New repository secret**
4. Completa:
   - **Name**: `RECAPTCHA_SECRET_KEY`
   - **Value**: `6LexampleSecretKeyxxxxxxxxxxxxxxxxxxxxxx`
5. Haz clic en **Add secret**

#### Docker y Docker Compose

Ya está configurado en:
- ✅ `docker-compose.yml` - Para desarrollo
- ✅ `docker-compose.prod.yml` - Para producción
- ✅ `.github/workflows/deploy.yml` - Para CI/CD
- ✅ `.github/workflows/ci.yml` - Para tests

### 3. Configurar el Frontend

#### Instalar reCAPTCHA en React/Next.js

```bash
npm install react-google-recaptcha-v3
# o
yarn add react-google-recaptcha-v3
```

#### Configurar el Provider

```tsx
// _app.tsx o layout.tsx
import { GoogleReCaptchaProvider } from 'react-google-recaptcha-v3';

function MyApp({ Component, pageProps }) {
  return (
    <GoogleReCaptchaProvider
      reCaptchaKey="6LexampleSiteKeyxxxxxxxxxxxxxxxxxxxxxx"
      language="es"
    >
      <Component {...pageProps} />
    </GoogleReCaptchaProvider>
  );
}
```

#### Usar en el Formulario de Contacto

```tsx
import { useGoogleReCaptcha } from 'react-google-recaptcha-v3';

function ContactForm() {
  const { executeRecaptcha } = useGoogleReCaptcha();

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Obtener token de reCAPTCHA
    if (!executeRecaptcha) {
      console.error('reCAPTCHA no disponible');
      return;
    }

    const recaptchaToken = await executeRecaptcha('contact_form');

    // Enviar formulario con el token
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

    const data = await response.json();
    
    if (response.ok) {
      // Éxito
      console.log('Mensaje enviado:', data);
    } else {
      // Error (puede ser por reCAPTCHA)
      console.error('Error:', data.detail);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Tus campos del formulario */}
      <button type="submit">Enviar</button>
    </form>
  );
}
```

#### JavaScript Vanilla (sin framework)

```html
<!-- Cargar el script de reCAPTCHA -->
<script src="https://www.google.com/recaptcha/api.js?render=6LexampleSiteKeyxxxxxxxxxxxxxxxxxxxxxx"></script>

<script>
function handleSubmit(event) {
  event.preventDefault();
  
  grecaptcha.ready(function() {
    grecaptcha.execute('6LexampleSiteKeyxxxxxxxxxxxxxxxxxxxxxx', {action: 'contact_form'})
      .then(function(token) {
        // Agregar el token al formulario
        const formData = {
          nombre: document.getElementById('nombre').value,
          correo_electronico: document.getElementById('email').value,
          telefono: document.getElementById('telefono').value,
          mensaje: document.getElementById('mensaje').value,
          recaptcha_token: token
        };
        
        // Enviar el formulario
        fetch('/api/v1/contact/send-message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            alert('Mensaje enviado!');
          } else {
            alert('Error: ' + data.detail);
          }
        });
      });
  });
}
</script>
```

## 🔍 Cómo Funciona

### Flujo de Verificación

```
┌─────────┐           ┌─────────┐           ┌─────────┐
│ Usuario │           │ Backend │           │ Google  │
└────┬────┘           └────┬────┘           └────┬────┘
     │                     │                     │
     │ 1. Submit form      │                     │
     ├────────────────────>│                     │
     │                     │                     │
     │                     │ 2. Verify token     │
     │                     ├────────────────────>│
     │                     │                     │
     │                     │ 3. Return score     │
     │                     │<────────────────────┤
     │                     │                     │
     │                     │ 4. Check score >= 0.5
     │                     │                     │
     │ 5. Success/Error    │                     │
     │<────────────────────┤                     │
```

### Validación en el Backend

El backend verifica el token con Google y comprueba:

1. ✅ **success**: ¿Es válido el token?
2. ✅ **score**: ¿Es >= 0.5? (configurable)
3. ✅ **action**: ¿Coincide con la acción esperada?

```python
# app/utils/recaptcha.py
async def verify_recaptcha(token: str, min_score: float = 0.5) -> dict:
    # Envía el token a Google
    response = await client.post(
        "https://www.google.com/recaptcha/api/siteverify",
        data={"secret": RECAPTCHA_SECRET_KEY, "response": token}
    )
    
    data = response.json()
    
    # Verifica el score
    if data.get("score", 0.0) < min_score:
        raise HTTPException(status_code=400, detail="Score bajo - posible bot")
    
    return data
```

## 🧪 Probar la Configuración

### Test 1: Sin token (debería fallar)

```bash
curl -X POST "http://localhost:8000/api/v1/contact/send-message" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Test",
    "correo_electronico": "test@test.com",
    "mensaje": "Test sin reCAPTCHA"
  }'
```

**Respuesta esperada** (si RECAPTCHA_SECRET_KEY está configurada):
```json
{
  "detail": "Token de reCAPTCHA requerido pero no proporcionado"
}
```

### Test 2: Con token válido (debería funcionar)

```bash
# Primero obtén un token desde el frontend
# Luego envíalo:
curl -X POST "http://localhost:8000/api/v1/contact/send-message" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Test",
    "correo_electronico": "test@test.com",
    "mensaje": "Test con reCAPTCHA",
    "recaptcha_token": "03AGdBq24..."
  }'
```

**Respuesta esperada**:
```json
{
  "success": true,
  "message": "Mensaje de contacto enviado exitosamente..."
}
```

### Test 3: Modo desarrollo (sin RECAPTCHA_SECRET_KEY)

Si no configuras `RECAPTCHA_SECRET_KEY`, el backend **saltará** la validación:

```bash
# Sin configurar RECAPTCHA_SECRET_KEY en .env
curl -X POST "http://localhost:8000/api/v1/contact/send-message" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Test",
    "correo_electronico": "test@test.com",
    "mensaje": "Test"
  }'
```

**Log del servidor**:
```
[WARNING] RECAPTCHA_SECRET_KEY no configurada. Saltando validación de reCAPTCHA.
```

## ⚙️ Configuración Avanzada

### Cambiar el Score Mínimo

Edita `app/api/v1/endpoints/contact.py`:

```python
# Score más estricto (menos tolerante)
await verify_recaptcha(message.recaptcha_token, min_score=0.7)

# Score más permisivo (más tolerante)
await verify_recaptcha(message.recaptcha_token, min_score=0.3)
```

**Recomendaciones**:
- **0.7-1.0**: Muy estricto - puede bloquear usuarios legítimos
- **0.5**: Recomendado - balance entre seguridad y usabilidad
- **0.0-0.4**: Muy permisivo - puede dejar pasar algunos bots

### Diferentes Scores por Acción

```python
# En contact.py
if is_high_risk_form:
    await verify_recaptcha(token, min_score=0.7)  # Más estricto
else:
    await verify_recaptcha(token, min_score=0.5)  # Normal
```

### Logs Detallados

Los logs del servidor muestran información útil:

```
[RECAPTCHA] Verificación: success=True, score=0.9, action=contact_form
[RECAPTCHA] Score bajo: 0.3 < 0.5. Posible bot detectado.
[RECAPTCHA ERROR] Timeout al conectar con Google reCAPTCHA
```

## 📊 Monitoreo en Google

1. Ve a [reCAPTCHA Admin Console](https://www.google.com/recaptcha/admin)
2. Selecciona tu sitio
3. Revisa las métricas:
   - Requests por día
   - Distribución de scores
   - Acciones detectadas

## 🔒 Seguridad

### ✅ Buenas Prácticas

1. **Nunca expongas la Secret Key** en el frontend
2. **Usa HTTPS** en producción
3. **Configura dominios específicos** en reCAPTCHA Admin
4. **Monitorea los scores** y ajusta el umbral si es necesario
5. **Combina con otras protecciones**:
   - Rate limiting
   - Sanitización de input
   - Validación de campos

### ⚠️ Limitaciones

- reCAPTCHA v3 **no es infalible** - bots avanzados pueden evadir
- Usuarios con JavaScript deshabilitado no podrán enviar el formulario
- Requiere conexión a servicios de Google

## 🐛 Troubleshooting

### Error: "Token de reCAPTCHA requerido pero no proporcionado"

**Causa**: El frontend no está enviando el token

**Solución**:
1. Verifica que el frontend esté generando el token
2. Verifica que el campo `recaptcha_token` esté en el request body
3. Usa las herramientas de desarrollo del navegador para inspeccionar el request

### Error: "reCAPTCHA inválido"

**Causa**: El token es inválido o ya expiró (tokens duran ~2 minutos)

**Solución**:
1. Genera un nuevo token para cada submit
2. No reutilices tokens
3. Verifica que la Secret Key sea correcta

### Error: "Score bajo - posible bot"

**Causa**: El score es menor al umbral (0.5)

**Solución**:
1. Verifica que estés en un navegador real (no curl o Postman sin configurar)
2. Intenta con un navegador diferente
3. Revisa los logs del servidor para ver el score exacto
4. Considera bajar el umbral temporalmente para testing

### Warning: "RECAPTCHA_SECRET_KEY no configurada"

**Causa**: La variable de entorno no está configurada

**Solución**:
- **Desarrollo**: Agrega `RECAPTCHA_SECRET_KEY` al `.env`
- **Producción**: Agrega como secret en GitHub Actions

### Error: "Timeout al conectar con Google reCAPTCHA"

**Causa**: Problema de red o Google reCAPTCHA está caído

**Solución**:
1. Verifica tu conexión a internet
2. Verifica el status de Google reCAPTCHA
3. Aumenta el timeout en `app/utils/recaptcha.py` si es necesario

## 📚 Referencias

- [Google reCAPTCHA v3 Documentation](https://developers.google.com/recaptcha/docs/v3)
- [reCAPTCHA Admin Console](https://www.google.com/recaptcha/admin)
- [React reCAPTCHA v3 Library](https://www.npmjs.com/package/react-google-recaptcha-v3)
- [reCAPTCHA Best Practices](https://developers.google.com/recaptcha/docs/faq)

## ✅ Checklist de Configuración

### Backend

- [ ] `RECAPTCHA_SECRET_KEY` agregada al `.env`
- [ ] Variable agregada como secret en GitHub Actions
- [ ] Variables en docker-compose.yml y docker-compose.prod.yml
- [ ] Servidor reiniciado después de cambios

### Frontend

- [ ] reCAPTCHA library instalada
- [ ] Site Key configurada en el provider
- [ ] Token generado en el submit
- [ ] Token enviado en el request body como `recaptcha_token`

### Testing

- [ ] Formulario funciona sin reCAPTCHA (modo desarrollo)
- [ ] Formulario funciona con reCAPTCHA válido
- [ ] Formulario rechaza tokens inválidos o ausentes
- [ ] Logs del servidor muestran información correcta

---

**Última actualización**: 2025-11-20  
**Estado**: ✅ Implementado y documentado

