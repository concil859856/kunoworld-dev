"""Long LTX-2.5 videos from chained shots joined by AV-extend: the experiment, run on one GPU before the product has it.

Every shot is one ordinary LTX-2.5 generation, built by the worker's own `build_call`. A shot continues the one before
it by holding the tail of that shot's latents fixed at the head of its own (the technique of ComfyUI-JoyLTX25, MIT):

  continue  the last `--overlap` video latent frames and the matching audio latents: one seamless take
  cut       the audio latents only: the voice and room tone carry across a picture cut
  fresh     nothing: an independent shot

The held head is trimmed from the shot's decoded frames and samples before the shots are concatenated.

How the pin is held, from diffusers 0.40 (pipelines/ltx2/pipeline_ltx2_condition.py, transformer_ltx2.py):
  video  LTX2ConditionPipeline's native conditioning. prepare_latents returns a per-token conditioning_mask; the loop
         passes the transformer `timestep * (1 - mask)` per token, so masked tokens are seen as clean context at t = 0,
         and blends x0 = denoised * (1 - mask) + clean * mask before the Euler step, so their velocity is exactly zero.
         The pipeline itself only puts VAE-encoded pixels there; LTX2ExtendPipeline puts the previous shot's tokens.
  audio  the pipelines have no audio mask and pass one audio timestep per batch, but the transformer accepts
         `audio_timestep` of shape (batch, audio_tokens). A forward pre-hook makes it `t * (1 - audio_mask)`, and
         prepare_audio_latents writes the tail. Nothing blends the audio x0, so the `audio_scheduler` component (a
         PinnedScheduler) writes the pinned tokens back after every step.
  both   PinnedScheduler also keeps each pass's final tokens. Later shots pin those: the pipeline's own normalized,
         packed tokens, so nothing is decoded, re-encoded or re-normalized between shots.

The distilled two-stage recipe (half size, x2 latent upsampler, refine at full size; runtimes.LtxAdapter) pins in both
passes, each from the previous shot's latents of the same pass, so the refine cannot redraw the join.

Geometry, read from the loaded pipeline (these are LTX-2.5's): the video VAE is causal, 8x in time and 32x in space, so
n latent frames decode to 1 + 8(n - 1) frames. Audio is 16 kHz mel at hop 160, 4x in time: 25 latents per second. The
audio VAE is causal too (n latents decode to 4n - 3 mel frames), and the vocoder with bandwidth extension gives 480
samples per mel frame at 48 kHz. A 2 s shot at 24 fps is 49 frames, 7 latent frames, 51 audio latents, 96,480 samples.

Backends:
  real  the worker's loader (weights at --models-dir) on a GPU
  tiny  the same diffusers classes and extension code with tiny random weights and LTX-2.5's geometry, on the CPU: proves
        the integration with diffusers (shapes, hooks, both passes), not the pictures
  fake  plain torch with the same geometry and a stand-in model that continues whatever clean context it is shown: proves
        the tail, pin, trim and stitch arithmetic end to end in seconds

README.md beside this file has the GPU commands and what to look at.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

JOINS = ("fresh", "continue", "cut")
ANCHORS = ("first", "previous")
# A fade in and out this long where a join's sound cannot run through (fresh, or an anchored pin): no click, no gap.
DECLICK_S = 0.005


class StoryboardError(ValueError):
    """The storyboard or the join settings cannot be rendered as asked."""


def write_json(path: Path, data) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)


def stable_seed(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:4], "big")


# ------------------------------------------------------------------ geometry (plain data)


@dataclass(frozen=True)
class Geometry:
    """Where latents sit in time. The defaults are LTX-2.5's; `from_pipeline` reads a loaded pipeline."""

    fps: float = 24.0
    temporal_ratio: int = 8  # video VAE: frames per latent frame after the first (the first latent frame is one frame)
    spatial_ratio: int = 32
    mel_sample_rate: int = 16000
    mel_hop: int = 160
    audio_ratio: int = 4  # audio VAE: mel frames per latent after the first
    sample_rate: int = 48000  # the vocoder's output

    @classmethod
    def from_pipeline(cls, pipeline: Any, fps: float) -> Geometry:
        config = getattr(getattr(pipeline, "vocoder", None), "config", None)
        return cls(
            fps=float(fps),
            temporal_ratio=int(pipeline.vae_temporal_compression_ratio),
            spatial_ratio=int(pipeline.vae_spatial_compression_ratio),
            mel_sample_rate=int(pipeline.audio_sampling_rate),
            mel_hop=int(pipeline.audio_hop_length),
            audio_ratio=int(pipeline.audio_vae_temporal_compression_ratio),
            sample_rate=int(getattr(config, "output_sampling_rate", None) or 48000),
        )

    @property
    def audio_latents_per_second(self) -> float:
        return self.mel_sample_rate / self.mel_hop / float(self.audio_ratio)

    @property
    def samples_per_mel(self) -> Fraction:
        return Fraction(self.mel_hop * self.sample_rate, self.mel_sample_rate)

    @property
    def samples_per_frame(self) -> Fraction:
        return Fraction(self.sample_rate) / Fraction(self.fps).limit_denominator(1001)

    def latent_frames(self, frames: int) -> int:
        return (frames - 1) // self.temporal_ratio + 1

    def pixel_frames(self, latent_frames: int) -> int:
        """Frames `latent_frames` decode to when they start a clip: the causal first one is a single frame."""
        return 1 + self.temporal_ratio * (latent_frames - 1) if latent_frames > 0 else 0

    def audio_latents(self, frames: int) -> int:
        # The pipelines' own arithmetic, float then round, so the count is always theirs.
        return round(frames / float(self.fps) * self.audio_latents_per_second)

    def mel_frames(self, audio_latents: int) -> int:
        return self.audio_ratio * audio_latents - (self.audio_ratio - 1) if audio_latents > 0 else 0

    def audio_samples(self, audio_latents: int) -> int:
        return round(self.mel_frames(audio_latents) * self.samples_per_mel)

    def to_dict(self) -> dict:
        return {
            "fps": self.fps, "video_temporal_ratio": self.temporal_ratio, "video_spatial_ratio": self.spatial_ratio,
            "mel_sample_rate": self.mel_sample_rate, "mel_hop": self.mel_hop, "audio_temporal_ratio": self.audio_ratio,
            "audio_latents_per_second": self.audio_latents_per_second, "samples_per_mel": float(self.samples_per_mel),
            "sample_rate": self.sample_rate, "samples_per_frame": float(self.samples_per_frame),
        }


# ------------------------------------------------------------------ storyboard (plain data)


@dataclass
class Shot:
    index: int
    prompt: str
    duration_s: float
    join: str = "fresh"


def load_storyboard(path: Path) -> tuple[str, list[Shot]]:
    """{"name": ..., "shots": [{"prompt", "duration_s", "join"}, ...]} or the bare list. A later shot's join defaults to
    continue; the first shot has nothing before it, so it is fresh."""
    data = json.loads(Path(path).read_text())
    items = data.get("shots") if isinstance(data, dict) else data
    if not isinstance(items, list) or not items:
        raise StoryboardError(f"{path}: expected a non-empty list of shots")
    shots = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not str(item.get("prompt", "")).strip():
            raise StoryboardError(f"{path}: shot {index + 1} needs a prompt")
        join = item.get("join", "fresh" if index == 0 else "continue")
        if join not in JOINS:
            raise StoryboardError(f"{path}: shot {index + 1} has join {join!r}; use one of {', '.join(JOINS)}")
        if index == 0 and join != "fresh":
            raise StoryboardError(f"{path}: shot 1 has nothing before it to {join}; its join must be fresh")
        try:
            duration = float(item["duration_s"])
        except (KeyError, TypeError, ValueError):
            raise StoryboardError(f"{path}: shot {index + 1} needs a numeric duration_s") from None
        shots.append(Shot(index=index, prompt=str(item["prompt"]).strip(), duration_s=duration, join=join))
    name = data.get("name") if isinstance(data, dict) else None
    return str(name or Path(path).stem), shots


# ------------------------------------------------------------------ the join plan (plain data)


