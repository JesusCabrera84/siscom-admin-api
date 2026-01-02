# Módulo: Subscriptions

## 📌 Descripción

Gestión de suscripciones de las organizaciones.
Permite ver, cancelar y configurar la renovación automática de suscripciones a planes.

---

## 👤 Actor

- Usuario autenticado (listar, ver detalles)
- Usuario con rol `owner` o `billing` (cancelar, configurar auto-renew)

---

## 🔌 APIs Consumidas

### 🔹 PostgreSQL (Base de datos)

| Tabla | Operación | Uso |
|-------|-----------|-----|
| `subscriptions` | SELECT | Listar suscripciones de la organización |
| `subscriptions` | UPDATE | Cancelar, cambiar auto_renew |
| `plans` | SELECT | Obtener información del plan asociado |

**Nota:** Este módulo no consume APIs externas, solo interactúa con la base de datos.

---

## 🔁 Flujo funcional

### Listar Suscripciones (`GET /subscriptions`)

```
1. Obtiene organization_id del token Cognito
2. Consulta suscripciones de la organización
3. Opcionalmente incluye históricas (canceladas/expiradas)
4. Calcula campos derivados:
   - is_active: basado en status y expires_at
   - days_remaining: días hasta expiración
5. Retorna lista con plan_name, plan_code y métricas
```

### Listar Suscripciones Activas (`GET /subscriptions/active`)

```
1. Obtiene organization_id del token
2. Filtra por status=ACTIVE|TRIAL y expires_at > now
3. Retorna solo suscripciones activas
```

### Obtener Detalle (`GET /subscriptions/{subscription_id}`)

```
1. Obtiene organization_id del token
2. Busca suscripción por ID y organization_id
3. Calcula campos derivados
4. Retorna detalle completo con información del plan
```

### Cancelar Suscripción (`POST /subscriptions/{subscription_id}/cancel`)

```
1. Verifica rol: owner o billing
2. Busca suscripción de la organización
3. Verifica que no esté ya cancelada
4. Actualiza:
   - cancelled_at = now
   - auto_renew = False
   - Si cancel_immediately: status=CANCELLED, expires_at=now
   - Si no: status=CANCELLED (sigue activa hasta expirar)
5. Retorna suscripción actualizada
```

### Configurar Auto-Renew (`PATCH /subscriptions/{subscription_id}/auto-renew`)

```
1. Verifica rol: owner o billing
2. Busca suscripción de la organización
3. Verifica que esté activa (ACTIVE o TRIAL)
4. Actualiza auto_renew al valor solicitado
5. Retorna suscripción actualizada
```

---

## ⚠️ Consideraciones

- Las suscripciones pertenecen a **organizaciones** (raíz operativa)
- Los pagos pertenecen a **accounts** (raíz comercial)
- Una organización puede tener **múltiples** suscripciones activas
- El estado activo se **calcula** dinámicamente (status + expires_at)
- La cancelación puede ser inmediata o al final del período
- Solo roles `owner` y `billing` pueden cancelar/modificar suscripciones

---

## 🔐 Permisos

| Endpoint | Requiere Auth | Rol Requerido |
|----------|---------------|---------------|
| `GET /subscriptions` | ✅ | Cualquier usuario |
| `GET /subscriptions/active` | ✅ | Cualquier usuario |
| `GET /subscriptions/{id}` | ✅ | Cualquier usuario |
| `POST /subscriptions/{id}/cancel` | ✅ | `owner` o `billing` |
| `PATCH /subscriptions/{id}/auto-renew` | ✅ | `owner` o `billing` |

---

## 📊 Estados de Suscripción

| Status | Descripción |
|--------|-------------|
| `ACTIVE` | Suscripción activa y pagada |
| `TRIAL` | Período de prueba |
| `CANCELLED` | Cancelada (puede seguir activa hasta expires_at) |
| `EXPIRED` | Período expirado |
| `SUSPENDED` | Suspendida por falta de pago |

---

## 📊 Estructura de Respuesta

```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "plan_id": "uuid",
  "plan_name": "Plan Pro",
  "plan_code": "pro_monthly",
  "status": "ACTIVE",
  "billing_cycle": "monthly",
  "started_at": "2025-01-01T00:00:00Z",
  "expires_at": "2025-02-01T00:00:00Z",
  "cancelled_at": null,
  "auto_renew": true,
  "days_remaining": 30,
  "is_active": true
}
```

---

## 🧭 Relación C4 (preview)

- **Container:** SISCOM Admin API (FastAPI)
- **Consumes:** PostgreSQL
- **Consumed by:** Web App (panel de facturación)
- **Related:** Payments module, Plans module


