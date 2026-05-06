#!/bin/bash
# Run AFTER DNS for brainstorm.news / www points to THIS Droplet.
# Usage: sudo bash run_certbot.sh [expected_ipv4]
set -euo pipefail

DOMAINS=(brainstorm.news www.brainstorm.news)
if [[ -n "${1:-}" ]]; then
  EXPECTED_IP="$1"
else
  # DigitalOcean / generic: prefer metadata, then public interface
  EXPECTED_IP=""
  if curl -sSf -m 2 http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address &>/dev/null; then
    EXPECTED_IP=$(curl -sSf -m 2 http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address)
  fi
  if [[ -z "$EXPECTED_IP" ]]; then
    EXPECTED_IP=$(curl -sSf -m 5 https://ifconfig.me || true)
  fi
fi

if [[ -z "$EXPECTED_IP" ]]; then
  echo "Could not detect this server's IPv4. Pass it explicitly: sudo bash run_certbot.sh 161.35.x.x"
  exit 1
fi

echo "Expecting domains to resolve to this server: ${EXPECTED_IP}"
for d in "${DOMAINS[@]}"; do
  RES=$(dig +short "$d" A | tail -n1)
  if [[ -z "$RES" ]]; then
    echo "ERROR: No A record for ${d}"
    exit 1
  fi
  if [[ "$RES" != "$EXPECTED_IP" ]]; then
    echo "ERROR: ${d} -> ${RES} (must be ${EXPECTED_IP}). Update DNS at your registrar, wait TTL, try again."
    exit 1
  fi
  echo "OK: ${d} -> ${RES}"
done

certbot --nginx \
  -d brainstorm.news -d www.brainstorm.news \
  --non-interactive --agree-tos \
  --register-unsafely-without-email \
  --redirect

systemctl reload nginx
echo "Let's Encrypt certificate installed. HTTPS redirect enabled."
