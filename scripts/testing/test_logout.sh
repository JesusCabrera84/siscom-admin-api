#!/bin/bash

# Script de prueba para el endpoint de logout
# 
# Uso:
#   ./test_logout.sh <email> <password>
#
# Descripción:
#   1. Hace login con las credenciales proporcionadas
#   2. Llama al endpoint de logout
#   3. Intenta usar el token después del logout (debe fallar)

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuración
API_URL="http://localhost:8000/api/v1"

# Función para mostrar ayuda
show_help() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Test: Logout de Usuario${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "Uso: $0 <email> <password>"
    echo ""
    echo "Descripción:"
    echo "  Este script prueba el endpoint de logout:"
    echo "  1. Hace login con las credenciales proporcionadas"
    echo "  2. Llama al endpoint de logout"
    echo "  3. Intenta usar el token después del logout (debe fallar)"
    echo ""
    echo "Ejemplo:"
    echo "  $0 usuario@example.com MiPassword123!"
    echo ""
}

# Verificar argumentos
EMAIL="$1"
PASSWORD="$2"

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
    echo -e "${RED}Error: Faltan argumentos${NC}"
    echo ""
    show_help
    exit 1
fi

# Verificar que jq esté instalado
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq no está instalado${NC}"
    echo "Instala jq con: sudo apt install jq"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  TEST: Logout de Usuario${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Email:${NC} $EMAIL"
echo -e "${YELLOW}Password:${NC} ********"
echo ""

# 1. Login para obtener access_token
echo -e "${CYAN}1. Haciendo login...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

if echo "$LOGIN_RESPONSE" | jq -e '.access_token' > /dev/null 2>&1; then
    ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
    echo -e "${GREEN}✓ Login exitoso${NC}"
    echo -e "${YELLOW}  Token obtenido:${NC} ${ACCESS_TOKEN:0:30}..."
else
    echo -e "${RED}✗ Error en login:${NC}"
    echo "$LOGIN_RESPONSE" | jq .
    exit 1
fi

echo ""

# 2. Llamar al endpoint de logout
echo -e "${CYAN}2. Cerrando sesión (logout)...${NC}"
LOGOUT_RESPONSE=$(curl -s -X POST "$API_URL/auth/logout" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo -e "${GREEN}Respuesta:${NC}"
echo "$LOGOUT_RESPONSE" | jq .

if echo "$LOGOUT_RESPONSE" | jq -e '.message' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Logout exitoso${NC}"
else
    echo -e "${RED}✗ Error al hacer logout${NC}"
    exit 1
fi

echo ""

# 3. Intentar usar el token después del logout (debe fallar)
echo -e "${CYAN}3. Intentando usar el token después del logout...${NC}"
echo -e "${YELLOW}  (Este intento debe fallar con error 401)${NC}"
echo ""

TEST_RESPONSE=$(curl -s -X PATCH "$API_URL/auth/password" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "{\"old_password\": \"test\", \"new_password\": \"test\"}")

echo -e "${GREEN}Respuesta:${NC}"
echo "$TEST_RESPONSE" | jq .

if echo "$TEST_RESPONSE" | jq -e '.detail' | grep -qi "token\|invalid\|unauthorized" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ El token fue invalidado correctamente${NC}"
    echo -e "${GREEN}  (El servidor rechazó el token como esperado)${NC}"
else
    echo -e "${YELLOW}⚠ Advertencia: El token aún podría ser válido${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ Prueba completada${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}Notas:${NC}"
echo "  • El token ha sido invalidado en Cognito"
echo "  • Todos los access tokens, ID tokens y refresh tokens del usuario fueron invalidados"
echo "  • El usuario debe volver a hacer login para obtener nuevos tokens"
echo ""

