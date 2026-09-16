"""ltx_extend.py's arithmetic, which the GPU run cannot afford to get wrong: which latents are pinned, how many frames and
samples each join trims, where every shot lands in the stitched video, and that pinned tokens never move.

The plain-data tests run anywhere. The torch tests (the fake and tiny backends, PinnedScheduler) skip without torch and
run inside the worker image; README.md has the command.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ltx_extend as lx  # noqa: E402

G24 = lx.Geometry(fps=24.0)


def ltx_frames(duration_s: float, fps: int) -> int:
    """kuno_protocol.profiles.ltx_num_frames, restated so these tests need nothing installed."""
    return 8 * max(1, round(duration_s * fps / 8)) + 1


def plan(joins: list[str], durations: list[float], fps: int = 24, overlap: int = 3, anchor: str = "previous") -> lx.Timeline:
    shots = [lx.Shot(index=i, prompt=f"shot {i}", duration_s=d, join=j) for i, (j, d) in enumerate(zip(joins, durations))]
    return lx.predicted_timeline(lx.Geometry(fps=float(fps)), shots, [ltx_frames(d, fps) for d in durations], overlap, anchor)


# ---------------------------------------------------------------- geometry


@pytest.mark.parametrize("fps", [24, 25, 48, 50])
@pytest.mark.parametrize("duration", [2, 3, 5, 8, 10])
def test_latent_frames_decode_back_to_the_clip(fps, duration):
    g = lx.Geometry(fps=float(fps))
    frames = ltx_frames(duration, fps)
    assert (frames - 1) % 8 == 0
    assert g.pixel_frames(g.latent_frames(frames)) == frames


def test_pinned_head_frame_counts():
    # The causal VAE's first latent frame is one frame, every later one eight.
    assert [G24.pixel_frames(k) for k in (1, 2, 3, 4, 6)] == [1, 9, 17, 25, 41]
    assert G24.latent_frames(49) == 7 and G24.latent_frames(121) == 16


def test_audio_geometry_matches_the_gpu_measurement():
    # LTX-2.5 on the RTX PRO 6000, 2026-09-15: 49 frames at 24 fps came back with 96,480 samples at 48 kHz.
    assert G24.audio_latents_per_second == 25.0
    assert G24.samples_per_mel == 480 and G24.samples_per_frame == 2000
    assert G24.audio_latents(49) == 51
    assert G24.mel_frames(51) == 201
    assert G24.audio_samples(51) == 96_480


@pytest.mark.parametrize("fps", [24, 25, 48, 50])
def test_audio_latent_count_is_the_pipelines_own_rounding(fps):
    g = lx.Geometry(fps=float(fps))
    for frames in range(9, 1000, 8):
        duration_s = frames / float(fps)  # pipeline_ltx2_condition.py: round(duration_s * audio_latents_per_second)
        assert g.audio_latents(frames) == round(duration_s * (16000 / 160 / float(4)))


# ---------------------------------------------------------------- tails and trims


def test_audio_tail_for_two_second_shots():
    timeline = plan(["fresh", "continue"], [2, 2])
    join = timeline.joins[1]
    assert (join.video_pin, join.video_trim) == (3, 17)
    assert join.audio_pin == 18 and join.audio_trim == 69 * 480 == 33_120
    assert join.audio_continuous and join.audio_source == 0
    assert join.sync_error_samples == -640  # -13.3 ms


def test_a_proportional_audio_tail_would_be_far_off():
    """JoyLTX25's round(audio_latents * overlap / latent_frames) against the count the timeline picks, for 2 s shots."""
    g, overlap, latents, audio = G24, 3, 7, 51
    proportional = round(audio * overlap / latents)
    assert proportional == 22
    video_head = g.pixel_frames(overlap) * g.samples_per_frame  # what the join trims from the picture
    shift_video = (g.pixel_frames(latents) - g.pixel_frames(overlap)) * g.samples_per_frame  # shot N+1's frame 0 in shot N
    for k, replayed_ms, skew_ms in ((proportional, 141.7, -173.3), (plan(["fresh", "continue"], [2, 2]).joins[1].audio_pin, None, -13.3)):
        shift_audio = g.audio_ratio * (audio - k) * g.samples_per_mel  # shot N+1's first sample in shot N
        assert round(float(shift_audio - shift_video) / 48, 1) == skew_ms
        if replayed_ms is not None:  # trimming only the picture's span would leave this much of shot N's sound in again
            assert round(float(g.audio_samples(k) - video_head) / 48, 1) == replayed_ms


