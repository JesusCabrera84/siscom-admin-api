# Runbook — desplegar la migración de tenancy (027)

**Estado:** escrita y probada en local contra el esquema productivo. **No se ha
desplegado.**

Corresponde a la **rebanada A de la Fase 2** (§3, §4, §11 y §23 del documento de
arquitectura). Es aditiva pura: ningún modelo, endpoint ni servicio de este
repositorio conoce todavía los objetos que crea. Puede quedarse mergeada y sin
desplegar indefinidamente, y puede desplegarse sin que cambie nada visible.

**No tiene prerrequisitos.** No necesita extensiones, ni privilegios que
`siscom_migrator` no tenga, ni un paso manual previo por parte de nadie. Es
deliberado: ver [ADR-006](../architecture/adr/006-camino-materializado-en-uuid.md),
donde se descarta `ltree` —que sí los habría necesitado— a favor de `uuid[]`.

---

## Qué añade

| Objeto | Qué es |
|---|---|
| `accounts.parent_account_id` | FK a `accounts`, `NULL` = raíz. `ON DELETE RESTRICT` |
| `accounts.account_type` | `PLATFORM` / `RESELLER` / `CUSTOMER`, por defecto `CUSTOMER` |
| `accounts.account_path` | `uuid[] NOT NULL` con la cadena de ancestros, la propia cuenta incluida. Índice GIN |
| `account_capabilities` | Límites comerciales por cuenta (§4) |
| `tenant_domains` | `hostname` → cuenta de marca. `UNIQUE` global |
| `tenant_branding` | Borrador y publicado del tema por tenant (§7) |
| `capabilities` | Cuatro códigos comerciales sembrados |

Las dos consultas que sostiene:

```sql
-- el subárbol de una cuenta: el aislamiento entre clientes
WHERE account_path @> ARRAY[:account_id]::uuid[]

-- sus ancestros: el techo descendente de capabilities
WHERE id = ANY (:account_path)
```

El camino lo mantienen dos triggers y lo ancla una restricción, no la
aplicación. Es deliberado: `account_path` es el predicado de aislamiento entre
clientes (§3), y un invariante del que depende quién ve los datos de quién no
puede vivir en una capa que se salta con un `INSERT` manual o un script de
soporte.

Ninguna cuenta existente cambia de sentido: todas quedan como raíz, con
`account_type = 'CUSTOMER'`. **Cuál es la cuenta `PLATFORM` de Geminis es una
decisión de negocio y la toma la rebanada B**, no esta migración.

---

## Despliegue

```bash
alembic upgrade head
```

Eso es todo.

### Comprobación después

`GET /health` debe reportar la revisión nueva:

```json
{ "schema_revision": "027_tenancy_esquema" }
```

Y el árbol debe quedar plano — todas las cuentas raíz, ninguna sin camino:

```sql
SELECT count(*) FILTER (WHERE account_path IS NULL)            AS sin_camino,
       count(*) FILTER (WHERE array_length(account_path,1) <> 1) AS no_raices,
       count(*) FILTER (WHERE account_path[array_length(account_path,1)] <> id)
                                                               AS camino_roto
  FROM accounts;
-- las tres deben ser 0 justo después de migrar
```

---

## Rollback

```bash
alembic downgrade -1
```

Deja `accounts` con exactamente sus seis columnas originales y borra las tres
tablas nuevas. Probado en
`tests/test_tenancy_esquema.py::test_el_downgrade_deja_accounts_como_estaba`.

Lo único que **no** revierte, a propósito: las definiciones de capability
sembradas solo se borran si nadie las referencia todavía. Si un plan o una
organización ya las usa, se quedan — son datos que esta migración no creó.

Como todo lo que borra es aditivo y sin lectores, el rollback no pierde nada que
exista antes de la rebanada B.

---

## Lo que esta migración deja abierto

- **`self_signup_mode` no se siembra.** Sus modos y sus defensas siguen sin
  acordarse (§12, §23). Un código en la tabla sin semántica acordada invita a que
  alguien le invente una.
- **La rebanada B** —modelos, resolución de capabilities con techo descendente y
  `GET /tenant-config`— va en el release siguiente.
- **Cuidado con `@>`:** casa un elemento en **cualquier posición**, no un
  prefijo. Es lo que se quiere para pertenencia al subárbol, pero significa que
  la corrección depende de que el array sea de verdad la cadena de ancestros. Las
  dos defensas están puestas —el trigger es el único escritor y
  `ck_accounts_camino_termina_en_si_misma` ancla el último elemento—, pero
  cualquier código futuro que escriba `account_path` a mano está haciendo algo
  mal.
