#!/bin/bash
# Force-recreate backend+worker from the currently built images (no rebuild),
# then verify the baked file matches the server tree byte-for-byte.
set -uo pipefail
cd /opt/wedding-app || exit 1
DC="docker compose -f infra/docker-compose.prod.yml"
REL="src/workers/media_processing.py"

echo "=== expected md5 (server tree, raw) ==="
md5sum "backend/$REL"

echo "=== force-recreate backend worker ==="
$DC up -d --force-recreate backend worker 2>&1 | tail -5
sleep 12

echo "=== raw md5 inside containers ==="
$DC exec -T backend md5sum "/app/$REL"
$DC exec -T worker md5sum "/app/$REL"

echo "=== container status ==="
$DC ps --format 'table {{.Name}}\t{{.Status}}'

echo "=== health ==="
curl -sk -o /dev/null -w 'health=%{http_code}\n' https://127.0.0.1/api/v1/health

echo "=== worker startup log ==="
$DC logs --tail=5 worker 2>&1 | tail -5
