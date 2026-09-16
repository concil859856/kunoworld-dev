#!/usr/bin/env bash
# Stage 0 of the KunoWorld test plan: the whole subnet workflow on one CPU machine, with the simulated TEE
# (KUNO_TEE=mock), against a real subtensor chain in Docker. README.md in this directory explains every step.
#
#   localnet.sh up              chain, wallets, subnet, neurons, stake, collateral; gateway, two workers, validator;
#                               then waits until the validator's weights on chain include both miners
#   localnet.sh status          what is running, the chain head, and the validator's weights right now
#   localnet.sh verify [WAIT]   exit 0 only if the validator's weights include both miners (polls up to WAIT seconds)
#   localnet.sh down            stop what `up` started (by PID file and recorded container id); removes the chain
#   localnet.sh reset           down, then delete the localnet data dir (the chain venv is kept)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
DATA="${KUNO_LOCALNET_DIR:-$ROOT/data/localnet}"
RUN="$DATA/run"
LOGS="$DATA/logs"
STATE="$DATA/state.json"

RPC_PORT="${KUNO_LOCALNET_RPC_PORT:-9944}"
GATEWAY_PORT="${KUNO_LOCALNET_GATEWAY_PORT:-8090}"
ENDPOINT="ws://127.0.0.1:$RPC_PORT"
GATEWAY_URL="http://127.0.0.1:$GATEWAY_PORT"
CONTAINER_NAME="${KUNO_LOCALNET_CONTAINER:-kuno-localnet}"
# RaoFoundation's localnet image (runtime spec 458; subtensor main a7ae07e, built 2026-09-14), pinned by digest.
IMAGE="${KUNO_LOCALNET_IMAGE:-ghcr.io/raofoundation/subtensor-localnet:main@sha256:450981f12515af0d7368af2beac8aeb773646f7f90154094f397ce032b9840f7}"
FAST_BLOCKS="${KUNO_LOCALNET_FAST_BLOCKS:-True}" # 250 ms blocks; False runs 12 s blocks
BITTENSOR_VERSION=11.1.0                         # uv.lock's pin for kuno-validator[chain]
TYPER_VERSION=0.27.1                             # btcli 11.1.0 crashes on exit under typer 0.27.2 (README.md)
VALIDATOR_INTERVAL="${KUNO_LOCALNET_VALIDATOR_INTERVAL:-30}"
MIN_COLLATERAL="${KUNO_LOCALNET_MIN_COLLATERAL_PER_GPU:-0.001}"
COLLATERAL_ALPHA="${KUNO_LOCALNET_COLLATERAL_ALPHA:-2}"
MECHANISMS="${KUNO_LOCALNET_MECHANISMS:-2}"
COMMIT_REVEAL="${KUNO_LOCALNET_COMMIT_REVEAL:-0}"
VERIFY_WAIT="${KUNO_LOCALNET_VERIFY_WAIT:-600}"

CHAIN_VENV="$DATA/venv"
WORKSPACE_BIN="$ROOT/.venv/bin"
SERVICES=(validator worker-b worker-a gateway) # in stop order

die() {
  echo "localnet: $*" >&2
  exit 1
}
say() { printf '\n== %s\n' "$*"; }

init_env() {
  command -v uv >/dev/null || die "uv is not installed"
  local uv_bin
  uv_bin="$(dirname "$(command -v uv)")"
  # Every process this script starts gets exactly this environment: nothing leaks in from the caller's shell (KUNO_*,
  # BT_*, a dev database URL). HOME points into the data dir because btcli and the SDK keep wallets, config and caches
  # under ~/.bittensor; uv keeps using the real cache and Python installs.
  BASE_ENV=(
    "PATH=$uv_bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    "HOME=$DATA/home"
    "LANG=C.UTF-8"
    "UV_CACHE_DIR=$(uv cache dir)"
    "UV_PYTHON_INSTALL_DIR=$(uv python dir)"
    "BT_CHAIN_ENDPOINT=$ENDPOINT" # what bittensor resolves --network local to
    "PYTHONUNBUFFERED=1"
  )
  BTCLI="$uv_bin/uvx --quiet --python 3.12 --from bittensor==$BITTENSOR_VERSION --with typer==$TYPER_VERSION btcli"
}

