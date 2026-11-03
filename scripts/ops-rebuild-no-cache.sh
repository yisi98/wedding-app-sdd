#!/bin/bash
# No-cache rebuild of backend+worker (bypasses a stale COPY layer entirely),
# force-recreate, then poll health until the stack is back.
set -uo pipefail
cd /opt/wedding-app || exit 1
DC="docker compose -f infra/docker-compose.prod.yml"
REL="src/workers/media_processing.py"

echo "=== host file md5 ==="
md5sum "backend/$REL"

echo "=== no-cache rebuild backend worker ==="
$DC build --no-cache backend worker > /tmp/build-nc.log 2>&1
echo "  build exit=$?"
tail -4 /tmp/build-nc.log

echo "=== recreate ==="
$DC up -d --force-recreate backend worker 2>&1 | tail -4

echo "=== poll health up to 90s ==="
for i in $(seq 1 18); do
  sleep 5
  code=$(curl -sk -o /dev/null -w '%{http_code}' https://127.0.0.1/api/v1/health)
  echo "  t=$((i*5))s health=$code"
  [ "$code" = "200" ] && break
done

echo "=== raw md5 inside containers ==="
$DC exec -T backend md5sum "/app/$REL"
$DC exec -T worker md5sum "/app/$REL"

echo "=== status + logs ==="
$DC ps --format 'table {{.Name}}\t{{.Status}}'
$DC logs --tail=4 worker 2>&1 | tail -4
$DC logs --tail=6 backend 2>&1 | tail -6
