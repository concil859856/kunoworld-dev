#!/usr/bin/env bash
# SageAttention A/B for MiniMax H3 Turbo on single GPUs, straight against SGLang: no gateway, no worker.
# research/attention-bottleneck_nunchux_2026-09-17.md says why. Runs on the GPU host (after the H3 region check).
#
#   sage-ab.sh build    Time-boxed to SETUP_TIMEOUT_S (300). Installs SageAttention at the commit SGLang 0.5.19's log
#                       names (SAGE_REF, the one with the SM90 binding fix a Hopper GPU needs) into /opt/sglang of a
#                       container from IMAGE, compiling its CUDA kernels with the venv's pip CUDA 13 toolkit, and commits
#                       it as SAGE_IMAGE. Writes $OUT/build.json ({"ok", "seconds", "reason", "import_check"}) and build.log.
#   sage-ab.sh run      Server A: IMAGE as published, default attention, on GPU_A, started at once. Server B: SAGE_IMAGE
#                       with --attention-backend sage_attn on GPU_B, once build.json exists and says ok (it waits for it).
#                       Both load fl2va with the Turbo 8-step LoRA and render RUNS (default a warm-up and a measured 5 s
#                       lighthouse clip, seed 1234, 8 passes = STEPS 9) through h3_bench.py. Then `report`.
#   sage-ab.sh report   $OUT/sage-ab.json: each server's load time, renders and the attention backend its log says it
#                       used, B's speed-up over A, and PSNR/SSIM (ffmpeg) of B's clip against A's and of each measured
#                       clip against its own warm-up (the same request twice: should be identical).
#   sage-ab.sh all      build, then run.
#
# SGLang falls back to FlashAttention *silently* (an INFO/WARNING line) when sageattention is missing or lacks the SM90
# fix, so B counts as sage only if its log says so: "sage_in_use" and "backend_log" in sage-ab.json.
#
# Settings (environment): IMAGE, SAGE_IMAGE, H3_CACHE (host HF cache holding MiniMaxAI/MiniMax-H3 at refs/main), LORA
# (host path of minimax_h3_fl2v_turbo_8step_v1.0_768p_bf16.safetensors), OUT (~/sage-ab), VIDEOS (~/repro), GPU_A (4),
# GPU_B (5), PORT_A (30110), PORT_B (30120), BUILD_GPU (GPU_B; "none" compiles for SAGE_ARCH without a GPU),
# SAGE_ARCH (9.0, Hopper), SAGE_MAX_JOBS (32 parallel compiles), SETUP_TIMEOUT_S (300), LOAD_TIMEOUT_S (900),
# BUILD_WAIT_S (900: how long `run` waits for build.json), RUNS, STEPS (9), LABEL (sage-ab),
# DOCKER_LABEL (kuno-sage-ab=1: every container this starts carries it), NAME_PREFIX (kuno-sage-ab).
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${IMAGE:-ghcr.io/concil859856/kunoworld-worker:h3-0.1.0-69e34d62492b}"
SAGE_IMAGE="${SAGE_IMAGE:-kuno-h3-sage:local}"
SAGE_REF="${SAGE_REF:-d9704247a5139ab4c03bf7fc6b35cc0e2cbb5ea4}"
SAGE_ARCH="${SAGE_ARCH:-9.0}"
SAGE_MAX_JOBS="${SAGE_MAX_JOBS:-32}"
H3_CACHE="${H3_CACHE:-}"
LORA="${LORA:-}"
OUT="${OUT:-$HOME/sage-ab}"
VIDEOS="${VIDEOS:-$HOME/repro}"
GPU_A="${GPU_A:-4}"
GPU_B="${GPU_B:-5}"
PORT_A="${PORT_A:-30110}"
PORT_B="${PORT_B:-30120}"
BUILD_GPU="${BUILD_GPU:-$GPU_B}"
SETUP_TIMEOUT_S="${SETUP_TIMEOUT_S:-300}"
LOAD_TIMEOUT_S="${LOAD_TIMEOUT_S:-900}"
BUILD_WAIT_S="${BUILD_WAIT_S:-900}"
RUNS="${RUNS:-warmup:lighthouse:5 lighthouse:5}"
STEPS="${STEPS:-9}"
LABEL="${LABEL:-sage-ab}"
DOCKER_LABEL="${DOCKER_LABEL:-kuno-sage-ab=1}"
NAME_PREFIX="${NAME_PREFIX:-kuno-sage-ab}"
SITE=/opt/sglang/lib/python3.12/site-packages
mkdir -p "$OUT/logs" "$VIDEOS"
log() { echo "$(date -u +%T) sage-ab: $*"; }

