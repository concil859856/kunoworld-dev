"""The agent channel through the whole network: a real gateway's `POST /v1/quote` is the price the job is then charged, in
both modes, for a clip, a fallback and a storyboard; `max_price_usd` refuses before anything is created or charged; and the
MCP tools make a Private storyboard on a mock-TEE worker and save the decrypted video, matching its receipt. Also: the
gateway's quote fills in the same defaults, and infers the same modes, as the Python SDK."""

from __future__ import annotations

import itertools
from pathlib import Path

import httpx
import pytest
from kuno_gateway import api_quote
from kuno_protocol.canonical import sha256_hex
from kuno_protocol.profiles import InputRole, Mode, load_profiles
from kunoworld import Input, KunoError, Shot, infer_mode
from kunoworld.client import _fit_params
from kunoworld.mcp.tools import Config, KunoTools

PROFILES = load_profiles()
FAST = PROFILES["ltx-2.5-fast"]
SCENE = "A small blue fishing boat in a quiet harbor, soft morning light."
SHOTS = [Shot("The boat leaves the harbor.", 3), Shot("It passes the lighthouse.", 3), Shot("Close on the skipper.", 2, "cut")]


def balance(network) -> float:
    return httpx.get(f"{network.url}/v1/account", headers={"authorization": f"Bearer {network.env['KUNO_DEV_API_KEY']}"}).json()["balance_usd"]


@pytest.mark.parametrize("privacy", ["private", "standard"])
def test_the_quote_is_what_the_job_is_charged(network, privacy):
    network.start_worker(["ltx-2.5-fast", "ltx-2.5-pro"])
    kuno = network.client(country="US")  # MiniMax H3 isn't licensed there: a request for it falls back to LTX-2.5
    try:
        cases = [
            dict(model="ltx-2.5-pro", duration_s=4, resolution="1080p", fps=48),
            dict(model="h3-turbo", duration_s=6),
            dict(model="ltx-2.5-fast", shots=SHOTS, resolution="720p"),
        ]
        for case in cases:
            quote = kuno.quote(privacy=privacy, **{k: v for k, v in case.items()})
            before = balance(network)
            job = kuno.generate(SCENE, privacy=privacy, wait=False, max_price_usd=quote.price_usd, **case)
            status = job.status()
            assert status.params == quote.params and status.price_usd == quote.price_usd, case
            assert round(before - balance(network), 6) == quote.price_usd
            assert (job.profile_id, job.fallback_reason) == (quote.profile_id, quote.fallback_reason)
            job.wait(timeout=120)
        assert quote.params.mode is Mode.STORYBOARD and quote.breakdown.billable_seconds == quote.params.duration_s
    finally:
        kuno.close()


def test_over_budget_nothing_is_created_or_charged(network):
    network.start_worker(["ltx-2.5-fast"])
    kuno = network.client()
    try:
        before = balance(network)
        with pytest.raises(KunoError) as refused:
            kuno.generate(SCENE, model="ltx-2.5-fast", shots=SHOTS, max_price_usd=0.5)
        assert refused.value.code == "over_budget" and refused.value.details["price_usd"] > 0.5
        dev = {"authorization": f"Bearer {network.env['KUNO_DEV_API_KEY']}"}
        assert balance(network) == before and httpx.get(f"{network.url}/v1/videos", headers=dev).json() == []
    finally:
        kuno.close()


def test_the_mcp_tools_make_and_open_a_private_storyboard(network, tmp_path):
    network.start_worker(["ltx-2.5-fast"])
    config = Config(api_key=network.env["KUNO_DEV_API_KEY"], api_url=network.url, output_dir=tmp_path / "videos",
                    jobs_dir=tmp_path / "jobs", max_job_usd=5.0, country="JP")
    tools = KunoTools(config, client_factory=lambda _config: network.client())
    tools.poll_s = 0.2
    shots = [{"prompt": shot.prompt, "duration_s": shot.duration_s, "join": shot.join} for shot in SHOTS]
    quote = tools.quote_price(model="ltx-2.5-fast", shots=shots, resolution="720p")
    stages: list[str] = []
    result = tools.generate_video(SCENE, model="ltx-2.5-fast", shots=shots, resolution="720p", seed=3, wait=True, timeout_s=120,
                                  on_status=lambda status: stages.append(status.stage or ""))
    assert (result["status"], result["price_usd"], result["privacy"]) == ("succeeded", quote["price_usd"], "private")
    saved = Path(result["download"]["path"])
    assert sha256_hex(saved.read_bytes()) == result["download"]["receipt"]["content_digest"] == result["download"]["sha256"]
    assert result["download"]["receipt"]["duration_s"] == pytest.approx(quote["settings"]["duration_s"], abs=1e-3)
    assert stages[-1] == "done" and len(stages) < 600  # polled every poll_s, not in a tight loop
    assert tools.list_jobs()["jobs"][0]["saved_path"] == str(saved)


def test_the_gateways_quote_fills_in_what_the_sdk_would_send():
    """The same defaults and adaptations (api_quote.fit_params against kunoworld.client._fit_params) and the same mode
    inference, so a quote without every field prices what `generate` sends."""
    for roles in itertools.chain.from_iterable(itertools.combinations(list(InputRole), n) for n in range(3)):
        assert api_quote.infer_mode(list(roles)) is infer_mode(list(roles))

    requests = [
        dict(),
        dict(resolution="1080p", aspect_ratio="9:16", fps=50, duration_s=7, audio=False),
        dict(resolution="768p", aspect_ratio="21:9", duration_s=14),
        dict(fps=25, shots=[{}, {"duration_s": 8, "join": "cut"}, {"duration_s": 3}]),
    ]
    for profile, request, fallback in itertools.product(PROFILES.values(), requests, (None, "region")):
        shots = request.get("shots")
        if shots is not None and profile.limits.storyboard is None:
            continue
        mode = Mode.STORYBOARD if shots is not None else Mode.TEXT_TO_VIDEO
        body = api_quote.QuoteRequest(profile_id=profile.id, **request)
        gateway = api_quote.fit_params(profile, body, mode, [], fallback)
        sdk = _fit_params(
            profile, mode, [], request.get("duration_s"), request.get("resolution"), request.get("aspect_ratio"), request.get("fps"),
            request.get("audio", True), fallback,
            shots=None if shots is None else [Shot("-", s.get("duration_s"), s.get("join")) for s in shots],
        )
        assert gateway == sdk, (profile.id, request, fallback)
    image = api_quote.fit_params(FAST, api_quote.QuoteRequest(), Mode.IMAGE_TO_VIDEO, [InputRole.FIRST_FRAME], None)
    assert image == _fit_params(FAST, Mode.IMAGE_TO_VIDEO, [Input(InputRole.FIRST_FRAME, b"", "")], None, None, None, None, True, None)
