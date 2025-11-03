#!/bin/bash

# Script para probar la creación de usuarios y que queden en estado CONFIRMED

echo "=================================================="
echo "PRUEBA: Creación de usuario sin FORCE_CHANGE_PASSWORD"
echo "=================================================="

# Variables de prueba
TEST_EMAIL="testuser_$(date +%s)@example.com"
TEST_PASSWORD="TestPass123!"
TEST_NAME="Usuario de Prueba"

echo ""
echo "1. Creando usuario de prueba..."
echo "   Email: $TEST_EMAIL"
echo "   Password: $TEST_PASSWORD"
echo ""

# Crear usuario (necesitarás ajustar el client_id a uno válido)
RESPONSE=$(curl -s -w "\n%{http_code}" --location 'http://localhost:8000/api/v1/users/' \
--header 'Content-Type: application/json' \
--data-raw "{
  \"email\": \"$TEST_EMAIL\",
  \"name\": \"$TEST_NAME\",
  \"password\": \"$TEST_PASSWORD\",
  \"is_master\": true,
  \"client_id\": \"00000000-0000-0000-0000-000000000000\"
}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

echo "Status Code: $HTTP_CODE"
echo "Response: $BODY"

if [ "$HTTP_CODE" -eq 201 ]; then
    echo ""
    echo "✅ Usuario creado exitosamente"
    echo ""
    echo "2. Esperando 2 segundos antes de probar el login..."
    sleep 2
    
    echo ""
    echo "3. Intentando login con las credenciales..."
    
    LOGIN_RESPONSE=$(curl -s -w "\n%{http_code}" --location 'http://localhost:8000/api/v1/auth/login' \
    --header 'Content-Type: application/json' \
    --data-raw "{
      \"email\": \"$TEST_EMAIL\",
      \"password\": \"$TEST_PASSWORD\"
    }")
    
    LOGIN_HTTP_CODE=$(echo "$LOGIN_RESPONSE" | tail -n1)
    LOGIN_BODY=$(echo "$LOGIN_RESPONSE" | head -n-1)
    
    echo "Status Code: $LOGIN_HTTP_CODE"
    echo "Response: $LOGIN_BODY"
    
    if [ "$LOGIN_HTTP_CODE" -eq 200 ]; then
        echo ""
        echo "✅ ¡LOGIN EXITOSO!"
        echo "=================================================="
        echo "✅ El usuario se creó en estado CONFIRMED"
        echo "✅ No hubo problemas con FORCE_CHANGE_PASSWORD"
        echo "=================================================="
    else
        echo ""
        echo "❌ Error en el login"
        echo "=================================================="
        echo "⚠️  Revisar el estado del usuario en Cognito"
        echo "=================================================="
    fi
else
    echo ""
    echo "❌ Error al crear usuario"
fi

echo ""

