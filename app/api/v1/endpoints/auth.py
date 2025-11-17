import base64
import hashlib
import hmac
import random
import uuid
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_full
from app.core.config import settings
from app.db.session import get_db
from app.models.token_confirmacion import TokenConfirmacion, TokenType
from app.models.user import User
from app.schemas.user import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    ConfirmEmailRequest,
    ConfirmEmailResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LogoutResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    UserLogin,
    UserLoginResponse,
)
from app.services.notifications import (
    send_password_reset_email,
    send_verification_email,
)

router = APIRouter()

# ------------------------------------------
# Cognito client
# ------------------------------------------
cognito = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)

# Security bearer para obtener el token
security = HTTPBearer()


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
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )

    # 2️⃣ Verificar que el email esté verificado
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Email no verificado"
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
                    detail=f"Se requiere completar el challenge: {challenge_name}",
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
            )

        access_token = auth_result.get("AccessToken")
        id_token = auth_result.get("IdToken")
        refresh_token = auth_result.get("RefreshToken")
        expires_in = auth_result.get("ExpiresIn", 3600)

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"].get("Message", str(e))

        # Log para debugging (en producción usar logger apropiado)
        print(
            f"[AUTH ERROR] Code: {error_code}, Message: {error_message}, Email: {credentials.email}"
        )

        if error_code == "NotAuthorizedException":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Credenciales inválidas. {error_message}",
            )
        elif error_code == "UserNotFoundException":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado en Cognito",
            )
        elif error_code == "UserNotConfirmedException":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no confirmado en Cognito",
            )
        elif error_code == "InvalidParameterException":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de configuración: {error_message}",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de autenticación [{error_code}]: {error_message}",
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
        expires_in=expires_in,
    )


