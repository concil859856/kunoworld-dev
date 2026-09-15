#!/usr/bin/env bash
# One-command smoke test of KunoWorld's LTX-2.5 worker image on a rented GPU server. README.md in this directory
# says what to rent and what every output file is.
#
#   HF_TOKEN=... GITHUB_TOKEN=... ./ltx-smoke.sh      the real model (KUNO_BACKEND=real) on this machine's GPU
#   KUNO_SMOKE_MOCK=1 ./ltx-smoke.sh                  dry run without a GPU: local images, KUNO_BACKEND=mock
#   KUNO_SMOKE_FAMILY=h3 GITHUB_TOKEN=... ./ltx-smoke.sh   MiniMax H3 instead: 4 GPUs, SGLang, the ungated FL2VA weights
#
# Everything runs in containers on 127.0.0.1 and nothing touches a chain: kuno-devkit init (mock-worker image), a dev
# gateway on SQLite (gateway image), then for each profile in turn kuno-plan, one worker container with the simulated
# TEE (worker image), one Standard-mode job submitted with the dev API key, the MP4 downloaded and checked with ffprobe.
# Timings, GPU memory and host RAM samples, results.json and every log end up in one tarball. Containers are removed on
# exit; the weights and the results stay.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------- settings (README.md lists them all)

MOCK="${KUNO_SMOKE_MOCK:-0}"
case "$MOCK" in 0 | 1) ;; *) echo "ltx-smoke: KUNO_SMOKE_MOCK must be 0 or 1" >&2 && exit 2 ;; esac
FAMILY="${KUNO_SMOKE_FAMILY:-ltx}"
case "$FAMILY" in ltx | h3) ;; *) echo "ltx-smoke: KUNO_SMOKE_FAMILY must be ltx or h3" >&2 && exit 2 ;; esac
if [ "$FAMILY" = h3 ]; then MOUNT=/models/h3; else MOUNT=/models/ltx-2.5; fi
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BASE="${KUNO_SMOKE_DIR:-$PWD/kuno-smoke}"
MODELS="${KUNO_SMOKE_MODELS_DIR:-$BASE/models/${MOUNT#/models/}}"
RUN_DIR="$BASE/runs/$STAMP"
DATA="$RUN_DIR/data"
RESULTS="$RUN_DIR/results"
LOGS="$RESULTS/logs"
JOBS="$RESULTS/jobs"
STATE="$RESULTS/state.tsv"
TARBALL="$RUN_DIR/ltx-smoke-$STAMP.tar.gz"
PORT="${KUNO_SMOKE_PORT:-18180}"
GATEWAY_URL="http://127.0.0.1:$PORT"
LABEL="kuno-smoke=$STAMP"
PREFIX="kuno-smoke-$STAMP"

REGISTRY="${KUNO_SMOKE_REGISTRY:-ghcr.io/concil859856}"
if [ "$MOCK" = 1 ]; then
  WORKER_IMAGE="${KUNO_SMOKE_WORKER_IMAGE:-kuno-worker:$FAMILY}"
  GATEWAY_IMAGE="${KUNO_SMOKE_GATEWAY_IMAGE:-kunoworld/gateway:local}"
  DEVKIT_IMAGE="${KUNO_SMOKE_DEVKIT_IMAGE:-kunoworld/mock-worker:local}"
  BACKEND="${KUNO_SMOKE_BACKEND:-mock}"
else
  if [ "$FAMILY" = h3 ]; then WORKER_TAG_DEFAULT=h3-0.1.0-0ad70874cd6b; else WORKER_TAG_DEFAULT=ltx-0.1.0-0ad70874cd6b; fi
  WORKER_IMAGE="${KUNO_SMOKE_WORKER_IMAGE:-$REGISTRY/kunoworld-worker:${KUNO_SMOKE_WORKER_TAG:-$WORKER_TAG_DEFAULT}}"
  GATEWAY_IMAGE="${KUNO_SMOKE_GATEWAY_IMAGE:-$REGISTRY/kunoworld-gateway:${KUNO_SMOKE_GATEWAY_TAG:-aa11a3ff9e34}}"
  DEVKIT_IMAGE="${KUNO_SMOKE_DEVKIT_IMAGE:-$REGISTRY/kunoworld-mock-worker:${KUNO_SMOKE_DEVKIT_TAG:-70f74725510f}}"
  # real: the resident diffusers pipelines, the only LTX runtime the image contains (README.md, "Why KUNO_BACKEND=real").
  BACKEND="${KUNO_SMOKE_BACKEND:-real}"
fi
SKIP_LOGIN="${KUNO_SMOKE_SKIP_LOGIN:-$MOCK}"
# always: pull every image; missing: use an image already on this machine (e.g. one built here) and pull the rest.
PULL="${KUNO_SMOKE_PULL:-always}"
case "$PULL" in always | missing) ;; *) echo "ltx-smoke: KUNO_SMOKE_PULL must be always or missing" >&2 && exit 2 ;; esac
REGISTRY_HOST="${REGISTRY%%/*}"
GHCR_USER="${KUNO_SMOKE_REGISTRY_USER:-concil859856}"
if [ "$FAMILY" = h3 ]; then
  # H3 renders 5-14 s at 768p only (1344x768 for 16:9); its SGLang server loads a Hugging Face cache.
  D_PROFILES=h3 D_DURATION=5 D_RESOLUTION=768p D_REPO=MiniMaxAI/MiniMax-H3 D_REVISION=main D_DRIVER=580 D_GPU_MIB=140000 D_GPUS=4
else
  D_PROFILES=ltx-2.5-fast,ltx-2.5-pro D_DURATION=2 D_RESOLUTION=720p D_REPO=Lightricks/LTX-2.5-Diffusers
  D_REVISION=426936f8b22dc28e4def61e515478b0b7e4a53cc D_DRIVER=570 D_GPU_MIB=80000 D_GPUS=1 # LTX revision: main on 2026-09-15
