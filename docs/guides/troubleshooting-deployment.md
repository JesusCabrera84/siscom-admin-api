# Troubleshooting - Problemas de Deployment

Esta guía te ayudará a resolver problemas comunes durante el deployment de SISCOM Admin API.

## 🔴 Error: "Bind for 0.0.0.0:8100 failed: port is already allocated"

### Descripción del Problema

```
Error response from daemon: driver failed programming external connectivity
on endpoint siscom-admin-api: Bind for 0.0.0.0:8100 failed: port is already allocated
```

Este error ocurre cuando:

- Hay un contenedor anterior que no se detuvo correctamente
- Otro proceso está usando el puerto 8100
- Hay contenedores huérfanos que siguen usando el puerto

### ✅ Solución Automática (Recomendada)

El workflow de GitHub Actions ahora incluye limpieza automática. Si el deployment falla, vuelve a ejecutarlo manualmente:

1. Ve a **GitHub → Actions → Deploy to EC2**
2. Click en **Run workflow**
3. Selecciona la rama `master`
4. Click en **Run workflow**

El workflow ahora:

- ✅ Detecta automáticamente contenedores usando el puerto 8100
- ✅ Los detiene y elimina
- ✅ Limpia contenedores huérfanos
- ✅ Verifica que el nuevo contenedor inicie correctamente

### 🔧 Solución Manual (Si la automática falla)

#### Opción 1: Script de Limpieza

Ejecuta el script de limpieza en tu servidor EC2:

```bash
# Conectarse al servidor
ssh -i tu-clave.pem ubuntu@tu-ip-ec2

# Navegar al directorio del proyecto
cd ~/siscom-admin-api

# Ejecutar el script de limpieza
./scripts/cleanup_deployment.sh
```

#### Opción 2: Limpieza Manual

Si no tienes el script, ejecuta estos comandos:

```bash
# 1. Detener el contenedor por nombre
docker stop siscom-admin-api
docker rm siscom-admin-api

# 2. Encontrar y detener contenedores usando el puerto 8100
docker ps | grep 8100
docker stop $(docker ps -q --filter "publish=8100")

# 3. Limpiar con docker-compose
cd ~/siscom-admin-api
docker-compose -f docker-compose.prod.yml down --remove-orphans

# 4. Verificar que el puerto esté libre
docker ps | grep 8100
# (no debería mostrar nada)

# 5. Levantar el contenedor nuevamente
docker-compose -f docker-compose.prod.yml up -d
```

#### Opción 3: Identificar qué está usando el puerto

```bash
# Ver qué contenedores usan el puerto 8100
docker ps --format "{{.Names}}\t{{.Ports}}" | grep 8100

# Ver procesos del sistema usando el puerto 8100
sudo lsof -i :8100
# o
sudo netstat -tulpn | grep 8100
```

---

## 🔴 Error: "Invalid endpoint: https://cognito-idp..amazonaws.com"

### Descripción del Problema

```
ValueError: Invalid endpoint: https://cognito-idp..amazonaws.com
COGNITO_REGION cannot be empty
```

Este error ocurre cuando `COGNITO_REGION` está vacía o no está configurada. Nota los **dos puntos seguidos** (`..`) en la URL - esto indica que la región está vacía.

### ✅ Solución

#### 1. Verificar que COGNITO_REGION esté configurada en GitHub

La variable **debe estar configurada como Variable**, NO como Secret:

1. Ve a tu repositorio en GitHub
2. **Settings → Secrets and variables → Actions → Variables**
3. Click en **New repository variable**
4. Nombre: `COGNITO_REGION`
5. Valor: Tu región de AWS (ejemplo: `us-east-1`, `us-west-2`, etc.)
6. Click en **Add variable**

#### 2. Verificar el valor

Regiones válidas de AWS:

