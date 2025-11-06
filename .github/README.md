# GitHub Actions - Configuración

Este directorio contiene los workflows de GitHub Actions para CI/CD del proyecto SISCOM Admin API.

## 📋 Workflows Disponibles

### 1. `deploy.yml` - Deployment Automático
Se ejecuta cuando:
- Se hace push a la rama `master`
- Se ejecuta manualmente desde GitHub Actions

**Pasos:**
1. Verifica el código con Ruff y Black
2. Construye la imagen Docker
3. Copia la imagen al servidor EC2
4. Despliega el contenedor en producción
5. Verifica que el deployment fue exitoso

### 2. `ci.yml` - Integración Continua
Se ejecuta cuando:
- Se crea o actualiza un Pull Request hacia `master` o `develop`
- Se hace push a la rama `develop`

**Pasos:**
1. Ejecuta linters (Ruff, Black)
2. Ejecuta tests con pytest
3. Construye y prueba la imagen Docker

## 🔐 Secrets Requeridos

Debes configurar los siguientes secrets en GitHub:
**Settings → Secrets and variables → Actions → New repository secret**

### Secrets de EC2:
```
EC2_HOST                    # IP o hostname del servidor EC2
EC2_USERNAME                # Usuario SSH (ej: ubuntu, ec2-user)
EC2_SSH_KEY                 # Clave privada SSH (contenido completo)
EC2_SSH_PORT                # Puerto SSH (generalmente 22)
```

### Secrets de Base de Datos:
```
DB_PASSWORD                 # Contraseña de PostgreSQL
```

### Secrets de AWS Cognito:
```
COGNITO_USER_POOL_ID        # ID del User Pool de Cognito (ej: us-east-1_XXXXXXXX)
COGNITO_CLIENT_ID           # Client ID de Cognito
COGNITO_CLIENT_SECRET       # Client Secret de Cognito
DEFAULT_USER_PASSWORD       # Contraseña temporal por defecto para nuevos usuarios
```

**💡 Nota sobre AWS Credentials**: NO necesitas configurar `AWS_ACCESS_KEY_ID` ni `AWS_SECRET_ACCESS_KEY` si tu instancia EC2 tiene un **IAM Role** asignado con permisos para Cognito. Boto3 usará automáticamente las credenciales del IAM Role. Esta es la forma recomendada y más segura.

📖 **Ver guía completa**: [Configuración de IAM Role para EC2](../docs/guides/iam-role-setup.md)

## 🔧 Variables de Entorno (Variables)

Configura estas variables en:
**Settings → Secrets and variables → Actions → Variables → New repository variable**

⚠️ **IMPORTANTE**: Estas deben configurarse como **Variables**, NO como Secrets:

| Variable | Valor de Ejemplo | Descripción |
|----------|------------------|-------------|
| `PROJECT_NAME` | `SISCOM Admin API` | Nombre del proyecto |
| `DB_HOST` | `siscom-db.xxxxx.us-east-1.rds.amazonaws.com` | Endpoint de RDS |
| `DB_PORT` | `5432` | Puerto de PostgreSQL |
| `DB_USER` | `siscom_admin` | Usuario de PostgreSQL |
| `DB_NAME` | `siscom_admin` | Nombre de la base de datos |
| `COGNITO_REGION` | `us-east-1` | **⚠️ CRÍTICO**: Región de AWS Cognito (ej: us-east-1, us-west-2) |

**Nota Importante**: `COGNITO_REGION` es crítica - si no está configurada o está vacía, el deployment fallará con error: `Invalid endpoint: https://cognito-idp..amazonaws.com`

## 🌍 Environments

El workflow de deploy usa el environment `production`. Debes crearlo en:
**Settings → Environments → New environment**

Nombre: `production`

Puedes configurar:
- **Protection rules**: Requerir aprobación antes de deploy
- **Environment secrets**: Secrets específicos para este environment

## 📝 Preparación del Servidor EC2

Antes de ejecutar el workflow por primera vez, asegúrate de que tu servidor EC2 tenga:

### 1. Docker y Docker Compose instalados:
```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Crear la red Docker:
```bash
docker network create siscom-network
```

### 3. Configurar el directorio de trabajo:
```bash
mkdir -p ~/siscom-admin-api
```

### 4. Configurar el firewall (si es necesario):
```bash
# Permitir tráfico en el puerto 8100
sudo ufw allow 8100/tcp
```

## 🚀 Ejecutar Deployment Manual

1. Ve a **Actions** en tu repositorio de GitHub
2. Selecciona el workflow **Deploy to EC2**
3. Click en **Run workflow**
4. Selecciona la rama `master`
5. Click en **Run workflow**

## 🧪 Testing Local del Workflow

Para probar el deployment localmente antes de hacer push:

```bash
# Construir la imagen
docker build -t siscom-admin-api:latest .

# Crear archivo .env para testing
cat > .env << EOF
PROJECT_NAME=SISCOM Admin API
DB_HOST=localhost
DB_PORT=5432
DB_USER=siscom
DB_PASSWORD=changeme
DB_NAME=siscom_admin
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
COGNITO_REGION=us-east-1
COGNITO_USER_POOL_ID=your_pool_id
COGNITO_CLIENT_ID=your_client_id
COGNITO_CLIENT_SECRET=your_client_secret
DEFAULT_USER_PASSWORD=TempPass123!
EOF

# Levantar con docker-compose
docker-compose -f docker-compose.prod.yml up -d

# Ver logs
docker logs -f siscom-admin-api

# Verificar health
curl http://localhost:8100/health
```

## 🔍 Troubleshooting

### ⚠️ Guía Completa de Troubleshooting

Para problemas comunes y soluciones detalladas, consulta:
📖 **[Guía de Troubleshooting Completa](../docs/guides/troubleshooting-deployment.md)**

### Problemas Comunes Rápidos

#### Error: "Port 8100 already allocated"

**Solución Automática**: Vuelve a ejecutar el workflow manualmente desde GitHub Actions.

**Solución Manual**: Ejecuta en el servidor:
```bash
cd ~/siscom-admin-api
./scripts/cleanup_deployment.sh
```

#### El deployment falla en "Deploy to EC2"
- Verifica que los secrets estén configurados correctamente
- Asegúrate de que la clave SSH tenga los permisos correctos
- Revisa que el servidor EC2 sea accesible desde GitHub Actions

#### El contenedor no inicia correctamente
- Revisa los logs: `docker logs siscom-admin-api`
- Verifica que todas las variables de entorno estén configuradas
- Asegúrate de que la base de datos sea accesible desde el servidor

#### Error de conexión a la base de datos
- Verifica que el security group de RDS permita conexiones desde el EC2
- Confirma que las credenciales de BD sean correctas
- Prueba la conexión manualmente desde el servidor EC2

Para más detalles y soluciones avanzadas, consulta la **[Guía de Troubleshooting](../docs/guides/troubleshooting-deployment.md)**

## 📚 Recursos Adicionales

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## 🤝 Contribuir

Para contribuir mejoras a los workflows:

1. Crea una rama para tus cambios
2. Prueba los workflows localmente cuando sea posible
3. Crea un Pull Request
4. El workflow de CI se ejecutará automáticamente

