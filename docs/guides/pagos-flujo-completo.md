# Flujo de pagos de Geminis Labs — de punta a punta

Este documento es la fuente de verdad del cobro de suscripciones NEXUS.
Describe qué hace el sistema, qué **no** hace, y cada resultado posible.

El plan de pruebas operativo vive fuera de este repo:
[`PLAN-PRUEBAS-PAGOS.md`](../../../PLAN-PRUEBAS-PAGOS.md)
(workspace `GeminisLabs/current`).

Código de referencia:

| Pieza | Archivo |
|-------|---------|
| HTTP Stripe (JWT) | `app/api/v1/endpoints/stripe_billing.py` |
| Gateway Stripe | `app/services/gateways/stripe_gateway.py` |
| Dinero | `app/services/money.py` |
| IVA y períodos | `app/services/billing_period.py` |
| Idempotencia HTTP | `app/services/idempotency_service.py` |
| Suscripción activa | `app/services/subscription_query.py` |
| Renovación automática | `app/services/renewal_service.py` |
| Efectivo GAC | `app/services/manual_payment_service.py` |
| Cron / efectivo | `app/api/v1/endpoints/internal/billing.py` |
| Resumen UI | `app/api/v1/endpoints/billing.py` |
| Checkout web | `geminis-labs-web-page/src/lib/components/CheckoutModal.svelte` |
| Cliente web | `geminis-labs-web-page/src/lib/services/billingService.js` |

---

## 1. Invariantes (léelos antes que el resto)

Estas reglas no se negocian. Si un caso parece contradecirlas, gana la invariante.

1. **El cliente nunca decide el monto.** El body de `POST /api/v1/stripe/payment-intent` solo admite `plan_id`, `billing_cycle` y `gateway`. Cualquier otro campo (`amount`, `total`, `tax`…) se rechaza con **422**. El importe sale de `plans` + IVA.
2. **El dinero no viaja en `float`.** Internamente es `Decimal` a dos centavos. En JSON sale como string (`"1738.84"`) o como entero de centavos (`173884`). `float` y `bool` se rechazan.
3. **Cargo, factura y pantalla usan el mismo desglose.** Total = subtotal redondeado + IVA redondeado. Nunca `subtotal * 1.16` como único redondeo.
4. **Hay dos capas de idempotencia**, independientes:
   - Cliente → API: header `Idempotency-Key` (obligatorio en el cobro).
   - API → Stripe: `payments.idempotency_key` determinista por período.
5. **El PAN nunca toca nuestros servidores.** Stripe.js / Payment Element tokenizan. Nosotros guardamos `pm_…`, marca, last4, vencimiento y fingerprint.
6. **Un cobro = una tarjeta = el total.** No existe pago partido en N tarjetas. Un éxito parcial dejaría dinero cobrado sin servicio o servicio sin cobro. La vía alternativa es efectivo vía GAC.
7. **3DS no se afirma como pagado.** `processing` y `requires_action` esperan. Solo `succeeded` (y `requires_capture`) activan la suscripción en firme.
8. **El webhook es la autoridad de fulfillment.** El front puede mostrar éxito cuando Stripe ya confirmó; la suscripción se activa al procesar `payment_intent.succeeded` (o al cumplir el PI si el backend lo recupera ya cobrado).
9. **Misma suscripción, no un objeto Stripe Billing.** Usamos PaymentIntents + SetupIntents. Los eventos `customer.subscription.*` de Stripe se reciben, pero la vigencia vive en `subscriptions` local.
10. **Account cobra, Organization opera.** El Customer de Stripe y las tarjetas pertenecen al Account. La suscripción pertenece a la Organization.

---

## 2. Actores y permisos

| Actor | Qué puede |
|-------|-----------|
| Usuario `owner` o `billing` | Cotizar, pagar, guardar/borrar tarjetas, auto-renovar |
| Usuario `admin` o `member` | Ver planes públicos; **403** en cobro y métodos de pago |
| Stripe (webhook, sin JWT) | Confirmar, fallar, reembolsar, disputar. Autenticación = firma del cuerpo |
| Operador GAC (`service=gac`, `role=GAC_ADMIN`, PASETO) | Registrar efectivo y disparar el cron de renovaciones |
| Cron diario | `POST /api/v1/internal/billing/renewals/run` |

