#!/usr/bin/env bash
# diagnose-gallery.sh — find why a gallery tile stays on its blurred LQIP placeholder.
# For each recent media row: print its DB fields, then fetch its thumbnail through
# nginx (following the 307 redirect to OSS) and show every hop's status.
set -e
cd /opt/wedding-app/infra

PY() { docker compose -f docker-compose.prod.yml exec -T backend uv run python; }

echo "== recent media rows =="
PY - <<'PYEOF'
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.config import get_settings
from src.models.media import Media


async def m():
    engine = create_async_engine(get_settings().database_url)
    async with AsyncSession(engine) as s:
        rows = (await s.execute(select(Media).order_by(Media.id.desc()).limit(6))).scalars().all()
        for r in rows:
            print(
                f"id={r.id} status={r.status} filename={r.original_filename} "
                f"thumb={r.thumbnail_path} optimized={r.optimized_path} "
                f"lqip={'yes' if r.lqip else 'no'} {r.width}x{r.height}"
            )

asyncio.run(m())
PYEOF

echo ""
echo "== thumbnail fetch test through nginx (follows redirect to OSS) =="
PY - <<'PYEOF' >/tmp/wmp-keys.txt
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.config import get_settings
from src.models.media import Media


async def m():
    engine = create_async_engine(get_settings().database_url)
    async with AsyncSession(engine) as s:
        rows = (await s.execute(select(Media).order_by(Media.id.desc()).limit(6))).scalars().all()
        for r in rows:
            for label, path in (("thumb", r.thumbnail_path), ("opt", r.optimized_path)):
                if path:
                    print(f"{r.id}|{label}|{path}")

asyncio.run(m())
PYEOF

while IFS='|' read -r mid label path; do
  echo "--- media id=$mid $label: $path"
  curl -sk -L -o /dev/null \
    -w '  hops: %{num_redirects}  final_code: %{http_code}  final_url: %{url_effective}\n' \
    "https://localhost:8443/api/v1/media-object/$path" | sed 's/X-Amz-Signature=[^&]*/X-Amz-Signature=.../'
  curl -sk -o /dev/null -w '  redirect_target_code: %{http_code}\n' \
    "https://localhost:8443/api/v1/media-object/$path"
done < /tmp/wmp-keys.txt

echo ""
echo "Interpretation:"
echo "  final_code 200  -> image serves fine (problem is browser-side / caching)"
echo "  403/400        -> OSS rejected the presigned URL (signature problem)"
echo "  404            -> object missing in OSS"
echo "  307 loop/000   -> redirect not followed / network issue"
