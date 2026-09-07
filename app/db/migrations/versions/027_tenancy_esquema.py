"""Tenancy: arbol de cuentas, capabilities comerciales, dominios y branding

Revision ID: 027_tenancy_esquema
Revises: 026_reconciliacion
Create Date: 2026-09-07 00:00:00.000000

Rebanada A de la Fase 2 (ver §3, §4, §11 y §23 del documento de arquitectura).

QUE ES Y QUE NO ES
==================
Es **solo esquema**. Ningun modelo, ningun endpoint y ningun servicio de este
repositorio conoce todavia estos objetos: el codigo actual sigue insertando
`accounts` sin `account_path` ni `account_type` y no consulta ninguna de las
tres tablas nuevas. Esa es la mitad "expand" del expand/contract (§18), y es lo
que permite que esta migracion viaje sola, se despliegue sola y se quede
esperando indefinidamente a la rebanada B — modelos, resolucion de capabilities
con techo descendente y `GET /tenant-config`.

Por eso mismo el comparador de deriva no puede probar lo de aqui: solo mira que
el esquema contenga lo que los modelos esperan, y los modelos aun no esperan
nada. Lo que si prueba, y es lo que importa hoy, es que esta migracion aplica
limpia sobre el esquema real de produccion. El comportamiento de los triggers
lo cubre `tests/test_tenancy_esquema.py`.

EL ARBOL
========
El tenant es la `Account` (§3): no se crea entidad nueva. Se materializa el
camino de ancestros en `account_path` para que "todo lo que cuelga de Mero
Mero" sea una comparacion indexada y no un recorrido recursivo por
`parent_account_id`.

`account_path` es un **`uuid[]` con la cadena de ancestros, la propia cuenta
incluida como ultimo elemento**, con indice GIN. Las dos consultas de la Fase 2
salen de ahi:

    -- el subarbol de una cuenta (aislamiento entre clientes)
    WHERE account_path @> ARRAY[:account_id]::uuid[]

    -- sus ancestros (techo descendente de capabilities, §4)
    WHERE id = ANY(:account_path)

`uuid[]` y no `ltree`, que es lo que decia §3 — ver
`docs/architecture/adr/006-camino-materializado-en-uuid.md`. Medido sobre un
arbol de 44 041 cuentas y 480 000 unidades, las dos codificaciones empatan en la
consulta que de verdad importa (16.4 ms contra 15.8 ms, dominadas por el join),
asi que deciden tres cosas que no son rendimiento: `ltree` exige `CREATE
EXTENSION`, que a su vez exige un privilegio que `siscom_migrator` no tiene;
sus etiquetas no admiten guiones, asi que el UUID entra codificado y hay que
reconstruirlo en cada frontera; y la politica RLS futura necesitaria el camino
entero del actor serializado en un GUC en vez de un solo id.

EL INVARIANTE, Y POR QUE VA ANCLADO
===================================
`@>` casa un elemento **en cualquier posicion**, no un prefijo. Eso es
exactamente lo que se quiere —pertenencia al subarbol— pero solo vale mientras
el array sea de verdad la cadena de ancestros. Un id suelto ahi dentro seria un
falso positivo en una comprobacion de autorizacion, que es la peor clase de
fallo posible en esta tabla.

Por eso hay dos defensas, y no son la misma en distinto sitio:

  - **Los triggers.** `accounts_tenancy_before` (BEFORE INSERT/UPDATE)
    construye el camino desde el del padre, rechaza ciclos y rechaza
    profundidad > 5. Como `account_path` esta en su `UPDATE OF`, escribirlo a
    mano no falla: se recalcula y se ignora. `accounts_tenancy_after` (AFTER
    UPDATE) propaga a los hijos con una reasignacion que no cambia nada
    (`parent_account_id = parent_account_id`) y deja que el trigger BEFORE de
    cada hijo recalcule; la recursion es la profundidad del subarbol, acotada
    en 5.
  - **La restriccion** `ck_accounts_camino_termina_en_si_misma`, que ancla el
    ultimo elemento a `id`. No es redundante con lo anterior: hay maneras
    normales de que el trigger no corra —una restauracion o una carga masiva
    con `session_replication_role = replica`, un `DISABLE TRIGGER` en una
    sesion de soporte— y la restriccion sigue ahi en las tres.

Las dos capas tienen test propio, por separado.

Se hace en la base y no en el codigo a proposito: `account_path` es el predicado
de aislamiento entre clientes (§3). Un invariante del que depende quien ve los
datos de quien no puede quedarse en una capa que se puede saltar con un INSERT
manual, un script de soporte o un endpoint que se olvide de llamarlo.

QUE AÑADE
=========
  accounts.parent_account_id   uuid FK a accounts, NULL = raiz
  accounts.account_type        PLATFORM | RESELLER | CUSTOMER, por defecto CUSTOMER
  accounts.account_path        uuid[] NOT NULL, mantenido por trigger, indice GIN
  account_capabilities         limites comerciales por cuenta (§4)
  tenant_domains               hostname -> cuenta de marca (§7, §8)
  tenant_branding              borrador y publicado del tema por tenant (§7)
  capabilities                 cuatro codigos comerciales sembrados

Todo aditivo e idempotente: correrla dos veces no hace nada la segunda. No
necesita extensiones ni privilegios que la credencial de migraciones no tenga.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "027_tenancy_esquema"
down_revision: Union[str, None] = "026_reconciliacion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Profundidad maxima del arbol de cuentas (§3). Geminis -> partner -> subpartner
# -> cliente -> subcliente. Es un limite de cordura, no de producto: sin el, un
# bucle en un script de alta hace crecer los caminos sin techo y el indice con
# ellos.
PROFUNDIDAD_MAXIMA = 5

_TIPOS_DE_CUENTA = ("PLATFORM", "RESELLER", "CUSTOMER")

_CAPABILITIES_COMERCIALES = [
    (
        "white_label_enabled",
        "La cuenta puede servirse bajo marca propia (dominio + branding)",
        "bool",
    ),
    (
        "max_custom_domains",
        "Numero maximo de dominios personalizados verificados",
        "int",
    ),
    (
        "max_sub_accounts",
        "Numero maximo de cuentas colgando de esta en el arbol",
        "int",
    ),
    (
        "can_resell",
        "La cuenta puede crear subcuentas y administrarlas (reventa delegada)",
        "bool",
    ),
]


def _existe_columna(conn, tabla: str, columna: str) -> bool:
    return bool(
        conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :t "
                "AND column_name = :c"
            ),
            {"t": tabla, "c": columna},
        ).scalar()
    )


def _existe_tabla(conn, tabla: str) -> bool:
    return bool(
        conn.execute(
            sa.text("SELECT to_regclass(:t)"), {"t": f"public.{tabla}"}
        ).scalar()
    )


def _existe_restriccion(conn, nombre: str) -> bool:
    return bool(
        conn.execute(
            sa.text("SELECT 1 FROM pg_constraint WHERE conname = :n"), {"n": nombre}
        ).scalar()
    )


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # 1. Columnas del arbol en `accounts`
    # ------------------------------------------------------------------
    if not _existe_columna(conn, "accounts", "parent_account_id"):
        op.execute("""
            ALTER TABLE public.accounts
              ADD COLUMN parent_account_id uuid NULL
              REFERENCES public.accounts(id) ON DELETE RESTRICT
            """)

    if not _existe_columna(conn, "accounts", "account_type"):
        # 'account_type' y no 'type': la tabla ya nombra su propia columna
        # 'account_name', y 'type' obliga a comillas en SQL crudo.
        #
        # CHECK y no un tipo ENUM: los ENUM de esta base solo se pueden ampliar
        # con ALTER TYPE, que exige ser dueño del tipo y no admite rollback
        # dentro de una transaccion. Un CHECK se cambia con una migracion
        # normal, y aqui el conjunto de valores es de producto, no de motor.
        valores = ", ".join(f"'{t}'" for t in _TIPOS_DE_CUENTA)
        op.execute(f"""
            ALTER TABLE public.accounts
              ADD COLUMN account_type text NOT NULL DEFAULT 'CUSTOMER',
              ADD CONSTRAINT ck_accounts_account_type
                CHECK (account_type IN ({valores}))
            """)

    if not _existe_columna(conn, "accounts", "account_path"):
        # Nace NULL: el backfill de mas abajo la llena y solo entonces pasa a
        # NOT NULL. Al reves, la propia migracion no podria correr.
        op.execute("ALTER TABLE public.accounts ADD COLUMN account_path uuid[] NULL")

    # ------------------------------------------------------------------
    # 2. Los triggers que mantienen el camino
    # ------------------------------------------------------------------
    op.execute(f"""
        CREATE OR REPLACE FUNCTION public.accounts_tenancy_before()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $fn$
        DECLARE
          path_padre uuid[];
        BEGIN
          IF NEW.parent_account_id IS NULL THEN
            NEW.account_path := ARRAY[NEW.id];
          ELSE
            -- Rama propia, y no un caso mas del ciclo de abajo, solo por el
            -- mensaje: en soporte no es lo mismo leer 'es su propio padre' que
            -- 'ciclo en el arbol'.
            IF NEW.parent_account_id = NEW.id THEN
              RAISE EXCEPTION USING
                ERRCODE = '23514',
                MESSAGE = 'la cuenta ' || NEW.id || ' no puede ser su propio padre';
            END IF;

            SELECT a.account_path INTO path_padre
              FROM public.accounts a
             WHERE a.id = NEW.parent_account_id;

            IF path_padre IS NULL THEN
              RAISE EXCEPTION USING
                ERRCODE = '23503',
                MESSAGE = 'la cuenta padre ' || NEW.parent_account_id ||
                          ' no existe o no tiene account_path';
            END IF;

            -- Ciclo: el padre nuevo cuelga de la propia cuenta que se mueve.
            -- No hace falta distinguir INSERT de UPDATE — en un INSERT el id es
            -- nuevo y no puede estar en el camino de nadie.
            IF NEW.id = ANY (path_padre) THEN
              RAISE EXCEPTION USING
                ERRCODE = '23514',
                MESSAGE = 'ciclo en el arbol de cuentas: ' || NEW.id ||
                          ' ya es ancestro de ' || NEW.parent_account_id;
            END IF;

            NEW.account_path := path_padre || NEW.id;
          END IF;

          IF array_length(NEW.account_path, 1) > {PROFUNDIDAD_MAXIMA} THEN
            RAISE EXCEPTION USING
              ERRCODE = '23514',
              MESSAGE = 'profundidad maxima del arbol de cuentas ({PROFUNDIDAD_MAXIMA}) superada: ' ||
                        array_length(NEW.account_path, 1) || ' niveles';
          END IF;

          RETURN NEW;
        END;
        $fn$
        """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.accounts_tenancy_after()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $fn$
        BEGIN
          -- Reasignacion que no cambia nada: existe para disparar el trigger
          -- BEFORE de cada hijo, que recalcula su camino desde el del padre
          -- —ya actualizado en esta misma transaccion— y a su vez propaga a
          -- los suyos. No se reescribe el subarbol de una sola pasada porque
          -- un UPDATE masivo lee el snapshot del inicio de la sentencia y los
          -- nietos recalcularian sobre el camino viejo del padre.
          UPDATE public.accounts
             SET parent_account_id = parent_account_id
           WHERE parent_account_id = NEW.id;
          RETURN NULL;
        END;
        $fn$
        """)

    op.execute("DROP TRIGGER IF EXISTS accounts_tenancy_before ON public.accounts")
    op.execute("""
        CREATE TRIGGER accounts_tenancy_before
        BEFORE INSERT OR UPDATE OF id, parent_account_id, account_path
        ON public.accounts
        FOR EACH ROW
        EXECUTE FUNCTION public.accounts_tenancy_before()
        """)

    op.execute("DROP TRIGGER IF EXISTS accounts_tenancy_after ON public.accounts")
    op.execute("""
        CREATE TRIGGER accounts_tenancy_after
        AFTER UPDATE ON public.accounts
        FOR EACH ROW
        WHEN (OLD.account_path IS DISTINCT FROM NEW.account_path)
        EXECUTE FUNCTION public.accounts_tenancy_after()
        """)

    # ------------------------------------------------------------------
    # 3. Backfill, NOT NULL y el ancla del invariante
    # ------------------------------------------------------------------
    # Todas las cuentas existentes son raices: nadie tiene padre todavia.
    # `account_type` se queda en el default 'CUSTOMER' a proposito — cual de
    # las cuentas es la PLATFORM de Geminis es una decision de negocio, no algo
    # que se pueda deducir del esquema. La toma la rebanada B.
    op.execute("""
        UPDATE public.accounts
           SET account_path = ARRAY[id]
         WHERE account_path IS NULL
        """)
    op.execute("ALTER TABLE public.accounts ALTER COLUMN account_path SET NOT NULL")

    if not _existe_restriccion(conn, "ck_accounts_camino_termina_en_si_misma"):
        # Sin esto, `account_path` podria contener cualquier lista de ids y
        # `@>` daria por buena una pertenencia inventada. Ver la cabecera.
        op.execute("""
            ALTER TABLE public.accounts
              ADD CONSTRAINT ck_accounts_camino_termina_en_si_misma
              CHECK (account_path[array_length(account_path, 1)] = id)
            """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_accounts_account_path
          ON public.accounts USING gin (account_path)
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_accounts_parent_account_id
          ON public.accounts (parent_account_id)
          WHERE parent_account_id IS NOT NULL
        """)

    # ------------------------------------------------------------------
    # 4. account_capabilities — el nivel comercial (§4)
    # ------------------------------------------------------------------
    if not _existe_tabla(conn, "account_capabilities"):
        op.execute("""
            CREATE TABLE public.account_capabilities (
              id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              account_id    uuid NOT NULL
                            REFERENCES public.accounts(id) ON DELETE CASCADE,
              capability_id uuid NOT NULL
                            REFERENCES public.capabilities(id),
              value_int     integer NULL,
              value_bool    boolean NULL,
              value_text    text NULL,
              reason        text NULL,
              expires_at    timestamptz NULL,
              created_at    timestamptz NOT NULL DEFAULT now(),
              updated_at    timestamptz NOT NULL DEFAULT now(),
              CONSTRAINT uq_account_capabilities
                UNIQUE (account_id, capability_id),
              -- organization_capabilities no lo tiene y por eso admite dos
              -- overrides contradictorios de la misma capability. Aqui no.
              CONSTRAINT ck_account_capabilities_un_valor
                CHECK (num_nonnulls(value_int, value_bool, value_text) = 1)
            )
            """)
        op.execute("""
            CREATE INDEX ix_account_capabilities_account_id
              ON public.account_capabilities (account_id)
            """)

    # ------------------------------------------------------------------
    # 5. tenant_domains — el hostname resuelve marca, nunca autoriza (§7)
    # ------------------------------------------------------------------
    if not _existe_tabla(conn, "tenant_domains"):
        op.execute("""
            CREATE TABLE public.tenant_domains (
              id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              account_id         uuid NOT NULL
                                 REFERENCES public.accounts(id) ON DELETE CASCADE,
              hostname           text NOT NULL,
              is_primary         boolean NOT NULL DEFAULT false,
              status             text NOT NULL DEFAULT 'PENDING',
              verification_token text NULL,
              verified_at        timestamptz NULL,
              created_at         timestamptz NOT NULL DEFAULT now(),
              updated_at         timestamptz NOT NULL DEFAULT now(),
              -- Global, no por cuenta: un hostname pertenece exactamente a una
              -- cuenta. Sin esto, dos marcas reclaman el mismo Host y quien
              -- resuelve elige, que es una decision que no deberia existir.
              CONSTRAINT uq_tenant_domains_hostname UNIQUE (hostname),
              -- El Host de una peticion llega en la caja que mande el cliente.
              -- Guardar solo minusculas hace que la busqueda sea una igualdad
              -- y no un lower() que no usaria el indice.
              CONSTRAINT ck_tenant_domains_hostname_minusculas
                CHECK (hostname = lower(hostname)),
              CONSTRAINT ck_tenant_domains_hostname_sin_espacios
                CHECK (hostname !~ '\\s' AND length(hostname) BETWEEN 3 AND 253),
              CONSTRAINT ck_tenant_domains_status
                CHECK (status IN ('PENDING', 'VERIFIED', 'DISABLED')),
              -- Verificado y sin fecha, o sin verificar y con ella, son dos
              -- formas de mentir sobre lo mismo.
              CONSTRAINT ck_tenant_domains_verificado_con_fecha
                CHECK ((status = 'VERIFIED') = (verified_at IS NOT NULL))
            )
            """)
        op.execute("""
            CREATE UNIQUE INDEX uq_tenant_domains_primario
              ON public.tenant_domains (account_id)
              WHERE is_primary
            """)
        op.execute("""
            CREATE INDEX ix_tenant_domains_account_id
              ON public.tenant_domains (account_id)
            """)

    # ------------------------------------------------------------------
    # 6. tenant_branding — borrador y publicado (§7)
    # ------------------------------------------------------------------
    if not _existe_tabla(conn, "tenant_branding"):
        # Los tokens van en jsonb y no en columnas: el juego de tokens todavia
        # va a cambiar durante la Fase 4, y una columna por token significa una
        # migracion por token. La validacion —contraste WCAG AA, saneado de
        # assets— es de aplicacion y vive en la rebanada B.
        #
        # `draft` y `published` separados desde el principio: es barato ahora y
        # molesto despues, porque implica reescribir cada lectura.
        op.execute("""
            CREATE TABLE public.tenant_branding (
              account_id   uuid PRIMARY KEY
                           REFERENCES public.accounts(id) ON DELETE CASCADE,
              brand_name   text NULL,
              published    jsonb NOT NULL DEFAULT '{}'::jsonb,
              draft        jsonb NULL,
              published_at timestamptz NULL,
              published_by uuid NULL REFERENCES public.users(id),
              created_at   timestamptz NOT NULL DEFAULT now(),
              updated_at   timestamptz NOT NULL DEFAULT now(),
              CONSTRAINT ck_tenant_branding_published_objeto
                CHECK (jsonb_typeof(published) = 'object'),
              CONSTRAINT ck_tenant_branding_draft_objeto
                CHECK (draft IS NULL OR jsonb_typeof(draft) = 'object')
            )
            """)

    # ------------------------------------------------------------------
    # 7. Los codigos de capability comerciales
    # ------------------------------------------------------------------
    # Sembrar la definicion es aditivo: sin filas en account_capabilities no
    # cambia nada para nadie. Deja la rebanada B como puro codigo.
    #
    # `self_signup_mode` NO se siembra: sus modos y sus defensas siguen sin
    # definir (§12, §23), y un codigo sin semantica acordada invita a que
    # alguien le invente una.
    for code, descripcion, tipo in _CAPABILITIES_COMERCIALES:
        conn.execute(
            sa.text("""
                INSERT INTO public.capabilities (code, description, value_type)
                VALUES (:code, :descripcion, :tipo)
                ON CONFLICT (code) DO NOTHING
                """),
            {"code": code, "descripcion": descripcion, "tipo": tipo},
        )


def downgrade() -> None:
    conn = op.get_bind()

    op.execute("DROP TABLE IF EXISTS public.tenant_branding")
    op.execute("DROP TABLE IF EXISTS public.tenant_domains")
    op.execute("DROP TABLE IF EXISTS public.account_capabilities")

    # Solo las que nadie referencia: si un plan o una organizacion ya usa la
    # definicion, borrarla se llevaria por delante datos que esta migracion no
    # creo.
    codigos = [c for c, _d, _t in _CAPABILITIES_COMERCIALES]
    conn.execute(
        sa.text("""
            DELETE FROM public.capabilities c
             WHERE c.code = ANY(:codigos)
               AND NOT EXISTS (
                     SELECT 1 FROM public.plan_capabilities pc
                      WHERE pc.capability_id = c.id)
               AND NOT EXISTS (
                     SELECT 1 FROM public.organization_capabilities oc
                      WHERE oc.capability_id = c.id)
            """),
        {"codigos": codigos},
    )

    op.execute("DROP TRIGGER IF EXISTS accounts_tenancy_after ON public.accounts")
    op.execute("DROP TRIGGER IF EXISTS accounts_tenancy_before ON public.accounts")
    op.execute("DROP FUNCTION IF EXISTS public.accounts_tenancy_after()")
    op.execute("DROP FUNCTION IF EXISTS public.accounts_tenancy_before()")

    op.execute("DROP INDEX IF EXISTS public.ix_accounts_parent_account_id")
    op.execute("DROP INDEX IF EXISTS public.ix_accounts_account_path")

    op.execute(
        "ALTER TABLE public.accounts "
        "DROP CONSTRAINT IF EXISTS ck_accounts_camino_termina_en_si_misma"
    )
    op.execute(
        "ALTER TABLE public.accounts "
        "DROP CONSTRAINT IF EXISTS ck_accounts_account_type"
    )
    op.execute("ALTER TABLE public.accounts DROP COLUMN IF EXISTS account_path")
    op.execute("ALTER TABLE public.accounts DROP COLUMN IF EXISTS account_type")
    op.execute("ALTER TABLE public.accounts DROP COLUMN IF EXISTS parent_account_id")