fi
PROFILES="${KUNO_SMOKE_PROFILES:-$D_PROFILES}"
DURATION="${KUNO_SMOKE_DURATION:-$D_DURATION}"
RESOLUTION="${KUNO_SMOKE_RESOLUTION:-$D_RESOLUTION}"
ASPECT="${KUNO_SMOKE_ASPECT:-16:9}"
FPS="${KUNO_SMOKE_FPS:-24}"
AUDIO="${KUNO_SMOKE_AUDIO:-1}"
LTX_OFFLOAD="${KUNO_SMOKE_LTX_OFFLOAD:-auto}"
WEIGHTS_VERIFY="${KUNO_SMOKE_WEIGHTS_VERIFY:-full}"
HF_REPO="${KUNO_SMOKE_HF_REPO:-$D_REPO}"
HF_REVISION="${KUNO_SMOKE_HF_REVISION:-$D_REVISION}"
DOWNLOAD_WORKERS="${KUNO_SMOKE_DOWNLOAD_WORKERS:-4}"
REGISTER_TIMEOUT="${KUNO_SMOKE_REGISTER_TIMEOUT:-2700}"
JOB_TIMEOUT="${KUNO_SMOKE_JOB_TIMEOUT:-1800}"
GPU_CHECK_IMAGE="${KUNO_SMOKE_GPU_CHECK_IMAGE:-ubuntu:24.04}"
MIN_DRIVER="${KUNO_SMOKE_MIN_DRIVER:-$D_DRIVER}"
MIN_GPU_MIB="${KUNO_SMOKE_MIN_GPU_MIB:-$D_GPU_MIB}"
MIN_GPUS="${KUNO_SMOKE_MIN_GPUS:-$D_GPUS}"
# Where the test customer is, sent as x-kuno-country (the dev gateway honours it). H3 is only served outside the
# licence's Excluded Territories, and a request from an unknown country counts as excluded, so H3 runs need it.
COUNTRY="${KUNO_SMOKE_COUNTRY:-}"
COUNTRY_HEADER=()
if [ -n "$COUNTRY" ]; then COUNTRY_HEADER=(-H "x-kuno-country: $COUNTRY"); fi
# H3 is offered in Private mode only (no Standard price), so its job goes through the kunoworld SDK, mounted from
# KUNO_SMOKE_SDK_DIR, ./sdk beside this script, or the repository's sdk/python/src.
if [ "$FAMILY" = h3 ]; then D_PRIVACY=private; else D_PRIVACY=standard; fi
PRIVACY="${KUNO_SMOKE_PRIVACY:-$D_PRIVACY}"
# h3-reference renders reference_to_video from KUNO_SMOKE_REFERENCE_IMAGE; KUNO_SMOKE_PROMPT replaces the built-in prompt.
REFERENCE_IMAGE="${KUNO_SMOKE_REFERENCE_IMAGE:-}"
PROMPT_OVERRIDE="${KUNO_SMOKE_PROMPT:-}"
SDK_DIR="${KUNO_SMOKE_SDK_DIR:-}"
if [ -z "$SDK_DIR" ]; then
  for candidate in "$HERE/sdk" "$HERE/../../sdk/python/src"; do
    if [ -d "$candidate/kunoworld" ]; then SDK_DIR="$(cd "$candidate" && pwd)" && break; fi
  done
fi
MIN_DISK_GB="${KUNO_SMOKE_MIN_DISK_GB:-200}"
MIN_RAM_GB="${KUNO_SMOKE_MIN_RAM_GB:-64}"

RUN_STARTED=0
MAIN_DONE=0
SAMPLER_PID=""
DOCKER_CFG=""
PREREQ_FAILED=0
PREREQ_LINES=()

# ---------------------------------------------------------------- output and bookkeeping

say() { printf '\n== %s\n' "$*"; }
info() { printf '        %s\n' "$*"; }
ok() { printf '  ok    %s\n' "$*"; }
warn() { printf '  WARN  %s\n' "$*"; }
bad() { printf '  FAIL  %s\n' "$*"; }
now() { date +%s.%N; }
since() { awk -v a="$1" -v b="$(now)" 'BEGIN { printf "%.1f", b - a }'; }

# One "key<TAB>value" line per fact; smoke.py results turns the file into results.json.
state() {
  if [ "$RUN_STARTED" = 1 ]; then
    printf '%s\t%s\n' "$1" "$(printf '%s' "$2" | tr '\t\n' '  ')" >>"$STATE"
  fi
}

die() {
  printf '\nltx-smoke: %s\n' "$*" >&2
  state failure "$*"
  exit 1
}