def test_trims_and_kept_counts_are_exact():
    timeline = plan(["fresh", "continue", "continue", "continue"], [2, 2, 2, 2])
    frames = [j.frames for j in timeline.joins]
    assert frames == [49, 49, 49, 49]
    assert [j.video_trim for j in timeline.joins] == [0, 17, 17, 17]
    assert [j.kept_frames for j in timeline.joins] == [49, 32, 32, 32]
    assert [j.video_start for j in timeline.joins] == [0, 49, 81, 113]
    for before, after in zip(timeline.joins, timeline.joins[1:]):
        assert after.video_start == before.video_start + before.kept_frames
        assert after.audio_start == before.audio_start + before.audio_keep
        if after.audio_continuous:
            assert before.audio_keep == before.decoded_samples - before.audio_trim  # nothing padded, nothing cut
            assert before.audio_pad == 0
    assert timeline.total_frames == 145
    assert timeline.total_samples == 145 * 2000
    last = timeline.joins[-1]
    assert last.audio_start + last.audio_keep == timeline.total_samples


@pytest.mark.parametrize("overlap", [1, 3, 5])
@pytest.mark.parametrize("fps", [24, 25, 48, 50])
def test_stitched_duration_is_the_shots_minus_the_overlaps(fps, overlap):
    joins = ["fresh", "continue", "cut", "continue", "fresh", "cut", "continue"]
    durations = [2, 3, 5, 2, 4, 6, 3]
    timeline = plan(joins, durations, fps=fps, overlap=overlap)
    g = timeline.geometry
    overlaps = sum(g.pixel_frames(overlap) for j in joins if j != "fresh")
    assert timeline.total_frames == sum(ltx_frames(d, fps) for d in durations) - overlaps
    assert timeline.total_samples == timeline.total_frames * g.samples_per_frame
    assert timeline.total_frames / g.fps == pytest.approx(
        sum(ltx_frames(d, fps) / fps for d in durations) - overlaps / fps
    )


@pytest.mark.parametrize("anchor", lx.ANCHORS)
@pytest.mark.parametrize("fps", [24, 25, 48, 50])
@pytest.mark.parametrize("overlap", [1, 2, 3, 5])
def test_sync_error_stays_within_half_an_audio_latent_and_never_adds_up(anchor, fps, overlap):
    joins = ["fresh"] + ["continue", "continue", "cut", "continue", "cut", "cut", "continue"] * 4
    durations = [2, 3, 2, 5, 4, 2, 7, 3] * 3 + [2, 3, 4, 5, 6]
    timeline = plan(joins, durations[: len(joins)], fps=fps, overlap=overlap, anchor=anchor)
    half_latent = timeline.geometry.audio_ratio * timeline.geometry.samples_per_mel / 2  # 960 samples, 20 ms
    for join in timeline.joins:
        if join.audio_continuous:
            assert abs(join.sync_error_samples) <= half_latent
        else:  # nothing to run through: padded or cut into sync, to the sample
            assert abs(join.sync_error_samples) <= 0.5
    # Continuous joins only ever correct toward zero, so the last shot is no further off than the first join.
    assert abs(timeline.joins[-1].sync_error_samples) <= half_latent


