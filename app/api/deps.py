from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.security import verify_cognito_token
from app.db.session import get_db

security = HTTPBearer()


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
