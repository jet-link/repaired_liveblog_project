#!/bin/bash
# Celery worker + beat — один процесс для trending/rollup.
# Запуск: ./scripts/celery_dev.sh
# Или через launchd — см. scripts/README_CELERY.md

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$PROJECT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

# Загрузить .env (DJANGO_DB_PASSWORD и др.)
if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  . "$ROOT_DIR/.env"
  set +a
fi

# Использовать venv, если есть
CELERY_BIN="$ROOT_DIR/venv/bin/celery"
if [ ! -x "$CELERY_BIN" ]; then
  CELERY_BIN="celery"
fi

exec "$CELERY_BIN" -A liveblog_project worker --beat -l info