def test_an_overlap_too_short_for_the_sound_pads_instead_of_drifting():
    # 2 s at 50 fps: 97 frames (93,120 samples of picture) but 48 audio latents (90,720 samples), 50 ms short. A one-frame
    # head trims 20 ms; even a one-latent audio pin would start the next shot's sound 40 ms early, and again at every join.
    timeline = plan(["fresh", "continue", "continue", "cut"], [2, 2, 2, 2], fps=50, overlap=1, anchor="previous")
    for join in timeline.joins[1:]:
        assert not join.audio_continuous and join.audio_source == join.index - 1
        assert join.audio_pin >= 1 and abs(join.sync_error_samples) <= 0.5
        assert "padded into sync" in join.notes[0]
    assert plan(["fresh", "continue"], [2, 2], fps=50, overlap=2).joins[1].audio_continuous  # 9 frames is enough


def test_audio_sources_follow_the_anchor():
    joins = ["fresh", "continue", "cut", "fresh", "cut", "continue"]
    first = plan(joins, [2] * 6, anchor="first")
    previous = plan(joins, [2] * 6, anchor="previous")
    assert [j.audio_source for j in first.joins] == [None, 0, 0, None, 3, 3]
    assert [j.audio_source for j in previous.joins] == [None, 0, 1, None, 3, 4]
    assert [j.video_source for j in first.joins] == [None, 0, None, None, None, 4]  # the picture always continues the previous shot
    assert [j.audio_continuous for j in first.joins] == [False, True, False, False, True, False]
    assert all(j.audio_pin == 0 and j.audio_trim == 0 and j.video_trim == 0 for j in first.joins if j.join == "fresh")


def test_anchored_and_fresh_joins_pad_the_previous_audio_into_sync():
    # Shot 2's pin is shot 1's own tail (continuous); shot 3's is anchored to shot 1 and shot 4 is fresh, so neither can run
    # through and the audio before each is padded to put the shot's audio clock exactly on its video clock.
    timeline = plan(["fresh", "cut", "cut", "fresh"], [2, 2, 2, 2], anchor="first")
    assert [j.audio_continuous for j in timeline.joins] == [False, True, False, False]
    assert [j.audio_pin for j in timeline.joins] == [0, 18, 18, 0]
    assert [j.sync_error_samples for j in timeline.joins] == [0, -640, 0, 0]
    # 49 frames are 98,000 samples of picture and the vocoder returns 96,480: about 32 ms of silence where a join cannot run through.
    assert [j.audio_pad for j in timeline.joins] == [0, 1280, 1520, 1520]
    assert [j.audio_start for j in timeline.joins] == [0, 96_480, 161_120, 226_000]


def test_stitched_audio_and_video_run_through_continuous_seams():
    """Clock arrays standing in for pictures and sound: shot N+1's own frame f is shot N's frame F - trim + f, and its
    sample s is shot N's sample S - trim + s. Stitched, a continuous seam must not repeat or skip a single one."""
    import numpy as np

    joins = ["fresh", "continue", "continue", "cut", "fresh", "cut", "continue"]
    timeline = plan(joins, [2, 3, 2, 4, 2, 3, 2], overlap=3, anchor="previous")
    video_clocks, audio_clocks = [], []
    for join in timeline.joins:
        if join.video_pin:  # frame 0 is the previous shot's frame F - trim
            video_base = video_clocks[-1][-1] + 1 - join.video_trim
        else:
            video_base = 100_000 * (join.index + 1)
        video_clocks.append(video_base + np.arange(join.decoded_frames))
        if join.audio_continuous:  # sample 0 is the previous shot's sample S - trim
            audio_base = audio_clocks[-1][-1] + 1 - join.audio_trim
        else:
            audio_base = 1_000_000 * (join.index + 1)
        audio_clocks.append(audio_base + np.arange(join.decoded_samples, dtype=np.float64))
    stitched_video = np.concatenate([clock[j.video_trim :] for j, clock in zip(timeline.joins, video_clocks)])
    assert len(stitched_video) == timeline.total_frames
    audio = lx.assemble_audio(timeline.joins, [c[None].astype(np.float32) for c in audio_clocks], timeline.total_samples)
    assert audio.shape == (1, timeline.total_samples)
    for join in timeline.joins[1:]:
        if join.video_pin:
            f = join.video_start
            assert stitched_video[f] - stitched_video[f - 1] == 1
        if join.audio_continuous:
            s = join.audio_start
            assert audio[0, s] - audio[0, s - 1] == 1


