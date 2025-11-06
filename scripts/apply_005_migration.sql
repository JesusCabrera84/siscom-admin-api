-- Migración 005: Renombrar imei a device_id
-- Este archivo contiene el SQL directo para aplicar la migración manualmente

-- 1. Eliminar el índice antiguo
DROP INDEX IF EXISTS idx_devices_imei;

-- 2. Renombrar la columna
ALTER TABLE devices RENAME COLUMN imei TO device_id;

-- 3. Crear el nuevo índice
CREATE INDEX idx_devices_device_id ON devices(device_id);

-- Verificar el cambio
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'devices' 
  AND column_name = 'device_id';

