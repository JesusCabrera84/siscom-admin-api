# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- `PATCH /devices/{id}/status` acepta el token PASETO de GAC (`service=gac`, `role=GAC_ADMIN`), no solo Cognito. GAC no tiene usuario Cognito en este servicio: sin este cambio, mover un dispositivo por la puerta que valida transiciones, escribe `unit_devices` y publica Kafka devolvía 401. `performed_by` queda nulo cuando autentica el servicio, y el evento anota el rol.

> **Nota.** Lo que sigue arrastra entradas de varias versiones ya liberadas que
> nunca se movieron a su sección. Se dejan aquí a propósito: atribuirlas exigiría
> saber qué salió en cada tag anterior a `1.25.0`, y adivinarlo produciría un
> historial falso. Las de `1.25.0`, `1.26.0`, `1.27.0` y `1.27.1` sí se
> repartieron, derivadas de `git log <tag-anterior>..<tag>`.

### Added

- **Esquema de tenancy — Fase 2, rebanada A** (migración `027_tenancy_esquema`). Árbol de cuentas con `parent_account_id` y `account_path` (`uuid[]` + índice GIN), `accounts.account_type` (`PLATFORM`/`RESELLER`/`CUSTOMER`), y las tablas `account_capabilities`, `tenant_domains` y `tenant_branding`. Aditiva pura: **ningún modelo, endpoint ni servicio la conoce todavía**, así que puede desplegarse sin que cambie nada visible, o quedarse mergeada sin desplegar. Es la mitad *expand* del expand/contract; la rebanada B —modelos, resolución de capabilities con techo descendente y `GET /tenant-config`— va en el release siguiente
  - **Sin prerrequisitos de despliegue**: `alembic upgrade head` y ya. Ni extensiones, ni privilegios que `siscom_migrator` no tenga, ni un paso manual previo por parte de nadie
  - **`account_path` lo mantienen dos triggers, no la aplicación.** Ese camino es el predicado de aislamiento entre clientes: un invariante del que depende quién ve los datos de quién no puede vivir en una capa que se salta con un `INSERT` manual o un script de soporte. El trigger `BEFORE` construye el camino desde el del padre y rechaza ciclos y profundidad > 5; el `AFTER` propaga a los descendientes cuando se mueve una rama
  - **`ck_accounts_camino_termina_en_si_misma`** ancla el invariante: `@>` casa un elemento en cualquier posición —que es lo que se quiere para pertenencia al subárbol— pero eso solo vale mientras el array sea de verdad la cadena de ancestros, y un id suelto ahí sería un falso positivo en una comprobación de autorización. La restricción no es redundante con el trigger: sobrevive a una restauración, a una carga con `session_replication_role = replica` y a un `DISABLE TRIGGER`
  - `tenant_domains.hostname` es `UNIQUE` **global**, no por cuenta: si dos marcas reclaman el mismo `Host`, quien resuelve tiene que elegir, y esa es una decisión que no debería existir. Se guarda en minúsculas por restricción, para que la búsqueda sea una igualdad indexable y no un `lower()`
  - `account_capabilities` lleva `UNIQUE (account_id, capability_id)` y un `CHECK` de un solo valor. `organization_capabilities` no tiene ninguno de los dos, y por eso admite hoy dos overrides que se contradicen
  - Las cuentas existentes quedan todas como raíz con `account_type = 'CUSTOMER'`. **Cuál es la cuenta `PLATFORM` de Geminis es una decisión de negocio y la toma la rebanada B.** `self_signup_mode` no se siembra: sus modos y sus defensas siguen sin acordarse

- **ADR-006 — el camino materializado va en `uuid[]`, no en `ltree`**, que es lo que decía §3 del documento de arquitectura. Se midió sobre un árbol con la forma del negocio real (44 041 cuentas, 480 000 unidades): en la consulta que de verdad se ejecuta —el join contra la tabla grande— las dos codificaciones **empatan** (16.4 ms contra 15.8 ms), así que el rendimiento no decide. Lo que sí mide algo es el recursivo sobre `parent_id`: 3 210 buffers contra 6, que es lo que justifica materializar el camino
  - Deciden tres cosas que no son rendimiento: `CREATE EXTENSION ltree` exige `CREATE` sobre la base y `siscom_migrator` solo tiene `CONNECT` (comprobado contra un rol acotado igual que el productivo); una etiqueta de `ltree` no admite guiones, así que el UUID entra codificado y hay que reconstruirlo en cada consulta, cada log y cada sesión de soporte; y la política RLS que §3 declara como destino necesita con `uuid[]` un solo id del actor en vez del camino entero serializado en un GUC
  - De regalo: índice de 3.4 MB en vez de 14 MB, `ARRAY(PGUUID)` nativo en SQLAlchemy en vez de un `TypeDecorator` propio, y se acabó el `SAWarning: Did not recognize type 'ltree'` del comparador de deriva

