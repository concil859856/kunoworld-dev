#!/usr/bin/env bash
# Runs on the rented 8x H200 host (after region-check.sh passed): downloads H3 FL2VA + two Turbo LoRAs, then measures
#   A. Turbo 8-step 768p LoRA, SGLang Ulysses x4 on GPUs 0-3 (5/10/14 s), then the 4-step 768p LoRA via /v1/set_lora
#   B. Turbo 8-step, SGLang on GPU 4 alone (5/14 s) -- is Turbo cheaper per GPU-second on one GPU?
#   C. full 50-step H3 on GPUs 4-7 (10/14 s, plus the 5 s smoke prompt again) -- the duration factor PRICING.md lacks
# Videos land in ~/repro (the local sync copies them); results in ~/turbo/results.jsonl; ~/turbo/DONE when finished.
set -uo pipefail
IMAGE="${IMAGE:-vocence/kunoworld-worker:h3-0.1.0-0ad70874cd6b}"
W="$HOME/kuno-turbo"; OUT="$HOME/turbo"; VID="$HOME/repro"
H3_REV="${H3_REV:-main}"
LORA_REV=3ec17a324ced54151364f24f8b5fb6bf7e26414f
LORA8=minimax_h3_fl2v_turbo_8step_v1.0_768p_bf16.safetensors
LORA4=minimax_h3_fl2v_turbo_4step_v1.0_768p_bf16.safetensors
SITE=/opt/sglang/lib/python3.12/site-packages
mkdir -p "$W/h3" "$W/turbo" "$OUT/logs" "$VID"
log() { echo "$(date -u +%T) $*"; }

log "pull $IMAGE"
docker pull -q "$IMAGE" || { log "pull failed"; exit 2; }

log "weights"
t0=$(date +%s)
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e HF_HUB_OFFLINE=0 -e HF_HUB_DISABLE_TELEMETRY=1 \
  -e HF_HUB_DISABLE_PROGRESS_BARS=1 -e HF_XET_HIGH_PERFORMANCE=1 -v "$W/h3:/models/h3" -v "$W/turbo:/models/turbo" \
  --entrypoint /opt/kuno/bin/python "$IMAGE" -c "
import json, time
from huggingface_hub import HfApi, hf_hub_download, snapshot_download
t = time.time()
p = snapshot_download('MiniMaxAI/MiniMax-H3', revision='$H3_REV', cache_dir='/models/h3',
                      allow_patterns=['*.json', 'LICENSE', 'README.md', 'FL2VA/*'], max_workers=16)
sha = HfApi().model_info('MiniMaxAI/MiniMax-H3', revision='$H3_REV').sha
for name in ('$LORA8', '$LORA4'):
    hf_hub_download('lightx2v/Minimax-h3-Turbo', name, revision='$LORA_REV', local_dir='/models/turbo')
print(json.dumps({'h3_snapshot': p, 'h3_sha': sha, 'lora_rev': '$LORA_REV', 'seconds': round(time.time() - t)}))
" > "$OUT/weights.json" 2> "$OUT/logs/weights.err" || { log "weights failed"; tail -5 "$OUT/logs/weights.err"; exit 2; }
log "weights done in $(( $(date +%s) - t0 )) s: $(cat "$OUT/weights.json")"

nvidia-smi --query-gpu=timestamp,index,memory.used,utilization.gpu --format=csv,noheader -l 2 > "$OUT/gpu-mem.csv" &
SMI=$!

serve() { # name devices ngpus port [extra sglang args...]
  local name=$1 dev=$2 n=$3 port=$4; shift 4
  docker rm -f "$name" >/dev/null 2>&1
  docker run -d --name "$name" --gpus "\"device=$dev\"" --ipc host --network host \
    -e HF_HUB_CACHE=/models/h3 -e HF_HUB_OFFLINE=1 -e PATH="/opt/sglang/bin:/opt/kuno/bin:/usr/local/bin:/usr/bin:/bin" \
    -e CUDA_HOME="$SITE/nvidia/cu13" -v "$W/h3:/models/h3:ro" -v "$W/turbo:/models/turbo:ro" -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    --entrypoint /opt/sglang/bin/sglang "$IMAGE" serve --model-path MiniMaxAI/MiniMax-H3 --model-variant fl2va \
    --num-gpus "$n" --ulysses-degree "$n" --performance-mode speed --host 127.0.0.1 --port "$port" \
    --master-port $((port + 1000)) --scheduler-port $((port + 2000)) "$@" >/dev/null
  echo "$(date +%s)" > "$OUT/logs/$name.started"
}
ready() { # name port -> waits for /health, records load seconds
  local name=$1 port=$2 start; start=$(cat "$OUT/logs/$name.started")
  for _ in $(seq 1 900); do
    if ! docker ps --format '{{.Names}}' | grep -qx "$name"; then log "$name exited"; docker logs "$name" > "$OUT/logs/$name.log" 2>&1; return 1; fi
    if curl -sf "http://127.0.0.1:$port/health" >/dev/null; then
      log "$name ready after $(( $(date +%s) - start )) s"
      echo "{\"label\": \"$name\", \"name\": \"${name}_load\", \"ok\": true, \"wall_s\": $(( $(date +%s) - start ))}" >> "$OUT/results.jsonl"
      return 0
    fi
    sleep 2
  done
  log "$name not ready"; return 1
}
bench() { python3 "$HOME/h3_bench.py" --out "$OUT" --videos "$VID" "$@"; }
stop() { docker logs "$1" > "$OUT/logs/$1.log" 2>&1; docker rm -f "$1" >/dev/null 2>&1; }

log "start A (turbo x4, GPUs 0-3) and B (turbo x1, GPU 4)"
serve turbo-x4 0,1,2,3 4 30010 --lora-path "/models/turbo/$LORA8" --lora-nickname t8
serve turbo-x1 4 1 30020 --lora-path "/models/turbo/$LORA8" --lora-nickname t8

(
  if ready turbo-x4 30010; then
    bench --url http://127.0.0.1:30010 --label turbo8-x4 --gpus 4 --steps 9 --flow-shift 6 --lora-note "$LORA8" \
      --runs warmup:lighthouse:5 lighthouse:5 forest:5 chef:10 lighthouse:14 chef:14
    bench --url http://127.0.0.1:30010 --label turbo4-x4 --gpus 4 --steps 5 --flow-shift 6 --lora-note "$LORA4" \
      --set-lora "t4=/models/turbo/$LORA4" --runs warmup:forest:5 lighthouse:5 chef:14
  fi
  stop turbo-x4
  log "A done"
) > "$OUT/logs/A.out" 2>&1 &
A=$!

(
  if ready turbo-x1 30020; then
    bench --url http://127.0.0.1:30020 --label turbo8-x1 --gpus 1 --steps 9 --flow-shift 6 --lora-note "$LORA8" \
      --runs warmup:lighthouse:5 lighthouse:5 chef:14
  fi
  stop turbo-x1
  log "B done; start C (full H3 x4, GPUs 4-7)"
  serve full-x4 4,5,6,7 4 30030
  if ready full-x4 30030; then
    bench --url http://127.0.0.1:30030 --label full50-x4 --gpus 4 --steps 51 --runs lighthouse:5 forest:10 chef:14
  fi
  stop full-x4
  log "C done"
) > "$OUT/logs/BC.out" 2>&1 &
BC=$!

wait "$A" "$BC"
kill "$SMI" 2>/dev/null
log "all done"
date -u +%FT%TZ > "$OUT/DONE"
