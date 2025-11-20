"""
Validadores reutilizables para diferentes campos de los modelos.
"""

import html
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


def sanitize_html(text: str, max_length: int = 5000) -> str:
    """
    Sanitiza texto escapando HTML y scripts para prevenir XSS.

    Args:
        text: El texto a sanitizar
        max_length: Longitud máxima permitida del texto

    Returns:
        str: El texto sanitizado y escapado

    Raises:
        ValueError: Si el texto excede la longitud máxima
    """
    if not text:
        return text

    # Limpiar espacios
    text = text.strip()

    # Validar longitud
    if len(text) > max_length:
        raise ValueError(f"El texto no puede exceder {max_length} caracteres")

    # Escapar HTML para prevenir XSS
    sanitized = html.escape(text)

    return sanitized


def sanitize_contact_field(text: str, field_name: str, max_length: int = 1000) -> str:
    """
    Sanitiza campos de formulario de contacto.

    Args:
        text: El texto a sanitizar
        field_name: Nombre del campo (para mensajes de error)
        max_length: Longitud máxima permitida

    Returns:
        str: El texto sanitizado

    Raises:
        ValueError: Si el texto es inválido
    """
    if not text:
        return text

    text = text.strip()

    if not text:
        raise ValueError(f"El campo {field_name} no puede estar vacío")

    if len(text) > max_length:
        raise ValueError(
            f"El campo {field_name} no puede exceder {max_length} caracteres"
        )

    # Escapar HTML
    return html.escape(text)


def validate_phone(phone: str) -> str:
    """
    Valida y sanitiza un número de teléfono.
    Permite números con espacios, guiones, paréntesis y signo +

    Args:
        phone: El teléfono a validar

    Returns:
        str: El teléfono sanitizado

    Raises:
        ValueError: Si el teléfono es inválido
    """
    if not phone:
        return phone

    phone = phone.strip()

    # Permitir solo caracteres válidos en números de teléfono
    if not re.match(r"^[\d\s\+\-\(\)]+$", phone):
        raise ValueError(
            "El teléfono solo puede contener números, espacios, +, -, ( y )"
        )

    # Validar longitud razonable (mínimo 7, máximo 20 caracteres)
    digits_only = re.sub(r"\D", "", phone)
    if len(digits_only) < 7:
        raise ValueError("El teléfono debe tener al menos 7 dígitos")

    if len(digits_only) > 20:
        raise ValueError("El teléfono no puede tener más de 20 dígitos")

    # Escapar cualquier HTML por seguridad
    return html.escape(phone)