- **`tests/test_tenancy_esquema.py` — 38 pruebas sobre esquema sin modelos.** Las dos redes habituales no alcanzan a la rebanada A: el harness construye la base con `create_all()`, así que solo conoce lo que algún modelo declara; y el comparador de deriva mira en una sola dirección, así que de la `027` solo comprueba que aplique. Este módulo levanta una base desechable con el snapshot productivo más `alembic upgrade head` y ejercita los triggers con datos: caminos, ancestros, reparentado con nietos, ciclos, profundidad, y cada restricción de las tres tablas nuevas. Incluye el `downgrade` y la vuelta a subir
  - Las dos capas de defensa del camino se prueban por separado, y la primera se descubrió al escribir la segunda: con el trigger activo, escribir `account_path` a mano **no falla** —se recalcula y se ignora—, así que la restricción solo se puede ejercitar desactivando el trigger, que es exactamente el escenario para el que existe
  - `tests/esquema_desechable.py` recoge la maquinaria de la base desechable, que antes vivía dentro de `scripts/verificar-deriva.py`. El script pasa a usarla; su comportamiento no cambia

- `docs/runbooks/desplegar-tenancy.md` — qué añade la migración, las tres comprobaciones de después, y qué no revierte el rollback (las definiciones de capability ya referenciadas)

- **Comprobación de deriva entre migraciones y modelos en CI** (`scripts/verificar-deriva.py` + `tests/schema/`). Parte del snapshot del esquema **productivo**, lo stampea, corre `alembic upgrade head` y compara el resultado contra `SQLModel.metadata`. Falla el PR si algo no cuadra.
  - **No se puede hacer con `create_all()`**: comparar la metadata contra una base construida desde esa misma metadata es tautológico y siempre sale vacío. Solo dice algo cuando el esquema viene de otro sitio
  - El snapshot corresponde a `025_device_and_unit_refs`, **antes** de la `026`, para que `upgrade head` ejecute migraciones de verdad en vez de ser un no-op
  - Verificado que sabe fallar: con una columna inventada en un modelo devuelve código 1 y la nombra; sin deriva, 0
  - `tests/schema/README.md` documenta las cinco limitaciones del snapshot —viene de un export gráfico, no de `pg_dump`— y cómo refrescarlo


### Removed

- **`device_services` y todo lo que colgaba de él.** La migración `006` borra esa tabla a propósito y producción no la tiene: aquí producción tenía razón y lo que sobraba era el código. Verificado antes de borrar que **ningún cliente lo usa** — se buscaron las cuatro rutas (`v1/services`, `/services/active`, `/services/confirm-payment`, `/services/{id}/cancel`) en `nexus-web-page`, `geminis-labs-web-page`, `gac-web`, `apple/INexus` y `android`: cero coincidencias en los cinco.
  - Fuera: `endpoints/services.py` (4 rutas legacy, el propio archivo se declaraba "⚠️ NO USAR"), `models/device_service.py`, `schemas/device_service.py`, `services/billing.py` y `services/device_activation.py` (solo alcanzables desde `services.py`), y `services/subscriptions.py` completo — sus cinco funciones tenían **cero llamadores**
  - Fuera también sus tres tests y la prueba de humo de `/services/active` en `test_auth.py`
  - Limpiadas las relaciones en `models/plan.py` y `models/device.py`, los exports de ambos `__init__.py`, y el `include_router` de `api/v1/router.py`
  - **No se tocan las migraciones `006` ni `026`**: son historia
  - `mobility_devices.py` y `mobility_device_service.py` **no** se tocan: `MobilityDeviceService` es otra clase

### Changed