def test_the_declick_fade_touches_only_seams_the_sound_cannot_run_through():
    import numpy as np

    timeline = plan(["fresh", "continue", "cut", "fresh", "cut"], [2, 2, 2, 2, 2], anchor="first")
    assert [j.audio_continuous for j in timeline.joins] == [False, True, False, False, True]
    audios = [np.ones((2, j.decoded_samples), dtype=np.float32) for j in timeline.joins]
    plain = lx.assemble_audio(timeline.joins, audios, timeline.total_samples)
    faded = lx.assemble_audio(timeline.joins, audios, timeline.total_samples, fade_samples=240)
    changed = np.flatnonzero((plain != faded).any(axis=0))
    for join in timeline.joins[1:]:
        s = join.audio_start
        if join.audio_continuous:
            assert np.array_equal(plain[:, s - 300 : s + 300], faded[:, s - 300 : s + 300])
        else:
            assert 0 < faded[0, s] < 0.01 and faded[0, s + 239] > 0.99  # ramped in
            before = timeline.joins[join.index - 1]
            end = before.audio_start + before.decoded_samples - before.audio_trim  # the last real sample before the pad
            assert faded[0, end - 1] < 0.01 and faded[0, end - 241] == 1.0  # ramped out
    assert len(changed) == 2 * 240 * 2  # two seams, both sides


def test_a_decoder_that_breaks_the_causal_rule_rescales_the_trim():
    timeline = lx.Timeline(G24, 3, "previous")
    for index, join in enumerate(["fresh", "continue"]):
        planned = timeline.plan(lx.Shot(index, "p", 2, join), 49)
        timeline.rendered(index, 49, 96_000)  # 480 fewer samples than the rule predicts
    join = timeline.joins[1]
    assert join.notes and "96000" in join.notes[0]
    assert join.audio_trim == round(96_000 * G24.mel_frames(planned.audio_pin) / G24.mel_frames(51))
    assert join.audio_start == timeline.joins[0].audio_start + timeline.joins[0].audio_keep


# ---------------------------------------------------------------- storyboards and settings


def test_storyboards_in_this_folder_load():
    for path in sorted((Path(__file__).parent / "storyboards").glob("*.json")):
        name, shots = lx.load_storyboard(path)
        assert name and shots[0].join == "fresh"
        assert all(s.join in lx.JOINS and s.duration_s >= 2 and s.prompt for s in shots)


@pytest.mark.parametrize(
    ("shots", "message"),
    [
        ([{"prompt": "a", "duration_s": 2, "join": "continue"}], "must be fresh"),
        ([{"prompt": "a", "duration_s": 2}, {"prompt": "b", "duration_s": 2, "join": "dissolve"}], "dissolve"),
        ([{"prompt": "", "duration_s": 2}], "needs a prompt"),
        ([{"prompt": "a"}], "duration_s"),
    ],
)
def test_bad_storyboards_are_refused(tmp_path, shots, message):
    path = tmp_path / "board.json"
    path.write_text(json.dumps({"shots": shots}))
    with pytest.raises(lx.StoryboardError, match=message):
        lx.load_storyboard(path)


def test_later_shots_default_to_continue(tmp_path):
    path = tmp_path / "board.json"
    path.write_text(json.dumps([{"prompt": "a", "duration_s": 2}, {"prompt": "b", "duration_s": 2}]))
    assert [s.join for s in lx.load_storyboard(path)[1]] == ["fresh", "continue"]


def test_an_overlap_the_shot_cannot_hold_is_refused():
    with pytest.raises(lx.StoryboardError, match="overlap of 7"):
        plan(["fresh", "continue"], [2, 2], overlap=7)  # 2 s is 7 latent frames: at most 6 can be pinned


# ---------------------------------------------------------------- torch: pins


def _torch():
    return pytest.importorskip("torch")


