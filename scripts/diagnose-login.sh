#!/bin/bash
# Read-only diagnosis of login failures on the wedding-app production host.
# Prints NO secret values: only lengths, structural validity and match/no-match.
set -u
cd /opt/wedding-app || exit 1
DC="docker compose -f infra/docker-compose.prod.yml"

echo "=== 1. backend/.env (masked) ==="
for k in EVENT_PASSWORD EVENT_PASSWORD_HASH ADMIN_PASSWORD ADMIN_PASSWORD_HASH DEBUG; do
  line=$(grep "^${k}=" backend/.env 2>/dev/null | head -1)
  if [ -z "$line" ]; then
    echo "$k: ABSENT"
  else
    v="${line#*=}"
    case "$v" in
      *'$$'*) dbl=yes ;;
      *) dbl=no ;;
    esac
    case "$k" in
      *_HASH) echo "$k: len=${#v} head=${v:0:4} doubled_dollar=$dbl" ;;
      DEBUG)  echo "$k: $v" ;;
      *)      echo "$k: SET len=${#v} doubled_dollar=$dbl" ;;
    esac
  fi
done

echo
echo "=== 2. container env (masked) ==="
for k in EVENT_PASSWORD EVENT_PASSWORD_HASH ADMIN_PASSWORD ADMIN_PASSWORD_HASH; do
  v=$($DC exec -T backend printenv "$k" 2>/dev/null | tr -d '\n')
  if [ -z "$v" ]; then
    echo "$k: UNSET_IN_CONTAINER"
  else
    case "$k" in
      *_HASH) echo "$k: len=${#v} head=${v:0:4}" ;;
      *)      echo "$k: SET len=${#v}" ;;
    esac
  fi
done

echo
echo "=== 3. what the app actually loaded (pydantic Settings) ==="
$DC exec -T backend uv run python - <<'PYEOF'
import bcrypt
from src.config import get_settings

s = get_settings()
print("debug:", s.debug)
print("event_password_hash_set:", bool(s.event_password_hash))
if s.event_password_hash:
    h = s.event_password_hash
    print("  len:", len(h), "head:", h[:4])
    try:
        bcrypt.checkpw(b"structural-probe", h.encode())
        print("  bcrypt_format: VALID (a wrong password returns False, not an error)")
    except ValueError as exc:
        print("  bcrypt_format: INVALID ->", exc)
        print("  ==> no event password can EVER match; this is the guest-login bug")
else:
    print("  plaintext EVENT_PASSWORD len:", len(s.event_password))
print("admin_password_hash_set:", bool(s.admin_password_hash))
print("admin_username:", s.admin_username)
PYEOF

echo
echo "=== 4. database users ==="
$DC exec -T backend uv run python - <<'PYEOF'
import asyncio

import bcrypt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.config import get_settings
from src.models.user import User

SENTINEL = "!"


async def main():
    engine = create_async_engine(get_settings().database_url)
    async with AsyncSession(engine) as s:
        total = (await s.execute(select(func.count()).select_from(User))).scalar_one()
        own = (
            await s.execute(
                select(User).where(User.hashed_password != SENTINEL)
            )
        ).scalars().all()
        print("total_users:", total)
        print("users_with_own_password:", len(own))
        settings = get_settings()
        for u in own:
            hp = u.hashed_password
            print(f"- username={u.username!r} role={u.role} active={u.is_active} "
                  f"hash_len={len(hp)} head={hp[:4]}")
            try:
                bcrypt.checkpw(b"structural-probe", hp.encode())
                print("    bcrypt_format: VALID")
                # Known-default probe: migration 0004 seeds from ADMIN_PASSWORD only,
                # so an unset ADMIN_PASSWORD leaves the repo default in the DB.
                if bcrypt.checkpw(b"dev-only-admin-pass", hp.encode()):
                    print("    MATCHES_REPO_DEFAULT_ADMIN_PASSWORD: yes")
                if settings.admin_password and bcrypt.checkpw(
                    settings.admin_password.encode(), hp.encode()
                ):
                    print("    MATCHES_ENV_ADMIN_PASSWORD: yes")
                if settings.admin_password_hash and bcrypt.checkpw(
                    b"structural-probe", settings.admin_password_hash.encode()
                ):
                    print("    env ADMIN_PASSWORD_HASH is also valid bcrypt")
            except ValueError as exc:
                print("    bcrypt_format: INVALID ->", exc)
                print("    ==> this account can never authenticate")
    await engine.dispose()


asyncio.run(main())
PYEOF

echo
echo "=== 5. login throttle state (redis) ==="
$DC exec -T redis redis-cli --scan --pattern 'wmp:login:fail:*' 2>/dev/null | head -5 || echo "redis scan unavailable"

echo
echo "=== 6. recent backend auth log lines ==="
$DC logs --tail=200 backend 2>&1 | grep -iE 'auth/login|401|429|throttl|bcrypt|ValueError' | tail -12

echo
echo "=== 7. service status ==="
$DC ps --format '{{.Name}} {{.Status}}'