- **Los tests corren contra PostgreSQL real, no contra SQLite.** `tests/conftest.py` levantaba SQLite en memoria y construía el esquema con `SQLModel.metadata.create_all()` bajo un parche (`_patch_metadata`) que borraba los `server_default`, sustituía `UUID`/`ARRAY`/`INET`/`JSONB` por `Text` y aplanaba `table.schema`. La batería no podía fallar por casi ninguna de las razones por las que falla producción. Lo que el cambio destapó de inmediato:
  - **`create_all()` no es una definición completa del esquema.** Los tipos ENUM de `app/core/pg_enums.py` llevan `create_type=False` —los crea el SQL crudo de la migración `023`— así que sin ellos falla con `type "payment_gateway" does not exist`. El fixture los crea derivándolos del propio módulo para que no puedan divergir.
  - **Hay tablas fuera de `public`**: `api_platform.*`. El parche las renombraba a `api_platform_api_alerts` en `public`, así que se probaban contra una tabla que el código de producción nunca toca.
  - Los tres `if dialect != postgresql` del código de producción desaparecen. El más relevante: `app/db/locks.py` hacía `return` temprano, de modo que **el lock consultivo que impide el doble cobro era un no-op declarado bajo test** y tenía cobertura cero.
  - Aislamiento por test: transacción externa revertida al terminar, con `join_transaction_mode="create_savepoint"` para que los `commit()` de fixtures y código se traduzcan a SAVEPOINTs. Antes se hacían `create_all` + `drop_all` de 73 tablas **por cada test**.
  - Los seis tests que fallaron al cambiar de motor: tres eran el bug de `is_active()` de arriba; dos insertaban un `Command` sin que existiera su `Device` —SQLite no aplica claves foráneas, y sin `relationship` declarada SQLAlchemy no ordena los `INSERT`—; uno afirmaba un orden de claves que JSONB no preserva (las normaliza por longitud y bytes). Ninguno de los tres últimos es bug de producción, pero los tres fijaban suposiciones falsas
  - `ci.yml` levanta un servicio `postgres:15`; el harness local es `docker-compose.db.yml`. Se eliminan `tests/sqlite_dialect.py` y `tests/test_sqlite_dialect.py`.


- `GET /internal/accounts` deja de usar `DISTINCT ON` (Postgres-only): el owner se resuelve con `GROUP BY` + `min(email)` para que el query sea válido en SQLite (CI) y en Postgres
- Middleware HTTP que convierte excepciones no manejadas en JSON `{"detail":"Internal server error"}` **dentro** de CORS, para que un 500 no se reporte en el browser como error de CORS
- Engineering foundation (PR-1): blocking CI (`quality` + `security` jobs)
- Soft foundations (PR-2): `.devcontainer/`, `docs/security/threat-model.md`, GitHub issue templates, process ADRs (002, 003)
- Quality gates (PR-3): `CODEOWNERS`, `dependabot.yml`, `docs/GOVERNANCE.md`, OSV-Scanner, `osv-scanner.toml`
- Coverage floor (65% on `app/`) via `pyproject.toml`

- `scripts/gitleaks-scan.sh`, `scripts/pip-audit-scan.sh`, `scripts/osv-scan.sh`, `scripts/setup.sh`
- `.pre-commit-config.yaml` (Ruff, Black, hygiene hooks)
- `AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`, `docs/RELEASE.md`
- `.editorconfig`, `.python-version`, `.gitleaks.toml`
- GitHub pull request template
- `make validate`, `make scan-secrets`, `make audit-deps`
- Docs: `docs/api/teams.md` documenta los endpoints de teams, miembros, reglas de visibilidad, invitaciones, emergencias y snapshots internos ya presentes en `develop`
- Docs: `docs/api/INDEX.md` incorpora teams y el set completo de `/mobility/devices` y `/mobility/locations` al índice y al mapa de rutas

### Changed

