#!/bin/bash
# Фоновый пересчёт trending без Celery (аналог beat-задачи update_trending).
# Запуск: ./scripts/trending_daemon.sh
# Остановка: Ctrl+C
#
# Опции передаются дальше, например:
#   ./scripts/trending_daemon.sh --interval 300

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$PROJECT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  . "$ROOT_DIR/.env"
  set +a
fi

PYTHON="$ROOT_DIR/venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

exec "$PYTHON" manage.py update_trending --daemon "$@"
