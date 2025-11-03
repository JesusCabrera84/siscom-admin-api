"""
Script para solucionar problemas comunes de usuarios en Cognito.
Uso: python scripts/fix_cognito_user.py <email> <password>
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import boto3
from botocore.exceptions import ClientError
from app.core.config import settings


def fix_user(email: str, password: str):
    """Soluciona problemas comunes de un usuario en Cognito."""
    
    print("="*80)
    print(f"🔧 SOLUCIONANDO PROBLEMAS DEL USUARIO EN COGNITO")
    print("="*80)
    print(f"Email: {email}")
    print(f"User Pool ID: {settings.COGNITO_USER_POOL_ID}")
    print("-"*80)
    
    cognito = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)
    
    # 1. Verificar si el usuario existe
    try:
        user_info = cognito.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=email
        )
        print(f"\n✅ Usuario encontrado: {user_info['Username']}")
        print(f"   Estado actual: {user_info['UserStatus']}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "UserNotFoundException":
            print(f"\n❌ Usuario NO encontrado en Cognito")
            return
        else:
            print(f"\n❌ Error: {e}")
            return
    
    # 2. Confirmar el usuario si no está confirmado
    status = user_info['UserStatus']
    if status in ['UNCONFIRMED', 'FORCE_CHANGE_PASSWORD']:
        print(f"\n⚙️  Confirmando usuario...")
        try:
            cognito.admin_confirm_sign_up(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=email
            )
            print("   ✅ Usuario confirmado")
        except ClientError as e:
            if e.response["Error"]["Code"] == "NotAuthorizedException":
                print("   ℹ️  Usuario ya está confirmado")
            else:
                print(f"   ⚠️  Error al confirmar: {e}")
    
    # 3. Establecer contraseña permanente
    print(f"\n⚙️  Estableciendo contraseña permanente...")
    try:
        cognito.admin_set_user_password(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=email,
            Password=password,
            Permanent=True
        )
        print("   ✅ Contraseña establecida")
    except ClientError as e:
        print(f"   ❌ Error al establecer contraseña: {e}")
        return
    
    # 4. Verificar email_verified
    email_verified_attr = next(
        (attr for attr in user_info.get('UserAttributes', []) 
         if attr['Name'] == 'email_verified'),
        None
    )
    
    if not email_verified_attr or email_verified_attr['Value'] == 'false':
        print(f"\n⚙️  Marcando email como verificado...")
        try:
            cognito.admin_update_user_attributes(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=email,
                UserAttributes=[
                    {
                        'Name': 'email_verified',
                        'Value': 'true'
                    }
                ]
            )
            print("   ✅ Email marcado como verificado")
        except ClientError as e:
            print(f"   ⚠️  Error al actualizar email_verified: {e}")
    else:
        print(f"\n✅ Email ya está verificado")
    
    # 5. Verificar estado final
    print(f"\n⚙️  Verificando estado final...")
    try:
        user_info_final = cognito.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=email
        )
        print(f"   Estado final: {user_info_final['UserStatus']}")
        
        email_verified_final = next(
            (attr for attr in user_info_final.get('UserAttributes', []) 
             if attr['Name'] == 'email_verified'),
            None
        )
        
        if email_verified_final:
            print(f"   email_verified: {email_verified_final['Value']}")
        
        if user_info_final['UserStatus'] == 'CONFIRMED':
            print("\n" + "="*80)
            print("✅ ¡TODO LISTO!")
            print("="*80)
            print(f"El usuario {email} está listo para hacer login.")
            print("\nPuedes probarlo con:")
            print(f"curl --location 'http://localhost:8000/api/v1/auth/login' \\")
            print(f"--header 'Content-Type: application/json' \\")
            print(f"--data-raw '{{")
            print(f"  \"email\": \"{email}\",")
            print(f"  \"password\": \"<tu_contraseña>\"")
            print(f"}}'")
        else:
            print(f"\n⚠️  Estado final: {user_info_final['UserStatus']}")
            print("   El usuario podría no estar listo para login")
            
    except ClientError as e:
        print(f"   ❌ Error al verificar estado final: {e}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python scripts/fix_cognito_user.py <email> <password>")
        print("Ejemplo: python scripts/fix_cognito_user.py test4@example.com 'StringTest4*'")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    fix_user(email, password)