- Contrato Kafka de `user-devices-updates`: el payload pasa al envelope de control (`event_id`, `event_type`, `entity`, `organization_id`, `data`). La key es el UUID de la fila `user_devices.id`, no el token. **Ya no se envía `unit_id`**. `alert-distributor` tiene que consumir este contrato (deploy de consumers **antes** que esta API)
- Deploy: `deploy.yml` y docker-compose reciben `KAFKA_UNIT_DEVICES_UPDATES_TOPIC` y `KAFKA_USER_UNITS_UPDATES_TOPIC`. Si las GitHub vars del environment `test` no existen, el workflow usa los defaults del código
- Test harness: SQLite keeps JSONB operators (`.astext`) via compile hook; pytest env defaults in `conftest` for runs without `.env`
- CI: Ruff, Black, pytest, and Docker build are blocking (removed `|| true`)
- Deploy workflow: quality gates delegated to CI; deploy only builds and ships on tags
- Deploy workflow: `alembic upgrade head` corre en un contenedor efímero (misma red y `.env`) antes de levantar el contenedor nuevo
- Test harness: session-scoped SQLite metadata patch, GAC auth in `authenticated_client`, telemetry/sims isolation fixes
- Minimum Python version raised to **3.12** (CI, Docker, Black/Ruff targets, docs)
- Dependency security bumps: `cryptography`, `idna`, `python-multipart`, `starlette`, `pyseto`
- Dependency security bumps: `cryptography` 48.0.1 → 50.0.0 (PYSEC-2026-3552/3553/3554), `kafka-python` 2.3.0 → 2.3.2 (PYSEC-2026-2190/2191), `pyasn1` 0.6.3 → 0.6.4 (PYSEC-2026-3455/3456/3457)
- `scripts/pip-audit-scan.sh` ignora `PYSEC-2026-1325` (`ecdsa`, transitivo vía `python-jose`): no hay versión corregida y no es alcanzable — solo verificamos JWT con RS256. Mismo riesgo ya aceptado en `osv-scanner.toml`
- Gitleaks scans working tree only (`--no-git`); doc placeholders sanitized

### Fixed

- **`Subscription.is_active()` lanzaba `TypeError` en cuanto una suscripción entraba en gracia.** `grace_until` es `TIMESTAMP WITH TIME ZONE` y `expires_at` es `TIMESTAMP` sin zona, mientras que `utcnow()` devuelve naive a propósito: comparar `grace_until > utcnow()` da `can't compare offset-naive and offset-aware datetimes`. Es el camino que recorre el código de cobranza al fallar un cobro. No se veía porque los tests corrían sobre SQLite, que devolvía todo naive. Se normaliza en la frontera de comparación con `as_naive_utc()`, siguiendo el patrón que ya usaba `access_control._aware`

- Reasignar un tracker a otra org/unidad no actualizaba caches de `event-processor` / `alert-distributor`: no había evento de control. Quien recibía el push seguía siendo el dueño anterior hasta reiniciar esos servicios
- Auth: las peticiones sin header `Authorization` (o con esquema distinto de Bearer) responden `401` con `WWW-Authenticate: Bearer` en lugar del `403` por defecto de `HTTPBearer`. Los clientes iOS/Android disparan el refresh de token solo con `401`
- `billing.py`: query devices by `device_id` (not legacy `Device.id`) — 8 billing unit tests re-enabled
- User-commands list/sync tests re-enabled on SQLite JSONB paths (2 tests)
- Auth: una caída de Cognito (JWKS inalcanzable y sin caché) ya no se presenta como `401`. En los endpoints de doble autenticación el error 5xx se propaga en vez de caer al camino PASETO y acabar respondiendo `401`, que mandaba al cliente a reautenticarse contra un problema que ninguna credencial arregla — y convertía la caída en una tormenta de peticiones sobre esta API

### Notes

- 24 tests still skipped (device status flow, orders invoice fixture, legacy DeviceService API, device activation) — follow-up PRs

### Security

- Gitleaks + Semgrep + pip-audit + OSV-Scanner in CI `security` job
- `POST /api/v1/mobility/locations` y `/batch` exigen JWT y validan que el `device_id` pertenezca a un dispositivo activo del usuario autenticado. Antes aceptaban cualquier `device_id` sin autenticación, lo que permitía inyectar ubicaciones de terceros al tópico de Kafka
- PASETO: los tokens de compartir ubicación se firman con `SHARE_LOCATION_KEY_B64`, una clave dedicada, en lugar de con `PASETO_SECRET_KEY`. El verificador de esos tokens vive en siscom-api; entregarle la clave de servicio le permitía firmar tokens `internal-*` y llamar a la API interna como administrador. Sin la clave nueva configurada, `/units/{id}/share-location` responde `503` en vez de degradar a la clave de servicio (ver ADR-004)
- `decode_any_token` se elimina: probaba las dos claves contra el mismo token, de modo que un token de compartir ubicación podía acabar aceptado donde se esperaba uno de servicio
- `scripts/paseto_key_fingerprint.py` imprime la huella SHA-256 (12 hex) del material de clave **efectivo**, para comparar entre servicios sin transmitir la clave
- Telemetría: el acceso a un dispositivo deja de ser un booleano y pasa a ser un conjunto de rangos temporales autorizados. Un dispositivo reasignado a otra organización deja de ser legible por la anterior fuera de la ventana en que estuvo asignado
- El resolver de alcance es explícito por sujeto (`ScopeSubject`): `accessible_device_ids`, que decidía a partir del usuario implícito, se elimina

