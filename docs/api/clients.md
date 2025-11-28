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
3. Genera token de verificación de email con `password_temp`
4. Guarda la contraseña temporalmente en el token (para usarla en Cognito después)
5. Envía email de verificación con link al token
6. El usuario debe confirmar su email con `POST /api/v1/auth/verify-email?token=...` antes de poder iniciar sesión

#### Nota Importante

La contraseña proporcionada en este endpoint se guarda temporalmente en el token de verificación (`password_temp`). Esta contraseña temporal:
- Se reutiliza en todos los reenvíos de verificación
- Solo se usa internamente para crear el usuario en AWS Cognito
- Nunca se envía por correo electrónico
- Se elimina permanentemente después de la verificación exitosa

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
  Token de verificación generado con password_temp
        ↓
  Email enviado con link de verificación
```

### 2. Verificación de Email

```
Usuario → Clic en link del email
        ↓
  POST /api/v1/auth/verify-email?token=...
        ↓
  Usuario creado en AWS Cognito
        ↓
  Contraseña establecida desde password_temp
        ↓
  Cliente actualizado a ACTIVE
        ↓
  password_temp eliminado permanentemente
        ↓
  Usuario puede hacer login con su contraseña
```

### 3. Email No Recibido (Reenvío)

```
Usuario → POST /api/v1/auth/resend-verification
        ↓
  Sistema busca password_temp del token previo
        ↓
  Nuevo token generado con el MISMO password_temp
        ↓
  Tokens anteriores invalidados
        ↓
  Nuevo email enviado
```

**Ventaja del Sistema de Reenvío:**
- El usuario puede solicitar reenvío 1, 10 o 100 veces
- La contraseña siempre será la misma (la que eligió al registrarse)
- No hay riesgo de inconsistencias
- Funciona incluso si los tokens expiran

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
- La contraseña se guarda temporalmente solo durante el proceso de verificación
- El `password_temp` se elimina permanentemente después de la verificación exitosa

### Verificación de Email

- Los endpoints de verificación están en `/api/v1/auth/`:
  - `POST /api/v1/auth/resend-verification` - Reenviar verificación
  - `POST /api/v1/auth/verify-email?token=...` - Verificar email
- El sistema reutiliza `password_temp` en reenvíos para garantizar consistencia
- Los tokens expiran en 24 horas pero pueden reenviarse indefinidamente
- La contraseña nunca se envía por correo, solo se usa internamente

### Acceso a Datos

- Siempre se valida el `client_id` del token
- No es posible cambiar el `client_id` de un usuario
- Los endpoints automáticamente filtran por cliente

### Usuario Maestro

- Se crea automáticamente con el cliente
- `is_master=True` por defecto
- Tiene permisos para invitar usuarios
- No puede eliminarse sin eliminar el cliente
- Solo los usuarios master tienen `password_temp` en el token de verificación
