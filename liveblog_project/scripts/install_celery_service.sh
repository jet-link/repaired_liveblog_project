#!/bin/bash
# Устанавливает Celery как launchd-сервис (автозапуск при входе).
# Запуск: ./scripts/install_celery_service.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_SRC="$SCRIPT_DIR/com.liveblog.celery.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.liveblog.celery.plist"

mkdir -p "$HOME/Library/LaunchAgents"

# Удалить старый если есть
launchctl unload "$PLIST_DST" 2>/dev/null || true

cp "$PLIST_SRC" "$PLIST_DST"
echo "Скопировано: $PLIST_DST"
launchctl load "$PLIST_DST"
echo "Сервис запущен. Проверка: launchctl list | grep liveblog"
echo "Логи: tail -f /tmp/celery-liveblog.log"
