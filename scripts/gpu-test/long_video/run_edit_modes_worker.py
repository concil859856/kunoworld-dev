"""Audio-to-video and retake through the worker's own LtxResidentBackend on a GPU, with the checks a viewer or listener would
otherwise make, and the GPU memory of encoding a retake's source against what admission counts. Nothing is downloaded: the
sound is synthesized with ffmpeg, the clip to retake is rendered first, and the long retake's source is a test pattern.

    python run_edit_modes_worker.py --out /out [--models-dir /models/ltx-2.5] [--resolution 720p] [--only retake,a2v]
    python run_edit_modes_worker.py --out /out --tiny --long-retake 3   # a CPU dry run on tiny random weights: the flow

Jobs, in this order (ltx-2.5-fast first, then ltx-2.5-pro, so the weights load once each, in one process):
  source         a 5 s text-to-video clip with sound on ltx-2.5-fast: the clip the retakes start from
  retake         its middle 2 s (1.5 s to 3.5 s) regenerated from a new prompt, picture and sound
  retake-audio   the same window with regenerate_video false: every video token held, the sound regenerated
  retake-long    the longest retake admission accepts at this size and frame rate (--long-retake auto; 18 s of 720p at
                 24 fps on an RTX PRO 6000), of a test-pattern clip with a tone, its middle 2 s regenerated
  a2v            ltx-2.5-pro (the only profile offering it) from a speech-like signal over a little melody, from 0.5 s in,
                 with the source clip's first frame as first_frame. Loading it evicts ltx-2.5-fast.

Checks (`edit_modes.json`, RESULT: PASS when all hold; --tiny skips the ones about pictures, sound and memory, which random
weights on a CPU can't pass):
  every job      frames == the job's frame count in the render and the MP4; the MP4's sound track as long as its picture
                 (within a frame); held tokens bit-identical after denoising and shown at timestep 0 in every pass;
                 on a GPU, the job's peak allocated memory within admission's estimate (quantized.admit: the larger of
                 the render's and the encode's peaks, plus the held tokens)
  a2v            the returned samples are the source's, exactly; the MP4's AAC track still lines up with the source (best
                 lag within 5 ms, correlation > 0.9); the audio VAE round trip (encode, decode, vocoder) resembles the
                 source (log-mel correlation > 0.6), which checks ltx_pinning.AUDIO_N_FFT against the real checkpoint
  retake         samples outside the regenerated span identical to the source's; frames a latent frame or more away from
                 the regenerated frames near-identical to the source's (PSNR >= 28 dB against the source decoded as the
                 job conforms it); the window changed (its mean PSNR below the held frames' lowest); no click at the
                 splice (sample jump at each end within 8x the typical step)
  retake-audio   every frame near-identical to the source (PSNR >= 28 dB); samples outside the span identical
  retake-long    samples outside the span identical; held-frame PSNR is recorded, not checked (a test pattern's fine
                 lines are the VAE's worst case)
  source encode  (`source_encode`, and `encode` in retake-long) the worker's chunked encode (ltx_chunked_encode) on its
                 own: its peak over the weights within quantized.source_encode_gib; at 5 s, its tokens against the
                 whole-clip encode's (`vae.encode`, as the worker encoded before): mean difference within 1% of their
                 spread and the largest within 25% (a misaligned chunk differs by the whole spread; bf16 kernel choice by
                 0.06 at most on 2026-09-17), with both peaks, a 16-frame-chunk
                 peak, the loaded encoder's layout and its cached activations per pixel (522 for diffusers' default layout)
  loads          every load after the first starts with none of the evicted profile's modules alive and, on a GPU, under
                 1 GiB still allocated. On 2026-09-17 the ltx-2.5-pro load ran out of memory at 94.19 GiB: this driver
                 had measured the encode at module level, so its `renderer` (an LTX2PinnedPipeline built from every
                 ltx-2.5-fast component) outlived the eviction. Every step is a function now, and Recording keeps
                 host copies and lets go of its adapter when the store unloads it.
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import subprocess
import sys
import time
import uuid
import weakref
from pathlib import Path

import numpy as np

from kuno_protocol.mp4 import probe
from kuno_protocol.profiles import InputRole, Mode, load_profiles, ltx_num_frames, validate_params
from kuno_protocol.schemas import GenerationParams, InputRef
from kuno_worker.backends import ltx_resident
from kuno_worker.backends.base import GenerationTask, InputFile
from kuno_worker.backends.ltx_edit import decode_audio, decode_frames, fit_samples
from kuno_worker.backends.ltx_resident import LtxResidentBackend
from kuno_worker.backends.media_tools import ffmpeg_exe
from kuno_worker.backends.quantized import _longest_fitting, latent_tokens, source_encode_gib, source_held_gib
from kuno_worker.backends.resident import PipelineResult

parser = argparse.ArgumentParser()
parser.add_argument("--out", default="/out")
parser.add_argument("--models-dir", default="/models/ltx-2.5")
parser.add_argument("--resolution", default="720p")
parser.add_argument("--fps", type=int, default=24)
parser.add_argument("--seed", type=int, default=1234)
parser.add_argument("--offload", default="auto")
parser.add_argument("--a2v-duration", type=float, default=4.0, help="ltx-2.5-pro renders 30 guided steps: about 58 s per output second at 720p")
parser.add_argument("--long-retake", default="auto", help="seconds, or auto: the longest retake admission accepts here (none without a memory plan)")
parser.add_argument("--only", default="retake,retake-audio,retake-long,a2v", help="comma-separated: retake, retake-audio, retake-long, a2v")
parser.add_argument("--tiny", action="store_true", help="CPU dry run on tiny random weights (needs subnet/worker/tests on PYTHONPATH)")
args = parser.parse_args()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

import torch  # noqa: E402

PROFILES = load_profiles()
FAST, PRO = PROFILES["ltx-2.5-fast"], PROFILES["ltx-2.5-pro"]
ONLY = set(args.only.split(","))
QUALITY = not args.tiny
PSNR_HELD_DB = 28.0
# A load after an eviction starts with the evicted weights gone: the CUDA context and allocator bookkeeping aren't allocations.
EVICTED_LEFT_GIB = 1.0
# Chunked tokens against the whole-clip encode's, as a share of their spread: a misaligned chunk would differ by about 1
# everywhere. In bf16 on the GPU, convolutions over 8 frames and over 121 pick different kernels. On 2026-09-17 the largest
# single difference was 0.06 of the spread and the mean 0.001, and the held frames' PSNR was identical to the whole-clip
# encode's run (35.83 dB minimum, 38.25 mean). So the mean decides, and the maximum only catches a gross misalignment.
ENCODE_MATCH_MEAN_SPREAD = 0.01
ENCODE_MATCH_MAX_SPREAD = 0.25
cuda = torch.cuda.is_available()
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
summary: dict = {"args": vars(args), "loads": [], "jobs": {}}


def save() -> None:
    (out / "edit_modes.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")


def gib(value: int) -> float:
    return round(value / 2**30, 2)


def ffmpeg(*command: str) -> None:
    subprocess.run([ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", *command], check=True)


# ---------------------------------------------------------------- media, synthesized


def speech_like(path: Path, seconds: float) -> None:
    """Stereo 48 kHz: a voiced buzz gliding between 110 and 170 Hz with six harmonics, chopped into 3.7 syllables a second
    with pauses and lifted around two formants, over a four-note melody. Not speech, but it has pitch, onsets and silences."""
    phase = "(2*PI*140*t-60*cos(PI*t))"
    harmonics = "+".join(f"{w}*sin({k}*{phase})" for k, w in ((1, 1), (2, 0.6), (3, 0.45), (4, 0.3), (5, 0.2), (6, 0.12)))
    envelope = r"pow(max(0\,sin(2*PI*3.7*t))\,0.7)*gt(sin(2*PI*0.37*t+1)\,-0.55)"
    voice = f"0.12*({harmonics})*{envelope}"
    notes = r"262*lt(mod(t\,2)\,0.5)+330*between(mod(t\,2)\,0.5\,1)+392*between(mod(t\,2)\,1\,1.5)+523*gte(mod(t\,2)\,1.5)"
    melody = f"0.08*sin(2*PI*t*({notes}))"
    ffmpeg("-f", "lavfi", "-i", f"aevalsrc=exprs={voice}+{melody}|0.8*{voice}+1.2*{melody}:s=48000:d={seconds:g}",
           "-af", "equalizer=f=700:t=q:w=1.2:g=6,equalizer=f=1200:t=q:w=1.2:g=4", "-c:a", "pcm_s16le", str(path))


def test_pattern_clip(path: Path, width: int, height: int, seconds: float) -> None:
    ffmpeg("-f", "lavfi", "-i", f"testsrc2=size={width}x{height}:rate={args.fps}:duration={seconds:g}", "-f", "lavfi", "-i",
           f"sine=frequency=220:sample_rate=48000:duration={seconds:g}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path))


def conformed_source(path: Path, width: int, height: int, seconds: float) -> tuple[np.ndarray, np.ndarray]:
    """The frames and samples a retake of `seconds` holds from `path`, fitted as the job fits them (ltx_edit.render_edit)."""
    frames = ltx_num_frames(seconds, args.fps)
    pictures = decode_frames(path, fps=args.fps, width=width, height=height, count=frames)
    if len(pictures) < frames:
        pictures = np.concatenate([pictures, np.repeat(pictures[-1:], frames - len(pictures), axis=0)])
    sound = fit_samples(decode_audio(path, sample_rate=48_000, duration_s=frames / args.fps), round(frames / args.fps * 48_000))
    return pictures, sound


# ---------------------------------------------------------------- measures


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = float(np.mean((a.astype(np.float32) - b.astype(np.float32)) ** 2))
    return 99.0 if mse == 0 else round(10 * np.log10(255.0**2 / mse), 2)


def best_lag(reference: np.ndarray, other: np.ndarray, max_lag: int) -> tuple[int, float]:
    """(lag in samples, correlation) that best lines `other` up with `reference`, mono float, via the FFT."""
    n = min(len(reference), len(other))
    x, y = reference[:n] - reference[:n].mean(), other[:n] - other[:n].mean()
    spectrum = np.fft.rfft(x, 2 * n) * np.conj(np.fft.rfft(y, 2 * n))
    corr = np.fft.irfft(spectrum)
    lags = np.concatenate([corr[: max_lag + 1], corr[-max_lag:]])
    index = int(np.argmax(lags))
    lag = index if index <= max_lag else index - len(lags)
    return -lag, float(lags[index] / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-9))


def jump_ratio(track: np.ndarray, at: int) -> float | None:
    """The sample step across `at` against the typical (median absolute) step of the 20 ms before it."""
    if at <= 960 or at >= track.shape[1]:
        return None
    mono = track.astype(np.float32).mean(axis=0)
    typical = float(np.median(np.abs(np.diff(mono[at - 960 : at])))) + 1.0
    return round(abs(float(mono[at] - mono[at - 1])) / typical, 2)


def log_mel(samples: np.ndarray, rate: int) -> np.ndarray:
    import torchaudio

    waveform = torch.as_tensor(samples, dtype=torch.float32)
    waveform = torchaudio.functional.resample(waveform, rate, 16_000)
    mel = torchaudio.transforms.MelSpectrogram(sample_rate=16_000, n_fft=1024, hop_length=160, n_mels=64, power=1.0, mel_scale="slaney", norm="slaney")(waveform)
    return torch.log(torch.clamp(mel, min=1e-5)).mean(dim=0).numpy()


# ---------------------------------------------------------------- the backend


def on_host(value):
    """`value` with every tensor in it copied to host memory: a raw result kept for the checks must not keep GPU memory
    (the text-to-video pipeline returns its sound as a CUDA tensor)."""
    if hasattr(value, "detach"):
        return value.detach().to("cpu")
    if isinstance(value, dict):
        return {key: on_host(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(on_host(item) for item in value)
    return value


class Recording:
    """The loaded adapter, keeping a host copy of each render's raw result (frames and samples before encoding). When the
    model store evicts it, it lets go of the adapter and the copy, so nothing here keeps the evicted weights alive."""

    def __init__(self, adapter):
        self.adapter, self.last = adapter, None

    def __call__(self, **call):
        result = self.adapter(**call)
        self.last = on_host(result)
        return result

    def unload(self) -> None:
        adapter, self.adapter, self.last = self.adapter, None, None
        adapter.unload()

    def __getattr__(self, name):
        adapter = self.__dict__.get("adapter")
        if adapter is None:
            raise AttributeError(f"{name}: this pipeline was unloaded")
        return getattr(adapter, name)


recordings: dict[str, Recording] = {}
loaded_modules: list = []  # weak references to every loaded profile's pipeline components


def recorded(profile, build) -> Recording:
    """Loads through `build`, noting first what of the previous load is still alive and allocated: the store has evicted
    it by now (capacity 1), so neither should be."""
    gc.collect()
    if cuda:
        torch.cuda.synchronize()
    summary["loads"].append({
        "profile": profile.id, "allocated_before_gib": gib(torch.cuda.memory_allocated()) if cuda else None,
        "evicted_modules_alive": sum(ref() is not None for ref in loaded_modules),
    })
    started = time.perf_counter()
    adapter = build(profile)
    summary["loads"][-1]["seconds"] = round(time.perf_counter() - started, 1)
    components = next(iter(adapter.pipelines.values())).components.values()
    loaded_modules[:] = [weakref.ref(module) for module in components if isinstance(module, torch.nn.Module)]
    recordings[profile.id] = Recording(adapter)
    save()
    return recordings[profile.id]


if args.tiny:
    from kuno_worker.backends.runtimes import LtxAdapter
    from ltx_storyboard_doubles import TinyPinnedRenderer, tiny_pipelines

    ltx_resident.FULL_STEPS = 3
    size = (320, 192)

    def load(profile):
        return recorded(profile, lambda _: LtxAdapter(tiny_pipelines(audio_ch_mult=(1, 1, 1)), device="cpu", renderer=lambda p, device: TinyPinnedRenderer(p)))
else:
    from kuno_worker.backends.runtimes import ltx_loader

    size = None
    base_loader = ltx_loader(Path(args.models_dir), offload=args.offload, weights_verify="size")

    def load(profile):
        return recorded(profile, base_loader)


backend = LtxResidentBackend(None, Path("/tmp/kuno-work"), loader=load, offload=args.offload)


def edit_plan(profile):
    """The memory plan the backend admits an edit by, or None (a CPU)."""
    return backend.memory_plan(profile) or backend._edit_plan(profile)


def task_for(profile, mode: Mode, prompt: str, duration: float, inputs: list[tuple[InputRole, Path, dict]], options: dict | None = None, seed: int | None = None):
    mimes = {".wav": "audio/wav", ".mp4": "video/mp4", ".png": "image/png"}
    files = []
    for index, (role, path, ref) in enumerate(inputs):
        data = path.read_bytes()
        files.append(InputFile(ref=InputRef(index=index, role=role, mime=mimes[path.suffix], sha256="0" * 64, size=len(data), **ref), data=data, mime=mimes[path.suffix]))
    params = GenerationParams(profile_id=profile.id, mode=mode, duration_s=duration, resolution=args.resolution, aspect_ratio="16:9", fps=args.fps,
                              input_roles=[role for role, _, _ in inputs])
    validate_params(profile, params)
    width, height = size or profile.size_for(args.resolution, "16:9")
    return GenerationTask(job_id=str(uuid.uuid4()), profile=profile, params=params, prompt=prompt, negative_prompt=None,
                          seed=args.seed if seed is None else seed, width=width, height=height, inputs=files, options=options or {})


def admission(task: GenerationTask) -> dict | None:
    """What quantized.admit estimates for `task`'s peak on this GPU, or None without a plan."""
    plan = edit_plan(task.profile) if cuda else None
    if plan is None:
        return None
    mode = task.params.mode.value if task.params.mode in (Mode.RETAKE, Mode.AUDIO_TO_VIDEO) else None
    tokens = latent_tokens(task.width, task.height, ltx_num_frames(task.params.duration_s, task.params.fps))
    encode, held = source_encode_gib(mode, task.width, task.height), source_held_gib(mode)
    render = plan.estimate_gib(tokens)
    return {
        "tokens": tokens, "render_gib": round(render, 2), "encode_gib": round(plan.encode_gib(encode), 2) if mode else None, "held_gib": held,
        "estimate_gib": round(max(render, plan.encode_gib(encode) if mode else 0.0) + held, 2), "usable_gib": plan.usable_gib,
    }


