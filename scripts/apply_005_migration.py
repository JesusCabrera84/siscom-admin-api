#!/usr/bin/env python3
"""
Script para aplicar la migración 005: Renombrar imei a device_id

Este script aplica la migración de Alembic que renombra la columna 'imei' 
a 'device_id' en la tabla devices.

Uso:
    python scripts/apply_005_migration.py
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from alembic import command
from alembic.config import Config


def main():
    """Aplica la migración 005."""
    print("=" * 60)
    print("Aplicando migración 005: Renombrar imei a device_id")
    print("=" * 60)
    
    try:
        # Configurar Alembic
        alembic_cfg = Config("alembic.ini")
        
        # Aplicar la migración específica
        print("\n📦 Aplicando migración...")
        command.upgrade(alembic_cfg, "005_rename_device_id")
        
        print("\n" + "=" * 60)
        print("✓ Migración aplicada exitosamente!")
        print("=" * 60)
        print("\nCambios realizados:")
        print("  - Columna 'imei' renombrada a 'device_id'")
        print("  - Índice 'idx_devices_imei' actualizado a 'idx_devices_device_id'")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error al aplicar migración: {e}")
        print("\nPuedes aplicar la migración manualmente con:")
        print("  alembic upgrade 005_rename_device_id")
        sys.exit(1)


if __name__ == "__main__":
    main()

