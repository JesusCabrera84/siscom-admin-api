# ADR-006: El camino materializado del árbol de cuentas va en `uuid[]`, no en `ltree`

**Estado:** Aceptado
**Fecha:** 2026-09-07
**Autores:** Equipo de Desarrollo
**Revisores:** -

## Contexto

La Fase 2 introduce el árbol de cuentas de profundidad arbitraria (§3 del
documento de arquitectura): `accounts.parent_account_id` más un camino
materializado `account_path` que permite resolver un subárbol sin recorrer la
tabla nodo a nodo.

Ese camino no es una comodidad de consulta: **es el predicado de aislamiento
entre clientes**. Toda consulta que devuelva datos de cliente acaba filtrando
por él, y el destino declarado en §3 es usarlo en políticas RLS.

§3 lo especificaba como `ltree` con índice GIST. Este ADR revisa esa elección
antes de que exista código que dependa de ella, y la cambia.

La otra mitad del mecanismo va en la dirección contraria: la resolución de
capabilities comerciales **camina hacia arriba** por los ancestros para aplicar
el techo descendente (§4). Las dos direcciones pesan en la decisión.

## Lo que se midió

Árbol con la forma del negocio real —1 cuenta plataforma, 40 marcas, 4 000
subcuentas, 40 000 clientes; 44 041 cuentas— y 480 000 unidades colgando de las
hojas. PostgreSQL 15.

| | `ltree` + GIST | `uuid[]` + GIN | recursivo sobre `parent_id` |
|---|---|---|---|
| Tamaño del índice | 14 MB | **3.4 MB** | 0 |
| Subárbol de una marca (1 101 cuentas) | 0.50 ms · 48 buffers | 0.25 ms · **6 buffers** | 3.2 ms · **3 210 buffers** |
| Ancestros de una hoja | 0.21 ms · 13 buf | 0.06 ms · 16 buf (*index only*) | — |
| **Unidades del subárbol (join contra 480 k)** | **16.4 ms** | **15.8 ms** | — |
| Mover una rama de 1 101 cuentas | 24.6 ms | 19.2 ms | — |

Dos lecturas, y la segunda es la que decide:

1. **Materializar el camino está justificado.** El recursivo hace un *index
   lookup* por nodo: 3 210 buffers contra 6. Es la diferencia que importa.
2. **Entre las dos codificaciones, el rendimiento no decide.** En la consulta que
   de verdad se ejecuta —la que lleva el join contra la tabla grande— el coste lo
   domina el escaneo de `unidades`; las dos resuelven el subárbol en menos de
   0.3 ms y la diferencia final es ruido de medición.

## Decisión

**`account_path uuid[]` con la cadena de ancestros, la propia cuenta incluida
como último elemento, e índice GIN.**

```sql
-- subárbol: el aislamiento entre clientes
WHERE account_path @> ARRAY[:account_id]::uuid[]

-- ancestros: el techo descendente de capabilities
WHERE id = ANY (:account_path)
```

Como el rendimiento empata, deciden tres cosas que no son rendimiento:

### 1. `ltree` exige un privilegio que la credencial de migraciones no tiene

`CREATE EXTENSION ltree` exige `CREATE` sobre la base de datos.
`siscom_migrator` solo tiene `CONNECT` (`database-siscom/initdb/01_roles.sql`).
Comprobado contra un rol acotado igual que el productivo:

```
ERROR:  permission denied to create extension "ltree"
HINT:  Must have CREATE privilege on current database to create this extension.
```

Eso convierte cada entorno nuevo en un paso manual, con otra credencial y otra
persona. En un repositorio donde [ADR-004](./004-separacion-claves-paseto.md) y
§19 documentan que la propiedad del DDL fue precisamente el problema, y donde
§21 registra que **todavía no existe camino de base vacía a `head`**, añadir un
prerrequisito no versionado va en la dirección contraria.

`uuid[]` y GIN son tipos del núcleo. No hay prerrequisito.

### 2. Una etiqueta de `ltree` no admite guiones, así que el UUID entra codificado

En PostgreSQL 15 una etiqueta de `ltree` solo admite `[A-Za-z0-9_]`. El UUID hay
que guardarlo sin guiones, y el camino deja de ser dato para pasar a ser una
cadena que hay que decodificar en cada frontera:

```sql
-- ltree: reconstruir el UUID a mano para volver a `accounts`
SELECT id FROM accounts WHERE id::text = ANY (
  SELECT regexp_replace(l, '^(.{8})(.{4})(.{4})(.{4})(.{12})$', '\1-\2-\3-\4-\5')
    FROM unnest(string_to_array(account_path::text, '.')) l);

-- uuid[]: el camino ya son los ids
SELECT id FROM accounts WHERE id = ANY (:account_path);
```

