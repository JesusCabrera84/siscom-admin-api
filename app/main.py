from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME, version="1.0.0", docs_url="/docs", redoc_url="/redoc"
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {"status": "ok", "message": "SISCOM Admin API running"}


@app.get("/health")
def health_check():
    """Health check endpoint para Docker y monitoring"""
    return {"status": "healthy", "service": "siscom-admin-api"}
