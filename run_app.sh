#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
PIP_BIN="${ROOT_DIR}/.venv/bin/pip"
DJANGO_ADDR="${DJANGO_ADDR:-127.0.0.1:8000}"
VITE_HOST="${VITE_HOST:-127.0.0.1}"
VITE_PORT="${VITE_PORT:-5173}"

backend_pid=""
frontend_pid=""

usage() {
  cat <<'USAGE'
Usage:
  ./run_app.sh             Run Django + Vite dev servers
  ./run_app.sh dev         Run Django + Vite dev servers
  ./run_app.sh django      Build frontend and serve it through Django
  ./run_app.sh docker      Run the full Docker Compose stack
  ./run_app.sh seed        Seed starter Life RPG data

Environment overrides:
  DJANGO_ADDR=127.0.0.1:8000
  VITE_HOST=127.0.0.1
  VITE_PORT=5173
USAGE
}

cleanup() {
  if [[ -n "${frontend_pid}" ]] && kill -0 "${frontend_pid}" 2>/dev/null; then
    kill "${frontend_pid}" 2>/dev/null || true
  fi

  if [[ -n "${backend_pid}" ]] && kill -0 "${backend_pid}" 2>/dev/null; then
    kill "${backend_pid}" 2>/dev/null || true
  fi
}

die() {
  echo "Error: $*" >&2
  exit 1
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

ensure_env_file() {
  if [[ ! -f "${ROOT_DIR}/.env" ]]; then
    cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/.env"
    echo "Created .env from .env.example."
    echo "Edit .env and set PostgreSQL credentials if your local database needs them."
  fi
}

ensure_python_env() {
  if [[ ! -x "${PYTHON_BIN}" ]]; then
    command_exists python3 || die "python3 is required."
    python3 -m venv "${ROOT_DIR}/.venv"
  fi

  if ! "${PYTHON_BIN}" -c "import django" >/dev/null 2>&1; then
    "${PIP_BIN}" install -r "${ROOT_DIR}/requirements.txt"
  fi
}

ensure_frontend_env() {
  command_exists npm || die "npm is required."

  if [[ ! -d "${ROOT_DIR}/frontend/node_modules" ]]; then
    npm --prefix "${ROOT_DIR}/frontend" install
  fi
}

run_migrations() {
  "${PYTHON_BIN}" "${ROOT_DIR}/manage.py" migrate
}

run_dev() {
  ensure_env_file
  ensure_python_env
  ensure_frontend_env
  run_migrations

  trap cleanup EXIT INT TERM

  echo "Starting Django at http://${DJANGO_ADDR}/"
  "${PYTHON_BIN}" "${ROOT_DIR}/manage.py" runserver "${DJANGO_ADDR}" &
  backend_pid=$!

  echo "Starting Vite at http://${VITE_HOST}:${VITE_PORT}/"
  npm --prefix "${ROOT_DIR}/frontend" run dev -- --host "${VITE_HOST}" --port "${VITE_PORT}" &
  frontend_pid=$!

  echo "Open http://${VITE_HOST}:${VITE_PORT}/"
  wait -n "${backend_pid}" "${frontend_pid}"
}

run_django() {
  ensure_env_file
  ensure_python_env
  ensure_frontend_env
  npm --prefix "${ROOT_DIR}/frontend" run build
  run_migrations
  echo "Open http://${DJANGO_ADDR}/"
  exec "${PYTHON_BIN}" "${ROOT_DIR}/manage.py" runserver "${DJANGO_ADDR}"
}

run_docker() {
  ensure_env_file

  if grep -Eq '^POSTGRES_PASSWORD=[[:space:]]*$' "${ROOT_DIR}/.env"; then
    die "Set POSTGRES_PASSWORD in .env before running Docker Compose."
  fi

  if docker compose version >/dev/null 2>&1; then
    exec docker compose up --build
  fi

  command_exists docker-compose || die "docker compose or docker-compose is required."
  exec docker-compose up --build
}

run_seed() {
  ensure_env_file
  ensure_python_env
  "${PYTHON_BIN}" "${ROOT_DIR}/manage.py" seed_life_rpg
}

cd "${ROOT_DIR}"

case "${1:-dev}" in
  dev)
    run_dev
    ;;
  django)
    run_django
    ;;
  docker)
    run_docker
    ;;
  seed)
    run_seed
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage
    exit 1
    ;;
esac
