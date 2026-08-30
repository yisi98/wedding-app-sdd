#!/bin/bash
# Move the admin password to hash-only config: copy the bcrypt hash already stored in
# the database into backend/.env as ADMIN_PASSWORD_HASH (compose-escaped). The
# plaintext password never appears in any file.
set -e
cd /opt/wedding-app/infra

LINE=$(docker compose -f docker-compose.prod.yml exec -T backend uv run python - <<'PYEOF'
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from src.config import get_settings
from src.models.user import User

async def main():
    engine = create_async_engine(get_settings().database_url)
    async with AsyncSession(engine) as s:
        u = (await s.execute(select(User).where(User.username == "admin"))).scalar_one()
        # compose interpolates $VAR in env files -> every literal $ must be doubled
        print("ADMIN_PASSWORD_HASH=" + u.hashed_password.replace("$", "$$"))

asyncio.run(main())
PYEOF
)

case "$LINE" in
  ADMIN_PASSWORD_HASH='$$'*)
    ENVF=/opt/wedding-app/backend/.env
    grep -v '^ADMIN_PASSWORD_HASH=' "$ENVF" > /tmp/wmp.env.new || true
    printf '%s\n' "$LINE" >> /tmp/wmp.env.new
    mv /tmp/wmp.env.new "$ENVF"
    grep '^ADMIN_PASSWORD_HASH=' "$ENVF" | cut -c1-40
    echo HASH_SAVED
    ;;
  *)
    echo "UNEXPECTED_OUTPUT: $LINE"
    exit 1
    ;;
esac