run_clean() { env -i "${BASE_ENV[@]}" "$@"; }

port_in_use() { ss -Hltn "sport = :$1" 2>/dev/null | grep -q .; }

state_get() {
  python3 -c 'import functools, json, sys; print(functools.reduce(lambda d, k: d[k], sys.argv[2].split("."), json.load(open(sys.argv[1]))))' "$STATE" "$1"
}

# ---------------------------------------------------------------- processes, by PID file only

proc_start_time() { awk '{print $22}' "/proc/$1/stat" 2>/dev/null || true; }

# The PID file holds the PID and its kernel start time, so a PID reused by another process is never signalled.
service_pid() {
  local file="$RUN/$1.pid" pid="" start=""
  [[ -f $file ]] || return 1
  read -r pid start <"$file" || true
  [[ -n $pid && -n $start && "$(proc_start_time "$pid")" == "$start" ]] || return 1
  echo "$pid"
}

start_service() { # name, then VAR=value... and the command
  local name=$1
  shift
  # setsid: the service leads its own process group, so `down` stops its children (ffmpeg) with it.
  setsid env -i "${BASE_ENV[@]}" "$@" >"$LOGS/$name.log" 2>&1 </dev/null &
  local pid=$!
  echo "$pid $(proc_start_time "$pid")" >"$RUN/$name.pid"
  echo "$name: pid $pid, log $LOGS/$name.log"
}

stop_service() {
  local name=$1 pid
  if pid="$(service_pid "$name")"; then
    echo "stopping $name (pid $pid)"
    local target=$pid
    [[ "$(ps -o pgid= -p "$pid" | tr -d ' ')" == "$pid" ]] && target="-$pid"
    kill -TERM -- "$target" 2>/dev/null || true
    for _ in $(seq 1 50); do
      service_pid "$name" >/dev/null || break
      sleep 0.2
    done
    if service_pid "$name" >/dev/null; then
      echo "  $name did not stop on SIGTERM; sending SIGKILL"
      kill -KILL -- "$target" 2>/dev/null || true
    fi
  fi
  rm -f "$RUN/$name.pid"
}

# ---------------------------------------------------------------- chain

container_id() { [[ -f "$RUN/chain.cid" ]] && cat "$RUN/chain.cid"; }

chain_running() {
  local cid
  cid="$(container_id)" || return 1
  [[ "$(docker inspect -f '{{.State.Running}}' "$cid" 2>/dev/null)" == true ]]
}

chain_head() {
  curl -sf -m 3 -H 'Content-Type: application/json' \
    -d '{"id":1,"jsonrpc":"2.0","method":"chain_getHeader","params":[]}' "http://127.0.0.1:$RPC_PORT" |
    python3 -c 'import json, sys; print(int(json.load(sys.stdin)["result"]["number"], 16))' 2>/dev/null
}

start_chain() {
  say "subtensor localnet $IMAGE (fast blocks: $FAST_BLOCKS)"
  if docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
    die "a container named $CONTAINER_NAME exists that this data dir has no record of; remove it yourself or set KUNO_LOCALNET_CONTAINER"
  fi
  local cid head=""
  cid="$(docker run -d --name "$CONTAINER_NAME" --label "org.kunoworld.localnet=$DATA" \
    -p "127.0.0.1:$RPC_PORT:9944" "$IMAGE" "$FAST_BLOCKS")"
  echo "$cid" >"$RUN/chain.cid"
  for _ in $(seq 1 180); do
    head="$(chain_head || true)"
    [[ -n $head && $head -ge 3 ]] && break
    chain_running || die "the chain container exited: docker logs ${cid:0:12}"
    sleep 1
  done
  [[ -n $head && $head -ge 3 ]] || die "no blocks on $ENDPOINT after 180 s: docker logs ${cid:0:12}"
  echo "container ${cid:0:12} on $ENDPOINT, block $head"
}

stop_chain() {
  local cid
  cid="$(container_id)" || return 0
  echo "removing chain container ${cid:0:12}"
  docker rm -f "$cid" >/dev/null 2>&1 || true
  rm -f "$RUN/chain.cid"
}

# ---------------------------------------------------------------- services

