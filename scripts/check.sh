#!/usr/bin/env bash
# Every check that runs without GPUs. Use before pushing.
#   scripts/check.sh          protocol + end-to-end + JS SDK + web build/lint/typecheck
#   scripts/check.sh --web    also runs the Playwright browser suite (starts the backend itself)
set -uo pipefail

cd "$(dirname "$0")/.."
ROOT=$PWD
FAILED=()

run() {  # run <label> <dir> <command...>
  local label=$1 dir=$2
  shift 2
  printf '\n\033[1m── %s ──\033[0m\n' "$label"
  if (cd "$dir" && "$@"); then
    printf '\033[32mok\033[0m  %s\n' "$label"
  else
    printf '\033[31mFAILED\033[0m  %s\n' "$label"
    FAILED+=("$label")
  fi
}

run "python: protocol, gateway, worker, validator, JS interop" "$ROOT" uv run pytest -q
run "js sdk: build" "$ROOT/sdk/js" npm run build
run "js sdk: unit tests" "$ROOT/sdk/js" npm test
run "web: typecheck" "$ROOT/platform/web" npm run typecheck
run "web: lint" "$ROOT/platform/web" npm run lint
run "web: build" "$ROOT/platform/web" npm run build

if [[ "${1:-}" == "--web" ]]; then
  if curl -sf http://127.0.0.1:8080/healthz >/dev/null; then
    echo "using the backend already running on :8080"
  else
    echo "starting backend on :8080"
    KUNO_DATA_DIR=/tmp/kuno-web-data KUNO_ALLOW_COUNTRY_OVERRIDE=1 "$ROOT/scripts/dev.sh" >/tmp/kuno-check-backend.log 2>&1 &
    STARTED=$!
    trap 'kill $STARTED 2>/dev/null' EXIT
    for _ in $(seq 1 60); do curl -sf http://127.0.0.1:8080/healthz >/dev/null && break; sleep 1; done
  fi
  run "web: playwright end-to-end" "$ROOT/platform/web" npm run test:e2e
fi

printf '\n'
if ((${#FAILED[@]})); then
  printf '\033[31m%d check(s) failed:\033[0m %s\n' "${#FAILED[@]}" "${FAILED[*]}"
  exit 1
fi
printf '\033[32mall checks passed\033[0m\n'
