"""
Servicio de notificaciones (stub).
En el futuro, se implementarán notificaciones por email, SMS y push notifications.
"""

from typing import Optional


def send_email(
    to: str,
    subject: str,
    body: str,
    template: Optional[str] = None,
) -> bool:
    """
    Envía un email (stub).

    Args:
        to: Dirección de email del destinatario
        subject: Asunto del email
        body: Cuerpo del mensaje
        template: Nombre del template a usar (opcional)

    Returns:
        True si se envió correctamente
    """
    # TODO: Implementar envío de emails (AWS SES, SendGrid, etc.)
    print(f"[STUB] Email enviado a {to}: {subject}")
    return True


def send_sms(to: str, message: str) -> bool:
    """
    Envía un SMS (stub).

    Args:
        to: Número de teléfono del destinatario
        message: Mensaje a enviar

    Returns:
        True si se envió correctamente
    """
    # TODO: Implementar envío de SMS (Twilio, AWS SNS, etc.)
    print(f"[STUB] SMS enviado a {to}: {message}")
    return True


def send_push_notification(
    user_id: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> bool:
    """
    Envía una notificación push (stub).

    Args:
        user_id: ID del usuario destinatario
        title: Título de la notificación
        body: Cuerpo de la notificación
        data: Datos adicionales (opcional)

    Returns:
        True si se envió correctamente
    """
    # TODO: Implementar push notifications (Firebase, OneSignal, etc.)
    print(f"[STUB] Push notification enviada a {user_id}: {title}")
    return True