- `us-east-1` (Virginia del Norte)
- `us-east-2` (Ohio)
- `us-west-1` (California del Norte)
- `us-west-2` (Oregón)
- `eu-west-1` (Irlanda)
- `eu-central-1` (Frankfurt)
- `ap-southeast-1` (Singapur)
- [Lista completa de regiones](https://docs.aws.amazon.com/general/latest/gr/rande.html)

#### 3. Volver a ejecutar el workflow

Después de configurar la variable, ejecuta el workflow nuevamente:

1. **GitHub → Actions → Deploy to EC2**
2. Click en **Run workflow**
3. Selecciona la rama `master`
4. Click en **Run workflow**

---

## 🔴 Error: "Container status: not_found" o "created"

### Descripción del Problema

```
Intento X/30: Status = not_found
Estado actual: created
```

El contenedor fue creado pero no pudo iniciar. Causas comunes:

1. **Variables de entorno faltantes o incorrectas**
2. **No puede conectarse a la base de datos**
3. **Error en la configuración de AWS Cognito**
4. **Imagen Docker corrupta**

### ✅ Soluciones

#### 1. Verificar logs del contenedor

```bash
# Ver logs completos
docker logs siscom-admin-api

# Ver últimas 50 líneas
docker logs --tail 50 siscom-admin-api

# Seguir logs en tiempo real
docker logs -f siscom-admin-api
```

#### 2. Verificar variables de entorno

```bash
# Verificar que el archivo .env existe
cd ~/siscom-admin-api
cat .env

# Verificar variables dentro del contenedor (si está corriendo)
docker exec siscom-admin-api env | grep -E "DB_|AWS_|COGNITO_"
```

#### 3. Probar conexión a la base de datos

```bash
# Desde el servidor EC2
psql -h $DB_HOST -U $DB_USER -d $DB_NAME

# Si falla, verificar:
# - Security Groups de RDS permiten conexiones desde EC2
# - Credenciales correctas en GitHub Secrets
# - El endpoint de RDS es correcto
```

#### 4. Verificar configuración de AWS Cognito

```bash
# Ver variables de Cognito
cd ~/siscom-admin-api
grep COGNITO .env

# Verificar que los valores sean correctos:
# - COGNITO_REGION (ej: us-east-1)
# - COGNITO_USER_POOL_ID (ej: us-east-1_XXXXXXXXX)
# - COGNITO_CLIENT_ID
# - COGNITO_CLIENT_SECRET
```

#### 5. Reconstruir la imagen Docker

Si sospechas que la imagen está corrupta:

```bash
# En tu máquina local, forzar rebuild
docker build --no-cache -t siscom-admin-api:latest .

# Luego hacer push/deploy nuevamente
git add .
git commit -m "Rebuild Docker image"
git push origin master
```

---

## 🔴 Error: "Container is unhealthy"

### Descripción del Problema

```
ERROR: Contenedor está unhealthy
```

El contenedor inició pero el health check falló.

### ✅ Soluciones

#### 1. Verificar que el endpoint /health funciona

```bash
# Desde el servidor EC2
curl http://localhost:8100/health

# O usando la IP del contenedor
CONTAINER_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' siscom-admin-api)
curl http://$CONTAINER_IP:8100/health
```

#### 2. Verificar configuración del health check

El `docker-compose.prod.yml` tiene configurado:

```yaml
healthcheck:
  test:
    [
      "CMD",
      "python",
      "-c",
      "import urllib.request; urllib.request.urlopen('http://localhost:8100/health').read()",
    ]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

Si la aplicación tarda mucho en iniciar, aumenta el `start_period`:

```yaml
start_period: 60s # o más
```

#### 3. Deshabilitar health check temporalmente (debugging)

Si necesitas debuggear, comenta el health check:

```yaml
# healthcheck:
#   test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"]
```

Luego vuelve a habilitarlo cuando encuentres el problema.

---

## 🔴 Error: "Cannot connect to database"

### Descripción del Problema

```
sqlalchemy.exc.OperationalError: could not connect to server
```

### ✅ Soluciones

#### 1. Verificar Security Groups de RDS

En la consola de AWS:

1. Ve a **RDS → Databases → Tu BD → Connectivity & security**
2. Click en el **Security group**
3. En la tab **Inbound rules**, verifica que exista una regla:
   - **Type**: PostgreSQL (5432)
   - **Source**: Security group de tu EC2 (o su IP)

#### 2. Verificar credenciales

```bash
# Probar conexión manualmente
psql -h TU_RDS_ENDPOINT -U siscom_admin -d siscom_admin

# Si falla, verifica en GitHub:
# Settings → Secrets → DB_PASSWORD, DB_USER, DB_HOST, etc.
```

#### 3. Verificar que la BD esté accesible

```bash
# Desde el servidor EC2
telnet TU_RDS_ENDPOINT 5432
# Debería conectarse. Presiona Ctrl+] y escribe "quit"

# O con netcat
nc -zv TU_RDS_ENDPOINT 5432
```

---

## 🔴 Deployment exitoso pero la API no responde

### Verificaciones

```bash
# 1. Verificar que el contenedor está corriendo
docker ps | grep siscom-admin-api

# 2. Verificar el estado de salud
docker inspect siscom-admin-api | grep -A 5 Health

# 3. Ver los logs
docker logs siscom-admin-api

# 4. Verificar que el puerto está abierto
curl http://localhost:8100/
curl http://localhost:8100/health

# 5. Verificar Security Group del EC2
# Debe permitir tráfico en el puerto 8100
```

### Abrir puerto en el Security Group

1. Ve a **EC2 → Security Groups**
2. Selecciona el security group de tu instancia
3. **Inbound rules → Edit inbound rules → Add rule**:
   - Type: Custom TCP
   - Port: 8100
   - Source: 0.0.0.0/0 (o tu IP específica)
4. **Save rules**

---

## 🔴 Workflow de GitHub Actions falla en "Build Docker image"

### Soluciones

```bash
# 1. Verificar que el Dockerfile es válido
docker build -t siscom-admin-api:latest .

# 2. Verificar que requirements.txt es correcto
pip install -r requirements.txt

# 3. Si hay errores de dependencias, actualiza requirements.txt
pip freeze > requirements.txt
```

---

## 🔴 Workflow falla en "Copy files to EC2"

### Causas comunes:

1. **SSH Key incorrecta**
2. **Host no alcanzable**
3. **Permisos del directorio**

### Soluciones

#### 1. Verificar SSH Key

```bash
# En tu máquina local, prueba la conexión
ssh -i tu-clave.pem ubuntu@tu-ip-ec2

# Si funciona, el problema puede ser el formato del secret
# Asegúrate de copiar la clave COMPLETA, incluyendo:
# -----BEGIN RSA PRIVATE KEY-----
# ...
# -----END RSA PRIVATE KEY-----
```

#### 2. Verificar conectividad

```bash
# Ping al servidor
ping tu-ip-ec2

# Verificar puerto SSH
nc -zv tu-ip-ec2 22
```

#### 3. Verificar Security Group

El Security Group debe permitir:

- SSH (puerto 22) desde las IPs de GitHub Actions
- O mejor: desde 0.0.0.0/0 (con autenticación por clave)

---

## 📝 Comandos Útiles para Debugging

```bash
# Ver todos los contenedores (incluyendo detenidos)
docker ps -a

# Ver logs de un contenedor detenido
docker logs siscom-admin-api

# Ver uso de recursos
docker stats siscom-admin-api

# Entrar al contenedor (si está corriendo)
docker exec -it siscom-admin-api /bin/bash

# Ver variables de entorno del contenedor
docker exec siscom-admin-api env

# Ver redes Docker
docker network ls
docker network inspect siscom-network

# Limpiar todo (⚠️ CUIDADO: elimina TODOS los contenedores detenidos)
docker system prune -a

# Ver espacio en disco
df -h
docker system df
```

---

## 🆘 Solución de Emergencia: Reset Completo

Si nada funciona, haz un reset completo:

```bash
# ⚠️ ADVERTENCIA: Esto elimina TODOS los contenedores y redes

# 1. Detener todos los contenedores
docker stop $(docker ps -aq)

# 2. Eliminar todos los contenedores
docker rm $(docker ps -aq)

# 3. Eliminar la red
docker network rm siscom-network

# 4. Crear la red nuevamente
docker network create siscom-network

# 5. Limpiar el directorio
cd ~
rm -rf siscom-admin-api
mkdir -p siscom-admin-api

# 6. Ejecutar el deployment desde GitHub Actions
```

---

## 📞 Obtener Ayuda

Si ninguna de estas soluciones funciona:

1. **Recopila información de debugging**:

   ```bash
   # Ejecuta este script y guarda la salida
   echo "=== Docker PS ===" && \
   docker ps -a && \
   echo -e "\n=== Logs ===" && \
   docker logs --tail 100 siscom-admin-api && \
   echo -e "\n=== Inspect ===" && \
   docker inspect siscom-admin-api && \
   echo -e "\n=== Networks ===" && \
   docker network ls
   ```

2. **Revisa los logs de GitHub Actions** completos

3. **Contacta al equipo de DevOps** con la información recopilada

---

**Última actualización:** Noviembre 2025
