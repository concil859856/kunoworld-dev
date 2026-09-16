"""Times MiniMax H3 renders straight against an SGLang server (POST /v1/videos, poll, fetch), one JSON line per
render. Stdlib only, so it runs with the host's python3.

  h3_bench.py --url http://127.0.0.1:30010 --label turbo8-x4 --gpus 4 --steps 8 --flow-shift 6 \
      --runs warmup:lighthouse:5 lighthouse:5 chef:14 --out ~/turbo --videos ~/repro
  h3_bench.py --url ... --set-lora t4=/models/turbo/<file>     # switch the server's LoRA first
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROMPTS = {
    # The prompt and seed of the full-H3 smoke job on 2026-09-15, for a side-by-side with Turbo.
    "lighthouse": "A lighthouse on a cliff at dawn, waves rolling in",
    "forest": "A slow aerial shot over a misty pine forest at sunrise, birds calling, a river glinting between the trees",
    "chef": (
        "A friendly chef in a bright kitchen looks at the camera and says: \"Today we are making a simple tomato soup, "
        "and it only takes twenty minutes.\" Onions sizzle in a pan beside her."
    ),
}
FPS = 24


def h3_frames(duration_s: float) -> int:
    """H3 snaps to 17n + 5 frames (research/research_model_capabilities.md)."""
    frames = max(5, round(duration_s * FPS))
    return 17 * math.ceil((frames - 5) / 17) + 5


def call(method: str, url: str, body: dict | None = None, timeout: float = 60.0) -> tuple[int, bytes]:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, method=method, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def probe(path: Path) -> dict:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,nb_frames,sample_rate:format=duration",
             "-of", "json", str(path)], capture_output=True, text=True, timeout=60, check=True).stdout
        return json.loads(out)
    except Exception as exc:  # noqa: BLE001 - a probe failure is recorded, not fatal
        return {"error": repr(exc)}


def render(args, label: str, prompt_key: str, duration_s: float, warmup: bool) -> dict:
    body = {
        "prompt": PROMPTS[prompt_key],
        "task": "t2va",
        "conditions": [],
        "target": {"short_edge": 768, "aspect_ratio": "16:9", "duration_seconds": duration_s},
        "seed": args.seed,
        "num_inference_steps": args.steps,
    }
    if args.flow_shift is not None:
        body["flow_shift"] = args.flow_shift
    if args.audio_flow_shift is not None:
        body["audio_flow_shift"] = args.audio_flow_shift
    name = f"{label}_{prompt_key}_{duration_s:g}s{'_warmup' if warmup else ''}"
    record = {"label": label, "name": name, "prompt": prompt_key, "duration_s": duration_s, "frames": h3_frames(duration_s),
              "gpus": args.gpus, "steps": args.steps, "flow_shift": args.flow_shift, "audio_flow_shift": args.audio_flow_shift,
              "seed": args.seed, "warmup": warmup, "lora": args.lora_note}
    started = time.time()
    status, raw = call("POST", f"{args.url}/v1/videos", body)
    if status >= 400:
        record.update(ok=False, error=f"submit HTTP {status}: {raw[:500].decode(errors='replace')}", wall_s=round(time.time() - started, 2))
        return record
    video_id = json.loads(raw)["id"]
    final: dict = {}
    while True:
        status, raw = call("GET", f"{args.url}/v1/videos/{video_id}")
        final = json.loads(raw) if status < 400 else {"status": "http", "code": status}
        state = str(final.get("status", "")).lower()
        if state in ("completed", "succeeded"):
            break
        if state in ("failed", "error", "cancelled", "canceled", "http") or time.time() - started > args.timeout:
            record.update(ok=False, error=f"state {state}: {json.dumps(final)[:800]}", wall_s=round(time.time() - started, 2))
            return record
        time.sleep(0.25)
    generated = time.time()
    status, data = call("GET", f"{args.url}/v1/videos/{video_id}/content", timeout=300)
    fetched = time.time()
    if status >= 400:
        record.update(ok=False, error=f"content HTTP {status}", wall_s=round(fetched - started, 2))
        return record
    path = Path(args.videos) / f"{name}.mp4"
    path.write_bytes(data)
    output_s = record["frames"] / FPS
    wall = generated - started
    record.update(
        ok=True, wall_s=round(wall, 2), fetch_s=round(fetched - generated, 2), bytes=len(data), video=str(path),
        output_s=round(output_s, 3), gpu_s=round(wall * args.gpus, 1), gpu_s_per_output_s=round(wall * args.gpus / output_s, 2),
        server=final, probe=probe(path),
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--gpus", type=int, required=True)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--flow-shift", type=float)
    parser.add_argument("--audio-flow-shift", type=float, default=3.0)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--set-lora", help="nickname=path: POST /v1/set_lora before rendering")
    parser.add_argument("--lora-note", default=None)
    parser.add_argument("--runs", nargs="+", required=True, help="[warmup:]prompt:duration_s ...")
    parser.add_argument("--out", required=True)
    parser.add_argument("--videos", required=True)
    args = parser.parse_args()
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    Path(args.videos).expanduser().mkdir(parents=True, exist_ok=True)
    args.videos = str(Path(args.videos).expanduser())
    results = out / "results.jsonl"

    def emit(record: dict) -> None:
        with results.open("a") as handle:
            handle.write(json.dumps(record) + "\n")
        brief = {k: record.get(k) for k in ("name", "ok", "wall_s", "gpu_s_per_output_s", "error")}
        print(json.dumps(brief), flush=True)

    if args.set_lora:
        nickname, path = args.set_lora.split("=", 1)
        started = time.time()
        status, raw = call("POST", f"{args.url}/v1/set_lora", {"lora_nickname": nickname, "lora_path": path}, timeout=900)
        emit({"label": args.label, "name": f"{args.label}_set_lora", "ok": status < 400, "wall_s": round(time.time() - started, 2),
              "error": None if status < 400 else raw[:800].decode(errors="replace")})
        if status >= 400:
            return 1
    failures = 0
    for spec in args.runs:
        parts = spec.split(":")
        warmup = parts[0] == "warmup"
        prompt_key, duration = parts[-2], float(parts[-1])
        record = render(args, args.label, prompt_key, duration, warmup)
        emit(record)
        failures += 0 if record.get("ok") else 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
