#!/bin/bash
# Reproduce the 500 on POST /api/v1/media/upload/init: mint an admin token using the
# app's own secret, call the endpoint through nginx, then print the traceback.
set -e
cd /opt/wedding-app/infra

TOKEN=$(docker compose -f docker-compose.prod.yml exec -T backend uv run python - <<'PYEOF'
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from src.config import get_settings
from src.models.user import User
from src.services.auth import create_access_token

async def m():
    engine = create_async_engine(get_settings().database_url)
    async with AsyncSession(engine) as s:
        u = (await s.execute(select(User).where(User.role == "admin"))).scalar_one()
        print(create_access_token(u, get_settings()))

asyncio.run(m())
PYEOF
)

echo "=== RESPONSE ==="
curl -sk -X POST https://localhost:8443/api/v1/media/upload/init \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"original_filename":"test.png","mime_type":"image/png","file_size":12345,"file_hash":"deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"}'
echo
echo "=== TRACEBACK ==="
docker logs infra-backend-1 2>&1 | grep -A 25 "Unhandled error" | tail -30
