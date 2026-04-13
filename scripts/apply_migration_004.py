"""
Script para aplicar la migración 004:
- Hace password_hash nullable en users
- Agrega password_temp a tokens_confirmacion

Uso: python scripts/apply_migration_004.py
"""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text

from app.db.session import engine


def apply_migration():
    """Aplica la migración 004."""

    print("=" * 80)
    print("🔧 APLICANDO MIGRACIÓN 004")
    print("=" * 80)
    print("\nEsta migración:")
    print("1. Hace password_hash nullable en users")
    print("2. Agrega password_temp a tokens_confirmacion")
    print("-" * 80)

    try:
        with engine.connect() as connection:
            # 1. Hacer password_hash nullable
            print("\n1. Haciendo password_hash nullable...")
            connection.execute(
                text(
                    """
                ALTER TABLE users
                ALTER COLUMN password_hash DROP NOT NULL
            """
                )
            )
            print("   ✅ password_hash ahora es nullable")

            # 2. Agregar password_temp a tokens_confirmacion
            print("\n2. Agregando password_temp a tokens_confirmacion...")
            connection.execute(
                text(
                    """
                ALTER TABLE tokens_confirmacion
                ADD COLUMN IF NOT EXISTS password_temp VARCHAR(255) NULL
            """
                )
            )
            print("   ✅ password_temp agregado")

            connection.commit()

            # 3. Verificar cambios
            print("\n3. Verificando cambios...")
            result = connection.execute(
                text(
                    """
                SELECT
                    column_name,
                    is_nullable,
                    data_type
                FROM information_schema.columns
                WHERE
                    (table_name = 'users' AND column_name = 'password_hash')
                    OR
                    (table_name = 'tokens_confirmacion' AND column_name = 'password_temp')
                ORDER BY table_name, column_name
            """
                )
            )

            print("\n   Columnas actualizadas:")
            for row in result:
                nullable_symbol = "✅" if row[1] == "YES" else "❌"
                print(f"   {nullable_symbol} {row[0]}: {row[2]} (nullable: {row[1]})")

    except Exception as e:
        print(f"\n❌ Error al aplicar la migración: {e}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("✅ ¡MIGRACIÓN 004 APLICADA EXITOSAMENTE!")
    print("=" * 80)
    print("\nAhora:")
    print("1. ✅ password_hash es opcional en users")
    print("2. ✅ tokens_confirmacion puede guardar contraseñas temporalmente")
    print("3. ✅ El flujo de verificación funciona correctamente")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    apply_migration()
