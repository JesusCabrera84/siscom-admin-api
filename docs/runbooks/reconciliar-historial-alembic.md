# Runbook — reconciliar el historial de alembic

**Estado:** el diagnóstico está hecho y medido. La reconciliación **no** se ha
aplicado: falta correr la sonda contra producción (paso 2), que es una decisión
y una credencial que no están en este repositorio.

## El problema, en una frase

El esquema tuvo dos gestores que nunca se hablaron: `database-siscom/initdb`
creó 73 tablas, `siscom-admin-api` evolucionó lo suyo con 25 migraciones de
alembic, y nadie stampeó la línea base. Por eso `alembic_version` no existe y
`alembic upgrade head` sobre la base real intenta aplicar desde la `001`.

## Lo que se midió (5 de septiembre de 2026)

Reproducido en local con `./scripts/db-local.sh` y el `initdb` de
`database-siscom`, que da exactamente las 73 tablas del snapshot productivo.

| Escenario | Resultado |
|---|---|
| `alembic upgrade head` sobre base **vacía** | ❌ `relation "users" does not exist` en la `001` |
| `alembic upgrade head` sobre el esquema de `initdb`, sin propiedad | ❌ `must be owner of table users` |
| ídem, **con** propiedad concedida | ❌ `relation "clients" does not exist` en la `001` |

Tres conclusiones:

1. **La cadena de alembic no es una definición de esquema, es un delta.** No
   existe camino de base vacía a `head`. El plan de "el bootstrap de entornos
   nuevos pasa a ser `alembic upgrade head`" no funciona sin una migración de
   línea base que primero declare el estado de partida.
2. **El fallo por propiedad fue una casualidad afortunada.** Es lo único que
   detuvo el incidente del 3 de septiembre. Concedida la propiedad, la `001`
   avanza un paso más y falla por `clients`, una tabla que se renombró a
   `organizations` hace mucho: el `initdb` es *posterior* a varias migraciones
   de la cadena.
3. **El resultado no es monótono.** De 25 marcadores, 15 están presentes en el
   snapshot y 10 no, pero con huecos: falta la `004` y faltan de la `016` a la
   `022`, mientras que la `023` sí está. Ningún `alembic stamp` único deja el
   historial correcto.

> El hueco `016`–`022` con la `023` presente tiene explicación: `initdb`
> incluye `03_payment.sql`, que crea las tablas de pagos por su cuenta. Es
> decir, **la presencia de un marcador no prueba que la migración corriera** —
> prueba que el efecto está. Para decidir el `stamp` es lo que importa, pero
> conviene no confundir las dos cosas.

## Procedimiento

### 1. Levantar la réplica local

```bash
./scripts/db-local.sh up
# opcional, para partir del esquema real:
for f in ../database-siscom/initdb/0[2-6]*.sql; do
  docker exec -i siscom-admin-db-local psql -q -U postgres -d siscom-dev < "$f"
done
```

Con un dump productivo, que es lo que de verdad hace falta para decidir:

```bash
./scripts/db-local.sh restore ~/dumps/siscom-prod.sql
./scripts/db-local.sh anonymize   # antes de dejarlo en disco
```

### 2. Correr la sonda contra PRODUCCIÓN — pendiente

Es **de solo lectura**: abre la conexión en `readonly`, no escribe nada, y
tarda segundos. Es el único paso que no se puede hacer desde el repositorio.

```bash
export DB_HOST=<host de produccion> DB_PORT=5432 DB_NAME=siscom-dev
export DB_USER=<usuario de solo lectura> DB_PASSWORD=<...>
python scripts/alembic-probe.py
```

La sonda dice una de tres cosas:

- **Prefijo limpio y completo** → `alembic stamp 025_device_and_unit_refs` y listo.
- **Prefijo limpio hasta N** → `alembic stamp N`, y `upgrade head` aplica el resto.
- **No monótono** → hace falta una migración de línea base. Es lo que da el
  snapshot local, y lo más probable en producción.

### 3. Según el veredicto

**Si es un prefijo limpio**, la reconciliación es una línea. Hacerla con la
base respaldada y verificando después que `/health` devuelve el
`schema_revision` esperado.

**Si no es monótono** (lo esperable), el trabajo es:

1. Escribir `000_baseline.py`, una migración cuyo `upgrade()` es un no-op
   condicionado —el esquema ya existe— y cuyo valor es declarar el punto de
   partida. `001_update_user` pasa a tener `down_revision = "000_baseline"`.
2. Reescribir las migraciones cuyo efecto ya está presente para que sean
   idempotentes (`IF NOT EXISTS`, comprobación por `inspector`). La `015` ya
   lo hace y sirve de modelo.
3. `alembic stamp 000_baseline` en producción.
4. `alembic upgrade head`, primero contra la réplica local restaurada del dump
   productivo, y solo después contra producción.

### 4. Solo entonces, la credencial DDL

**No conceder DDL antes de reconciliar.** Un `GRANT CREATE ON SCHEMA public`
fue exactamente lo que hizo que el despliegue intentara aplicar desde la `001`
sobre un esquema completo. El orden es: reconciliar, verificar en local, y
después crear `DB_MIGRATION_USER`.

El prototipo del rol está en `scripts/db-local/01_roles.sql`. Lleva una
corrección que hay que trasladar a `database-siscom/initdb/01_roles.sql`: el
`ALTER DEFAULT PRIVILEGES` de producción **no lleva `FOR ROLE`**, así que
aplica solo al rol que lo ejecutó. En cuanto las tablas las cree
`siscom_migrator`, el usuario de runtime se queda sin permisos sobre las
nuevas.

## Lo que ya está protegido

- `tests/test_migrations_chain.py` — cabeza única, base única, sin huérfanos ni
  ciclos, todas las revisiones en la cadena principal, `downgrade()` con cuerpo
  real, y prefijo de fichero coherente con el orden. Corre en cada PR.
- `.github/workflows/deploy.yml` — `set -eo pipefail`; las migraciones corren
  **antes** de tocar el contenedor en marcha y abortan el despliegue si fallan,
  dejando el servicio anterior intacto; rollback a la imagen previa si el
  contenedor nuevo no levanta.
- `/health` consulta la base y expone `schema_revision`. Devuelve 503 si la
  base no responde, así que el healthcheck de Docker y el bucle de espera del
  despliegue ya no pueden dar verde sobre una base inservible.

## Lo que sigue abierto

- Correr la sonda contra producción (paso 2).
- La migración de línea base, según el veredicto.
- `DB_MIGRATION_USER` en `database-siscom` y en los secretos del despliegue.
- Comprobar si `events` y `event_types` existen en producción: `/api/v1/events`
  las consulta y no las crea ningún artefacto conocido.
  `SELECT to_regclass('public.events'), to_regclass('public.event_types');`
