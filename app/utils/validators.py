"""
Validadores reutilizables para diferentes campos de los modelos.
"""

import re


def validate_password(password: str) -> str:
    """
    Valida que la contraseña cumpla con los requisitos de seguridad:
    - Al menos 8 caracteres
    - Máximo 72 caracteres (límite de bcrypt)
    - Al menos una letra mayúscula
    - Al menos un número
    - Al menos un carácter especial

    Args:
        password: La contraseña a validar

    Returns:
        str: La contraseña validada

    Raises:
        ValueError: Si la contraseña no cumple con los requisitos
    """
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")

    if len(password) > 72:
        raise ValueError("La contraseña no puede tener más de 72 caracteres")

    if not re.search(r"[A-Z]", password):
        raise ValueError("La contraseña debe contener al menos una letra mayúscula")

    if not re.search(r"\d", password):
        raise ValueError("La contraseña debe contener al menos un número")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\];~]', password):
        raise ValueError(
            "La contraseña debe contener al menos un carácter especial "
            '(!@#$%^&*(),.?":{}|<>_-+=[];)'
        )

    return password


def validate_name(name: str) -> str:
    """
    Valida que el nombre no esté vacío y tenga un formato válido.

    Args:
        name: El nombre a validar

    Returns:
        str: El nombre validado

    Raises:
        ValueError: Si el nombre no cumple con los requisitos
    """
    name = name.strip()

    if not name:
        raise ValueError("El nombre no puede estar vacío")

    if len(name) < 2:
        raise ValueError("El nombre debe tener al menos 2 caracteres")

    return name
