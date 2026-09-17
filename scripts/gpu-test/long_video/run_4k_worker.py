"""ltx-2.5-4k through the worker's own LtxResidentBackend on a GPU: a 1440p and a 2160p clip, each checked for its frames, size
and sound, with its latent render and its diffusion decode timed apart and their peak memory set against admission's
estimates. Nothing is downloaded but the weights ltx-smoke.sh already fetched.

    python run_4k_worker.py --out /out [--models-dir /models/ltx-2.5] [--clips 1440p:4,2160p:3] [--fps 24] [--repeat]
    python run_4k_worker.py --out /out --tiny   # a CPU dry run on tiny random weights: the flow (needs subnet/worker/tests on PYTHONPATH)

Jobs, text-to-video with sound, 16:9, one per `--clips` entry (<resolution>:<seconds>), in order, on one loaded ltx-2.5-4k:
  4k-1440p     2560x1408
  4k-2160p     3840x2176
  4k-repeat    with --repeat: the first clip again from the same seed
A clip the card's memory plan refuses (quantized.admit) is recorded as refused with admission's reason and not rendered.

How a clip renders (backends/ltx_resident.build_call, runtimes.LtxAdapter): ltx-2.5-fast's distilled passes at the clip's
own frame rate (8 sigmas at half size, the latents upsampled x2, 3 sigmas at full size) return latents; diffusers'
LTX2VideoDiffusionDecodePipeline decodes them with the chunked neighborhood attention and its default tiling
(backends/ltx_diffusion_decode.py); the audio VAE and vocoder decode the sound.

Checks (`4k.json`; RESULT: PASS when every rendered clip passes all of them and at least one clip rendered; --tiny skips the
memory checks, which a CPU can't make):
  frames        the render's frame count, the MP4's and ltx_num_frames(seconds, fps) agree
  size          the MP4 is the profile's width x height (--tiny: 320x192)
  sound         the MP4 has a sound track, as long as its picture within a frame
  render peak   on a GPU: the latent render's peak allocated memory (the text encoder, both passes, the upsampler) within
                admission's render estimate (quantized.MemoryPlan.estimate_gib: the distilled recipe's measured line,
                extrapolated from 51,000 to these tokens)
  decode peak   on a GPU: the diffusion decode's peak allocated memory within admission's decode estimate
                (MemoryPlan.decode_gib: the decoder's shapes and a count of its live tensors, never measured on a GPU)
  repeat        with --repeat: the repeated clip's frames are the first clip's, byte for byte
Recorded as well: seconds per phase (latent_render, video_decode, audio_decode) and for the whole job (which adds the MP4
encode), each phase's peak allocated and reserved GiB, the load, the card's envelope for ltx-2.5-4k as its plan computes it,
and the decoder's attention processor, budget and tiling.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
import uuid
from pathlib import Path

from kuno_protocol.mp4 import probe
from kuno_protocol.profiles import Mode, load_profiles, ltx_num_frames, validate_params
from kuno_protocol.schemas import GenerationParams
from kuno_worker.backends.base import GenerationTask
from kuno_worker.backends.ltx_edit import decode_audio
from kuno_worker.backends.ltx_resident import LtxResidentBackend, build_call
from kuno_worker.backends.media_tools import CapacityRefused
from kuno_worker.backends.quantized import call_frames, call_tokens, envelope_for_plan
from kuno_worker.backends.resident import PipelineResult

parser = argparse.ArgumentParser()
parser.add_argument("--out", default="/out")
parser.add_argument("--models-dir", default="/models/ltx-2.5")
parser.add_argument("--clips", default="1440p:4,2160p:3", help="comma-separated <resolution>:<seconds>, rendered in order")
parser.add_argument("--fps", type=int, default=24)
parser.add_argument("--seed", type=int, default=1234)
parser.add_argument("--offload", default="auto")
parser.add_argument("--repeat", action="store_true", help="render the first clip again and check its frames repeat")
parser.add_argument("--prompt", default="A lighthouse on a rocky coast at dusk, waves breaking below, its beam sweeping through sea spray. "
                                        "Gulls cry over the wind and the surf.")
parser.add_argument("--tiny", action="store_true", help="CPU dry run on tiny random weights (needs subnet/worker/tests on PYTHONPATH)")
args = parser.parse_args()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

import torch  # noqa: E402

FOUR_K = load_profiles()["ltx-2.5-4k"]
cuda = torch.cuda.is_available() and not args.tiny
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
summary: dict = {"args": vars(args), "clips": {}}


def save() -> None:
    (out / "4k.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")


class Recording:
    """The loaded adapter, keeping what each render reported (timings, per-phase memory, a digest of its frames) and never its
    frames: a 2160p clip is 25 MiB a frame on the host."""

    def __init__(self, adapter):
        self.adapter, self.last = adapter, None

    def __call__(self, **call):
        result = self.adapter(**call)
        frames = PipelineResult.from_pipeline(result).frames
        digest = hashlib.sha256()
        for frame in frames:
            digest.update(frame.tobytes() if hasattr(frame, "tobytes") else bytes(frame))
        self.last = {"timings": result.get("timings"), "memory_gib": result.get("memory_gib"), "frames": len(frames), "frames_sha256": digest.hexdigest()}
        return result

    def unload(self) -> None:
        adapter, self.adapter = self.adapter, None
        adapter.unload()

    def __getattr__(self, name):
        adapter = self.__dict__.get("adapter")
        if adapter is None:
            raise AttributeError(f"{name}: this pipeline was unloaded")
        return getattr(adapter, name)


recording: Recording | None = None


def load(profile):
    global recording
    started = time.perf_counter()
    if args.tiny:
        from kuno_worker.backends.runtimes import LtxAdapter
        from ltx_4k_doubles import tiny_4k_pipelines

        adapter = LtxAdapter(tiny_4k_pipelines(), device="cpu")
    else:
        from kuno_worker.backends.runtimes import ltx_loader

        adapter = ltx_loader(Path(args.models_dir), offload=args.offload, weights_verify="size")(profile)
        adapter.measure_memory = True
    summary["load"] = {"seconds": round(time.perf_counter() - started, 1), "allocated_gib": round(torch.cuda.memory_allocated() / 2**30, 2) if cuda else None}
    decoder = adapter.pipelines["decode"].diffusion_decoder
    processors = {type(m.processor).__name__ for m in decoder.modules() if hasattr(m, "kernel_size") and hasattr(m, "processor")}
    budgets = {getattr(m.processor, "budget_bytes", None) for m in decoder.modules() if hasattr(m, "kernel_size") and hasattr(m, "processor")}
    summary["decoder"] = {
        "attention_processors": sorted(processors), "budget_bytes": sorted(b for b in budgets if b is not None), "dtype": str(decoder.dtype),
        "tiling": {key: getattr(decoder, key) for key in ("use_tiling", "tile_sample_min_height", "tile_sample_min_width", "tile_sample_min_num_frames",
                                                         "tile_sample_stride_height", "tile_sample_stride_width", "tile_sample_stride_num_frames")},
    }
    recording = Recording(adapter)
    save()
    return recording


backend = LtxResidentBackend(None, Path("/tmp/kuno-work"), loader=load, offload=args.offload)


def task_for(resolution: str, seconds: float, seed: int) -> GenerationTask:
    params = GenerationParams(profile_id=FOUR_K.id, mode=Mode.TEXT_TO_VIDEO, duration_s=seconds, resolution=resolution, aspect_ratio="16:9",
                              fps=args.fps, audio=True)
    validate_params(FOUR_K, params)
    width, height = (320, 192) if args.tiny else FOUR_K.size_for(resolution, "16:9")
    return GenerationTask(job_id=str(uuid.uuid4()), profile=FOUR_K, params=params, prompt=args.prompt, negative_prompt=None, seed=seed,
                          width=width, height=height)


def admission(task: GenerationTask) -> dict:
    """What quantized.admit estimates for the task on this card: its tokens, the render's and the decode's peaks. Empty
    without a plan (a CPU, or a card whose plan fits every request)."""
    plan = backend.memory_plan(task.profile) if cuda else None
    if plan is None:
        return {}
    call = build_call(task)
    tokens, frames = call_tokens(call, task.width, task.height), call_frames(call)
    return {"tokens": tokens, "render_gib": round(plan.estimate_gib(tokens), 2), "decode_gib": round(plan.decode_gib(task.width, task.height, frames), 2),
            "usable_gib": round(plan.usable_gib, 2), "offload": plan.offload}


def run(name: str, task: GenerationTask) -> dict:
    estimate = admission(task)
    try:
        backend.admit(task, build_call(task))
    except CapacityRefused as refused:
        record = {"refused": str(refused), "admission": estimate, "checks": {}}
        summary["clips"][name] = record
        save()
        print(f"{name}: refused by admission: {refused}")
        return record
    started = time.perf_counter()
    result = backend.generate(task, lambda value, stage: logging.info("%s %.2f %s", name, value, stage))
    wall = round(time.perf_counter() - started, 1)
    path = out / f"{name}.mp4"
    path.write_bytes(result.data)
    info = probe(result.data)
    frames = ltx_num_frames(task.params.duration_s, task.params.fps)
    track = decode_audio(path, sample_rate=48_000)
    video_s, audio_s = info.frames / task.params.fps, (None if track is None else track.shape[1] / 48_000)
    rendered = recording.last
    checks = {
        "frames": rendered["frames"] == result.info.frames == info.frames == frames,
        "size": (info.width, info.height) == (task.width, task.height),
        "sound": info.audio and audio_s is not None and abs(audio_s - video_s) <= 1 / task.params.fps,
    }
    memory = rendered.get("memory_gib") or {}
    if cuda and estimate:
        checks["render peak within admission's estimate"] = memory["latent_render"]["allocated"] <= estimate["render_gib"]
        checks["decode peak within admission's estimate"] = memory["video_decode"]["allocated"] <= estimate["decode_gib"]
    record = {
        "size": f"{task.width}x{task.height}", "fps": task.params.fps, "seconds": task.params.duration_s, "frames": info.frames, "expected_frames": frames,
        "video_s": round(video_s, 3), "audio_s": audio_s, "mp4_bytes": len(result.data), "wall_s": wall, "timings_s": rendered["timings"],
        "memory_gib": memory, "admission": estimate, "frames_sha256": rendered["frames_sha256"], "checks": checks,
    }
    record["ok"] = all(checks.values())
    summary["clips"][name] = record
    save()
    print(f"{name}:", json.dumps(record, default=str))
    return record


if cuda:
    summary["device"] = {"name": torch.cuda.get_device_name(0), "total_gib": round(torch.cuda.get_device_properties(0).total_memory / 2**30, 2)}
plan = backend.memory_plan(FOUR_K) if cuda else None
summary["plan"] = None if plan is None else {
    "recipe": plan.recipe_id, "offload": plan.offload, "usable_gib": plan.usable_gib, "max_tokens": plan.max_tokens, "diffusion_decode": plan.diffusion_decode,
    "measured": plan.measured, "envelope": envelope_for_plan(plan, FOUR_K),
}
backend.warm(FOUR_K)

clips = [(resolution, float(seconds)) for resolution, seconds in (entry.split(":") for entry in args.clips.split(","))]
first = None
for index, (resolution, seconds) in enumerate(clips):
    name = f"4k-{resolution}" if [r for r, _ in clips].count(resolution) == 1 else f"4k-{resolution}-{index}"
    record = run(name, task_for(resolution, seconds, args.seed))
    if first is None and "refused" not in record:
        first = (name, resolution, seconds, record)
if args.repeat and first is not None:
    name, resolution, seconds, record = first
    again = run("4k-repeat", task_for(resolution, seconds, args.seed))
    if "refused" not in again:
        again["checks"]["repeat: the same frames"] = again["frames_sha256"] == record["frames_sha256"]
        again["ok"] = all(again["checks"].values())
        save()

rendered = [clip for clip in summary["clips"].values() if "refused" not in clip]
summary["result"] = "PASS" if rendered and all(clip["ok"] for clip in rendered) else "FAIL"
save()
print("RESULT:", summary["result"])
sys.exit(0 if summary["result"] == "PASS" else 1)