container_running() { [ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null || true)" = true ]; }
port_in_use() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
gpu_args() { if [ "$MOCK" != 1 ]; then printf '%s\n' --gpus all; fi; }

# smoke.py inside an image, as the invoking user, with the results dir writable and the gateway data dir read-only.
helper() {
  local image="$1"
  shift
  local sdk=()
  if [ -n "$SDK_DIR" ]; then sdk=(-v "$SDK_DIR:/sdk:ro" -e PYTHONPATH=/sdk); fi
  docker run --rm --label "$LABEL" --network host --user "$(id -u):$(id -g)" -e HOME=/tmp -e USER=kuno-smoke \
    ${sdk[@]+"${sdk[@]}"} -v "$HERE/smoke.py:/smoke/smoke.py:ro" -v "$RESULTS:/out" -v "$DATA:/var/lib/kuno/data:ro" \
    --entrypoint python "$image" -W ignore /smoke/smoke.py "$@"
}

# ---------------------------------------------------------------- prerequisites

pre_ok() {
  ok "$1: $2"
  PREREQ_LINES+=("check.$1"$'\t'"ok: $2")
}
pre_fail() {
  bad "$1: $2"
  PREREQ_LINES+=("check.$1"$'\t'"fail: $2")
  PREREQ_FAILED=1
}
pre_skip() {
  printf '  skip  %s: %s\n' "$1" "$2"
  PREREQ_LINES+=("check.$1"$'\t'"skipped: $2")
}

check_prerequisites() {
  if [ "$MOCK" = 1 ]; then say "prerequisites (dry run, KUNO_SMOKE_MOCK=1: no GPU checks, no downloads)"; else say "prerequisites"; fi

  local cmd missing=()
  for cmd in docker curl ffprobe tar awk df du; do
    command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
  done
  if [ "$MOCK" != 1 ] && ! command -v nvidia-smi >/dev/null 2>&1; then missing+=(nvidia-smi); fi
  if [ ${#missing[@]} -eq 0 ]; then
    pre_ok commands "docker, curl, ffprobe, tar$([ "$MOCK" = 1 ] || printf ', nvidia-smi')"
  else
    pre_fail commands "missing ${missing[*]} (ffprobe: apt-get install -y ffmpeg; nvidia-smi ships with the NVIDIA driver)"
  fi

  local docker_ok=0 version
  if version="$(docker info --format '{{.ServerVersion}}' 2>/dev/null)" && [ -n "$version" ]; then
    docker_ok=1
    pre_ok docker "Docker $version"
    HOST_DOCKER="$version"
  else
    pre_fail docker "cannot reach the Docker daemon (is it running, and may this user run docker?)"
  fi

  if [ "$MOCK" = 1 ]; then
    pre_skip tokens "the dry run uses local images and downloads no weights"
  else
    if [ -n "${HF_TOKEN:-}" ]; then pre_ok HF_TOKEN "set"
    elif [ "$FAMILY" = h3 ]; then pre_ok HF_TOKEN "not needed: $HF_REPO is not gated"
    else pre_fail HF_TOKEN "not set: export a Hugging Face read token of the account that accepted the LTX-2.5 licence"; fi
    if [ "$SKIP_LOGIN" = 1 ]; then
      pre_skip GITHUB_TOKEN "KUNO_SMOKE_SKIP_LOGIN=1"
    elif [ -n "${GITHUB_TOKEN:-}" ]; then
      pre_ok GITHUB_TOKEN "set"
    else
      pre_fail GITHUB_TOKEN "not set: export a GitHub token with read:packages for $REGISTRY"
    fi
  fi

  if [ "$FAMILY" = h3 ]; then
    if [ -n "$COUNTRY" ]; then
      pre_ok country "$COUNTRY, sent as x-kuno-country"
    else
      pre_fail country "KUNO_SMOKE_COUNTRY is not set: H3 is served only to customers outside the US, EU, UK and Korea; set the test customer's two-letter country"
    fi
  fi

  case ",$PROFILES," in
    *,h3-reference,*)
      if [ -f "$REFERENCE_IMAGE" ]; then pre_ok reference-image "$REFERENCE_IMAGE"
      else pre_fail reference-image "h3-reference needs KUNO_SMOKE_REFERENCE_IMAGE, an image file"; fi ;;
  esac

  if [ "$PRIVACY" = private ]; then
    if [ -n "$SDK_DIR" ]; then
      pre_ok sdk "kunoworld SDK from $SDK_DIR (Private mode)"
    else
      pre_fail sdk "Private mode needs the kunoworld SDK: copy sdk/python/src/kunoworld to $HERE/sdk/ or set KUNO_SMOKE_SDK_DIR"
    fi
  fi

  if [ "$MOCK" = 1 ]; then
    pre_skip gpu "dry run"
  elif command -v nvidia-smi >/dev/null 2>&1; then
    local query major
    if ! query="$(nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader,nounits 2>&1)"; then
      pre_fail nvidia-smi "nvidia-smi failed: $(printf '%s\n' "$query" | head -n 1)"
    else
      HOST_GPU="$(printf '%s\n' "$query" | head -n 1 | awk -F', *' '{ print $1 }')"
      HOST_DRIVER="$(printf '%s\n' "$query" | head -n 1 | awk -F', *' '{ print $2 }')"
      HOST_GPU_MIB="$(printf '%s\n' "$query" | awk -F', *' 'BEGIN { m = 0 } $3 + 0 > m { m = $3 + 0 } END { print m }')"
      HOST_GPU_COUNT="$(printf '%s\n' "$query" | grep -c .)"
      major="${HOST_DRIVER%%.*}"
      if [ "$major" -ge "$MIN_DRIVER" ] 2>/dev/null; then
        pre_ok driver "NVIDIA $HOST_DRIVER"
      else
        pre_fail driver "NVIDIA $HOST_DRIVER is older than R$MIN_DRIVER, which the image's CUDA 12.8 PyTorch needs: rent a host image with R570 or newer"
      fi
      if [ "$HOST_GPU_MIB" -ge "$MIN_GPU_MIB" ]; then
        pre_ok gpu-memory "$HOST_GPU_COUNT x $HOST_GPU, $HOST_GPU_MIB MiB on the largest"
      else
        pre_fail gpu-memory "$HOST_GPU has $HOST_GPU_MIB MiB; $FAMILY needs $MIN_GPU_MIB MiB per GPU"
      fi
      if [ "$HOST_GPU_COUNT" -ge "$MIN_GPUS" ]; then
        pre_ok gpu-count "$HOST_GPU_COUNT (needs $MIN_GPUS)"
      else
        pre_fail gpu-count "$HOST_GPU_COUNT GPU(s); $FAMILY needs $MIN_GPUS in one worker"
      fi
    fi
  fi

  local ram_kib
  ram_kib="$(awk '/^MemTotal:/ { print $2 }' /proc/meminfo)"
  HOST_RAM_GB="$(awk -v k="$ram_kib" 'BEGIN { printf "%.1f", k * 1024 / 1e9 }')"
  if [ "$MOCK" = 1 ]; then
    pre_skip ram "$HOST_RAM_GB GB (not judged in a dry run)"
  elif awk -v k="$ram_kib" -v m="$MIN_RAM_GB" 'BEGIN { exit !(k * 1024 >= m * 1e9) }'; then
    pre_ok ram "$HOST_RAM_GB GB"
  else
    pre_fail ram "$HOST_RAM_GB GB is less than $MIN_RAM_GB GB; loading the bf16 weights needs the host RAM"
  fi

  mkdir -p "$BASE" "$MODELS"
  local free_gb have_gb
  free_gb="$(df -Pk "$MODELS" | awk 'NR == 2 { printf "%d", $4 * 1024 / 1e9 }')"
  have_gb="$(du -sk "$MODELS" 2>/dev/null | awk '{ printf "%d", $1 * 1024 / 1e9 }')"
  HOST_DISK_FREE_GB="$free_gb"
  if [ "$MOCK" = 1 ]; then
    pre_skip disk "$free_gb GB free under $MODELS (not judged in a dry run)"
  elif [ $((free_gb + have_gb)) -ge "$MIN_DISK_GB" ]; then
    pre_ok disk "$free_gb GB free under $MODELS, $have_gb GB of weights already there"
  else
    pre_fail disk "$free_gb GB free under $MODELS (+$have_gb GB already downloaded) is less than $MIN_DISK_GB GB: set KUNO_SMOKE_DIR to a larger disk"
  fi

  if [ "$MOCK" = 1 ]; then
    pre_skip docker-gpu "dry run"
  elif [ -z "${HOST_GPU:-}" ]; then
    pre_skip docker-gpu "no GPU was found on the host (above)"
  elif [ "$docker_ok" = 1 ]; then
    local out
    if out="$(docker run --rm --label "$LABEL" --gpus all "$GPU_CHECK_IMAGE" nvidia-smi -L 2>&1)"; then
      pre_ok docker-gpu "$(printf '%s\n' "$out" | grep -c '^GPU ') GPU(s) visible inside a container"
    else
      pre_fail docker-gpu "docker run --gpus all failed: $(printf '%s\n' "$out" | tail -n 1). Install nvidia-container-toolkit, run 'nvidia-ctk runtime configure --runtime=docker' and restart Docker"
    fi
  fi

  if port_in_use "$PORT"; then
    pre_fail port "127.0.0.1:$PORT is in use: set KUNO_SMOKE_PORT"
  else
    pre_ok port "127.0.0.1:$PORT is free"
  fi

  if [ "$MOCK" = 1 ] && [ "$docker_ok" = 1 ]; then
    local image
    for image in "$WORKER_IMAGE" "$GATEWAY_IMAGE" "$DEVKIT_IMAGE"; do
      if docker image inspect "$image" >/dev/null 2>&1; then
        pre_ok "image $image" "present locally"
      else
        pre_fail "image $image" "not on this machine; the dry run uses local images (set KUNO_SMOKE_WORKER_IMAGE, _GATEWAY_IMAGE or _DEVKIT_IMAGE)"
      fi
    done
  fi

  if [ "$PREREQ_FAILED" = 1 ]; then
    printf '\nltx-smoke: prerequisites failed (above); nothing was started\n' >&2
    exit 2
  fi
}

# ---------------------------------------------------------------- run setup and teardown

begin_run() {
  mkdir -p "$DATA" "$LOGS" "$JOBS"
  : >"$STATE"
  RUN_STARTED=1
  local line
  for line in "${PREREQ_LINES[@]}"; do printf '%s\n' "$line" >>"$STATE"; done
  state mode "$([ "$MOCK" = 1 ] && printf mock || printf gpu)"
  state started_epoch "$(now)"
  state backend "$BACKEND"
  state profiles "$PROFILES"
  state image.worker "$WORKER_IMAGE"
  state image.gateway "$GATEWAY_IMAGE"
  state image.devkit "$DEVKIT_IMAGE"
  local key
  for key in FAMILY COUNTRY PRIVACY DURATION RESOLUTION ASPECT FPS AUDIO LTX_OFFLOAD WEIGHTS_VERIFY HF_REPO HF_REVISION GATEWAY_URL MODELS DATA; do
    state "setting.$(printf '%s' "$key" | tr '[:upper:]' '[:lower:]')" "${!key}"
  done
  state host.kernel "$(uname -r)"
  state host.cpu "$(awk -F': ' '/^model name/ { print $2; exit }' /proc/cpuinfo)"
  state host.cpus "$(getconf _NPROCESSORS_ONLN)"
  state host.ram_total_gb "$HOST_RAM_GB"
  state host.disk_free_gb "$HOST_DISK_FREE_GB"
  state host.docker "${HOST_DOCKER:-}"
  state host.gpu "${HOST_GPU:-none}"
  state host.gpu_count "${HOST_GPU_COUNT:-0}"
  state host.gpu_mem_mib "${HOST_GPU_MIB:-0}"
  state host.nvidia_driver "${HOST_DRIVER:-none}"
  printf '\nrun %s: results in %s\n' "$STAMP" "$RESULTS"
}

# epoch, host RAM total and used (MemTotal - MemAvailable), and the busiest GPU's memory and utilization, every second.
start_sampler() {
  local file="$RESULTS/samples.csv"
  printf 'epoch_s,mem_total_kib,mem_used_kib,gpu_mem_used_mib,gpu_mem_total_mib,gpu_util_pct\n' >"$file"
  (
    trap - EXIT INT TERM
    set +e
    while :; do
      mem="$(awk '/^MemTotal:/ { t = $2 } /^MemAvailable:/ { a = $2 } END { printf "%d,%d", t, t - a }' /proc/meminfo)"
      gpu=",,"
      if [ "$MOCK" != 1 ]; then
        gpu="$(nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits 2>/dev/null |
          awk -F', *' 'BEGIN { u = -1 } $1 + 0 > u { u = $1 + 0; t = $2; g = $3 } END { if (u >= 0) printf "%s,%s,%s", u, t, g; else printf ",," }')"
      fi
      printf '%s,%s,%s\n' "$(date +%s)" "$mem" "${gpu:-,,}"
      sleep 1
    done >>"$file"
  ) &
  SAMPLER_PID=$!
}

# Leaves the log of every container this run created in logs/, then removes the container.
remove_containers() {
  local id name
  for id in $(docker ps -aq --filter "label=$LABEL" 2>/dev/null); do
    name="$(docker inspect -f '{{.Name}}' "$id" 2>/dev/null | sed 's#^/##')"
    docker stop -t 60 "$id" >/dev/null 2>&1
    if [ -n "$name" ] && [ ! -s "$LOGS/${name#"$PREFIX"-}.log" ]; then
      docker logs "$id" >"$LOGS/${name#"$PREFIX"-}.log" 2>&1
    fi
    docker rm -f "$id" >/dev/null 2>&1
  done
}

# Replaces any secret value that reached a log with [redacted]. The values never go on a command line.
redact() {
  local values=() value name file
  if [ -r "$DATA/dev.env" ]; then
    for name in KUNO_DEV_API_KEY KUNO_ADMIN_TOKEN KUNO_VALIDATOR_API_KEY; do
      value="$(awk -F= -v k="$name" '$1 == k { print substr($0, length(k) + 2) }' "$DATA/dev.env")"
      if [ -n "$value" ]; then values+=("$value"); fi
    done
  fi
  if [ -n "${HF_TOKEN:-}" ]; then values+=("$HF_TOKEN"); fi
  if [ -n "${GITHUB_TOKEN:-}" ]; then values+=("$GITHUB_TOKEN"); fi
  for value in ${values[@]+"${values[@]}"}; do
    while IFS= read -r file; do
      SECRET="$value" awk '{ s = ENVIRON["SECRET"]; out = ""; while ((i = index($0, s)) > 0) { out = out substr($0, 1, i - 1) "[redacted]"; $0 = substr($0, i + length(s)) } print out $0 }' \
        "$file" >"$file.redacted" && mv "$file.redacted" "$file"
    done < <(grep -rlF --exclude='*.mp4' -f <(printf '%s\n' "$value") "$RESULTS" 2>/dev/null || true)
  done
}

on_exit() {
  local code=$?
  trap - EXIT INT TERM
  set +e
  if [ -n "$SAMPLER_PID" ]; then
    kill "$SAMPLER_PID" 2>/dev/null
    wait "$SAMPLER_PID" 2>/dev/null
  fi
  if [ -n "$DOCKER_CFG" ]; then rm -rf "$DOCKER_CFG"; fi
  if [ "$RUN_STARTED" != 1 ]; then exit "$code"; fi
  if [ "$MAIN_DONE" != 1 ]; then state failure "the run stopped early (exit code $code); see logs/"; fi

  say "cleanup"
  remove_containers
  info "removed this run's containers (label $LABEL)"
  state finished_epoch "$(now)"
  redact

  say "results"
  local result=1
  if docker image inspect "$GATEWAY_IMAGE" >/dev/null 2>&1; then
    helper "$GATEWAY_IMAGE" results --dir /out
    result=$?
  else
    printf '{"result": "fail", "failures": ["the gateway image is missing, so results were not assembled; see state.tsv"]}\n' >"$RESULTS/results.json"
    echo "RESULT: FAIL (see $RESULTS/state.tsv)"
  fi
  tar -C "$RUN_DIR" -czf "$TARBALL" results
  printf '\nresults.json  %s\ntarball       %s (%s)\ngateway data  %s (dev keys: not in the tarball)\nweights       %s (kept)\n' \
    "$RESULTS/results.json" "$TARBALL" "$(du -h "$TARBALL" | cut -f1)" "$DATA" "$MODELS"
  if [ "$MAIN_DONE" = 1 ] && [ "$result" = 0 ]; then exit 0; fi
  if [ "$code" = 0 ]; then exit 1; fi
  exit "$code"
}

# ---------------------------------------------------------------- steps

pull_images() {
  local image started t
  say "images"
  if [ "$MOCK" = 1 ]; then
    info "dry run: local images, nothing pulled"
    state timing.image_pull_s skipped
  else
    if [ "$SKIP_LOGIN" != 1 ]; then
      DOCKER_CFG="$(mktemp -d)"
      chmod 700 "$DOCKER_CFG"
      # A throwaway Docker config: the token is read from stdin and never lands in ~/.docker/config.json.
      if ! printf '%s' "$GITHUB_TOKEN" | DOCKER_CONFIG="$DOCKER_CFG" docker login "$REGISTRY_HOST" -u "$GHCR_USER" --password-stdin >"$LOGS/registry-login.log" 2>&1; then
        die "docker login $REGISTRY_HOST failed ($(tail -n 1 "$LOGS/registry-login.log")): GITHUB_TOKEN needs read:packages and access to $REGISTRY"
      fi
      ok "logged in to $REGISTRY_HOST as $GHCR_USER"
    fi
    started="$(now)"
    for image in "$WORKER_IMAGE" "$GATEWAY_IMAGE" "$DEVKIT_IMAGE"; do
      t="$(now)"
      if [ "$PULL" = missing ] && docker image inspect "$image" >/dev/null 2>&1; then
        info "using the local $image (KUNO_SMOKE_PULL=missing)"
        continue
      fi
      info "pulling $image"
      if ! DOCKER_CONFIG="${DOCKER_CFG:-${DOCKER_CONFIG:-$HOME/.docker}}" docker pull "$image" >>"$LOGS/pull.log" 2>&1; then
        die "could not pull $image ($(tail -n 1 "$LOGS/pull.log")); override with KUNO_SMOKE_REGISTRY, KUNO_SMOKE_*_TAG or KUNO_SMOKE_*_IMAGE"
      fi
      state "timing.pull.${image##*/}_s" "$(since "$t")"
    done
    state timing.image_pull_s "$(since "$started")"
    ok "images ready in $(since "$started")s"
    if [ -n "$DOCKER_CFG" ]; then
      rm -rf "$DOCKER_CFG"
      DOCKER_CFG=""
    fi
  fi
  for image in worker:"$WORKER_IMAGE" gateway:"$GATEWAY_IMAGE" devkit:"$DEVKIT_IMAGE"; do
    state "image.${image%%:*}.id" "$(docker image inspect -f '{{.Id}}' "${image#*:}")"
  done
}

# H3: the SGLang servers resolve MiniMaxAI/MiniMax-H3 in a Hugging Face cache (HF_HUB_CACHE=/models/h3, offline), so this
# writes that layout for the checkpoint variant each profile uses: FL2VA for h3 and h3-turbo, Ref2VA for h3-reference.
fetch_h3_weights() {
  local started code=0 patterns='"*.json","LICENSE","README.md"'
  started="$(now)"
  case ",$PROFILES," in *,h3,* | *,h3-turbo,*) patterns+=',"FL2VA/*"' ;; esac
  case ",$PROFILES," in *,h3-reference,*) patterns+=',"Ref2VA/*"' ;; esac
  docker run --rm --label "$LABEL" --name "$PREFIX-weights" --user "$(id -u):$(id -g)" \
    -e HF_TOKEN -e HF_HUB_OFFLINE=0 -e HF_HUB_DISABLE_TELEMETRY=1 -e HF_HUB_DISABLE_PROGRESS_BARS=1 \
    -e HF_XET_HIGH_PERFORMANCE=1 -e HOME=/tmp -v "$MODELS:$MOUNT" -v "$RESULTS:/out" --entrypoint python "$WORKER_IMAGE" -W ignore -c "
import json, time
from huggingface_hub import snapshot_download
started = time.time()
path = snapshot_download('$HF_REPO', revision='$HF_REVISION', cache_dir='$MOUNT', allow_patterns=[$patterns], max_workers=$DOWNLOAD_WORKERS)
print('snapshot', path)
json.dump({'repo': '$HF_REPO', 'revision_requested': '$HF_REVISION', 'revision': path.rstrip('/').rsplit('/', 1)[-1],
           'allow_patterns': [$patterns], 'seconds': round(time.time() - started, 1)}, open('/out/weights.json', 'w'), indent=2)
" 2>&1 | tee "$LOGS/weights.log" || code=$?
  if [ "$code" != 0 ]; then die "downloading the H3 weights failed (exit $code; see logs/weights.log). Run again to resume"; fi
  state timing.weights_download_s "$(since "$started")"
  ok "weights ready: $(du -sh "$MODELS" | cut -f1) in $(since "$started")s"
}