def run(name: str, task: GenerationTask) -> tuple[dict, dict]:
    """Renders `task`, writes <name>.mp4, and returns (record, host copy of the raw result)."""
    if cuda:
        torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    result = backend.generate(task, lambda value, stage: logging.info("%s %.2f %s", name, value, stage))
    wall = round(time.perf_counter() - started, 1)
    (out / f"{name}.mp4").write_bytes(result.data)
    raw = recordings[task.profile.id].last
    rendered = PipelineResult.from_pipeline(raw).frames
    info = probe(result.data)
    frames = ltx_num_frames(task.params.duration_s, task.params.fps)
    track = decode_audio(out / f"{name}.mp4", sample_rate=48_000)
    video_s = info.frames / task.params.fps
    audio_s = None if track is None else track.shape[1] / 48_000
    report = raw.get("edit") or {}
    stages = report.get("pins_exact", {})
    checks = {
        "frames": result.info.frames == info.frames == len(rendered) == frames,
        "sound as long as the picture": audio_s is not None and abs(audio_s - video_s) <= 1 / task.params.fps,
        "no step commitment": result.step_commitment is None,
    }
    if report:
        checks["held tokens exact in every pass"] = bool(stages) and all(value is True for value in stages.values())
        # Per pass and modality: True where tokens were held, None where none were; never False.
        seen = [value for per_pass in report["seen_clean"].values() for value in per_pass.values()]
        checks["held tokens seen at t = 0"] = bool(seen) and False not in seen and True in seen
    peak = gib(torch.cuda.max_memory_allocated()) if cuda else None
    estimate = admission(task)
    if estimate is not None:
        checks["peak within admission's estimate"] = peak <= estimate["estimate_gib"]
    record = {
        "frames": info.frames, "expected_frames": frames, "container_s": info.duration_s, "video_s": round(video_s, 3), "audio_s": audio_s,
        "wall_s": wall, "peak_gpu_gib": peak, "peak_gpu_reserved_gib": gib(torch.cuda.max_memory_reserved()) if cuda else None,
        "admission": estimate, "edit": report, "checks": checks,
    }
    return record, raw