Eso no se amortiza: se paga en cada consulta, cada log y cada sesión de soporte
—donde un `3d065c7663a64713bc88cc300130fbd9` hay que re-guionar mentalmente para
cruzarlo con un `account_id`, justo cuando peor viene—. Y en SQLAlchemy, `uuid[]`
es `ARRAY(PGUUID)` nativo, mientras que `ltree` no tiene tipo: obligaría a
`sqlalchemy-utils` o a un `TypeDecorator` propio. El comparador de deriva ya lo
avisaba: `SAWarning: Did not recognize type 'ltree' of column 'account_path'`.

### 3. La política RLS necesita un escalar, no un camino serializado

Es la diferencia más limpia, y §3 declara RLS como destino:

```sql
-- ltree: hay que serializar el camino entero del actor en un GUC de sesión
USING (account_path <@ current_setting('app.actor_path')::ltree)

-- uuid[]: basta con el id del actor
USING (account_path @> ARRAY[current_setting('app.actor_id')::uuid])
```

Con `ltree`, cada petición tiene que construir bien una cadena y puede quedar
desincronizada del árbol. Con `uuid[]`, lo que la sesión necesita es **quién es
el actor**, que se tiene de todos modos. En una política de seguridad, cuanto
menos haya que construir bien, mejor.

## Consecuencias

### El invariante hay que anclarlo, y no estaba en el diseño de `ltree`

`@>` sobre array casa un elemento **en cualquier posición**, mientras que `<@`
sobre `ltree` compara un prefijo estructural. La semántica que se quiere
—pertenencia al subárbol— es la del array, pero solo vale mientras el array sea
de verdad la cadena de ancestros: un id suelto ahí dentro sería un **falso
positivo en una comprobación de autorización**.

La migración pone dos defensas donde `ltree` tenía una:

- `ck_accounts_camino_termina_en_si_misma`:
  `CHECK (account_path[array_length(account_path, 1)] = id)`.
- Los triggers como único escritor. `account_path` está en el `UPDATE OF` del
  trigger BEFORE, así que escribirlo a mano no falla: se recalcula y se ignora.

La restricción no es redundante. El trigger se salta de maneras normales —una
restauración o una carga masiva con `session_replication_role = replica`, un
`DISABLE TRIGGER` en una sesión de soporte— y la restricción sigue ahí en los
tres casos. Ambas capas están cubiertas por tests separados.

### Lo que se pierde

`lquery`, el *pattern matching* sobre la forma del camino (`*.foo.*{1,3}`), y el
orden lexicográfico por etiqueta. Las dos son funciones de taxonomías con
etiquetas legibles. Con un UUID por etiqueta no aportan nada, y no hay ningún uso
previsto de ellas.

### Coste operativo

GIN escribe a través de una **lista pendiente** (`fastupdate=on` por defecto,
comprobado en el índice creado). Eso abarata cada inserción, pero a cambio una de
ellas paga el volcado entero de vez en cuando, y las búsquedas recorren la lista
pendiente hasta que se vuelca. Con 44 k cuentas y cambios de árbol infrecuentes es
irrelevante, y la medición de reparentado sale a favor del array de todas formas
(19.2 ms contra 24.6 ms). Si algún día dejara de serlo, se apaga con
`ALTER INDEX ... SET (fastupdate = off)` — no obliga a cambiar la codificación.

### Cuándo habría que revisar esta decisión

Si el camino pasara a llevar **etiquetas legibles y estables** en vez de UUID
—por ejemplo si el árbol se expusiera al usuario como una ruta con nombres—,
`ltree` recuperaría sus dos ventajas de golpe y tocaría reconsiderar.

## Alternativas descartadas

- **Solo lista de adyacencia, con `WITH RECURSIVE`.** Es el punto de partida y
  sigue siendo la fuente de verdad; lo que se descarta es usarlo como camino de
  consulta: 3 210 buffers contra 6, en un predicado que se evalúa en cada
  petición.
- **Camino en `text` con `LIKE 'prefijo%'`.** Funciona, pero el índice solo se usa
  si es `text_pattern_ops` o la base está en collation C. Cuando eso se olvida, el
  fallo no es un error: es un *sequential scan* en cada comprobación de
  autorización.
- **Tabla de cierre.** La respuesta portable de libro de texto, y la mejor si
  hiciera falta guardar metadatos por par ancestro-descendiente. Aquí no hacen
  falta, y cuesta una tabla más y reescribir subárbol × profundidad filas en cada
  movimiento.
- **Nested sets.** Descartada: cualquier alta reescribe media tabla.

## Referencias

- §3 y §4 del documento de arquitectura del white-label (a los que este ADR
  corrige en la codificación, no en el modelo).
- `app/db/migrations/versions/027_tenancy_esquema.py`
- `tests/test_tenancy_esquema.py`
- `docs/runbooks/desplegar-tenancy.md`
