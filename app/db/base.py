from sqlmodel import SQLModel

# Importar todos los modelos para que Alembic los detecte

# Base para Alembic
Base = SQLModel.metadata