def finish(name: str, record: dict) -> None:
    record["ok"] = all(record["checks"].values())
    summary["jobs"][name] = record
    save()
    print(f"{name}:", json.dumps({k: v for k, v in record.items() if k not in ("edit", "psnr_db")}, default=str))


def frame_array(frame) -> np.ndarray:
    return np.asarray(frame.convert("RGB") if hasattr(frame, "convert") else frame, dtype=np.uint8)


# ---------------------------------------------------------------- encoding a retake's source


def whole_clip_tokens(renderer, pictures: np.ndarray):
    """The source's tokens as the worker encoded them before chunking: every frame on the GPU, one `vae.encode`."""
    pipeline, vae = renderer.pipeline, renderer.pipeline.vae
    device = pipeline._execution_device
    height, width = pictures.shape[1:3]
    pixels = torch.empty((1, 3, len(pictures), height, width), dtype=vae.dtype, device=device)
    with torch.no_grad():
        for index, frame in enumerate(pictures):
            pixels[0, :, index] = (torch.from_numpy(frame).to(device).permute(2, 0, 1).to(torch.float32) / 127.5 - 1.0).to(vae.dtype)
        latent = vae.encode(pixels).latent_dist.mode()
        del pixels
        latent = pipeline._normalize_latents(latent, vae.latents_mean, vae.latents_std).to(torch.float32)
        return pipeline._pack_latents(latent, pipeline.transformer_spatial_patch_size, pipeline.transformer_temporal_patch_size)


