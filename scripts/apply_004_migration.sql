-- Migración 004: Add password_temp to tokens_confirmacion and make password_hash nullable
-- Ejecutar con: psql -d siscom_admin -f scripts/apply_004_migration.sql

BEGIN;

-- 1. Hacer password_hash nullable en users
ALTER TABLE users 
ALTER COLUMN password_hash DROP NOT NULL;

-- 2. Agregar password_temp a tokens_confirmacion
ALTER TABLE tokens_confirmacion 
ADD COLUMN IF NOT EXISTS password_temp VARCHAR(255) NULL;

-- Verificar los cambios
SELECT 
    'users.password_hash' as campo,
    is_nullable 
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'password_hash'

UNION ALL

SELECT 
    'tokens_confirmacion.password_temp' as campo,
    is_nullable 
FROM information_schema.columns 
WHERE table_name = 'tokens_confirmacion' AND column_name = 'password_temp';

COMMIT;

-- Mostrar mensaje de éxito
SELECT '✅ Migración 004 aplicada exitosamente' as resultado;

