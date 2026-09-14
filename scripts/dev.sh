#!/usr/bin/env bash
# Local KunoWorld network: gateway on :8080 and one mock-TEE worker serving every profile.
# Real end-to-end encryption; placeholder video instead of GPUs. Ctrl+C stops both.
set -euo pipefail

cd "$(dirname "$0")/.."
DATA="${KUNO_DATA_DIR:-data}"
mkdir -p "$DATA/logs"

PORT="${KUNO_PORT:-8080}"
# Both web dev-server ports: Playwright runs a second one for the region tests.
export KUNO_CORS_ORIGINS="${KUNO_CORS_ORIGINS:-http://localhost:3000,http://localhost:3001}"
uv run kuno-devkit init --data "$DATA" >/dev/null
# Local runs sign in many test users from one address; production keeps the defaults (20 per IP, 5 per email).
export KUNO_SIGNIN_LINKS_PER_IP="${KUNO_SIGNIN_LINKS_PER_IP:-1000}" KUNO_SIGNIN_LINKS_PER_EMAIL="${KUNO_SIGNIN_LINKS_PER_EMAIL:-100}"
export KUNO_DATA_DIR="$DATA" KUNO_ALLOW_COUNTRY_OVERRIDE=1 KUNO_GATEWAY_URL="http://127.0.0.1:$PORT"
# Dev only: the devkit's KUNO_ADMIN_TOKEN as break-glass (never honoured in production). Operators normally sign in
# by email: uv run kuno-gateway grant-role --email you@example.com --role admin
export KUNO_ALLOW_ADMIN_TOKEN="${KUNO_ALLOW_ADMIN_TOKEN:-1}"

uv run kuno-gateway --port "$PORT" >"$DATA/logs/gateway.log" 2>&1 &
GATEWAY=$!
trap 'kill $GATEWAY ${WORKER:-} 2>/dev/null; wait 2>/dev/null' EXIT INT TERM

for _ in $(seq 1 50); do
  curl -sf "$KUNO_GATEWAY_URL/healthz" >/dev/null && break
  sleep 0.2
done

uv run kuno-worker >"$DATA/logs/worker.log" 2>&1 &
WORKER=$!

echo "Gateway  $KUNO_GATEWAY_URL   (logs: $DATA/logs/)"
echo "API key  $(grep KUNO_DEV_API_KEY "$DATA/dev.env" | cut -d= -f2)"
echo "Ctrl+C to stop."
wait
