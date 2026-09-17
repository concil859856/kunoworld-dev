"""The Director and the new memory limits on a GPU, through the worker's own code (no gateway):

1. what `LtxResidentBackend` advertises on this card (the serving envelope from the memory plan);
2. plans for every brief through `Worker._checked_plan`: the loaded enhancer writes, `kuno_protocol.plans` repairs,
   the image's safety gate checks every shot prompt; then `validate`, timing, tokens, and the GPU memory the planner
   leaves behind (the enhancer lives in host RAM between jobs);
3. one revision of the first plan (a single shot rewritten);
4. one plan rendered as a storyboard;
5. one enhanced-prompt clip (enhancement, the prompt check, the render);
6. the longest single 720p and 1080p clips the envelope advertises, with the audio length checked against the video.

    python run_director_worker.py /boards/briefs.json --out /out [--render roastery] [--skip-limits]
    python run_director_worker.py /boards/briefs.json --clip 720p:4:3:20 --clip 720p:21:9:14
"""

import argparse
import json
import logging
import time
import uuid
from dataclasses import replace
from pathlib import Path

from kuno_protocol.envelope import max_duration
from kuno_protocol.mp4 import probe
from kuno_protocol.plans import PlanOptions, PlanRevision, plan_context
from kuno_protocol.plans import validate as validate_plan
from kuno_protocol.profiles import (
    Mode,
    load_profiles,
    storyboard_frames,
    validate_params,
)
from kuno_protocol.schemas import GenerationParams
from kuno_worker.backends.base import GenerationTask
from kuno_worker.backends.ltx_resident import LtxResidentBackend
from kuno_worker.safety import check_request, default_gate
from kuno_worker.worker import Worker

parser = argparse.ArgumentParser()
parser.add_argument("briefs")
parser.add_argument("--out", default="/out")
parser.add_argument("--models-dir", default="/models/ltx-2.5")
parser.add_argument("--render", default="roastery", help="the brief whose plan is rendered as a storyboard")
parser.add_argument("--seed", type=int, default=1234)
parser.add_argument("--skip-limits", action="store_true")
parser.add_argument("--clip", action="append", default=[], metavar="RES:AR:SECONDS",
                    help="only render these single clips (e.g. 720p:4:3:20), with nothing else")
args = parser.parse_args()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("director-check")

import torch

out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
profile = load_profiles()["ltx-2.5-fast"]
summary: dict = {"steps": {}}


def gib(value: int) -> float:
    return round(value / 2**30, 2)


def save() -> None:
    (out / "director.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")


def streams(path: Path) -> dict:
    """Container, video and audio durations, from PyAV (the worker image has no ffprobe binary)."""
    import av

    with av.open(str(path)) as container:
        found = {s.type: float(s.duration * s.time_base) for s in container.streams if s.duration is not None}
        return {"format_s": container.duration / av.time_base, "video_s": found.get("video"), "audio_s": found.get("audio")}


class PlanRunner:
    """The worker's plan-writing methods without a gateway: progress is logged, nothing is sealed or uploaded."""

    PLAN_WRITES = Worker.PLAN_WRITES
    _checked_plan = Worker._checked_plan
    _draft_plan = Worker._draft_plan
    _generate_checked = staticmethod(Worker._generate_checked)

    def _progress(self, job_id, value, stage, force=False):
        log.info("job %s %.2f %s", job_id[:8], value, stage)


def task_for(params: GenerationParams, prompt: str, **extra) -> GenerationTask:
    width, height = profile.size_for(params.resolution, params.aspect_ratio)
    return GenerationTask(job_id=str(uuid.uuid4()), profile=profile, params=params, prompt=prompt, negative_prompt=None,
                          seed=args.seed, width=width, height=height, **extra)


default_gate()  # the image's classifiers, loaded before timing anything
backend = LtxResidentBackend(Path(args.models_dir), Path("/tmp/kuno-work"), offload="auto", weights_verify="size")
envelope = backend.serving_envelope(profile)
summary["device_gib"] = backend.device_gib
summary["envelope"] = envelope
started = time.perf_counter()
backend.warm(profile)
summary["load_s"] = round(time.perf_counter() - started, 1)
summary["after_load_allocated_gib"] = gib(torch.cuda.memory_allocated())
save()
print("envelope:", json.dumps(envelope))

# ---------------------------------------------------------------- plans
runner = PlanRunner()
briefs = {} if args.clip else json.loads(Path(args.briefs).read_text())
plans = {}
for name, brief in briefs.items():
    params = GenerationParams(profile_id=profile.id, mode=Mode.PLAN, duration_s=brief["target_s"], resolution=brief["resolution"],
                              aspect_ratio=brief["aspect_ratio"], fps=24, audio=brief.get("audio", True))
    record: dict = {"target_s": brief["target_s"], "aspect_ratio": brief["aspect_ratio"]}
    try:
        validate_params(profile, params)
        options = PlanOptions(style=brief.get("style"))
        served = max_duration(envelope, params.resolution, params.aspect_ratio, params.fps)
        context = plan_context(profile, params, options, served_max_s=served)
        task = task_for(params, brief["brief"], options={"plan": options.model_dump(mode="json", exclude_none=True)})
        before = torch.cuda.memory_allocated()
        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        plan, tokens = runner._checked_plan(backend, task, context, options)
        record["wall_s"] = round(time.perf_counter() - started, 1)
        validate_plan(plan, profile, context=context)
        record.update(
            ok=True, tokens=tokens, tokens_per_s=round(tokens / record["wall_s"], 1), max_shot_s=context.max_shot_s,
            shots=len(plan.shots), duration_s=plan.duration_s, joins=[s.join for s in plan.shots],
            durations=[s.duration_s for s in plan.shots], repairs=plan.repairs, title=plan.title,
            peak_extra_gib=gib(torch.cuda.max_memory_allocated() - before), left_on_gpu_gib=gib(torch.cuda.memory_allocated() - before),
        )
        (out / f"plan-{name}.json").write_text(plan.model_dump_json(indent=2) + "\n")
        plans[name] = (plan, context, task)
    except Exception as exc:  # record and go on to the next brief
        record.update(ok=False, error=f"{type(exc).__name__}: {getattr(exc, 'code', '')} {exc}")
        log.exception("plan %s failed", name)
    summary["steps"][f"plan:{name}"] = record
    save()
    print(f"plan {name}:", json.dumps(record))