build() {
  local started src="$OUT/src" name="$NAME_PREFIX-build" reason="" code="" remaining gpu=() import_check=""
  started=$(date +%s)
  rm -f "$OUT/build.json"
  docker rm -f "$name" >/dev/null 2>&1
  rm -rf "$src" && mkdir -p "$src"
  log "build: SageAttention@${SAGE_REF:0:12} into $SAGE_IMAGE (at most ${SETUP_TIMEOUT_S}s)"
  # GitHub's tarball of the commit: the image has no git.
  if ! curl -fsSL --max-time 90 "https://codeload.github.com/thu-ml/SageAttention/tar.gz/$SAGE_REF" | tar -xz -C "$src" --strip-components=1; then
    reason="downloading SageAttention@$SAGE_REF failed"
  fi
  if [ -z "$reason" ]; then
    if [ "$BUILD_GPU" != none ]; then gpu=(--gpus "\"device=$BUILD_GPU\"" -e NVIDIA_DRIVER_CAPABILITIES=compute,utility); fi
    # The build settings are exported inside, not passed with -e, so the committed image keeps the published environment.
    # The venv's nvcc is 13.4 but its CUDA runtime headers are 13.0, and CCCL (thrust/cub) refuses that pairing by default:
    # CCCL_DISABLE_CTK_COMPATIBILITY_CHECK lets the same major version through (found in a CPU dry run on 2026-09-17).
    # pip runs under /opt/sglang's interpreter (--python), so --no-build-isolation builds against that venv's torch.
    if ! docker run -d --name "$name" --label "$DOCKER_LABEL" --user 0:0 ${gpu[@]+"${gpu[@]}"} -v "$src:/src:ro" \
      --entrypoint bash "$IMAGE" -c "
        set -ex
        export CUDA_HOME=$SITE/nvidia/cu13 TORCH_CUDA_ARCH_LIST='$SAGE_ARCH' MAX_JOBS=$SAGE_MAX_JOBS EXT_PARALLEL=4 NVCC_APPEND_FLAGS='--threads 8 -DCCCL_DISABLE_CTK_COMPATIBILITY_CHECK'
        export PATH=/opt/sglang/bin:\$CUDA_HOME/bin:/usr/local/bin:/usr/bin:/bin HOME=/root
        nproc; nvidia-smi -L || true; nvcc --version | tail -n 2
        # setup.py links -lcuda, which the pip toolkit doesn't ship: the driver's (mounted with the GPU) or, with no GPU,
        # an empty stub whose soname is the driver's, so the extension still loads libcuda.so.1 at run time.
        mkdir -p /tmp/cudalib
        if [ -e /usr/lib/x86_64-linux-gnu/libcuda.so.1 ]; then ln -sf /usr/lib/x86_64-linux-gnu/libcuda.so.1 /tmp/cudalib/libcuda.so
        else echo | gcc -shared -x c - -Wl,-soname,libcuda.so.1 -o /tmp/cudalib/libcuda.so; fi
        export LIBRARY_PATH=/tmp/cudalib
        cp -r /src /tmp/sage && cd /tmp/sage
        /usr/local/bin/python3 -m pip --python /opt/sglang/bin/python install --no-deps --no-build-isolation --no-cache-dir .
        cd / && rm -rf /tmp/sage /tmp/cudalib
        if [ -e /usr/lib/x86_64-linux-gnu/libcuda.so.1 ]; then
          /opt/sglang/bin/python -c 'import sageattention; from sageattention import sageattn; from sageattention.sm90_compile import qk_int8_sv_f8_accum_f32_fuse_v_scale_attn_inst_buf_fake_impl; print(\"IMPORT_CHECK ok\", sageattention.__file__)'
        else  # no driver, so the kernels can't load: check the SM90 binding SGLang looks for was installed
          /usr/local/bin/python3 -m pip --python /opt/sglang/bin/python show -f sageattention | grep -q 'sm90_compile.py' && echo 'IMPORT_CHECK files only (no GPU driver in the build container)'
        fi
      " >/dev/null; then
      reason="docker run of the build container failed"
    fi
  fi
  if [ -z "$reason" ]; then
    remaining=$((SETUP_TIMEOUT_S - ($(date +%s) - started)))
    if [ "$remaining" -le 0 ] || ! code="$(timeout "$remaining" docker wait "$name")"; then
      reason="not finished within the ${SETUP_TIMEOUT_S}s time box"
      docker stop -t 2 "$name" >/dev/null 2>&1
    elif [ "$code" != 0 ]; then
      reason="the build exited $code (build.log)"
    fi
    docker logs "$name" >"$OUT/build.log" 2>&1
    import_check="$(grep -m1 '^IMPORT_CHECK' "$OUT/build.log" || true)"
    if [ -z "$reason" ]; then
      if ! docker commit --change 'USER kuno' --change 'ENTRYPOINT ["kuno-h3-worker"]' --change 'CMD []' "$name" "$SAGE_IMAGE" >/dev/null 2>>"$OUT/build.log"; then
        reason="docker commit failed"
      fi
    fi
    docker rm -f "$name" >/dev/null 2>&1
  fi
  local seconds=$(($(date +%s) - started))
  python3 - "$OUT/build.json" "$reason" "$seconds" "$SAGE_REF" "$SAGE_IMAGE" "$import_check" "$OUT/build.log" <<'PY'
import json, sys
path, reason, seconds, ref, image, check, log = sys.argv[1:]
try:
    tail = open(log, errors="replace").read().splitlines()[-40:]
except OSError:
    tail = []
json.dump({"ok": not reason, "reason": reason or None, "seconds": int(seconds), "sage_ref": ref, "image": image if not reason else None,
           "import_check": check or None, "log_tail": tail}, open(path, "w"), indent=2)
PY
  if [ -z "$reason" ]; then log "build ok in ${seconds}s"; else log "build FAILED after ${seconds}s: $reason"; fi
  [ -z "$reason" ]
}

