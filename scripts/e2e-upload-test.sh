#!/bin/bash
# Full end-to-end upload test through the production stack:
# 0. set OSS bucket CORS for the web origins (browser PUT/GET path)
# 1. mint admin token  2. generate a real JPEG  3. upload/init
# 4. PUT bytes to the presigned OSS URL  5. upload/confirm  6. poll status in DB
set -e
cd /opt/wedding-app/infra

PY() { docker compose -f docker-compose.prod.yml exec -T backend uv run python; }

echo "=== 0. OSS bucket CORS ==="
PY - <<'PYEOF' || echo "NOTE: could not set bucket CORS (RAM user lacks bucket-admin permission) — set it in the OSS console."
from botocore.config import Config
import boto3
from src.config import get_settings

s = get_settings()
client = boto3.client(
    "s3", endpoint_url=s.storage_endpoint, region_name=s.storage_region,
    aws_access_key_id=s.storage_access_key, aws_secret_access_key=s.storage_secret_key,
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)
client.put_bucket_cors(
    Bucket=s.storage_bucket,
    CORSConfiguration={"CORSRules": [{
        "AllowedOrigins": [
            "https://39.107.108.11:8443",
            "https://nata-yisi.cn",
            "https://www.nata-yisi.cn",
        ],
        "AllowedMethods": ["PUT", "GET"],
        "AllowedHeaders": ["*"],
        "ExposeHeaders": ["ETag"],
        "MaxAgeSeconds": 3000,
    }]},
)
print("CORS rule set on bucket", s.storage_bucket)
PYEOF
# Non-fatal on purpose (see above).

TOKEN=$(PY - <<'PYEOF'
import asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from src.config import get_settings
from src.models.media import Media
from src.models.user import User
from src.services.auth import create_access_token

async def m():
    engine = create_async_engine(get_settings().database_url)
    async with AsyncSession(engine) as s:
        # Drop rows left over from earlier e2e runs so dedup doesn't 409.
        await s.execute(delete(Media).where(Media.filename == "e2e-test.jpg"))
        await s.commit()
        u = (await s.execute(select(User).where(User.role == "admin"))).scalar_one()
        print(create_access_token(u, get_settings()))

asyncio.run(m())
PYEOF
)

# A real small JPEG (red 64x64), written via Pillow inside the backend container.
PY - <<'PYEOF'
from PIL import Image
Image.new("RGB", (64, 64), (200, 30, 30)).save("/tmp/e2e-test.jpg", "JPEG")
PYEOF
docker cp infra-backend-1:/tmp/e2e-test.jpg /tmp/e2e-test.jpg >/dev/null

HASH=$(sha256sum /tmp/e2e-test.jpg | cut -d' ' -f1)
SIZE=$(stat -c%s /tmp/e2e-test.jpg)
echo "test file: size=$SIZE hash=${HASH:0:12}"

echo "=== 1. upload/init ==="
INIT=$(curl -sk -X POST https://localhost:8443/api/v1/media/upload/init \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"original_filename\":\"e2e-test.jpg\",\"mime_type\":\"image/jpeg\",\"file_size\":$SIZE,\"file_hash\":\"$HASH\"}")
echo "$INIT" | head -c 300; echo

UPLOAD_URL=$(echo "$INIT" | sed -n 's/.*"upload_url":"\([^"]*\)".*/\1/p')
MEDIA_ID=$(echo "$INIT" | sed -n 's/.*"media_id":\([0-9]*\).*/\1/p' | head -1)
if [ -z "$UPLOAD_URL" ]; then echo "INIT FAILED"; exit 1; fi
echo "media_id=$MEDIA_ID"

echo "=== 2. PUT to OSS ==="
HTTP_CODE=$(curl -sk -X PUT -H "Content-Type: image/jpeg" --data-binary @/tmp/e2e-test.jpg \
  -o /tmp/put-body.txt -w '%{http_code}' "$UPLOAD_URL")
echo "PUT status: $HTTP_CODE"; [ "$HTTP_CODE" = "200" ] || { head -c 300 /tmp/put-body.txt; exit 1; }

echo "=== 3. upload/confirm ==="
curl -sk -X POST "https://localhost:8443/api/v1/media/upload/confirm" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"media_id\":$MEDIA_ID}" | head -c 300; echo

echo "=== 4. poll status in DB (worker processing) ==="
for i in 1 2 3 4 5 6 7 8 9 10; do
  sleep 3
  STATUS=$(PY - <<PYEOF
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from src.config import get_settings
from src.models.media import Media

async def m():
    engine = create_async_engine(get_settings().database_url)
    async with AsyncSession(engine) as s:
        r = await s.get(Media, $MEDIA_ID)
        print(r.status)

asyncio.run(m())
PYEOF
)
  echo "attempt $i: status=$STATUS"
  [ "$STATUS" = "ready" ] && break
  [ "$STATUS" = "failed" ] && break
done

echo "=== 5. CORS preflight against OSS (browser PUT path) ==="
BUCKET_HOST=$(echo "$UPLOAD_URL" | sed -n 's|https://\([^/]*\)/.*|\1|p')
curl -sk -o /dev/null -X OPTIONS "https://$BUCKET_HOST/media/$HASH/e2e-test.jpg" \
  -H "Origin: https://39.107.108.11:8443" \
  -H "Access-Control-Request-Method: PUT" \
  -H "Access-Control-Request-Headers: content-type" \
  -D - | grep -i 'HTTP/\|access-control' || echo "no CORS headers returned"