def measure_encode(renderer, pictures: np.ndarray, *, whole: bool = False, chunk: int | None = None) -> tuple[dict, object]:
    """One encode of `pictures` on its own: seconds and the peak allocated over what was allocated before, and its tokens on
    the host."""
    height, width = pictures.shape[1:3]
    if cuda:
        torch.cuda.synchronize()
        before = torch.cuda.memory_allocated()
        torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    tokens = whole_clip_tokens(renderer, pictures) if whole else renderer.encode_video(pictures, width, height, chunk)
    if cuda:
        torch.cuda.synchronize()
    record = {"seconds": round(time.perf_counter() - started, 2), "measured_extra_gib": gib(torch.cuda.max_memory_allocated() - before) if cuda else None}
    tokens = tokens.detach().to("cpu", torch.float32)
    if cuda:
        torch.cuda.empty_cache()
    return record, tokens


def encoder_layout(renderer) -> dict:
    from kuno_worker.backends.ltx_chunked_encode import CHUNK_LATENT_FRAMES, encoder_cache_values

    vae = renderer.pipeline.vae
    config = {key: vae.config.get(key) for key in ("block_out_channels", "layers_per_block", "downsample_type", "spatio_temporal_scaling",
                                                   "patch_size", "patch_size_t", "encoder_causal")}
    return {"chunk_frames": CHUNK_LATENT_FRAMES * int(vae.temporal_compression_ratio), "cache_values_per_pixel": encoder_cache_values(vae.encoder),
            "vae_encoder_config": config}


