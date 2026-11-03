#!/bin/bash
# Docker's COPY layer cache can serve a stale image after a file-sync deploy.
# Compare the code baked into the running backend/worker images against the
# server tree (md5, CRLF-stripped), then rebuild + recreate to converge.
set -uo pipefail
cd /opt/wedding-app || exit 1
DC="docker compose -f infra/docker-compose.prod.yml"
REL="src/workers/media_processing.py"

echo "=== expected md5 (server tree, CRLF-stripped) ==="
tr -d '\r' < "backend/$REL" | md5sum

echo "=== baked in running images ==="
$DC exec -T backend sh -c "tr -d '\r' < /app/$REL | md5sum"
$DC exec -T worker sh -c "tr -d '\r' < /app/$REL | md5sum"

echo "=== rebuild + recreate backend worker ==="
$DC build backend worker > /tmp/build-bw.log 2>&1
echo "  build exit=$?"
tail -6 /tmp/build-bw.log
$DC up -d backend worker 2>&1 | tail -4
sleep 10
$DC ps --format 'table {{.Name}}\t{{.Status}}' | grep -E 'backend|worker'

echo "=== post-recreate baked check ==="
$DC exec -T backend sh -c "tr -d '\r' < /app/$REL | md5sum"
$DC exec -T worker sh -c "tr -d '\r' < /app/$REL | md5sum"
$DC logs --tail=6 backend 2>&1 | tail -6
