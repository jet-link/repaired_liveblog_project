#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/brainstorm/liveblog_project/liveblog_project"
VENV="/home/brainstorm/liveblog_project/venv/bin"

echo "==> Collecting static files..."
cd "$PROJECT_DIR"
"$VENV/python" manage.py collectstatic --noinput

echo "==> Compressing static assets (django-compressor)..."
"$VENV/python" manage.py compress --force 2>/dev/null || echo "    (compress skipped — run manually if needed)"

echo "==> Running database migrations..."
"$VENV/python" manage.py migrate --noinput

echo "==> Restarting Gunicorn..."
sudo systemctl restart gunicorn

echo "==> Reloading Nginx..."
sudo nginx -t && sudo systemctl reload nginx

echo "==> Deploy complete."