fetch_weights() {
  say "weights: $HF_REPO@${HF_REVISION:0:12} into $MODELS"
  if [ "$MOCK" = 1 ]; then
    info "dry run: skipped (KUNO_BACKEND=$BACKEND never reads $MODELS)"
    state timing.weights_download_s skipped
    return
  fi
  chmod 0755 "$MODELS"
  local started code=0
  started="$(now)"
  # huggingface_hub from the worker image itself, so the host needs no Python. HF_TOKEN is passed by name only.
  if [ "$FAMILY" = h3 ]; then
    fetch_h3_weights
    return
  fi
  docker run --rm --label "$LABEL" --name "$PREFIX-weights" --user "$(id -u):$(id -g)" \
    -e HF_TOKEN -e HF_HUB_OFFLINE=0 -e TRANSFORMERS_OFFLINE=0 -e HF_HUB_DISABLE_TELEMETRY=1 \
    -e HF_HUB_DISABLE_PROGRESS_BARS=1 -e HF_XET_HIGH_PERFORMANCE=1 -e HOME=/tmp \
    -v "$MODELS:$MOUNT" -v "$HERE/smoke.py:/smoke/smoke.py:ro" -v "$RESULTS:/out" \
    --entrypoint python "$WORKER_IMAGE" -W ignore /smoke/smoke.py fetch-weights \
    --repo "$HF_REPO" --revision "$HF_REVISION" --profiles "$PROFILES" --dest "$MOUNT" \
    --summary /out/weights.json --workers "$DOWNLOAD_WORKERS" 2>&1 | tee "$LOGS/weights.log" || code=$?
  if [ "$code" != 0 ]; then
    case "$code" in
      20) die "the gated weights were refused (HTTP 401/403, above); nothing else was started" ;;
      *) die "downloading the weights failed (exit $code; see logs/weights.log). Run again to resume" ;;
    esac
  fi
  state timing.weights_download_s "$(since "$started")"
}

