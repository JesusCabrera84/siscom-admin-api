"""
Utilidades de seguridad para manejo de contraseñas y tokens.
"""

import secrets
import warnings
from passlib.context import CryptContext

# Suprimir warnings de passlib sobre la versión de bcrypt
warnings.filterwarnings("ignore", category=UserWarning, module="passlib")

# Contexto para hasheo de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hashea una contraseña usando bcrypt.

    Args:
        password: La contraseña en texto plano

    Returns:
        str: La contraseña hasheada
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña coincide con su hash.

    Args:
        plain_password: La contraseña en texto plano
        hashed_password: El hash de la contraseña

    Returns:
        bool: True si coinciden, False si no
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_verification_token() -> str:
    """
    Genera un token seguro para verificación de email.

    Returns:
        str: Token de 32 caracteres hexadecimales
    """
    return secrets.token_urlsafe(32)