serve() { # name image gpu port [extra sglang args...]
  local name=$1 image=$2 gpu=$3 port=$4
  shift 4
  docker rm -f "$name" >/dev/null 2>&1
  date +%s >"$OUT/logs/$name.started"
  docker run -d --name "$name" --label "$DOCKER_LABEL" --gpus "\"device=$gpu\"" --ipc host --network host \
    -e HF_HUB_CACHE=/models/h3 -e HF_HUB_OFFLINE=1 -e PATH="/opt/sglang/bin:/opt/kuno/bin:/usr/local/bin:/usr/bin:/bin" \
    -e CUDA_HOME="$SITE/nvidia/cu13" -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    -v "$H3_CACHE:/models/h3:ro" -v "$(dirname "$LORA"):/models/turbo:ro" \
    --entrypoint /opt/sglang/bin/sglang "$image" serve --model-path MiniMaxAI/MiniMax-H3 --model-variant fl2va \
    --num-gpus 1 --ulysses-degree 1 --performance-mode speed --host 127.0.0.1 --port "$port" \
    --master-port $((port + 1000)) --scheduler-port $((port + 2000)) \
    --lora-path "/models/turbo/$(basename "$LORA")" --lora-nickname turbo "$@" >/dev/null
}

ready() { # name port: waits for /health; records the load seconds
  local name=$1 port=$2 start
  start=$(cat "$OUT/logs/$name.started")
  while [ $(($(date +%s) - start)) -lt "$LOAD_TIMEOUT_S" ]; do
    if [ "$(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null)" != true ]; then
      log "$name exited while loading"
      return 1
    fi
    if curl -sf "http://127.0.0.1:$port/health" >/dev/null; then
      echo $(($(date +%s) - start)) >"$OUT/logs/$name.load_s"
      log "$name ready after $(cat "$OUT/logs/$name.load_s")s"
      return 0
    fi
    sleep 2
  done
  log "$name not ready after ${LOAD_TIMEOUT_S}s"
  return 1
}

