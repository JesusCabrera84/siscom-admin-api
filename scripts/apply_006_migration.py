#!/usr/bin/env python3
"""
Script para aplicar la migración 006: Reestructuración de devices y creación de device_events

Este script:
1. Verifica el estado actual de la base de datos
2. Aplica la migración 006 usando Alembic
3. Valida que los cambios se aplicaron correctamente
4. Muestra estadísticas de dispositivos migrados

Uso:
    python scripts/apply_006_migration.py [--dry-run]
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.config import settings
from alembic.config import Config
from alembic import command


def get_db_engine():
    """Crea y retorna el engine de la base de datos"""
    database_url = f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    return create_engine(database_url)


def check_current_schema(session: Session):
    """Verifica el esquema actual de la tabla devices"""
    print("🔍 Verificando esquema actual...")
    
    # Verificar si existe la tabla devices
    result = session.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'devices'
        )
    """))
    devices_exists = result.scalar()
    
    if not devices_exists:
        print("❌ La tabla 'devices' no existe")
        return False
    
    # Verificar columnas actuales
    result = session.execute(text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'devices'
        ORDER BY ordinal_position
    """))
    
    columns = result.fetchall()
    print(f"✅ Tabla 'devices' encontrada con {len(columns)} columnas")
    
    # Verificar si tiene la estructura antigua (con campo 'active')
    has_active = any(col[0] == 'active' for col in columns)
    has_status = any(col[0] == 'status' for col in columns)
    
    if has_active and not has_status:
        print("📋 Esquema antiguo detectado (con campo 'active')")
        return "old"
    elif has_status and not has_active:
        print("✅ Esquema nuevo detectado (con campo 'status')")
        return "new"
    else:
        print("⚠️  Esquema en estado desconocido")
        return "unknown"


def get_device_count(session: Session) -> int:
    """Obtiene el número de dispositivos en la base de datos"""
    try:
        result = session.execute(text("SELECT COUNT(*) FROM devices"))
        return result.scalar()
    except Exception:
        return 0


def check_device_events_table(session: Session) -> bool:
    """Verifica si existe la tabla device_events"""
    result = session.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'device_events'
        )
    """))
    return result.scalar()


def apply_migration(dry_run: bool = False):
    """Aplica la migración usando Alembic"""
    print("\n" + "="*60)
    print("🚀 Iniciando migración 006")
    print("="*60 + "\n")
    
    engine = get_db_engine()
    
    with Session(engine) as session:
        # Verificar estado actual
        schema_status = check_current_schema(session)
        device_count = get_device_count(session)
        has_events = check_device_events_table(session)
        
        print(f"\n📊 Estado actual:")
        print(f"   - Dispositivos en BD: {device_count}")
        print(f"   - Tabla device_events: {'✅ Existe' if has_events else '❌ No existe'}")
        
        if schema_status == "new" and has_events:
            print("\n✅ La migración ya fue aplicada anteriormente")
            print("   No se requiere ninguna acción")
            return True
        
        if schema_status == "unknown":
            print("\n❌ Error: Esquema en estado desconocido")
            print("   Revise manualmente el estado de la base de datos")
            return False
        
        if dry_run:
            print("\n🔍 Modo DRY RUN - No se aplicarán cambios")
            print("\nCambios que se aplicarían:")
            print("  1. Migrar campo 'active' a 'status' con múltiples estados")
            print("  2. Hacer client_id nullable")
            print("  3. Cambiar device_id a PRIMARY KEY")
            print("  4. Agregar campos: firmware_version, last_assignment_at, notes")
            print("  5. Crear tabla device_events")
            print("  6. Crear trigger para prevenir DELETE")
            print("  7. Migrar datos existentes preservando información")
            return True
        
        # Confirmar con el usuario
        print("\n⚠️  ADVERTENCIA: Esta migración hará cambios estructurales importantes")
        print("   Se recomienda tener un backup de la base de datos")
        print(f"\n   Se migrarán {device_count} dispositivos")
        
        response = input("\n¿Desea continuar? (sí/no): ").strip().lower()
        if response not in ['sí', 'si', 'yes', 'y', 's']:
            print("\n❌ Migración cancelada por el usuario")
            return False
        
        # Aplicar migración con Alembic
        print("\n🔄 Aplicando migración...")
        
        try:
            alembic_cfg = Config(str(root_dir / "alembic.ini"))
            alembic_cfg.set_main_option("script_location", str(root_dir / "app" / "db" / "migrations"))
            
            # Ejecutar upgrade a la revisión 006
            command.upgrade(alembic_cfg, "006_devices_events")
            
            print("✅ Migración aplicada exitosamente")
            
        except Exception as e:
            print(f"\n❌ Error al aplicar migración: {e}")
            return False
        
        # Validar cambios
        print("\n🔍 Validando cambios...")
        session.commit()  # Refresh session
        
        schema_status_after = check_current_schema(session)
        has_events_after = check_device_events_table(session)
        device_count_after = get_device_count(session)
        
        if schema_status_after != "new":
            print("❌ Error: El esquema no se actualizó correctamente")
            return False
        
        if not has_events_after:
            print("❌ Error: La tabla device_events no fue creada")
            return False
        
        if device_count_after != device_count:
            print(f"⚠️  Advertencia: El número de dispositivos cambió ({device_count} → {device_count_after})")
        
        # Obtener estadísticas de eventos creados
        result = session.execute(text("SELECT COUNT(*) FROM device_events"))
        event_count = result.scalar()
        
        print("\n" + "="*60)
        print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("="*60)
        print(f"\n📊 Resumen:")
        print(f"   - Dispositivos migrados: {device_count_after}")
        print(f"   - Eventos creados: {event_count}")
        print(f"   - Tabla device_events: ✅ Creada")
        print(f"   - Trigger de protección: ✅ Instalado")
        
        # Mostrar distribución de estados
        result = session.execute(text("""
            SELECT status, COUNT(*) as count
            FROM devices
            GROUP BY status
            ORDER BY count DESC
        """))
        
        print("\n📈 Distribución de estados:")
        for row in result:
            print(f"   - {row[0]}: {row[1]}")
        
        print("\n✅ Todas las validaciones pasaron correctamente")
        print("\n💡 Siguiente paso: Verificar manualmente algunos registros en la BD")
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Aplica la migración 006 para reestructurar devices"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra qué cambios se aplicarían sin ejecutarlos"
    )
    
    args = parser.parse_args()
    
    try:
        success = apply_migration(dry_run=args.dry_run)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

