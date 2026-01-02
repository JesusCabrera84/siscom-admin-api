# Módulo: Contact

## 📌 Descripción

Formulario de contacto público del sitio web.
Permite a visitantes enviar mensajes de contacto que se reenvían al email configurado.

---

## 👤 Actor

- Visitante anónimo (usuario no autenticado)

---

## 🔌 APIs Consumidas

### 🔹 Google reCAPTCHA v3 (Security)

| Endpoint | Método | Uso |
|----------|--------|-----|
| `https://www.google.com/recaptcha/api/siteverify` | POST | Verificar token de reCAPTCHA |

**Request:**
```
POST https://www.google.com/recaptcha/api/siteverify
Content-Type: application/x-www-form-urlencoded

secret={RECAPTCHA_SECRET_KEY}
response={token_del_frontend}
```

**Response:**
```json
{
  "success": true,
  "score": 0.9,
  "action": "submit",
  "challenge_ts": "2025-12-29T00:00:00Z",
  "hostname": "siscom.com"
}
```

**Configuración requerida:**
- `RECAPTCHA_SECRET_KEY`

**Score mínimo:** 0.5 (configurable)

---

### 🔹 AWS SES (Email Service)

| Template | Uso |
|----------|-----|
| `contact_message.html` | Formato del mensaje de contacto |

**Configuración requerida:**
- `SES_FROM_EMAIL` (remitente)
- `CONTACT_EMAIL` (destinatario)

---

## 🔁 Flujo funcional

### Enviar Mensaje (`POST /contact/send-message`)

```
1. Valida que CONTACT_EMAIL esté configurado
2. Verifica token reCAPTCHA v3:
   a. Envía token a Google
   b. Verifica success=true
   c. Verifica score >= 0.5
   d. Si falla, rechaza la solicitud
3. Envía email via SES:
   a. Renderiza template con datos del mensaje
   b. Envía a CONTACT_EMAIL
4. Retorna confirmación de envío
```

---

## ⚠️ Consideraciones

- Este endpoint es **público** (no requiere autenticación)
- reCAPTCHA es **obligatorio** en producción
- Si `RECAPTCHA_SECRET_KEY` no está configurado, se salta la validación (solo desarrollo)
- El endpoint requiere al menos `correo_electronico` o `telefono`
- Los errores de reCAPTCHA se logean pero no exponen detalles al cliente
- El timeout de reCAPTCHA es de 10 segundos

---

## 🛡️ Protección contra Bots

### Niveles de Score reCAPTCHA v3

| Score | Interpretación | Acción |
|-------|----------------|--------|
| 0.9+ | Muy probablemente humano | ✅ Permitir |
| 0.7-0.9 | Probablemente humano | ✅ Permitir |
| 0.5-0.7 | Sospechoso | ✅ Permitir (límite) |
| < 0.5 | Probablemente bot | ❌ Rechazar |

---

## 📊 Estructura de Request

```json
{
  "nombre": "Juan Pérez",
  "correo_electronico": "juan@ejemplo.com",
  "telefono": "+52 555 123 4567",
  "mensaje": "Contenido del mensaje de contacto",
  "recaptcha_token": "token_de_recaptcha_v3"
}
```

**Validaciones:**
- `nombre`: Requerido
- `correo_electronico`: Opcional (requerido si no hay teléfono)
- `telefono`: Opcional (requerido si no hay email)
- `mensaje`: Requerido
- `recaptcha_token`: Requerido en producción

---

## 📧 Template de Email

El email enviado incluye:
- Nombre del remitente
- Email de contacto (si se proporcionó)
- Teléfono de contacto (si se proporcionó)
- Contenido del mensaje
- Año actual (para el footer)

**Subject:** `Nuevo mensaje de contacto desde la página web - {nombre}`

---

## 🔐 Seguridad

| Medida | Descripción |
|--------|-------------|
| reCAPTCHA v3 | Protección contra bots automáticos |
| Score mínimo | Umbral de 0.5 para detección de bots |
| Rate limiting | (Pendiente) Limitar solicitudes por IP |
| Validación de email | Formato válido si se proporciona |

---

## 🧭 Relación C4 (preview)

- **Container:** SISCOM Admin API (FastAPI)
- **Consumes:** Google reCAPTCHA API, AWS SES
- **Consumed by:** Landing Page (sitio web público)


