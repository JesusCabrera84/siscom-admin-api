"""
Script para poblar datos iniciales en la base de datos.
Ejecutar después de las migraciones: python scripts/seed_data.py
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.client import Client, ClientStatus
from app.models.user import User
from app.models.plan import Plan
from app.models.device import Device
from uuid import uuid4


def seed_plans(db: Session):
    """Crea planes de ejemplo."""
    plans = [
        Plan(
            id=uuid4(),
            name="Plan Básico",
            description="Plan básico para rastreo GPS",
            price_monthly="299.00",
            price_yearly="2990.00",
            max_devices=5,
            history_days=7,
            ai_features=False,
            analytics_tools=False,
            features={"real_time_tracking": True, "alerts": True, "reports": "basic"},
        ),
        Plan(
            id=uuid4(),
            name="Plan Profesional",
            description="Plan profesional con características avanzadas",
            price_monthly="599.00",
            price_yearly="5990.00",
            max_devices=20,
            history_days=90,
            ai_features=True,
            analytics_tools=True,
            features={
                "real_time_tracking": True,
                "alerts": True,
                "reports": "advanced",
                "geofencing": True,
                "maintenance_alerts": True,
            },
        ),
        Plan(
            id=uuid4(),
            name="Plan Empresarial",
            description="Plan empresarial sin límites",
            price_monthly="1499.00",
            price_yearly="14990.00",
            max_devices=None,  # Sin límite
            history_days=365,
            ai_features=True,
            analytics_tools=True,
            features={
                "real_time_tracking": True,
                "alerts": True,
                "reports": "premium",
                "geofencing": True,
                "maintenance_alerts": True,
                "custom_integrations": True,
                "dedicated_support": True,
            },
        ),
    ]
    
    for plan in plans:
        existing = db.query(Plan).filter(Plan.name == plan.name).first()
        if not existing:
            db.add(plan)
            print(f"✓ Plan creado: {plan.name}")
        else:
            print(f"- Plan ya existe: {plan.name}")
    
    db.commit()


def seed_test_client(db: Session):
    """Crea un cliente de prueba con usuario."""
    # Crear cliente
    client = Client(
        id=uuid4(),
        name="Transportes Demo",
        status=ClientStatus.ACTIVE.value,
    )
    
    existing_client = db.query(Client).filter(Client.name == client.name).first()
    if existing_client:
        print(f"- Cliente ya existe: {client.name}")
        return existing_client
    
    db.add(client)
    db.flush()
    print(f"✓ Cliente creado: {client.name}")
    
    # Crear usuario de prueba
    # Nota: En producción, el cognito_sub vendría de AWS Cognito
    user = User(
        id=uuid4(),
        client_id=client.id,
        cognito_sub="demo-user-cognito-sub-123",
        email="demo@transportes.com",
        full_name="Usuario Demo",
        is_master=True,
    )
    db.add(user)
    db.flush()
    print(f"✓ Usuario creado: {user.email}")
    
    # Crear algunos dispositivos de prueba
    devices = [
        Device(
            id=uuid4(),
            client_id=client.id,
            imei="123456789012345",
            brand="Queclink",
            model="GV300",
            active=True,
        ),
        Device(
            id=uuid4(),
            client_id=client.id,
            imei="234567890123456",
            brand="Teltonika",
            model="FMB920",
            active=True,
        ),
        Device(
            id=uuid4(),
            client_id=client.id,
            imei="345678901234567",
            brand="Queclink",
            model="GV500",
            active=True,
        ),
    ]
    
    for device in devices:
        db.add(device)
        print(f"✓ Dispositivo creado: {device.imei}")
    
    db.commit()
    
    return client


def main():
    print("=" * 60)
    print("Poblando base de datos con datos iniciales...")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Crear planes
        print("\n📋 Creando planes...")
        seed_plans(db)
        
        # Crear cliente y usuario de prueba
        print("\n👥 Creando cliente de prueba...")
        seed_test_client(db)
        
        print("\n" + "=" * 60)
        print("✓ Datos iniciales creados exitosamente!")
        print("=" * 60)
        print("\nInformación de prueba:")
        print("  Email: demo@transportes.com")
        print("  Cognito Sub: demo-user-cognito-sub-123")
        print("\nPuedes usar estos datos para testing.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error al poblar datos: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

