"""
Script para diagnosticar el estado de un usuario en Cognito.
Uso: python scripts/diagnose_cognito_user.py <email>
"""

import base64
import hashlib
import hmac
import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


def get_secret_hash(username: str) -> str:
    """Genera el SECRET_HASH para Cognito."""
    message = bytes(username + settings.COGNITO_CLIENT_ID, "utf-8")
    secret = bytes(settings.COGNITO_CLIENT_SECRET, "utf-8")
    dig = hmac.new(secret, msg=message, digestmod=hashlib.sha256).digest()
    return base64.b64encode(dig).decode()


def diagnose_user(email: str):
    """Diagnostica el estado de un usuario en Cognito."""

    print("=" * 80)
    print("🔍 DIAGNÓSTICO DE USUARIO EN COGNITO")
    print("=" * 80)
    print(f"Email: {email}")
    print(f"User Pool ID: {settings.COGNITO_USER_POOL_ID}")
    print(f"Client ID: {settings.COGNITO_CLIENT_ID}")
    print(f"Region: {settings.COGNITO_REGION}")
    print("-" * 80)

    cognito = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)

    # 1. Verificar si el usuario existe y su estado
    try:
        user_info = cognito.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID, Username=email
        )

        print("\n✅ Usuario encontrado en Cognito")
        print(f"   - Username: {user_info['Username']}")
        print(f"   - User Status: {user_info['UserStatus']}")
        print(f"   - Enabled: {user_info.get('Enabled', True)}")
        print(f"   - Created: {user_info['UserCreateDate']}")
        print(f"   - Modified: {user_info['UserLastModifiedDate']}")

        print("\n📋 Atributos del usuario:")
        for attr in user_info.get("UserAttributes", []):
            if attr["Name"] == "email_verified":
                verified = attr["Value"]
                if verified == "true":
                    print(f"   ✅ {attr['Name']}: {attr['Value']}")
                else:
                    print(f"   ❌ {attr['Name']}: {attr['Value']}")
            else:
                print(f"   - {attr['Name']}: {attr['Value']}")

        # Diagnóstico del estado
        status = user_info["UserStatus"]
        print(f"\n🔍 Análisis del estado '{status}':")

        if status == "CONFIRMED":
            print("   ✅ El usuario está confirmado y debería poder hacer login.")
        elif status == "UNCONFIRMED":
            print("   ⚠️  El usuario NO está confirmado. Necesita ser confirmado.")
            print("   💡 Solución: Ejecutar admin_confirm_sign_up")
        elif status == "FORCE_CHANGE_PASSWORD":
            print("   ⚠️  El usuario debe cambiar su contraseña.")
            print("   💡 Solución: Usar admin_set_user_password con Permanent=True")
        elif status == "RESET_REQUIRED":
            print("   ⚠️  El usuario requiere resetear su contraseña.")
        else:
            print(f"   ⚠️  Estado desconocido: {status}")

    except ClientError as e:
        if e.response["Error"]["Code"] == "UserNotFoundException":
            print("\n❌ Usuario NO encontrado en Cognito")
            print("   💡 El usuario necesita ser creado en Cognito primero")
        else:
            print(f"\n❌ Error al consultar usuario: {e}")
            print(f"   Code: {e.response['Error']['Code']}")
            print(f"   Message: {e.response['Error']['Message']}")
        return

    # 2. Verificar que el usuario tiene email_verified
    email_verified_attr = next(
        (
            attr
            for attr in user_info.get("UserAttributes", [])
            if attr["Name"] == "email_verified"
        ),
        None,
    )

    if email_verified_attr and email_verified_attr["Value"] == "false":
        print("\n⚠️  ATENCIÓN: email_verified = false en Cognito")
        print("   Esto puede causar problemas con algunos flujos de autenticación")

    print("\n" + "=" * 80)
    print("💡 RECOMENDACIONES:")
    print("=" * 80)

    if status != "CONFIRMED":
        print("\n1. Confirmar el usuario en Cognito:")
        print("   aws cognito-idp admin-confirm-sign-up \\")
        print(f"       --user-pool-id {settings.COGNITO_USER_POOL_ID} \\")
        print(f"       --username {email}")

    print("\n2. Establecer una contraseña permanente:")
    print("   aws cognito-idp admin-set-user-password \\")
    print(f"       --user-pool-id {settings.COGNITO_USER_POOL_ID} \\")
    print(f"       --username {email} \\")
    print("       --password 'TuNuevaContraseña' \\")
    print("       --permanent")

    if email_verified_attr and email_verified_attr["Value"] == "false":
        print("\n3. Marcar el email como verificado:")
        print("   aws cognito-idp admin-update-user-attributes \\")
        print(f"       --user-pool-id {settings.COGNITO_USER_POOL_ID} \\")
        print(f"       --username {email} \\")
        print("       --user-attributes Name=email_verified,Value=true")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/diagnose_cognito_user.py <email>")
        print("Ejemplo: python scripts/diagnose_cognito_user.py test4@example.com")
        sys.exit(1)

    email = sys.argv[1]
    diagnose_user(email)