def test_pinned_timesteps_are_zero_on_the_head_only():
    torch = _torch()
    t = torch.tensor([909.375, 909.375])  # a CFG batch of two
    out = lx.pinned_timesteps(t, 51, 18)
    assert out.shape == (2, 51)
    assert torch.equal(out[:, :18], torch.zeros(2, 18)) and torch.equal(out[:, 18:], torch.full((2, 33), 909.375))
    assert lx.clean_head(out, torch.zeros(1, 18, 128)) is True
    assert lx.clean_head(t, torch.zeros(1, 18, 128)) is False  # one timestep per row: the model sees the head as noise


def _fake_call(seed: int, prompt: str = "harbor", frames: int = 49, second: bool = True) -> dict:
    from_worker = {  # the shape of ltx_resident.build_call for ltx-2.5-fast
        "pipeline": "text", "prompt": prompt, "width": 320, "height": 192, "num_frames": frames, "frame_rate": 24.0, "seed": seed,
        "generate_audio": True, "sigmas": [1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875],
    }
    if second:
        from_worker["second_stage_sigmas"] = [0.909375, 0.725, 0.421875]
    return from_worker


def test_fake_pins_stay_bit_identical_through_every_step():
    torch = _torch()
    renderer = lx.FakeRenderer(overlap=3, trace=True)
    timeline = lx.Timeline(G24, 3, "previous")
    tails = {}
    for index, join_mode in enumerate(["fresh", "continue"]):
        join = timeline.plan(lx.Shot(index, "p", 2, join_mode), 49)
        call = _fake_call(1234 + index)
        pins = {stage: lx.pins_for(join, tails, stage) for stage in renderer.stages(call)}
        renderer.head_trace.clear()
        rendered = renderer.render(call, pins)
        timeline.rendered(index, len(rendered.frames), rendered.audio.shape[1])
        tails[index] = rendered.tails
    assert rendered.pins_exact == {"half": True, "full": True}
    assert rendered.seen_clean == {"half": {"video": True, "audio": True}, "full": {"video": True, "audio": True}}
    assert len(renderer.head_trace) == 8 + 3
    for stage, video_head, audio_head in renderer.head_trace:
        assert torch.equal(video_head, pins[stage].video)
        assert torch.equal(audio_head, pins[stage].audio)
    assert pins["half"].video.shape == (1, 3 * 5 * 3, 128)  # 3 latent frames of the 160x96 pass's 5x3 grid
    assert pins["full"].video.shape == (1, 3 * 10 * 6, 128)  # and of the 320x192 pass's 10x6 grid
    assert pins["full"].audio.shape == (1, join.audio_pin, 128)


def test_pinned_scheduler_holds_the_head_and_changes_nothing_else():
    torch = _torch()
    pytest.importorskip("diffusers")
    from diffusers import FlowMatchEulerDiscreteScheduler

    Scheduler, _ = lx.extend_classes()
    sigmas = [1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875]
    pinned, stock = Scheduler.from_config(FlowMatchEulerDiscreteScheduler().config), FlowMatchEulerDiscreteScheduler()
    for scheduler in (pinned, stock):
        scheduler.set_timesteps(sigmas=sigmas, device="cpu")
        scheduler.set_begin_index(0)
    generator = torch.Generator("cpu").manual_seed(0)
    head = torch.randn(1, 18, 128, generator=generator)
    pinned.start(head)
    sample_pinned = torch.randn(1, 51, 128, generator=generator)
    sample_pinned[:, :18] = head
    sample_stock = sample_pinned.clone()
    for t in pinned.timesteps:
        velocity = torch.randn(1, 51, 128, generator=generator)
        sample_pinned = pinned.step(velocity, t, sample_pinned, return_dict=False)[0]
        sample_stock = stock.step(velocity, t, sample_stock, return_dict=False)[0]
        assert torch.equal(sample_pinned[:, :18], head)
        assert torch.equal(sample_pinned[:, 18:], sample_stock[:, 18:])  # the step itself is the stock one
    assert not torch.equal(sample_stock[:, :18], head)  # without the pin the head would have moved
    assert torch.equal(pinned.final, sample_pinned)


