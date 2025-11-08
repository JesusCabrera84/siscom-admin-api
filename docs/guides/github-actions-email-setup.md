# Configuración de Variables de GitHub Actions para Emails

Esta guía te ayudará a configurar las nuevas variables de entorno necesarias para el sistema de emails en GitHub Actions.

## Variables a Configurar en GitHub

Para que el pipeline de CI/CD funcione correctamente con el sistema de emails, necesitas agregar las siguientes variables en tu repositorio de GitHub.

### Cómo Acceder a la Configuración

1. Ve a tu repositorio en GitHub
2. Haz clic en **Settings** (Configuración)
3. En el menú lateral, ve a **Secrets and variables** → **Actions**
4. Verás dos tabs: **Secrets** y **Variables**

---

## Variables Nuevas Requeridas

### 1. Variables de Repositorio (Repository Variables)

Estas se agregan en el tab **Variables**:

| Nombre | Valor de Ejemplo | Descripción |
|--------|------------------|-------------|
| `SES_FROM_EMAIL` | `noreply@tudominio.com` | Email verificado en AWS SES que se usará como remitente |
| `SES_REGION` | `us-east-1` | Región de AWS SES (puede ser la misma que COGNITO_REGION) |
| `FRONTEND_URL` | `https://app.tudominio.com` | URL base de tu aplicación frontend (sin trailing slash) |

#### Pasos para agregar Variables:

```bash
1. Settings → Secrets and variables → Actions → Variables
2. Clic en "New repository variable"
3. Name: SES_FROM_EMAIL
   Value: noreply@tudominio.com
4. Clic en "Add variable"
5. Repetir para SES_REGION y FRONTEND_URL
```

### 2. Secrets Existentes (No requieren cambios)

Los siguientes secrets ya deben estar configurados:

- `EC2_HOST` - IP o hostname del servidor EC2
- `EC2_USERNAME` - Usuario SSH del EC2
- `EC2_SSH_KEY` - Llave privada SSH
- `EC2_SSH_PORT` - Puerto SSH (usualmente 22)
- `DB_PASSWORD` - Contraseña de la base de datos
- `COGNITO_USER_POOL_ID` - ID del User Pool de Cognito
- `COGNITO_CLIENT_ID` - Client ID de Cognito
- `COGNITO_CLIENT_SECRET` - Client Secret de Cognito
- `DEFAULT_USER_PASSWORD` - Contraseña por defecto

---

## Captura de Pantalla de Ejemplo

Tu configuración en GitHub debería verse así:

### Variables (Repository Variables):
```
PROJECT_NAME          = SISCOM Admin API
DB_HOST               = tu-db-host
DB_PORT               = 5432
DB_USER               = siscom
DB_NAME               = siscom_admin
COGNITO_REGION        = us-east-1
SES_FROM_EMAIL        = noreply@tudominio.com    ← NUEVA
SES_REGION            = us-east-1                 ← NUEVA
FRONTEND_URL          = https://app.tudominio.com ← NUEVA
```

### Secrets (Repository Secrets):
```
EC2_HOST
EC2_USERNAME
EC2_SSH_KEY
EC2_SSH_PORT
DB_PASSWORD
COGNITO_USER_POOL_ID
COGNITO_CLIENT_ID
COGNITO_CLIENT_SECRET
DEFAULT_USER_PASSWORD
```

---

## Verificación de la Configuración

### 1. Verificar que las variables están configuradas

Después de agregarlas, puedes verificar ejecutando un workflow manualmente:

```bash
1. Ve a tu repositorio en GitHub
2. Clic en "Actions"
3. Selecciona el workflow "Deploy to EC2"
4. Clic en "Run workflow" → "Run workflow"
5. Revisa los logs del deployment
```

### 2. Verificar en el servidor EC2

Una vez que el deployment se complete, verifica que las variables se pasaron correctamente:

```bash
# Conectarse al servidor EC2
ssh usuario@ec2-ip

# Ir al directorio del proyecto
cd siscom-admin-api

# Ver las variables de entorno configuradas
cat .env

# Deberías ver:
# SES_FROM_EMAIL=noreply@tudominio.com
# SES_REGION=us-east-1
# FRONTEND_URL=https://app.tudominio.com
```

### 3. Verificar que el contenedor tiene las variables