La regla de billing es `OrganizationService.can_manage_billing`.

---

## 3. Entidades

```
Account  (raíz comercial)
  ├── PaymentGatewayCustomer   stripe_customer_id
  ├── PaymentMethod[]          tarjetas (pm_…)
  ├── Invoice[]
  └── Payment[]

Organization  (raíz operativa, pertenece a un Account)
  └── Subscription[]           vigencia NEXUS
```

### 3.1 Estados de `Payment`

| Estado | Significado |
|--------|-------------|
| `PENDING` | PI creado, aún no confirmado |
| `REQUIRES_ACTION` | Banco pide 3DS / autorización. Típico en renovación off-session |
| `PROCESSING` | Stripe aún no cierra (async / 3DS en curso) |
| `SUCCESS` | Cobrado. Activa o encadena la suscripción |
| `FAILED` | Rechazo (fondos, tarjeta, etc.) |
| `CANCELED` | PI cancelado (checkout abandonado, repricing, …) |
| `DISPUTED` | Chargeback abierto o perdido |
| `REFUNDED` | Reembolso total. Se anula un período |
| `PARTIALLY_REFUNDED` | Reembolso parcial. **El servicio sigue** |

### 3.2 Estados de `Invoice`

`DRAFT`, `OPEN` (intento vivo), `PAID`, `PAST_DUE`, `VOID` (cancelado o reembolso total), `UNCOLLECTIBLE` (disputa perdida).

### 3.3 Estados de `Subscription`

| Estado | ¿Opera? |
|--------|---------|
| `ACTIVE` | Sí, si `expires_at` es futuro (o nulo) |
| `TRIAL` | Sí, misma regla de fechas |
| `PAST_DUE` | Sí **mientras** `grace_until > now` |
| `CANCELLED` / `EXPIRED` | No |

Fuente de verdad: `app/services/subscription_query.py`.
`organizations.active_subscription_id` es legacy y **no** se usa.

Si hay varias activas, la “principal” (la que muestra el panel) es la más reciente por `started_at`.

### 3.4 Ciclos y duración

| Ciclo | Días de vigencia que se venden |
|-------|--------------------------------|
| `MONTHLY` | 30 |
| `YEARLY` | 365 |

No son meses ni años calendario. Un mensual cobrado el 31 de enero vence 30 días después.

---

## 4. Dinero e IVA

Módulo: `billing_period.with_iva` + `money.parse` / `money.dump` / `money.to_cents`.

```
IVA_RATE = 0.16
tax      = round_half_up(subtotal * 0.16, 2 decimales)
total    = subtotal + tax
cents    = total * 100   (entero; es lo que se manda a Stripe)
```

Ejemplo: lista `1499.00` MXN → IVA `239.84` → total `1738.84` → Stripe `173884` centavos.

El catálogo (`GET /api/v1/plans`) ya incluye `monthly_quote` y `yearly_quote` con ese desglose. El checkout **no recalcula**: llama `GET /api/v1/stripe/quote`.

Stripe cobra el **precio de lista del plan + IVA**, una vez. No multiplica por `active_units`.

El pago en efectivo GAC sí: `with_iva(precio_ciclo × active_units)`.

---

## 5. Cotización oficial

```
GET /api/v1/stripe/quote?plan_id=<uuid>&billing_cycle=MONTHLY|YEARLY
Authorization: Bearer <cognito>
```

Respuesta:

```json
{
  "plan_id": "…",
  "plan_name": "Pro",
  "plan_code": "pro",
  "billing_cycle": "MONTHLY",
  "currency": "MXN",
  "subtotal": "1499.00",
  "tax": "239.84",
  "total": "1738.84",
  "amount_cents": 173884
}
```

Errores: ciclo inválido **400**, plan inexistente o inactivo **404**.

El modal de checkout muestra exactamente esos campos. Si al crear el PI Stripe/BD cotizan otro `amount_cents`, el front **no confirma**: avisa el nuevo importe y pide que el usuario pulse Pagar de nuevo.

---

