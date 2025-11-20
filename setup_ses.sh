#!/bin/bash

# Script para configurar AWS SES para el endpoint de contacto
# Ejecutar: bash setup_ses.sh

set -e

echo "🔧 Configurando AWS SES para Siscom Admin API"
echo "================================================"
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables
REGION="us-east-1"
FROM_EMAIL="noreply@geminislabs.com"
CONTACT_EMAIL="contacto@geminislabs.com"
IAM_USER="github-actions"

echo "📧 Emails a configurar:"
echo "  - Remitente (FROM): $FROM_EMAIL"
echo "  - Contacto (TO): $CONTACT_EMAIL"
echo ""

# Paso 1: Verificar emails en SES
echo "📝 Paso 1: Verificando emails en AWS SES..."
echo ""

echo "Verificando $FROM_EMAIL..."
if aws ses verify-email-identity --email-address "$FROM_EMAIL" --region "$REGION" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Solicitud de verificación enviada a $FROM_EMAIL"
else
    echo -e "${RED}✗${NC} Error al verificar $FROM_EMAIL"
fi

echo "Verificando $CONTACT_EMAIL..."
if aws ses verify-email-identity --email-address "$CONTACT_EMAIL" --region "$REGION" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Solicitud de verificación enviada a $CONTACT_EMAIL"
else
    echo -e "${RED}✗${NC} Error al verificar $CONTACT_EMAIL"
fi

echo ""
echo -e "${YELLOW}⚠️  IMPORTANTE:${NC} Revisa las bandejas de entrada de ambos emails"
echo "   y haz clic en los enlaces de verificación que AWS te envió."
echo ""

# Paso 2: Agregar permisos al usuario IAM
echo "🔐 Paso 2: Agregando permisos de SES al usuario IAM..."
echo ""

# Crear archivo de política temporal
cat > /tmp/ses-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail",
        "ses:VerifyEmailIdentity",
        "ses:GetIdentityVerificationAttributes"
      ],
      "Resource": "*"
    }
  ]
}
EOF

echo "Aplicando política al usuario $IAM_USER..."
if aws iam put-user-policy \
    --user-name "$IAM_USER" \
    --policy-name "SESSendEmailPolicy" \
    --policy-document file:///tmp/ses-policy.json 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Permisos agregados correctamente"
else
    echo -e "${RED}✗${NC} Error al agregar permisos (puede que el usuario no exista o no tengas permisos)"
    echo "   Si usas IAM Role en EC2, este error es normal."
fi

# Limpiar archivo temporal
rm -f /tmp/ses-policy.json

echo ""

# Paso 3: Verificar estado actual
echo "📊 Paso 3: Verificando estado de los emails..."
echo ""

# Esperar un momento para que AWS procese
sleep 2

# Verificar estado de verificación
if aws ses get-identity-verification-attributes \
    --identities "$FROM_EMAIL" "$CONTACT_EMAIL" \
    --region "$REGION" > /tmp/ses-status.json 2>/dev/null; then
    
    echo "Estado de verificación:"
    cat /tmp/ses-status.json | grep -A 2 "VerificationStatus" || echo "  Pendiente de verificación"
    rm -f /tmp/ses-status.json
else
    echo -e "${YELLOW}⚠${NC} No se pudo verificar el estado. Ejecuta manualmente:"
    echo "   aws ses list-verified-email-addresses --region $REGION"
fi

echo ""

# Paso 4: Prueba opcional
echo "🧪 Paso 4: Prueba de envío (opcional)"
echo ""
read -p "¿Deseas hacer una prueba de envío de email? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo "Enviando email de prueba..."
    if aws ses send-email \
        --from "$FROM_EMAIL" \
        --destination "ToAddresses=$CONTACT_EMAIL" \
        --message "Subject={Data='Test - Siscom Admin API'},Body={Text={Data='Este es un email de prueba desde Siscom Admin API.'}}" \
        --region "$REGION" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Email de prueba enviado correctamente"
        echo "   Revisa la bandeja de entrada de $CONTACT_EMAIL"
    else
        echo -e "${RED}✗${NC} Error al enviar email de prueba"
        echo "   Esto es normal si los emails aún no están verificados."
        echo "   Verifica los emails y vuelve a intentar."
    fi
fi

echo ""
echo "================================================"
echo -e "${GREEN}✅ Configuración completada${NC}"
echo ""
echo "📋 Próximos pasos:"
echo "   1. Verifica los emails en las bandejas de entrada"
echo "   2. Haz clic en los enlaces de verificación"
echo "   3. Reinicia el servidor: uvicorn app.main:app --reload"
echo "   4. Prueba el endpoint de contacto"
echo ""
echo "📖 Para más información, consulta:"
echo "   - CONFIGURAR_AWS_SES.md"
echo "   - docs/api/contact.md"
echo ""