```bash
# Ver las variables de entorno del contenedor
docker exec siscom-admin-api env | grep -E "SES|FRONTEND"

# Deberías ver:
# SES_FROM_EMAIL=noreply@tudominio.com
# SES_REGION=us-east-1
# FRONTEND_URL=https://app.tudominio.com
```

---

## Troubleshooting

### ❌ Error: "SES_FROM_EMAIL is required"

**Causa**: La variable no está configurada en GitHub

**Solución**:
```bash
1. Ve a Settings → Secrets and variables → Actions → Variables
2. Verifica que SES_FROM_EMAIL esté configurada
3. Si no está, agrégala
4. Vuelve a ejecutar el workflow
```

### ❌ El workflow falla en "Deploy to EC2"

**Causa**: Las variables no se están pasando correctamente al SSH

**Solución**:
```bash
1. Verifica que las variables estén en el campo "envs" del deploy.yml
2. Debe incluir: SES_FROM_EMAIL,SES_REGION,FRONTEND_URL
3. Si no están, el archivo deploy.yml no está actualizado
```

### ❌ El contenedor arranca pero los emails no se envían

**Causa 1**: Las variables no se pasaron al contenedor

**Solución**:
```bash
# Verificar en el servidor
docker exec siscom-admin-api python -c "from app.core.config import settings; print(settings.SES_FROM_EMAIL)"
```

**Causa 2**: El email no está verificado en AWS SES

**Solución**:
```bash
# Ir a AWS SES Console y verificar el email
```

---

## Uso con GitHub Environments

Si estás usando GitHub Environments (recomendado para diferentes entornos):

### Environment: test

```bash
Variables:
- SES_FROM_EMAIL = test@tudominio.com
- SES_REGION = us-east-1
- FRONTEND_URL = https://test-app.tudominio.com
```

### Environment: production

```bash
Variables:
- SES_FROM_EMAIL = noreply@tudominio.com
- SES_REGION = us-east-1
- FRONTEND_URL = https://app.tudominio.com
```

---

## Comandos Útiles

### Ver todas las variables configuradas en GitHub (usando gh CLI)

```bash
# Instalar gh CLI si no lo tienes
# https://cli.github.com/

# Ver variables
gh variable list

# Ver secrets (solo los nombres, no los valores)
gh secret list

# Agregar una variable
gh variable set SES_FROM_EMAIL --body "noreply@tudominio.com"

# Agregar una variable para un environment específico
gh variable set SES_FROM_EMAIL --body "test@tudominio.com" --env test
```

### Probar el deployment localmente

```bash
# Simular las variables de GitHub Actions
export SES_FROM_EMAIL="noreply@tudominio.com"
export SES_REGION="us-east-1"
export FRONTEND_URL="https://app.tudominio.com"

# Ejecutar docker-compose con las variables
docker-compose -f docker-compose.prod.yml up -d

# Verificar que el contenedor tiene las variables
docker exec siscom-admin-api env | grep -E "SES|FRONTEND"
```

---

## Checklist de Configuración

Antes de hacer push a master y disparar el deployment, verifica:

- [ ] ✅ Variables agregadas en GitHub (Settings → Secrets and variables → Actions → Variables):
  - [ ] `SES_FROM_EMAIL`
  - [ ] `SES_REGION`
  - [ ] `FRONTEND_URL`

- [ ] ✅ Email verificado en AWS SES Console:
  - [ ] Ir a SES → Verified identities
  - [ ] Verificar que el email de `SES_FROM_EMAIL` está verificado

- [ ] ✅ Permisos IAM configurados en EC2:
  - [ ] El IAM Role tiene permisos `ses:SendEmail` y `ses:SendRawEmail`

- [ ] ✅ Archivos actualizados:
  - [ ] `.github/workflows/deploy.yml` (incluye las nuevas variables)
  - [ ] `docker-compose.prod.yml` (incluye las nuevas variables)
  - [ ] `docker-compose.yml` (incluye las nuevas variables)

- [ ] ✅ Dependencia agregada:
  - [ ] `jinja2==3.1.3` en `requirements.txt`

---

## Referencias

- [GitHub Actions - Using secrets and variables](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions)
- [AWS SES - Verificación de identidades](https://docs.aws.amazon.com/ses/latest/dg/creating-identities.html)
- [Guía de configuración de emails](./email-configuration.md)

---

**Fecha de actualización**: 2025-11-08

