# Arquitectura del Sistema

## Descripción General

SISCOM Admin API es una aplicación FastAPI que implementa un sistema multi-tenant para gestión de dispositivos GPS/IoT.

---

## Stack Tecnológico

### Backend

- **FastAPI**: Framework web de alto rendimiento
- **Python 3.11+**: Lenguaje de programación
- **SQLAlchemy 2.x**: ORM para base de datos
- **Pydantic**: Validación de datos

### Base de Datos

- **PostgreSQL 16**: Base de datos relacional
- **Alembic**: Migraciones de esquema

### Autenticación

- **AWS Cognito**: Gestión de identidad y acceso
- **JWT**: Tokens de autenticación
- **Boto3**: SDK de AWS para Python

### DevOps

- **Docker**: Contenedorización
- **Docker Compose**: Orquestación local

---

## Arquitectura Multi-tenant

### Aislamiento de Datos

Cada cliente (organización) tiene sus datos completamente aislados:

```
Token JWT → cognito_sub
          ↓
  Búsqueda de Usuario por cognito_sub
          ↓
  Extracción de client_id
          ↓
  Filtrado automático de todas las consultas
```

### Ventajas

- **Seguridad**: Imposible acceder a datos de otros clientes
- **Simplicidad**: Una sola base de datos
- **Escalabilidad**: Fácil agregar nuevos clientes
- **Mantenimiento**: Un solo código base

---

## Modelo de Datos

### Entidades Principales

```
Client (Organización)
  ├── Users (Usuarios)
  ├── Devices (Dispositivos)
  │   └── DeviceServices (Servicios activos)
  ├── Orders (Órdenes de compra)
  └── Payments (Pagos)
```

### Relaciones Clave

```
Client 1:N Users
User N:1 Client

Client 1:N Devices
Device N:1 Client
Device 1:N DeviceServices

DeviceService N:1 Device
DeviceService N:1 Plan
DeviceService 1:1 Payment

Order N:1 Client
Order 1:N OrderItems
Order 1:1 Payment
```

---

## Flujo de Autenticación

### 1. Registro

```
POST /api/v1/clients/
  ↓
Crear Client (status=PENDING)
  ↓
Crear User master (sin cognito_sub)
  ↓
Generar token de verificación
  ↓
Enviar email de verificación
```

### 2. Verificación

```
Usuario hace clic en link del email
  ↓
POST /api/v1/auth/verify-email?token=...
  ↓
Validar token (no expirado, no usado)
  ↓
Crear usuario en AWS Cognito
  ↓
Establecer contraseña usando password_temp
  ↓
Actualizar User.cognito_sub
  ↓
Actualizar Client.status = ACTIVE
  ↓
Eliminar password_temp permanentemente
```

**Reenvío de Verificación:**

```
Usuario solicita reenvío
  ↓
POST /api/v1/auth/resend-verification
  ↓
Buscar password_temp del token previo
  ↓
Crear nuevo token con MISMO password_temp
  ↓
Invalidar tokens anteriores
  ↓
Enviar nuevo email
```

### 3. Login

```
POST /api/v1/auth/login
  ↓
Validar credenciales en Cognito
  ↓
Obtener tokens (access, id, refresh)
  ↓
Retornar tokens al cliente
```

### 4. Request Autenticado

```
Request con Authorization: Bearer <token>
  ↓
Validar token con Cognito
  ↓
Extraer cognito_sub del token
  ↓
Buscar usuario por cognito_sub
  ↓
Extraer client_id del usuario
  ↓
Ejecutar query con filtro por client_id
```

---

## Flujo de Negocio

### Compra de Hardware

```
1. Cliente crea orden
   POST /api/v1/orders/
   ↓
2. Sistema crea Payment (PENDING)
   ↓
3. Cliente realiza pago externo
   ↓
4. Admin confirma pago
   UPDATE payment.status = SUCCESS
   ↓
5. Admin envía dispositivos
   ↓
6. Admin marca orden como completada
   UPDATE order.status = COMPLETED
   ↓
7. Sistema crea dispositivos en BD
   INSERT INTO devices
```

### Activación de Servicio

```
1. Cliente registra dispositivo
   POST /api/v1/devices/
   ↓
2. Cliente instala físicamente el dispositivo
   ↓
3. Cliente selecciona plan
   GET /api/v1/plans/
   ↓
4. Cliente activa servicio
   POST /api/v1/services/activate
   ↓
5. Sistema crea Payment (SUCCESS)
   ↓
6. Sistema crea DeviceService (ACTIVE)
   ↓
7. Sistema actualiza Device.active = true
   ↓
8. Dispositivo comienza a rastrear
```

---

## Capas de la Aplicación

### 1. API Layer (app/api/)

Responsabilidades:

- Definir endpoints HTTP
- Validar request/response
- Manejar autenticación/autorización
- Retornar respuestas HTTP

