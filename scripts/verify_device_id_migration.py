#!/usr/bin/env python3
"""
Script para verificar que la migración de imei a device_id se aplicó correctamente.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text

from app.db.session import DATABASE_URL


def main():
    print("=" * 60)
    print("Verificando migración: imei → device_id")
    print("=" * 60)

    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Verificar columnas en la tabla devices
        result = conn.execute(
            text(
                """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'devices'
            AND column_name IN ('imei', 'device_id')
            ORDER BY column_name
        """
            )
        )

        columns = result.fetchall()

        print("\n📋 Columnas en la tabla 'devices':")
        if not columns:
            print("  ❌ No se encontraron las columnas")
            return False

        has_device_id = False
        has_imei = False

        for col in columns:
            if col[0] == "device_id":
                print(f"  ✓ device_id: {col[1]} (nullable: {col[2]})")
                has_device_id = True
            elif col[0] == "imei":
                print(f"  ✗ imei: {col[1]} (nullable: {col[2]}) - ¡No debería existir!")
                has_imei = True

        # Verificar índices
        print("\n📇 Índices en la tabla 'devices':")
        result = conn.execute(
            text(
                """
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'devices'
            AND indexname IN ('idx_devices_imei', 'idx_devices_device_id')
            ORDER BY indexname
        """
            )
        )

        indexes = result.fetchall()

        has_device_id_idx = False
        has_imei_idx = False

        for idx in indexes:
            if idx[0] == "idx_devices_device_id":
                print(f"  ✓ {idx[0]}")
                has_device_id_idx = True
            elif idx[0] == "idx_devices_imei":
                print(f"  ✗ {idx[0]} - ¡No debería existir!")
                has_imei_idx = True

        # Resultado final
        print("\n" + "=" * 60)
        if has_device_id and not has_imei and has_device_id_idx and not has_imei_idx:
            print("✅ Migración aplicada correctamente!")
            print("=" * 60)
            return True
        else:
            print("❌ La migración no se aplicó correctamente")
            if not has_device_id:
                print("  - Falta la columna device_id")
            if has_imei:
                print("  - La columna imei todavía existe")
            if not has_device_id_idx:
                print("  - Falta el índice idx_devices_device_id")
            if has_imei_idx:
                print("  - El índice idx_devices_imei todavía existe")
            print("=" * 60)
            return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
