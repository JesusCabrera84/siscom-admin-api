"""
Script para corregir el cognito_sub de un usuario en la base de datos.
Uso: python scripts/fix_user_cognito_sub.py <email>
"""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User


def fix_cognito_sub(email: str):
    """Corrige el cognito_sub de un usuario en la base de datos."""

    print("=" * 80)
    print("🔧 CORRIGIENDO COGNITO_SUB DEL USUARIO")
    print("=" * 80)
    print(f"Email: {email}")
    print("-" * 80)

    # 1. Buscar usuario en la base de datos
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == email).first()

        if not user:
            print("\n❌ Usuario NO encontrado en la base de datos")
            return

        print("\n✅ Usuario encontrado en BD")
        print(f"   - ID: {user.id}")
        print(f"   - Cognito Sub actual: {user.cognito_sub}")

        # 2. Obtener el cognito_sub correcto desde Cognito
        cognito = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)

        try:
            user_info = cognito.admin_get_user(
                UserPoolId=settings.COGNITO_USER_POOL_ID, Username=email
            )

            # Buscar el atributo 'sub'
            cognito_sub = next(
                (
                    attr["Value"]
                    for attr in user_info.get("UserAttributes", [])
                    if attr["Name"] == "sub"
                ),
                None,
            )

            if not cognito_sub:
                print("\n❌ No se pudo obtener el cognito_sub desde Cognito")
                return

            print(f"\n✅ Cognito Sub en Cognito: {cognito_sub}")

            # 3. Verificar si necesita actualización
            if user.cognito_sub == cognito_sub:
                print(
                    "\n✅ El cognito_sub ya es correcto. No se necesita actualización."
                )
                return

            # 4. Actualizar el cognito_sub en la base de datos
            print("\n⚙️  Actualizando cognito_sub en la base de datos...")
            print(f"   Anterior: {user.cognito_sub}")
            print(f"   Nuevo:    {cognito_sub}")

            user.cognito_sub = cognito_sub
            db.commit()

            print("\n✅ ¡Cognito_sub actualizado correctamente!")

            # 5. Verificar la actualización
            db.refresh(user)
            print("\n✓ Verificación:")
            print(f"   - Cognito Sub en BD: {user.cognito_sub}")

        except ClientError as e:
            if e.response["Error"]["Code"] == "UserNotFoundException":
                print("\n❌ Usuario NO encontrado en Cognito")
            else:
                print(f"\n❌ Error al consultar Cognito: {e}")
            return

    finally:
        db.close()

    print("\n" + "=" * 80)
    print("✅ ¡PROCESO COMPLETADO!")
    print("=" * 80)
    print("\nAhora puedes usar el token de acceso con este usuario.")
    print("\nPrueba el endpoint de invitación nuevamente:")
    print("curl --location 'http://localhost:8000/api/v1/users/invite' \\")
    print("--header 'Authorization: Bearer <tu_token>' \\")
    print("--header 'Content-Type: application/json' \\")
    print("--data-raw '{")
    print('  "email": "invitado@ejemplo.com",')
    print('  "full_name": "Juan Pérez"')
    print("}'")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/fix_user_cognito_sub.py <email>")
        print("Ejemplo: python scripts/fix_user_cognito_sub.py test4@example.com")
        sys.exit(1)

    email = sys.argv[1]
    fix_cognito_sub(email)
