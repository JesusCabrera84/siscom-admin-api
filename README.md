# SISCOM Admin API

API administrativa para sistema de rastreo GPS/IoT con arquitectura multi-tenant.

## Descripción

Esta API proporciona funcionalidad completa para gestionar un sistema de rastreo GPS/IoT con las siguientes características:

- **Multi-tenant**: Cada cliente tiene sus propios datos aislados
- **Autenticación AWS Cognito**: Validación de tokens JWT
- **Gestión de Dispositivos**: Registro y seguimiento de dispositivos GPS
- **Servicios por Dispositivo**: Activación y gestión de servicios mensuales/anuales
- **Planes Flexibles**: Catálogo de planes con diferentes características
- **Órdenes y Pagos**: Gestión completa de compras y facturación

## Tecnologías

- **FastAPI**: Framework web de alto rendimiento
- **SQLAlchemy 2.x / SQLModel**: ORM para PostgreSQL
- **PostgreSQL 16**: Base de datos relacional
- **AWS Cognito**: Autenticación y autorización
- **Alembic**: Migraciones de base de datos
- **Docker & Docker Compose**: Contenedorización

## Flujo de Negocio

1. **Compra de Hardware**: El cliente realiza pedidos de dispositivos físicos (`orders`, `payments`)
2. **Instalación**: Los dispositivos se instalan en unidades/vehículos (`device_installations`, `units`)
3. **Activación de Servicio**: Se activa el servicio mensual/anual por dispositivo (`device_services`)
4. **Rastreo Activo**: El dispositivo comienza a enviar datos de ubicación

## Requisitos

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+ (para desarrollo local)

## Instalación

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd siscom-admin-api
```

### 2. Configurar variables de entorno

Crea un archivo `.env` basado en `.env.example`:

```bash
# .env
PROJECT_NAME=SISCOM Admin API

DB_HOST=localhost
DB_PORT=5432
DB_USER=siscom
DB_PASSWORD=tu_password_seguro
DB_NAME=siscom_admin

AWS_REGION=us-east-1
COGNITO_USERPOOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Importante**: Reemplaza los valores de `COGNITO_USERPOOL_ID` y `COGNITO_CLIENT_ID` con los valores reales de tu User Pool de AWS Cognito.

### 3. Levantar los servicios con Docker

```bash
docker-compose up -d
```

Esto levantará:
- PostgreSQL en el puerto 5432
- API en el puerto 8000

### 4. Ejecutar migraciones

```bash
docker-compose exec api alembic upgrade head
```

### 5. Verificar que la API está corriendo

```bash
curl http://localhost:8000/
# Respuesta: {"status":"ok","message":"SISCOM Admin API running"}
```

## Desarrollo Local (sin Docker)

### 1. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar base de datos PostgreSQL

Asegúrate de tener PostgreSQL corriendo y crea la base de datos:

```sql
CREATE DATABASE siscom_admin;
```

### 4. Ejecutar migraciones

```bash
alembic upgrade head
```

### 5. Iniciar el servidor de desarrollo

```bash
uvicorn app.main:app --reload
```

La API estará disponible en http://localhost:8000

## Documentación de la API

Una vez que la API esté corriendo, puedes acceder a:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **📚 Documentación Completa**: [docs/README.md](docs/README.md)

## Guías Rápidas

- **[Inicio Rápido](docs/guides/quickstart.md)** - Configuración y primeros pasos
- **[Configuración de Cognito](docs/guides/cognito-setup.md)** - Setup de AWS Cognito

## Documentación por Endpoint

- **[Autenticación](docs/api/auth.md)** - Login, recuperación de contraseña
- **[Clientes](docs/api/clients.md)** - Registro de organizaciones
- **[Usuarios](docs/api/users.md)** - Invitaciones y gestión
- **[Dispositivos](docs/api/devices.md)** - Registro de GPS
- **[Servicios](docs/api/services.md)** - Activación de suscripciones
- **[Planes](docs/api/plans.md)** - Catálogo de planes
- **[Órdenes](docs/api/orders.md)** - Compra de dispositivos
- **[Pagos](docs/api/payments.md)** - Historial de pagos