@pytest.mark.parametrize("two_stage", [True, False])
def test_fake_chain_runs_through_every_continuous_seam(two_stage):
    """The fake decodes clocks through the causal VAEs' own frame and mel-frame layout, independently of the timeline's
    arithmetic: stitched, a continue seam advances the picture by one frame and a continuous audio join by one sample."""
    np = pytest.importorskip("numpy")
    _torch()
    renderer = lx.FakeRenderer(overlap=3)
    joins = ["fresh", "continue", "continue", "cut", "fresh", "cut", "continue"]
    durations = [2, 3, 2, 3, 2, 2, 3]
    timeline = lx.Timeline(G24, 3, "previous")
    tails, frame_clocks, sample_clocks = {}, [], []
    for index, (join_mode, duration) in enumerate(zip(joins, durations)):
        join = timeline.plan(lx.Shot(index, f"p{index}", duration, join_mode), ltx_frames(duration, 24))
        call = _fake_call(1234 + index, prompt=f"p{index}", frames=join.frames, second=two_stage)
        rendered = renderer.render(call, {stage: lx.pins_for(join, tails, stage) for stage in renderer.stages(call)})
        timeline.rendered(index, len(rendered.frames), rendered.audio.shape[1])
        tails[index] = rendered.tails
        frame_clocks.append(rendered.debug["frame_clock"])
        sample_clocks.append(rendered.debug["sample_clock"])
    total_frames, total_samples = timeline.finish()
    video = np.concatenate([c[j.video_trim :] for j, c in zip(timeline.joins, frame_clocks)])
    audio = lx.assemble_audio(timeline.joins, [c[None] for c in sample_clocks], total_samples)[0].astype(np.float64)
    assert len(video) == total_frames
    frame, sample = 1 / 24, 1 / 48_000
    within = np.diff(video[: timeline.joins[1].video_start])
    assert np.allclose(within, frame, atol=1e-4)
    for join in timeline.joins[1:]:
        f, s = join.video_start, join.audio_start
        if join.join == "continue":
            assert video[f] - video[f - 1] == pytest.approx(frame, abs=1e-4)
        if join.audio_continuous:
            assert audio[s] - audio[s - 1] == pytest.approx(sample, abs=1e-3)
            assert audio[s + 480] - audio[s - 1] == pytest.approx(481 * sample, abs=1e-3)


# ---------------------------------------------------------------- whole runs


def _board(tmp_path: Path, joins: list[str], duration: int = 2) -> Path:
    path = tmp_path / "board.json"
    path.write_text(json.dumps({"name": "test", "shots": [
        {"prompt": f"A calm lake at dawn, shot {i + 1}", "duration_s": duration, "join": j} for i, j in enumerate(joins)
    ]}))
    return path


def test_plan_only_needs_no_torch(tmp_path):
    pytest.importorskip("kuno_worker")
    out = tmp_path / "out"
    assert lx.main([str(_board(tmp_path, ["fresh", "continue", "cut"])), "--plan-only", "--out", str(out)]) == 0
    results = json.loads((out / "results.json").read_text())
    assert results["result"] == "planned"
    assert results["planned_stitched"]["frames"] == 3 * 49 - 2 * 17
    assert [s["audio_pin_latents"] for s in results["planned"]] == [0, 18, 18]


def _probe(path: Path) -> tuple[int, float, float]:
    """Decoded video frames, and the video's and audio's decoded lengths in seconds."""
    av = pytest.importorskip("av")
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        frames = sum(1 for _ in container.decode(video=0))
        video_s = frames / float(stream.average_rate)
    with av.open(str(path)) as container:
        rate = container.streams.audio[0].rate
        audio_s = sum(f.samples for f in container.decode(audio=0)) / rate
    return frames, video_s, audio_s