finish_server() { docker logs "$1" >"$OUT/logs/$1.log" 2>&1; docker rm -f "$1" >/dev/null 2>&1; }

one_side() { # side image gpu port label [extra sglang args]
  local side=$1 image=$2 gpu=$3 port=$4 label=$5
  shift 5
  local name="$NAME_PREFIX-$side"
  serve "$name" "$image" "$gpu" "$port" "$@" || { log "$name: docker run failed"; echo "docker run failed" >"$OUT/logs/$name.error"; return 1; }
  if ready "$name" "$port"; then
    # shellcheck disable=SC2086 # RUNS is a list of run specs
    python3 "$HERE/h3_bench.py" --url "http://127.0.0.1:$port" --label "$label" --gpus 1 --steps "$STEPS" --flow-shift 6 \
      --lora-note "$(basename "$LORA")" --runs $RUNS --out "$OUT" --videos "$VIDEOS" 2>&1 | sed "s/^/$side: /"
  else
    echo "not ready (see logs/$name.log)" >"$OUT/logs/$name.error"
  fi
  finish_server "$name"
}

run() {
  if [ ! -d "$H3_CACHE/models--MiniMaxAI--MiniMax-H3" ] || [ ! -f "$LORA" ]; then
    log "run needs H3_CACHE (a HF cache with MiniMaxAI/MiniMax-H3) and LORA (the Turbo 8-step file)"
    return 2
  fi
  rm -f "$OUT/results.jsonl" "$OUT/sage-ab.json"
  log "A: default attention on GPU $GPU_A"
  one_side a "$IMAGE" "$GPU_A" "$PORT_A" "$LABEL-default" &
  local a=$!
  log "B: waiting for the build (build.json, at most ${BUILD_WAIT_S}s)"
  local waited=0
  while [ ! -f "$OUT/build.json" ] && [ "$waited" -lt "$BUILD_WAIT_S" ]; do sleep 5; waited=$((waited + 5)); done
  if [ -f "$OUT/build.json" ] && python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1]))["ok"] else 1)' "$OUT/build.json"; then
    log "B: --attention-backend sage_attn on GPU $GPU_B"
    one_side b "$SAGE_IMAGE" "$GPU_B" "$PORT_B" "$LABEL-sage" --attention-backend sage_attn
  else
    log "B: skipped, the build failed"
  fi
  wait "$a"
  report
}

report() {
  python3 - "$OUT" "$VIDEOS" "$LABEL" "$NAME_PREFIX" "$IMAGE" "$SAGE_IMAGE" "$GPU_A" "$GPU_B" <<'PY'
import json, re, subprocess, sys
from pathlib import Path

out, videos, label, prefix, image, sage_image, gpu_a, gpu_b = sys.argv[1:]
out, videos = Path(out), Path(videos)
rows = [json.loads(l) for l in (out / "results.jsonl").read_text().splitlines() if l.strip()] if (out / "results.jsonl").exists() else []


def read(path):
    try:
        return path.read_text()
    except OSError:
        return None


def compare(a, b):
    """ffmpeg's mean PSNR (dB, all planes) and SSIM (All) of clip b against clip a, frame by frame."""
    result = {"a": a.name, "b": b.name}
    if not (a.exists() and b.exists()):
        return result | {"error": "missing clip"}
    for name, pattern in (("psnr_db", r"average:(\S+)"), ("ssim", r"All:(\S+)")):
        flt = "psnr" if name == "psnr_db" else "ssim"
        proc = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(b), "-i", str(a), "-lavfi", f"[0:v][1:v]{flt}", "-f", "null", "-"],
                              capture_output=True, text=True)
        match = re.findall(pattern, proc.stderr)
        value = match[-1] if match else None
        result[name] = None if value is None else ("inf: identical" if value == "inf" else float(value))
        if value is None:
            result[f"{name}_error"] = proc.stderr[-400:]
    return result