start_gateway() {
  say "gateway on $GATEWAY_URL (data $DATA/gateway)"
  [[ -f "$DATA/gateway/dev.env" ]] || run_clean "$WORKSPACE_BIN/kuno-devkit" init --data "$DATA/gateway" >/dev/null
  start_service gateway KUNO_DATA_DIR="$DATA/gateway" KUNO_GATEWAY_URL="$GATEWAY_URL" KUNO_ALLOW_COUNTRY_OVERRIDE=1 \
    "$WORKSPACE_BIN/kuno-gateway" --host 127.0.0.1 --port "$GATEWAY_PORT"
  for _ in $(seq 1 100); do
    curl -sf -m 2 "$GATEWAY_URL/healthz" >/dev/null && return 0
    service_pid gateway >/dev/null || die "the gateway exited; see $LOGS/gateway.log"
    sleep 0.3
  done
  die "the gateway does not answer $GATEWAY_URL/healthz; see $LOGS/gateway.log"
}

start_worker() { # service name, miner wallet, profiles
  local service=$1 wallet=$2 profiles=$3 hotkey seed
  hotkey="$(state_get "neurons.$wallet.hotkey")"
  seed="$(state_get "neurons.$wallet.hotkey_seed_file")"
  say "$service: mock-TEE worker for $wallet ($hotkey), profiles $profiles"
  mkdir -p "$DATA/$service"
  start_service "$service" KUNO_DATA_DIR="$DATA/gateway" KUNO_GATEWAY_URL="$GATEWAY_URL" KUNO_TEE=mock KUNO_BACKEND=mock \
    KUNO_PROFILES="$profiles" KUNO_HOTKEY_SEED_FILE="$seed" KUNO_MINER_HOTKEY="$hotkey" KUNO_WORKDIR="$DATA/$service" \
    "$WORKSPACE_BIN/kuno-worker"
}

start_validator() {
  local netuid=$1
  say "validator on netuid $netuid, a round every ${VALIDATOR_INTERVAL}s (collateral required: $MIN_COLLATERAL alpha per GPU)"
  mkdir -p "$DATA/validator"
  ln -sfn "$DATA/gateway/dev.env" "$DATA/validator/dev.env" # the validator API key, manifest and owner key
  start_service validator KUNO_DATA_DIR="$DATA/validator" KUNO_GATEWAY_URL="$GATEWAY_URL" \
    KUNO_CHAIN_ENDPOINT="$ENDPOINT" KUNO_MIN_COLLATERAL_PER_GPU="$MIN_COLLATERAL" \
    "$CHAIN_VENV/bin/kuno-validator" run --role main --interval "$VALIDATOR_INTERVAL" --netuid "$netuid" --network local \
    --wallet-name validator --wallet-hotkey default --wallet-path "$DATA/wallets" \
    --canary ltx-2.5-fast --canary ltx-2.5-pro
}

verify() { run_clean "$CHAIN_VENV/bin/python" "$HERE/verify.py" --state "$STATE" --wait "$1"; }

# ---------------------------------------------------------------- commands