```python
@router.post("/activate")
def activate_service(
    service_in: DeviceServiceCreate,
    client_id: UUID = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    return activate_device_service(db, client_id, ...)
```

### 2. Service Layer (app/services/)

Responsabilidades:

- Implementar lógica de negocio
- Coordinar múltiples operaciones
- Manejar transacciones
- Validar reglas de negocio

```python
def activate_device_service(
    db: Session,
    client_id: UUID,
    device_id: UUID,
    ...
):
    # Validar device ownership
    # Verificar no hay servicio activo
    # Crear payment
    # Crear device_service
    # Actualizar device.active
    return device_service
```

### 3. Model Layer (app/models/)

Responsabilidades:

- Definir estructura de datos
- Relaciones entre tablas
- Validaciones de DB

```python
class DeviceService(SQLModel, table=True):
    __tablename__ = "device_services"

    id: UUID
    client_id: UUID
    device_id: UUID
    status: str
    ...
```

### 4. Schema Layer (app/schemas/)

Responsabilidades:

- Definir contratos de API
- Validar entrada/salida
- Transformar datos

```python
class DeviceServiceCreate(BaseModel):
    device_id: UUID
    plan_id: UUID
    subscription_type: SubscriptionType
```

---

## Seguridad

### Autenticación

- **AWS Cognito**: Single source of truth para identidades
- **JWT**: Tokens firmados y verificables
- **Tokens expirados**: Access token 1 hora, refresh indefinido

### Autorización

- **Multi-tenant**: Automático por client_id
- **Role-based**: is_master flag para permisos especiales
- **Ownership validation**: Siempre verificar client_id

### Mejores Prácticas

```python
# ✅ CORRECTO: Filtrar por client_id
devices = db.query(Device).filter(
    Device.client_id == client_id
).all()

# ❌ INCORRECTO: No filtrar por client_id
devices = db.query(Device).all()
```

---

## Escalabilidad

### Horizontal

- **Stateless**: No estado en servidor
- **Load Balancer**: Múltiples instancias de API
- **Session en JWT**: No requiere sesiones en servidor

### Vertical

- **Connection Pooling**: SQLAlchemy pool
- **Async where needed**: FastAPI async endpoints
- **Índices DB**: Optimizar queries frecuentes

### Caching

```python
# Planes (cambian raramente)
@lru_cache(maxsize=100)
def get_active_plans(db: Session):
    return db.query(Plan).filter(Plan.active == True).all()
```

---

## Monitoreo

### Logs

- **FastAPI logging**: Requests/responses
- **Application logs**: Errores de negocio
- **Database logs**: Queries lentas

### Métricas

- **Requests por segundo**
- **Latencia promedio**
- **Error rate**
- **Active users**
- **Active devices**

### Alertas

- **Error rate > 5%**
- **Latency > 1s**
- **DB connections > 80%**
- **Cognito rate limits**

---

## Testing

### Unit Tests

```python
def test_activate_service():
    # Given
    device = create_test_device()
    plan = create_test_plan()

    # When
    service = activate_device_service(...)

    # Then
    assert service.status == "ACTIVE"
    assert device.active == True
```

### Integration Tests

```python
def test_activate_service_endpoint(client, auth_token):
    response = client.post(
        "/api/v1/services/activate",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={...}
    )
    assert response.status_code == 201
```

---

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

### Docker Compose

```yaml
services:
  db:
    image: postgres:16

  api:
    build: .
    depends_on:
      - db
    environment:
      - DATABASE_URL=postgresql://...
```

### Producción

- **Nginx**: Reverse proxy
- **Gunicorn**: WSGI server con workers
- **PostgreSQL**: Instancia dedicada
- **SSL/TLS**: Certificados válidos
- **Backups**: Diarios automáticos

---

## Mejores Prácticas

### Código

- **Type hints**: Siempre usar tipado
- **Docstrings**: Documentar funciones complejas
- **Error handling**: Usar HTTPException apropiadas
- **Validation**: Pydantic para todo input

### Base de Datos

- **Migrations**: Siempre usar Alembic
- **Transactions**: Usar db.commit() explícitamente
- **Indexes**: En foreign keys y campos frecuentes
- **Constraints**: Unique, not null, foreign keys

### API

- **Versioning**: /api/v1/, /api/v2/
- **Status codes**: Usar códigos HTTP correctos
- **Error messages**: Mensajes claros y útiles
- **Documentation**: Swagger UI actualizado

---

## Roadmap

### Corto Plazo

- [ ] Webhooks de gateways de pago
- [ ] Renovación automática de servicios
- [ ] Notificaciones por email
- [ ] API de reportes

### Mediano Plazo

- [ ] Dashboard de métricas
- [ ] Integración con hardware GPS
- [ ] App móvil
- [ ] Exportación de datos

### Largo Plazo

- [ ] Machine Learning para predicciones
- [ ] Alertas inteligentes
- [ ] Integración con terceros
- [ ] API pública para partners
