# Seguridad del Endpoint de Contacto

## 🔒 Medidas de Seguridad Implementadas

El endpoint `/api/v1/contact/send-message` tiene implementadas múltiples capas de seguridad para prevenir ataques comunes.

## 🛡️ Protecciones Implementadas

### 1. Limitación del Tamaño del Body (DoS Prevention)

**Ubicación**: `app/main.py` - Middleware global

```python
@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    max_body_size = 50000  # 50KB
    if content_length > max_body_size:
        return Response(status_code=413)
```

**Protege contra**:
- ✅ Ataques de denegación de servicio (DoS)
- ✅ Payloads excesivamente grandes
- ✅ Abuso del endpoint

**Límite**: 50KB (50,000 bytes)

**Respuesta si se excede**:
```http
HTTP/1.1 413 Payload Too Large
Content-Type: text/plain

Payload demasiado grande. Máximo permitido: 50KB
```

### 2. Sanitización de HTML/Scripts (XSS Prevention)

**Ubicación**: `app/utils/validators.py`

Todas las entradas de texto son sanitizadas usando `html.escape()` para prevenir ataques de Cross-Site Scripting (XSS).

#### Función `sanitize_html()`

```python
def sanitize_html(text: str, max_length: int = 5000) -> str:
    """Sanitiza texto escapando HTML y scripts"""
    sanitized = html.escape(text)
    return sanitized
```

**Convierte**:
```python
"<script>alert('XSS')</script>" 
# → 
"&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;"
```

**Protege contra**:
- ✅ Cross-Site Scripting (XSS)
- ✅ Inyección de HTML
- ✅ Inyección de JavaScript
- ✅ Ataques de phishing en emails

### 3. Validación y Sanitización de Campos

**Ubicación**: `app/schemas/contact.py`

Cada campo tiene validaciones específicas:

#### Campo `nombre` (máx 200 caracteres)
```python
@field_validator("nombre")
def validate_nombre(cls, v: str) -> str:
    return sanitize_contact_field(v, "nombre", max_length=200)
```

**Valida**:
- ✅ No puede estar vacío
- ✅ Máximo 200 caracteres
- ✅ HTML escapado

#### Campo `mensaje` (máx 5000 caracteres)
```python
@field_validator("mensaje")
def validate_mensaje(cls, v: str) -> str:
    return sanitize_html(v, max_length=5000)
```

**Valida**:
- ✅ No puede estar vacío
- ✅ Máximo 5000 caracteres
- ✅ HTML escapado

#### Campo `telefono` (validación de formato)
```python
@field_validator("telefono")
def validate_telefono(cls, v: Optional[str]) -> Optional[str]:
    return validate_phone(v)
```

**Valida**:
- ✅ Solo caracteres permitidos: `0-9`, `+`, `-`, `(`, `)`, espacios
- ✅ Mínimo 7 dígitos
- ✅ Máximo 20 dígitos
- ✅ HTML escapado

#### Campo `correo_electronico`
```python
correo_electronico: Optional[EmailStr] = None
```

**Valida**:
- ✅ Formato de email válido (Pydantic EmailStr)
- ✅ No requiere sanitización adicional (validado por Pydantic)

### 4. Validación de Campos Requeridos

```python
def model_post_init(self, __context) -> None:
    if not self.correo_electronico and not self.telefono:
        raise ValueError("Debe proporcionar al menos un correo electrónico o un teléfono")
```

**Valida**:
- ✅ Al menos `correo_electronico` o `telefono` deben estar presentes

## 🧪 Ejemplos de Protección

### Ejemplo 1: Intento de XSS en el nombre

**Request**:
```json
{
  "nombre": "<script>alert('hack')</script>",
  "correo_electronico": "test@test.com",
  "mensaje": "Hola"
}
```

**Procesado internamente**:
```python
nombre = "&lt;script&gt;alert(&#x27;hack&#x27;)&lt;/script&gt;"
```

**Email recibido**: El script aparece como texto plano inofensivo

### Ejemplo 2: Intento de XSS en el mensaje

**Request**:
```json
{
  "nombre": "Juan",
  "correo_electronico": "test@test.com",
  "mensaje": "<img src=x onerror='alert(1)'>"
}
```

**Procesado**:
```python
mensaje = "&lt;img src=x onerror=&#x27;alert(1)&#x27;&gt;"
```

**Resultado**: El código malicioso es neutralizado

### Ejemplo 3: Payload demasiado grande

**Request con body > 50KB**:
```http
POST /api/v1/contact/send-message
Content-Length: 60000

{...payload grande...}
```

**Response**:
```http
HTTP/1.1 413 Payload Too Large
Content-Type: text/plain

Payload demasiado grande. Máximo permitido: 50KB
```

### Ejemplo 4: Mensaje demasiado largo

**Request**:
```json
{
  "nombre": "Juan",
  "correo_electronico": "test@test.com",
  "mensaje": "texto muy largo..." // > 5000 caracteres
}
```

**Response**:
```http
HTTP/1.1 422 Unprocessable Entity

{
  "detail": [
    {
      "type": "value_error",
      "msg": "El texto no puede exceder 5000 caracteres"
    }
  ]
}
```

### Ejemplo 5: Teléfono con caracteres inválidos

