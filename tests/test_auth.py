"""
Tests de autenticación.
Verifica que los endpoints protegidos rechacen requests sin token válido.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import status

from app.core.config import settings
from app.models.token_confirmacion import TokenConfirmacion, TokenType
from app.utils.datetime import utcnow


def test_endpoint_without_token_returns_401(client):
    """GET /organizations requiere autenticación."""
    response = client.get("/api/v1/organizations")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_missing_credentials_sets_www_authenticate_header(client):
    """RFC 9110 exige `WWW-Authenticate` en las respuestas 401."""
    response = client.get("/api/v1/organizations")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["www-authenticate"] == "Bearer"


def test_non_bearer_scheme_returns_401_with_www_authenticate(client):
    """Un esquema distinto de Bearer es 'no sé quién eres', no 'no puedes'."""
    headers = {"Authorization": "Basic dXNlcjpwYXNz"}
    response = client.get("/api/v1/organizations", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["www-authenticate"] == "Bearer"


def test_endpoint_with_invalid_token_returns_401(client):
    """Token inválido en endpoint protegido."""
    headers = {"Authorization": "Bearer invalid_token_here"}
    response = client.get("/api/v1/organizations", headers=headers)
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        status.HTTP_503_SERVICE_UNAVAILABLE,
    ]


def test_devices_my_devices_endpoint_without_auth(client):
    """GET /devices/my-devices requiere autenticación."""
    response = client.get("/api/v1/devices/my-devices")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_services_endpoint_without_auth(client):
    """GET /services/active requiere autenticación."""
    response = client.get("/api/v1/services/active")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_verify_email_existing_cognito_user_sends_email_attribute(
    client, db_session, test_user_data
):
    """
    Cognito exige `email` junto a `email_verified` en admin_update_user_attributes.
    Cubre la rama de usuario master que ya existe en Cognito (Flujo A).
    """
    token_value = "verify-existing-cognito-user"
    token_record = TokenConfirmacion(
        id=uuid4(),
        token=token_value,
        expires_at=utcnow() + timedelta(hours=1),
        used=False,
        type=TokenType.EMAIL_VERIFICATION,
        user_id=test_user_data.id,
        email=test_user_data.email,
        password_temp="TempPass123!",
    )
    db_session.add(token_record)
    db_session.commit()

    existing_sub = "existing-cognito-sub-456"
    mock_cognito = MagicMock()
    mock_cognito.admin_get_user.return_value = {
        "UserAttributes": [
            {"Name": "sub", "Value": existing_sub},
            {"Name": "email", "Value": test_user_data.email},
            {"Name": "email_verified", "Value": "false"},
        ]
    }

    with patch("app.api.v1.endpoints.auth.cognito", mock_cognito):
        response = client.post(f"/api/v1/auth/verify-email?token={token_value}")

    assert response.status_code == status.HTTP_200_OK
    mock_cognito.admin_create_user.assert_not_called()
    mock_cognito.admin_set_user_password.assert_called_once()
    mock_cognito.admin_update_user_attributes.assert_called_once_with(
        UserPoolId=settings.COGNITO_USER_POOL_ID,
        Username=test_user_data.email,
        UserAttributes=[
            {"Name": "email", "Value": test_user_data.email},
            {"Name": "email_verified", "Value": "true"},
        ],
    )

    db_session.refresh(test_user_data)
    db_session.refresh(token_record)
    assert test_user_data.email_verified is True
    assert test_user_data.cognito_sub == existing_sub
    assert token_record.used is True
    assert token_record.password_temp is None


# ---------------------------------------------------------------------------
# Data token adjunto al login (Fase 1)
# ---------------------------------------------------------------------------


def _make_verified_user(db_session, test_organization_data):
    from app.models.user import User

    user = User(
        id=uuid4(),
        organization_id=test_organization_data.id,
        email="login-datatoken@example.com",
        full_name="Login Test",
        email_verified=True,
        is_master=True,
        cognito_sub=str(uuid4()),
    )
    db_session.add(user)
    db_session.commit()
    return user


def _cognito_ok():
    return {
        "AuthenticationResult": {
            "AccessToken": "access",
            "IdToken": "id",
            "RefreshToken": "refresh",
            "ExpiresIn": 3600,
        }
    }


def test_login_without_data_plane_still_succeeds(
    client, db_session, test_organization_data
):
    """
    El plano de datos no puede impedir iniciar sesión. Sin Valkey el usuario entra
    igual y verá la aplicación sin mapa, en vez de no poder entrar; el cliente lo
    reintenta luego contra `POST /auth/data-token`, que ahí sí devuelve 503.
    """
    from app.api.deps import get_scope_store
    from app.main import app as fastapi_app
    from app.services.scope_store import ScopeStore

    user = _make_verified_user(db_session, test_organization_data)
    fastapi_app.dependency_overrides[get_scope_store] = lambda: ScopeStore(None)

    try:
        with patch("app.api.v1.endpoints.auth.cognito") as cognito:
            cognito.initiate_auth.return_value = _cognito_ok()
            response = client.post(
                "/api/v1/auth/login",
                json={"email": user.email, "password": "irrelevante"},
            )
    finally:
        fastapi_app.dependency_overrides.pop(get_scope_store, None)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data_token"] is None
    # Las credenciales de sesión siguen llegando
    assert body["access_token"] == "access"
