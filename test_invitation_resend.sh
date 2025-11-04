#!/bin/bash

# Script de prueba para el reenvío de invitaciones
# 
# Uso:
#   ./test_invitation_resend.sh <email_maestro> <password_maestro> <email_invitado>
#
# Ejemplo:
#   ./test_invitation_resend.sh maestro@example.com Password123! invitado@ejemplo.com

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

# Validar argumentos
if [ $# -lt 3 ]; then
    echo -e "${RED}Error: Faltan argumentos${NC}"
    echo "Uso: $0 <email_maestro> <password_maestro> <email_invitado>"
    echo ""
    echo "Ejemplo:"
    echo "  $0 maestro@example.com Password123! invitado@ejemplo.com"
    exit 1
fi

EMAIL_MAESTRO="$1"
PASSWORD_MAESTRO="$2"
EMAIL_INVITADO="$3"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  TEST: Flujo de Reenvío de Invitación${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Usuario Maestro:${NC} $EMAIL_MAESTRO"
echo -e "${YELLOW}Email Invitado:${NC} $EMAIL_INVITADO"
echo ""

# ===========================================
# 1. Login como usuario maestro
# ===========================================
echo -e "${CYAN}1. Autenticando usuario maestro...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL_MAESTRO\", \"password\": \"$PASSWORD_MAESTRO\"}")

if echo "$LOGIN_RESPONSE" | jq -e '.access_token' > /dev/null 2>&1; then
    ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
    echo -e "${GREEN}✓ Login exitoso${NC}"
else
    echo -e "${RED}✗ Error en login:${NC}"
    echo "$LOGIN_RESPONSE" | jq .
    exit 1
fi

echo ""

# ===========================================
# 2. Verificar si existe invitación pendiente
# ===========================================
echo -e "${CYAN}2. Verificando invitaciones pendientes para $EMAIL_INVITADO...${NC}"

# Verificar en BD
if command -v docker-compose &> /dev/null; then
    INVITATIONS_COUNT=$(docker-compose exec -T db psql -U postgres -d siscom_db -t -c \
      "SELECT COUNT(*) FROM tokens_confirmacion WHERE type='invitation' AND email='$EMAIL_INVITADO' AND used=false;" 2>/dev/null | tr -d ' ' | tr -d '\n' | tr -d '\r')
    
    if [ -n "$INVITATIONS_COUNT" ] && [ "$INVITATIONS_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ Encontradas $INVITATIONS_COUNT invitación(es) pendiente(s)${NC}"
        HAS_INVITATION="yes"
    else
        echo -e "${YELLOW}⚠ No hay invitaciones pendientes para este email${NC}"
        HAS_INVITATION="no"
    fi
else
    echo -e "${YELLOW}⚠ docker-compose no disponible, saltando verificación en BD${NC}"
    HAS_INVITATION="unknown"
fi

echo ""

# ===========================================
# 3. Intentar invitar (si no hay invitación)
# ===========================================
if [ "$HAS_INVITATION" = "no" ]; then
    echo -e "${CYAN}3. Enviando invitación inicial...${NC}"
    
    INVITE_RESPONSE=$(curl -s -X POST "$API_URL/users/invite" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -d "{\"email\": \"$EMAIL_INVITADO\", \"full_name\": \"Usuario de Prueba\"}")
    
    if echo "$INVITE_RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Invitación inicial enviada${NC}"
        echo "$INVITE_RESPONSE" | jq .
    else
        echo -e "${YELLOW}⚠ No se pudo enviar invitación inicial (puede que ya exista):${NC}"
        echo "$INVITE_RESPONSE" | jq .
    fi
    
    echo ""
fi

# ===========================================
# 4. Reenviar invitación
# ===========================================
echo -e "${CYAN}4. Reenviando invitación...${NC}"

RESEND_RESPONSE=$(curl -s -X POST "$API_URL/users/resend-invitation" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "{\"email\": \"$EMAIL_INVITADO\"}")

echo -e "${GREEN}Respuesta:${NC}"
echo "$RESEND_RESPONSE" | jq .

if echo "$RESEND_RESPONSE" | jq -e '.message' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Invitación reenviada exitosamente${NC}"
    EXPIRES_AT=$(echo "$RESEND_RESPONSE" | jq -r '.expires_at')
    echo -e "${YELLOW}Expira:${NC} $EXPIRES_AT"
else
    echo -e "${RED}✗ Error al reenviar invitación${NC}"
    exit 1
fi

echo ""

# ===========================================
# 5. Obtener token de la base de datos
# ===========================================
echo -e "${CYAN}5. Obteniendo token de invitación de la base de datos...${NC}"

if command -v docker-compose &> /dev/null; then
    TOKEN=$(docker-compose exec -T db psql -U postgres -d siscom_db -t -c \
      "SELECT token FROM tokens_confirmacion WHERE type='invitation' AND email='$EMAIL_INVITADO' AND used=false ORDER BY created_at DESC LIMIT 1;" 2>/dev/null | tr -d ' ' | tr -d '\n' | tr -d '\r')
    
    if [ -n "$TOKEN" ]; then
        echo -e "${GREEN}✓ Token obtenido: ${TOKEN:0:30}...${NC}"
    else
        echo -e "${RED}✗ No se pudo obtener el token de la BD${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ docker-compose no disponible${NC}"
    echo ""
    echo -e "${CYAN}Obtén el token manualmente:${NC}"
    echo "  docker-compose exec db psql -U postgres -d siscom_db -c \\"
    echo "    \"SELECT token, expires_at FROM tokens_confirmacion \\"
    echo "    \"WHERE type='invitation' AND email='$EMAIL_INVITADO' AND used=false \\"
    echo "    \"ORDER BY created_at DESC LIMIT 1;\""
    exit 0
fi

echo ""

# ===========================================
# 6. Información para aceptar invitación
# ===========================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Siguiente Paso: Aceptar Invitación${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Para que el invitado acepte la invitación:${NC}"
echo ""
echo -e "${CYAN}curl -X POST $API_URL/users/accept-invitation \\${NC}"
echo -e "  ${CYAN}-H \"Content-Type: application/json\" \\${NC}"
echo -e "  ${CYAN}-d '{${NC}"
echo -e "    ${CYAN}\"token\": \"$TOKEN\",${NC}"
echo -e "    ${CYAN}\"password\": \"NuevaPassword123!\"${NC}"
echo -e "  ${CYAN}}'${NC}"
echo ""
echo -e "${GREEN}Luego el usuario puede hacer login con:${NC}"
echo -e "  ${GREEN}Email: $EMAIL_INVITADO${NC}"
echo -e "  ${GREEN}Password: NuevaPassword123!${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ Test completado exitosamente${NC}"
echo -e "${GREEN}========================================${NC}"