## [1.27.1] - 2026-09-07

### Fixed

- **El `set -eo pipefail` del despliegue rompía las comprobaciones que endurecía.** `docker ps | grep -q NOMBRE`: `grep -q` sale al primer match, el productor recibe `SIGPIPE` y termina con 141, y `pipefail` da el pipeline por fallido **aunque `grep` haya encontrado lo que buscaba**. En el despliegue de `v1.27.0` el contenedor levantó bien (`Up 5 seconds`) y el script lo dio por caído, revirtiendo la imagen sin necesidad. Nueve comprobaciones tenían esa forma; ahora usan `docker ps -q --filter "name=^X$"` y here-strings (`<<<`) en vez de pipes, y están probadas contra contenedores reales con `pipefail` activo, no solo con `bash -n`

## [1.27.0] - 2026-09-06

Reconciliación del esquema de producción con la cadena de migraciones, y el mecanismo que mantuvo esa divergencia invisible.

### Added

- Deuda de migraciones — diagnóstico, harness y protecciones (no incluye la reconciliación en sí):
  - `docker-compose.db.yml` + `scripts/db-local.sh`: Postgres local con la misma imagen que producción (`timescale/timescaledb:2.15.1-pg15`) para probar migraciones y DDL antes de tocar producción. Incluye `restore` de un dump productivo y `anonymize`. Es prerrequisito de la Fase 2: `ltree` y los índices GIST de `account_path` no se pueden probar en SQLite, que es contra lo que corren hoy los tests
  - `scripts/alembic-probe.py`: sonda **de solo lectura** que, para cada revisión, comprueba si su efecto ya está presente en el esquema vivo, y dice si el historial es reconciliable con un solo `alembic stamp` o necesita una migración de línea base. Es el paso que falta correr contra producción
  - `tests/test_migrations_chain.py`: integridad de la cadena en cada PR — cabeza única, base única, sin huérfanos ni ciclos, todas las revisiones alcanzables desde la cabeza, `downgrade()` con cuerpo real, y prefijo de fichero coherente con el orden de la cadena. Antes nada en CI miraba las migraciones
  - `DB_MIGRATION_USER` / `DB_MIGRATION_PASSWORD`: credencial de migraciones separada de la de runtime, que solo tiene DML. Alembic la usa cuando existe y cae a `DB_USER` cuando no, así que no rompe el despliegue actual
  - `docs/runbooks/reconciliar-historial-alembic.md`: el diagnóstico medido y el procedimiento

### Fixed

- **Reconciliación del esquema (migración `026`).** Medida contra el DDL de producción del 5-6 de septiembre, no deducida. La sonda dio 21 de 25 revisiones presentes con huecos en `004`, `021`, `022` y `024`: no monótono, así que ningún `alembic stamp` único deja el historial correcto. Repara, con endpoints vivos afectados:
  - `api_idempotency_requests` (mig. `021`) — `POST /payment-intent` inserta ahí la reserva de idempotencia antes de llamar a Stripe. Sin la tabla, el endpoint de cobro falla
  - `account_tax_profiles` (mig. `024`) — timbrado CFDI
  - `plan_products` — la usa `internal/plans.py` con un `JOIN`; no la crea ninguna migración, estaba solo en `initdb/02_schema.sql`
  - Siete columnas: `subscriptions.grace_until` y `renewal_last_error`, `invitations.role`, `organization_capabilities.reason` y `expires_at`, `order_items.created_at`, `trip_events.value`
  - `gateway_event_status += 'processing'`
  - **Es idempotente objeto por objeto, no por migración**: la `022` está *parcialmente* aplicada (tiene `dunning_last_attempt` y `dunning_next_attempt`, le faltan las otras dos), así que reejecutarla entera fallaría
  - No toca `device_services` —la mig. `006` la borra a propósito y el sobrante es el modelo— ni `unified_sim_profiles`, que sí existe en producción
  - Ensayada contra una réplica del esquema productivo: aplica, revierte, reaplica, y es no-op sobre un esquema ya reparado