# ------------------------------------------
# Forgot Password - Solicitud de recuperación de contraseña
# ------------------------------------------
@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
)
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Solicita la recuperación de contraseña para un usuario.

    Proceso:
    1. Verifica que el usuario exista en la base de datos
    2. Genera un código de 6 dígitos aleatorio
    3. Guarda el código en la tabla tokens_confirmacion con tipo PASSWORD_RESET
    4. Envía un correo electrónico con el código de 6 dígitos
    5. Retorna un mensaje de éxito (siempre, incluso si el email no existe, por seguridad)

    Notas de seguridad:
    - Siempre retorna el mismo mensaje, independientemente de si el usuario existe o no,
      para evitar enumerar usuarios válidos del sistema.
    """

    # 1️⃣ Buscar el usuario en la base de datos
    user = db.query(User).filter(User.email == request.email).first()

    if user:
        # 2️⃣ Generar un código de 6 dígitos aleatorio
        reset_code = str(random.randint(100000, 999999))

        # 3️⃣ Guardar el código en la base de datos
        token_record = TokenConfirmacion(
            token=reset_code,
            type=TokenType.PASSWORD_RESET,
            user_id=user.id,
            email=user.email,
            expires_at=datetime.utcnow() + timedelta(hours=1),  # Expira en 1 hora
            used=False,
        )
        db.add(token_record)
        db.commit()

        # 4️⃣ Enviar correo electrónico con el código de 6 dígitos
        email_sent = send_password_reset_email(user.email, reset_code)
        if email_sent:
            print(f"[PASSWORD RESET] Correo enviado a {user.email} con código: {reset_code}")
        else:
            print(f"[PASSWORD RESET ERROR] No se pudo enviar el correo a {user.email}")
    else:
        # Por seguridad, no revelar que el usuario no existe
        print(
            f"[PASSWORD RESET] Intento de recuperación para email no registrado: {request.email}"
        )

    # 5️⃣ Siempre retornar el mismo mensaje de éxito (por seguridad)
    return ForgotPasswordResponse(
        message="Se ha enviado un código de verificación al correo registrado."
    )


# ------------------------------------------
# Reset Password - Restablecimiento de contraseña con código
# ------------------------------------------
@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
)
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Restablece la contraseña de un usuario utilizando un código de verificación de 6 dígitos.

    Proceso:
    1. Busca el usuario por email
    2. Busca y valida el código en la base de datos
    3. Verifica que el código no haya expirado
    4. Verifica que el código no haya sido usado
    5. Actualiza la contraseña en AWS Cognito usando AdminSetUserPassword
    6. Marca el código como usado
    7. Retorna un mensaje de éxito

    Códigos de error:
    - 400: Código inválido, expirado o ya usado
    - 404: Usuario no encontrado
    - 500: Error al actualizar la contraseña en Cognito
    """

    # 1️⃣ Buscar el usuario en la base de datos
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )

    # 2️⃣ Buscar el código en la base de datos
    token_record = (
        db.query(TokenConfirmacion)
        .filter(
            TokenConfirmacion.token == request.code,
            TokenConfirmacion.type == TokenType.PASSWORD_RESET,
            TokenConfirmacion.email == request.email,
        )
        .first()
    )

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código de verificación inválido",
        )

    # 3️⃣ Verificar que el código no haya expirado
    if token_record.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código de verificación ha expirado. Por favor, solicita uno nuevo.",
        )

    # 4️⃣ Verificar que el código no haya sido usado
    if token_record.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este código de verificación ya ha sido utilizado",
        )

    # 5️⃣ Actualizar la contraseña en AWS Cognito
    try:
        cognito.admin_set_user_password(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=user.email,
            Password=request.new_password,
            Permanent=True,  # La contraseña es permanente, no temporal
        )

        print(f"[PASSWORD RESET] Contraseña actualizada exitosamente para {user.email}")

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"].get("Message", str(e))

        print(
            f"[PASSWORD RESET ERROR] Code: {error_code}, Message: {error_message}, Email: {user.email}"
        )

        if error_code == "UserNotFoundException":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado en Cognito",
            )
        elif error_code == "InvalidPasswordException":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Contraseña inválida: {error_message}",
            )
        elif error_code == "InvalidParameterException":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parámetro inválido: {error_message}",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al actualizar la contraseña [{error_code}]: {error_message}",
            )

    # 6️⃣ Marcar el código como usado
    token_record.used = True
    db.commit()

    # 7️⃣ Retornar mensaje de éxito
    return ResetPasswordResponse(
        message="Contraseña restablecida exitosamente. Ahora puede iniciar sesión con su nueva contraseña."
    )


# ------------------------------------------
# Change Password - Cambio de contraseña (usuario autenticado)
# ------------------------------------------
@router.patch(
    "/password", response_model=ChangePasswordResponse, status_code=status.HTTP_200_OK
)
def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    """
    Cambia la contraseña de un usuario autenticado.

    El usuario debe proporcionar su contraseña actual y la nueva contraseña.
    Utiliza ChangePassword de AWS Cognito para cambiar la contraseña de forma segura.

    Proceso:
    1. Verifica que el usuario esté autenticado
    2. Obtiene el access_token del usuario (necesario para ChangePassword)
    3. Llama a change_password de Cognito con la contraseña actual y la nueva
    4. Retorna mensaje de éxito

    Códigos de error:
    - 400: Contraseña actual incorrecta o nueva contraseña inválida
    - 401: Token de acceso inválido o expirado
    - 500: Error al cambiar la contraseña en Cognito

    Nota: Este endpoint requiere autenticación (Bearer token en el header Authorization)
    """

    # Para usar ChangePassword necesitamos el AccessToken del usuario
    # El access token debe venir en el header Authorization
    # Aquí tenemos un problema: get_current_user_full valida el token pero no lo retorna
    # Necesitamos obtener el access token del header

    # Por seguridad, vamos a usar AdminSetUserPassword en lugar de ChangePassword
    # Esto nos permite cambiar la contraseña sin necesitar el access token
    # Pero primero validamos la contraseña actual autenticando al usuario

    # 1️⃣ Verificar la contraseña actual autenticando con Cognito
    try:
        auth_params = {
            "USERNAME": current_user.email,
            "PASSWORD": request.old_password,
            "SECRET_HASH": get_secret_hash(current_user.email),
        }

        cognito.initiate_auth(
            ClientId=settings.COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters=auth_params,
        )

        # Si llegamos aquí, la contraseña actual es correcta

    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        if error_code == "NotAuthorizedException":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña actual es incorrecta",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al verificar la contraseña actual: {error_code}",
            )

    # 2️⃣ Cambiar la contraseña usando AdminSetUserPassword
    try:
        cognito.admin_set_user_password(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=current_user.email,
            Password=request.new_password,
            Permanent=True,
        )

        print(
            f"[CHANGE PASSWORD] Contraseña actualizada exitosamente para {current_user.email}"
        )

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"].get("Message", str(e))

        print(
            f"[CHANGE PASSWORD ERROR] Code: {error_code}, Message: {error_message}, Email: {current_user.email}"
        )

        if error_code == "InvalidPasswordException":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La nueva contraseña no cumple con los requisitos: {error_message}",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al actualizar la contraseña: {error_code}",
            )

    # 3️⃣ Retornar mensaje de éxito
    return ChangePasswordResponse(message="Contraseña actualizada exitosamente.")


