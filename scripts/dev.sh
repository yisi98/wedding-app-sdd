#!/usr/bin/env bash
# Run the whole app locally with no external services.
#
# Uses the zero-infra path: SQLite instead of PostgreSQL, the local filesystem instead of
# object storage, and inline media processing instead of Celery. Nothing to install beyond
# uv and Node. For the production-shaped stack (PostgreSQL + Redis + MinIO) use
# `docker compose -f infra/docker-compose.dev.yml up` instead.
#
#   ./scripts/dev.sh          start both servers
#   ./scripts/dev.sh --reset  start fresh, discarding the local database and uploads
# This check must come before `set -o pipefail`, which dash rejects outright — otherwise
# `sh scripts/dev.sh` dies with "Illegal option -o pipefail" instead of something useful.
if [ -z "${BASH_VERSION:-}" ]; then
  echo "Run this with bash, not sh:  ./scripts/dev.sh   (or: bash scripts/dev.sh)" >&2
  exit 1
fi

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"

bold() { printf '\033[1m%s\033[0m\n' "$1"; }
warn() { printf '\033[33m%s\033[0m\n' "$1"; }
die()  { printf '\033[31m%s\033[0m\n' "$1" >&2; exit 1; }

# uv and nvm-managed node install to per-user directories that a non-login shell often
# hasn't picked up yet, so look there before declaring them missing.
for extra in "$HOME/.local/bin" "$HOME/.cargo/bin" "/opt/homebrew/bin" "/usr/local/bin"; do
  [[ -d "$extra" ]] && case ":$PATH:" in *":$extra:"*) ;; *) PATH="$PATH:$extra" ;; esac
done
export PATH

if ! command -v uv >/dev/null 2>&1; then
  die "uv not found on PATH.
  Install:  curl -LsSf https://astral.sh/uv/install.sh | sh
  If you just installed it, open a new terminal (or: export PATH=\"\$HOME/.local/bin:\$PATH\").
  Already have Python? You can skip this script — see 'Running the pieces individually'
  in the README."
fi
command -v node >/dev/null 2>&1 || die "Node 20+ not found on PATH — https://nodejs.org"
command -v ffmpeg >/dev/null 2>&1 || warn "ffmpeg not found: videos will upload but get no thumbnail, duration, or transcode."

if [[ "${1:-}" == "--reset" ]]; then
  bold "Resetting local database and uploads…"
  rm -f "$BACKEND/wedding.db"
  rm -rf "$BACKEND/.data"
fi

# Config files. Neither is committed; both are created on first run.
[[ -f "$BACKEND/.env" ]] || { cp "$BACKEND/.env.example" "$BACKEND/.env"; bold "Created backend/.env from the example."; }
if [[ ! -f "$FRONTEND/.env.local" ]]; then
  echo "NEXT_PUBLIC_API_BASE=http://localhost:$API_PORT" > "$FRONTEND/.env.local"
  bold "Created frontend/.env.local."
fi

bold "Installing dependencies (first run takes a minute)…"
(cd "$BACKEND" && uv sync --quiet)
[[ -d "$FRONTEND/node_modules" ]] || (cd "$FRONTEND" && npm install --silent)

# Free the ports so a previous run can't linger and serve stale code.
for port in "$API_PORT" "$WEB_PORT"; do
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti:"$port" -sTCP:LISTEN 2>/dev/null | xargs -r kill -9 2>/dev/null || true
  fi
done

cleanup() {
  echo
  bold "Stopping…"
  [[ -n "${API_PID:-}"  ]] && kill "$API_PID"  2>/dev/null || true
  [[ -n "${WEB_PID:-}" ]] && kill "$WEB_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

bold "Starting the API on :$API_PORT…"
(cd "$BACKEND" && uv run uvicorn src.main:app --host 0.0.0.0 --port "$API_PORT" --reload) &
API_PID=$!

for _ in $(seq 1 60); do
  curl -sf "http://localhost:$API_PORT/api/v1/health" >/dev/null 2>&1 && break
  sleep 1
done

bold "Starting the web app on :$WEB_PORT…"
(cd "$FRONTEND" && npm run dev -- --port "$WEB_PORT") &
WEB_PID=$!

for _ in $(seq 1 60); do
  curl -sf "http://localhost:$WEB_PORT" >/dev/null 2>&1 && break
  sleep 1
done

cat <<EOF

$(bold "Ready.")

  App        http://localhost:$WEB_PORT
  API docs   http://localhost:$API_PORT/docs

  Guest      any name you like + password  $(grep -oP '^EVENT_PASSWORD=\K.*' "$BACKEND/.env" || echo 'see backend/.env')
  Admin      admin  /  $(grep -oP '^ADMIN_PASSWORD=\K.*' "$BACKEND/.env" || echo 'see backend/.env')

  From your phone: connect it to the same wi-fi and open
    http://<this-computer's-LAN-IP>:$WEB_PORT
  then set NEXT_PUBLIC_API_BASE in frontend/.env.local to that same IP
  (http://<LAN-IP>:$API_PORT) and restart, or the browser will call
  localhost and find nothing.

  Ctrl+C to stop.  ./scripts/dev.sh --reset  wipes the local data.

EOF

wait
