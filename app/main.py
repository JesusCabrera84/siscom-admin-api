import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware  # type: ignore[attr-defined]
from fastapi.responses import JSONResponse

from app.api.deps import (
    close_geofences_kafka_producer,
    close_mobility_kafka_producer,
    close_rules_kafka_producer,
    close_unit_devices_kafka_producer,
    close_user_devices_kafka_producer,
    close_user_units_kafka_producer,
)
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.services.health import (
    check_database,
    check_kafka_accessibility,
    get_schema_revision,
)
from app.startup import print_startup_banner

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup: verifica accesibilidad de servicios externos
    print_startup_banner()
    check_kafka_accessibility()
    from app.services.gateways import initialize_gateways

    initialize_gateways()

    yield

    # Shutdown: cierra recursos compartidos
    close_rules_kafka_producer()
    close_geofences_kafka_producer()
    close_user_devices_kafka_producer()
    close_unit_devices_kafka_producer()
    close_user_units_kafka_producer()
    close_mobility_kafka_producer()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# Middleware para limitar el tamaño del body y prevenir ataques DoS
@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    """
    Middleware para limitar el tamaño del body de las peticiones.
    Previene ataques de denegación de servicio (DoS) con payloads grandes.

    Límite: 50KB (50,000 bytes)
    """
    max_body_size = 50_000  # 50KB

    if "/stripe/webhook/" in request.url.path:
        return await call_next(request)

    if request.headers.get("content-length"):
        content_length = int(request.headers["content-length"])
        if content_length > max_body_size:
            return Response(
                content="Payload demasiado grande. Máximo permitido: 50KB",
                status_code=413,
                media_type="text/plain",
            )

    return await call_next(request)


@app.middleware("http")
async def unhandled_exception_to_json(request: Request, call_next):
    """
    Captura excepciones no manejadas por dentro de CORSMiddleware.
    Starlette pone ServerErrorMiddleware por fuera de CORS; un 500 crudo
    llega al browser sin Access-Control-Allow-Origin y se reporta como CORS.
    """
    try:
        return await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled exception on %s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )


app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {"status": "ok", "message": "SISCOM Admin API running"}


@app.get("/health")
def health_check(response: Response):
    """Health check para Docker, el ALB y el bucle de espera del despliegue.

    Consulta la base. Si no responde, devuelve 503 y el contenedor pasa a
    unhealthy: es la senal que el despliegue necesita para abortar en vez de
    declarar exito sobre una base inservible.
    """
    db_ok, db_error = check_database()

    payload = {
        "status": "healthy" if db_ok else "unhealthy",
        "service": "siscom-admin-api",
        "database": "ok" if db_ok else "unreachable",
        # None significa que alembic nunca gestiono este esquema.
        "schema_revision": get_schema_revision() if db_ok else None,
    }
    if not db_ok:
        response.status_code = 503
        payload["detail"] = db_error

    return payload
