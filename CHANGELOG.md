# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Engineering foundation (PR-1): blocking CI (`quality` + `security` jobs)
- Soft foundations (PR-2): `.devcontainer/`, `docs/security/threat-model.md`, GitHub issue templates, process ADRs (002, 003)
- Quality gates (PR-3): `CODEOWNERS`, `dependabot.yml`, `docs/GOVERNANCE.md`, OSV-Scanner, `osv-scanner.toml`
- Coverage floor (65% on `app/`) via `pyproject.toml`
- `scripts/gitleaks-scan.sh`, `scripts/pip-audit-scan.sh`, `scripts/osv-scan.sh`, `scripts/setup.sh`
- `.pre-commit-config.yaml` (Ruff, Black, hygiene hooks)
- `AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`, `docs/RELEASE.md`
- `.editorconfig`, `.python-version`, `.gitleaks.toml`
- GitHub pull request template
- `make validate`, `make scan-secrets`, `make audit-deps`
- Docs: `docs/api/teams.md` documenta los endpoints de teams, miembros, reglas de visibilidad, invitaciones, emergencias y snapshots internos ya presentes en `develop`
- Docs: `docs/api/INDEX.md` incorpora teams y el set completo de `/mobility/devices` y `/mobility/locations` al índice y al mapa de rutas

### Changed

- Test harness: SQLite keeps JSONB operators (`.astext`) via compile hook; pytest env defaults in `conftest` for runs without `.env`
- CI: Ruff, Black, pytest, and Docker build are blocking (removed `|| true`)
- Deploy workflow: quality gates delegated to CI; deploy only builds and ships on tags
- Deploy workflow: `alembic upgrade head` corre en un contenedor efímero (misma red y `.env`) antes de levantar el contenedor nuevo
- Test harness: session-scoped SQLite metadata patch, GAC auth in `authenticated_client`, telemetry/sims isolation fixes
- Minimum Python version raised to **3.12** (CI, Docker, Black/Ruff targets, docs)
- Dependency security bumps: `cryptography`, `idna`, `python-multipart`, `starlette`, `pyseto`
- Dependency security bumps: `cryptography` 48.0.1 → 50.0.0 (PYSEC-2026-3552/3553/3554), `kafka-python` 2.3.0 → 2.3.2 (PYSEC-2026-2190/2191), `pyasn1` 0.6.3 → 0.6.4 (PYSEC-2026-3455/3456/3457)
- `scripts/pip-audit-scan.sh` ignora `PYSEC-2026-1325` (`ecdsa`, transitivo vía `python-jose`): no hay versión corregida y no es alcanzable — solo verificamos JWT con RS256. Mismo riesgo ya aceptado en `osv-scanner.toml`
- Gitleaks scans working tree only (`--no-git`); doc placeholders sanitized

### Fixed

- Auth: las peticiones sin header `Authorization` (o con esquema distinto de Bearer) responden `401` con `WWW-Authenticate: Bearer` en lugar del `403` por defecto de `HTTPBearer`. Los clientes iOS/Android disparan el refresh de token solo con `401`
- `billing.py`: query devices by `device_id` (not legacy `Device.id`) — 8 billing unit tests re-enabled
- User-commands list/sync tests re-enabled on SQLite JSONB paths (2 tests)

### Notes

- 24 tests still skipped (device status flow, orders invoice fixture, legacy DeviceService API, device activation) — follow-up PRs

### Security

- Gitleaks + Semgrep + pip-audit + OSV-Scanner in CI `security` job
- `POST /api/v1/mobility/locations` y `/batch` exigen JWT y validan que el `device_id` pertenezca a un dispositivo activo del usuario autenticado. Antes aceptaban cualquier `device_id` sin autenticación, lo que permitía inyectar ubicaciones de terceros al tópico de Kafka

## [1.23.1] - 2026-08-08

### Fixed

- `ALLOWED_ORIGINS` en formato CSV ya no rompe el arranque. El campo estaba declarado como `list[str]`, así que `EnvSettingsSource` corría `json.loads` sobre el valor crudo antes de que se ejecutara el validador `parse_allowed_origins`: cualquier CSV —o una cadena vacía— reventaba con `SettingsError` y tiraba el contenedor. Ahora se anota como `Annotated[list[str], NoDecode]` y el validador existente recibe el string sin tocar (PR #38)
- Guía de deploy: las variables de GitHub viven en el environment `test`, no a nivel repositorio. Una variable creada en el scope equivocado se ignora en silencio, porque las de environment tienen precedencia (PR #38)

### Added

- `tests/test_config.py`: cobertura del parseo de `ALLOWED_ORIGINS` desde variables de entorno — CSV, JSON array, espacios, slash final, duplicados, valores en blanco, JSON malformado y el default (PR #38)
- Troubleshooting del `SettingsError` de `ALLOWED_ORIGINS` y del scope de variables en `docs/guides/github-actions-deployment.md` (PR #38)

### Changed

- `pydantic-settings` 2.1.0 → 2.15.0. `NoDecode` se agregó en 2.3.0; el pin previo era de diciembre 2023, 14 minors atrás de `pydantic==2.12.5` (PR #38)

## [1.23.2] - 2026-08-09

### Fixed

- `KAFKA_TEAM_RULES_TOPIC` ya llega al contenedor. La variable estaba declarada en `app/core/config.py` y `TeamRulesKafkaProducer` la leía vía `settings`, pero no se propagaba en ningún compose ni en `deploy.yml`: el topic de teams era en la práctica un hardcode y no se podía cambiar sin reconstruir la imagen, a diferencia de los otros cuatro topics de Kafka. Se añade a `.env.example`, ambos compose y a las tres apariciones de `deploy.yml` —bloque `env`, lista `envs:` del `ssh-action` y el heredoc que escribe el `.env` remoto— (PR #40)