@dataclass
class Join:
    """How one shot attaches to the shots before it, and what of it the stitched video keeps. Counts are the shot's own;
    `video_start` and `audio_start` are positions in the stitched output."""

    index: int
    join: str
    frames: int
    latent_frames: int
    audio_latents: int
    video_pin: int = 0  # latent frames of video_source's tail held at the head
    video_source: int | None = None
    audio_pin: int = 0  # audio latents of audio_source's tail held at the head
    audio_source: int | None = None
    audio_continuous: bool = False  # the audio pin is the previous shot's own tail: the sound runs straight through
    video_trim: int = 0  # decoded frames dropped from the head
    audio_trim: int = 0  # decoded samples dropped from the head
    video_start: int = 0
    audio_start: int = 0
    decoded_frames: int | None = None
    decoded_samples: int | None = None
    audio_keep: int | None = None  # samples kept from audio_trim on (past the decoded end: silence); set by the next join
    video_zero: Fraction = Fraction(0)  # where this shot's own frame 0 falls in the output, in samples
    sync_error_samples: float = 0.0  # this shot's audio clock start minus its video clock start, in the output
    notes: list[str] = field(default_factory=list)

    @property
    def kept_frames(self) -> int | None:
        return None if self.decoded_frames is None else self.decoded_frames - self.video_trim

    @property
    def audio_pad(self) -> int | None:
        """Silence appended after the decoded audio (negative: samples cut from its end)."""
        if self.audio_keep is None or self.decoded_samples is None:
            return None
        return self.audio_keep - (self.decoded_samples - self.audio_trim)

    def to_dict(self, geometry: Geometry) -> dict:
        shot = lambda i: None if i is None else i + 1  # noqa: E731 - shot numbers in results are 1-based
        return {
            "shot": self.index + 1, "join": self.join, "frames": self.frames, "latent_frames": self.latent_frames,
            "audio_latents": self.audio_latents, "video_pin_latent_frames": self.video_pin, "video_source_shot": shot(self.video_source),
            "audio_pin_latents": self.audio_pin, "audio_source_shot": shot(self.audio_source), "audio_continuous": self.audio_continuous,
            "video_trim_frames": self.video_trim, "audio_trim_samples": self.audio_trim, "kept_frames": self.kept_frames,
            "kept_audio_samples": self.audio_keep, "audio_end_pad_samples": self.audio_pad, "video_start_frame": self.video_start,
            "audio_start_sample": self.audio_start, "decoded_frames": self.decoded_frames, "decoded_audio_samples": self.decoded_samples,
            "predicted_audio_samples": geometry.audio_samples(self.audio_latents),
            "sync_error_ms": round(1000.0 * self.sync_error_samples / geometry.sample_rate, 3), "notes": self.notes,
        }


class Timeline:
    """Plans every join from what the shots before it actually decoded to.

    Video: a continue or cut join drops the frames its first `overlap` latent frames decode to, 1 + 8(overlap - 1). For
    continue those are the pinned ones, so the first kept frame is the one right after the previous shot's last. Cut drops
    the same span: those frames were drawn under the previous shot's replayed sound.

    Audio: the pinned latents decode to 4k - 3 mel frames, exactly what is trimmed, so a shot whose pin is the previous
    shot's own tail continues its sound sample for sample. Only the count k is a choice. A tail proportional to the
    overlap (JoyLTX25: round(audio_latents * overlap / latent_frames)) ignores that both VAEs are causal: for 2 s shots at
    24 fps it replays about 140 ms of sound and shifts the pinned sound 170 ms against the pinned picture. Here k is the
    count that best lines the shot's audio clock up with its video clock in the output, given every earlier choice, so
    the error stays within half an audio latent (20 ms) and never adds up. Where the sound cannot run through (a fresh
    shot, or a pin anchored to an earlier shot) the previous shot's audio is padded with silence or cut at its end so the
    next shot starts in sync.
    """

    def __init__(self, geometry: Geometry, overlap: int, anchor: str = "first"):
        if anchor not in ANCHORS:
            raise StoryboardError(f"audio anchor must be one of {', '.join(ANCHORS)}, not {anchor!r}")
        if overlap < 1:
            raise StoryboardError("overlap must be at least one latent frame")
        self.geometry, self.overlap, self.anchor = geometry, overlap, anchor
        self.joins: list[Join] = []
        self.total_frames: int | None = None
        self.total_samples: int | None = None

    def chain_start(self, index: int) -> int:
        """The shot that began the current run of joined shots: the latest fresh one before `index`."""
        return max(j.index for j in self.joins[:index] if j.join == "fresh")

    def plan(self, shot: Shot, frames: int) -> Join:
        g, index = self.geometry, len(self.joins)
        if shot.join not in JOINS:
            raise StoryboardError(f"shot {index + 1}: unknown join {shot.join!r}")
        join = Join(index=index, join=shot.join, frames=frames, latent_frames=g.latent_frames(frames), audio_latents=g.audio_latents(frames))
        if index == 0:
            if shot.join != "fresh":
                raise StoryboardError("shot 1 has nothing before it to join; its join must be fresh")
            self.joins.append(join)
            return join
        prev = self.joins[-1]
        if prev.decoded_frames is None or prev.decoded_samples is None:
            raise RuntimeError(f"shot {index + 1} is planned from what shot {index} decoded to; render shot {index} first")
        join.video_start = prev.video_start + prev.kept_frames
        if shot.join != "fresh":
            if not 1 <= self.overlap < min(join.latent_frames, prev.latent_frames):
                raise StoryboardError(
                    f"shot {index + 1}: an overlap of {self.overlap} latent frames needs shots of at least {self.overlap + 1} latent "
                    f"frames ({g.pixel_frames(self.overlap + 1)} frames); shots {index} and {index + 1} have {prev.latent_frames} and "
                    f"{join.latent_frames}"
                )
            join.video_trim = g.pixel_frames(self.overlap)
        if shot.join == "continue":
            join.video_pin, join.video_source = self.overlap, index - 1
        join.video_zero = (join.video_start - join.video_trim) * g.samples_per_frame
        if shot.join != "fresh":
            source = index - 1 if self.anchor == "previous" else self.chain_start(index)
            join.audio_source, join.audio_continuous = source, source == index - 1
            limit = min(self.joins[source].audio_latents, join.audio_latents) - 1
            if join.audio_continuous:
                start = prev.audio_start + (prev.decoded_samples - prev.audio_trim)
                join.audio_pin = self._audio_pin(start - join.video_zero, limit, index)
                miss = abs(start - g.audio_samples(join.audio_pin) - join.video_zero)
                if miss > g.audio_ratio * g.samples_per_mel / 2:
                    # Even the shortest pin starts the sound too early: the previous shot's audio falls short of its
                    # picture by more than this overlap trims (a 1-latent-frame overlap at 50 fps). Running it through
                    # would drift further at every join, so this join pads into sync instead.
                    join.audio_continuous = False
                    join.notes.append(
                        f"an overlap of {self.overlap} trims {join.video_trim} frames, less than shot {index}'s audio falls short of its "
                        f"picture: its sound is padded into sync instead of running through ({1000 * float(miss) / g.sample_rate:.0f} ms off otherwise)"
                    )
            if not join.audio_continuous:
                # The pinned sound spans the time of the trimmed frames.
                join.audio_pin = self._audio_pin(join.video_trim * g.samples_per_frame, limit, index)
            join.audio_trim = g.audio_samples(join.audio_pin)
        self.joins.append(join)
        self._place_audio(join)
        return join

    def _audio_pin(self, target: Fraction, limit: int, index: int) -> int:
        """The audio latent count whose decoded span is closest to `target` samples."""
        g = self.geometry
        if limit < 1:
            raise StoryboardError(f"shot {index + 1}: too short to hold an audio pin")
        guess = round((target / g.samples_per_mel + (g.audio_ratio - 1)) / g.audio_ratio)
        candidates = {max(1, min(limit, guess + d)) for d in (-1, 0, 1)}
        return min(candidates, key=lambda k: (abs(g.audio_samples(k) - target), k))

    def _place_audio(self, join: Join) -> None:
        if join.index == 0:
            return
        prev = self.joins[join.index - 1]
        if join.audio_continuous:
            prev.audio_keep = prev.decoded_samples - prev.audio_trim  # all of it: this shot's first kept sample follows its last
            join.audio_start = prev.audio_start + prev.audio_keep
        else:
            join.audio_start = round(join.video_zero + join.audio_trim)
            prev.audio_keep = join.audio_start - prev.audio_start
        join.sync_error_samples = float(join.audio_start - join.audio_trim - join.video_zero)

    def rendered(self, index: int, frames: int, samples: int) -> Join:
        """Records what shot `index` decoded to. The plan assumed LTX-2.5's causal audio decoder; if the samples differ,
        the trim becomes the same share of what did come back and the difference is noted."""
        g, join = self.geometry, self.joins[index]
        join.decoded_frames, join.decoded_samples = int(frames), int(samples)
        if frames != join.frames:
            join.notes.append(f"decoded {frames} frames, planned {join.frames}")
        if frames <= join.video_trim:
            raise RuntimeError(f"shot {index + 1} decoded {frames} frames, no more than the {join.video_trim} its join trims")
        predicted = g.audio_samples(join.audio_latents)
        if samples != predicted:
            join.notes.append(f"decoded {samples} audio samples, the causal decoder rule predicts {predicted}")
            if join.audio_pin:
                join.audio_trim = round(samples * g.mel_frames(join.audio_pin) / g.mel_frames(join.audio_latents))
                self._place_audio(join)
        return join

    def finish(self) -> tuple[int, int]:
        """Closes the last shot's audio at the end of the video: (stitched frames, stitched samples)."""
        last = self.joins[-1]
        if last.decoded_frames is None:
            raise RuntimeError("finish() needs every shot rendered")
        self.total_frames = last.video_start + last.kept_frames
        self.total_samples = round(self.total_frames * self.geometry.samples_per_frame)
        last.audio_keep = self.total_samples - last.audio_start
        return self.total_frames, self.total_samples


