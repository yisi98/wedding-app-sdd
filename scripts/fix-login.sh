#!/bin/bash
# fix-login.sh — reset BOTH wedding-app passwords and verify login end-to-end.
#
# Two independent stores, either of which can silently hold a password nobody knows:
#   Guest event password — bcrypt hash in backend/.env as EVENT_PASSWORD_HASH. It must
#     be $$-escaped, because compose interpolates $ in env_file values (see
#     docs/DEPLOY-CHINA.md); an unescaped hash loses its $salt segment, bcrypt.checkpw
#     then raises ValueError and NO password can ever match -> 401 "活动密码不正确".
#   Admin password — bcrypt hash in the users table, seeded once by migration 0004 from
#     ADMIN_PASSWORD. ensure_default_admin() never overwrites an existing row, so fixing
#     the env file cannot fix the database. Every role=admin row is updated, not just the
#     first one, because a deployment can accumulate several.
#
# Not a diagnosis tool: run diagnose-login.sh first if you do not yet know which store is
# wrong. And if both logins here return 200 while a real browser still fails, the cause is
# client-side, not a password — check CORS (fix-cors.sh) and the login throttle.
#
# Run on the server as root:   bash /tmp/fix-login.sh
# Re-runnable. Passwords are read hidden and never written to disk in plaintext.

set -u
cd /opt/wedding-app || exit 1
DC="docker compose -f infra/docker-compose.prod.yml"
ENVF=backend/.env
D=nata-yisi.cn
ST=wmp-selftest
push() { docker cp "$1" "$($DC ps -q backend):$2"; }
cenv() { $DC exec -T backend printenv "$1" 2>/dev/null | tr -d '\n'; }

echo "--- BEFORE (masked, no secret values printed) ---"
for k in EVENT_PASSWORD EVENT_PASSWORD_HASH ADMIN_PASSWORD ADMIN_PASSWORD_HASH DEBUG; do
  v=$(grep "^$k=" "$ENVF" 2>/dev/null | head -1 | cut -d= -f2-)
  if [ -z "$v" ]; then echo "  $k: absent"; else echo "  $k: len=${#v} head=${v:0:4}"; fi
done
c=$(cenv EVENT_PASSWORD_HASH)
echo "  container EVENT_PASSWORD_HASH: len=${#c} head=${c:0:4}"
echo "  (usable bcrypt = len 60, head \$2b\$ ; anything else can never match)"

