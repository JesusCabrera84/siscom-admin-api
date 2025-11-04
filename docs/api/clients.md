# API de Clientes

## Descripción

Endpoints para gestionar clientes (organizaciones) en el sistema. Un cliente representa una empresa u organización que utiliza el sistema de rastreo GPS.

---

## Endpoints

### 1. Crear Cliente

**POST** `/api/v1/clients/`

Crea un nuevo cliente con un usuario maestro asociado. Este es el endpoint de registro público.

#### Request Body

```json
{
  "name": "Transportes XYZ",
  "email": "admin@transportesxyz.com",
  "password": "Password123!"
}
```

#### Validaciones

- El email no debe estar registrado
- El nombre del cliente debe ser único
- La contraseña debe cumplir requisitos de seguridad

#### Response 201 Created

```json
{
  "id": "456e4567-e89b-12d3-a456-426614174000",
  "name": "Transportes XYZ",
  "status": "PENDING",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### Proceso Interno

1. Crea el cliente con estado `PENDING`
2. Crea el usuario maestro asociado (sin `cognito_sub` aún)
3. Genera token de verificación de email
4. Envía email de verificación
5. El usuario debe confirmar su email antes de poder iniciar sesión

---

### 2. Obtener Cliente Actual

**GET** `/api/v1/clients/`

Obtiene la información del cliente autenticado.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response 200 OK

```json
{
  "id": "456e4567-e89b-12d3-a456-426614174000",
  "name": "Transportes XYZ",
  "status": "ACTIVE",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### 3. Confirmar Email del Cliente

**POST** `/api/v1/clients/confirm-email`

Confirma el email del usuario maestro y activa el cliente en Cognito.

#### Request Body

```json
{
  "token": "abc123def456..."
}
```

#### Validaciones

- El token debe ser válido y no estar expirado
- El token no debe haber sido usado
- Debe ser un token de tipo `EMAIL_VERIFICATION`

#### Response 200 OK

```json
{
  "message": "Email verificado exitosamente. Cliente activado.",
  "client_id": "456e4567-e89b-12d3-a456-426614174000",
  "email": "admin@transportesxyz.com"
}
```

#### Proceso Interno

1. Valida el token de verificación
2. Crea el usuario en AWS Cognito
3. Actualiza el usuario con `cognito_sub`
4. Actualiza el cliente a estado `ACTIVE`
5. Marca el token como usado

---

### 4. Reenviar Email de Verificación

**POST** `/api/v1/clients/resend-verification`

Reenvía el email de verificación a un cliente pendiente.

#### Request Body

```json
{
  "email": "admin@transportesxyz.com"
}
```

#### Response 200 OK

```json
{
  "message": "Si el email existe y no está verificado, recibirás un nuevo código.",
  "email": "admin@transportesxyz.com"
}
```

---

## Estados del Cliente

### PENDING

- Cliente recién creado
- Email no verificado
- No puede iniciar sesión
- Esperando confirmación de email

### ACTIVE

- Email verificado
- Usuario maestro creado en Cognito
- Puede iniciar sesión y usar el sistema

### SUSPENDED

- Cliente suspendido (no usado actualmente)
- No puede acceder al sistema
- Datos preservados

---

## Flujo de Registro Completo

### 1. Registro Inicial

```
Usuario → POST /api/v1/clients/
        ↓
  Cliente creado (PENDING)
        ↓
  Usuario master creado (sin cognito_sub)
        ↓
  Token de verificación generado
        ↓
  Email enviado con link de verificación
```

### 2. Verificación de Email

```
Usuario → Clic en link del email
        ↓
  POST /api/v1/clients/confirm-email
        ↓
  Usuario creado en AWS Cognito
        ↓
  Cliente actualizado a ACTIVE
        ↓
  Usuario puede hacer login
```

### 3. Email No Recibido

```
Usuario → POST /api/v1/clients/resend-verification
        ↓
  Token renovado
        ↓
  Nuevo email enviado
```

---

## Arquitectura Multi-tenant

### Aislamiento de Datos

- Cada cliente tiene acceso solo a sus propios datos
- Todos los modelos tienen `client_id` como foreign key
- Las consultas automáticamente filtran por `client_id`

### Identificación del Cliente

```
Token JWT → cognito_sub extraído
          ↓
  Usuario buscado por cognito_sub
          ↓
  client_id extraído del usuario
          ↓
  Todas las consultas filtradas por client_id
```

### Ventajas

- **Aislamiento**: Los datos están completamente separados
- **Seguridad**: Imposible acceder a datos de otros clientes
- **Escalabilidad**: Fácil agregar nuevos clientes
- **Simplicidad**: Una sola base de datos para todos

---

## Relaciones del Cliente

Un cliente tiene:

- **Usuarios** (`users`): Uno o más usuarios, al menos uno maestro
- **Dispositivos** (`devices`): Dispositivos GPS del cliente
- **Órdenes** (`orders`): Historial de compras
- **Pagos** (`payments`): Historial de pagos
- **Servicios** (`device_services`): Servicios activos/históricos

---

## Notas de Seguridad

### Creación de Cliente

- Endpoint público (no requiere autenticación)
- Rate limiting recomendado
- Validación de email para evitar spam

### Acceso a Datos

- Siempre se valida el `client_id` del token
- No es posible cambiar el `client_id` de un usuario
- Los endpoints automáticamente filtran por cliente

### Usuario Maestro

- Se crea automáticamente con el cliente
- `is_master=True` por defecto
- Tiene permisos para invitar usuarios
- No puede eliminarse sin eliminar el cliente