- `docs/RELEASE.md` decía que revertir una liberación era redesplegar el tag anterior. **Eso falla cuando la liberación trae una migración**: alembic aborta con `Can't locate revision identified by ...` porque esa revisión no existe en la historia del código viejo. Ahora documenta los dos pasos reales, en orden, y aclara que el primero —revertir la imagen— basta casi siempre, porque las migraciones son aditivas por política (expand/contract)
- `scripts/nota-de-migracion.py`: genera la nota de migración y rollback de una liberación —qué revisiones añade y el `downgrade` exacto— derivándola del repositorio, para que no pueda envejecer. La plantilla de PR la pide como obligatoria, aunque sea para decir que no hay migraciones
- `scripts/alembic-probe.py` buscaba en `public` tablas que las migraciones `016`–`019` crean en los esquemas `team` y `mobility`, así que daba cuatro revisiones por ausentes cuando sí estaban aplicadas. El veredicto real es 21/25, no 17/25

### Changed

- `deploy.yml` propaga `DB_MIGRATION_USER` (variable) y `DB_MIGRATION_PASSWORD` (secret) en los tres sitios que hacen falta: el bloque `env:`, la lista `envs:` del `ssh-action` —el que se olvida— y el heredoc del `.env`. Anuncia en el log con qué usuario va a migrar, y aborta si el usuario está definido pero la contraseña sale vacía, que es el síntoma de haberla guardado como variable en vez de como secret
- `/health` consulta la base de datos y expone `schema_revision` (la revisión de alembic aplicada, o `null` si `alembic_version` no existe). Devuelve **503** cuando la base no responde. Antes era un diccionario estático: el healthcheck de Docker y el bucle de espera del despliegue daban verde con la base inservible
- `deploy.yml` — `set -eo pipefail` en los dos scripts remotos: sin él, un paso que fallaba no abortaba el despliegue, que terminaba imprimiendo "completado exitosamente". Además:
  - las migraciones corren **antes** de tocar el contenedor en marcha y abortan el despliegue si fallan, dejando el servicio anterior sirviendo intacto
  - la imagen anterior se etiqueta `:rollback` y se restaura si el contenedor nuevo no levanta o no llega a *healthy*
  - se registra la revisión de esquema antes y después de migrar
  - la verificación del endpoint `/health` deja de ser un *warning* y aborta el despliegue

## [1.26.0] - 2026-09-04

### Added

- Control plane de notificaciones: la API publica a Kafka **después del commit** cuando cambia una asignación unidad-dispositivo, un grant `user_units` o un token push. Tópicos nuevos: `KAFKA_UNIT_DEVICES_UPDATES_TOPIC` (`unit-devices-updates`) y `KAFKA_USER_UNITS_UPDATES_TOPIC` (`user-units-updates`). Cubre `POST/DELETE` de `/user-units`, `/units/{id}/users`, `/units/{id}/device`, `/unit-devices`, `PATCH /devices/{imei}/status` (asignado/devuelto) y register/deactivate de `/user-devices`

## [1.25.0] - 2026-09-03

### Added

- Fase 1 — aislamiento del plano de datos:
  - `devices.device_ref` y `units.unit_ref`: identificadores opacos (UUIDv4) para direccionar dispositivos y unidades sin exponer el IMEI. `device_id` **es** el IMEI (lo renombró la migración 005), así que hoy acaba en los logs de acceso de uvicorn y del ALB y en cabeceras `Referer`. Las columnas se añaden; `device_id` y `units.id` siguen existiendo y funcionando (migración `025`)
  - `app/utils/data_token.py`: emisión de data tokens PASETO **v4.public** (Ed25519). admin-api firma, siscom-api solo verifica — asimétrico a propósito: con v4.local el verificador también podría firmar
  - `app/services/scope_store.py`: el alcance se materializa en Valkey (`dt:scope:<ref>`), con TTL por encima del token. Las claves del índice de revocación por propietario se derivan por HMAC, de modo que Valkey nunca revela de quién es un alcance
  - `POST /auth/data-token` y data token adjunto al login. El plano de datos no puede impedir iniciar sesión: sin Valkey el login sigue funcionando y el cliente reintenta contra ese endpoint
  - Autorización temporal: el alcance lleva ventanas `[from, to)`; una petición parcialmente cubierta se recorta al rango autorizado en vez de rechazarse, y `to: null` significa ventana abierta (datos en vivo autorizados)
  - Revocación: `DELETE /units/{id}/share-location` invalida los enlaces emitidos con el formato nuevo
  - ADR-005 documenta el diseño y la secuencia de despliegue

