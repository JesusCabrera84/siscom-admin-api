# Guía de Deployment con GitHub Actions

Esta guía te ayudará a configurar y utilizar GitHub Actions para deployments automáticos de SISCOM Admin API.

## 📋 Tabla de Contenidos

1. [Resumen de los Workflows](#resumen-de-los-workflows)
2. [Configuración Inicial](#configuración-inicial)
3. [Secrets y Variables](#secrets-y-variables)
4. [Preparación del Servidor EC2](#preparación-del-servidor-ec2)
5. [Primer Deployment](#primer-deployment)
6. [Troubleshooting](#troubleshooting)
7. [Mejores Prácticas](#mejores-prácticas)

## Resumen de los Workflows

### 🚀 Deploy (deploy.yml)

**Se ejecuta automáticamente cuando:**

- Haces push a la rama `master`

**Puedes ejecutarlo manualmente:**

- Desde GitHub Actions → Deploy to EC2 → Run workflow

**Qué hace:**

1. ✅ Verifica el código (Ruff + Black)
2. 🐋 Construye la imagen Docker
3. 📦 Comprime y copia la imagen al servidor EC2
4. 🗄️ Ejecuta las migraciones Alembic (`alembic upgrade head`)
5. 🚀 Despliega el contenedor en producción
6. ✅ Verifica que el deployment fue exitoso

> **Migraciones:** corren en un contenedor efímero (`docker run --rm`) con la imagen
> recién construida, la red `siscom-network` y el mismo `.env` del servidor, **antes**
> de detener el contenedor viejo. Si una migración falla, el deploy se detiene y la
> versión anterior sigue sirviendo tráfico.

### 🧪 CI (ci.yml)

**Se ejecuta automáticamente cuando:**

- Creas o actualizas un Pull Request hacia `master` o `develop`
- Haces push a la rama `develop`

**Qué hace:**

1. 🔍 Ejecuta linters (Ruff + Black)
2. 🧪 Ejecuta tests con pytest
3. 🐋 Construye y prueba la imagen Docker

## Configuración Inicial

### 1. Verificar la configuración local

Primero, ejecuta el script de verificación:

```bash
./scripts/verify_deployment_config.sh
```

Este script verificará que todos los archivos necesarios estén en su lugar.

### 2. Crear el Environment en GitHub

1. Ve a tu repositorio en GitHub
2. Settings → Environments → New environment
3. Nombre: `production`
4. (Opcional) Configura protection rules:
   - ✅ Required reviewers (para aprobar deployments)
   - ✅ Wait timer (esperar X minutos antes de deploy)

## Secrets y Variables

### 🔐 Configurar Secrets

Ve a: **Settings → Secrets and variables → Actions → Secrets → New repository secret**

Crea los siguientes secrets:

#### Secrets de EC2

| Secret         | Descripción                | Ejemplo                          |
| -------------- | -------------------------- | -------------------------------- |
| `EC2_HOST`     | IP o hostname del servidor | `3.85.123.45` o `api.siscom.com` |
| `EC2_USERNAME` | Usuario SSH                | `ubuntu` o `ec2-user`            |
| `EC2_SSH_KEY`  | Clave privada SSH completa | Contenido de `~/.ssh/id_rsa`     |
| `EC2_SSH_PORT` | Puerto SSH                 | `22`                             |

#### Secrets de Base de Datos

| Secret        | Descripción              | Ejemplo             |
| ------------- | ------------------------ | ------------------- |
| `DB_PASSWORD` | Contraseña de PostgreSQL | `secretpassword123` |

#### Secrets de AWS

| Secret                  | Descripción                            | Dónde obtenerlo                     |
| ----------------------- | -------------------------------------- | ----------------------------------- |
| `AWS_ACCESS_KEY_ID`     | Access Key de AWS                      | AWS Console → IAM → Users           |
| `AWS_SECRET_ACCESS_KEY` | Secret Key de AWS                      | AWS Console → IAM → Users           |
| `COGNITO_USER_POOL_ID`  | ID del User Pool                       | AWS Console → Cognito               |
| `COGNITO_CLIENT_ID`     | Client ID de Cognito                   | AWS Console → Cognito → App clients |
| `COGNITO_CLIENT_SECRET` | Client Secret de Cognito               | AWS Console → Cognito → App clients |
| `DEFAULT_USER_PASSWORD` | Password temporal para nuevos usuarios | `TempPass123!`                      |

### 🔧 Configurar Variables

Ve a: **Settings → Secrets and variables → Actions → Variables → New repository variable**

- `PROJECT_NAME`: Nombre del proyecto. Ejemplo: `SISCOM Admin API`
- `DB_HOST`: Hostname de PostgreSQL. Ejemplo: `siscom-db.xxxxx.us-east-1.rds.amazonaws.com`
- `DB_PORT`: Puerto de PostgreSQL. Ejemplo: `5432`
- `DB_USER`: Usuario de PostgreSQL. Ejemplo: `siscom_admin`
- `DB_NAME`: Nombre de la base de datos. Ejemplo: `siscom_admin`
- `COGNITO_REGION`: Región de AWS Cognito. Ejemplo: `us-east-1`
- `ALLOWED_ORIGINS`: Orígenes CORS permitidos. Ejemplo: `https://admin.geminislabs.com,https://nexus.geminislabs.com`

`ALLOWED_ORIGINS` acepta una lista separada por comas o un JSON array, por ejemplo:

```bash
https://admin.geminislabs.com,https://nexus.geminislabs.com
# o
["https://admin.geminislabs.com", "https://nexus.geminislabs.com"]
```

## Preparación del Servidor EC2

### 1. Conectarse al servidor

```bash
ssh -i tu-clave.pem ubuntu@tu-ip-ec2
```

### 2. Instalar Docker

```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Agregar tu usuario al grupo docker
sudo usermod -aG docker $USER

# Reiniciar la sesión SSH o ejecutar:
newgrp docker

# Verificar instalación
docker --version
```

### 3. Instalar Docker Compose

```bash
# Descargar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Dar permisos de ejecución
sudo chmod +x /usr/local/bin/docker-compose

# Verificar instalación
docker-compose --version
```

### 4. Crear la red Docker

```bash
docker network create siscom-network
```

### 5. Crear el directorio de trabajo

```bash
mkdir -p ~/siscom-admin-api
cd ~/siscom-admin-api
```

### 6. Configurar el firewall (si usas UFW)

```bash
# Permitir SSH
sudo ufw allow 22/tcp

# Permitir el puerto de la API
sudo ufw allow 8100/tcp

# Habilitar firewall
sudo ufw enable
```

### 7. Configurar Security Group en AWS

Asegúrate de que tu EC2 Security Group permita:

- **Puerto 22** (SSH) desde tu IP
- **Puerto 8100** (API) desde donde sea necesario
- **Puerto 5432** (PostgreSQL) si la base de datos está en la misma VPC

## Primer Deployment

### Opción 1: Push a master (automático)

```bash
# En tu máquina local
git checkout master
git pull origin master

# Hacer un cambio (si es necesario)
git add .
git commit -m "Setup GitHub Actions deployment"
git push origin master
```

El workflow se ejecutará automáticamente. Puedes ver el progreso en:
**GitHub → Actions → Deploy to EC2**

### Opción 2: Ejecución manual

1. Ve a **GitHub → Actions**
2. Selecciona **Deploy to EC2**
3. Click en **Run workflow**
4. Selecciona la rama `master`
5. Click en **Run workflow**

### Verificar el deployment

Una vez completado el workflow, verifica:

```bash
# Desde tu servidor EC2
ssh ubuntu@tu-ip-ec2

# Ver contenedores corriendo
docker ps

# Ver logs de la API
docker logs -f siscom-admin-api

# Verificar health check
curl http://localhost:8100/health

# Verificar variable CORS en archivo .env remoto
grep '^ALLOWED_ORIGINS=' ~/siscom-admin-api/.env

# Verificar variable CORS dentro del contenedor
docker exec siscom-admin-api printenv ALLOWED_ORIGINS
```

## Troubleshooting

### ❌ Error: "Permission denied (publickey)"

**Problema:** La clave SSH no tiene los permisos correctos o no es la correcta.

**Solución:**

1. Verifica que copiaste toda la clave privada (incluyendo `-----BEGIN` y `-----END`)
2. Asegúrate de que sea la clave privada, no la pública
3. Verifica que el usuario SSH sea correcto (`ubuntu` para Ubuntu, `ec2-user` para Amazon Linux)

### ❌ Error: "Connection timeout"

**Problema:** No se puede conectar al servidor EC2.

**Solución:**

1. Verifica que el Security Group permita conexiones SSH desde GitHub Actions IPs
2. O mejor aún, usa AWS Systems Manager Session Manager
3. Verifica que la IP del servidor sea correcta

### ❌ Error: "Container is unhealthy"

**Problema:** El contenedor no pasa el health check.

**Solución:**

```bash
# Ver logs del contenedor
docker logs siscom-admin-api

# Verificar que el health endpoint existe
curl http://localhost:8100/health

# Entrar al contenedor
docker exec -it siscom-admin-api /bin/bash
```

Causas comunes:

- Endpoint `/health` no implementado
- Base de datos no accesible
- Variables de entorno incorrectas

### ❌ Error: "Cannot connect to database"

**Problema:** La aplicación no puede conectarse a PostgreSQL.

**Solución:**

1. Verifica que el Security Group de RDS permita conexiones desde el EC2
1. Prueba la conexión manualmente:

```bash
# Desde el servidor EC2
psql -h tu-rds-endpoint.rds.amazonaws.com -U siscom_admin -d siscom_admin
```

1. Verifica las variables de entorno en `.env`

### ⚠️ Linter failures

**Problema:** Ruff o Black encuentran problemas en el código.

**Solución:**

```bash
# En local, antes de hacer push
make format      # Formatear con Black
make lint        # Ver problemas con Ruff

# O correr todas las verificaciones
make all-checks
```

## Mejores Prácticas

### 1. 🌿 Usa ramas de desarrollo

```bash
# Trabaja en una rama feature
git checkout -b feature/nueva-funcionalidad

# Haz tus cambios
git add .
git commit -m "Add: nueva funcionalidad"

# Push a GitHub
git push origin feature/nueva-funcionalidad

# Crea un Pull Request
# El workflow de CI se ejecutará automáticamente

# Una vez aprobado, merge a master para deployment
```

### 2. ✅ Verifica localmente antes de push

```bash
# Ejecutar todas las verificaciones
make all-checks

# Probar la imagen Docker localmente
make build
make deploy-test
make health
```

### 3. 📊 Monitorea los deployments

- Revisa los logs en GitHub Actions después de cada deployment
- Configura notificaciones (Slack, email, etc.) para deployments fallidos
- Mantén un registro de cambios (CHANGELOG.md)

### 4. 🔄 Rollback si es necesario

Si algo sale mal después del deployment:

```bash
# En el servidor EC2
cd ~/siscom-admin-api

# Ver imágenes disponibles
docker images | grep siscom-admin-api

# Detener contenedor actual
docker-compose -f docker-compose.prod.yml down

# Cambiar a imagen anterior
docker tag siscom-admin-api:previous siscom-admin-api:latest

# Levantar contenedor
docker-compose -f docker-compose.prod.yml up -d
```

### 5. 🔐 Rotación de secrets

- Rota tus secrets periódicamente (especialmente las claves de AWS)
- Actualiza los secrets en GitHub cuando cambien
- Después de actualizar un secret, redeploya manualmente

### 6. 📝 Mantén la documentación actualizada

- Si agregas nuevas variables de entorno, actualiza este documento
- Si cambias la configuración, actualiza los workflows
- Documenta cualquier cambio en el proceso de deployment

## Comandos Útiles

### En el servidor EC2

```bash
# Ver todos los contenedores
docker ps -a

# Ver logs en tiempo real
docker logs -f siscom-admin-api

# Ver últimas 100 líneas de logs
docker logs --tail 100 siscom-admin-api

# Entrar al contenedor
docker exec -it siscom-admin-api /bin/bash

# Ver uso de recursos
docker stats siscom-admin-api

# Reiniciar contenedor
docker restart siscom-admin-api

# Ver redes
docker network ls

# Limpiar recursos no usados
docker system prune -a
```

### En local

```bash
# Ver el status del workflow
gh workflow view "Deploy to EC2"

# Ejecutar workflow manualmente
gh workflow run "Deploy to EC2"

# Ver logs del último workflow
gh run list --workflow=deploy.yml
gh run view <run-id> --log
```

## Recursos Adicionales

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [AWS EC2 Documentation](https://docs.aws.amazon.com/ec2/)

## Soporte

Si tienes problemas con el deployment:

1. Revisa esta documentación
2. Ejecuta el script de verificación: `./scripts/verify_deployment_config.sh`
3. Revisa los logs en GitHub Actions
4. Revisa los logs del contenedor en el servidor
5. Contacta al equipo de DevOps

---

**Última actualización:** Noviembre 2025
