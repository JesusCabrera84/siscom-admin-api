"""
Utilidad para verificar reCAPTCHA v3 de Google.
"""

import httpx
from fastapi import HTTPException

from app.core.config import settings


async def verify_recaptcha(token: str, min_score: float = 0.5) -> dict:
    """
    Verifica el token de reCAPTCHA v3 con Google.

    Args:
        token: Token de reCAPTCHA recibido del frontend
        min_score: Score mínimo requerido (0.0 a 1.0). Default: 0.5
                  - 1.0: Muy probablemente humano
                  - 0.5: Neutro
                  - 0.0: Muy probablemente bot

    Returns:
        dict: Respuesta de Google con score y otros datos

    Raises:
        HTTPException: Si el reCAPTCHA es inválido o el score es bajo
    """
    # Si no hay secret key configurada, saltamos la validación (solo desarrollo)
    if not settings.RECAPTCHA_SECRET_KEY:
        print(
            "[WARNING] RECAPTCHA_SECRET_KEY no configurada. "
            "Saltando validación de reCAPTCHA."
        )
        return {
            "success": True,
            "score": 1.0,
            "action": "submit",
            "challenge_ts": "",
            "hostname": "localhost",
            "warning": "reCAPTCHA deshabilitado - solo para desarrollo",
        }

    if not token:
        raise HTTPException(
            status_code=400, detail="Token de reCAPTCHA requerido pero no proporcionado"
        )

    url = "https://www.google.com/recaptcha/api/siteverify"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                data={"secret": settings.RECAPTCHA_SECRET_KEY, "response": token},
            )

        data = response.json()

        # Log para debug
        print(
            f"[RECAPTCHA] Verificación: success={data.get('success')}, "
            f"score={data.get('score')}, action={data.get('action')}"
        )

        # Verificar si la respuesta fue exitosa
        if not data.get("success"):
            error_codes = data.get("error-codes", [])
            print(f"[RECAPTCHA ERROR] Error codes: {error_codes}")
            raise HTTPException(
                status_code=400,
                detail="reCAPTCHA inválido. Por favor intenta nuevamente.",
            )

        # Verificar el score
        score = data.get("score", 0.0)
        if score < min_score:
            print(
                f"[RECAPTCHA] Score bajo: {score} < {min_score}. "
                f"Posible bot detectado."
            )
            raise HTTPException(
                status_code=400,
                detail="Verificación de seguridad fallida. "
                "Por favor intenta nuevamente o contacta al administrador.",
            )

        return data

    except httpx.TimeoutException:
        print("[RECAPTCHA ERROR] Timeout al conectar con Google reCAPTCHA")
        raise HTTPException(
            status_code=503,
            detail="Servicio de verificación temporalmente no disponible. "
            "Por favor intenta más tarde.",
        )
    except httpx.RequestError as e:
        print(f"[RECAPTCHA ERROR] Error de red: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Error al verificar reCAPTCHA. Por favor intenta más tarde.",
        )
    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except Exception as e:
        print(f"[RECAPTCHA ERROR] Error inesperado: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Error interno al verificar reCAPTCHA"
        )