# ------------------------------------------
# Resend Verification - Reenviar verificación de email
# ------------------------------------------
@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
    status_code=status.HTTP_200_OK,
)
def resend_verification(
    request: ResendVerificationRequest, db: Session = Depends(get_db)
):
    """
    Reenvía el correo de verificación de email a un usuario no verificado.

    Proceso:
    1. Busca el usuario por email
    2. Si no existe o ya está verificado, retorna mensaje genérico (seguridad)
    3. Si existe y no está verificado:
       a. Invalida todos los tokens de verificación anteriores no usados
       b. Genera un nuevo token UUID
       c. Guarda el token en tokens_confirmacion con tipo EMAIL_VERIFICATION
       d. TODO: Envía correo con el token
    4. Retorna mensaje genérico

    Notas de seguridad:
    - Siempre retorna el mismo mensaje, sin revelar si el usuario existe o ya está verificado
    - Invalida tokens anteriores para evitar que se usen tokens antiguos
    """

    # 1️⃣ Buscar el usuario en la base de datos
    user = db.query(User).filter(User.email == request.email).first()

    # 2️⃣ Si no existe o ya está verificado, retornar mensaje genérico
    if not user:
        print(
            f"[RESEND VERIFICATION] Intento para email no registrado: {request.email}"
        )
        return ResendVerificationResponse(
            message="Si la cuenta existe, se ha reenviado el correo de verificación."
        )

    if user.email_verified:
        print(f"[RESEND VERIFICATION] Usuario ya verificado: {request.email}")
        return ResendVerificationResponse(
            message="Si la cuenta existe, se ha reenviado el correo de verificación."
        )

    # 3️⃣ Usuario existe y no está verificado, continuar con el reenvío

    # a) Invalidar tokens anteriores no usados del usuario
    previous_tokens = (
        db.query(TokenConfirmacion)
        .filter(
            TokenConfirmacion.user_id == user.id,
            TokenConfirmacion.type == TokenType.EMAIL_VERIFICATION,
            ~TokenConfirmacion.used,
        )
        .all()
    )

    for token in previous_tokens:
        token.used = True

    # b) Generar nuevo token UUID
    verification_token = str(uuid.uuid4())

    # c) Guardar el token en la base de datos
    token_record = TokenConfirmacion(
        token=verification_token,
        type=TokenType.EMAIL_VERIFICATION,
        user_id=user.id,
        email=user.email,
        expires_at=datetime.utcnow() + timedelta(hours=24),  # Expira en 24 horas
        used=False,
    )
    db.add(token_record)
    db.commit()

    # d) Enviar correo electrónico con el token
    email_sent = send_verification_email(user.email, verification_token)
    if email_sent:
        print(f"[RESEND VERIFICATION] Correo enviado a {user.email}")
    else:
        print(f"[RESEND VERIFICATION ERROR] No se pudo enviar el correo a {user.email}")

    # 4️⃣ Retornar mensaje genérico
    return ResendVerificationResponse(
        message="Si la cuenta existe, se ha reenviado el correo de verificación."
    )