def source_encode_at_5s(pictures: np.ndarray) -> None:
    """The chunked encode against admission's estimate and against the whole-clip encode, which fits at 5 s."""
    frames, (height, width) = len(pictures), pictures.shape[1:3]
    with backend.store.acquire(FAST) as loaded:
        renderer = loaded.pinned_renderer()
        chunked, tokens = measure_encode(renderer, pictures)
        by_16, _ = measure_encode(renderer, pictures, chunk=2)
        whole, reference = measure_encode(renderer, pictures, whole=True)
        record = {"frames": frames, "size": f"{width}x{height}", **encoder_layout(renderer), **chunked,
                  "estimate_gib": round(source_encode_gib("retake", width, height), 2), "chunks_of_16_frames": by_16, "whole_clip": whole}
    difference = (tokens - reference).abs()
    spread = float(reference.std())
    record["tokens_against_whole_clip"] = {"max_abs": float(difference.max()), "mean_abs": float(difference.mean()), "spread": spread}
    record["checks"] = {"tokens match the whole-clip encode": float(difference.mean()) <= ENCODE_MATCH_MEAN_SPREAD * spread
                        and float(difference.max()) <= ENCODE_MATCH_MAX_SPREAD * spread}
    if cuda:
        record["checks"]["chunked encode within the estimate"] = record["measured_extra_gib"] <= record["estimate_gib"]
    summary["source_encode"] = record
    save()
    print("source encode:", json.dumps(record, default=str))


