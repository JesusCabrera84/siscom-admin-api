# SISCOM Admin API

Plataforma **SaaS B2B multi-tenant** para gestión de flotas GPS/IoT.

## Descripción

SISCOM Admin API es una API REST que implementa un sistema completo de gestión de flotas con las siguientes características:

- **Multi-tenant**: Cada organización tiene sus datos completamente aislados
- **Autenticación Dual**: AWS Cognito (usuarios) + PASETO (servicios internos)
- **Roles Organizacionales**: owner, admin, billing, member
- **Suscripciones Múltiples**: Una organización puede tener varias suscripciones
- **Sistema de Capabilities**: Límites y features configurables por plan y organización
- **Gestión de Dispositivos**: Registro y seguimiento de dispositivos GPS
- **Planes Flexibles**: Catálogo de planes con capabilities específicas
- **Órdenes y Pagos**: Gestión completa de compras y facturación

> **Documentación de Arquitectura**: Ver [docs/guides/organizational-model.md](docs/guides/organizational-model.md) para entender el modelo de negocio completo.

## Tecnologías

- **FastAPI**: Framework web de alto rendimiento
- **SQLAlchemy 2.x / SQLModel**: ORM para PostgreSQL
- **PostgreSQL 16**: Base de datos relacional
- **AWS Cognito**: Autenticación y autorización
- **Alembic**: Migraciones de base de datos
- **Docker & Docker Compose**: Contenedorización

## Modelo de Negocio

### Conceptos Clave

| Concepto | Descripción |
|----------|-------------|
| **Account** | Raíz comercial (billing, facturación) |
| **Organización** | Raíz operativa (permisos, uso diario) |
| **Suscripciones** | Una organización puede tener **múltiples** suscripciones |
| **Capabilities** | Límites y features que gobiernan el acceso |
| **Roles** | owner, admin, billing, member |

### Flujo de Negocio

1. **Registro**: La organización se registra y verifica su email
2. **Compra de Hardware**: Realiza pedidos de dispositivos físicos (`orders`, `payments`)
3. **Instalación**: Los dispositivos se instalan en unidades/vehículos (`units`)
4. **Activación de Servicio**: Se activa el servicio según plan seleccionado (`device_services`)
5. **Capabilities**: Los límites se validan según el plan y overrides de la organización
6. **Rastreo Activo**: El dispositivo comienza a enviar datos de ubicación

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
COGNITO_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxx

# AWS SES - Configuración de emails
SES_FROM_EMAIL=noreply@tudominio.com
SES_REGION=us-east-1

# Frontend URL - Para links en emails
FRONTEND_URL=https://app.tudominio.com
```

**Importante**:

- Reemplaza los valores de `COGNITO_*` con los valores reales de tu User Pool de AWS Cognito
- `SES_FROM_EMAIL` debe estar verificado en AWS SES
- Ver [Guía de configuración de emails](docs/guides/email-configuration.md) para más detalles

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

### 📘 Documentación Principal

| Documento | Descripción |
|-----------|-------------|
| **[Modelo Organizacional](docs/guides/organizational-model.md)** | 📌 **LECTURA OBLIGATORIA** - Modelo conceptual de negocio |
| **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** | Guía exhaustiva de endpoints |
| **[docs/README.md](docs/README.md)** | Índice completo de documentación |

### Documentación Interactiva

Una vez que la API esté corriendo:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Guías de Arquitectura

- **[Modelo Organizacional](docs/guides/organizational-model.md)** - Conceptos de negocio
- **[Arquitectura del Sistema](docs/guides/architecture.md)** - Diseño técnico
- **[Inicio Rápido](docs/guides/quickstart.md)** - Configuración inicial
- **[Configuración de Cognito](docs/guides/cognito-setup.md)** - Setup de AWS Cognito

### Documentación por Endpoint

| Endpoint | Descripción |
|----------|-------------|
| **[Autenticación](docs/api/auth.md)** | Login, tokens (Cognito + PASETO) |
| **[Cuentas (Accounts)](docs/api/accounts.md)** | Onboarding y gestión de cuentas |
| **[API Interna](docs/api/internal-organizations.md)** | Endpoints administrativos (PASETO) |
| **[Usuarios](docs/api/users.md)** | Invitaciones y roles organizacionales |
| **[Planes](docs/api/plans.md)** | Catálogo de planes y capabilities |
| **[Dispositivos](docs/api/devices.md)** | Registro de GPS |
| **[Servicios](docs/api/services.md)** | Activación de suscripciones |
| **[Órdenes](docs/api/orders.md)** | Compra de dispositivos |
| **[Pagos](docs/api/payments.md)** | Historial de pagos |

## Ejemplo Rápido

```bash
# 1. Crear cuenta (onboarding)
POST /api/v1/auth/register

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
│   │   ├── accounts.md
│   │   ├── users.md
│   │   ├── devices.md
│   │   ├── services.md
│   │   ├── plans.md
│   │   ├── orders.md
│   │   └── payments.md
│   └── guides/                 # Guías
│       ├── quickstart.md
│       ├── cognito-setup.md
│       └── email-configuration.md
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

### Modelo Organizacional

- **Account = Raíz comercial, Organization = Raíz operativa**: El modelo sigue esta jerarquía
- **Suscripciones Múltiples**: Una organización puede tener varias suscripciones simultáneamente
- **`active_subscription_id` es DEPRECADO**: Las suscripciones activas se calculan dinámicamente
- **Capabilities**: Los límites se resuelven: `org_override ?? plan_capability ?? default`

### Roles Organizacionales

| Rol | Descripción |
|-----|-------------|
| `owner` | Propietario con permisos totales |
| `admin` | Gestión de usuarios y configuración |
| `billing` | Gestión de pagos y facturación |
| `member` | Acceso operativo según asignaciones |

### Índice Único en device_services

Existe un índice único parcial que garantiza que **solo puede haber UN servicio ACTIVE por dispositivo**:

```sql
CREATE UNIQUE INDEX uq_device_services_active_one
ON device_services(device_id)
WHERE status = 'ACTIVE';
```

### Multi-tenancy

- Todos los datos están aislados por `organization_id` (`client_id`)
- El `organization_id` se extrae del token de Cognito mediante `cognito_sub`
- Todos los endpoints validan automáticamente el ownership

### Sistema de Capabilities

- Los límites se validan antes de operaciones de creación
- Si se excede un límite → HTTP 403 con detalle del límite
- Los overrides por organización tienen prioridad sobre el plan

### Expiración de Servicios

- **MONTHLY**: 30 días de duración
- **YEARLY**: 365 días de duración
- El campo `expires_at` se calcula automáticamente al activar
- El campo `auto_renew` indica si se renovará automáticamente

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
