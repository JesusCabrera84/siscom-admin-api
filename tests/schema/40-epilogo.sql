-- ============================================================================
-- `unified_sim_profiles` — existe en producción y no la crea ningún artefacto.
--
-- Comprobado por consulta directa el 6/09/2026: `to_regclass` la encuentra. No
-- venía en el export, que es como se descubrió que ese export no era
-- exhaustivo.
--
-- ADVERTENCIA sobre esta definición: sale del MODELO
-- (`app/models/unified_sim_profile.py`), no de producción. Eso significa que el
-- comparador NO puede detectar deriva sobre esta tabla — la estaría comparando
-- consigo misma. Es un hueco conocido y acotado a una tabla.
--
-- Se cierra el día que haya un `pg_dump --schema-only` de verdad. Ver la
-- cabecera de README.md en este directorio.
-- ============================================================================
CREATE TABLE unified_sim_profiles (
	sim_id UUID NOT NULL, 
	device_id TEXT NOT NULL, 
	carrier TEXT NOT NULL, 
	iccid TEXT NOT NULL, 
	msisdn TEXT, 
	imsi TEXT, 
	status TEXT NOT NULL, 
	kore_sim_id TEXT, 
	metadata JSONB, 
	PRIMARY KEY (sim_id)
);