# ---------------------------------------------------------------- a revision of one shot
if args.render in plans:
    plan, context, task = plans[args.render]
    options = PlanOptions(revise=PlanRevision(plan=plan, instruction="Make this shot a close-up of the roaster's hands.", shots=[2]))
    record = {}
    try:
        started = time.perf_counter()
        revised, tokens = runner._checked_plan(backend, replace(task, prompt=""), context, options)
        record = {"ok": True, "wall_s": round(time.perf_counter() - started, 1), "tokens": tokens,
                  "others_identical": all(a == b for i, (a, b) in enumerate(zip(plan.shots, revised.shots)) if i != 1)
                  and (plan.title, plan.scene) == (revised.title, revised.scene),
                  "shot2_before": plan.shots[1].prompt, "shot2_after": revised.shots[1].prompt, "repairs": revised.repairs}
        (out / f"plan-{args.render}-revised.json").write_text(revised.model_dump_json(indent=2) + "\n")
    except Exception as exc:
        record = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        log.exception("revision failed")
    summary["steps"]["revise"] = record
    save()
    print("revise:", json.dumps(record))

    # ------------------------------------------------------------ the plan rendered as a storyboard
    params = plan.storyboard_params()
    validate_params(profile, params)
    board = task_for(params, plan.scene, shot_prompts=plan.model_prompts())
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    record = {}
    try:
        result = backend.generate(board, lambda value, stage: None)
        path = out / f"storyboard-{args.render}.mp4"
        path.write_bytes(result.data)
        info = probe(result.data)
        expected = storyboard_frames(profile, params.shots, params.fps)
        record = {"ok": info.frames == expected, "wall_s": round(time.perf_counter() - started, 1), "frames": info.frames, "expected": expected,
                  "streams": streams(path), "peak_gib": gib(torch.cuda.max_memory_allocated())}
    except Exception as exc:
        record = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        log.exception("storyboard render failed")
    summary["steps"]["render-plan"] = record
    save()
    print("render-plan:", json.dumps(record))

# ---------------------------------------------------------------- an enhanced-prompt clip


def clip(name: str, prompt: str, resolution: str, duration: float, enhance: bool = False, aspect_ratio: str = "16:9") -> None:
    params = GenerationParams(profile_id=profile.id, mode=Mode.TEXT_TO_VIDEO, duration_s=duration, resolution=resolution,
                              aspect_ratio=aspect_ratio, fps=24)
    record: dict = {"resolution": resolution, "aspect_ratio": aspect_ratio, "duration_s": duration}
    try:
        validate_params(profile, params)
        task = task_for(params, prompt)
        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        if enhance:
            before = torch.cuda.memory_allocated()
            enhanced = backend.enhance_prompt(task)
            record["enhance_s"] = round(time.perf_counter() - started, 1)
            record["enhanced_prompt"] = enhanced
            record["enhancer_left_on_gpu_gib"] = gib(torch.cuda.memory_allocated() - before)
            check_request(enhanced)
            task = replace(task, prompt=enhanced)
        result = backend.generate(task, lambda value, stage: None)
        path = out / f"{name}.mp4"
        path.write_bytes(result.data)
        found = streams(path)
        record.update(ok=abs((found["audio_s"] or 0) - found["video_s"]) <= 0.05, wall_s=round(time.perf_counter() - started, 1),
                      frames=result.info.frames, streams=found, peak_gib=gib(torch.cuda.max_memory_allocated()),
                      peak_reserved_gib=gib(torch.cuda.max_memory_reserved()))
    except Exception as exc:
        record.update(ok=False, error=f"{type(exc).__name__}: {exc}")
        log.exception("clip %s failed", name)
    summary["steps"][name] = record
    save()
    print(f"{name}:", json.dumps(record))


MARKET = "A busy night market in the rain, neon signs, people with umbrellas, sizzling food stalls."
for spec in args.clip:
    resolution, ratio_w, ratio_h, seconds = spec.split(":")
    clip(f"clip-{resolution}-{ratio_w}x{ratio_h}-{seconds}s", MARKET, resolution, float(seconds), aspect_ratio=f"{ratio_w}:{ratio_h}")
if not args.clip:
    clip("enhanced-720p-5s", "a red fox trotting through fresh snow at dusk", "720p", 5, enhance=True)
if not args.skip_limits and not args.clip:
    clip("audio-720p-11s", "A lighthouse on a rocky coast at night, waves crashing, wind howling.", "720p", 11)
    for resolution in ("720p", "1080p"):
        longest = max_duration(envelope, resolution, "16:9", 24)
        if longest:
            clip(f"longest-{resolution}-{longest:g}s", MARKET, resolution, longest)
summary["result"] = "PASS" if all(step.get("ok") for step in summary["steps"].values()) else "FAIL"
save()
print("RESULT:", summary["result"])
