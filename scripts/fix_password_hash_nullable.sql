-- Hacer password_hash nullable en la tabla users
-- Esto es necesario porque usamos AWS Cognito para autenticación
-- y no almacenamos contraseñas en nuestra base de datos

ALTER TABLE users 
ALTER COLUMN password_hash DROP NOT NULL;

-- Verificar el cambio
SELECT 
    column_name, 
    data_type, 
    is_nullable 
FROM 
    information_schema.columns 
WHERE 
    table_name = 'users' 
    AND column_name = 'password_hash';

