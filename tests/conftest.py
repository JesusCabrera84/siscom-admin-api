import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from uuid import uuid4

from app.main import app
from app.db.session import get_db
from app.api.deps import get_current_client_id, get_current_user_full, get_current_user_id
from app.models.client import Client
from app.models.user import User
from app.models.device import Device
from app.models.plan import Plan
from app.models.unit import Unit

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
def test_client_data(db_session):
    """
    Crea un cliente de prueba en la base de datos.
    """
    client = Client(
        id=uuid4(),
        name="Test Client",
        status="ACTIVE",
    )
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


@pytest.fixture(scope="function")
def test_user_data(db_session, test_client_data):
    """
    Crea un usuario de prueba vinculado al cliente de prueba.
    """
    user = User(
        id=uuid4(),
        client_id=test_client_data.id,
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
    Crea un dispositivo de prueba en estado 'nuevo' sin cliente asignado.
    """
    device = Device(
        device_id="123456789012345",
        brand="Queclink",
        model="GV300",
        firmware_version="1.0.0",
        status="nuevo",
        client_id=None,  # Sin cliente asignado inicialmente
        notes="Dispositivo de prueba",
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device


@pytest.fixture(scope="function")
def test_unit_data(db_session, test_client_data):
    """
    Crea una unidad (vehículo) de prueba.
    """
    unit = Unit(
        id=uuid4(),
        client_id=test_client_data.id,
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
def authenticated_client(client, test_client_data, test_user_data):
    """
    Cliente autenticado que bypasea la validación de Cognito.
    """
    def override_get_current_client_id():
        return test_client_data.id
    
    def override_get_current_user_full():
        return test_user_data
    
    def override_get_current_user_id():
        return test_user_data.id
    
    app.dependency_overrides[get_current_client_id] = override_get_current_client_id
    app.dependency_overrides[get_current_user_full] = override_get_current_user_full
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id
    
    yield client
    
    app.dependency_overrides.clear()

