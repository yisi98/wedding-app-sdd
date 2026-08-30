#!/bin/bash
# e2e-video-test.sh — end-to-end VIDEO upload test through the production stack.
#
# Exercises the last untested path:
#   1. ffmpeg is present in the worker/backend image
#   2. an .mp4 upload (web-safe): duration + poster thumbnail, NO transcode
#   3. a .mov upload (video/quicktime, NOT web-safe): duration + thumbnail + H.264/AAC
#      transcode to playable.mp4 (tests ffmpeg transcode + the +faststart flag)
#   4. HTTP Range serving through nginx -> 307 -> presigned OSS GET (iOS seeking)
set -e
cd /opt/wedding-app/infra
PY() { docker compose -f docker-compose.prod.yml exec -T backend uv run python; }

echo "=== 0. ffmpeg in the containers ==="
docker compose -f docker-compose.prod.yml exec -T backend ffmpeg -version 2>/dev/null | head -1
docker compose -f docker-compose.prod.yml exec -T worker  ffmpeg -version 2>/dev/null | head -1

echo "=== 1. mint admin token (and drop old e2e video rows) ==="
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
        await s.execute(delete(Media).where(Media.filename.in_(["e2e-video.mp4", "e2e-video.mov"])))
        await s.commit()
        u = (await s.execute(select(User).where(User.role == "admin"))).scalar_one()
        print(create_access_token(u, get_settings()))

asyncio.run(m())
PYEOF
)
echo "token ok (${#TOKEN} chars)"

echo "=== 2. generate test videos (inside the backend container) ==="
# 3-second, 320x240, 30fps H.264+AAC — twice, in two containers.
GEN='ffmpeg -y -loglevel error -f lavfi -i testsrc2=size=320x240:rate=30:duration=3 -f lavfi -i sine=frequency=440:duration=3 -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest'
docker compose -f docker-compose.prod.yml exec -T backend sh -c "$GEN /tmp/e2e-video.mp4"
docker compose -f docker-compose.prod.yml exec -T backend sh -c "$GEN -f mov /tmp/e2e-video.mov"
docker cp infra-backend-1:/tmp/e2e-video.mp4 /tmp/e2e-video.mp4 >/dev/null
docker cp infra-backend-1:/tmp/e2e-video.mov  /tmp/e2e-video.mov  >/dev/null
ls -l /tmp/e2e-video.mp4 /tmp/e2e-video.mov