devkit_init() {
  say "kuno-devkit init"
  local started
  started="$(now)"
  # The data dir belongs to uid 10001, the user the gateway and both worker images run as.
  docker run --rm --label "$LABEL" --user 0:0 --entrypoint sh -v "$DATA:/data" "$DEVKIT_IMAGE" \
    -c 'chown 10001:10001 /data && chmod 0755 /data'
  if ! docker run --rm --label "$LABEL" --name "$PREFIX-devkit" -v "$DATA:/var/lib/kuno/data" \
    "$DEVKIT_IMAGE" kuno-devkit init --data /var/lib/kuno/data >"$LOGS/devkit.log" 2>&1; then
    die "kuno-devkit init failed (logs/devkit.log)"
  fi
  state timing.devkit_init_s "$(since "$started")"
  ok "dev keys, golden manifest and dev.env in $DATA ($(since "$started")s)"
}

start_gateway() {
  say "gateway on $GATEWAY_URL (SQLite and blobs in the data dir)"
  local started deadline
  started="$(now)"
  docker run -d --label "$LABEL" --name "$PREFIX-gateway" --network host \
    -e KUNO_DATA_DIR=/var/lib/kuno/data -e KUNO_PORT="$PORT" -e KUNO_ALLOW_COUNTRY_OVERRIDE=1 -v "$DATA:/var/lib/kuno/data" \
    "$GATEWAY_IMAGE" kuno-gateway --host 127.0.0.1 --port "$PORT" >/dev/null
  deadline=$(($(date +%s) + 180))
  until curl -fsS -o /dev/null "$GATEWAY_URL/healthz" 2>/dev/null; do
    if ! container_running "$PREFIX-gateway"; then
      docker logs --tail 20 "$PREFIX-gateway" 2>&1 | sed 's/^/        /'
      die "the gateway exited during start-up (logs/gateway.log)"
    fi
    if [ "$(date +%s)" -ge "$deadline" ]; then die "the gateway was not healthy after 180s (logs/gateway.log)"; fi
    sleep 1
  done
  state timing.gateway_start_s "$(since "$started")"
  ok "healthy after $(since "$started")s"
}

