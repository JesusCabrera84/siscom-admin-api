# Configurar Variable CONTACT_EMAIL en GitHub Actions

Esta guía te ayudará a configurar la variable `CONTACT_EMAIL` en GitHub Actions para el deployment automático.

## 📋 ¿Qué es CONTACT_EMAIL?

`CONTACT_EMAIL` es la dirección de correo electrónico donde se recibirán todos los mensajes enviados desde el formulario de contacto del sitio web.

**Tipo**: Variable (no secret) - Es información pública que puede estar visible.

## 🚀 Pasos para Configurar

### 1. Ir a la Configuración del Repositorio

1. Ve a tu repositorio en GitHub
2. Haz clic en **Settings** (Configuración)
3. En el menú lateral izquierdo, busca **Secrets and variables**
4. Haz clic en **Actions**

### 2. Agregar la Variable

1. Selecciona la pestaña **Variables** (no Secrets)
2. Haz clic en **New repository variable**
3. Completa los campos:
   - **Name**: `CONTACT_EMAIL`
   - **Value**: `contacto@geminislabs.com`
4. Haz clic en **Add variable**

## 📸 Captura Visual

```
GitHub Repository → Settings → Secrets and variables → Actions → Variables tab

┌─────────────────────────────────────────────────────────┐
│ Repository variables                                     │
├─────────────────────────────────────────────────────────┤
│ Name                    Value                   Updated  │
│ CONTACT_EMAIL          contacto@geminislabs... Now      │
│ SES_FROM_EMAIL         noreply@geminislabs...  ...      │
│ SES_REGION             us-east-1                ...      │
│ FRONTEND_URL           https://...              ...      │
└─────────────────────────────────────────────────────────┘
```

## ✅ Variables Existentes que Debes Tener

Asegúrate de tener **todas** estas variables configuradas:

### Variables (Public - No Secrets)

| Variable         | Ejemplo                       | Descripción                             |
| ---------------- | ----------------------------- | --------------------------------------- |
| `CONTACT_EMAIL`  | `contacto@geminislabs.com`    | Email para recibir mensajes de contacto |
| `SES_FROM_EMAIL` | `noreply@geminislabs.com`     | Email remitente de SES                  |
| `SES_REGION`     | `us-east-1`                   | Región de AWS SES                       |
| `FRONTEND_URL`   | `https://app.geminislabs.com` | URL del frontend                        |
| `PROJECT_NAME`   | `SISCOM Admin API`            | Nombre del proyecto                     |
| `DB_HOST`        | `localhost`                   | Host de la base de datos                |
| `DB_PORT`        | `5432`                        | Puerto de la base de datos              |
| `DB_USER`        | `siscom`                      | Usuario de la base de datos             |
| `DB_NAME`        | `siscom_admin`                | Nombre de la base de datos              |
| `COGNITO_REGION` | `us-east-1`                   | Región de AWS Cognito                   |

### Secrets (Private - Encrypted)

| Secret                  | Descripción                     |
| ----------------------- | ------------------------------- |
| `DB_PASSWORD`           | Contraseña de la base de datos  |
| `COGNITO_USER_POOL_ID`  | ID del User Pool de Cognito     |
| `COGNITO_CLIENT_ID`     | Client ID de Cognito            |
| `COGNITO_CLIENT_SECRET` | Client Secret de Cognito        |
| `DEFAULT_USER_PASSWORD` | Contraseña temporal por defecto |
| `EC2_HOST`              | IP o hostname del servidor EC2  |
| `EC2_USERNAME`          | Usuario SSH del servidor        |
| `EC2_SSH_KEY`           | Clave privada SSH               |
| `EC2_SSH_PORT`          | Puerto SSH (usualmente 22)      |

## 🔍 Verificar la Configuración

### Opción 1: Ver Variables en GitHub

1. Ve a **Settings** → **Secrets and variables** → **Actions**
2. Pestaña **Variables**
3. Verifica que `CONTACT_EMAIL` aparezca en la lista

### Opción 2: Verificar en el Workflow

Después de hacer un push a `master`, verifica el workflow:

1. Ve a la pestaña **Actions** del repositorio
2. Haz clic en el workflow más reciente
3. Expande **Deploy to EC2** → **Deploy to EC2** step
4. Busca en los logs: `CONTACT_EMAIL=${CONTACT_EMAIL}`

Deberías ver algo como:

```bash
🔧 Configurando variables de entorno...
PROJECT_NAME=SISCOM Admin API
DB_HOST=localhost
...
CONTACT_EMAIL=contacto@geminislabs.com
```

## 🧪 Probar el Deployment

Después de configurar la variable, haz un cambio pequeño y haz push:

```bash
# Hacer un cambio pequeño
echo "# Test" >> README.md
git add README.md
git commit -m "test: verificar CONTACT_EMAIL en deployment"
git push origin master
```

