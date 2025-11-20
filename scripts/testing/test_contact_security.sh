#!/bin/bash

# Script para probar las medidas de seguridad del endpoint de contacto
# Ejecutar: bash scripts/testing/test_contact_security.sh

set -e

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

API_URL="${API_URL:-http://localhost:8000}"
ENDPOINT="$API_URL/api/v1/contact/send-message"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Test de Seguridad - Endpoint de Contacto                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Testing endpoint: $ENDPOINT"
echo ""

# Contador de tests
PASSED=0
FAILED=0

# Función para hacer tests
test_request() {
    local test_name="$1"
    local payload="$2"
    local expected_status="$3"
    local description="$4"
    
    echo -e "${YELLOW}Test:${NC} $test_name"
    echo "Descripción: $description"
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$ENDPOINT" \
        -H "Content-Type: application/json" \
        -d "$payload")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} - HTTP $http_code (esperado: $expected_status)"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC} - HTTP $http_code (esperado: $expected_status)"
        echo "Response: $body"
        ((FAILED++))
    fi
    echo ""
}

echo -e "${BLUE}═══ Tests de Validación Básica ═══${NC}"
echo ""

# Test 1: Request válido
test_request \
    "Request válido" \
    '{
        "nombre": "Juan Pérez",
        "correo_electronico": "juan@example.com",
        "telefono": "+52 123 456 7890",
        "mensaje": "Este es un mensaje de prueba válido"
    }' \
    200 \
    "Request con todos los campos válidos"

# Test 2: Sin email ni teléfono
test_request \
    "Sin email ni teléfono" \
    '{
        "nombre": "Juan Pérez",
        "mensaje": "Mensaje sin contacto"
    }' \
    422 \
    "Debe fallar porque no hay email ni teléfono"

# Test 3: Nombre vacío
test_request \
    "Nombre vacío" \
    '{
        "nombre": "",
        "correo_electronico": "test@test.com",
        "mensaje": "Test"
    }' \
    422 \
    "Debe fallar porque el nombre está vacío"

echo -e "${BLUE}═══ Tests de Sanitización XSS ═══${NC}"
echo ""

# Test 4: XSS en nombre
test_request \
    "XSS en nombre" \
    '{
        "nombre": "<script>alert(\"XSS\")</script>",
        "correo_electronico": "test@test.com",
        "mensaje": "Test"
    }' \
    200 \
    "Debe aceptar pero sanitizar el HTML en nombre"

# Test 5: XSS en mensaje
test_request \
    "XSS en mensaje" \
    '{
        "nombre": "Test",
        "correo_electronico": "test@test.com",
        "mensaje": "<img src=x onerror=\"alert(1)\">"
    }' \
    200 \
    "Debe aceptar pero sanitizar el HTML en mensaje"

# Test 6: Inyección de HTML compleja
test_request \
    "Inyección HTML compleja" \
    '{
        "nombre": "Test",
        "correo_electronico": "test@test.com",
        "mensaje": "<iframe src=\"evil.com\"></iframe><script>alert(\"XSS\")</script>"
    }' \
    200 \
    "Debe aceptar pero sanitizar todo el HTML"

echo -e "${BLUE}═══ Tests de Límites de Longitud ═══${NC}"
echo ""

# Test 7: Nombre muy largo (>200 caracteres)
test_request \
    "Nombre muy largo" \
    "{
        \"nombre\": \"$(printf 'A%.0s' {1..201})\",
        \"correo_electronico\": \"test@test.com\",
        \"mensaje\": \"Test\"
    }" \
    422 \
    "Debe fallar porque el nombre excede 200 caracteres"

# Test 8: Mensaje muy largo (>5000 caracteres)
test_request \
    "Mensaje muy largo" \
    "{
        \"nombre\": \"Test\",
        \"correo_electronico\": \"test@test.com\",
        \"mensaje\": \"$(printf 'A%.0s' {1..5001})\"
    }" \
    422 \
    "Debe fallar porque el mensaje excede 5000 caracteres"

echo -e "${BLUE}═══ Tests de Validación de Teléfono ═══${NC}"
echo ""

# Test 9: Teléfono válido con formato internacional
test_request \
    "Teléfono válido" \
    '{
        "nombre": "Test",
        "telefono": "+52 (123) 456-7890",
        "mensaje": "Test"
    }' \
    200 \
    "Debe aceptar teléfono con formato válido"

# Test 10: Teléfono con caracteres inválidos
test_request \
    "Teléfono con SQL injection" \
    '{
        "nombre": "Test",
        "telefono": "123; DROP TABLE users;",
        "mensaje": "Test"
    }' \
    422 \
    "Debe fallar porque el teléfono tiene caracteres inválidos"

# Test 11: Teléfono demasiado corto
test_request \
    "Teléfono muy corto" \
    '{
        "nombre": "Test",
        "telefono": "123",
        "mensaje": "Test"
    }' \
    422 \
    "Debe fallar porque el teléfono es muy corto"

# Test 12: Teléfono demasiado largo
test_request \
    "Teléfono muy largo" \
    '{
        "nombre": "Test",
        "telefono": "123456789012345678901",
        "mensaje": "Test"
    }' \
    422 \
    "Debe fallar porque el teléfono es muy largo"

echo -e "${BLUE}═══ Tests de Email ═══${NC}"
echo ""

# Test 13: Email inválido
test_request \
    "Email inválido" \
    '{
        "nombre": "Test",
        "correo_electronico": "not-an-email",
        "mensaje": "Test"
    }' \
    422 \
    "Debe fallar porque el email no es válido"

# Test 14: Solo email sin teléfono
test_request \
    "Solo email" \
    '{
        "nombre": "Test",
        "correo_electronico": "test@test.com",
        "mensaje": "Test"
    }' \
    200 \
    "Debe aceptar con solo email"

# Test 15: Solo teléfono sin email
test_request \
    "Solo teléfono" \
    '{
        "nombre": "Test",
        "telefono": "+52 123 456 7890",
        "mensaje": "Test"
    }' \
    200 \
    "Debe aceptar con solo teléfono"

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                      Resultados Finales                         ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Tests Pasados:${NC} $PASSED"
echo -e "${RED}Tests Fallados:${NC} $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ Todos los tests pasaron exitosamente!${NC}"
    exit 0
else
    echo -e "${RED}✗ Algunos tests fallaron. Revisa la salida arriba.${NC}"
    exit 1
fi

