from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "SISCOM Admin API"
    API_V1_STR: str = "/api/v1"

    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # AWS Credentials - Opcionales si usas IAM Role en EC2
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None

    # AWS Cognito - Requeridos
    COGNITO_REGION: str
    COGNITO_USER_POOL_ID: str
    COGNITO_CLIENT_ID: str
    COGNITO_CLIENT_SECRET: str
    DEFAULT_USER_PASSWORD: str = "TempPass123!"

    @field_validator("COGNITO_REGION")
    @classmethod
    def validate_cognito_region(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError(
                "COGNITO_REGION cannot be empty. "
                "Please set it in your environment variables or .env file. "
                "Example: us-east-1, us-west-2, etc."
            )
        return v.strip()

    class Config:
        env_file = ".env"


settings = Settings()
