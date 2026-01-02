# Módulo: Users

## 📌 Descripción

Gestión de usuarios de la organización.
Permite listar usuarios, obtener perfil, invitar nuevos usuarios y gestionar invitaciones.

---

## 👤 Actor

- Usuario autenticado (listar, perfil)
- Usuario maestro (invitar, reenviar invitación)
- Usuario invitado (aceptar invitación)

---

## 🔌 APIs Consumidas

### 🔹 AWS Cognito (Identity Provider)

| Endpoint/Operación | Método | Uso |
|-------------------|--------|-----|
| `AdminCreateUser` | POST | Crear usuario al aceptar invitación |
| `AdminSetUserPassword` | POST | Establecer contraseña del nuevo usuario |
| `AdminGetUser` | POST | Verificar si usuario existe |
| `AdminUpdateUserAttributes` | POST | Marcar email como verificado |

**Configuración requerida:**
- `COGNITO_REGION`
- `COGNITO_USER_POOL_ID`

---

### 🔹 AWS SES (Email Service)

| Template | Uso |
|----------|-----|
| `invitation.html` | Envío de invitación a nuevos usuarios |

**Configuración requerida:**
- `SES_FROM_EMAIL`
- `FRONTEND_URL` (para construir URL de invitación)

---

### 🔹 PostgreSQL (Base de datos)

| Tabla | Operación | Uso |
|-------|-----------|-----|
| `users` | SELECT | Listar usuarios, verificar existencia |
| `users` | INSERT | Crear usuario al aceptar invitación |
| `tokens_confirmacion` | INSERT | Crear token de invitación |
| `tokens_confirmacion` | SELECT | Validar token de invitación |
| `tokens_confirmacion` | UPDATE | Marcar invitación como usada |

---

## 🔁 Flujo funcional

### Listar Usuarios (`GET /users`)

```
1. Obtiene organization_id del token Cognito
2. Consulta usuarios de la organización
3. Retorna lista de usuarios
```

### Obtener Perfil (`GET /users/me`)

```
1. Obtiene cognito_sub del token
2. Busca usuario en BD
3. Retorna información del usuario
```

### Invitar Usuario (`POST /users/invite`)

```
1. Verifica que el usuario autenticado sea maestro (is_master=True)
2. Verifica que el email no esté registrado
3. Verifica que no exista invitación pendiente
4. Genera token de invitación (UUID)
5. Guarda en tokens_confirmacion (tipo: INVITATION, expira en 3 días)
6. Envía email de invitación via SES
7. Retorna confirmación con fecha de expiración
```

### Aceptar Invitación (`POST /users/accept-invitation`)

```
1. Busca y valida token de invitación
2. Verifica que no esté usado ni expirado
3. Extrae email, full_name y organization_id del token
4. Verifica que el usuario no exista en BD
5. Verifica/crea usuario en Cognito
6. Establece contraseña proporcionada
7. Crea registro de usuario en BD
8. Marca token como usado
9. Retorna información del usuario creado
```

### Reenviar Invitación (`POST /users/resend-invitation`)

```
1. Verifica que el usuario autenticado sea maestro
2. Verifica que el email NO esté registrado
3. Busca invitaciones existentes (incluyendo expiradas)
4. Obtiene datos de la invitación original (full_name)
5. Invalida invitaciones anteriores
6. Genera nueva invitación con nueva expiración
7. Envía email con nuevo link
8. Retorna confirmación con nueva fecha de expiración
```

---

## ⚠️ Consideraciones

- Solo usuarios maestros (`is_master=True`) pueden enviar invitaciones
- Las invitaciones expiran en 3 días
- Un email no puede tener múltiples invitaciones pendientes
- Al aceptar invitación, el usuario se crea con `is_master=False`
- El email se marca como verificado automáticamente al aceptar
- El `organization_id` se hereda del token de invitación
- Si el usuario ya existe en Cognito, solo se actualiza la contraseña

---

## 🔐 Permisos

| Endpoint | Requiere Auth | Rol Requerido |
|----------|---------------|---------------|
| `GET /users` | ✅ | Cualquier usuario autenticado |
| `GET /users/me` | ✅ | Cualquier usuario autenticado |
| `POST /users/invite` | ✅ | Solo maestro (`is_master=True`) |
| `POST /users/accept-invitation` | ❌ | Ninguno (endpoint público) |
| `POST /users/resend-invitation` | ✅ | Solo maestro (`is_master=True`) |

---

## 📊 Estructura de Token de Invitación

```json
{
  "token": "uuid-v4",
  "type": "INVITATION",
  "organization_id": "uuid",
  "email": "invitado@ejemplo.com",
  "full_name": "Nombre del Invitado",
  "expires_at": "2025-01-02T00:00:00Z",
  "used": false,
  "user_id": null  // Se asigna al aceptar
}
```

---

## 🧭 Relación C4 (preview)

- **Container:** SISCOM Admin API (FastAPI)
- **Consumes:** AWS Cognito, AWS SES, PostgreSQL
- **Consumed by:** Web App (panel de administración)