## 6. Endpoints HTTP

Base pública: `/api/v1`. Auth Cognito salvo el webhook.

### 6.1 Stripe (JWT, rol billing/owner salvo `config` y `quote`)

| Método | Ruta | Notas |
|--------|------|-------|
| `GET` | `/stripe/config` | `publishable_key`. Nunca va hardcodeada en el front |
| `GET` | `/stripe/quote` | Cotización oficial |
| `POST` | `/stripe/setup-intent` | Guardar tarjeta (Payment Element). **201** |
| `POST` | `/stripe/payment-methods/confirm` | Persiste el SetupIntent ya confirmado. `{ "setup_intent_id" }` |
| `POST` | `/stripe/payment-intent` | Crear cobro. Header `Idempotency-Key` **obligatorio**. **201** |
| `GET` | `/stripe/payment-methods` | Tarjetas del Account |
| `DELETE` | `/stripe/payment-methods/{external_token}` | Anti-IDOR: el token debe ser del Account |
| `PATCH` | `/stripe/payment-methods/default` | `{ "external_token", "gateway" }` |
| `PATCH` | `/stripe/auto-renew` | `{ "auto_renew": true\|false }` sobre la suscripción principal |
| `POST` | `/stripe/webhook/{gateway}` | **Sin JWT.** Firma Stripe. No aparece en OpenAPI |

### 6.2 Lectura de facturación (JWT)

| Método | Ruta |
|--------|------|
| `GET` | `/billing/summary` |
| `GET` | `/billing/payments` |
| `GET` | `/billing/invoices` |
| `GET` | `/billing/invoices/{id}` |

`summary.current_plan.amount_due` es el **total con IVA** (string Decimal serializado). También va `quote` con subtotal/tax/total/cents.

`summary.renewal`:

| `state` | Cuándo |
|---------|--------|
| `ok` | Activa, sin dunning |
| `action_required` | Hay un Payment de renovación (`idempotency_key` con prefijo `renew:`) en `REQUIRES_ACTION` |
| `no_payment_method` | `PAST_DUE` y no hay tarjeta default |
| `past_due` | `PAST_DUE` con tarjeta; el cobro falló |

`pending_amount` = suma de Payments `PENDING` del Account (checkout a medias).

### 6.3 Interno GAC (PASETO `gac` / `GAC_ADMIN`)

| Método | Ruta |
|--------|------|
| `POST` | `/internal/billing/manual-payments` |
| `POST` | `/internal/billing/renewals/run?limit=1..1000` |

Hay un segundo toggle histórico: `PATCH /api/v1/subscriptions/{id}/auto-renew`. El panel usa **`/stripe/auto-renew`**.

---

## 7. Flujo A — primera suscripción (checkout interactivo)

```
Usuario elige plan + ciclo
        │
        ▼
GET /stripe/quote          ← solo display
        │
        ▼
¿Hay tarjetas guardadas?
  no  → Continuar → Payment Element (mode=payment, amount=amount_cents)
  sí  → selecciona una o “Usar otra tarjeta”
        │
        ▼
POST /stripe/payment-intent
  header Idempotency-Key = sessionStorage(plan, ciclo)
  body { plan_id, billing_cycle, gateway: "stripe" }
        │
        ├─ 201  client_token + amount_cents + desglose
        ├─ 400  key ausente / inválida, plan sin precio
        ├─ 403  no es owner/billing
        ├─ 404  plan inactivo
        ├─ 409  ya pagó este período calendario  O  key reusada con otro body
        ├─ 422  mandó amount u otro campo extra
        └─ 503  no se pudo verificar un PI anterior (no se afirma ni se cancela)
        │
        ▼
Stripe.js confirmCardPayment / confirmPayment
  return_url = /control-panel/billing/summary?checkout=resume
        │
        ├─ succeeded / requires_capture → “Pago listo”
        ├─ requires_action / processing → la ventana ESPERA (poll 90 s)
        ├─ card_declined / insufficient_funds / … → error, no se cobra de nuevo
        └─ redirect 3DS → summary lee payment_intent_client_secret
        │
        ▼
Stripe envía payment_intent.succeeded
        │
        ▼
Webhook → Payment SUCCESS, Invoice PAID, Subscription ACTIVE
```

