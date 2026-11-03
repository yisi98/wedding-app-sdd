#!/bin/bash
# File-sync deploy: extract a `git archive` tarball onto /opt/wedding-app and
# rebuild + recreate the production stack. The server has no git checkout, so
# releases ride in as tarballs over SSH (see docs/DEPLOY-CHINA.md).
# Usage: ops-deploy-sync.sh <tarball.tgz>
set -uo pipefail
TARBALL="${1:?usage: ops-deploy-sync.sh <tarball.tgz>}"
cd /opt/wedding-app || exit 1
DC="docker compose -f infra/docker-compose.prod.yml"

echo "=== extract master tree ==="
tar -xzf "$TARBALL" -C /opt/wedding-app && echo "  extracted ok"

echo "=== rebuild backend worker frontend ==="
$DC build backend worker frontend 2>&1 | tail -6

echo "=== recreate containers ==="
$DC up -d 2>&1 | tail -8
sleep 12
$DC ps --format 'table {{.Name}}\t{{.Status}}'

echo "=== health + worker ==="
curl -sk -o /dev/null -w '  health=%{http_code}\n' https://127.0.0.1/api/v1/health
$DC logs --tail=4 worker 2>&1 | tail -4
