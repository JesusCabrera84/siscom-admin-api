"""
Script para hacer password_hash nullable en la tabla users.
Esto es necesario porque usamos AWS Cognito para autenticación.

Uso: python scripts/apply_password_hash_migration.py
"""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text

from app.db.session import engine


def apply_migration():
    """Aplica la migración para hacer password_hash nullable."""

    print("=" * 80)
    print("🔧 APLICANDO MIGRACIÓN: password_hash nullable")
    print("=" * 80)
    print("\nEsta migración es necesaria porque:")
    print("- Usamos AWS Cognito para autenticación")
    print("- No necesitamos almacenar contraseñas en nuestra base de datos")
    print("- Las contraseñas se manejan completamente en Cognito")
    print("-" * 80)

    try:
        with engine.connect() as connection:
            # 1. Verificar el estado actual
            print("\n1. Verificando estado actual de la columna...")
            result = connection.execute(
                text(
                    """
                SELECT
                    column_name,
                    data_type,
                    is_nullable
                FROM
                    information_schema.columns
                WHERE
                    table_name = 'users'
                    AND column_name = 'password_hash'
            """
                )
            )

            row = result.fetchone()
            if row:
                print(f"   Column: {row[0]}")
                print(f"   Type: {row[1]}")
                print(f"   Is Nullable: {row[2]}")

                if row[2] == "YES":
                    print("\n✅ La columna password_hash ya es nullable.")
                    print("   No se necesita aplicar la migración.")
                    return
            else:
                print("   ⚠️  No se encontró la columna password_hash")
                return

            # 2. Aplicar la migración
            print("\n2. Aplicando migración...")
            connection.execute(
                text(
                    """
                ALTER TABLE users
                ALTER COLUMN password_hash DROP NOT NULL
            """
                )
            )
            connection.commit()
            print("   ✅ Migración aplicada exitosamente")

            # 3. Verificar el resultado
            print("\n3. Verificando el resultado...")
            result = connection.execute(
                text(
                    """
                SELECT
                    column_name,
                    data_type,
                    is_nullable
                FROM
                    information_schema.columns
                WHERE
                    table_name = 'users'
                    AND column_name = 'password_hash'
            """
                )
            )

            row = result.fetchone()
            if row:
                print(f"   Column: {row[0]}")
                print(f"   Type: {row[1]}")
                print(f"   Is Nullable: {row[2]}")

                if row[2] == "YES":
                    print("\n" + "=" * 80)
                    print("✅ ¡MIGRACIÓN COMPLETADA EXITOSAMENTE!")
                    print("=" * 80)
                    print("\nAhora puedes:")
                    print("1. Crear usuarios sin necesidad de password_hash")
                    print("2. Usar el endpoint de accept-invitation correctamente")
                    print("3. Las contraseñas se manejan completamente en Cognito")
                else:
                    print("\n⚠️  La columna sigue siendo NOT NULL")

    except Exception as e:
        print(f"\n❌ Error al aplicar la migración: {e}")
        print("\nPuedes intentar ejecutar manualmente:")
        print(
            '  psql -d siscom_admin -c "ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;"'
        )
        sys.exit(1)

    print("\n" + "=" * 80)


if __name__ == "__main__":
    apply_migration()