### 7.1 Qué ve el usuario

1. Precio primero (plan, IVA, total). No se salta al formulario si no hay tarjetas.
2. Mensual / anual. El badge de ahorro anual solo aparece si `yearly_savings_percent > 0`.
3. **Continuar** (sin tarjeta) vs **Pagar $X** (con tarjeta).
4. En el paso de tarjeta, recap del total.
5. 3DS: “Autoriza $X en tu banco. Esta ventana espera.”
6. Si el banco no cierra a tiempo: no se muestra “Pago procesado correctamente”. El resumen dice **“Estamos confirmando tu pago”**.

El front compara `amount_cents` **enteros**. Nunca compara pesos en float.

### 7.2 Clave HTTP del cliente

`sessionStorage` key `payment_idem_{planId}_{CYCLE}`.

- Doble clic y reintento de red reutilizan la misma key → la API devuelve el mismo 201 cacheado.
- Otro plan o ciclo genera otra key.
- Tras éxito (o “ya procesado”) se borra para el siguiente período.

TTL de la reserva en BD: **24 h**. Si un cobro queda `in_progress` más de **30 s**, el siguiente request puede tomar la reserva (takeover). Un **5xx** **borra** la reserva para no cachear un resultado desconocido.

---

## 8. Flujo B — PaymentIntent en el backend (detalle)

Al crear el PI el backend:

1. Resuelve Account desde Organization.
2. Crea o reusa `Customer` Stripe (`get_or_create_customer`).
3. Cotiza con `with_iva(price_monthly | price_yearly)`.
4. Toma un lock transaccional `pg_advisory_xact_lock("pi", account_id)`.
5. Busca un Payment del mismo período:
   - **MONTHLY** bucket `YYYYMM` → un éxito por cuenta+plan+ciclo **por mes calendario**.
   - **YEARLY** bucket `YYYY` → un éxito **por año calendario**.
6. Si ya hay `SUCCESS` → **409** “Este pago ya fue procesado exitosamente este período”.
7. Si hay un PI pendiente con **el mismo** `amount_cents` → se reusa (mismo `client_secret`).
8. Si el pendiente tiene **otro** monto (repricing) → se intenta cancelar el PI viejo:
   - cancelado → se emite uno nuevo con key Stripe distinta (`…|stripe_reissue|<pi_id>`);
   - el viejo ya estaba cobrado → se cumple localmente y **409**;
   - Stripe no responde → **503**, se abandona la reserva HTTP.
9. Cancela Payments `PENDING` de **otros** buckets del mismo Account, **excepto** los que empiezan con `renew:` (un checkout no debe abortar una renovación en curso).
10. Crea Invoice `OPEN` + Payment `PENDING` con el total con IVA.
11. Stripe PI: `confirm=false`, `setup_future_usage=off_session`, `allow_redirects=never`, currency `mxn`.

Metadata del PI (imprescindible para activar):

```
account_id, organization_id, plan_id, plan_code, billing_cycle
```

Sin `plan_id` el webhook no puede activar y lanza error (Stripe reintenta el evento).

### 8.1 Implicación del bucket calendario

Pagar **el mismo plan y ciclo dos veces en el mismo mes calendario** (o el mismo año si es anual) vía checkout **no es posible**: 409.

Para extender vigencia en el mismo mes:

- esperar al mes siguiente y volver a pagar, **o**
- dejar que la renovación automática cobre cerca del vencimiento (usa otra llave: `renew:` + fecha de `expires_at`), **o**
- cambiar de plan (otro `plan_id` → otra llave), **o**
- registrar efectivo por GAC (no usa esa llave de período Stripe).

Cuando el segundo cobro **sí** entra (otro mes, otro plan, o renovación), `_activate_subscription` **encadena** 30/365 días al `expires_at` vigente si es el mismo plan+ciclo. Si cambia el plan o el ciclo, el período **reinicia hoy**.

---

## 9. Flujo C — guardar una tarjeta sin cobrar

