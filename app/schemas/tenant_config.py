"""
Esquemas de `GET /tenant-config`.

Lo que este endpoint devuelve es **solo marca**: logo, colores, nombre. Nada de
módulos habilitados, límites ni identificadores internos.

No es una omisión por prudencia genérica, es la consecuencia de que el endpoint
sea público: se sirve sin autenticación para que el servidor de SvelteKit pueda
pintar la marca correcta en el primer HTML, antes de que exista una sesión. Todo
lo que se ponga aquí queda enumerable por cualquiera que pruebe hostnames.
"""

from typing import Any

from pydantic import BaseModel, Field


class TenantConfigResponse(BaseModel):
    """La configuración de marca de un hostname."""

    hostname: str = Field(
        description="El Host normalizado con el que se resolvió, en minúsculas y sin puerto"
    )
    brand_name: str = Field(description="Nombre visible de la marca")
    theme: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Tokens del tema publicado. Vacío mientras el partner no publique: "
            "el cliente debe caer a su tema por defecto, no fallar"
        ),
    )
    is_default: bool = Field(
        description=(
            "True cuando el Host no corresponde a ninguna marca verificada y se "
            "está sirviendo la configuración genérica"
        )
    )
