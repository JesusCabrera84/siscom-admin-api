from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.token_confirmacion import TokenConfirmacion, TokenType
from app.schemas.user import (
    UserLogin, 
    UserLoginResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse
)
from app.core.config import settings
from botocore.exceptions import ClientError
import hmac
import hashlib
import base64
import boto3
import uuid

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
            # Puede ser que requiera un challenge (ej: cambio de contraseña)
            challenge_name = response.get("ChallengeName")
            if challenge_name:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Se requiere completar el challenge: {challenge_name}"
                )
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
        error_message = e.response["Error"].get("Message", str(e))
        
        # Log para debugging (en producción usar logger apropiado)
        print(f"[AUTH ERROR] Code: {error_code}, Message: {error_message}, Email: {credentials.email}")
        
        if error_code == "NotAuthorizedException":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Credenciales inválidas. {error_message}"
            )
        elif error_code == "UserNotFoundException":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado en Cognito"
            )
        elif error_code == "UserNotConfirmedException":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no confirmado en Cognito"
            )
        elif error_code == "InvalidParameterException":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de configuración: {error_message}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de autenticación [{error_code}]: {error_message}"
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


# ------------------------------------------
# Forgot Password - Solicitud de recuperación de contraseña
# ------------------------------------------
@router.post("/forgot-password", response_model=ForgotPasswordResponse, status_code=status.HTTP_200_OK)
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Solicita la recuperación de contraseña para un usuario.
    
    Proceso:
    1. Verifica que el usuario exista en la base de datos
    2. Genera un token único (UUID)
    3. Guarda el token en la tabla tokens_confirmacion con tipo PASSWORD_RESET
    4. TODO: Envía un correo electrónico con el token (pendiente de implementar)
    5. Retorna un mensaje de éxito (siempre, incluso si el email no existe, por seguridad)
    
    Notas de seguridad:
    - Siempre retorna el mismo mensaje, independientemente de si el usuario existe o no,
      para evitar enumerar usuarios válidos del sistema.
    """
    
    # 1️⃣ Buscar el usuario en la base de datos
    user = db.query(User).filter(User.email == request.email).first()
    
    if user:
        # 2️⃣ Generar un token único
        reset_token = str(uuid.uuid4())
        
        # 3️⃣ Guardar el token en la base de datos
        token_record = TokenConfirmacion(
            token=reset_token,
            type=TokenType.PASSWORD_RESET,
            user_id=user.id,
            email=user.email,
            expires_at=datetime.utcnow() + timedelta(hours=1),  # Expira en 1 hora
            used=False
        )
        db.add(token_record)
        db.commit()
        
        # 4️⃣ TODO: Enviar correo electrónico con el token
        # Aquí irá la lógica de envío de correo cuando esté implementado el servicio
        # Por ahora, solo registramos en logs (en producción usar un logger apropiado)
        print(f"[PASSWORD RESET] Token generado para {user.email}: {reset_token}")
        print("[PASSWORD RESET] El token expira en 1 hora")
        print("[PASSWORD RESET] TODO: Enviar correo electrónico con el token")
    else:
        # Por seguridad, no revelar que el usuario no existe
        print(f"[PASSWORD RESET] Intento de recuperación para email no registrado: {request.email}")
    
    # 5️⃣ Siempre retornar el mismo mensaje de éxito (por seguridad)
    return ForgotPasswordResponse(
        message="Se ha enviado un código de verificación al correo registrado."
    )


# ------------------------------------------
# Reset Password - Restablecimiento de contraseña con token
# ------------------------------------------
@router.post("/reset-password", response_model=ResetPasswordResponse, status_code=status.HTTP_200_OK)
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Restablece la contraseña de un usuario utilizando un token de recuperación.
    
    Proceso:
    1. Busca y valida el token en la base de datos
    2. Verifica que el token no haya expirado
    3. Verifica que el token no haya sido usado
    4. Busca el usuario asociado al token
    5. Actualiza la contraseña en AWS Cognito usando AdminSetUserPassword
    6. Marca el token como usado
    7. Retorna un mensaje de éxito
    
    Códigos de error:
    - 400: Token inválido, expirado o ya usado
    - 404: Usuario no encontrado
    - 500: Error al actualizar la contraseña en Cognito
    """
    
    # 1️⃣ Buscar el token en la base de datos
    token_record = db.query(TokenConfirmacion).filter(
        TokenConfirmacion.token == request.token,
        TokenConfirmacion.type == TokenType.PASSWORD_RESET
    ).first()
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de recuperación inválido"
        )
    
    # 2️⃣ Verificar que el token no haya expirado
    if token_record.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El token de recuperación ha expirado. Por favor, solicita uno nuevo."
        )
    
    # 3️⃣ Verificar que el token no haya sido usado
    if token_record.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este token de recuperación ya ha sido utilizado"
        )
    
    # 4️⃣ Buscar el usuario asociado al token
    user = db.query(User).filter(User.id == token_record.user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # 5️⃣ Actualizar la contraseña en AWS Cognito
    try:
        cognito.admin_set_user_password(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=user.email,
            Password=request.new_password,
            Permanent=True  # La contraseña es permanente, no temporal
        )
        
        print(f"[PASSWORD RESET] Contraseña actualizada exitosamente para {user.email}")
        
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"].get("Message", str(e))
        
        print(f"[PASSWORD RESET ERROR] Code: {error_code}, Message: {error_message}, Email: {user.email}")
        
        if error_code == "UserNotFoundException":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado en Cognito"
            )
        elif error_code == "InvalidPasswordException":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Contraseña inválida: {error_message}"
            )
        elif error_code == "InvalidParameterException":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parámetro inválido: {error_message}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al actualizar la contraseña [{error_code}]: {error_message}"
            )
    
    # 6️⃣ Marcar el token como usado
    token_record.used = True
    db.commit()
    
    # 7️⃣ Retornar mensaje de éxito
    return ResetPasswordResponse(
        message="Contraseña restablecida exitosamente. Ahora puede iniciar sesión con su nueva contraseña."
    )