@pytest.mark.parametrize("anchor", lx.ANCHORS)
def test_fake_run_writes_every_output(tmp_path, anchor):
    _torch()
    pytest.importorskip("kuno_worker")
    out = tmp_path / "out"
    code = lx.main([str(_board(tmp_path, ["fresh", "continue", "cut", "fresh"])), "--fake", "--size", "320x192", "--audio-anchor", anchor, "--out", str(out)])
    results = json.loads((out / "results.json").read_text())
    assert code == 0, results["failures"]
    assert results["result"] == "pass" and not results["failures"]
    assert results["stitched"]["frames"] == results["stitched"]["expected_frames"] == 4 * 49 - 2 * 17
    assert [s["pins_exact"] for s in results["shots"]][1] == {"half": True, "full": True}
    assert len(results["seams"]) == 3 and results["seams"][0]["video_step_ratio"] == pytest.approx(1.0, abs=0.2)
    assert (out / "seams.png").stat().st_size > 0 and len(list((out / "shots").glob("*.mp4"))) == 4
    frames, video_s, audio_s = _probe(out / "stitched.mp4")
    assert frames == results["stitched"]["frames"]
    assert audio_s == pytest.approx(video_s, abs=0.03)


def test_a_failed_load_still_writes_results(tmp_path, monkeypatch):
    pytest.importorskip("kuno_worker")

    def no_gpu(args):
        raise RuntimeError("no CUDA device is visible to PyTorch")

    monkeypatch.setattr(lx, "make_renderer", no_gpu)
    out = tmp_path / "out"
    assert lx.main([str(_board(tmp_path, ["fresh", "continue"])), "--out", str(out)]) == 1
    results = json.loads((out / "results.json").read_text())
    assert results["result"] == "fail" and "no CUDA device" in results["failures"][0]
    assert results["planned_stitched"]["frames"] == 49 + 32


def test_a_shot_that_fails_leaves_the_earlier_shots_stitched(tmp_path, monkeypatch):
    _torch()
    pytest.importorskip("kuno_worker")
    render = lx.FakeRenderer.render
    calls = []

    def out_of_memory_on_shot_three(self, call, pins):
        calls.append(call["seed"])
        if len(calls) == 3:
            raise RuntimeError("CUDA out of memory")
        return render(self, call, pins)

    monkeypatch.setattr(lx.FakeRenderer, "render", out_of_memory_on_shot_three)
    out = tmp_path / "out"
    code = lx.main([str(_board(tmp_path, ["fresh", "continue", "cut", "continue"])), "--fake", "--size", "320x192", "--no-shot-videos", "--out", str(out)])
    results = json.loads((out / "results.json").read_text())
    assert code == 1 and results["result"] == "fail" and "out of memory" in results["failures"][0]
    assert results["stitched"]["partial"] is True and results["stitched"]["shots"] == 2
    assert results["stitched"]["frames"] == 49 + 32 and len(results["seams"]) == 1
    frames, video_s, audio_s = _probe(out / "stitched.mp4")
    assert frames == 81 and audio_s == pytest.approx(video_s, abs=0.03)


def test_tiny_diffusers_run_holds_the_pins_in_both_passes(tmp_path):
    _torch()
    pytest.importorskip("diffusers")
    pytest.importorskip("kuno_worker")
    out = tmp_path / "out"
    code = lx.main([str(_board(tmp_path, ["fresh", "continue", "cut"])), "--backend", "tiny", "--size", "320x192", "--no-shot-videos", "--out", str(out)])
    results = json.loads((out / "results.json").read_text())
    assert code == 0, results["failures"]
    shots = results["shots"]
    assert shots[1]["pins_exact"] == shots[2]["pins_exact"] == {"half": True, "full": True}
    assert shots[1]["pinned_head_seen_at_t0"] == {"half": {"video": True, "audio": True}, "full": {"video": True, "audio": True}}
    assert shots[2]["pinned_head_seen_at_t0"] == {"half": {"video": None, "audio": True}, "full": {"video": None, "audio": True}}
    assert all(s["decoded_audio_samples"] == s["predicted_audio_samples"] for s in shots)  # the real audio VAE and vocoder
    assert results["geometry"]["sample_rate"] == 48_000 and results["geometry"]["audio_latents_per_second"] == 25.0