run_preflight() {
  say "kuno-preflight --no-tee (worker image)"
  local code=0
  # shellcheck disable=SC2046 # gpu_args prints either nothing or "--gpus all", one word per line
  docker run --rm --label "$LABEL" $(gpu_args) --network host --entrypoint kuno-preflight "$WORKER_IMAGE" \
    --no-tee --gateway "$GATEWAY_URL" >"$RESULTS/preflight.txt" 2>"$LOGS/preflight.stderr" || code=$?
  # shellcheck disable=SC2046
  docker run --rm --label "$LABEL" $(gpu_args) --network host --entrypoint kuno-preflight "$WORKER_IMAGE" \
    --no-tee --gateway "$GATEWAY_URL" --json >"$RESULTS/preflight.json" 2>>"$LOGS/preflight.stderr" || true
  state preflight_exit "$code"
  sed -i 's/\x1b\[[0-9;]*m//g' "$RESULTS/preflight.txt"
  sed 's/^/      /' "$RESULTS/preflight.txt"
  if [ "$code" = 0 ]; then
    ok "preflight: ready"
  elif [ "$MOCK" = 1 ]; then
    info "preflight exited $code, as expected on a machine without a GPU (recorded, not judged)"
  else
    warn "preflight exited $code: see preflight.txt (continuing; the job decides)"
  fi
}

