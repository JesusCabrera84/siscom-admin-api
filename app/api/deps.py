from dataclasses import dataclass
from typing import Literal, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import verify_cognito_token
from app.db.session import get_db
from app.utils.paseto_token import decode_service_token

security = HTTPBearer()


@dataclass
class AuthResult:
    """
    Resultado de autenticación que soporta tanto Cognito como PASETO.
    """

    auth_type: Literal["cognito", "paseto"]
    payload: dict
    # Solo para Cognito
    user_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    # Solo para PASETO service tokens
    service: Optional[str] = None
    role: Optional[str] = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Extrae y valida el token de Cognito del header Authorization.
    Retorna el payload del token validado.
    """
    token = credentials.credentials
    payload = verify_cognito_token(token)
    return payload


def resolve_current_client(db: Session, cognito_payload: dict) -> UUID:
    """
    Busca el usuario por cognito_sub y retorna su client_id.
    """
    from app.models.user import User

    cognito_sub = cognito_payload.get("sub")
    if not cognito_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: falta 'sub'",
        )

    user = db.query(User).filter(User.cognito_sub == cognito_sub).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado en el sistema",
        )

    return user.client_id


def get_current_client_id(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> UUID:
    """
    Dependency que combina autenticación y resolución de client_id.
    Retorna el client_id del usuario autenticado.
    """
    return resolve_current_client(db, current_user)


def get_current_user_full(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retorna el objeto User completo del usuario autenticado.
    """
    from app.models.user import User

    cognito_sub = current_user.get("sub")
    user = db.query(User).filter(User.cognito_sub == cognito_sub).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    return user


def get_current_user_id(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> UUID:
    """
    Retorna el UUID del usuario autenticado.
    """
    from app.models.user import User

    cognito_sub = current_user.get("sub")
    user = db.query(User).filter(User.cognito_sub == cognito_sub).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    return user.id


def get_auth_cognito_or_paseto(
    required_service: Optional[str] = None,
    required_role: Optional[str] = None,
):
    """
    Factory para crear una dependencia que acepta tanto Cognito como PASETO.

    Args:
        required_service: Servicio requerido para tokens PASETO (ej: "gac")
        required_role: Rol requerido para tokens PASETO (ej: "NEXUS_ADMIN")

    Returns:
        Una dependencia de FastAPI que valida el token y retorna AuthResult
    """

    def _verify_auth(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db),
    ) -> AuthResult:
        """
        Verifica el token de autenticación.
        Intenta primero con Cognito, si falla intenta con PASETO.
        """
        from app.models.user import User

        token = credentials.credentials

        # Intentar primero con Cognito
        try:
            cognito_payload = verify_cognito_token(token)

            # Si llegamos aquí, es un token de Cognito válido
            cognito_sub = cognito_payload.get("sub")
            if not cognito_sub:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token de Cognito inválido: falta 'sub'",
                )

            user = db.query(User).filter(User.cognito_sub == cognito_sub).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado en el sistema",
                )

            return AuthResult(
                auth_type="cognito",
                payload=cognito_payload,
                user_id=user.id,
                client_id=user.client_id,
            )

        except HTTPException:
            # Cognito falló, intentar con PASETO
            pass
        except Exception:
            # Cualquier otro error de Cognito, intentar con PASETO
            pass

        # Intentar con PASETO service token
        paseto_payload = decode_service_token(
            token,
            required_service=required_service,
            required_role=required_role,
        )

        if paseto_payload:
            return AuthResult(
                auth_type="paseto",
                payload=paseto_payload,
                service=paseto_payload.get("service"),
                role=paseto_payload.get("role"),
            )

        # Si ambos fallaron, retornar error
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido. Se requiere un token de Cognito válido o un token PASETO de servicio válido.",
        )

    return _verify_auth


# Dependencia pre-configurada para endpoints que requieren NEXUS_ADMIN del servicio gac
get_auth_for_gac_nexus_admin = get_auth_cognito_or_paseto(
    required_service="gac",
    required_role="NEXUS_ADMIN",
)
