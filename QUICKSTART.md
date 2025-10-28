# 🚀 Inicio Rápido - SISCOM Admin API

## Pasos para ejecutar el proyecto

### 1️⃣ Crear archivo .env

```bash
cat > .env << 'EOF'
PROJECT_NAME=SISCOM Admin API

DB_HOST=db
DB_PORT=5432
DB_USER=siscom
DB_PASSWORD=changeme123
DB_NAME=siscom_admin

AWS_REGION=us-east-1
COGNITO_USERPOOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
EOF
```

**⚠️ IMPORTANTE**: Reemplaza `COGNITO_USERPOOL_ID` y `COGNITO_CLIENT_ID` con valores reales de tu AWS Cognito User Pool.

### 2️⃣ Levantar servicios con Docker

```bash
docker-compose up -d
```

Esto levantará:
- ✅ PostgreSQL 16 en puerto 5432
- ✅ API en puerto 8000

### 3️⃣ Generar migración inicial de Alembic

```bash
# Generar migración
docker-compose exec api alembic revision --autogenerate -m "initial_schema"
```

**⚠️ MUY IMPORTANTE**: Editar el archivo generado en `app/db/migrations/versions/xxxx_initial_schema.py`

Agregar al final de la función `upgrade()`:

```python
def upgrade() -> None:
    # ... código autogenerado por Alembic ...
    
    # ⭐ AGREGAR MANUALMENTE - Índice único parcial (CRÍTICO):
    op.execute("""
        CREATE UNIQUE INDEX uq_device_services_active_one 
        ON device_services(device_id) 
        WHERE status = 'ACTIVE'
    """)
    
    # ⭐ AGREGAR MANUALMENTE - Índice condicional (OPCIONAL pero recomendado):
    op.execute("""
        CREATE INDEX idx_invitations_expires_at 
        ON invitations (expires_at)
        WHERE accepted = FALSE
    """)
```

Y en la función `downgrade()`:

```python
def downgrade() -> None:
    # ⭐ AGREGAR PRIMERO (antes del código autogenerado):
    op.execute("DROP INDEX IF EXISTS uq_device_services_active_one")
    op.execute("DROP INDEX IF EXISTS idx_invitations_expires_at")
    
    # ... código autogenerado por Alembic ...
```

**Consulta MIGRATION_NOTES.md para más detalles sobre estos cambios.**

### 4️⃣ Aplicar migraciones

```bash
docker-compose exec api alembic upgrade head
```

### 5️⃣ (Opcional) Poblar datos de prueba

```bash
docker-compose exec api python scripts/seed_data.py
```

Esto creará:
- ✅ 3 planes de ejemplo (Básico, Profesional, Empresarial)
- ✅ 1 cliente de prueba: "Transportes Demo"
- ✅ 1 usuario de prueba: demo@transportes.com
- ✅ 3 dispositivos de prueba

### 6️⃣ Verificar que todo funciona

```bash
# Verificar API
curl http://localhost:8000/
# Respuesta esperada: {"status":"ok","message":"SISCOM Admin API running"}

# Verificar documentación
curl http://localhost:8000/docs
# Debería retornar HTML

# Ver logs
docker-compose logs -f api
```

### 7️⃣ Acceder a la documentación

Abre en tu navegador:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 8️⃣ Ejecutar tests

```bash
docker-compose exec api pytest -v
```

Deberías ver ~20 tests pasando correctamente.

## 📝 Endpoints Principales

### Sin autenticación:
- `GET /` - Health check
- `GET /api/v1/plans/` - Catálogo de planes

### Con autenticación (requiere token de Cognito):
- `GET /api/v1/clients/` - Info del cliente
- `GET /api/v1/users/me` - Info del usuario
- `GET /api/v1/devices/` - Listar dispositivos
- `POST /api/v1/devices/` - Registrar dispositivo
- **`POST /api/v1/services/activate` ⭐** - Activar servicio
- **`GET /api/v1/services/active` ⭐** - Servicios activos
- `POST /api/v1/orders/` - Crear orden
- `GET /api/v1/payments/` - Listar pagos

## 🧪 Testing sin Cognito

Para probar los endpoints sin configurar Cognito, usa los tests:

```bash
# Ejecutar test específico
docker-compose exec api pytest tests/test_services.py::test_activate_device_service_monthly -v

# Ver cobertura
docker-compose exec api pytest --cov=app --cov-report=html
```

## 🛠️ Comandos Útiles

```bash
# Ver logs en tiempo real
docker-compose logs -f api

# Reiniciar servicios
docker-compose restart

# Detener servicios
docker-compose down

# Detener y eliminar volúmenes (⚠️ borra la BD)
docker-compose down -v

# Entrar al contenedor de la API
docker-compose exec api bash

# Entrar a PostgreSQL
docker-compose exec db psql -U siscom -d siscom_admin

# Ver estado de migraciones
docker-compose exec api alembic current

# Crear nueva migración
docker-compose exec api alembic revision -m "descripcion"

# Revertir última migración
docker-compose exec api alembic downgrade -1
```

## 🔧 Desarrollo Local (sin Docker)

Si prefieres trabajar sin Docker:

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar .env apuntando a localhost
# DB_HOST=localhost

# Levantar PostgreSQL (necesitas tenerlo instalado)
# O usar Docker solo para la BD:
docker run -d -p 5432:5432 -e POSTGRES_USER=siscom -e POSTGRES_PASSWORD=changeme123 -e POSTGRES_DB=siscom_admin postgres:16

# Ejecutar migraciones
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload

# Ejecutar tests
pytest -v
```

## 📚 Documentación Adicional

- **README.md**: Documentación completa del proyecto
- **IMPLEMENTATION_SUMMARY.md**: Resumen detallado de toda la implementación
- **app/api/v1/endpoints/**: Código fuente de los endpoints con docstrings

## ⚠️ Notas Importantes

1. **Índice Único**: No olvides agregar manualmente el índice único en la migración inicial (paso 3️⃣)
2. **Cognito**: Para producción, necesitas configurar AWS Cognito real
3. **Multi-tenant**: Todos los datos están aislados por `client_id` automáticamente
4. **Device Services**: Solo puede haber 1 servicio ACTIVE por dispositivo (garantizado por índice único)

## 🆘 Solución de Problemas

**Error: "relation does not exist"**
→ Ejecutar `alembic upgrade head`

**Error: "could not connect to server"**
→ Verificar que PostgreSQL está corriendo: `docker-compose ps`

**Tests fallan con errores de imports**
→ Asegurarse de estar en el directorio raíz del proyecto

**Error 401 en endpoints**
→ Los endpoints requieren token de Cognito o usar los tests con auth mockeado

## ✅ Checklist de Verificación

- [ ] Archivo `.env` creado con variables correctas
- [ ] Docker Compose levantado (`docker-compose ps` muestra servicios corriendo)
- [ ] Migración generada y editada con índice único
- [ ] Migraciones aplicadas (`alembic current` muestra versión)
- [ ] Datos de prueba poblados (opcional)
- [ ] API responde en http://localhost:8000
- [ ] Documentación visible en http://localhost:8000/docs
- [ ] Tests pasan correctamente

## 🎉 ¡Listo!

Si todos los pasos anteriores funcionaron, tu API está corriendo correctamente. Puedes empezar a desarrollar o integrar con tu aplicación frontend.

Para más detalles, consulta el **README.md** completo.

