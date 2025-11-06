.PHONY: help install lint format test build run stop clean deploy-test

help:  ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Instala las dependencias
	pip install -r requirements.txt

lint:  ## Ejecuta el linter (Ruff)
	ruff check app/

format:  ## Formatea el código con Black
	black app/

format-check:  ## Verifica el formato sin modificar archivos
	black --check app/

test:  ## Ejecuta los tests
	pytest tests/ -v

test-cov:  ## Ejecuta los tests con coverage
	pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

build:  ## Construye la imagen Docker
	docker build -t siscom-admin-api:latest .

run:  ## Ejecuta el contenedor localmente
	docker-compose up -d

run-dev:  ## Ejecuta en modo desarrollo con hot-reload
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8100

stop:  ## Detiene los contenedores
	docker-compose down

logs:  ## Muestra los logs del contenedor
	docker-compose logs -f api

clean:  ## Limpia archivos temporales y caché
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage

deploy-test:  ## Prueba el deployment localmente
	docker-compose -f docker-compose.prod.yml up -d

deploy-test-logs:  ## Muestra los logs del deployment de prueba
	docker logs -f siscom-admin-api

deploy-test-stop:  ## Detiene el deployment de prueba
	docker-compose -f docker-compose.prod.yml down

health:  ## Verifica el health check
	@echo "Verificando health check..."
	@curl -f http://localhost:8100/health && echo "\n✅ Health check OK" || echo "\n❌ Health check FAILED"

shell:  ## Abre una shell en el contenedor
	docker exec -it siscom-admin-api /bin/bash

db-shell:  ## Abre una shell de PostgreSQL
	docker exec -it siscom-admin-db psql -U siscom -d siscom_admin

migrations-create:  ## Crea una nueva migración (usar: make migrations-create NAME="nombre_migracion")
	alembic revision --autogenerate -m "$(NAME)"

migrations-up:  ## Aplica todas las migraciones pendientes
	alembic upgrade head

migrations-down:  ## Revierte la última migración
	alembic downgrade -1

migrations-history:  ## Muestra el historial de migraciones
	alembic history

all-checks: format-check lint test  ## Ejecuta todas las verificaciones (formato, lint, tests)
	@echo "✅ Todas las verificaciones pasaron correctamente"

verify-github-config:  ## Verifica qué variables y secrets de GitHub faltan configurar
	./scripts/verify_github_config.sh

