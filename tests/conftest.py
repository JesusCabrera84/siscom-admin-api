from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.api.deps import (
    get_current_organization_id,
    get_current_user_full,
    get_current_user_id,
)
from app.db.session import get_db
from app.main import app
from app.models.account import Account
from app.models.organization import Organization
from app.models.device import Device
from app.models.plan import Plan
from app.models.unit import Unit
from app.models.user import User

# Base de datos SQLite en memoria para tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=None,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Crea una nueva sesión de base de datos para cada test.
    """
    SQLModel.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        SQLModel.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    Cliente de prueba de FastAPI con base de datos mockeada.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_account_data(db_session):
    """
    Crea una cuenta de prueba en la base de datos.
    """
    account = Account(
        id=uuid4(),
        name="Test Account",
        status="ACTIVE",
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture(scope="function")
def test_organization_data(db_session, test_account_data):
    """
    Crea una organización de prueba vinculada a la cuenta.
    """
    organization = Organization(
        id=uuid4(),
        name="Test Organization",
        status="ACTIVE",
        account_id=test_account_data.id,
    )
    db_session.add(organization)
    db_session.commit()
    db_session.refresh(organization)
    return organization


# Alias de compatibilidad para tests existentes
@pytest.fixture(scope="function")
def test_client_data(test_organization_data):
    """
    DEPRECATED: Usar test_organization_data.
    Alias para compatibilidad con tests existentes.
    """
    return test_organization_data


@pytest.fixture(scope="function")
def test_user_data(db_session, test_organization_data):
    """
    Crea un usuario de prueba vinculado a la organización de prueba.
    """
    user = User(
        id=uuid4(),
        organization_id=test_organization_data.id,
        cognito_sub="test-cognito-sub-123",
        email="test@example.com",
        full_name="Test User",
        is_master=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_device_data(db_session):
    """
    Crea un dispositivo de prueba en estado 'nuevo' sin organización asignada.
    """
    device = Device(
        device_id="123456789012345",
        brand="Queclink",
        model="GV300",
        firmware_version="1.0.0",
        status="nuevo",
        organization_id=None,  # Sin organización asignada inicialmente
        notes="Dispositivo de prueba",
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device


@pytest.fixture(scope="function")
def test_unit_data(db_session, test_organization_data):
    """
    Crea una unidad (vehículo) de prueba.
    """
    unit = Unit(
        id=uuid4(),
        organization_id=test_organization_data.id,
        name="Camión Test",
        plate="ABC-123",
        type="Camión",
        description="Unidad de prueba",
    )
    db_session.add(unit)
    db_session.commit()
    db_session.refresh(unit)
    return unit


@pytest.fixture(scope="function")
def test_plan_data(db_session):
    """
    Crea un plan de prueba.
    """
    plan = Plan(
        id=uuid4(),
        name="Plan Test",
        description="Plan de prueba",
        price_monthly="299.00",
        price_yearly="2990.00",
        max_devices=10,
        history_days=30,
        ai_features=False,
        analytics_tools=False,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


@pytest.fixture(scope="function")
def authenticated_client(client, test_organization_data, test_user_data):
    """
    Cliente autenticado que bypasea la validación de Cognito.
    """

    def override_get_current_organization_id():
        return test_organization_data.id

    def override_get_current_user_full():
        return test_user_data

    def override_get_current_user_id():
        return test_user_data.id

    app.dependency_overrides[get_current_organization_id] = (
        override_get_current_organization_id
    )
    app.dependency_overrides[get_current_user_full] = override_get_current_user_full
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id

    yield client

    app.dependency_overrides.clear()
