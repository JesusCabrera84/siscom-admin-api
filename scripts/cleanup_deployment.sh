#!/bin/bash

# Script de limpieza de emergencia para el servidor
# Úsalo cuando el puerto 8000 esté bloqueado o haya contenedores huérfanos

set -e

echo "🧹 Script de Limpieza de Deployment - SISCOM Admin API"
echo ""

CONTAINER_NAME="siscom-admin-api"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== 1. Deteniendo contenedores de siscom-admin-api ==="
if docker ps -a | grep -q ${CONTAINER_NAME}; then
    echo -e "${YELLOW}Deteniendo contenedor ${CONTAINER_NAME}...${NC}"
    docker stop ${CONTAINER_NAME} 2>/dev/null || true
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
    echo -e "${GREEN}✓ Contenedor ${CONTAINER_NAME} eliminado${NC}"
else
    echo -e "${GREEN}✓ No hay contenedores con nombre ${CONTAINER_NAME}${NC}"
fi
echo ""

echo "=== 2. Verificando puerto 8100 ==="
PORT_IN_USE=$(docker ps -q --filter "publish=8100" 2>/dev/null || true)
if [ ! -z "$PORT_IN_USE" ]; then
    echo -e "${YELLOW}Puerto 8100 en uso por contenedor(es): $PORT_IN_USE${NC}"
    for CONTAINER_ID in $PORT_IN_USE; do
        CONTAINER_INFO=$(docker inspect --format='{{.Name}} - {{.Config.Image}}' $CONTAINER_ID)
        echo "  → Deteniendo: $CONTAINER_INFO"
        docker stop $CONTAINER_ID 2>/dev/null || true
        docker rm $CONTAINER_ID 2>/dev/null || true
    done
    echo -e "${GREEN}✓ Puerto 8100 liberado${NC}"
else
    echo -e "${GREEN}✓ Puerto 8100 está libre${NC}"
fi
echo ""

echo "=== 3. Limpiando con docker-compose ==="
cd ~/siscom-admin-api 2>/dev/null || cd /home/$USER/siscom-admin-api || {
    echo -e "${RED}✗ No se encontró el directorio siscom-admin-api${NC}"
    exit 1
}

if [ -f "docker-compose.prod.yml" ]; then
    echo "Ejecutando docker-compose down..."
    docker-compose -f docker-compose.prod.yml down --remove-orphans 2>/dev/null || true
    echo -e "${GREEN}✓ Docker-compose limpiado${NC}"
else
    echo -e "${YELLOW}⚠ No se encontró docker-compose.prod.yml${NC}"
fi
echo ""

echo "=== 4. Limpiando contenedores detenidos ==="
STOPPED_CONTAINERS=$(docker ps -a -f status=exited -f status=created -q | wc -l)
if [ "$STOPPED_CONTAINERS" -gt 0 ]; then
    echo "Eliminando $STOPPED_CONTAINERS contenedores detenidos..."
    docker container prune -f
    echo -e "${GREEN}✓ Contenedores detenidos eliminados${NC}"
else
    echo -e "${GREEN}✓ No hay contenedores detenidos${NC}"
fi
echo ""

echo "=== 5. Limpiando imágenes sin usar ==="
DANGLING_IMAGES=$(docker images -f "dangling=true" -q | wc -l)
if [ "$DANGLING_IMAGES" -gt 0 ]; then
    echo "Eliminando $DANGLING_IMAGES imágenes sin etiquetar..."
    docker image prune -f
    echo -e "${GREEN}✓ Imágenes sin usar eliminadas${NC}"
else
    echo -e "${GREEN}✓ No hay imágenes sin usar${NC}"
fi
echo ""

echo "=== 6. Estado actual ==="
echo "Contenedores corriendo:"
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "Uso del puerto 8100:"
if docker ps --format "{{.Names}}\t{{.Ports}}" | grep -q 8100; then
    docker ps --format "{{.Names}}\t{{.Ports}}" | grep 8100
else
    echo -e "${GREEN}Puerto 8100 libre${NC}"
fi
echo ""

echo -e "${GREEN}✅ Limpieza completada!${NC}"
echo ""
echo "Puedes ejecutar el deployment nuevamente ejecutando:"
echo "  cd ~/siscom-admin-api"
echo "  docker-compose -f docker-compose.prod.yml up -d"