def predicted_timeline(geometry: Geometry, shots: list[Shot], frames: list[int], overlap: int, anchor: str) -> Timeline:
    """The whole plan up front, assuming every shot decodes to what the geometry predicts."""
    timeline = Timeline(geometry, overlap, anchor)
    for shot, count in zip(shots, frames):
        join = timeline.plan(shot, count)
        timeline.rendered(join.index, count, geometry.audio_samples(join.audio_latents))
    timeline.finish()
    return timeline


def assemble_audio(joins: list[Join], audios: list, total_samples: int, fade_samples: int = 0):
    """The stitched track: each shot's kept samples at its audio_start, silence where a join pads. `audios` are
    (channels, samples) arrays. Where a join's sound does not run through, `fade_samples` ramps the sound out before it
    and in after it, so two unrelated waveforms do not click; a continuous join is never touched."""
    import numpy as np

    channels = max(a.shape[0] for a in audios)
    out = np.zeros((channels, total_samples), dtype=np.float32)
    for index, (join, audio) in enumerate(zip(joins, audios)):
        keep = max(0, join.audio_keep or 0)
        piece = audio[:, join.audio_trim : join.audio_trim + keep]
        if fade_samples and piece.shape[1]:
            n = min(fade_samples, piece.shape[1])
            ramp = (np.arange(1, n + 1, dtype=np.float32) / (n + 1))[None]
            if index > 0 and not join.audio_continuous:
                piece = piece.copy()
                piece[:, :n] *= ramp
            if index + 1 < len(joins) and not joins[index + 1].audio_continuous:
                piece = piece.copy()
                piece[:, -n:] *= ramp[:, ::-1]
        end = min(total_samples, join.audio_start + piece.shape[1])
        if end > join.audio_start:
            out[: piece.shape[0], join.audio_start : end] = piece[:, : end - join.audio_start]
    return out


def audio_array(audio: Any):
    """(channels, samples) float32 from what a pipeline returns: diffusers' vocoder gives a bfloat16 tensor on the GPU."""
    import numpy as np

    if hasattr(audio, "detach"):
        audio = audio.detach().to("cpu").float().numpy()
    array = np.asarray(audio, dtype=np.float32)
    while array.ndim > 2:
        array = array[0]
    if array.ndim == 1:
        array = array[None]
    if array.shape[0] > array.shape[1]:
        array = array.T
    return np.ascontiguousarray(array)


def frame_array(frames: Any):
    """(frames, height, width, 3) uint8 from PIL images or arrays."""
    import numpy as np

    if hasattr(frames, "ndim") and frames.ndim == 4 and frames.dtype == np.uint8:
        return frames
    return np.stack([np.asarray(f.convert("RGB") if hasattr(f, "convert") else f, dtype=np.uint8) for f in frames])


# ------------------------------------------------------------------ pins and tails (torch)


@dataclass
class Pins:
    """Tokens held at the head of one pass: [1, tokens, features], in the pipeline's normalized, packed space."""

    video: Any = None
    audio: Any = None


@dataclass
class Tail:
    """The end of one shot's latents after one pass, kept for later shots: the last `overlap` video latent frames, and all
    of the audio (each join takes the count it planned)."""

    video: Any
    audio: Any


def pins_for(join: Join, tails: dict[int, dict[str, Tail]], stage: str) -> Pins:
    video = tails[join.video_source][stage].video if join.video_pin else None
    audio = tails[join.audio_source][stage].audio[:, -join.audio_pin :] if join.audio_pin else None
    return Pins(video=video, audio=audio)


def pinned_timesteps(timestep: Any, tokens: int, head: int):
    """Per-token timesteps for one modality: 0 on the pinned head, so the transformer reads it as clean context."""
    import torch

    mask = torch.zeros(tokens, device=timestep.device, dtype=timestep.dtype)
    mask[:head] = 1
    return timestep.reshape(-1, 1) * (1 - mask)[None]


def take_tail(video_tokens: Any, audio_tokens: Any, latent_frames: int, tokens_per_frame: int, overlap: int) -> Tail:
    if video_tokens.shape[1] != latent_frames * tokens_per_frame:
        raise RuntimeError(
            f"the final video latents have {video_tokens.shape[1]} tokens, not {latent_frames} latent frames x {tokens_per_frame}: "
            "the pipeline's patching is not what this script assumes"
        )
    keep = min(overlap, latent_frames)
    video = video_tokens[:, (latent_frames - keep) * tokens_per_frame :].detach().to("cpu", copy=True)
    return Tail(video=video, audio=audio_tokens.detach().to("cpu", copy=True))


def head_matches(tokens: Any, head: Any) -> bool | None:
    import torch

    if head is None:
        return None
    return bool(torch.equal(tokens[:, : head.shape[1]].to("cpu"), head.to("cpu", tokens.dtype)))


def clean_head(timestep: Any, head: Any) -> bool | None:
    """Whether per-token timesteps show the transformer the pinned head at t = 0 and everything after it as noise."""
    if head is None:
        return None
    if timestep is None or timestep.ndim != 2:
        return False
    n = head.shape[1]
    return bool((timestep[:, :n] == 0).all()) and bool((timestep[:, n:] > 0).all())


_EXTEND_CLASSES: tuple | None = None


def extend_classes() -> tuple:
    """PinnedScheduler and LTX2ExtendPipeline, defined on first use so the plain-data parts import without diffusers."""
    global _EXTEND_CLASSES
    if _EXTEND_CLASSES is not None:
        return _EXTEND_CLASSES
    from diffusers import FlowMatchEulerDiscreteScheduler, LTX2ConditionPipeline
    from diffusers.schedulers.scheduling_flow_match_euler_discrete import FlowMatchEulerDiscreteSchedulerOutput

    class PinnedScheduler(FlowMatchEulerDiscreteScheduler):
        """The Euler step, then the pinned head written back exactly. Keeps the pass's final tokens in `final`."""

        pin = None
        final = None

        def start(self, pin: Any) -> None:
            self.pin, self.final = pin, None

        def step(self, model_output, timestep, sample, *args, return_dict: bool = True, **kwargs):
            prev = super().step(model_output, timestep, sample, *args, return_dict=False, **kwargs)[0]
            if self.pin is not None:
                prev[:, : self.pin.shape[1]] = self.pin.to(prev.device, prev.dtype)
            if self.step_index is not None and self.step_index >= len(self.timesteps):
                self.final = prev.detach().clone()
            return FlowMatchEulerDiscreteSchedulerOutput(prev_sample=prev) if return_dict else (prev,)

    class LTX2ExtendPipeline(LTX2ConditionPipeline):
        """LTX2ConditionPipeline with `pins` written at the head, where it would put an encoded first frame."""

        pins: Pins | None = None

        def prepare_latents(self, *args, **kwargs):
            latents, mask, clean, keyframe_coords = super().prepare_latents(*args, **kwargs)
            head = getattr(self.pins, "video", None)
            if head is not None:
                n = head.shape[1]
                head = head.to(latents.device, latents.dtype)
                # mask 1: the loop's timestep * (1 - mask) shows these to the transformer at t = 0, and its x0 blend keeps
                # them, so the Euler step moves them by exactly nothing.
                latents[:, :n] = head
                clean[:, :n] = head
                mask[:, :n] = 1.0
            return latents, mask, clean, keyframe_coords

        def prepare_audio_latents(self, *args, **kwargs):
            latents = super().prepare_audio_latents(*args, **kwargs)
            head = getattr(self.pins, "audio", None)
            if head is not None:
                latents[:, : head.shape[1]] = head.to(latents.device, latents.dtype)
            return latents

    _EXTEND_CLASSES = (PinnedScheduler, LTX2ExtendPipeline)
    return _EXTEND_CLASSES


