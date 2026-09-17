"""Audio-to-video and retake through the worker's own LtxResidentBackend on a GPU, with the checks a viewer or listener would
otherwise make. Nothing is downloaded: the sound is synthesized with ffmpeg and the clip to retake is rendered first.

    python run_edit_modes_worker.py --out /out [--models-dir /models/ltx-2.5] [--resolution 720p] [--only retake,a2v]
    python run_edit_modes_worker.py --out /out --tiny     # a CPU dry run on tiny random weights: the flow, not the pictures

Jobs, in this order (ltx-2.5-fast first, then ltx-2.5-pro, so the weights load once each):
  source         a 5 s text-to-video clip with sound on ltx-2.5-fast: the clip every retake starts from
  retake         its middle 2 s (1.5 s to 3.5 s) regenerated from a new prompt, picture and sound
  retake-audio   the same window with regenerate_video false: every video token held, the sound regenerated
  a2v            ltx-2.5-pro (the only profile offering it) from a speech-like signal over a little melody, from 0.5 s in,
                 with the source clip's first frame as first_frame

Checks (`edit_modes.json`, RESULT: PASS when all hold; --tiny skips the ones about pictures and sound, which random
weights can't pass):
  every job      frames == the job's frame count in the render and the MP4; the MP4's sound track as long as its picture
                 (within a frame); held tokens bit-identical after denoising and shown at timestep 0 in every pass
  a2v            the returned samples are the source's, exactly; the MP4's AAC track still lines up with the source (best
                 lag within 5 ms, correlation > 0.9); the audio VAE round trip (encode, decode, vocoder) resembles the
                 source (log-mel correlation > 0.6), which checks ltx_pinning.AUDIO_N_FFT against the real checkpoint
  retake         samples outside the regenerated span identical to the source's; frames a latent frame or more away from
                 the regenerated frames near-identical to the source's (PSNR >= 28 dB against the source decoded as the
                 job conforms it); the window changed (its mean PSNR below the held frames' lowest); no click at the
                 splice (sample jump at each end within 8x the typical step)
  retake-audio   every frame near-identical to the source (PSNR >= 28 dB); samples outside the span identical
Also recorded: wall time, peak GPU memory per job, and the GPU memory encoding the source took on its own against
quantized.source_encode_gib's estimate (the number admission refuses retakes by; unmeasured until this runs).
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
import uuid
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
from kuno_worker.backends.quantized import latent_tokens, source_encode_gib
from kuno_worker.backends.resident import PipelineResult

parser = argparse.ArgumentParser()
parser.add_argument("--out", default="/out")
parser.add_argument("--models-dir", default="/models/ltx-2.5")
parser.add_argument("--resolution", default="720p")
parser.add_argument("--fps", type=int, default=24)
parser.add_argument("--seed", type=int, default=1234)
parser.add_argument("--offload", default="auto")
parser.add_argument("--a2v-duration", type=float, default=4.0, help="ltx-2.5-pro renders 30 guided steps: about 100 s per 2 s at 720p")
parser.add_argument("--only", default="retake,retake-audio,a2v", help="comma-separated: retake, retake-audio, a2v")
parser.add_argument("--tiny", action="store_true", help="CPU dry run on tiny random weights (needs subnet/worker/tests on PYTHONPATH)")
args = parser.parse_args()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

import torch  # noqa: E402

PROFILES = load_profiles()
FAST, PRO = PROFILES["ltx-2.5-fast"], PROFILES["ltx-2.5-pro"]
ONLY = set(args.only.split(","))
QUALITY = not args.tiny
PSNR_HELD_DB = 28.0
cuda = torch.cuda.is_available()
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
summary: dict = {"args": vars(args), "jobs": {}}


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


class Recording:
    """The loaded adapter, keeping each render's raw result (frames and samples before encoding)."""

    def __init__(self, adapter):
        self.adapter, self.last = adapter, None

    def __call__(self, **call):
        self.last = self.adapter(**call)
        return self.last

    def __getattr__(self, name):
        return getattr(self.adapter, name)


