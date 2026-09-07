-- ============================================================================
-- Objetos que el esquema de producción usa y los dumps NO traen.
--
-- El export de DDL del 5 de septiembre de 2026 salió de una herramienta gráfica
-- y resultó no ser exhaustivo: trae los CREATE TABLE pero no los tipos, ni los
-- esquemas, ni las funciones, ni la tabla `unified_sim_profiles` — que sí
-- existe en producción, comprobado por consulta directa.
--
-- Este preámbulo los repone para que el snapshot cargue completo.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS api_platform;
CREATE SCHEMA IF NOT EXISTS team;
CREATE SCHEMA IF NOT EXISTS mobility;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- El rol al que pertenecen las tablas en producción. En el snapshot solo hace
-- falta para que los GRANT del dump no fallen.
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'pgadmin') THEN
    CREATE ROLE pgadmin;
  END IF;
END $$;

-- Tipos ENUM. Los cinco primeros los declara `app/core/pg_enums.py` con
-- create_type=False; los crea el SQL crudo de la migración 023.
CREATE TYPE payment_gateway AS ENUM ('stripe','conekta','mercadopago','paypal','manual');
CREATE TYPE payment_method_type AS ENUM ('card','cash_voucher','bank_transfer','bank_redirect','wallet','installments','real_time','loyalty_points','gift_card','crypto','manual');
CREATE TYPE payment_status AS ENUM ('PENDING','REQUIRES_ACTION','PROCESSING','SUCCESS','FAILED','CANCELED','DISPUTED','REFUNDED','PARTIALLY_REFUNDED');
CREATE TYPE invoice_status AS ENUM ('DRAFT','OPEN','PAID','PAST_DUE','VOID','UNCOLLECTIBLE');
-- Sin 'processing': lo añade la migración 021, que en este punto del historial
-- todavía no se había aplicado. Es parte de lo que el snapshot debe reflejar.
CREATE TYPE gateway_event_status AS ENUM ('processed','failed','skipped');

CREATE TYPE public.event_type_enum AS ENUM ('HARSH_ACCEL','HARSH_BRKE','OVERSPEED_START','OVERSPEED_END','IDLE_START','IDLE_END','JAMMING','DISCONNECT','CUSTOM');
CREATE TYPE public.discount_type AS ENUM ('percentage','fixed_amount','volume','referral');
CREATE TYPE public.coupon_duration AS ENUM ('once','repeating','forever');

-- Estos dos NO aparecen en ningún repositorio: existen solo en producción.
-- Se conservan por decisión explícita (§22 del documento de arquitectura).
CREATE TYPE public.fuel_type_t AS ENUM ('UNKNOWN','GASOLINE','DIESEL','LPG','CNG','ELECTRIC','HYBRID');
CREATE TYPE public.ignition_source_t AS ENUM ('VIRTUAL','PHYSICAL','VOLTAGE','RPM');

-- Tampoco está en ningún repositorio. Igual que los tipos de arriba.
CREATE FUNCTION set_updated_at() RETURNS trigger AS $fn$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$fn$ LANGUAGE plpgsql;
