#!/usr/bin/env bash
# The AV-extend long-video experiment on a rented GPU server: ltx_extend.py inside the LTX worker image, on the weights
# ltx-smoke.sh already downloaded. README.md in this directory says what it tests and what to look at.
#
#   ./run.sh storyboards/mixed-joins.json                                  ltx-2.5-fast, 720p, overlap 3, audio anchor first
#   ./run.sh storyboards/narrator.json --audio-anchor previous             any ltx_extend.py flag after the storyboard
#   KUNO_EXTEND_BACKEND=fake ./run.sh storyboards/mixed-joins.json --size 320x192    no GPU, no weights: the CPU stand-in
#
# Output: $KUNO_SMOKE_DIR/extend/<UTC stamp>-<storyboard>/ with stitched.mp4, shots/, seams.png, results.json, run.log,
# samples.csv (GPU memory and host RAM once a second) and a tarball of all of it beside the directory.
# KUNO_EXTEND_COPY_TO=~/repro also copies the stitched and per-shot MP4s there, where data/gpu-tests/tools/sync.sh looks.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ $# -lt 1 ] || [ ! -f "$1" ]; then
  echo "usage: run.sh STORYBOARD.json [ltx_extend.py flags]  (storyboards/ has three)" >&2
  exit 2
fi
BOARD="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
shift
BACKEND="${KUNO_EXTEND_BACKEND:-real}"
case "$BACKEND" in real | tiny | fake) ;; *) echo "run.sh: KUNO_EXTEND_BACKEND must be real, tiny or fake" >&2 && exit 2 ;; esac
BASE="${KUNO_SMOKE_DIR:-$PWD/kuno-smoke}"
MODELS="${KUNO_SMOKE_MODELS_DIR:-$BASE/models/ltx-2.5}"
# The smoke test's default worker image; any image with kuno_worker and diffusers 0.40 works (KUNO_EXTEND_IMAGE).
IMAGE="${KUNO_EXTEND_IMAGE:-${KUNO_SMOKE_WORKER_IMAGE:-ghcr.io/concil859856/kunoworld-worker:ltx-0.1.0-0ad70874cd6b}}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
NAME="$(basename "$BOARD" .json)"
RUN_DIR="${KUNO_EXTEND_OUT:-$BASE/extend/$STAMP-$NAME}"
CONTAINER="kuno-extend-$STAMP"
SAMPLER_PID=""

ok() { printf '  ok    %s\n' "$*"; }
bad() { printf '  FAIL  %s\n' "$*" >&2; }

on_exit() {
  local code=$?
  trap - EXIT INT TERM
  set +e
  if [ -n "$SAMPLER_PID" ]; then kill "$SAMPLER_PID" 2>/dev/null; wait "$SAMPLER_PID" 2>/dev/null; fi
  docker rm -f "$CONTAINER" >/dev/null 2>&1
  if [ -n "${KUNO_EXTEND_COPY_TO:-}" ] && [ -d "$RUN_DIR" ]; then
    mkdir -p "$KUNO_EXTEND_COPY_TO"
    for video in "$RUN_DIR/stitched.mp4" "$RUN_DIR"/shots/*.mp4; do
      if [ -f "$video" ]; then cp "$video" "$KUNO_EXTEND_COPY_TO/extend-$STAMP-${NAME}_$(basename "$video")"; fi
    done
  fi
  if [ -d "$RUN_DIR" ] && [ -n "$(ls -A "$RUN_DIR" 2>/dev/null)" ]; then
    tar -C "$(dirname "$RUN_DIR")" -czf "$RUN_DIR.tar.gz" "$(basename "$RUN_DIR")"
    printf '\nresults  %s\ntarball  %s (%s)\n' "$RUN_DIR" "$RUN_DIR.tar.gz" "$(du -h "$RUN_DIR.tar.gz" | cut -f1)"
  fi
  exit "$code"
}
trap on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf '== prerequisites\n'
failed=0
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  bad "image $IMAGE is not on this machine: run ltx-smoke.sh once (it pulls it), or docker pull it, or set KUNO_EXTEND_IMAGE"
  failed=1
else
  ok "image $IMAGE"
fi
if [ "$BACKEND" = real ]; then
  if [ -f "$MODELS/model_index.json" ] && [ -d "$MODELS/transformer" ] && [ -d "$MODELS/latent_upsampler" ]; then
    ok "weights $MODELS ($(du -sh "$MODELS" 2>/dev/null | cut -f1))"
  else
    bad "no LTX-2.5-Diffusers weights at $MODELS (model_index.json, transformer/, latent_upsampler/): run ltx-smoke.sh first or set KUNO_SMOKE_MODELS_DIR"
    failed=1
  fi
  if gpu="$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1)" && [ -n "$gpu" ]; then
    ok "GPU $gpu"
  else
    bad "nvidia-smi sees no GPU"
    failed=1
  fi
fi
if [ "$failed" = 1 ]; then exit 2; fi
mkdir -p "$RUN_DIR"
cp "$BOARD" "$RUN_DIR/storyboard.json"

# Host RAM and the busiest GPU's memory once a second, as ltx-smoke.sh records them.
{
  printf 'epoch_s,mem_used_kib,gpu_mem_used_mib,gpu_mem_total_mib,gpu_util_pct\n'
  while :; do
    mem="$(awk '/^MemTotal:/ { t = $2 } /^MemAvailable:/ { a = $2 } END { printf "%d", t - a }' /proc/meminfo)"
    gpu="$(nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits 2>/dev/null |
      awk -F', *' 'BEGIN { u = -1 } $1 + 0 > u { u = $1 + 0; t = $2; g = $3 } END { if (u >= 0) printf "%s,%s,%s", u, t, g; else printf ",," }')"
    printf '%s,%s,%s\n' "$(date +%s)" "$mem" "${gpu:-,,}"
    sleep 1
  done
} >"$RUN_DIR/samples.csv" 2>/dev/null &
SAMPLER_PID=$!

printf '\n== %s: %s backend, output in %s\n' "$NAME" "$BACKEND" "$RUN_DIR"
# As the invoking user, so the results are the host's: the image runs as kuno otherwise. USER is set because torch calls
# getpass.getuser(), which crashes for a uid the image's /etc/passwd does not know.
args=(
  --rm --name "$CONTAINER" --user "$(id -u):$(id -g)" -e HOME=/tmp -e USER=kuno-extend -e HF_HUB_OFFLINE=1
  -e KUNO_EXTEND_IMAGE="$IMAGE" -v "$HERE:/extend:ro" -v "$(dirname "$BOARD"):/storyboard:ro" -v "$RUN_DIR:/out"
)
if [ "$BACKEND" = real ]; then
  args+=(--gpus all -e NVIDIA_DRIVER_CAPABILITIES=compute,utility -v "$MODELS:/models/ltx-2.5:ro")
fi
code=0
docker run "${args[@]}" --entrypoint python "$IMAGE" -u -W ignore /extend/ltx_extend.py "/storyboard/$(basename "$BOARD")" \
  --backend "$BACKEND" --models-dir /models/ltx-2.5 --out /out "$@" 2>&1 | tee "$RUN_DIR/run.log" || code=$?
peak="$(awk -F, 'NR > 1 && $3 != "" && $3 + 0 > p { p = $3 + 0 } END { print p + 0 }' "$RUN_DIR/samples.csv")"
printf '\npeak GPU memory (nvidia-smi): %s MiB\n' "$peak"
exit "$code"
