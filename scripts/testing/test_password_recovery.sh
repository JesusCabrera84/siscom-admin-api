#!/bin/bash

# Script de prueba para el sistema de recuperación de contraseña
# 
# Uso:
#   ./test_password_recovery.sh <email> [nueva_contraseña]
#
# Ejemplos:
#   ./test_password_recovery.sh usuario@example.com
#   ./test_password_recovery.sh usuario@example.com "NuevaPassword123!"

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
API_URL="http://localhost:8000/api/v1"

# Validar argumentos
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: Debe proporcionar un email${NC}"
    echo "Uso: $0 <email> [nueva_contraseña]"
    exit 1
fi

EMAIL="$1"
NEW_PASSWORD="${2:-NuevaPassword123!}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  TEST: Sistema de Recuperación de Contraseña${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Email:${NC} $EMAIL"
echo -e "${YELLOW}Nueva contraseña:${NC} $NEW_PASSWORD"
echo ""

# ===========================================
# 1. Solicitar recuperación de contraseña
# ===========================================
echo -e "${BLUE}1. Solicitando recuperación de contraseña...${NC}"
FORGOT_RESPONSE=$(curl -s -X POST "$API_URL/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\"}")

echo -e "${GREEN}Respuesta:${NC}"
echo "$FORGOT_RESPONSE" | jq .

# Verificar si la respuesta fue exitosa
if echo "$FORGOT_RESPONSE" | jq -e '.message' > /dev/null; then
    echo -e "${GREEN}✓ Solicitud enviada correctamente${NC}"
else
    echo -e "${RED}✗ Error en la solicitud${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}⚠ IMPORTANTE:${NC}"
echo "Para continuar, necesitas el token de recuperación."
echo "El token se generó y se almacenó en la base de datos."
echo ""
echo -e "${BLUE}Opciones para obtener el token:${NC}"
echo ""
echo "  1. Revisa los logs de la aplicación"
echo "     (busca la línea que dice: [PASSWORD RESET] Token generado para...)"
echo ""
echo "  2. Consulta directamente la base de datos:"
echo "     docker-compose exec db psql -U postgres -d siscom_db -c \\"
echo "       \"SELECT token, email, expires_at, used FROM tokens_confirmacion \\"
echo "       \"WHERE type = 'password_reset' AND email = '$EMAIL' \\"
echo "       \"ORDER BY created_at DESC LIMIT 1;\""
echo ""
echo "  3. Cuando se implemente el servicio de correo, el token llegará al email del usuario"
echo ""
echo -e "${YELLOW}Una vez que tengas el token, continúa con:${NC}"
echo ""
echo -e "  ${GREEN}# 2. Restablecer contraseña${NC}"
echo "  curl -X POST $API_URL/auth/reset-password \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{"
echo "      \"token\": \"TU_TOKEN_AQUI\","
echo "      \"new_password\": \"$NEW_PASSWORD\""
echo "    }'"
echo ""
echo -e "  ${GREEN}# 3. Iniciar sesión con la nueva contraseña${NC}"
echo "  curl -X POST $API_URL/auth/login \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{"
echo "      \"email\": \"$EMAIL\","
echo "      \"password\": \"$NEW_PASSWORD\""
echo "    }'"
echo ""
echo -e "${BLUE}========================================${NC}"