```
POST /stripe/setup-intent  →  client_token
Stripe.js confirmSetup
POST /stripe/payment-methods/confirm  { setup_intent_id }
  → el servidor recupera el SetupIntent en Stripe y persiste PaymentMethod
webhook setup_intent.succeeded  (idempotente; misma persistencia)
  → PaymentMethod local (brand, last4, fingerprint)
  → primera tarjeta del Account = default
  → misma fingerprint → se detacha el pm duplicado en Stripe, no se inserta
```

El front **no espera el webhook** para listar la tarjeta: si Stripe.js ya confirmó, `confirm` copia el método a BD. El webhook cubre el caso de 3DS con redirect o un crash a mitad del flujo.

La key de Stripe del SetupIntent es única por llamada (`uuid`). Un bucket horario reutilizaría un SI ya confirmado y bloquearía la segunda tarjeta.

`usage=off_session`: esa tarjeta sirve después para renovar sin el cliente presente.

---

## 10. Webhooks

```
POST /api/v1/stripe/webhook/stripe
Header: stripe-signature
Auth: STRIPE_WEBHOOK_SECRET
```

| Resultado | HTTP |
|-----------|------|
| Firma inválida / payload roto | **400** |
| Evento duplicado o no manejado | **200** `{ "received": true }` |
| Error transitorio al cumplir | **500** (Stripe reintenta) |

Deduplicación: tabla `payment_gateway_events` por `(gateway, external_event_id)`.

- `processed` / `skipped` → se ignora.
- `processing` con menos de 30 s → se ignora (otro worker lo tiene).
- `processing` viejo o `failed` → se retoma (`retry_count++`).

### 10.1 Eventos manejados

| Evento | Efecto |
|--------|--------|
| `setup_intent.succeeded` | Persiste la tarjeta |
| `payment_intent.succeeded` | `_fulfill_local_success`: Payment SUCCESS, Invoice PAID, activa suscripción |
| `payment_intent.payment_failed` | Payment FAILED (solo si seguía PENDING) |
| `payment_intent.canceled` | Payment CANCELED (solo si seguía PENDING) |
| `payment_intent.processing` | Payment PROCESSING |
| `payment_intent.requires_action` | Payment REQUIRES_ACTION |
| `charge.refunded` | Ver §12 |
| `charge.dispute.created` / `updated` | Marca disputa; **no corta** el servicio |
| `charge.dispute.closed` | `won` restaura; `lost` revoca un período + invoice UNCOLLECTIBLE |
| `customer.subscription.updated/deleted` | Log / sync residual. No es el motor de vigencia |
| `invoice.payment_failed` | Solo log. No usamos Stripe Invoices/Subscriptions de Billing |
| Cualquier otro | `skipped` |

Si llega `payment_intent.succeeded` y **no hay** fila local de Payment: se registra error y se responde 200 (no se puede inventar el cobro). Es una alerta operativa.

`_fulfill_local_success` es idempotente: si el Payment ya es SUCCESS, no hace nada.

---

## 11. Activación y encadenamiento de períodos

```
lock("sub", organization_id)     # dos webhooks no pisan el mismo expires_at
¿hay suscripción activa?
  no  → crea ACTIVE, período = now → now+30/365, auto_renew=true
  sí y mismo plan+ciclo → start = expires_at actual (si es futuro), end = start+30/365
  sí y otro plan o ciclo → start = now, end = now+30/365
```

La misma política aplica al **efectivo GAC**.

Ejemplo: Pro mensual vence el 20 sep. El 10 sep pagan otra vez Pro mensual (si el bucket de agosto/septiembre lo permite — en la práctica el segundo cobro checkout en el mismo mes calendario choca con 409; en renovación automática sí entra). El nuevo fin = 20 sep + 30 días. El cliente **no pierde** los 10 días que ya había pagado.

Cambio Pro → Enterprise: el período empieza hoy. Lo contratado es otro producto.

---

## 12. Reembolsos

Stripe manda el **acumulado** `amount_refunded`, no el delta. Se asigna, no se suma.

| Caso | Payment | Invoice | Vigencia |
|------|---------|---------|----------|
| Parcial (`refunded=false` y `refunded_amount < amount`) | `PARTIALLY_REFUNDED` | no se toca | **sigue** |
| Total (`refunded=true` o acumulado ≥ cobrado) | `REFUNDED` | `VOID` | se resta **un** ciclo (30 o 365 días) |