Luego verifica que el deployment se complete exitosamente y que la variable esté presente.

## 🐛 Troubleshooting

### Error: "CONTACT_EMAIL: Field required"

**Causa**: La variable no está configurada en GitHub Actions

**Solución**:

1. Verifica que agregaste la variable en **Variables** (no en Secrets)
2. Verifica que el nombre sea exactamente `CONTACT_EMAIL` (case-sensitive)
3. Verifica que el valor no esté vacío

### La variable no aparece en el contenedor

**Causa**: El workflow de deployment no se actualizó

**Solución**:

1. Asegúrate de haber hecho pull del último código:
   ```bash
   git pull origin master
   ```
2. Verifica que el archivo `.github/workflows/deploy.yml` tenga `CONTACT_EMAIL` en:
   - Línea ~91: `CONTACT_EMAIL: ${{ vars.CONTACT_EMAIL }}`
   - Línea ~97: En la lista de `envs`
   - Línea ~124: En el archivo `.env` que se genera

### El endpoint devuelve "servicio no configurado"

**Causa**: La variable no llegó al contenedor o está vacía

**Solución**:

1. Conéctate al servidor EC2:
   ```bash
   ssh user@server
   ```
2. Verifica que el contenedor tenga la variable:

   ```bash
   docker exec siscom-admin-api env | grep CONTACT_EMAIL
   ```

   Debería mostrar: `CONTACT_EMAIL=contacto@geminislabs.com`

3. Si no aparece, verifica el archivo `.env` en el servidor:
   ```bash
   cat ~/siscom-admin-api/.env | grep CONTACT_EMAIL
   ```

## 📝 Comandos Útiles

### Ver todas las variables configuradas en GitHub

```bash
# Usando GitHub CLI (gh)
gh variable list
```

### Agregar la variable usando GitHub CLI

```bash
gh variable set CONTACT_EMAIL --body "contacto@geminislabs.com"
```

### Actualizar la variable

```bash
# Método 1: GitHub Web UI
# Settings → Secrets and variables → Actions → Variables → Edit

# Método 2: GitHub CLI
gh variable set CONTACT_EMAIL --body "nuevo-email@geminislabs.com"
```

### Eliminar la variable (no recomendado)

```bash
gh variable delete CONTACT_EMAIL
```

## 🌐 Configuración para Múltiples Ambientes

Si tienes múltiples ambientes (dev, staging, production):

### Opción 1: Ambientes de GitHub

1. Ve a **Settings** → **Environments**
2. Crea ambientes: `test`, `staging`, `production`
3. En cada ambiente, agrega `CONTACT_EMAIL` con valores diferentes:
   - **test**: `test-contact@geminislabs.com`
   - **staging**: `staging-contact@geminislabs.com`
   - **production**: `contacto@geminislabs.com`

### Opción 2: Variables con Prefijo

```bash
# En Variables de GitHub
CONTACT_EMAIL_DEV=dev-contact@geminislabs.com
CONTACT_EMAIL_STAGING=staging-contact@geminislabs.com
CONTACT_EMAIL_PROD=contacto@geminislabs.com
```

Luego en el workflow:

```yaml
env:
  CONTACT_EMAIL: ${{ vars.CONTACT_EMAIL_PROD }} # o _DEV, _STAGING
```

## ✅ Checklist Final

Antes de hacer deployment, verifica:

- [ ] Variable `CONTACT_EMAIL` agregada en GitHub Actions (Variables)
- [ ] Valor correcto: `contacto@geminislabs.com`
- [ ] Email verificado en AWS SES
- [ ] Workflow actualizado con la variable
- [ ] Cambios commiteados y pusheados a master
- [ ] Deployment exitoso
- [ ] Variable presente en el contenedor
- [ ] Endpoint de contacto funciona correctamente

## 📚 Referencias

- [GitHub Actions Variables Documentation](https://docs.github.com/en/actions/learn-github-actions/variables)
- [GitHub Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Configuración de AWS SES](./email-configuration.md)
- [API de Contacto](../api/contact.md)

## 💡 Buenas Prácticas

1. ✅ **Usar Variables para información pública** (como emails de contacto)
2. ✅ **Usar Secrets para información sensible** (como contraseñas)
3. ✅ **Documentar todas las variables** necesarias
4. ✅ **Usar valores por defecto** en docker-compose.yml para desarrollo local
5. ✅ **Verificar variables** después de cada deployment
6. ✅ **Mantener valores actualizados** en la documentación

---

**¿Necesitas ayuda?**

- Revisa los logs del workflow en la pestaña **Actions**
- Verifica la configuración en **Settings** → **Secrets and variables**
- Consulta la documentación en `/docs/guides/`