echo "--- type the new passwords (hidden) ---"
echo "  event password = what guests and the 网安 reviewer use."
echo "  Re-type the one you intended if you remember it; it gets hashed correctly now."
echo "  Avoid: double-quote, backslash, backtick."
read -rsp "  event (guest) password: " EPW; echo
read -rsp "  repeat:                 " EPW2; echo
read -rsp "  admin password:         " APW; echo
read -rsp "  repeat:                 " APW2; echo
[ "$EPW" = "$EPW2" ] || { echo "ABORT: event mismatch"; exit 1; }
[ "$APW" = "$APW2" ] || { echo "ABORT: admin mismatch"; exit 1; }
[ "${#EPW}" -ge 8 ] || { echo "ABORT: event password >= 8 chars"; exit 1; }
[ "${#APW}" -ge 10 ] || { echo "ABORT: admin password >= 10 chars"; exit 1; }
case "$EPW$APW" in *'"'*|*'\'*|*'`'*) echo "ABORT: bad character"; exit 1 ;; esac

echo "--- 1. hash both + rewrite the admin row in the database ---"
cat > /tmp/wmp_pw.py <<'PYEOF'
import asyncio
import os
import sys

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.config import get_settings
from src.models.user import ROLE_ADMIN, User

lines = sys.stdin.read().split("\n")


def hashed(pw):
    h = bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=12)).decode()
    if not bcrypt.checkpw(pw.encode(), h.encode()):
        raise SystemExit("hash self-check failed")
    return h


eh, ah = hashed(lines[0]), hashed(lines[1])


async def main():
    eng = create_async_engine(get_settings().database_url)
    async with AsyncSession(eng) as s:
        rows = (await s.execute(select(User).where(User.role == ROLE_ADMIN))).scalars().all()
        if not rows:
            print("  DB_ADMIN: none found")
        for u in rows:
            u.hashed_password = ah
            u.is_active = True
            print("  DB_ADMIN_UPDATED username=%s hash_len=%d" % (u.username, len(ah)))
        await s.commit()
    await eng.dispose()


asyncio.run(main())
print("EH=" + eh)
print("AH=" + ah)
PYEOF
push /tmp/wmp_pw.py /tmp/wmp_pw.py
OUT=$(printf '%s\n%s\n' "$EPW" "$APW" | $DC exec -T backend uv run python /tmp/wmp_pw.py) \
  || { echo "$OUT"; echo "ABORT: hash/DB step failed"; exit 1; }
echo "$OUT" | grep -v '^EH=\|^AH='
EH=$(echo "$OUT" | sed -n 's/^EH=//p')
AH=$(echo "$OUT" | sed -n 's/^AH=//p')
AU=$(echo "$OUT" | sed -n 's/.*DB_ADMIN_UPDATED username=\([^ ]*\).*/\1/p' | head -1)
[ -n "$AU" ] || AU=admin
[ "${#EH}" = "60" ] || { echo "ABORT: bad event hash"; exit 1; }

echo "--- 2. write env hashes, auto-detecting the escaping compose honours ---"
for m in double raw quoted; do
  case $m in
    double) e=$(printf '%s' "$EH" | awk '{gsub(/\$/, "$$"); printf "%s", $0}')
            a=$(printf '%s' "$AH" | awk '{gsub(/\$/, "$$"); printf "%s", $0}') ;;
    raw)    e=$EH; a=$AH ;;
    quoted) e="'$EH'"; a="'$AH'" ;;
  esac
  grep -v -e '^EVENT_PASSWORD=' -e '^EVENT_PASSWORD_HASH=' \
        -e '^ADMIN_PASSWORD=' -e '^ADMIN_PASSWORD_HASH=' "$ENVF" > /tmp/wmp_e1
  { printf 'EVENT_PASSWORD_HASH=%s\nADMIN_PASSWORD_HASH=%s\n' "$e" "$a"; cat /tmp/wmp_e1; } > /tmp/wmp_e2
  mv /tmp/wmp_e2 "$ENVF"; chmod 600 "$ENVF"
  $DC up -d --force-recreate backend >/dev/null 2>&1
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
    sleep 5
    curl -sf --resolve "$D:443:127.0.0.1" "https://$D/api/v1/health" -o /dev/null && break
  done
  g=$(cenv EVENT_PASSWORD_HASH)
  echo "  mode=$m -> container len=${#g} head=${g:0:4}"
  if [ "${#g}" = "60" ] && [ "${g:0:2}" = '$2' ]; then echo "  WORKING_MODE=$m"; break; fi
done

echo "--- 3. clear login lockouts ---"
$DC exec -T redis sh -c 'redis-cli --scan --pattern "wmp:login:fail:*" | xargs -r redis-cli del' 2>/dev/null
echo "  throttle keys cleared"

echo "--- 4. real logins through nginx ---"
t() {
  code=$(curl -s -o /tmp/wmp_lj -w '%{http_code}' --resolve "$D:443:127.0.0.1" \
    -X POST "https://$D/api/v1/auth/login" -H 'Content-Type: application/json' \
    -d "{\"display_name\":\"$1\",\"event_password\":\"$2\"}")
  echo "  LOGIN $1 -> HTTP $code"
  [ "$code" = "200" ] || { echo "  body: $(head -c 200 /tmp/wmp_lj)"; return 1; }
}
G=0; A=0
t "$ST" "$EPW" && G=1
t "$AU" "$APW" && A=1

echo "--- 5. delete the self-test guest ---"
cat > /tmp/wmp_cl.py <<'PYEOF'
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.config import get_settings
from src.models.user import User


async def main():
    eng = create_async_engine(get_settings().database_url)
    async with AsyncSession(eng) as s:
        u = (await s.execute(select(User).where(User.username == "wmp-selftest"))).scalar_one_or_none()
        if u is None:
            print("  no self-test user")
        else:
            await s.delete(u)
            await s.commit()
            print("  deleted wmp-selftest (refresh tokens cascade)")
    await eng.dispose()


asyncio.run(main())
PYEOF
push /tmp/wmp_cl.py /tmp/wmp_cl.py
$DC exec -T backend uv run python /tmp/wmp_cl.py
rm -f /tmp/wmp_pw.py /tmp/wmp_cl.py /tmp/wmp_lj /tmp/wmp_e1 /tmp/wmp_e2

echo "--- RESULT ---"
[ "$G" = "1" ] && echo "  GUEST LOGIN: FIXED (HTTP 200)" || echo "  GUEST LOGIN: STILL FAILING"
[ "$A" = "1" ] && echo "  ADMIN LOGIN: FIXED (HTTP 200)" || echo "  ADMIN LOGIN: STILL FAILING"
echo "  https://$D/login  guests: any display name + event password"
echo "  https://$D/login  admin : display name '$AU' + admin password"