**Request**:
```json
{
  "nombre": "Juan",
  "telefono": "+52 123-456-7890; DROP TABLE users;",
  "mensaje": "Hola"
}
```

**Response**:
```http
HTTP/1.1 422 Unprocessable Entity

{
  "detail": [
    {
      "type": "value_error",
      "msg": "El teléfono solo puede contener números, espacios, +, -, ( y )"
    }
  ]
}
```

## 📊 Límites Configurados

| Campo | Límite | Validación |
|-------|--------|------------|
| Body completo | 50KB | Middleware global |
| `nombre` | 200 caracteres | Schema validator |
| `mensaje` | 5000 caracteres | Schema validator |
| `telefono` (dígitos) | 7-20 dígitos | Regex validator |
| `correo_electronico` | N/A | EmailStr de Pydantic |

## 🔍 Cómo Funciona `html.escape()`

La función `html.escape()` convierte caracteres especiales de HTML en sus entidades HTML correspondientes:

| Carácter | Entidad HTML | Descripción |
|----------|--------------|-------------|
| `<` | `&lt;` | Menor que |
| `>` | `&gt;` | Mayor que |
| `&` | `&amp;` | Ampersand |
| `"` | `&quot;` | Comillas dobles |
| `'` | `&#x27;` | Comilla simple |

### Antes de sanitizar:
```html
<script>alert('XSS')</script>
<img src=x onerror='alert(1)'>
<iframe src="evil.com"></iframe>
```

### Después de sanitizar:
```html
&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;
&lt;img src=x onerror=&#x27;alert(1)&#x27;&gt;
&lt;iframe src=&quot;evil.com&quot;&gt;&lt;/iframe&gt;
```

## 🧪 Probar las Validaciones

### Test 1: XSS en nombre
```bash
curl -X POST "http://localhost:8000/api/v1/contact/send-message" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "<script>alert(\"XSS\")</script>",
    "correo_electronico": "test@test.com",
    "mensaje": "Test"
  }'
```

**Resultado**: ✅ Acepta la petición pero sanitiza el HTML

### Test 2: Payload grande
```bash
curl -X POST "http://localhost:8000/api/v1/contact/send-message" \
  -H "Content-Type: application/json" \
  -H "Content-Length: 60000" \
  -d @large-payload.json
```

**Resultado**: ❌ 413 Payload Too Large

### Test 3: Mensaje muy largo
```bash
curl -X POST "http://localhost:8000/api/v1/contact/send-message" \
  -H "Content-Type: application/json" \
  -d "{
    \"nombre\": \"Test\",
    \"correo_electronico\": \"test@test.com\",
    \"mensaje\": \"$(python -c 'print(\"A\" * 6000)')\"
  }"
```

**Resultado**: ❌ 422 Unprocessable Entity (excede 5000 caracteres)

### Test 4: Teléfono inválido
```bash
curl -X POST "http://localhost:8000/api/v1/contact/send-message" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Test",
    "telefono": "123; DROP TABLE;",
    "mensaje": "Test"
  }'
```

**Resultado**: ❌ 422 Unprocessable Entity (caracteres inválidos)

## 🛠️ Configuración

### Cambiar el límite del body

Edita `app/main.py`:

```python
@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    max_body_size = 100000  # Cambiar a 100KB
    # ...
```

### Cambiar límites de campos

Edita `app/schemas/contact.py`:

```python
# Nombre más largo
sanitize_contact_field(v, "nombre", max_length=500)

# Mensaje más largo
sanitize_html(v, max_length=10000)
```

## 📚 Referencias

- [OWASP - Cross Site Scripting (XSS)](https://owasp.org/www-community/attacks/xss/)
- [OWASP - Input Validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [Python html.escape() documentation](https://docs.python.org/3/library/html.html#html.escape)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)

## ✅ Checklist de Seguridad

- [x] Limitación de tamaño del body (50KB)
- [x] Sanitización de HTML en todos los campos de texto
- [x] Validación de formato de email
- [x] Validación de formato de teléfono
- [x] Validación de longitud máxima por campo
- [x] Prevención de XSS
- [x] Prevención de inyección de HTML
- [x] Prevención de DoS por payload grande
- [x] Mensajes de error informativos pero no reveladores

## 🔐 Recomendaciones Adicionales

### 1. Rate Limiting (Próximamente)

Considera agregar rate limiting a nivel de nginx o usando `slowapi`:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/contact/send-message")
@limiter.limit("5/minute")  # Máximo 5 peticiones por minuto
async def send_contact_message(request: Request, message: ContactMessageCreate):
    ...
```

### 2. CAPTCHA

Para producción, considera agregar Google reCAPTCHA o similar en el frontend.

### 3. Honeypot Fields

Agrega campos ocultos que los bots llenarán pero los humanos no:

```python
class ContactMessageCreate(BaseModel):
    # Campo honeypot - debe estar vacío
    website: Optional[str] = None
    
    def model_post_init(self, __context) -> None:
        if self.website:
            raise ValueError("Spam detectado")
```

### 4. Logging de Intentos Sospechosos

Log requests con patrones sospechosos:

```python
if "<script>" in mensaje or "DROP TABLE" in mensaje:
    logger.warning(f"Intento de ataque detectado desde {request.client.host}")
```

---

**Última actualización**: 2025-11-20  
**Estado**: ✅ Implementado y probado

