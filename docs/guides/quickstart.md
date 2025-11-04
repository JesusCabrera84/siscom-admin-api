# Guía Rápida - SISCOM Admin API

## Introducción

Esta guía te ayudará a empezar a usar la API de SISCOM en minutos.

---

## 1. Requisitos Previos

- Docker & Docker Compose instalados
- Cuenta de AWS con Cognito configurado
- Editor de código (VS Code recomendado)

---

## 2. Instalación

### Clonar el Repositorio

```bash
git clone <repository-url>
cd siscom-admin-api
```

### Configurar Variables de Entorno

Crea un archivo `.env`:

```bash
# Base de datos
DB_HOST=localhost
DB_PORT=5432
DB_USER=siscom
DB_PASSWORD=tu_password_seguro
DB_NAME=siscom_admin

# AWS Cognito
AWS_REGION=us-east-1
COGNITO_USERPOOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
COGNITO_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
COGNITO_REGION=us-east-1

# API
PROJECT_NAME=SISCOM Admin API
```

### Levantar Servicios

```bash
docker-compose up -d
```

### Ejecutar Migraciones

```bash
docker-compose exec api alembic upgrade head
```

---

## 3. Verificar Instalación

```bash
curl http://localhost:8000/
```

**Respuesta esperada:**
```json
{
  "status": "ok",
  "message": "SISCOM Admin API running"
}
```

---

## 4. Documentación Interactiva

Abre en tu navegador:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 5. Primer Cliente (Registro)

### Crear Cliente

```bash
curl -X POST http://localhost:8000/api/v1/clients/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mi Empresa",
    "email": "admin@miempresa.com",
    "password": "MiPassword123!"
  }'
```

**Respuesta:**
```json
{
  "id": "...",
  "name": "Mi Empresa",
  "status": "PENDING"
}
```

### Verificar Email

1. Revisa tu email para el código de verificación
2. Confirma el email:

```bash
curl -X POST http://localhost:8000/api/v1/clients/confirm-email \
  -H "Content-Type: application/json" \
  -d '{
    "token": "token_recibido_por_email"
  }'
```

---

## 6. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@miempresa.com",
    "password": "MiPassword123!"
  }'
```

**Respuesta:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "id_token": "...",
  "refresh_token": "...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

**Guarda el `access_token`** para usarlo en siguientes requests.

---

## 7. Primer Dispositivo

### Crear Dispositivo

```bash
curl -X POST http://localhost:8000/api/v1/devices/ \
  -H "Authorization: Bearer <tu_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "serial_number": "GPS-2024-001",
    "model": "TK103",
    "imei": "353451234567890"
  }'
```

---

## 8. Ver Planes Disponibles

```bash
curl http://localhost:8000/api/v1/plans/
```

**Nota**: Este endpoint es público, no requiere autenticación.

---

## 9. Activar Servicio

```bash
curl -X POST http://localhost:8000/api/v1/services/activate \
  -H "Authorization: Bearer <tu_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "id_del_dispositivo",
    "plan_id": "id_del_plan",
    "subscription_type": "MONTHLY"
  }'
```

---

## 10. Ver Servicios Activos

```bash
curl http://localhost:8000/api/v1/services/active \
  -H "Authorization: Bearer <tu_access_token>"
```

---

## Próximos Pasos

### Invitar Usuarios

Ver [Documentación de Usuarios](../api/users.md)

### Crear Órdenes

Ver [Documentación de Órdenes](../api/orders.md)

### Gestionar Pagos

Ver [Documentación de Pagos](../api/payments.md)

---

## Documentación Completa por Endpoint

- [Autenticación](../api/auth.md)
- [Clientes](../api/clients.md)
- [Usuarios](../api/users.md)
- [Dispositivos](../api/devices.md)
- [Servicios](../api/services.md)
- [Planes](../api/plans.md)
- [Órdenes](../api/orders.md)
- [Pagos](../api/payments.md)

---

## Soporte

Para soporte técnico o preguntas:
- Email: soporte@siscom.com
- Documentación: http://localhost:8000/docs