def side(key, attention):
    name = f"{prefix}-{key}"
    lab = f"{label}-{attention}"
    log = read(out / "logs" / f"{name}.log") or ""
    renders = [r for r in rows if r.get("label") == lab]
    measured = next((r for r in renders if r.get("ok") and not r.get("warmup")), None)
    warm = next((r for r in renders if r.get("ok") and r.get("warmup")), None)
    load = read(out / "logs" / f"{name}.load_s")
    backend_lines = sorted({l.strip()[-200:] for l in log.splitlines() if re.search(r"attention backend|Sage Attention|sageattention|Falling back", l)})
    return {
        "attention_requested": attention,
        "load_s": int(load) if load else None,
        "error": (read(out / "logs" / f"{name}.error") or "").strip() or None,
        "backend_log": backend_lines,
        "sage_in_use": any("sage" in l.lower() and "using" in l.lower() for l in backend_lines) and not any("falling back" in l.lower() for l in backend_lines),
        "renders": [{k: r.get(k) for k in ("name", "ok", "warmup", "wall_s", "gpu_s_per_output_s", "steps", "seed", "error", "video")}
                    | {"inference_time_s": (r.get("server") or {}).get("inference_time_s"), "peak_memory_mb": (r.get("server") or {}).get("peak_memory_mb")}
                    for r in renders],
        "measured": measured,
        "warmup": warm,
    }


build = json.loads(read(out / "build.json") or "null")
a, b = side("a", "default"), side("b", "sage")
report = {"image": image, "sage_image": sage_image if build and build.get("ok") else None, "gpus": {"a": gpu_a, "b": gpu_b},
          "build": {k: v for k, v in (build or {}).items() if k != "log_tail"} if build else None,
          "a": {k: v for k, v in a.items() if k not in ("measured", "warmup")},
          "b": {k: v for k, v in b.items() if k not in ("measured", "warmup")},
          "note": "A and B render at the same time on different GPUs of the same host, alongside whatever else it runs"}
if a["measured"] and b["measured"]:
    report["speedup_wall"] = round(a["measured"]["wall_s"] / b["measured"]["wall_s"], 3)
    ia, ib = (a["measured"].get("server") or {}).get("inference_time_s"), (b["measured"].get("server") or {}).get("inference_time_s")
    report["speedup_inference"] = round(ia / ib, 3) if ia and ib else None
quality = {}
if a["measured"] and b["measured"]:
    quality["sage_vs_default"] = compare(Path(a["measured"]["video"]), Path(b["measured"]["video"]))
for key, s in (("default_repeat", a), ("sage_repeat", b)):
    if s["measured"] and s["warmup"]:
        quality[key] = compare(Path(s["warmup"]["video"]), Path(s["measured"]["video"]))
report["quality"] = quality
(out / "sage-ab.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
print(json.dumps({"build_ok": (build or {}).get("ok"), "sage_in_use": b["sage_in_use"], "speedup_wall": report.get("speedup_wall"),
                  "psnr_sage_vs_default": (quality.get("sage_vs_default") or {}).get("psnr_db")}, default=str))
PY
}

case "${1:-}" in
  build) build ;;
  run) run ;;
  report) report ;;
  all) build; run ;;
  *) echo "usage: sage-ab.sh build|run|report|all (settings in the header)" >&2; exit 2 ;;
esac