# ------------------------------------------------------------------ renderers


@dataclass
class Rendered:
    frames: Any  # (frames, height, width, 3) uint8
    audio: Any  # (channels, samples) float32
    sample_rate: int
    tails: dict[str, Tail]
    pins_exact: dict[str, bool | None]  # per pass: the pinned tokens came out of denoising bit-identical
    timings: dict[str, float]
    peak_gpu_gib: dict[str, float] | None = None
    # per pass and modality: the transformer's first call saw the pinned head at timestep 0 and the rest above it
    seen_clean: dict[str, dict[str, bool | None]] = field(default_factory=dict)
    debug: dict[str, Any] = field(default_factory=dict)


def _clock(cuda: bool) -> float:
    if cuda:
        import torch

        torch.cuda.synchronize()
    return time.perf_counter()


class ExtendRenderer:
    """One shot at a time on the pipelines the worker's loader builds, through LTX2ExtendPipeline sharing their modules."""

    backend = "real"

    def __init__(self, pipelines: dict[str, Any], device: str, overlap: int):
        Scheduler, Pipeline = extend_classes()
        source = pipelines.get("condition") or pipelines["text"]
        components = dict(source.components)
        # Its own schedulers, so the pins never touch the worker's pipelines. from_config keeps the recipe's schedule
        # (build_ltx_pipelines gives the pro model dynamic shifting).
        components["scheduler"] = Scheduler.from_config(source.scheduler.config)
        components["audio_scheduler"] = Scheduler.from_config(source.scheduler.config)
        self.pipeline = Pipeline(**components)
        self.upsample = pipelines.get("upsample")
        self.device = device
        self.overlap = overlap

    def geometry(self, fps: float) -> Geometry:
        return Geometry.from_pipeline(self.pipeline, fps)

    def stages(self, call: dict[str, Any]) -> tuple[str, ...]:
        return ("half", "full") if call.get("second_stage_sigmas") and self.upsample is not None else ("full",)

    def prepare_call(self, call: dict[str, Any]) -> dict[str, Any]:
        return call

    def render(self, call: dict[str, Any], pins: dict[str, Pins]) -> Rendered:
        import torch
        from kuno_worker.backends.resident import PipelineResult
        from kuno_worker.backends.runtimes import _audio_rate

        call = dict(call)
        for key in ("pipeline", "kuno_trajectory_tap", "conditions", "generate_audio"):  # as runtimes.LtxAdapter does
            call.pop(key, None)
        generator = torch.Generator(device=self.device).manual_seed(int(call.pop("seed")))
        second = call.pop("second_stage_sigmas", None)
        call = self.prepare_call(call)
        cuda = str(self.device).startswith("cuda") and torch.cuda.is_available()
        if cuda:
            torch.cuda.reset_peak_memory_stats()
        timings: dict[str, float] = {}
        tails: dict[str, Tail] = {}
        exact: dict[str, bool | None] = {}
        seen: dict[str, dict[str, bool | None]] = {}
        record = (timings, tails, exact, seen, cuda)
        width, height = call.pop("width"), call.pop("height")
        if second and self.upsample is not None:
            # runtimes.LtxAdapter._two_stage, with the pins held in both passes.
            latents, audio_latents = self._pass(
                "half", call, pins, generator, record, width=width // 2, height=height // 2, output_type="latent", return_dict=False,
            )
            started = _clock(cuda)
            upsampled = self.upsample(latents=latents, output_type="latent", return_dict=False)[0]
            timings["upsample_s"] = round(_clock(cuda) - started, 3)
            result = self._pass(
                "full", {**call, "sigmas": second}, pins, generator, record, width=width, height=height,
                latents=upsampled, audio_latents=audio_latents, noise_scale=second[0],
            )
        else:
            result = self._pass("full", call, pins, generator, record, width=width, height=height)
        started = time.perf_counter()
        normalized = PipelineResult.from_pipeline(
            {"videos": result.frames, "audio": result.audio, "sampling_rate": _audio_rate(self.pipeline, result)}
        )
        frames, audio = frame_array(normalized.frames), audio_array(normalized.audio)
        timings["to_arrays_s"] = round(time.perf_counter() - started, 3)
        peak = None
        if cuda:
            peak = {
                "allocated": round(torch.cuda.max_memory_allocated() / 2**30, 2),
                "reserved": round(torch.cuda.max_memory_reserved() / 2**30, 2),
            }
        return Rendered(frames, audio, normalized.sample_rate, tails, exact, timings, peak, seen)

    def _pass(self, stage, call, pins, generator, record, **extra) -> Any:
        timings, tails, exact, seen, cuda = record
        pipeline = self.pipeline
        pin = pins.get(stage) or Pins()
        pin = Pins(*(None if t is None else t.to(self.device) for t in (pin.video, pin.audio)))  # once, not every step
        pipeline.pins = pin
        pipeline.scheduler.start(pin.video)
        pipeline.audio_scheduler.start(pin.audio)
        seen[stage] = {}

        def timesteps(module, args, kwargs):
            audio_t, audio_tokens = kwargs.get("audio_timestep"), kwargs.get("audio_hidden_states")
            if pin.audio is not None and audio_t is not None and audio_t.ndim == 1 and audio_tokens is not None:
                # One timestep per batch row becomes one per audio token, 0 on the pinned head. audio_sigma (prompt
                # AdaLN, cross-modal modulation) stays per row, as it does for video.
                kwargs["audio_timestep"] = audio_t = pinned_timesteps(audio_t, audio_tokens.shape[1], pin.audio.shape[1])
            if not seen[stage]:  # the pass's first transformer call: what the model is actually shown
                seen[stage] = {"video": clean_head(kwargs.get("timestep"), pin.video), "audio": clean_head(audio_t, pin.audio)}
            return args, kwargs

        hook = pipeline.transformer.register_forward_pre_hook(timesteps, with_kwargs=True)
        started = _clock(cuda)
        try:
            output = pipeline(generator=generator, **call, **extra)
        finally:
            hook.remove()
            pipeline.pins = None
        timings[f"{stage}_s"] = round(_clock(cuda) - started, 3)
        video, audio = pipeline.scheduler.final, pipeline.audio_scheduler.final
        pipeline.scheduler.start(None)
        pipeline.audio_scheduler.start(None)
        if video is None or audio is None:
            raise RuntimeError(f"the {stage} pass finished without a final scheduler step")
        exact[stage] = _all_exact(head_matches(video, pin.video), head_matches(audio, pin.audio))
        p = int(pipeline.transformer_spatial_patch_size)
        tokens_per_frame = (extra["height"] // pipeline.vae_spatial_compression_ratio // p) * (extra["width"] // pipeline.vae_spatial_compression_ratio // p)
        latent_frames = (call["num_frames"] - 1) // pipeline.vae_temporal_compression_ratio + 1
        tails[stage] = take_tail(video, audio, latent_frames, tokens_per_frame, self.overlap)
        return output


def _all_exact(*checks: bool | None) -> bool | None:
    present = [c for c in checks if c is not None]
    return all(present) if present else None


def tiny_pipelines(seed: int = 0) -> dict[str, Any]:
    """LTX2ConditionPipeline and the latent upsampler with tiny random weights, LTX-2.5's geometry (32x/8x video VAE, 16 kHz
    mel at hop 160, 4x audio VAE, 48 kHz vocoder with bandwidth extension) and 128-feature tokens for both modalities. No
    text encoder: TinyRenderer passes prompt embeddings."""
    import torch
    from diffusers import (
        AutoencoderKLLTX2Audio,
        AutoencoderKLLTX2Video,
        FlowMatchEulerDiscreteScheduler,
        LTX2ConditionPipeline,
        LTX2LatentUpsamplePipeline,
        LTX2VideoTransformer3DModel,
    )
    from diffusers.pipelines.ltx2 import LTX2TextConnectors
    from diffusers.pipelines.ltx2.latent_upsampler import LTX2LatentUpsamplerModel
    from diffusers.pipelines.ltx2.vocoder import LTX2VocoderWithBWE

    torch.manual_seed(seed)
    text = TinyRenderer.text_channels
    vae = AutoencoderKLLTX2Video(
        latent_channels=128, block_out_channels=(8, 16, 32, 64), decoder_block_out_channels=(8, 16, 32),
        layers_per_block=(1, 1, 1, 1, 1), decoder_layers_per_block=(1, 1, 1, 1), patch_size=4, patch_size_t=1,
        spatial_compression_ratio=32, temporal_compression_ratio=8,
    )
    audio_vae = AutoencoderKLLTX2Audio(base_channels=128, ch_mult=(1,), num_res_blocks=1, latent_channels=8, mel_bins=64)
    # Non-trivial normalization, so a token taken or written in the wrong space would show.
    for module in (vae, audio_vae):
        module.latents_mean.copy_(torch.randn_like(module.latents_mean) * 0.1)
        module.latents_std.copy_(torch.rand_like(module.latents_std) + 0.5)
    vocoder = LTX2VocoderWithBWE(
        in_channels=128, hidden_channels=128, out_channels=2, resnet_kernel_sizes=[3], resnet_dilations=[[1]],
        bwe_in_channels=128, bwe_hidden_channels=64, bwe_out_channels=2, bwe_resnet_kernel_sizes=[3], bwe_resnet_dilations=[[1]],
    )
    connectors = LTX2TextConnectors(
        caption_channels=text, text_proj_in_factor=TinyRenderer.text_layers + 1, video_connector_num_attention_heads=2,
        video_connector_attention_head_dim=8, video_connector_num_layers=1, video_connector_num_learnable_registers=None,
        audio_connector_num_attention_heads=2, audio_connector_attention_head_dim=8, audio_connector_num_layers=1,
        audio_connector_num_learnable_registers=None, connector_rope_base_seq_len=32, rope_double_precision=False, rope_type="split",
    )
    transformer = LTX2VideoTransformer3DModel(
        in_channels=128, out_channels=128, num_attention_heads=2, attention_head_dim=8, cross_attention_dim=16,
        audio_in_channels=128, audio_out_channels=128, audio_num_attention_heads=2, audio_attention_head_dim=4,
        audio_cross_attention_dim=8, num_layers=2, caption_channels=text, rope_double_precision=False, rope_type="split",
        cross_attn_mod=True, audio_cross_attn_mod=True,  # the LTX-2.3+ branch: prompt AdaLN and 9 modulation parameters
    )
    condition = LTX2ConditionPipeline(
        scheduler=FlowMatchEulerDiscreteScheduler(), vae=vae, audio_vae=audio_vae, text_encoder=None, tokenizer=None,
        connectors=connectors, transformer=transformer, vocoder=vocoder,
    )
    upsampler = LTX2LatentUpsamplerModel(in_channels=128, mid_channels=32, num_blocks_per_stage=1)
    return {"condition": condition, "upsample": LTX2LatentUpsamplePipeline(vae=vae, latent_upsampler=upsampler)}


class TinyRenderer(ExtendRenderer):
    """ExtendRenderer on tiny_pipelines(), on the CPU. The pictures are noise; the shapes, hooks and passes are the real ones."""

    backend = "tiny"
    text_channels, text_layers, text_tokens = 16, 2, 8

    def __init__(self, overlap: int, seed: int = 0):
        super().__init__(tiny_pipelines(seed), device="cpu", overlap=overlap)
        self.pipeline.set_progress_bar_config(disable=True)

    def prepare_call(self, call: dict[str, Any]) -> dict[str, Any]:
        import torch

        prompt = call.pop("prompt")
        call.pop("negative_prompt", None)
        shape = (1, self.text_tokens, self.text_channels * (self.text_layers + 1))
        generator = torch.Generator("cpu").manual_seed(stable_seed(prompt))
        call["prompt_embeds"] = torch.randn(shape, generator=generator)
        call["prompt_attention_mask"] = torch.ones(1, self.text_tokens, dtype=torch.long)
        if call.get("guidance_scale", 3.0) > 1.0 or (call.get("audio_guidance_scale") or 0) > 1.0:
            call["negative_prompt_embeds"] = torch.zeros(shape)
            call["negative_prompt_attention_mask"] = torch.ones(1, self.text_tokens, dtype=torch.long)
        return call


class FakeRenderer:
    """LTX-2.5's latent geometry in plain torch on the CPU, with a stand-in for the transformer.

    Tokens are packed like the pipeline's ([1, latent frames x h x w, 128] and [1, audio latents, 128]) and denoised by the
    same Euler steps over the call's sigmas, with the same per-token timesteps, x0 blend and re-imposition as the real
    path, in both passes of the two-stage recipe. The stand-in writes a clock into channel 0: the time of each latent's
    last frame (or mel frame), counted on from the first latent of whatever head it is shown at timestep 0 (a fresh
    clock otherwise), plus a colour in channels 1-3. Decoding follows the causal VAEs, so the stitched video's clock
    advances by exactly one frame, and its audio clock by one sample, across every seam the plan says is continuous.
    """

    backend = "fake"
    features = 128

    def __init__(self, overlap: int, trace: bool = False):
        self.overlap = overlap
        self.trace = trace
        self.head_trace: list[tuple[str, Any, Any]] = []

    def geometry(self, fps: float) -> Geometry:
        return Geometry(fps=float(fps))

    def stages(self, call: dict[str, Any]) -> tuple[str, ...]:
        return ("half", "full") if call.get("second_stage_sigmas") else ("full",)

    def render(self, call: dict[str, Any], pins: dict[str, Pins]) -> Rendered:
        import numpy as np
        import torch

        g = self.geometry(call["frame_rate"])
        frames = int(call["num_frames"])
        latent_frames, audio_latents = g.latent_frames(frames), g.audio_latents(frames)
        generator = torch.Generator("cpu").manual_seed(int(call["seed"]))
        fresh = 5.0 * (int(call["seed"]) % 20 + 1)
        colour = torch.tensor([((stable_seed(call["prompt"]) >> s) % 200) / 100.0 - 1.0 for s in (0, 8, 16)])
        width, height, second = call["width"], call["height"], call.get("second_stage_sigmas")
        timings: dict[str, float] = {}
        tails: dict[str, Tail] = {}
        exact: dict[str, bool | None] = {}
        seen: dict[str, dict[str, bool | None]] = {}
        started = time.perf_counter()
        if second:
            h, w = height // 2 // g.spatial_ratio, width // 2 // g.spatial_ratio
            video, audio, seen["half"] = self._pass("half", g, pins, generator, call["sigmas"], latent_frames, h * w, audio_latents, fresh, colour)
            tails["half"] = take_tail(video, audio, latent_frames, h * w, self.overlap)
            half = pins.get("half") or Pins()
            exact["half"] = _all_exact(head_matches(video, half.video), head_matches(audio, half.audio))
            # The x2 latent upsampler, then the refine starts from it noised to its first sigma, as the pipeline does.
            grid = video.reshape(1, latent_frames, h, w, -1).repeat_interleave(2, dim=2).repeat_interleave(2, dim=3)
            init = (grid.reshape(1, latent_frames * 4 * h * w, -1), audio)
            video, audio, seen["full"] = self._pass("full", g, pins, generator, second, latent_frames, 4 * h * w, audio_latents, fresh, colour, init)
            tokens_per_frame = 4 * h * w
        else:
            steps = call.get("sigmas") or list(np.linspace(1.0, 1.0 / call["num_inference_steps"], call["num_inference_steps"]))
            tokens_per_frame = (height // g.spatial_ratio) * (width // g.spatial_ratio)
            video, audio, seen["full"] = self._pass("full", g, pins, generator, steps, latent_frames, tokens_per_frame, audio_latents, fresh, colour)
        full = pins.get("full") or Pins()
        exact["full"] = _all_exact(head_matches(video, full.video), head_matches(audio, full.audio))
        tails["full"] = take_tail(video, audio, latent_frames, tokens_per_frame, self.overlap)
        timings["generation_s"] = round(time.perf_counter() - started, 3)
        frame_pixels, frame_clock = self._decode_video(g, video, latent_frames, tokens_per_frame, frames, width, height)
        samples, sample_clock = self._decode_audio(g, audio)
        return Rendered(
            frame_pixels, samples, g.sample_rate, tails, exact, timings, None, seen,
            debug={"frame_clock": frame_clock, "sample_clock": sample_clock},
        )

    def _pass(self, stage, g, pins, generator, sigmas, latent_frames, tokens_per_frame, audio_latents, fresh, colour, init=None):
        import torch

        pin = pins.get(stage) or Pins()
        sigmas = [float(s) for s in sigmas] + [0.0]
        video = torch.randn(1, latent_frames * tokens_per_frame, self.features, generator=generator)
        audio = torch.randn(1, audio_latents, self.features, generator=generator)
        if init is not None:
            video = sigmas[0] * video + (1 - sigmas[0]) * init[0]
            audio = sigmas[0] * audio + (1 - sigmas[0]) * init[1]
        video_head = 0 if pin.video is None else pin.video.shape[1]
        audio_head = 0 if pin.audio is None else pin.audio.shape[1]
        clean = torch.zeros_like(video)
        mask = torch.zeros(1, video.shape[1], 1)
        if video_head:
            video[:, :video_head] = clean[:, :video_head] = pin.video
            mask[:, :video_head] = 1.0
        if audio_head:
            audio[:, :audio_head] = pin.audio
        seen: dict[str, bool | None] = {}
        for i in range(len(sigmas) - 1):
            sigma, following = sigmas[i], sigmas[i + 1]
            t = torch.tensor([sigma * 1000.0])
            t_video, t_audio = pinned_timesteps(t, video.shape[1], video_head), pinned_timesteps(t, audio.shape[1], audio_head)
            if i == 0:
                seen = {"video": clean_head(t_video, pin.video), "audio": clean_head(t_audio, pin.audio)}
            x0_video, x0_audio = self._model(g, video, audio, t_video, t_audio, latent_frames, tokens_per_frame, fresh, colour)
            x0_video = x0_video * (1 - mask) + clean * mask  # the pipeline's blend
            video = video + (following - sigma) * ((video - x0_video) / sigma)  # FlowMatchEulerDiscreteScheduler.step
            audio = audio + (following - sigma) * ((audio - x0_audio) / sigma)
            if video_head:
                video[:, :video_head] = pin.video  # PinnedScheduler.step
            if audio_head:
                audio[:, :audio_head] = pin.audio
            if self.trace:
                self.head_trace.append((stage, video[:, :video_head].clone(), audio[:, :audio_head].clone()))
        return video, audio, seen

    def _model(self, g, video, audio, t_video, t_audio, latent_frames, tokens_per_frame, fresh, colour):
        """x0 for every token. Context is only what arrives at timestep 0: a head re-imposed after the step but shown
        noised would not count."""
        import torch

        video_context = bool(t_video[0, :tokens_per_frame].eq(0).all())
        audio_context = bool(t_audio[0, :1].eq(0).all())
        v0 = float(video[0, 0, 0]) if video_context else float(audio[0, 0, 0]) if audio_context else fresh
        a0 = float(audio[0, 0, 0]) if audio_context else v0
        tint = video[0, 0, 1:4] if video_context else colour
        x0_video = torch.zeros_like(video)
        clock = v0 + g.temporal_ratio * torch.arange(latent_frames, dtype=torch.float64) / g.fps
        x0_video[0, :, 0] = clock.repeat_interleave(tokens_per_frame).to(video.dtype)
        x0_video[0, :, 1:4] = tint
        x0_audio = torch.zeros_like(audio)
        step = g.audio_ratio * g.mel_hop / g.mel_sample_rate
        x0_audio[0, :, 0] = (a0 + step * torch.arange(audio.shape[1], dtype=torch.float64)).to(audio.dtype)
        return x0_video, x0_audio

    @staticmethod
    def _decode_video(g, tokens, latent_frames, tokens_per_frame, frames, width, height):
        import numpy as np

        grid = tokens[0].reshape(latent_frames, tokens_per_frame, -1).double().mean(dim=1).numpy()
        clocks, tints = grid[:, 0], grid[:, 1:4]
        f = np.arange(frames)
        block = np.where(f == 0, 0, (f + g.temporal_ratio - 1) // g.temporal_ratio)
        share = np.where(f == 0, 1.0, (f - (g.temporal_ratio * block - (g.temporal_ratio - 1)) + 1) / g.temporal_ratio)
        before = clocks[np.maximum(block - 1, 0)]
        frame_clock = np.where(f == 0, clocks[0], before + share * (clocks[block] - before))
        pixels = np.empty((frames, height, width, 3), dtype=np.uint8)
        pixels[:] = np.clip(127.5 * (tints[block] + 1.0), 0, 255).astype(np.uint8)[:, None, None, :]
        bar = ((frame_clock * 0.25) % 1.0 * (width - 8)).astype(int)  # a bar crossing the frame every 4 s of clock
        for i, x in enumerate(bar):
            pixels[i, :, x : x + 8] = 255
        return pixels, frame_clock

    @staticmethod
    def _decode_audio(g, tokens):
        import numpy as np

        clocks = tokens[0, :, 0].double().numpy()
        spm = int(g.samples_per_mel)
        s = np.arange(g.audio_samples(len(clocks)))
        mel = s // spm
        block = np.where(mel == 0, 0, (mel + g.audio_ratio - 1) // g.audio_ratio)
        share = np.where(mel == 0, 1.0, (mel - (g.audio_ratio * block - (g.audio_ratio - 1)) + 1) / g.audio_ratio)
        before = clocks[np.maximum(block - 1, 0)]
        mel_clock = np.where(mel == 0, clocks[0], before + share * (clocks[block] - before))
        sample_clock = mel_clock + (s % spm) / g.sample_rate
        wave = (0.2 * np.sin(2 * np.pi * 220.0 * sample_clock)).astype(np.float32)
        return np.stack([wave, wave]), sample_clock


# ------------------------------------------------------------------ output: videos, seam strip, seam measures


class StitchWriter:
    """The stitched video, encoded as shots arrive (a long take does not fit in RAM as raw frames), with the audio muxed in
    at the end. Same H.264 settings as media_tools.encode_video."""

    def __init__(self, path: Path, fps: float, width: int, height: int, crf: int = 18):
        from kuno_worker.backends.media_tools import ffmpeg_exe

        self.path, self.fps, self.size = path, fps, (width, height)
        self.video_only = path.with_name(path.stem + ".video-only.mp4")
        self.log = path.with_name(path.stem + ".ffmpeg.log")
        self.frames = 0
        self._stderr = self.log.open("wb")
        self.process = subprocess.Popen(
            [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
             "-r", f"{fps:g}", "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p", str(self.video_only)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self._stderr,
        )

    def add(self, frames) -> None:
        import numpy as np

        for frame in frames:
            if frame.shape[:2] != (self.size[1], self.size[0]):
                raise RuntimeError(f"frame is {frame.shape[1]}x{frame.shape[0]}, the stitched video is {self.size[0]}x{self.size[1]}")
            self.process.stdin.write(np.ascontiguousarray(frame, dtype=np.uint8).tobytes())
            self.frames += 1

    def finish(self, audio, sample_rate: int) -> None:
        from kuno_worker.backends.media_tools import _write_wav, ffmpeg_exe

        self.process.stdin.close()
        code = self.process.wait(timeout=3600)
        self._stderr.close()
        if code != 0:
            raise RuntimeError(f"encoding the stitched video failed (ffmpeg exit {code}, {self.log})")
        wav = self.path.with_name(self.path.stem + ".wav")
        _write_wav(wav, audio, sample_rate)
        subprocess.run(
            [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(self.video_only), "-i", str(wav), "-map", "0:v:0",
             "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(self.path)],
            check=True, capture_output=True, timeout=3600,
        )
        self.video_only.unlink(missing_ok=True)
        if self.log.stat().st_size == 0:
            self.log.unlink()

    def abort(self) -> None:
        try:
            self.process.kill()
            self._stderr.close()
        except Exception:
            pass


def small(frame, width: int = 480):
    """A downscaled copy of one frame, for the seam strip and the seam measure."""
    from PIL import Image

    image = Image.fromarray(frame)
    return image.resize((width, max(1, round(image.height * width / image.width))), Image.BILINEAR)


def video_step_ratio(before: list, after) -> float | None:
    """How far the picture moves across the seam, in units of the ordinary frame-to-frame change just before it: about 1
    for a seamless join, far more for a cut."""
    import numpy as np

    grey = lambda image: np.asarray(image.convert("L"), dtype=np.float32)  # noqa: E731
    if len(before) < 2:
        return None
    steps = [float(np.abs(grey(a) - grey(b)).mean()) for a, b in zip(before, before[1:])]
    seam = float(np.abs(grey(before[-1]) - grey(after)).mean())
    return round(seam / max(float(np.median(steps)), 1e-3), 2)


def audio_jump_ratio(audio, at: int, sample_rate: int) -> float | None:
    """The largest sample-to-sample change within 10 ms of `at`, over the typical (median) largest change per 10 ms in
    the 200 ms before it: about 1 when the sound runs through, far more for a click or a hard cut."""
    import numpy as np

    near = sample_rate // 100
    if at - 20 * near < 0 or at + near > audio.shape[1]:
        return None
    seam = float(np.abs(np.diff(audio[:, at - near : at + near], axis=1)).max())
    windows = [float(np.abs(np.diff(audio[:, at - (k + 1) * near : at - k * near], axis=1)).max()) for k in range(1, 20)]
    return round(seam / max(float(np.median(windows)), 1e-6), 2)


def seam_strip(path: Path, rows: list[dict]) -> None:
    """One row per join: the last kept frame before it and the first kept frame after it, labelled."""
    from PIL import Image, ImageDraw

    if not rows:
        return
    tw, th = rows[0]["before"].size
    gap, band = 8, 22
    canvas = Image.new("RGB", (2 * tw + 3 * gap, len(rows) * (th + band + gap) + gap), (24, 24, 24))
    draw = ImageDraw.Draw(canvas)
    for n, row in enumerate(rows):
        top = gap + n * (th + band + gap)
        draw.text((gap, top + 4), row["label"], fill=(235, 235, 235))
        canvas.paste(row["before"], (gap, top + band))
        canvas.paste(row["after"], (2 * gap + tw, top + band))
    canvas.save(path)


# ------------------------------------------------------------------ run


def shot_calls(args, shots: list[Shot]) -> tuple[Any, list[dict[str, Any]]]:
    """The worker's own call for each shot (kuno_worker.backends.ltx_resident.build_call), seed + shot index."""
    from kuno_protocol.profiles import Mode, ParamError, load_profiles, validate_params
    from kuno_worker.backends.ltx_resident import build_call
    from kuno_worker.plan import build_task, example_task

    profile = load_profiles()[args.profile]
    calls = []
    with tempfile.TemporaryDirectory(prefix="kuno-extend-") as tmp:
        for shot in shots:
            params = example_task(
                profile, Mode.TEXT_TO_VIDEO, duration_s=shot.duration_s, resolution=args.resolution, aspect_ratio=args.aspect,
                fps=args.fps, audio=True,
            )
            try:
                validate_params(profile, params)
            except ParamError as exc:
                raise StoryboardError(f"shot {shot.index + 1}: {exc}") from None
            call = build_call(build_task(profile, params, Path(tmp), seed=args.seed + shot.index, prompt=shot.prompt))
            if args.size:
                call["width"], call["height"] = args.size
            calls.append(call)
    return profile, calls


def parse_size(text: str) -> tuple[int, int]:
    try:
        width, height = (int(v) for v in text.lower().split("x"))
    except ValueError:
        raise argparse.ArgumentTypeError(f"--size takes WIDTHxHEIGHT, not {text!r}") from None
    if width % 64 or height % 64:
        raise argparse.ArgumentTypeError("--size must be multiples of 64 (the half-size pass is 32x-compressed)")
    return width, height


def make_renderer(args) -> tuple[Any, float | None]:
    if args.backend == "fake":
        return FakeRenderer(args.overlap), None
    if args.backend == "tiny":
        return TinyRenderer(args.overlap, seed=args.seed), None
    from kuno_protocol.profiles import load_profiles
    from kuno_worker.backends.runtimes import ltx_loader

    # No hardware class and no digest: the loader checks file sizes instead of hashing 80 GB, as a performance-mode worker.
    loader = ltx_loader(Path(args.models_dir), device="cuda", offload=args.offload, weights_verify=args.weights_verify)
    started = time.perf_counter()
    adapter = loader(load_profiles()[args.profile])
    load_s = round(time.perf_counter() - started, 1)
    renderer = ExtendRenderer(adapter.pipelines, device="cuda", overlap=args.overlap)
    renderer.load_plan = getattr(adapter, "load_plan", None)
    if args.vae_tiling:
        renderer.pipeline.vae.enable_tiling()
    return renderer, load_s


def environment() -> dict[str, Any]:
    info: dict[str, Any] = {"python": sys.version.split()[0], "image": os.environ.get("KUNO_EXTEND_IMAGE")}
    try:
        import torch

        info["torch"] = torch.__version__
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            info["gpu"] = props.name
            info["gpu_memory_gib"] = round(props.total_memory / 2**30, 1)
    except ImportError:
        pass
    try:
        import diffusers

        info["diffusers"] = diffusers.__version__
    except ImportError:
        pass
    return info


def print_plan(timeline: Timeline) -> None:
    g = timeline.geometry
    print(f"{'shot':>4}  {'join':8} {'frames':>6} {'lat':>3} {'aud':>3}  {'v.pin':>5} {'a.pin':>9}  {'trim f':>6} {'trim smp':>8}  {'kept':>5}  {'sync ms':>7}")
    for j in timeline.joins:
        source = f"{j.audio_pin}<{j.audio_source + 1}" if j.audio_pin else "-"
        print(
            f"{j.index + 1:>4}  {j.join:8} {j.frames:>6} {j.latent_frames:>3} {j.audio_latents:>3}  {j.video_pin or '-':>5} {source:>9}  "
            f"{j.video_trim:>6} {j.audio_trim:>8}  {j.kept_frames:>5}  {1000 * j.sync_error_samples / g.sample_rate:>7.1f}"
        )
    if timeline.total_frames is not None:
        print(f"stitched: {timeline.total_frames} frames, {timeline.total_frames / g.fps:.3f} s, {timeline.total_samples} samples")


def cmd_run(args) -> int:
    run_started = time.perf_counter()
    name, shots = load_storyboard(Path(args.storyboard))
    out = Path(args.out or f"extend-out/{name}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}")
    (out / "shots").mkdir(parents=True, exist_ok=True)
    profile, calls = shot_calls(args, shots)
    fps = float(calls[0]["frame_rate"])
    width, height = calls[0]["width"], calls[0]["height"]
    results: dict[str, Any] = {
        "result": "fail", "failures": [], "warnings": [], "backend": args.backend,
        "model_exercised": args.backend == "real",
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "storyboard": {"file": str(args.storyboard), "name": name, "shots": len(shots)},
        "settings": {
            "profile": profile.id, "resolution": args.resolution, "aspect": args.aspect, "fps": fps, "width": width, "height": height,
            "seed": args.seed, "seeds": "seed + shot index (0-based)", "overlap_latent_frames": args.overlap,
            "audio_anchor": args.audio_anchor, "offload": args.offload, "vae_tiling": args.vae_tiling,
        },
        "mechanism": {
            "video": "LTX2ConditionPipeline conditioning_mask = 1 on the pinned tokens: per-token timestep 0 and x0 blend (native)",
            "audio": "per-token audio_timestep 0 via a transformer forward pre-hook, and re-imposed after every audio scheduler step",
            "tails": "each pass's final scheduler tokens (normalized, packed); both passes pinned from the same pass",
        },
    }
    # The plan up front, from LTX-2.5's default geometry (the real run replans each join from what actually decoded).
    planned = predicted_timeline(Geometry(fps=fps), shots, [c["num_frames"] for c in calls], args.overlap, args.audio_anchor)
    results["planned"] = [j.to_dict(planned.geometry) for j in planned.joins]
    results["planned_stitched"] = {"frames": planned.total_frames, "duration_s": round(planned.total_frames / fps, 3), "samples": planned.total_samples}
    print(f"{name}: {len(shots)} shots, {profile.id}, {width}x{height} at {fps:g} fps, overlap {args.overlap}, audio anchor {args.audio_anchor}")
    print_plan(planned)
    if args.plan_only:
        results["result"] = "planned"
        write_json(out / "results.json", results)
        print(f"plan only: {out / 'results.json'}")
        return 0

    def report(code: int) -> int:
        results["total_wall_s"] = round(time.perf_counter() - run_started, 1)
        results["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        write_json(out / "results.json", results)
        for failure in results["failures"]:
            print(f"FAIL  {failure}")
        for warning in results["warnings"]:
            print(f"WARN  {warning}")
        print(f"RESULT: {results['result'].upper()}  ({out / 'results.json'})")
        return code

    try:
        renderer, load_s = make_renderer(args)
    except Exception as exc:  # recorded with its traceback: a GPU failure must say more than its type
        traceback.print_exc()
        results["failures"].append(f"loading the pipelines failed: {type(exc).__name__}: {exc}")
        return report(1)
    results["load_s"] = load_s
    results["environment"] = environment()
    load_plan = getattr(renderer, "load_plan", None)
    if load_plan is not None:
        results["environment"]["load_plan"] = {"recipe": load_plan.recipe.id, "offload": load_plan.offload, "weights": load_plan.weights.mode}
    geometry = renderer.geometry(fps)
    results["geometry"] = geometry.to_dict()
    if geometry != planned.geometry:
        results["warnings"].append(f"the loaded pipeline's geometry {geometry.to_dict()} is not LTX-2.5's default; the plan above is stale")
    timeline = Timeline(geometry, args.overlap, args.audio_anchor)
    writer = StitchWriter(out / "stitched.mp4", fps, width, height)
    tails: dict[int, dict[str, Tail]] = {}
    audios, metrics, thumbs = [], [], []
    sample_rate = None

    def snapshot() -> None:
        results["shots"] = [
            {**j.to_dict(geometry), "prompt": shots[j.index].prompt, "duration_s": shots[j.index].duration_s,
             **(metrics[j.index] if j.index < len(metrics) else {})}
            for j in timeline.joins
        ]
        write_json(out / "results.json", results)

    def stitch() -> None:
        """The stitched video, seam measures and seam strip from every shot whose frames reached the writer."""
        total_frames, total_samples = timeline.finish()
        fade = round(sample_rate * DECLICK_S)
        audio = assemble_audio(timeline.joins, audios, total_samples, fade_samples=fade)
        writer.finish(audio, sample_rate)
        data = (out / "stitched.mp4").read_bytes()
        expected = sum(j.frames for j in timeline.joins) - sum(j.video_trim for j in timeline.joins)
        results["stitched"] = {
            "file": "stitched.mp4", "shots": len(timeline.joins), "frames": writer.frames, "expected_frames": expected,
            "duration_s": round(total_frames / fps, 3), "audio_samples": total_samples, "sample_rate": sample_rate,
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "declick_fade_samples_where_sound_does_not_run_through": fade,
        }
        if writer.frames != total_frames or writer.frames != expected:
            results["failures"].append(f"the stitched video has {writer.frames} frames; the plan says {total_frames}")
        seams, rows = [], []
        for join in timeline.joins[1:]:
            before, after = thumbs[join.index - 1], thumbs[join.index]
            seam = {
                "shot": join.index + 1, "join": join.join, "frame": join.video_start, "time_s": round(join.video_start / fps, 3),
                "video_step_ratio": video_step_ratio(before["tail"], after["head"]),
                "audio_sample": join.audio_start, "audio_jump_ratio": audio_jump_ratio(audio, join.audio_start, sample_rate),
                "audio_continuous": join.audio_continuous, "sync_error_ms": round(1000 * join.sync_error_samples / sample_rate, 2),
            }
            seams.append(seam)
            rows.append({
                "before": before["last"], "after": after["first"],
                "label": f"shot {join.index} -> {join.index + 1}  {join.join}  t={seam['time_s']}s  picture step x{seam['video_step_ratio']}  "
                         f"audio jump x{seam['audio_jump_ratio']}",
            })
        results["seams"] = seams
        seam_strip(out / "seams.png", rows)

    stitched = 0  # shots whose kept frames and audio are in the stitch
    try:
        for shot, call in zip(shots, calls):
            wall = time.perf_counter()
            join = timeline.plan(shot, call["num_frames"])
            stages = renderer.stages(call)
            pins = {stage: pins_for(join, tails, stage) for stage in stages}
            print(
                f"\nshot {shot.index + 1}/{len(shots)} [{shot.join}] {shot.duration_s:g}s, {call['num_frames']} frames, seed {call['seed']}: "
                f"video pin {join.video_pin or '-'}, audio pin {join.audio_pin or '-'}"
                + (f" from shot {join.audio_source + 1}" if join.audio_pin else ""), flush=True,
            )
            rendered = renderer.render(call, pins)
            timeline.rendered(join.index, len(rendered.frames), rendered.audio.shape[1])
            tails[join.index] = rendered.tails
            if sample_rate is None:
                sample_rate = rendered.sample_rate
            elif rendered.sample_rate != sample_rate:
                raise RuntimeError(f"shot {shot.index + 1} came back at {rendered.sample_rate} Hz, earlier shots at {sample_rate} Hz")
            started = time.perf_counter()
            shot_file = out / "shots" / f"{shot.index + 1:02d}-{shot.join}.mp4"
            if not args.no_shot_videos:
                from kuno_worker.backends.media_tools import encode_video

                shot_file.write_bytes(encode_video(rendered.frames, fps, rendered.audio, rendered.sample_rate))
            kept = rendered.frames[join.video_trim :]
            writer.add(kept)
            thumbs.append({"first": small(kept[0]), "last": small(kept[-1]), "tail": [small(f, 160) for f in kept[-4:]], "head": small(kept[0], 160)})
            audios.append(rendered.audio)
            stitched += 1
            for stage in stages:
                if (pins[stage].video is not None or pins[stage].audio is not None) and rendered.pins_exact.get(stage) is not True:
                    results["failures"].append(f"shot {shot.index + 1}: the pinned {stage}-pass tokens changed during denoising")
                for modality, head in (("video", pins[stage].video), ("audio", pins[stage].audio)):
                    if head is not None and (rendered.seen_clean.get(stage) or {}).get(modality) is not True:
                        results["failures"].append(
                            f"shot {shot.index + 1}: the transformer was not shown the pinned {modality} head at timestep 0 in the {stage} pass"
                        )
            metrics.append({
                "seed": call["seed"], "stages": list(stages), "pins_exact": rendered.pins_exact,
                "pinned_head_seen_at_t0": rendered.seen_clean,
                "wall_s": round(time.perf_counter() - wall, 2),
                "generation_s": round(sum(v for k, v in rendered.timings.items() if k != "to_arrays_s"), 2),
                "timings_s": rendered.timings, "encode_s": round(time.perf_counter() - started, 2),
                "peak_gpu_memory_gib": rendered.peak_gpu_gib, "file": None if args.no_shot_videos else str(shot_file.relative_to(out)),
            })
            print(
                f"  generated in {metrics[-1]['generation_s']}s ({rendered.timings}), wall {metrics[-1]['wall_s']}s, "
                f"peak GPU {rendered.peak_gpu_gib}, pins exact {rendered.pins_exact}, head seen at t=0 {rendered.seen_clean}", flush=True,
            )
            for note in join.notes:
                print(f"  note: {note}")
            snapshot()
        stitch()
    except Exception as exc:  # recorded with its traceback: a GPU failure must say more than its type
        traceback.print_exc()
        results["failures"].append(f"{type(exc).__name__}: {exc}")
        if stitched and "stitched" not in results:
            # Out of memory at shot 5 still leaves four shots and three seams worth looking at.
            del timeline.joins[stitched:]
            try:
                stitch()
                results["stitched"]["partial"] = True
                print(f"stitched the {stitched} shots rendered before the failure", flush=True)
            except Exception:
                traceback.print_exc()
                writer.abort()
        else:
            writer.abort()
    finally:
        snapshot()
    for j in timeline.joins:
        results["warnings"].extend(f"shot {j.index + 1}: {note}" for note in j.notes)
    results["result"] = "fail" if results["failures"] else "pass"
    print()
    if timeline.total_frames is not None:
        print_plan(timeline)
    return report(0 if results["result"] == "pass" else 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("storyboard", help="JSON: {name, shots: [{prompt, duration_s, join: fresh|continue|cut}]}")
    parser.add_argument("--profile", default="ltx-2.5-fast", help="ltx-2.5-fast (two-stage, distilled) or ltx-2.5-pro")
    parser.add_argument("--resolution", default="720p")
    parser.add_argument("--aspect", default="16:9")
    parser.add_argument("--fps", type=int, default=None, help="default: the profile's (24)")
    parser.add_argument("--seed", type=int, default=1234, help="shot N renders with seed + N - 1")
    parser.add_argument("--overlap", type=int, default=3, help="video latent frames pinned by a continue join (3 = 17 frames)")
    parser.add_argument("--audio-anchor", choices=ANCHORS, default="first",
                        help="first: every audio pin comes from the first shot of the run of joined shots (JoyLTX25 1.2.1, "
                             "against voice drift); previous: from the shot just before, so the sound runs straight through")
    parser.add_argument("--out", default=None, help="output directory (default ./extend-out/<name>-<UTC stamp>)")
    parser.add_argument("--backend", choices=("real", "tiny", "fake"), default="real")
    parser.add_argument("--fake", dest="backend", action="store_const", const="fake", help="same as --backend fake")
    parser.add_argument("--size", type=parse_size, default=None, help="WIDTHxHEIGHT instead of the profile's size (fake/tiny tests)")
    parser.add_argument("--models-dir", default=os.environ.get("KUNO_LTX_MODELS_DIR", "/models/ltx-2.5"))
    parser.add_argument("--offload", default=os.environ.get("KUNO_LTX_OFFLOAD", "auto"), choices=("auto", "none", "model", "group"))
    parser.add_argument("--weights-verify", default="full", choices=("full", "size"))
    parser.add_argument("--vae-tiling", action="store_true", help="decode in tiles (for GPU out-of-memory on long shots)")
    parser.add_argument("--plan-only", action="store_true", help="print and save the join plan; load nothing")
    parser.add_argument("--no-shot-videos", action="store_true", help="skip the per-shot MP4s")
    args = parser.parse_args(argv)
    try:
        return cmd_run(args)
    except StoryboardError as exc:
        print(f"ltx_extend: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