La resta es idempotente (`extra_data.period_revoked=true`). Un webhook repetido no quita dos períodos.

Si al restar `expires_at` queda en el pasado → `CANCELLED`.

No hay endpoint propio de reembolso: se hace en el Dashboard de Stripe (o API Stripe) y llega el webhook.

---

## 13. Disputas (chargebacks)

| Fase | Payment | Servicio |
|------|---------|----------|
| Abierta (`created`/`updated`) | `DISPUTED`, se guardan id/razón/vencimiento de evidencia | **Sigue.** Cortar a alguien que puede ganar el cargo es peor |
| Cerrada `won` | vuelve a `SUCCESS`, invoice `PAID` | si se había revocado, se **devuelve** el período |
| Cerrada `lost` | sigue `DISPUTED`, invoice `UNCOLLECTIBLE` | se revoca un período (misma función que el reembolso total) |

---

## 14. Renovación automática

No usamos Stripe Billing Subscriptions. Un cron llama:

```
POST /api/v1/internal/billing/renewals/run?limit=200
Authorization: Bearer <PASETO gac / GAC_ADMIN>
```

Es seguro llamarlo varias veces al día.

### 14.1 Política

| Parámetro | Valor |
|-----------|-------|
| Primer intento | 3 días **antes** de `expires_at` |
| Gracia | 7 días **después del vencimiento** (no después del intento) |
| Reintentos | días 1, 3 y 5 desde el primer fallo |
| Tras agotar | no se cobra más; al vencer `grace_until` deja de ser activa **sola** |

Candidatas: `auto_renew=true`, status `ACTIVE` o `PAST_DUE`, `expires_at <= now+3d`, `dunning_next_attempt` nulo o ya debido, gracia no vencida.

Cada suscripción se cobra en su propia transacción + lock `("renew", subscription_id)`. Un error no tumba el lote.

### 14.2 Cobro off-session

`PaymentIntent.create(..., off_session=True, confirm=True, payment_method=default)`.

Llave **BD** (estable entre reintentos del mismo vencimiento):

```
renew: + sha256("renew" | subscription_id | expires_at YYYYMMDD)
```

Llave **Stripe** (cambia por intento, para no cachear el rechazo anterior):

```
sha256(db_key | "attempt" | N)
```

Antes de emitir un PI nuevo se consulta el anterior:

- ya `succeeded` → se cumple y se da por renovado (no segundo cargo);
- sigue `requires_action` / `processing` → se espera al cliente, no se emite otro;
- Stripe no responde → `unavailable` esta corrida, **no** se inventa un PI (evitar doble cobro).

### 14.3 Resultados de una corrida

```json
{
  "renewed": 3,
  "action_required": 1,
  "retry_scheduled": 2,
  "exhausted": 0,
  "skipped": 1,
  "details": [
    { "subscription_id": "…", "result": "renewed", "detail": "" }
  ]
}
```

| `result` | Qué pasó en la suscripción |
|----------|----------------------------|
| `renewed` | SUCCESS (o `processing`: el webhook cerrará). status ACTIVE, dunning limpio, período encadenado |
| `action_required` | Banco pide 3DS. `PAST_DUE` + gracia. **No consume** el mismo tipo de reintento que un decline; `dunning_next_attempt = now+1d` por si el cliente no autoriza |
| `retry_scheduled` | Decline / sin tarjeta / Stripe caído. `PAST_DUE`, gracia desde `expires_at`, siguiente intento según (1, 3, 5) |
| `exhausted` | Ya se usaron los 3 reintentos. `dunning_next_attempt=null`. Sigue hasta `grace_until` |
| `skipped` | Ya no aplicaba, no existe, o error interno de esa fila |

`authentication_required` se trata como `action_required`, no como decline.

Al **encender** auto-renew desde el panel se limpian `dunning_*` y `renewal_last_error` (si ya cambió la tarjeta, no debe esperar al reintento agendado). Apagarlo **no cancela**: solo deja de cobrar; el servicio sigue hasta `expires_at`.