## Ejemplo Rápido

```bash
# 1. Crear cliente
POST /api/v1/clients/

# 2. Login
POST /api/v1/auth/login

# 3. Crear dispositivo
POST /api/v1/devices/

# 4. Activar servicio
POST /api/v1/services/activate
```

Ver [documentación completa](docs/README.md) para más detalles.

## Estructura del Proyecto

```
siscom-admin-api/
├── app/
│   ├── api/
│   │   ├── deps.py              # Dependencies de autenticación
│   │   └── v1/
│   │       ├── endpoints/       # Endpoints de la API
│   │       └── router.py        # Router principal v1
│   ├── core/
│   │   ├── config.py            # Configuración (Settings)
│   │   ├── security.py          # Validación de tokens Cognito
│   │   └── logging_config.py    # Configuración de logs
│   ├── db/
│   │   ├── base.py              # Importa todos los modelos
│   │   ├── session.py           # Engine y SessionLocal
│   │   └── migrations/          # Migraciones de Alembic
│   ├── models/                  # Modelos SQLModel
│   ├── schemas/                 # Schemas Pydantic
│   ├── services/                # Lógica de negocio
│   ├── utils/                   # Utilidades
│   └── main.py                  # Aplicación FastAPI
├── docs/                        # 📚 Documentación
│   ├── README.md               # Índice de documentación
│   ├── api/                    # Docs de endpoints
│   │   ├── auth.md
│   │   ├── clients.md
│   │   ├── users.md
│   │   ├── devices.md
│   │   ├── services.md
│   │   ├── plans.md
│   │   ├── orders.md
│   │   └── payments.md
│   └── guides/                 # Guías
│       ├── quickstart.md
│       └── cognito-setup.md
├── scripts/
│   └── testing/                # Scripts de prueba
├── tests/                      # Tests con pytest
├── alembic.ini                 # Configuración de Alembic
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Pruebas

Ejecutar todos los tests:

```bash
pytest -v
```

Ejecutar tests específicos:

```bash
pytest tests/test_services.py -v
```

Con cobertura:

```bash
pytest --cov=app --cov-report=html
```

## Notas Importantes

### Índice Único en device_services

Existe un índice único parcial que garantiza que **solo puede haber UN servicio ACTIVE por dispositivo**:

```sql
CREATE UNIQUE INDEX uq_device_services_active_one 
ON device_services(device_id) 
WHERE status = 'ACTIVE';
```

### Multi-tenancy

- Todos los datos están aislados por `client_id`
- El `client_id` se extrae del token de Cognito mediante `cognito_sub`
- Todos los endpoints validan automáticamente el ownership

### Expiración de Servicios

- **MONTHLY**: 30 días de duración
- **YEARLY**: 365 días de duración
- El campo `expires_at` se calcula automáticamente al activar
- El campo `auto_renew` indica si se renovará automáticamente

### Device Active Status

- `device.active` se actualiza automáticamente:
  - `True` cuando se activa un servicio
  - `False` cuando se cancela el último servicio activo

## Migraciones de Base de Datos

### Crear una nueva migración

```bash
alembic revision --autogenerate -m "descripcion_del_cambio"
```

### Aplicar migraciones

```bash
alembic upgrade head
```

### Revertir última migración

```bash
alembic downgrade -1
```

### Ver historial

```bash
alembic history
```

## Linting y Formateo

```bash
# Formatear con black
black app/

# Lint con ruff
ruff check app/
```

## Contribución

1. Crear una rama para tu feature: `git checkout -b feature/nueva-funcionalidad`
2. Hacer commit de cambios: `git commit -am 'Agregar nueva funcionalidad'`
3. Push a la rama: `git push origin feature/nueva-funcionalidad`
4. Crear Pull Request

## Licencia

[Especificar licencia]

## Soporte

Para soporte técnico, contactar a [email de soporte]

