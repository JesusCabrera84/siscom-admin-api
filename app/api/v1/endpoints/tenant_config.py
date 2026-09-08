"""
`GET /tenant-config` — qué marca corresponde al Host de la petición.

Es el endpoint que permite que un solo despliegue de Nexus se pinte con la marca
de cada partner (§7). Lo consume el `hooks.server.js` de nexus-web-page en cada
petición, antes de que exista sesión, para que el primer HTML salga ya con el
logo, los colores y el título correctos — y no con los de Geminis durante
200–800 ms, que es lo que se ve hoy y lo que además arruina el unfurl de
WhatsApp, donde el crawler no ejecuta JavaScript.

LA REGLA QUE MÁS ERRORES PREVIENE EN ESTAS PLATAFORMAS
======================================================
**El Host resuelve apariencia y NUNCA autoriza.** El tenant de marca y el tenant
de datos son cosas distintas: la marca la determina el dominio por el que entró
la petición; los datos, el subárbol del usuario autenticado. Que alguien mande
`Host: meromero.com` a mano no le da acceso a nada, porque por aquí no sale un
solo dato de cliente — ni siquiera el `account_id` de la marca.

Confundir ambas resoluciones es el bug clásico de estas arquitecturas, y por eso
este módulo no importa nada de autenticación: no hay dónde equivocarse.
"""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.tenancy import TenantBranding, TenantDomain
from app.schemas.tenant_config import TenantConfigResponse

router = APIRouter()

# Lo que se sirve cuando el Host no es de nadie: localhost, la IP del ALB, un
# dominio que aún no se ha verificado, o alguien probando hostnames.
MARCA_POR_DEFECTO = "Nexus"

# El navegador puede cachearlo un rato: cambia cuando el partner publica su
# tema, que es una acción manual y poco frecuente. Corto de todos modos, para
# que publicar se note sin tener que purgar nada.
CACHE_SEGUNDOS = 60


def normalizar_host(host: str | None) -> str | None:
    """
    Deja el `Host` como está guardado en `tenant_domains`, o `None` si no puede.

    El Host llega en la caja que mande el cliente y puede traer puerto, punto
    final o mayúsculas. La columna es minúsculas por restricción de la base
    justamente para que la búsqueda sea una igualdad indexable.

    Devuelve `None` —y no una cadena vacía ni el valor crudo— cuando el Host no
    sirve: quien llama tiene que decidir explícitamente qué hacer con eso, en
    lugar de acabar consultando por "" y encontrando lo que sea.
    """
    if not host:
        return None
    host = host.strip().lower().rstrip(".")
    # IPv6 entre corchetes: [::1]:8000
    if host.startswith("["):
        cierre = host.find("]")
        if cierre == -1:
            return None
        host = host[: cierre + 1]
    elif ":" in host:
        host = host.split(":", 1)[0]
    if not host or len(host) > 253:
        return None
    return host


@router.get(
    "/tenant-config",
    response_model=TenantConfigResponse,
    summary="Configuración de marca del Host de la petición",
)
def get_tenant_config(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TenantConfigResponse:
    """
    Devuelve la marca que corresponde al `Host` de esta petición.

    **Público y sin autenticación**, por diseño: hace falta antes de que exista
    sesión. Devuelve únicamente datos de marca.

    Un Host desconocido **no es un error**: responde 200 con la configuración
    genérica y `is_default: true`. Un 404 obligaría a cada cliente a tratar el
    caso, y el fallo más probable —un dominio recién dado de alta y todavía sin
    verificar— dejaría la aplicación sin pintar en vez de pintarla neutra.
    """
    response.headers["Cache-Control"] = f"public, max-age={CACHE_SEGUNDOS}"
    # El contenido depende del Host: sin esto, una caché intermedia serviría la
    # marca de un partner a otro.
    response.headers["Vary"] = "Host"

    hostname = normalizar_host(request.headers.get("host"))
    if hostname is None:
        return TenantConfigResponse(
            hostname="", brand_name=MARCA_POR_DEFECTO, theme={}, is_default=True
        )

    dominio = (
        db.query(TenantDomain)
        .filter(
            TenantDomain.hostname == hostname,
            # Solo verificado: un dominio en PENDING lo puede reclamar
            # cualquiera hasta que demuestre control por DNS, y servir su marca
            # antes de eso permitiría suplantar a un partner con solo apuntar
            # un CNAME.
            TenantDomain.status == "VERIFIED",
        )
        .first()
    )

    if dominio is None:
        return TenantConfigResponse(
            hostname=hostname,
            brand_name=MARCA_POR_DEFECTO,
            theme={},
            is_default=True,
        )

    branding = (
        db.query(TenantBranding)
        .filter(TenantBranding.account_id == dominio.account_id)
        .first()
    )

    return TenantConfigResponse(
        hostname=hostname,
        brand_name=(
            branding.brand_name
            if branding and branding.brand_name
            else MARCA_POR_DEFECTO
        ),
        # `published`, nunca `draft`: el borrador es lo que el partner está
        # editando y no ha publicado.
        theme=(branding.published if branding else {}) or {},
        is_default=False,
    )