def retake_checks(record: dict, raw: dict, pictures: np.ndarray, sound: np.ndarray, *, quality: bool) -> None:
    report = raw["edit"]
    s0, s1 = report["regenerated_samples"] or (0, 0)
    track = raw["audio"]
    record["checks"]["sound outside the span identical to the source"] = bool(
        np.array_equal(track[:, :s0], sound[:, :s0]) and np.array_equal(track[:, s1:], sound[:, s1:])
    )
    p0, p1 = report["regenerated_frames"]
    scores = [psnr(frame_array(f), pictures[i]) for i, f in enumerate(PipelineResult.from_pipeline(raw).frames)]
    held = [s for i, s in enumerate(scores) if p1 <= p0 or i < p0 - 8 or i >= p1 + 8]
    inside = [s for i, s in enumerate(scores) if p0 <= i < p1]
    record["psnr_db"] = {"per_frame": scores, "held_min": min(held) if held else None, "held_mean": round(float(np.mean(held)), 2) if held else None,
                         "window_mean": round(float(np.mean(inside)), 2) if inside else None}
    record["splice_jump_ratio"] = [jump_ratio(track, s0), jump_ratio(track, s1)] if s1 > s0 else None
    if quality:
        record["checks"]["held frames near-identical to the source"] = bool(held) and min(held) >= PSNR_HELD_DB
        if inside:
            record["checks"]["the window changed"] = float(np.mean(inside)) < min(held)
        if s1 > s0:
            record["checks"]["no click at the splice"] = all(r is None or r <= 8 for r in record["splice_jump_ratio"])