upload_one() {  # $1=file  $2=filename  $3=mime  -> echoes "media_id key_hash" on stdout
  local FILE="$1" NAME="$2" MIME="$3"
  local HASH SIZE INIT UPLOAD_URL MEDIA_ID
  HASH=$(sha256sum "$FILE" | cut -d' ' -f1)
  SIZE=$(stat -c%s "$FILE")
  echo "--- upload $NAME (size=$SIZE) ---" >&2
  INIT=$(curl -sk -X POST https://localhost:8443/api/v1/media/upload/init \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"original_filename\":\"$NAME\",\"mime_type\":\"$MIME\",\"file_size\":$SIZE,\"file_hash\":\"$HASH\"}")
  UPLOAD_URL=$(echo "$INIT" | sed -n 's/.*"upload_url":"\([^"]*\)".*/\1/p')
  MEDIA_ID=$(echo "$INIT" | sed -n 's/.*"media_id":\([0-9]*\).*/\1/p' | head -1)
  [ -n "$UPLOAD_URL" ] || { echo "INIT FAILED: $INIT" >&2; exit 1; }
  local HTTP
  HTTP=$(curl -sk -X PUT -H "Content-Type: $MIME" --data-binary "@$FILE" \
    -o /tmp/put-body.txt -w '%{http_code}' "$UPLOAD_URL")
  echo "PUT to OSS: $HTTP" >&2; [ "$HTTP" = "200" ] || { head -c 300 /tmp/put-body.txt >&2; exit 1; }
  curl -sk -X POST "https://localhost:8443/api/v1/media/upload/confirm" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"media_id\":$MEDIA_ID}" -o /dev/null
  echo "$MEDIA_ID $HASH"
}

echo "=== 3. upload both videos ==="
read MP4_ID MP4_HASH <<< "$(upload_one /tmp/e2e-video.mp4 e2e-video.mp4 video/mp4)"
read MOV_ID MOV_HASH <<< "$(upload_one /tmp/e2e-video.mov e2e-video.mov video/quicktime)"
echo "mp4 media_id=$MP4_ID  mov media_id=$MOV_ID"
[ -n "$MP4_ID" ] && [ -n "$MOV_ID" ] || { echo "UPLOAD FAILED"; exit 1; }

echo "=== 4. poll worker processing (transcode may take a while) ==="
poll_status() {
  local MID="$1" NAME="$2" STATUS=""
  for i in $(seq 1 30); do
    sleep 3
    STATUS=$(PY - <<PYEOF
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from src.config import get_settings
from src.models.media import Media

async def m():
    engine = create_async_engine(get_settings().database_url)
    async with AsyncSession(engine) as s:
        r = await s.get(Media, $MID)
        print(r.status)

asyncio.run(m())
PYEOF
)
    echo "  $NAME attempt $i: $STATUS"
    [ "$STATUS" = "ready" ] && return 0
    [ "$STATUS" = "failed" ] && return 1
  done
  return 1
}
poll_status "$MP4_ID" "mp4" || echo "!! mp4 did not reach ready"
poll_status "$MOV_ID" "mov" || echo "!! mov did not reach ready"

echo "=== 5. derivative check in DB ==="
PY - <<PYEOF
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from src.config import get_settings
from src.models.media import Media

async def m():
    engine = create_async_engine(get_settings().database_url)
    async with AsyncSession(engine) as s:
        for mid, name in [($MP4_ID, "mp4"), ($MOV_ID, "mov")]:
            r = await s.get(Media, mid)
            print(f"id={mid} ({name}) status={r.status} duration={r.duration:.2f}s")
            print(f"   thumbnail_path={r.thumbnail_path}")
            print(f"   optimized_path={r.optimized_path}   <- playable.mp4 expected ONLY for mov")

asyncio.run(m())
PYEOF

echo "=== 6. HTTP Range requests through the full chain (nginx -> 307 -> OSS) ==="
range_test() {  # $1=key  $2=label
  local CODE
  CODE=$(curl -sk -o /tmp/range-body.bin -w '%{http_code}' -L \
    -H "Range: bytes=0-1023" "https://localhost:8443/media-object/$1")
  local BYTES=$(stat -c%s /tmp/range-body.bin)
  echo "  $2: HTTP $CODE, body $BYTES bytes (expect 206 + 1024)"
  curl -sk -D - -o /dev/null -L -H "Range: bytes=0-1023" \
    "https://localhost:8443/media-object/$1" | grep -i '^HTTP/\|content-range' | tr -d '\r'
}
range_test "media/$MP4_HASH/e2e-video.mp4"       "mp4 original (what the browser plays)"
range_test "media/$MOV_HASH/playable.mp4"        "mov transcoded playable.mp4"

echo "=== 7. faststart check on the transcode (moov before mdat → iOS-safe) ==="
PY - <<PYEOF
from src.services.storage import get_storage
data = get_storage().get("media/$MOV_HASH/playable.mp4")
moov, mdat = data.find(b"moov"), data.find(b"mdat")
print(f"  playable.mp4: {len(data)} bytes, moov@{moov}, mdat@{mdat} ->",
      "FASTSTART OK" if 0 < moov < mdat else "PROBLEM: mdat before moov")
PYEOF

echo ""
echo "=== DONE ==="
echo "Both videos are in the gallery — open the site, tap each video, scrub the"
echo "timeline (that's the Range path iOS Safari depends on), then delete them from"
echo "the admin panel if you don't want them there."