recordings: dict[str, Recording] = {}
if args.tiny:
    from kuno_worker.backends.runtimes import LtxAdapter
    from ltx_storyboard_doubles import TinyPinnedRenderer, tiny_pipelines

    ltx_resident.FULL_STEPS = 3
    size = (320, 192)

    def load(profile):
        adapter = LtxAdapter(tiny_pipelines(audio_ch_mult=(1, 1, 1)), device="cpu", renderer=lambda p, device: TinyPinnedRenderer(p))
        recordings[profile.id] = Recording(adapter)
        return recordings[profile.id]
else:
    from kuno_worker.backends.runtimes import ltx_loader

    size = None
    base_loader = ltx_loader(Path(args.models_dir), offload=args.offload, weights_verify="size")

    def load(profile):
        recordings[profile.id] = Recording(base_loader(profile))
        return recordings[profile.id]


backend = LtxResidentBackend(None, Path("/tmp/kuno-work"), loader=load, offload=args.offload)


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


def run(name: str, task: GenerationTask) -> tuple[dict, dict, bytes]:
    """Renders `task`, writes <name>.mp4, and returns (record, raw result, MP4)."""
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
    record = {
        "frames": info.frames, "expected_frames": frames, "container_s": info.duration_s, "video_s": round(video_s, 3), "audio_s": audio_s,
        "wall_s": wall, "peak_gpu_gib": gib(torch.cuda.max_memory_allocated()) if cuda else None,
        "peak_gpu_reserved_gib": gib(torch.cuda.max_memory_reserved()) if cuda else None, "edit": report, "checks": checks,
    }
    return record, raw, result.data


def finish(name: str, record: dict) -> None:
    record["ok"] = all(record["checks"].values())
    summary["jobs"][name] = record
    save()
    print(f"{name}:", json.dumps({k: v for k, v in record.items() if k != "edit"}, default=str))


def frame_array(frame) -> np.ndarray:
    return np.asarray(frame.convert("RGB") if hasattr(frame, "convert") else frame, dtype=np.uint8)


# ---------------------------------------------------------------- retake (ltx-2.5-fast)

