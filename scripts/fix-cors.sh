#!/bin/bash
# Add the www origin to the backend CORS allow-list and verify the preflight.
set -uo pipefail
ENVF=/opt/wedding-app/backend/.env
NEW='CORS_ORIGINS=["https://nata-yisi.cn","https://www.nata-yisi.cn"]'

echo "=== before ==="
grep -n '^CORS_ORIGINS=' "$ENVF" || echo "(no CORS_ORIGINS line)"

if grep -q '^CORS_ORIGINS=' "$ENVF"; then
  sed -i "s|^CORS_ORIGINS=.*|${NEW}|" "$ENVF"
else
  printf '%s\n' "$NEW" >> "$ENVF"
fi

echo "=== after ==="
grep -n '^CORS_ORIGINS=' "$ENVF"

cd /opt/wedding-app || exit 1
docker compose -f infra/docker-compose.prod.yml up -d --force-recreate backend
sleep 8

preflight() {
  curl -sk -o /dev/null -w '%{http_code}' -X OPTIONS https://127.0.0.1/api/v1/auth/login \
    -H "Origin: $1" \
    -H 'Access-Control-Request-Method: POST' \
    -H 'Access-Control-Request-Headers: content-type'
}
echo "=== preflight status codes (expect 200) ==="
echo "www   : $(preflight https://www.nata-yisi.cn)"
echo "apex  : $(preflight https://nata-yisi.cn)"
echo "=== allow-origin header for www ==="
curl -sk -i -X OPTIONS https://127.0.0.1/api/v1/auth/login \
  -H 'Origin: https://www.nata-yisi.cn' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type' \
  | grep -i 'access-control-allow-origin' || echo "(header missing)"
