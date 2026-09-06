#!/usr/bin/env bash
#
# Postgres local para probar migraciones antes de tocar producción.
#
#   ./scripts/db-local.sh up          levanta el motor y espera a que acepte conexiones
#   ./scripts/db-local.sh down        lo apaga (conserva el volumen)
#   ./scripts/db-local.sh reset       lo destruye y lo vuelve a crear vacío
#   ./scripts/db-local.sh psql [...]  abre psql como superusuario
#   ./scripts/db-local.sh restore F   restaura un dump productivo (.sql o .dump)
#   ./scripts/db-local.sh anonymize   ofusca correos, IMEIs y coordenadas
#   ./scripts/db-local.sh env         imprime los export para apuntar alembic aquí
#
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

COMPOSE_FILE=docker-compose.db.yml
SERVICE=postgres-local
CONTAINER=siscom-admin-db-local
DB_NAME="${LOCAL_DB_NAME:-siscom-dev}"
DB_PORT="${LOCAL_DB_PORT:-55432}"
SUPERUSER="${LOCAL_DB_SUPERUSER:-postgres}"

compose() { docker compose -f "$COMPOSE_FILE" "$@"; }
psql_super() { docker exec -i "$CONTAINER" psql -v ON_ERROR_STOP=1 -U "$SUPERUSER" -d "$DB_NAME" "$@"; }

wait_ready() {
  echo "⏳ esperando a Postgres..."
  for _ in $(seq 1 60); do
    if docker exec "$CONTAINER" pg_isready -U "$SUPERUSER" -d "$DB_NAME" >/dev/null 2>&1; then
      echo "✅ Postgres listo en localhost:${DB_PORT}/${DB_NAME}"
      return 0
    fi
    sleep 1
  done
  echo "❌ Postgres no respondió a tiempo" >&2
  docker logs --tail 40 "$CONTAINER" >&2 || true
  return 1
}

cmd_up() {
  compose up -d "$SERVICE"
  wait_ready
}

cmd_down() { compose down; }

cmd_reset() {
  echo "🧨 destruyendo el volumen local..."
  compose down -v
  cmd_up
}

cmd_psql() {
  # -t solo si hay terminal: si no, falla con "the input device is not a TTY"
  local flags=-i
  [ -t 0 ] && flags=-it
  docker exec $flags "$CONTAINER" psql -U "$SUPERUSER" -d "$DB_NAME" "$@"
}

cmd_restore() {
  local dump="${1:?uso: db-local.sh restore <archivo.sql|.dump>}"
  [ -f "$dump" ] || { echo "❌ no existe: $dump" >&2; exit 1; }
  echo "📥 restaurando $dump — esto DESTRUYE el contenido local actual"
  compose down -v >/dev/null 2>&1 || true
  cmd_up
  case "$dump" in
    *.dump|*.custom)
      docker exec -i "$CONTAINER" pg_restore -U "$SUPERUSER" -d "$DB_NAME" --no-owner --no-privileges < "$dump"
      ;;
    *)
      docker exec -i "$CONTAINER" psql -U "$SUPERUSER" -d "$DB_NAME" < "$dump"
      ;;
  esac
  echo "✅ restaurado. Corre ahora: ./scripts/db-local.sh anonymize"
}

cmd_anonymize() {
  echo "🕶️  ofuscando datos personales..."
  psql_super <<'SQL'
BEGIN;
-- Correos: se conserva la forma y la unicidad, se pierde la identidad.
UPDATE users SET email = 'user+' || id::text || '@example.invalid'
  WHERE email IS NOT NULL AND email NOT LIKE '%@example.invalid';
-- IMEIs y referencias de equipo.
UPDATE devices SET device_id = lpad((abs(hashtext(device_id)) % 1000000000000000)::text, 15, '0')
  WHERE device_id IS NOT NULL;
COMMIT;
SQL
  echo "✅ anonimizado. Revisa el resultado antes de compartir el volumen."
  echo "   Nota: solo cubre users.email y devices.device_id. Amplía este bloque"
  echo "   conforme la réplica incorpore más tablas con dato personal."
}

cmd_env() {
  cat <<EOF
export DB_HOST=localhost
export DB_PORT=${DB_PORT}
export DB_NAME=${DB_NAME}
# runtime (solo DML) — con esto la app arranca pero alembic NO puede migrar
export DB_USER=siscom
export DB_PASSWORD=siscom
# migraciones (DDL) — con esto sí
export DB_MIGRATION_USER=siscom_migrator
export DB_MIGRATION_PASSWORD=siscom_migrator
EOF
}

case "${1:-}" in
  up)        cmd_up ;;
  down)      cmd_down ;;
  reset)     cmd_reset ;;
  psql)      shift; cmd_psql "$@" ;;
  restore)   shift; cmd_restore "$@" ;;
  anonymize) cmd_anonymize ;;
  env)       cmd_env ;;
  *)         sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