run_profile() {
  local p="$1"
  local pre="profile.$p" name="$PREFIX-worker-$p" audio_flag=() code started registered gpus mode=text_to_video extra=()
  if [ "$p" = h3-reference ]; then mode=reference_to_video; fi
  say "$p"
  if [ "$AUDIO" != 1 ]; then audio_flag=(--no-audio); fi

  code=0
  docker run --rm --label "$LABEL" --entrypoint kuno-plan "$WORKER_IMAGE" "$p" "$mode" \
    --duration "$DURATION" --resolution "$RESOLUTION" --aspect "$ASPECT" --fps "$FPS" --models-dir "$MOUNT" \
    ${audio_flag[@]+"${audio_flag[@]}"} >"$RESULTS/plan-$p.txt" 2>"$LOGS/plan-$p.stderr" || code=$?
  state "$pre.plan_exit" "$code"
  if [ "$code" = 0 ]; then ok "kuno-plan: $(head -n 1 "$RESULTS/plan-$p.txt")"; else warn "kuno-plan exited $code (plan-$p.txt)"; fi

  code=0
  if [ "$FAMILY" = h3 ]; then
    info "resident-call check skipped: it inspects LTX2Pipeline, and H3 runs in SGLang"
  else
  helper "$WORKER_IMAGE" resident-call --profile "$p" --duration "$DURATION" --resolution "$RESOLUTION" \
    --aspect "$ASPECT" --fps "$FPS" --audio "$AUDIO" --out "/out/resident-call-$p.json" 2>"$LOGS/resident-call-$p.stderr" || code=$?
  case "$code" in
    0 | 10) ;;
    *) warn "the resident-call check itself failed (exit $code; logs/resident-call-$p.stderr)" ;;
  esac
  fi

  local worker=(
    -d --label "$LABEL" --name "$name" --network host
    -v "$DATA:/var/lib/kuno/data:ro" -v "$MODELS:$MOUNT:ro"
    -e KUNO_DATA_DIR=/var/lib/kuno/data -e KUNO_GATEWAY_URL="$GATEWAY_URL"
    -e KUNO_TEE=mock -e KUNO_BACKEND="$BACKEND" -e KUNO_PROFILES="$p"
    -e KUNO_WEIGHTS_ALLOW_UNPINNED=1 -e KUNO_WEIGHTS_VERIFY="$WEIGHTS_VERIFY"
    -e KUNO_MOCK_QUOTE_KEY_FILE=/var/lib/kuno/data/mock_quote.key -e KUNO_PROVENANCE=off
  )
  if [ "$FAMILY" = h3 ]; then
    # One worker on four GPUs (Ulysses 4); NCCL needs the host's shared memory. SGLang's log is kept on a dev box.
    # KUNO_MINER_COUNTRY: H3 is licensed by territory, so the gateway refuses to register it from an excluded
    # (or unknown) country. Here it is the country this test machine runs in.
    worker+=(--ipc host -e HF_HUB_CACHE="$MOUNT" -e HF_HUB_OFFLINE=1 -e KUNO_H3_NUM_GPUS="$MIN_GPUS" -e KUNO_SGLANG_LOG=inherit)
    if [ -n "$COUNTRY" ]; then worker+=(-e KUNO_MINER_COUNTRY="$COUNTRY"); fi
    gpus="$(seq -s, 0 $((MIN_GPUS - 1)))"
  else
    worker+=(-e KUNO_LTX_MODELS_DIR="$MOUNT" -e KUNO_LTX_OFFLOAD="$LTX_OFFLOAD")
    gpus=all
  fi
  if [ "$MOCK" != 1 ]; then
    if [ "$gpus" = all ]; then worker+=(--gpus all); else worker+=(--gpus "\"device=$gpus\""); fi
    worker+=(-e "NVIDIA_DRIVER_CAPABILITIES=compute,utility")
  fi
  if [ -n "${KUNO_MODEL_DIGEST:-}" ]; then worker+=(-e KUNO_MODEL_DIGEST); fi

  started="$(now)"
  state "$pre.worker_start_epoch" "$started"
  if ! docker run "${worker[@]}" "$WORKER_IMAGE" >/dev/null; then
    state "$pre.error" "docker run of the worker failed"
    bad "could not start the worker container"
    return 1
  fi
  info "worker started (KUNO_BACKEND=$BACKEND, KUNO_TEE=mock); waiting for it to register"

  local deadline last_note body status
  deadline=$(($(date +%s) + REGISTER_TIMEOUT))
  last_note=$(date +%s)
  registered=0
  while :; do
    body="$(curl -fsS ${COUNTRY_HEADER[@]+"${COUNTRY_HEADER[@]}"} "$GATEWAY_URL/v1/route?mode=$mode&profile_id=$p&privacy=$PRIVACY" 2>/dev/null || true)"
    case "$body" in *"\"profile_id\":\"$p\""*) case "$body" in *'"enclaves":[{'*) registered=1 ;; esac ;; esac
    if [ "$registered" = 1 ]; then break; fi
    if ! container_running "$name"; then
      status="$(docker inspect -f 'exit code {{.State.ExitCode}}, OOMKilled {{.State.OOMKilled}}' "$name" 2>/dev/null || true)"
      docker logs --tail 25 "$name" 2>&1 | sed 's/^/        /'
      state "$pre.error" "the worker exited before registering ($status); see logs/worker-$p.log"
      state "$pre.worker_exit" "$status"
      break
    fi
    if [ "$(date +%s)" -ge "$deadline" ]; then
      state "$pre.error" "the worker did not register within ${REGISTER_TIMEOUT}s; see logs/worker-$p.log"
      break
    fi
    if [ $(($(date +%s) - last_note)) -ge 60 ]; then
      info "still waiting after $(since "$started")s; worker: $(docker logs --tail 1 "$name" 2>&1 | cut -c1-150)"
      last_note=$(date +%s)
    fi
    sleep 3
  done

  local result=1
  if [ "$registered" = 1 ]; then
    state "$pre.registered_epoch" "$(now)"
    state "$pre.cold_start_to_registered_s" "$(since "$started")"
    ok "registered $(since "$started")s after docker run"

    if [ "$mode" = reference_to_video ]; then
      mkdir -p "$RESULTS/inputs" && cp "$REFERENCE_IMAGE" "$RESULTS/inputs/"
      extra+=(--reference-image "/out/inputs/$(basename "$REFERENCE_IMAGE")")
    fi
    if [ -n "$PROMPT_OVERRIDE" ]; then extra+=(--prompt "$PROMPT_OVERRIDE"); fi
    code=0
    helper "$GATEWAY_IMAGE" run-job --gateway "$GATEWAY_URL" --data /var/lib/kuno/data --profile "$p" \
      --duration "$DURATION" --resolution "$RESOLUTION" --aspect "$ASPECT" --fps "$FPS" --audio "$AUDIO" \
      --country "$COUNTRY" --privacy "$PRIVACY" --mode "$mode" ${extra[@]+"${extra[@]}"} --out /out/jobs --timeout "$JOB_TIMEOUT" 2>&1 | tee "$LOGS/job-$p.log" || code=$?
    if [ "$code" != 0 ]; then
      state "$pre.error" "the job did not produce a video (see logs/job-$p.log and logs/worker-$p.log)"
    elif ! ffprobe -v error -print_format json -show_format -show_streams "$JOBS/$p.mp4" >"$JOBS/$p.ffprobe.json" 2>"$LOGS/ffprobe-$p.log"; then
      state "$pre.error" "ffprobe could not read $p.mp4 ($(tail -n 1 "$LOGS/ffprobe-$p.log"))"
    else
      code=0
      helper "$GATEWAY_IMAGE" check-video --job "/out/jobs/$p.job.json" --ffprobe "/out/jobs/$p.ffprobe.json" \
        --out "/out/jobs/$p.check.json" || code=$?
      if [ "$code" = 0 ]; then result=0; else state "$pre.error" "ffprobe checks failed (jobs/$p.check.json)"; fi
    fi
  else
    bad "the worker never registered"
  fi

  docker stop -t 60 "$name" >/dev/null 2>&1 || true
  state "$pre.worker_stop_epoch" "$(now)"
  docker logs "$name" >"$LOGS/worker-$p.log" 2>&1 || true
  docker rm -f "$name" >/dev/null 2>&1 || true
  if [ "$result" = 0 ]; then ok "$p passed"; else bad "$p failed"; fi
  return "$result"
}

# ---------------------------------------------------------------- main

trap on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

check_prerequisites
begin_run
start_sampler
pull_images
fetch_weights
devkit_init
start_gateway
run_preflight
IFS=',' read -r -a PROFILE_LIST <<<"$PROFILES"
for profile in "${PROFILE_LIST[@]}"; do
  run_profile "$profile" || true
done
MAIN_DONE=1
