"""Storyboards through the whole network (PROTOCOL.md, "Storyboards"): the Python SDK plans the shots, a real gateway
prices and routes the job by its stitched length and longest shot, a mock-TEE worker renders every shot and returns one
stitched video, and the receipt, the video and the validator's view all agree on its length."""

from __future__ import annotations

import httpx
from kuno_protocol.mp4 import probe
from kuno_protocol.profiles import load_profiles, storyboard_duration_s, storyboard_frames
from kuno_protocol.schemas import ShotSpec
from kuno_validator.ledger import duration_bounds
from kunoworld import Shot

FAST = load_profiles()["ltx-2.5-fast"]
SCENE = "A small blue fishing boat in a quiet harbor, soft morning light."
SHOTS = [
    Shot("The boat leaves the harbor, gulls circling.", duration_s=3),
    Shot("It passes the lighthouse at the end of the breakwater.", duration_s=3),
    Shot("Close on the skipper at the wheel.", duration_s=2, join="cut"),
    Shot("Night: the boat's lamp alone on a dark sea.", duration_s=3, join="fresh"),
]
SPECS = [ShotSpec(duration_s=3, join="fresh"), ShotSpec(duration_s=3, join="continue"), ShotSpec(duration_s=2, join="cut"),
         ShotSpec(duration_s=3, join="fresh")]


def run(network, privacy: str):
    network.start_worker(["ltx-2.5-fast"])
    kuno = network.client()
    statuses = []
    try:
        quoted = kuno.estimate_price("ltx-2.5-fast", shots=SHOTS, resolution="720p", privacy=privacy)
        result = kuno.generate(SCENE, shots=SHOTS, model="ltx-2.5-fast", resolution="720p", seed=7, privacy=privacy,
                               timeout=120, on_progress=statuses.append)
    finally:
        kuno.close()
    frames, duration = storyboard_frames(FAST, SPECS, 24), storyboard_duration_s(FAST, SPECS, 24)
    body = result.receipt.body
    assert (result.privacy, result.profile_id) == (privacy, "ltx-2.5-fast")
    assert body.video.frames == frames and abs(body.video.duration_s - duration) < 1e-3
    assert abs(probe(result.video).duration_s - duration) < 0.1
    low, high = duration_bounds(FAST, duration, 24, storyboard=True)
    assert low <= body.video.duration_s <= high
    final = statuses[-1]
    assert final.params.shots == SPECS and final.params.duration_s == duration and final.price_usd == quoted
    return result


def test_a_private_storyboard_is_one_sealed_job_one_stitched_video_and_one_receipt(network):
    run(network, "private")


def test_a_standard_storyboard_round_trips_with_its_shot_prompts_visible_to_validators(network):
    result = run(network, "standard")
    validator = {"authorization": f"Bearer {network.env['KUNO_VALIDATOR_API_KEY']}"}
    feed = httpx.get(f"{network.url}/validator/v1/standard-jobs/{result.job_id}", headers=validator).json()
    assert feed["prompt"] == SCENE and [shot["prompt"] for shot in feed["shots"]] == [shot.prompt for shot in SHOTS]
