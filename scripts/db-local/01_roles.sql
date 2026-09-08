-- ============================================================
-- Roles del Postgres local — prototipo del reparto de §19.
--
-- Refleja database-siscom/initdb/01_roles.sql MÁS la separación
-- pendiente: un usuario de migraciones con DDL, distinto del de
-- runtime, que hoy no existe (punto 1 de la deuda de migraciones).
--
-- Cuando esto se lleve a database-siscom, este archivo es la fuente.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- El motor productivo es TimescaleDB (database-siscom/Dockerfile:
-- timescale/timescaledb:2.15.1-pg15). initdb/05_fuel.sql llama a
-- create_hypertable(), asi que sin esta extension el esquema no carga entero.
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Usuario de RUNTIME: solo DML. Es el que usa la aplicación.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'siscom') THEN
    CREATE USER siscom WITH PASSWORD 'siscom';
  END IF;
END
$$;

-- Usuario de MIGRACIONES: DDL. Es el único que ejecuta alembic.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'siscom_migrator') THEN
    CREATE USER siscom_migrator WITH PASSWORD 'siscom_migrator';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE "siscom-dev" TO siscom, siscom_migrator;
GRANT USAGE ON SCHEMA public TO siscom;
GRANT USAGE, CREATE ON SCHEMA public TO siscom_migrator;

-- Runtime sobre lo que ya existe.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO siscom;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO siscom;

-- La línea que hace que la separación funcione sin grants manuales tras
-- cada migración: las tablas que cree el migrador nacen con DML para el
-- usuario de runtime.
--
-- Ojo: el ALTER DEFAULT PRIVILEGES de producción NO lleva FOR ROLE, así que
-- aplica solo al rol que lo ejecutó (hoy pgadmin). En cuanto las tablas las
-- cree siscom_migrator, siscom se queda sin permisos sobre las nuevas. Este
-- FOR ROLE es la corrección, y hay que llevarla a database-siscom junto con
-- la credencial.
ALTER DEFAULT PRIVILEGES FOR ROLE siscom_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO siscom;
ALTER DEFAULT PRIVILEGES FOR ROLE siscom_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO siscom;
