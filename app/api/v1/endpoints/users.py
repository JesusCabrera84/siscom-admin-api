from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from app.db.session import get_db
from app.api.deps import get_current_client_id, get_current_user_full
from app.models.user import User
from app.schemas.user import UserCreate, UserOut
from app.core.config import settings
from botocore.exceptions import ClientError

import boto3

router = APIRouter()


# ------------------------------------------
# Cognito client
# ------------------------------------------
cognito = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)


# ------------------------------------------
# Crear usuario
# ------------------------------------------
@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Crea un usuario en AWS Cognito y lo registra en la base de datos.
    """
    
    # 🔍 Verificar que el usuario no exista en la base de datos
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="El usuario con este correo electrónico ya existe en el sistema."
        )

    try:
        # 1️⃣ Crear usuario en Cognito
        cognito_resp = cognito.admin_create_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=user.email,
            UserAttributes=[
                {"Name": "email", "Value": user.email},
                {"Name": "name", "Value": user.name},
            ],
            DesiredDeliveryMediums=["EMAIL"],  # o "SMS"
            MessageAction="SUPPRESS",  # evita que Cognito envíe correo automático
        )

        # 2️⃣ Establecer contraseña proporcionada por el usuario
        cognito.admin_set_user_password(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=user.email,
            Password=user.password,
            Permanent=True,
        )

        cognito_sub = cognito_resp["User"]["Attributes"][0]["Value"]

    except ClientError as e:
        if e.response["Error"]["Code"] == "UsernameExistsException":
            raise HTTPException(
                status_code=400, detail="El usuario ya existe en Cognito."
            )
        raise HTTPException(status_code=500, detail=f"Error en Cognito: {e}")

    # 3️⃣ Guardar usuario en la base de datos
    new_user = User(
        email=user.email,
        full_name=user.name,  # Usamos el campo 'name' recibido
        cognito_sub=cognito_sub,
        is_master=user.is_master,
        client_id=user.client_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/", response_model=List[UserOut])
def list_users(
    client_id: UUID = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    """
    Lista todos los usuarios del cliente autenticado.
    """
    users = db.query(User).filter(User.client_id == client_id).all()
    return users


@router.get("/me", response_model=UserOut)
def get_current_user_info(
    current_user: User = Depends(get_current_user_full),
):
    """
    Obtiene la información del usuario actualmente autenticado.
    """
    return current_user
