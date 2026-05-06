#!/bin/bash
# Run ONCE on the server: sudo bash once_sudo_setup.sh
# Installs nginx and proxies HTTP to Gunicorn. Does NOT run Certbot (needs DNS on this server first).
set -euo pipefail

APP_USER="brainstorm"
CONF_SRC="/home/${APP_USER}/liveblog_project/digitalocean/nginx-brainstorm.conf"
NGINX_SITE="/etc/nginx/sites-available/brainstorm"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq nginx certbot python3-certbot-nginx

cp "${CONF_SRC}" "${NGINX_SITE}"
ln -sf "${NGINX_SITE}" /etc/nginx/sites-enabled/brainstorm.conf
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl enable nginx
systemctl reload nginx

echo "Nginx is up on port 80. Next steps:"
echo "  1) Point DNS A/AAAA for brainstorm.news and www.brainstorm.news to THIS server's public IP."
echo "  2) dig +short brainstorm.news A  — must show this Droplet IP, not the old host."
echo "  3) sudo bash /home/${APP_USER}/liveblog_project/digitalocean/run_certbot.sh"
