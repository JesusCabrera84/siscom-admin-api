#!/bin/bash

# Script para verificar que las Variables y Secrets de GitHub estén configurados
# Este script te ayuda a verificar qué falta antes de hacer deployment

echo "🔍 Verificación de Configuración de GitHub Actions"
echo "=================================================="
echo ""
echo "Este script te ayuda a identificar qué variables y secrets"
echo "debes configurar en GitHub para que el deployment funcione."
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Variables que deben configurarse como VARIABLES ===${NC}"
echo "Ruta: Settings → Secrets and variables → Actions → Variables"
echo ""

VARIABLES=(
    "PROJECT_NAME:SISCOM Admin API"
    "DB_HOST:tu-rds-endpoint.amazonaws.com"
    "DB_PORT:5432"
    "DB_USER:siscom_admin"
    "DB_NAME:siscom_admin"
    "COGNITO_REGION:us-east-1"
)

echo "Variables requeridas:"
for var_info in "${VARIABLES[@]}"; do
    IFS=':' read -r var_name var_example <<< "$var_info"
    echo -e "  ${YELLOW}✓${NC} $var_name"
    echo -e "    Ejemplo: ${GREEN}$var_example${NC}"
done

echo ""
echo -e "${RED}⚠️  CRÍTICO: COGNITO_REGION debe estar configurada${NC}"
echo "   Si está vacía, el deployment fallará con:"
echo "   'Invalid endpoint: https://cognito-idp..amazonaws.com'"
echo ""

echo -e "${BLUE}=== Secrets que deben configurarse como SECRETS ===${NC}"
echo "Ruta: Settings → Secrets and variables → Actions → Secrets"
echo ""

SECRETS=(
    "EC2_HOST:IP o hostname del servidor EC2"
    "EC2_USERNAME:Usuario SSH (ubuntu, ec2-user, etc)"
    "EC2_SSH_KEY:Clave privada SSH completa"
    "EC2_SSH_PORT:Puerto SSH (generalmente 22)"
    "DB_PASSWORD:Contraseña de PostgreSQL"
    "COGNITO_USER_POOL_ID:ID del User Pool (us-east-1_XXXXXX)"
    "COGNITO_CLIENT_ID:Client ID de Cognito App"
    "COGNITO_CLIENT_SECRET:Client Secret de Cognito App"
    "DEFAULT_USER_PASSWORD:Password temporal para nuevos usuarios"
)

echo "Secrets requeridos:"
for secret_info in "${SECRETS[@]}"; do
    IFS=':' read -r secret_name secret_desc <<< "$secret_info"
    echo -e "  ${YELLOW}✓${NC} $secret_name"
    echo -e "    ${secret_desc}"
done

echo ""
echo -e "${BLUE}=== Environment ===${NC}"
echo "Debes crear un environment llamado 'production'"
echo "Ruta: Settings → Environments → New environment"
echo "Nombre: production"
echo ""

echo -e "${BLUE}=== Cómo verificar que todo está configurado ===${NC}"
echo ""
echo "1. Ve a tu repositorio en GitHub"
echo "2. Settings → Secrets and variables → Actions"
echo "3. Verifica que tengas:"
echo "   - 6 Variables en la tab 'Variables'"
echo "   - 9 Secrets en la tab 'Secrets'"
echo ""
echo -e "${YELLOW}💡 Nota:${NC} NO necesitas AWS_ACCESS_KEY_ID ni AWS_SECRET_ACCESS_KEY"
echo "   si tu EC2 tiene un IAM Role con permisos para Cognito."
echo ""

echo -e "${GREEN}=== Regiones comunes de AWS ===${NC}"
echo "Para COGNITO_REGION, usa una de estas:"
echo "  • us-east-1      (Virginia del Norte)"
echo "  • us-east-2      (Ohio)"
echo "  • us-west-1      (California del Norte)"
echo "  • us-west-2      (Oregón)"
echo "  • eu-west-1      (Irlanda)"
echo "  • eu-central-1   (Frankfurt)"
echo "  • sa-east-1      (São Paulo)"
echo ""

echo -e "${BLUE}=== Próximos pasos ===${NC}"
echo "1. Configura todas las Variables y Secrets en GitHub"
echo "2. Verifica que COGNITO_REGION no esté vacía"
echo "3. Ejecuta el workflow: GitHub → Actions → Deploy to EC2 → Run workflow"
echo ""

echo -e "${GREEN}✅ Usa esta checklist para verificar tu configuración${NC}"
echo ""
echo "Variables (6):"
echo "  [ ] PROJECT_NAME"
echo "  [ ] DB_HOST"
echo "  [ ] DB_PORT"
echo "  [ ] DB_USER"
echo "  [ ] DB_NAME"
echo "  [ ] COGNITO_REGION ⚠️ CRÍTICO"
echo ""
echo "Secrets (9):"
echo "  [ ] EC2_HOST"
echo "  [ ] EC2_USERNAME"
echo "  [ ] EC2_SSH_KEY"
echo "  [ ] EC2_SSH_PORT"
echo "  [ ] DB_PASSWORD"
echo "  [ ] COGNITO_USER_POOL_ID"
echo "  [ ] COGNITO_CLIENT_ID"
echo "  [ ] COGNITO_CLIENT_SECRET"
echo "  [ ] DEFAULT_USER_PASSWORD"
echo ""
echo -e "${YELLOW}💡${NC} AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY NO son necesarios"
echo "   si usas IAM Role en tu EC2 (recomendado)."
echo ""
echo "Environment:"
echo "  [ ] production (creado)"
echo ""

echo -e "${YELLOW}=================================================${NC}"
echo "Para más información, consulta:"
echo "  📖 .github/README.md"
echo "  📖 docs/guides/github-actions-deployment.md"
echo "  📖 docs/guides/troubleshooting-deployment.md"