def retakes(width: int, height: int) -> None:
    source = out / "retake-source.mp4"
    if args.tiny:
        test_pattern_clip(source, width, height, 5.2)
    else:
        record, _ = run("retake-source", task_for(
            FAST, Mode.TEXT_TO_VIDEO, "A woman at a kitchen table talks to the camera about her garden, gesturing with a mug. Warm morning light. "
            "She says: \"The tomatoes came in early this year, and the basil is everywhere.\"", 5.0, [],
        ))
        finish("retake-source", record)
    pictures, sound = conformed_source(source, width, height, 5.0)
    source_encode_at_5s(pictures)
    for name, options, prompt in (
        ("retake", {}, "The woman stands up, laughing, and holds a basket of red tomatoes up to the camera."),
        ("retake-audio", {"regenerate_video": False}, "She says: \"Honestly, the peppers were a disaster.\""),
    ):
        if name not in ONLY:
            continue
        task = task_for(FAST, Mode.RETAKE, prompt, 5.0, [(InputRole.SOURCE_VIDEO, source, {"start_s": 1.5, "end_s": 3.5})], options=options, seed=args.seed + 7)
        record, raw = run(name, task)
        retake_checks(record, raw, pictures, sound, quality=QUALITY)
        finish(name, record)


def long_retake(width: int, height: int) -> None:
    if args.long_retake == "auto":
        plan = edit_plan(FAST) if cuda else None
        seconds = _longest_fitting(plan, FAST, width, height, args.fps, "retake") if plan is not None else None
        if seconds is None:
            summary["retake_long_skipped"] = "no memory plan to find the longest retake by; pass --long-retake <seconds>"
            save()
            return
    else:
        seconds = float(args.long_retake)
    source = out / "retake-long-source.mp4"
    test_pattern_clip(source, width, height, seconds + 0.2)
    pictures, sound = conformed_source(source, width, height, seconds)
    with backend.store.acquire(FAST) as loaded:
        encode, _ = measure_encode(loaded.pinned_renderer(), pictures)
    encode.update(frames=len(pictures), estimate_gib=round(source_encode_gib("retake", width, height), 2))
    middle = seconds / 2
    task = task_for(FAST, Mode.RETAKE, "A test card fills the screen, then a slow pan across a bright studio set.", seconds,
                    [(InputRole.SOURCE_VIDEO, source, {"start_s": middle - 1.0, "end_s": middle + 1.0})], seed=args.seed + 11)
    record, raw = run("retake-long", task)
    retake_checks(record, raw, pictures, sound, quality=False)
    record["encode"] = encode
    if cuda:
        record["checks"]["chunked encode within the estimate"] = encode["measured_extra_gib"] <= encode["estimate_gib"]
    finish("retake-long", record)


# ---------------------------------------------------------------- audio-to-video (ltx-2.5-pro)


