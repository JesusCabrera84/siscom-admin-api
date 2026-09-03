"""Apply test-only environment defaults before app Settings() loads."""

import os

from tests.sqlite_dialect import register_sqlite_dialect_compat

_TEST_ENV_DEFAULTS = {
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_USER": "test",
    "DB_PASSWORD": "test",
    "DB_NAME": "test",
    "COGNITO_REGION": "us-east-1",
    "COGNITO_USER_POOL_ID": "us-east-1_testpool",
    "COGNITO_CLIENT_ID": "test-client-id",
    "COGNITO_CLIENT_SECRET": "test-client-secret",
    "SES_FROM_EMAIL": "test@example.com",
    "FRONTEND_URL": "http://localhost:3000",
    "PASETO_SECRET_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    # Distinta de PASETO_SECRET_KEY a propósito: los tests deben correr
    # con las dos claves separadas, igual que producción.
    # gitleaks:allow — valor fijo de test, no es un secreto real. Se anota en
    # línea en vez de meter tests/ en el allowlist de .gitleaks.toml: eso haría
    # que un secreto de verdad pegado en un test pasara desapercibido.
    "SHARE_LOCATION_KEY_B64": "c2hhcmUtbG9jYXRpb24tdGVzdC1rZXktMzJieXRlcyE=",  # gitleaks:allow
    "STRIPE_SECRET_KEY": "sk_test_siscom_unit_tests",
    "STRIPE_PUBLISHABLE_KEY": "pk_test_siscom_unit_tests",
    "STRIPE_WEBHOOK_SECRET": "whsec_test_siscom_unit_tests",
    "FACTURAPI_API_KEY": "sk_test_siscom_unit_tests",
}


def apply_test_env_defaults() -> None:
    for key, value in _TEST_ENV_DEFAULTS.items():
        os.environ.setdefault(key, value)


def bootstrap_test_runtime() -> None:
    apply_test_env_defaults()
    register_sqlite_dialect_compat()
