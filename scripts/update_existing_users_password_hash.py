"""
Script para actualizar el password_hash de usuarios existentes que no lo tengan.

NOTA: Este script establece una contraseña temporal. Los usuarios deberán
cambiarla o usar el sistema de recuperación de contraseña.

Uso: python scripts/update_existing_users_password_hash.py
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.models.user import User
from app.utils.security import hash_password
from app.core.config import settings


def update_users_without_password_hash():
    """Actualiza usuarios que no tienen password_hash."""
    
    print("="*80)
    print("🔧 ACTUALIZANDO PASSWORD_HASH DE USUARIOS EXISTENTES")
    print("="*80)
    print("\nBuscando usuarios sin password_hash...")
    print("-"*80)
    
    db = SessionLocal()
    
    try:
        # Buscar usuarios sin password_hash
        users_without_hash = db.query(User).filter(
            (User.password_hash == None) | (User.password_hash == '')
        ).all()
        
        if not users_without_hash:
            print("\n✅ Todos los usuarios ya tienen password_hash.")
            print("   No se necesita actualizar nada.")
            return
        
        print(f"\n📋 Encontrados {len(users_without_hash)} usuarios sin password_hash:")
        print()
        
        for user in users_without_hash:
            print(f"   - {user.email} (ID: {user.id})")
        
        print("\n" + "-"*80)
        print("⚠️  IMPORTANTE:")
        print(f"   Se establecerá la contraseña temporal: {settings.DEFAULT_USER_PASSWORD}")
        print("   Los usuarios deberán cambiarla después del primer login.")
        print("-"*80)
        
        # Solicitar confirmación
        response = input("\n¿Deseas continuar? (sí/no): ").strip().lower()
        
        if response not in ['sí', 'si', 'yes', 'y', 's']:
            print("\n❌ Operación cancelada por el usuario.")
            return
        
        # Actualizar usuarios
        print("\n⚙️  Actualizando usuarios...")
        temp_password = settings.DEFAULT_USER_PASSWORD
        temp_password_hash = hash_password(temp_password)
        
        updated_count = 0
        for user in users_without_hash:
            user.password_hash = temp_password_hash
            updated_count += 1
            print(f"   ✓ {user.email}")
        
        db.commit()
        
        print("\n" + "="*80)
        print(f"✅ ¡ACTUALIZACIÓN COMPLETADA!")
        print("="*80)
        print(f"\nSe actualizaron {updated_count} usuarios.")
        print(f"\nContraseña temporal establecida: {temp_password}")
        print("\n⚠️  Recuerda notificar a los usuarios que deben cambiar su contraseña.")
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"\n❌ Error al actualizar usuarios: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    update_users_without_password_hash()

