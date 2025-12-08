from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================
# Device Schemas
# ============================================

DeviceStatus = Literal[
    "nuevo", "preparado", "enviado", "entregado", "asignado", "devuelto", "inactivo"
]


class DeviceBase(BaseModel):
    """Schema base para dispositivos"""

    brand: Optional[str] = Field(
        None, max_length=100, description="Marca del dispositivo"
    )
    model: Optional[str] = Field(
        None, max_length=100, description="Modelo del dispositivo"
    )
    firmware_version: Optional[str] = Field(None, description="Versión de firmware")
    notes: Optional[str] = Field(None, description="Notas administrativas")


class DeviceCreate(BaseModel):
    """Schema para crear un nuevo dispositivo (admin/inventario)"""

    device_id: str = Field(
        ...,
        min_length=10,
        max_length=50,
        description="Identificador único del dispositivo (IMEI, serial, etc)",
    )
    brand: str = Field(
        ..., min_length=1, max_length=100, description="Marca del dispositivo"
    )
    model: str = Field(
        ..., min_length=1, max_length=100, description="Modelo del dispositivo"
    )
    firmware_version: Optional[str] = Field(None, description="Versión de firmware")
    notes: Optional[str] = Field(None, description="Notas administrativas")
    iccid: Optional[str] = Field(
        None,
        min_length=18,
        max_length=22,
        description="ICCID de la tarjeta SIM (opcional)",
    )


class DeviceUpdate(BaseModel):
    """Schema para actualizar información básica del dispositivo"""

    brand: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    firmware_version: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)
    iccid: Optional[str] = Field(
        None,
        min_length=18,
        max_length=22,
        description="ICCID de la tarjeta SIM",
    )


class DeviceStatusUpdate(BaseModel):
    """Schema para actualizar el estado de un dispositivo"""

    new_status: DeviceStatus = Field(..., description="Nuevo estado del dispositivo")
    client_id: Optional[UUID] = Field(
        None, description="ID del cliente (requerido para 'preparado')"
    )
    unit_id: Optional[UUID] = Field(
        None, description="ID de la unidad (requerido para 'asignado')"
    )
    notes: Optional[str] = Field(None, description="Notas sobre el cambio de estado")


class DeviceOut(BaseModel):
    """Schema de salida para dispositivos"""

    device_id: str
    brand: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None
    client_id: Optional[UUID] = None
    status: str
    last_comm_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    last_assignment_at: Optional[datetime] = None
    notes: Optional[str] = None
    iccid: Optional[str] = Field(None, description="ICCID de la tarjeta SIM asignada")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "device_id": "864537040123456",
                "brand": "Suntech",
                "model": "ST300",
                "firmware_version": "1.0.17",
                "client_id": "d1e92a7a-bab3-4d87-8219-9cb8471a0c2b",
                "status": "asignado",
                "last_comm_at": "2025-01-15T10:30:00Z",
                "created_at": "2025-11-01T10:20:00Z",
                "updated_at": "2025-11-03T08:00:00Z",
                "last_assignment_at": "2025-11-03T08:00:00Z",
                "notes": "Instalado en unidad #45",
                "iccid": "89340123456789012345",
            }
        }


class DeviceWithProfileOut(DeviceOut):
    """Schema de salida para dispositivos con información del perfil de la unidad asignada"""

    # Información del perfil de la unidad (unit_profile)
    unit_id: Optional[UUID] = Field(None, description="ID de la unidad asignada")
    unit_name: Optional[str] = Field(None, description="Nombre de la unidad")
    profile_color: Optional[str] = Field(None, description="Color del vehículo/unidad")
    profile_icon_type: Optional[str] = Field(
        None, description="Tipo de ícono del vehículo/unidad"
    )
    profile_brand: Optional[str] = Field(None, description="Marca del vehículo/unidad")
    profile_model: Optional[str] = Field(None, description="Modelo del vehículo/unidad")
    profile_year: Optional[int] = Field(None, description="Año del vehículo/unidad")
    profile_serial: Optional[str] = Field(
        None, description="Número de serie del vehículo/unidad"
    )
    profile_description: Optional[str] = Field(
        None, description="Descripción del vehículo/unidad"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "device_id": "864537040123456",
                "brand": "Suntech",
                "model": "ST300",
                "firmware_version": "1.0.17",
                "client_id": "d1e92a7a-bab3-4d87-8219-9cb8471a0c2b",
                "status": "asignado",
                "last_comm_at": "2025-01-15T10:30:00Z",
                "created_at": "2025-11-01T10:20:00Z",
                "updated_at": "2025-11-03T08:00:00Z",
                "last_assignment_at": "2025-11-03T08:00:00Z",
                "notes": "Instalado en unidad #45",
                "iccid": "89340123456789012345",
                "unit_id": "abc12345-e89b-12d3-a456-426614174000",
                "unit_name": "Camión #45",
                "profile_color": "Rojo",
                "profile_icon_type": "truck",
                "profile_brand": "Ford",
                "profile_model": "F-350",
                "profile_year": 2020,
                "profile_serial": "1FDUF3GT5GED12345",
                "profile_description": "Camión de carga pesada",
            }
        }


# ============================================
# DeviceEvent Schemas
# ============================================

EventType = Literal[
    "creado",
    "preparado",
    "enviado",
    "entregado",
    "asignado",
    "devuelto",
    "firmware_actualizado",
    "nota",
    "estado_cambiado",
]


class DeviceEventBase(BaseModel):
    """Schema base para eventos de dispositivos"""

    event_type: EventType
    event_details: Optional[str] = None


class DeviceEventCreate(DeviceEventBase):
    """Schema para crear un evento de dispositivo"""

    device_id: str = Field(..., description="ID del dispositivo")
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    performed_by: Optional[UUID] = None


class DeviceEventOut(BaseModel):
    """Schema de salida para eventos de dispositivos"""

    id: UUID
    device_id: str
    event_type: str
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    performed_by: Optional[UUID] = None
    event_details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "423e4567-e89b-12d3-a456-426614174000",
                "device_id": "123456789012345",
                "event_type": "asignado",
                "old_status": "entregado",
                "new_status": "asignado",
                "performed_by": "523e4567-e89b-12d3-a456-426614174000",
                "event_details": "Dispositivo asignado a unidad ABC-123",
                "created_at": "2024-01-12T14:20:00Z",
            }
        }


class UnitBase(BaseModel):
    name: str
    plate: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None


class UnitCreate(UnitBase):
    pass


class UnitOut(UnitBase):
    id: UUID
    client_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "323e4567-e89b-12d3-a456-426614174000",
                "client_id": "223e4567-e89b-12d3-a456-426614174000",
                "name": "Camión 01",
                "plate": "ABC-123-XY",
                "type": "Camión de carga",
                "description": "Camión para entregas locales",
                "created_at": "2024-01-10T08:00:00Z",
                "updated_at": "2024-01-10T08:00:00Z",
            }
        }