width, height = size or FAST.size_for(args.resolution, "16:9")
source = out / "retake-source.mp4"
if ONLY & {"retake", "retake-audio"}:
    if args.tiny:
        test_pattern_clip(source, width, height, 5.2)
    else:
        record, _, data = run("retake-source", task_for(
            FAST, Mode.TEXT_TO_VIDEO, "A woman at a kitchen table talks to the camera about her garden, gesturing with a mug. Warm morning light. "
            "She says: \"The tomatoes came in early this year, and the basil is everywhere.\"", 5.0, [],
        ))
        finish("retake-source", record)
    frames = ltx_num_frames(5.0, args.fps)
    conformed = decode_frames(source, fps=args.fps, width=width, height=height, count=frames)
    if len(conformed) < frames:
        conformed = np.concatenate([conformed, np.repeat(conformed[-1:], frames - len(conformed), axis=0)])
    source_sound = fit_samples(decode_audio(source, sample_rate=48_000, duration_s=frames / args.fps), round(frames / args.fps * 48_000))

    # What encoding the source takes on the GPU by itself, against admission's estimate.
    if cuda:
        with backend.store.acquire(FAST) as loaded:
            renderer = loaded.pinned_renderer()
            torch.cuda.synchronize()
            before = torch.cuda.memory_allocated()
            torch.cuda.reset_peak_memory_stats()
            started = time.perf_counter()
            renderer.encode_video(conformed, width, height)
            torch.cuda.synchronize()
            summary["source_encode"] = {
                "frames": frames, "size": f"{width}x{height}", "seconds": round(time.perf_counter() - started, 2),
                "measured_extra_gib": gib(torch.cuda.max_memory_allocated() - before),
                "estimate_gib": round(source_encode_gib("retake", frames, width, height), 2),
                # The distilled bf16 recipe's measured activation line (precision_recipes.json) at the clip's tokens.
                "render_activation_estimate_gib": round(3.32 + 4.6 * latent_tokens(width, height, frames) / 10_000, 2),
            }
            record = summary["source_encode"]
            # Admission counts the source beside a render's activations, never both at once: the encode must fit in their sum.
            record["within_admission"] = record["measured_extra_gib"] <= record["estimate_gib"] + record["render_activation_estimate_gib"]
            torch.cuda.empty_cache()
        save()
        print("source encode:", json.dumps(summary["source_encode"]))

    for name, options, prompt in (
        ("retake", {}, "The woman stands up, laughing, and holds a basket of red tomatoes up to the camera."),
        ("retake-audio", {"regenerate_video": False}, "She says: \"Honestly, the peppers were a disaster.\""),
    ):
        if name not in ONLY:
            continue
        task = task_for(FAST, Mode.RETAKE, prompt, 5.0, [(InputRole.SOURCE_VIDEO, source, {"start_s": 1.5, "end_s": 3.5})], options=options, seed=args.seed + 7)
        record, raw, _ = run(name, task)
        report = raw["edit"]
        s0, s1 = report["regenerated_samples"] or (0, 0)
        track = raw["audio"]
        record["checks"]["sound outside the span identical to the source"] = bool(
            np.array_equal(track[:, :s0], source_sound[:, :s0]) and np.array_equal(track[:, s1:], source_sound[:, s1:])
        )
        p0, p1 = report["regenerated_frames"]
        scores = [psnr(frame_array(f), conformed[i]) for i, f in enumerate(PipelineResult.from_pipeline(raw).frames)]
        held = [s for i, s in enumerate(scores) if p1 <= p0 or i < p0 - 8 or i >= p1 + 8]
        inside = [s for i, s in enumerate(scores) if p0 <= i < p1]
        record["psnr_db"] = {"per_frame": scores, "held_min": min(held) if held else None, "held_mean": round(float(np.mean(held)), 2) if held else None,
                             "window_mean": round(float(np.mean(inside)), 2) if inside else None}
        record["splice_jump_ratio"] = [jump_ratio(track, s0), jump_ratio(track, s1)] if s1 > s0 else None
        if QUALITY:
            record["checks"]["held frames near-identical to the source"] = bool(held) and min(held) >= PSNR_HELD_DB
            if inside:
                record["checks"]["the window changed"] = float(np.mean(inside)) < min(held)
            if s1 > s0:
                record["checks"]["no click at the splice"] = all(r is None or r <= 8 for r in record["splice_jump_ratio"])
        finish(name, record)

# ---------------------------------------------------------------- audio-to-video (ltx-2.5-pro)

if "a2v" in ONLY:
    sound = out / "a2v-source.wav"
    speech_like(sound, args.a2v_duration + 1.0)
    first = out / "a2v-first-frame.png"
    if source.exists():
        ffmpeg("-i", str(source), "-frames:v", "1", str(first))
    else:
        ffmpeg("-f", "lavfi", "-i", f"color=0x406080:s={width}x{height}", "-frames:v", "1", str(first))
    task = task_for(
        PRO, Mode.AUDIO_TO_VIDEO, "A woman at a kitchen table talks and hums along to music playing from a small radio beside her.",
        args.a2v_duration, [(InputRole.SOURCE_AUDIO, sound, {"start_s": 0.5}), (InputRole.FIRST_FRAME, first, {})],
    )
    record, raw, data = run("a2v", task)
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

encode_ok = summary.get("source_encode", {}).get("within_admission", True)
summary["result"] = "PASS" if summary["jobs"] and encode_ok and all(job["ok"] for job in summary["jobs"].values()) else "FAIL"
save()
print("RESULT:", summary["result"])
sys.exit(0 if summary["result"] == "PASS" else 1)