cmd_up() {
  init_env
  [[ -f "$RUN/chain.cid" ]] && die "already up, or not cleanly stopped: run '$0 down' first"
  local service
  for service in "${SERVICES[@]}"; do
    service_pid "$service" >/dev/null && die "$service is still running: run '$0 down' first"
  done
  command -v docker >/dev/null || die "docker is not installed"
  [[ -x "$WORKSPACE_BIN/kuno-gateway" && -x "$WORKSPACE_BIN/kuno-worker" && -x "$WORKSPACE_BIN/kuno-devkit" ]] ||
    die "no workspace venv with the gateway and worker at $ROOT/.venv: run 'uv sync' in $ROOT"
  port_in_use "$RPC_PORT" && die "port $RPC_PORT is taken (set KUNO_LOCALNET_RPC_PORT)"
  port_in_use "$GATEWAY_PORT" && die "port $GATEWAY_PORT is taken (set KUNO_LOCALNET_GATEWAY_PORT)"
  mkdir -p "$RUN" "$LOGS" "$DATA/home"
  touch "$DATA/.kuno-localnet"
  trap 'echo "localnet: up failed; logs in $LOGS. Run '"'"'$0 down'"'"' to stop what was started." >&2' ERR

  say "chain venv $CHAIN_VENV: kuno-validator[chain,canary] exactly as uv.lock pins it"
  (cd "$ROOT" && UV_PROJECT_ENVIRONMENT="$CHAIN_VENV" uv sync --frozen --no-dev --package kuno-validator \
    --extra chain --extra canary --quiet)

  start_chain
  say "chain setup (log $LOGS/setup-chain.log)"
  # Passed as arguments: setup runs under env -i, so the caller's KUNO_LOCALNET_* variables don't reach it.
  local setup_args=(--endpoint "$ENDPOINT" --data "$DATA" --collateral-alpha "$COLLATERAL_ALPHA" --mechanisms "$MECHANISMS")
  if [[ $COMMIT_REVEAL == 1 ]]; then setup_args+=(--commit-reveal); fi
  run_clean KUNO_LOCALNET_BTCLI="$BTCLI" "$CHAIN_VENV/bin/python" "$HERE/setup_chain.py" "${setup_args[@]}" 2>&1 |
    tee "$LOGS/setup-chain.log"

  start_gateway
  start_worker worker-a miner-a ltx-2.5-fast
  start_worker worker-b miner-b ltx-2.5-pro

  say "paid customer jobs, one per miner (log $LOGS/drive-jobs.log)"
  run_clean "$CHAIN_VENV/bin/python" "$HERE/drive_jobs.py" --gateway "$GATEWAY_URL" --data "$DATA/gateway" \
    --profile ltx-2.5-fast --profile ltx-2.5-pro 2>&1 | tee "$LOGS/drive-jobs.log"

  start_validator "$(state_get netuid)"

  say "waiting for the validator's weights on chain (up to ${VERIFY_WAIT}s)"
  if verify "$VERIFY_WAIT"; then
    say "Stage 0 is up. '$0 status' shows it; '$0 down' stops it."
  else
    die "the validator's weights do not include both miners; see $LOGS/validator.log ('$0 down' stops everything)"
  fi
}

cmd_status() {
  init_env
  local cid pid service
  if cid="$(container_id)"; then
    if chain_running; then
      printf '%-10s running  container %s, %s, block %s\n' chain "${cid:0:12}" "$ENDPOINT" "$(chain_head || echo '?')"
    else
      printf '%-10s stopped  container %s is not running\n' chain "${cid:0:12}"
    fi
  else
    printf '%-10s not started\n' chain
  fi
  for service in gateway worker-a worker-b validator; do
    if pid="$(service_pid "$service")"; then
      printf '%-10s running  pid %s, log %s\n' "$service" "$pid" "$LOGS/$service.log"
    elif [[ -f "$RUN/$service.pid" ]]; then
      printf '%-10s exited   log %s\n' "$service" "$LOGS/$service.log"
    else
      printf '%-10s not started\n' "$service"
    fi
  done
  if service_pid gateway >/dev/null; then
    curl -sf -m 2 "$GATEWAY_URL/healthz" >/dev/null && echo "gateway answers $GATEWAY_URL/healthz" || echo "gateway does not answer $GATEWAY_URL/healthz"
  fi
  if chain_running && [[ -f $STATE ]]; then
    verify 0 || true
  fi
}

cmd_verify() {
  init_env
  [[ -f $STATE ]] || die "no $STATE: run '$0 up' first"
  verify "${1:-0}"
}

cmd_down() {
  local service file
  for service in "${SERVICES[@]}"; do stop_service "$service"; done
  for file in "$RUN"/*.pid; do
    [[ -e $file ]] && stop_service "$(basename "$file" .pid)"
  done
  command -v docker >/dev/null && stop_chain
  echo "localnet stopped (state kept in $DATA; '$0 reset' deletes it)"
}

cmd_reset() {
  cmd_down
  if [[ ! -f "$DATA/.kuno-localnet" ]]; then
    echo "nothing to reset at $DATA"
    return 0
  fi
  find "$DATA" -mindepth 1 -maxdepth 1 ! -name venv -exec rm -rf {} +
  echo "deleted the localnet state in $DATA (kept the chain venv)"
}

case "${1:-}" in
up) cmd_up ;;
status) cmd_status ;;
verify) cmd_verify "${2:-0}" ;;
down) cmd_down ;;
reset) cmd_reset ;;
*)
  sed -n '2,10p' "$0"
  exit 2
  ;;
esac