def audio_to_video(width: int, height: int) -> None:
    sound = out / "a2v-source.wav"
    speech_like(sound, args.a2v_duration + 1.0)
    first = out / "a2v-first-frame.png"
    source = out / "retake-source.mp4"
    if source.exists():
        ffmpeg("-i", str(source), "-frames:v", "1", str(first))
    else:
        ffmpeg("-f", "lavfi", "-i", f"color=0x406080:s={width}x{height}", "-frames:v", "1", str(first))
    task = task_for(
        PRO, Mode.AUDIO_TO_VIDEO, "A woman at a kitchen table talks and hums along to music playing from a small radio beside her.",
        args.a2v_duration, [(InputRole.SOURCE_AUDIO, sound, {"start_s": 0.5}), (InputRole.FIRST_FRAME, first, {})],
    )
    record, raw = run("a2v", task)
    frames = ltx_num_frames(args.a2v_duration, args.fps)
    samples = round(frames / args.fps * 48_000)
    expected = fit_samples(decode_audio(sound, sample_rate=48_000, start_s=0.5, duration_s=frames / args.fps), samples)
    record["checks"]["returned samples are the source's"] = bool(np.array_equal(raw["audio"], expected))
    encoded = decode_audio(out / "a2v.mp4", sample_rate=48_000)
    lag, corr = best_lag(expected.astype(np.float32).mean(axis=0), fit_samples(encoded, samples).astype(np.float32).mean(axis=0), 4800)
    record["mp4_sound"] = {"lag_ms": round(1000 * lag / 48_000, 2), "correlation": round(corr, 4)}
    with backend.store.acquire(PRO) as loaded:
        renderer = loaded.pinned_renderer()
        pipeline = renderer.pipeline
        g = renderer.geometry(float(args.fps))
        latents = g.audio_latents(frames)
        with torch.no_grad():
            tokens = renderer.encode_audio(expected.astype(np.float32) / 32768, 48_000, latents)
            unpacked = pipeline._unpack_audio_latents(
                pipeline._denormalize_audio_latents(tokens, pipeline.audio_vae.latents_mean, pipeline.audio_vae.latents_std), latents,
                num_mel_bins=pipeline.audio_mel_bins // pipeline.audio_vae_mel_compression_ratio,
            )
            mel = pipeline.audio_vae.decode(unpacked.to(pipeline.audio_vae.dtype), return_dict=False)[0]
            back = pipeline.vocoder(mel).float().cpu().numpy()[0]
    rebuilt, original = log_mel(back, g.sample_rate), log_mel(expected.astype(np.float32) / 32768, 48_000)
    n = min(rebuilt.shape[1], original.shape[1])
    round_trip = float(np.corrcoef(rebuilt[:, :n].ravel(), original[:, :n].ravel())[0, 1])
    record["audio_vae_round_trip"] = {"log_mel_correlation": round(round_trip, 4), "samples": int(back.shape[-1])}
    if QUALITY:
        record["checks"]["the MP4's sound lines up with the source"] = abs(lag) <= 240 and corr > 0.9
        record["checks"]["the audio VAE round trip resembles the source"] = round_trip > 0.6
    finish("a2v", record)


# ---------------------------------------------------------------- the run

# Every step is a function: whatever it held on the GPU (a renderer, a loaded adapter) is released when it returns, so the
# model store's eviction of ltx-2.5-fast really frees it before ltx-2.5-pro loads.
width, height = size or FAST.size_for(args.resolution, "16:9")
if ONLY & {"retake", "retake-audio"}:
    retakes(width, height)
if "retake-long" in ONLY:
    long_retake(width, height)
if "a2v" in ONLY:
    audio_to_video(width, height)

later = summary["loads"][1:]
summary["evicted_before_each_load"] = all(
    load["evicted_modules_alive"] == 0 and (not cuda or load["allocated_before_gib"] < EVICTED_LEFT_GIB) for load in later
)
checks = [all(summary.get("source_encode", {}).get("checks", {}).values()), summary["evicted_before_each_load"]]
summary["result"] = "PASS" if summary["jobs"] and all(checks) and all(job["ok"] for job in summary["jobs"].values()) else "FAIL"
save()
print("RESULT:", summary["result"])
sys.exit(0 if summary["result"] == "PASS" else 1)