El checkout interactivo **nunca** cancela PIs `renew:` (§8 paso 9).

---

## 15. Efectivo (GAC)

```
POST /api/v1/internal/billing/manual-payments
```

```json
{
  "account_id": "…",
  "organization_id": "…",
  "plan_id": "…",
  "billing_cycle": "MONTHLY",
  "active_units": 1,
  "transaction_ref": "CAJA-123",
  "registration_notes": "Pago en sucursal",
  "operator_email": "ops@gac"
}
```

Monto = `with_iva(precio_ciclo × active_units)`. Planes cuyo `code` contiene `migrate` exigen ≥ 20 unidades.

Crea Invoice `PAID` + Payment `SUCCESS` (`gateway=MANUAL`) y activa/encadena con la **misma** política de períodos que Stripe.

Requiere `GAC_SYSTEM_USER_ID` válido (queda en `payments.registered_by`).

---

## 16. Lo que explícitamente no existe

| Idea | Estado |
|------|--------|
| Pago partido en N tarjetas | No. Trampa de dinero. Alternativa: efectivo GAC |
| Stripe Billing Subscriptions / Coupons / Proration nativa | No. PI + suscripción local |
| PayPal | Registry menciona gateways; solo Stripe está implementado |
| El cliente manda el monto | Prohibido (422) |
| MSI / meses sin intereses | Columnas en `payments`, el checkout no las usa |
| Correos de “vamos a renovar / falló el cobro” | El panel muestra avisos. Envío de email de dunning **no** está cableado |
| Job de purge de `api_idempotency_requests` | Hay índice por `expires_at`; no hay cron de borrado |
| OXXO / SPEI en este checkout | El historial puede etiquetar métodos viejos; el cobro actual es tarjeta Stripe |

---

## 17. Casos de borde (catálogo completo)

Cada fila es un comportamiento **definido**. Si ocurre otra cosa, es un bug.

