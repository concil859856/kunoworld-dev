"""One storyboard through the worker's own LtxResidentBackend on a GPU: task -> admission -> shots -> stitched MP4.

    python run_storyboard.py /boards/mixed-joins.json [--resolution 720p] [--fps 24] [--seed 1234] [--hardware-class C1...]
"""

import argparse
import json
import logging
import time
import uuid
from pathlib import Path

from kuno_protocol.mp4 import probe
from kuno_protocol.profiles import Mode, load_profiles, shot_prompt, storyboard_duration_s, storyboard_frames, validate_params
from kuno_protocol.schemas import GenerationParams, ShotSpec
from kuno_worker.backends.base import GenerationTask
from kuno_worker.backends.ltx_resident import LtxResidentBackend

parser = argparse.ArgumentParser()
parser.add_argument("board")
parser.add_argument("--out", default="/out")
parser.add_argument("--models-dir", default="/models/ltx-2.5")
parser.add_argument("--resolution", default="720p")
parser.add_argument("--fps", type=int, default=24)
parser.add_argument("--seed", type=int, default=1234)
parser.add_argument("--hardware-class", default=None, help="e.g. C1.rtx-pro-6000-bw-se.x1: verified-mode determinism on")
parser.add_argument("--offload", default="auto")
parser.add_argument("--size", default=None, help="WIDTHxHEIGHT override (CPU dry runs only)")
args = parser.parse_args()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

profile = load_profiles()["ltx-2.5-fast"]
board = json.loads(Path(args.board).read_text())
items = board["shots"] if isinstance(board, dict) else board
shots = [ShotSpec(duration_s=float(s["duration_s"]), join=s.get("join", "fresh" if i == 0 else "continue")) for i, s in enumerate(items)]
params = GenerationParams(
    profile_id=profile.id, mode=Mode.STORYBOARD, duration_s=storyboard_duration_s(profile, shots, args.fps), resolution=args.resolution,
    aspect_ratio="16:9", fps=args.fps, shots=shots,
)
validate_params(profile, params)
width, height = (int(v) for v in args.size.split("x")) if args.size else profile.size_for(args.resolution, "16:9")
task = GenerationTask(
    job_id=str(uuid.uuid4()), profile=profile, params=params, prompt="", negative_prompt=None, seed=args.seed, width=width, height=height,
    shot_prompts=[shot_prompt("", s["prompt"]) for s in items],
)
backend = LtxResidentBackend(
    Path(args.models_dir), Path("/tmp/kuno-work"), hardware_class=args.hardware_class, offload=args.offload, weights_verify="size",
    allow_unpinned_weights=args.hardware_class is not None,
)
started = time.perf_counter()
backend.warm(profile)
load_s = time.perf_counter() - started

try:
    import torch

    cuda = torch.cuda.is_available()
    if cuda:
        torch.cuda.reset_peak_memory_stats()
except ImportError:
    cuda = False
reports = []
started = time.perf_counter()
result = backend.generate(task, lambda value, stage: reports.append((round(time.perf_counter() - started, 1), round(value, 3), stage)))
wall_s = time.perf_counter() - started

out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
(out / "stitched.mp4").write_bytes(result.data)
info = probe(result.data)
expected = storyboard_frames(profile, shots, args.fps)
checks = {
    "frames == storyboard_frames": result.info.frames == info.frames == expected,
    "container duration ~ frames/fps": abs(info.duration_s - expected / args.fps) < 0.1,
    "audio track": bool(info.audio),
    "no step commitment": result.step_commitment is None,
    "shot i/N stages": [s for _, _, s in reports][: len(shots)] == [f"shot {i + 1}/{len(shots)}" for i in range(len(shots))],
}
summary = {
    "board": args.board, "shots": len(shots), "size": f"{width}x{height}", "fps": args.fps, "seed": args.seed, "hardware_class": args.hardware_class,
    "expected_frames": expected, "info": result.info.model_dump(), "container": {"frames": info.frames, "duration_s": info.duration_s},
    "load_s": round(load_s, 1), "wall_s": round(wall_s, 1), "progress": reports, "checks": checks,
    "peak_gpu_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2) if cuda else None,
    "peak_gpu_reserved_gib": round(torch.cuda.max_memory_reserved() / 2**30, 2) if cuda else None,
}
(out / "storyboard.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
print("RESULT:", "PASS" if all(checks.values()) else "FAIL")
