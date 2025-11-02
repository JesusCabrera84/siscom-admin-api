from datetime import datetime
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserLogin, UserLoginResponse
from app.core.config import settings
from botocore.exceptions import ClientError
import hmac
import hashlib
import base64
import boto3

router = APIRouter()

# ------------------------------------------
# Cognito client
# ------------------------------------------
cognito = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)


def get_secret_hash(username: str) -> str:
    """
    Genera el SECRET_HASH requerido por Cognito cuando se usa CLIENT_SECRET.
    """
    message = bytes(username + settings.COGNITO_CLIENT_ID, "utf-8")
    secret = bytes(settings.COGNITO_CLIENT_SECRET, "utf-8")
    dig = hmac.new(secret, msg=message, digestmod=hashlib.sha256).digest()
    return base64.b64encode(dig).decode()


# ------------------------------------------
# Login de usuario
# ------------------------------------------
@router.post("/login", response_model=UserLoginResponse, status_code=status.HTTP_200_OK)
def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Autentica un usuario con sus credenciales.
    
    Proceso:
    1. Verifica que el usuario exista en la base de datos
    2. Verifica que el email esté verificado
    3. Autentica con AWS Cognito
    4. Actualiza el last_login_at
    5. Retorna la información del usuario y los tokens de Cognito
    
    Códigos de error:
    - 404: Usuario no encontrado
    - 403: Email no verificado
    - 401: Credenciales inválidas
    """
    
    # 1️⃣ Buscar el usuario en la base de datos
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # 2️⃣ Verificar que el email esté verificado
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email no verificado"
        )
    
    # 3️⃣ Autenticar con AWS Cognito
    try:
        auth_params = {
            "USERNAME": credentials.email,
            "PASSWORD": credentials.password,
            "SECRET_HASH": get_secret_hash(credentials.email),
        }
        
        response = cognito.initiate_auth(
            ClientId=settings.COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters=auth_params,
        )
        
        # Extraer tokens de la respuesta
        auth_result = response.get("AuthenticationResult")
        
        if not auth_result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )
        
        access_token = auth_result.get("AccessToken")
        id_token = auth_result.get("IdToken")
        refresh_token = auth_result.get("RefreshToken")
        expires_in = auth_result.get("ExpiresIn", 3600)
        
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        
        if error_code == "NotAuthorizedException":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )
        elif error_code == "UserNotFoundException":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        elif error_code == "UserNotConfirmedException":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no confirmado en Cognito"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de autenticación: {str(e)}"
            )
    
    # 4️⃣ Actualizar el last_login_at del usuario
    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    # 5️⃣ Retornar la información del usuario y los tokens
    return UserLoginResponse(
        user=user,
        access_token=access_token,
        id_token=id_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=expires_in
    )