## [1.24.0] - 2026-08-25

### Added

- Cotización en servidor para los cobros de Stripe: el importe deja de venir del cliente y se calcula en el backend (PR #45)
- Idempotencia de peticiones (`app/services/idempotency_service.py`, migración `021_api_idempotency`) para que un reintento de cobro no genere un segundo cargo (PR #45)
- Servicio de renovaciones de suscripción (`app/services/renewal_service.py`, migración `022_subscription_renewal`) (PR #45)
- Comprobante interno en PDF (`app/services/receipt_pdf.py`, `app/services/invoice_numbering.py`) (PR #45)
- Perfiles fiscales por cuenta (migración `024_account_tax_profiles`) y CFDI emitido **a petición**, no en cada cobro (PR #45)
- `app/services/money.py` y `app/db/locks.py`; esquema de métodos de pago reestructurado (migración `023_payment_methods_schema`) (PR #45)
- Guía `docs/guides/pagos-flujo-completo.md` (PR #45)

### Changed

- Stripe y Facturapi pasan a ser **opcionales**: sin claves en el ambiente el servicio arranca igual y esas integraciones quedan inactivas (PR #45)

## [1.23.1] - 2026-08-08

### Fixed

- `ALLOWED_ORIGINS` en formato CSV ya no rompe el arranque. El campo estaba declarado como `list[str]`, así que `EnvSettingsSource` corría `json.loads` sobre el valor crudo antes de que se ejecutara el validador `parse_allowed_origins`: cualquier CSV —o una cadena vacía— reventaba con `SettingsError` y tiraba el contenedor. Ahora se anota como `Annotated[list[str], NoDecode]` y el validador existente recibe el string sin tocar (PR #38)
- Guía de deploy: las variables de GitHub viven en el environment `test`, no a nivel repositorio. Una variable creada en el scope equivocado se ignora en silencio, porque las de environment tienen precedencia (PR #38)

### Added

- `tests/test_config.py`: cobertura del parseo de `ALLOWED_ORIGINS` desde variables de entorno — CSV, JSON array, espacios, slash final, duplicados, valores en blanco, JSON malformado y el default (PR #38)
- Troubleshooting del `SettingsError` de `ALLOWED_ORIGINS` y del scope de variables en `docs/guides/github-actions-deployment.md` (PR #38)

### Changed

- `pydantic-settings` 2.1.0 → 2.15.0. `NoDecode` se agregó en 2.3.0; el pin previo era de diciembre 2023, 14 minors atrás de `pydantic==2.12.5` (PR #38)

## [1.23.2] - 2026-08-09

### Fixed

- `KAFKA_TEAM_RULES_TOPIC` ya llega al contenedor. La variable estaba declarada en `app/core/config.py` y `TeamRulesKafkaProducer` la leía vía `settings`, pero no se propagaba en ningún compose ni en `deploy.yml`: el topic de teams era en la práctica un hardcode y no se podía cambiar sin reconstruir la imagen, a diferencia de los otros cuatro topics de Kafka. Se añade a `.env.example`, ambos compose y a las tres apariciones de `deploy.yml` —bloque `env`, lista `envs:` del `ssh-action` y el heredoc que escribe el `.env` remoto— (PR #40)

## [1.23.3] - 2026-08-10

### Fixed

- `POST /auth/verify-email` ya no devuelve 500 cuando el usuario ya existe en Cognito. Esa rama llamaba a `admin_update_user_attributes` solo con `email_verified`, y Cognito exige que `email` viaje en la misma llamada: la excepción `InvalidParameterException` dejaba el correo sin verificar. Se incluye `email` junto a `email_verified` (PR #42)