| # | Situación | Resultado esperado |
|---|-----------|-------------------|
| 1 | Doble clic en Pagar | Un solo PI. Misma `Idempotency-Key`. Un solo cargo |
| 2 | Refresh a mitad del 3DS | Summary con `checkout=resume` / `payment_intent_client_secret`. Poll. No segundo cargo |
| 3 | Cierra el modal antes de confirmar | Payment `PENDING`. Banner “Pago iniciado pero no completado”. Completar **reusa** el PI si el monto no cambió |
| 4 | Precio del plan cambia con PI abierto | Se cancela el PI viejo, se emite otro, el modal muestra el nuevo total y pide confirmar |
| 5 | Precio cambia y el PI viejo ya estaba cobrado | 409 already processed. Se cumple localmente. No se cobra de más |
| 6 | Stripe no deja ver el PI viejo | 503. Reserva HTTP abandonada. Reintentar es seguro |
| 7 | Mismo plan+ciclo, mismo mes/año calendario, ya SUCCESS | 409. No hay doble mes regalado ni doble cargo |
| 8 | Webhook `succeeded` duplicado | Segunda vez no-op (`SUCCESS` ya puesto) |
| 9 | Webhook llega antes que el commit del Payment | Log “Payment no encontrado”. 200. Al reintento de Stripe ya existe la fila |
| 10 | Tarjeta 3DS en checkout | Modal espera hasta 90 s. No dice “activado” hasta `succeeded` |
| 11 | Timeout de 90 s con PI aún `processing` | “Estamos confirmando”. Banner índigo en resumen. Webhook activará solo |
| 12 | Tarjeta declinada | Error en modal. Payment FAILED vía webhook. Puede reintentar (otra key de sesión o el mismo PI según estado) |
| 13 | `card_declined` / `insufficient_funds` / `expired_card` / `incorrect_cvc` | Mensajes en español en el modal |
| 14 | Usuario `member` llama payment-intent | 403 |
| 15 | Body con `"amount": 1` | 422 extra fields not permitted |
| 16 | Sin `Idempotency-Key` | 400 |
| 17 | Misma key, otro `plan_id` | 409 payload distinto |
| 18 | Guardar dos veces la misma física (fingerprint) | Segunda se detacha en Stripe. Una sola fila local |
| 19 | Borrar `pm_` de otro account | 404 (anti-IDOR) |
| 20 | Reembolso 50 % | `PARTIALLY_REFUNDED`. Suscripción intacta |
| 21 | Reembolso 100 % | `REFUNDED`, invoice VOID, −30 o −365 días. Webhook 2.ª vez: no resta otra vez |
| 22 | Dispute open | Flag + `DISPUTED`. Servicio sigue |
| 23 | Dispute won | SUCCESS + período restaurado si se había quitado |
| 24 | Dispute lost | UNCOLLECTIBLE + −1 período |
| 25 | Cron, tarjeta ok, off-session | `renewed`. Período encadenado. Un cargo |
| 26 | Cron dos veces el mismo día, ya SUCCESS | Segunda: `skipped` o `renewed` no-op. Un cargo en Stripe |
| 27 | Cron, `authentication_required` | `action_required`. Panel: autoriza. No segundo PI mientras el primero viva |
| 28 | Cron, decline | `retry_scheduled`. PAST_DUE + gracia desde **expires_at** |
| 29 | Cron, sin tarjeta | `retry_scheduled` / `no_payment_method` en summary |
| 30 | Tres declines | `exhausted`. Servicio hasta `grace_until`. Luego deja de ser activa sin job de corte |
| 31 | Usuario apaga auto-renew | No se cobra. Sigue hasta `expires_at` |
| 32 | Usuario enciende auto-renew en PAST_DUE | Limpia dunning. Próximo cron puede cobrar ya |
| 33 | Checkout con renovación `PENDING` `renew:` | El barrido de stale **no** cancela esa renovación |
| 34 | Efectivo 3 unidades, plan 1499 | Total = with_iva(4497) |
| 35 | Efectivo, mismo plan vigente | Encadena período (no reinicia hoy) |
| 36 | Efectivo, otro plan | Reinicia hoy |
| 37 | Plan `migrate*` con 19 unidades | 400 mínimo 20 |
| 38 | `GAC_SYSTEM_USER_ID` ausente | 500 en manual-payments |
| 39 | Firma webhook basura | 400. No se procesa |
| 40 | `PAST_DUE` + `grace_until` futuro | `has_active_subscription=true`. Capabilities siguen |
| 41 | `PAST_DUE` + gracia vencida | Ya no es activa. Sin cron extra |
| 42 | Float en money.parse | `MoneyError` |
| 43 | Quote vs Elements: cents distintos | Front no confirma; pide revisar importe |
| 44 | Pago ya SUCCESS y el front reintenta | 409 mapeado a “Este período ya fue pagado”; el modal puede cerrar como éxito |

---

## 18. Variables de entorno

| Variable | Uso |
|----------|-----|
| `STRIPE_SECRET_KEY` | API Stripe (sk_test / sk_live) |
| `STRIPE_PUBLISHABLE_KEY` | La sirve `/stripe/config` al front |
| `STRIPE_WEBHOOK_SECRET` | `whsec_…` del endpoint o de `stripe listen` |
| `GAC_SYSTEM_USER_ID` | UUID del usuario sistema para `registered_by` en efectivo |

Migraciones necesarias: **021** (`api_idempotency_requests`) y **022** (`grace_until`, dunning, `PAST_DUE` en el check de status).

Webhook en el Dashboard (o CLI):

```
https://<api>/api/v1/stripe/webhook/stripe
```

Eventos mínimos: los de la tabla §10.1.

Cron (diario, una o más veces):

```
POST https://<api>/api/v1/internal/billing/renewals/run
```

---

## 19. Lecturas relacionadas

- Plan de pruebas: [`PLAN-PRUEBAS-PAGOS.md`](../../../PLAN-PRUEBAS-PAGOS.md) (workspace)
- API read-only de billing: [`../api/billing.md`](../api/billing.md) — el encabezado “PSP no implementado” está **desactualizado**; el cobro vive en este guía
- Módulo suscripciones: [`../architecture/modules/subscriptions.md`](../architecture/modules/subscriptions.md)
- Pagos raw históricos: [`../api/payments.md`](../api/payments.md)