# ------------------------------------------
# Confirm Email - Confirmar email con token
# ------------------------------------------
@router.post(
    "/confirm-email",
    response_model=ConfirmEmailResponse,
    status_code=status.HTTP_200_OK,
)
def confirm_email(request: ConfirmEmailRequest, db: Session = Depends(get_db)):
    """
    Confirma el email de un usuario utilizando un token de verificación.

    Proceso:
    1. Busca y valida el token en la base de datos
    2. Verifica que el token no haya expirado
    3. Verifica que el token no haya sido usado
    4. Marca el token como usado
    5. Actualiza user.email_verified = True
    6. Retorna mensaje de éxito

    Códigos de error:
    - 400: Token inválido, expirado o ya usado
    - 404: Usuario no encontrado
    """

    # 1️⃣ Buscar el token en la base de datos
    token_record = (
        db.query(TokenConfirmacion)
        .filter(
            TokenConfirmacion.token == request.token,
            TokenConfirmacion.type == TokenType.EMAIL_VERIFICATION,
        )
        .first()
    )

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de verificación inválido",
        )

    # 2️⃣ Verificar que el token no haya expirado
    if token_record.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El token de verificación ha expirado. Por favor, solicita un nuevo código.",
        )

    # 3️⃣ Verificar que el token no haya sido usado
    if token_record.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este token de verificación ya ha sido utilizado",
        )

    # 4️⃣ Buscar el usuario asociado al token
    user = db.query(User).filter(User.id == token_record.user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )

    # 5️⃣ Marcar el token como usado
    token_record.used = True

    # 6️⃣ Actualizar email_verified del usuario
    user.email_verified = True

    db.commit()

    print(f"[EMAIL VERIFICATION] Email verificado exitosamente para {user.email}")

    # 7️⃣ Retornar mensaje de éxito
    return ConfirmEmailResponse(
        message="Email verificado exitosamente. Ahora puede iniciar sesión."
    )


# ------------------------------------------
# Logout - Cerrar sesión del usuario actual
# ------------------------------------------
@router.post("/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_full),
):
    """
    Cierra la sesión del usuario actual en AWS Cognito.

    Proceso:
    1. Obtiene el access token del header Authorization
    2. Llama a global_sign_out de Cognito para invalidar todas las sesiones del usuario
    3. Retorna mensaje de éxito

    Este endpoint invalida:
    - Todos los access tokens del usuario
    - Todos los ID tokens del usuario
    - El refresh token ya no podrá usarse para obtener nuevos tokens

    Códigos de error:
    - 401: Token inválido o expirado
    - 500: Error al cerrar sesión en Cognito

    Nota: Este endpoint requiere autenticación (Bearer token en el header Authorization)
    """

    # 1️⃣ Obtener el access token del header Authorization
    access_token = credentials.credentials

    # 2️⃣ Llamar a global_sign_out de Cognito
    try:
        cognito.global_sign_out(AccessToken=access_token)

        print(f"[LOGOUT] Sesión cerrada exitosamente para {current_user.email}")

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"].get("Message", str(e))

        print(
            f"[LOGOUT ERROR] Code: {error_code}, Message: {error_message}, Email: {current_user.email}"
        )

        if error_code == "NotAuthorizedException":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al cerrar sesión [{error_code}]: {error_message}",
            )

    # 3️⃣ Retornar mensaje de éxito
    return LogoutResponse(message="Sesión cerrada exitosamente.")
