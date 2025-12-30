# Module Dependency Documentation (C4-aligned)

Estos documentos describen qué APIs y recursos externos consume cada módulo de la aplicación y cómo interactúan en tiempo de ejecución.

Esta documentación soporta diagramas de contenedores y componentes C4.

---

## 📋 Índice de Módulos

| Módulo | Descripción | Dependencias Principales |
|--------|-------------|-------------------------|
| [auth](./auth.md) | Autenticación y gestión de sesiones | AWS Cognito, AWS SES, PostgreSQL |
| [users](./users.md) | Gestión de usuarios e invitaciones | AWS Cognito, AWS SES, PostgreSQL |
| [commands](./commands.md) | Envío de comandos a dispositivos | KORE Wireless API, PostgreSQL |
| [contact](./contact.md) | Formulario de contacto público | AWS SES, Google reCAPTCHA v3 |
| [subscriptions](./subscriptions.md) | Gestión de suscripciones | PostgreSQL |
| [trips](./trips.md) | Consulta de viajes y telemetría | PostgreSQL, PASETO |

---

## 🔌 Resumen de Dependencias Externas

### APIs y Servicios Externos

| Servicio | Tipo | Propósito | Módulos que lo usan |
|----------|------|-----------|---------------------|
| **AWS Cognito** | Identity Provider | Autenticación de usuarios, gestión de credenciales | auth, users |
| **AWS SES** | Email Service | Envío de correos transaccionales | auth, users, contact |
| **KORE Wireless API** | IoT/SMS Gateway | Envío de comandos SMS a dispositivos SuperSIM | commands |
| **Google reCAPTCHA v3** | Security | Protección contra bots en formularios públicos | contact |
| **PostgreSQL** | Database | Persistencia de datos | Todos los módulos |

---

### 🔐 AWS Cognito

**URL Base:** `https://cognito-idp.{region}.amazonaws.com`

| Endpoint/Operación | Uso |
|-------------------|-----|
| `/.well-known/jwks.json` | Validación de JWT tokens |
| `InitiateAuth` | Login de usuarios |
| `GlobalSignOut` | Logout de usuarios |
| `AdminCreateUser` | Creación de usuarios |
| `AdminSetUserPassword` | Establecer/cambiar contraseñas |
| `AdminGetUser` | Verificar existencia de usuario |
| `AdminUpdateUserAttributes` | Actualizar atributos (email_verified) |

---

### 📧 AWS SES (Simple Email Service)

**Región:** Configurable via `SES_REGION` (fallback: `COGNITO_REGION`)

| Template | Uso | Módulo |
|----------|-----|--------|
| `verification_email.html` | Verificación de email de nuevos usuarios | auth |
| `password_reset.html` | Recuperación de contraseña (código 6 dígitos) | auth |
| `invitation.html` | Invitación a nuevos usuarios | users |
| `contact_message.html` | Mensajes de contacto del sitio web | contact |

---

### 📡 KORE Wireless API (SuperSIM)

**Autenticación:** OAuth2 Client Credentials

| Endpoint | Método | Uso |
|----------|--------|-----|
| `KORE_API_AUTH` | POST | Obtener access token |
| `KORE_API_SMS` | POST | Enviar comando SMS a SIM |
| `{sms_url}` | GET | Consultar estado de SMS enviado |

---

### 🛡️ Google reCAPTCHA v3

**URL:** `https://www.google.com/recaptcha/api/siteverify`

| Parámetro | Descripción |
|-----------|-------------|
| `secret` | Secret key del servidor |
| `response` | Token recibido del frontend |

**Score mínimo requerido:** 0.5

---

## 🗄️ Base de Datos (PostgreSQL)

Todos los módulos interactúan con PostgreSQL a través de SQLAlchemy/SQLModel.

### Tablas Principales por Módulo

| Módulo | Tablas |
|--------|--------|
| auth | `users`, `tokens_confirmacion` |
| users | `users`, `tokens_confirmacion`, `organization_users` |
| commands | `commands`, `devices`, `unified_sim_profiles` |
| contact | (sin tablas propias, solo envío de email) |
| subscriptions | `subscriptions`, `plans` |
| trips | `trips`, `trip_points`, `trip_alerts`, `trip_events`, `units`, `unit_devices`, `user_units` |

---

## 🔑 Autenticación de API

### API Pública (Usuarios)

- **Mecanismo:** JWT de AWS Cognito
- **Header:** `Authorization: Bearer {access_token}`
- **Validación:** JWKS de Cognito

### API Interna (Servicios)

- **Mecanismo:** PASETO v4.local
- **Header:** `Authorization: Bearer {paseto_token}`
- **Claims requeridos:** `service`, `role`
- **Servicios autorizados:** `gac` con rol `NEXUS_ADMIN`

---

## 🧭 Relación C4 (preview)

```
┌─────────────────────────────────────────────────────────────────┐
│                        [External Systems]                        │
├─────────────────┬──────────────┬───────────────┬────────────────┤
│   AWS Cognito   │   AWS SES    │ KORE Wireless │ Google reCAPTCHA│
└────────┬────────┴──────┬───────┴───────┬───────┴────────┬───────┘
         │               │               │                │
         ▼               ▼               ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SISCOM Admin API (FastAPI)                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │   Auth   │ │  Users   │ │ Commands │ │ Contact  │ │ Trips  │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ │
│       │            │            │            │           │      │
│       └────────────┴────────────┴────────────┴───────────┘      │
│                              │                                   │
│                              ▼                                   │
│                     ┌────────────────┐                          │
│                     │   PostgreSQL   │                          │
│                     └────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 Convenciones de Documentación

Cada archivo de módulo sigue esta estructura:

1. **Descripción** - Propósito del módulo
2. **Actor** - Quién utiliza el módulo
3. **APIs Consumidas** - Servicios externos utilizados
4. **Flujo funcional** - Secuencia de operaciones
5. **Consideraciones** - Notas importantes y requisitos
6. **Relación C4** - Container y componentes relacionados

---

## 🔄 Mantenimiento

Esta documentación debe actualizarse cuando:

- Se agreguen nuevas dependencias externas
- Se creen nuevos módulos
- Cambien los flujos de autenticación
- Se modifiquen endpoints de servicios externos


