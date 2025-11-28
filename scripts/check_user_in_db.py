"""
Script para verificar si un usuario existe en la base de datos y su cognito_sub.
Uso: python scripts/check_user_in_db.py <email>
"""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal
from app.models.user import User


def check_user(email: str):
    """Verifica si un usuario existe en la base de datos."""

    print("=" * 80)
    print("🔍 VERIFICANDO USUARIO EN BASE DE DATOS")
    print("=" * 80)
    print(f"Email: {email}")
    print("-" * 80)

    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == email).first()

        if user:
            print("\n✅ Usuario encontrado en la base de datos")
            print(f"   - ID: {user.id}")
            print(f"   - Email: {user.email}")
            print(f"   - Full Name: {user.full_name}")
            print(f"   - Client ID: {user.client_id}")
            print(f"   - Cognito Sub: {user.cognito_sub}")
            print(f"   - Email Verified: {user.email_verified}")
            print(f"   - Is Master: {user.is_master}")
            print(f"   - Created At: {user.created_at}")

            if not user.cognito_sub:
                print("\n⚠️  PROBLEMA: El usuario NO tiene cognito_sub asignado")
                print("   Esto causará errores al intentar autenticarse")
                print("   Solución: El usuario necesita ser creado con cognito_sub")

            if not user.email_verified:
                print("\n⚠️  ADVERTENCIA: El email no está verificado")
                print("   El usuario no podrá hacer login")
        else:
            print("\n❌ Usuario NO encontrado en la base de datos")
            print("\n💡 Posibles causas:")
            print("   1. El usuario solo existe en Cognito pero no en la base de datos")
            print("   2. El email es diferente")
            print("\n💡 Solución:")
            print("   - Crear el usuario usando el endpoint POST /api/v1/users/")
            print("   - O verificar que el email sea correcto")

    finally:
        db.close()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/check_user_in_db.py <email>")
        print("Ejemplo: python scripts/check_user_in_db.py test4@example.com")
        sys.exit(1)

    email = sys.argv[1]
    check_user(email)
