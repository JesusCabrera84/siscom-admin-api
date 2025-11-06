#!/bin/bash

# Script para verificar que la configuración de GitHub Actions esté completa
# antes de hacer deployment

set -e

echo "🔍 Verificando configuración para GitHub Actions..."
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Contador de errores
ERRORS=0
WARNINGS=0

# Función para verificar si un archivo existe
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} Archivo encontrado: $1"
    else
        echo -e "${RED}✗${NC} Archivo faltante: $1"
        ((ERRORS++))
    fi
}

# Función para verificar contenido de archivo
check_file_content() {
    if grep -q "$2" "$1" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $3"
    else
        echo -e "${YELLOW}⚠${NC} $3"
        ((WARNINGS++))
    fi
}

echo "=== 1. Verificando archivos de GitHub Actions ==="
check_file ".github/workflows/deploy.yml"
check_file ".github/workflows/ci.yml"
check_file "docker-compose.prod.yml"
check_file "Dockerfile"
check_file "requirements.txt"
echo ""

echo "=== 2. Verificando Dockerfile ==="
check_file_content "Dockerfile" "python:3.11" "Usa Python 3.11"
check_file_content "Dockerfile" "EXPOSE 8000" "Expone puerto 8000"
check_file_content "Dockerfile" "uvicorn" "Comando uvicorn configurado"
echo ""

echo "=== 3. Verificando health endpoint ==="
if grep -q "/health" app/main.py; then
    echo -e "${GREEN}✓${NC} Endpoint /health encontrado en app/main.py"
else
    echo -e "${RED}✗${NC} Endpoint /health NO encontrado en app/main.py"
    echo "   Agrega este código a app/main.py:"
    echo ""
    echo "   @app.get(\"/health\")"
    echo "   def health_check():"
    echo "       return {\"status\": \"healthy\"}"
    echo ""
    ((ERRORS++))
fi
echo ""

echo "=== 4. Verificando dependencias para linting ==="
if grep -q "ruff" requirements.txt; then
    echo -e "${GREEN}✓${NC} ruff encontrado en requirements.txt"
else
    echo -e "${YELLOW}⚠${NC} ruff NO encontrado en requirements.txt"
    ((WARNINGS++))
fi

if grep -q "black" requirements.txt; then
    echo -e "${GREEN}✓${NC} black encontrado en requirements.txt"
else
    echo -e "${YELLOW}⚠${NC} black NO encontrado en requirements.txt"
    ((WARNINGS++))
fi
echo ""

echo "=== 5. Verificando configuración de base de datos ==="
if grep -q "DB_HOST\|DB_PORT\|DB_USER\|DB_PASSWORD\|DB_NAME" app/core/config.py; then
    echo -e "${GREEN}✓${NC} Variables de BD configuradas en config.py"
else
    echo -e "${RED}✗${NC} Variables de BD NO encontradas en config.py"
    ((ERRORS++))
fi
echo ""

echo "=== 6. Verificando configuración de AWS Cognito ==="
if grep -q "COGNITO" app/core/config.py; then
    echo -e "${GREEN}✓${NC} Variables de Cognito configuradas"
else
    echo -e "${YELLOW}⚠${NC} Variables de Cognito NO encontradas"
    ((WARNINGS++))
fi
echo ""

echo "=== 7. Lista de Secrets que debes configurar en GitHub ==="
echo ""
echo "Ve a: Settings → Secrets and variables → Actions → New repository secret"
echo ""
echo "Secrets requeridos:"
echo "  - EC2_HOST"
echo "  - EC2_USERNAME"
echo "  - EC2_SSH_KEY"
echo "  - EC2_SSH_PORT"
echo "  - DB_PASSWORD"
echo "  - AWS_ACCESS_KEY_ID"
echo "  - AWS_SECRET_ACCESS_KEY"
echo "  - COGNITO_USER_POOL_ID"
echo "  - COGNITO_CLIENT_ID"
echo "  - COGNITO_CLIENT_SECRET"
echo "  - DEFAULT_USER_PASSWORD"
echo ""

echo "=== 8. Lista de Variables que debes configurar en GitHub ==="
echo ""
echo "Ve a: Settings → Secrets and variables → Actions → Variables"
echo ""
echo "Variables requeridas:"
echo "  - PROJECT_NAME"
echo "  - DB_HOST"
echo "  - DB_PORT"
echo "  - DB_USER"
echo "  - DB_NAME"
echo "  - COGNITO_REGION"
echo ""

echo "=== 9. Configuración del servidor EC2 ==="
echo ""
echo "Comandos a ejecutar en tu servidor EC2:"
echo ""
echo "# Instalar Docker"
echo "curl -fsSL https://get.docker.com -o get-docker.sh"
echo "sudo sh get-docker.sh"
echo "sudo usermod -aG docker \$USER"
echo ""
echo "# Instalar Docker Compose"
echo "sudo curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose"
echo "sudo chmod +x /usr/local/bin/docker-compose"
echo ""
echo "# Crear red Docker"
echo "docker network create siscom-network"
echo ""
echo "# Crear directorio de trabajo"
echo "mkdir -p ~/siscom-admin-api"
echo ""

echo "================================"
echo ""
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ Todo listo para deployment!${NC}"
    echo ""
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Hay $WARNINGS advertencias, pero puedes continuar${NC}"
    echo ""
else
    echo -e "${RED}❌ Hay $ERRORS errores que deben corregirse antes del deployment${NC}"
    echo ""
    exit 1
fi

echo "Próximos pasos:"
echo "1. Configura todos los Secrets y Variables en GitHub"
echo "2. Prepara tu servidor EC2 con Docker"
echo "3. Haz push a la rama master para activar el deployment"
echo "   O ejecuta el workflow manualmente desde GitHub Actions"
echo ""

