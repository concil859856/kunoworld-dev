"""End-to-end: SDK → gateway → mock-TEE worker → sealed video back to the SDK."""

from __future__ import annotations

import hashlib
import os
import time

import httpx
import pytest

from kuno_protocol.attestation import GoldenManifest
from kuno_protocol.canonical import b64d
from kuno_protocol.profiles import Mode, load_profiles
from kuno_protocol.schemas import JobState
from kuno_protocol.switch import SwitchConfig, sign_switch
from kuno_validator.scoring import normalize
from kuno_validator.validator import Validator
from kunoworld import KunoError

ALL_PROFILES = list(load_profiles())


def _is_mp4(data: bytes) -> bool:
    return data[4:8] == b"ftyp"


def test_text_to_video_round_trip_with_provenance(network):
    network.start_worker(ALL_PROFILES)
    with network.client("JP") as client:
        result = client.generate("A lighthouse keeper lights the lamp at dusk", model="h3-turbo", duration_s=5, aspect_ratio="21:9")
    assert _is_mp4(result.video)
    body = result.receipt.body
    assert body.profile_id == "h3-turbo" and body.video.width == 1536 and body.video.audio
    assert body.content_digest == hashlib.sha256(result.video).hexdigest()

    proof = httpx.get(f"{network.url}/v1/provenance/{body.content_digest}").json()
    assert proof["signature_valid"] is True
    assert proof["model"]["attribution"] == "MiniMax H3"
    assert proof["enclave"]["image_digest"] == body.image_digest


def test_gateway_never_stores_plaintext(network, images):
    network.start_worker(ALL_PROFILES)
    secret = "ZEBRA-7781-UNRELEASED-CAMPAIGN"
    with network.client("JP") as client:
        result = client.generate(f"{secret}: product reveal on a marble plinth", model="h3-turbo", first_frame=images["red"])
    assert _is_mp4(result.video)
    stored = b"".join(p.read_bytes() for p in network.data_dir.rglob("*") if p.is_file())
    assert secret.encode() not in stored
    assert images["red"] not in stored  # the reference image only exists as ciphertext
    assert result.video not in stored  # nor does the output


def test_first_last_frame_and_keyframes_on_ltx(network, images):
    network.start_worker(["ltx-2.5-fast"])
    with network.client("US") as client:
        flf = client.generate("Red dissolves to blue", model="ltx-2.5-fast", first_frame=images["red"], last_frame=images["blue"], duration_s=2)
        keys = client.generate(
            "Color study",
            model="ltx-2.5-fast",
            keyframes=[(images["red"], 0.0), (images["blue"], 1.5)],
            duration_s=2,
            aspect_ratio="9:16",
        )
    assert _is_mp4(flf.video) and _is_mp4(keys.video)
    assert keys.receipt.body.video.width == 704


def test_every_mode_survives_the_whole_pipeline(network, images, sample_audio, sample_video):
    """One job per generation mode: a role the worker cannot classify fails the job."""
    network.start_worker(ALL_PROFILES)
    with network.client("JP") as client:
        cases = {
            "text_to_video": dict(model="ltx-2.5-fast", duration_s=2),
            "image_to_video": dict(model="ltx-2.5-fast", duration_s=2, first_frame=images["red"]),
            "last_frame": dict(model="ltx-2.5-fast", duration_s=2, last_frame=images["blue"]),
            "keyframes": dict(model="ltx-2.5-fast", duration_s=2, keyframes=[(images["red"], 0.0), (images["blue"], 1.0)]),
            "audio_to_video": dict(model="ltx-2.5-pro", duration_s=2, source_audio=sample_audio, first_frame=images["red"]),
            # A lone source video infers video_edit, so retake has to say so.
            "retake": dict(model="ltx-2.5-fast", duration_s=2, source_video=sample_video, mode="retake"),
            "reference_to_video": dict(model="h3-reference", duration_s=5, reference_images=[images["red"]], reference_audio=[sample_audio]),
            "video_edit": dict(model="h3-reference", duration_s=5, source_video=sample_video),
            "extend_video": dict(model="h3-reference", duration_s=5, source_video=sample_video, mode="extend_video"),
        }
        for mode, kwargs in cases.items():
            result = client.generate(f"A harbour at dawn ({mode})", **kwargs)
            assert _is_mp4(result.video), mode
            assert result.receipt.body.video.duration_s > 0, mode


def test_region_rule_falls_back_to_ltx(network):
    network.start_worker(ALL_PROFILES)
    with network.client("US") as client:
        result = client.generate("City rooftops at night", model="h3-turbo", duration_s=6, resolution="768p")
    assert result.profile_id == "ltx-2.5-fast"
    assert result.fallback_reason == "region"
    assert result.receipt.body.video.width == 1280  # adapted to the fallback model's sizes


def test_owner_switch_routes_everything_to_ltx(network):
    network.start_worker(ALL_PROFILES)
    signed = sign_switch(network.owner_key(), SwitchConfig(mode="ltx", issued_at=int(time.time()) + 1))
    admin = {"authorization": f"Bearer {network.env['KUNO_ADMIN_TOKEN']}"}
    assert httpx.put(f"{network.url}/admin/v1/switch", json=signed.model_dump(mode="json"), headers=admin).status_code == 200

    unsigned = signed.model_copy(update={"signature": None})
    assert httpx.put(f"{network.url}/admin/v1/switch", json=unsigned.model_dump(mode="json"), headers=admin).status_code == 403

    with network.client("JP") as client:
        result = client.generate("Paper boats on a canal", model="h3")
    assert result.profile_id.startswith("ltx-2.5") and result.fallback_reason == "switched_off"


def test_tampered_public_params_fail_inside_the_enclave(network):
    network.start_worker(ALL_PROFILES)
    with network.client("JP") as client:
        prepared = client.prepare("Waves on black sand", model="h3-turbo", duration_s=5)
        # A malicious relay upgrades the job to 8 seconds after the client sealed it.
        prepared.request.params = prepared.request.params.model_copy(update={"duration_s": 8.0})
        job = client.submit(prepared)
        with pytest.raises(KunoError) as exc:
            job.wait(timeout=30)
    assert exc.value.code == "decrypt_failed"


def test_failed_jobs_are_refunded(network):
    network.start_worker(ALL_PROFILES)
    with network.client("JP") as client:
        before = _balance(network)
        with pytest.raises(KunoError):
            client.generate("csam", model="h3-turbo", timeout=30)
        assert _balance(network) == pytest.approx(before)


def _balance(network) -> float:
    from sqlalchemy import create_engine, text

    engine = create_engine(f"sqlite:///{network.data_dir / 'gateway.db'}")
    with engine.connect() as conn:
        return conn.execute(text("select balance_micros from accounts where id='dev'")).scalar_one() / 1_000_000


def test_validator_attests_and_scores_miners(network):
    network.start_worker(["h3-turbo", "ltx-2.5-fast"], hotkey="5MinerA")
    network.start_worker(["ltx-2.5-fast"], hotkey="5MinerB")
    manifest = GoldenManifest.model_validate_json((network.data_dir / "manifest.json").read_text())
    validator = Validator(
        network.url, network.env["KUNO_VALIDATOR_API_KEY"], manifest, b64d(network.env["KUNO_OWNER_PUBLIC_KEY"]), country="JP"
    )
    try:
        canary = validator.run_canary("h3-turbo")
        assert canary.ok, canary.detail
        with network.client("US") as client:
            client.generate("Morning market", model="ltx-2.5-fast", duration_s=2)
        verdicts = validator.check_enclaves()
        assert len(verdicts) == 2 and all(v.ok for v in verdicts.values())
        weights = normalize(validator.score(verdicts))
    finally:
        validator.close()
    assert set(weights) <= {"5MinerA", "5MinerB"} and "5MinerA" in weights
    assert sum(weights.values()) == pytest.approx(1.0)


def test_a_worker_that_leaves_releases_the_network(network):
    worker = network.start_worker(["ltx-2.5-fast"])
    # The enclave feed is for registered validators.
    validator = {"authorization": f"Bearer {network.env['KUNO_VALIDATOR_API_KEY']}"}
    assert any(e["status"] == "active" for e in httpx.get(f"{network.url}/validator/v1/enclaves", headers=validator).json())

    worker.retire()

    assert all(e["status"] != "active" for e in httpx.get(f"{network.url}/validator/v1/enclaves", headers=validator).json())
    assert httpx.get(f"{network.url}/v1/models").json()["workers_online"] == 0
    with network.client("JP") as client, pytest.raises(KunoError) as exc:
        client.generate("nobody home", model="ltx-2.5-fast", timeout=5)
    assert exc.value.code in ("no_capacity", "no_attested_worker", "mode_unavailable")


def test_worker_with_unapproved_image_is_rejected(network):
    with pytest.raises(AssertionError, match="failed to register"):
        network.start_worker(["h3-turbo"], image_digest="sha256:" + os.urandom(8).hex())
    with network.client("JP") as client, pytest.raises(KunoError) as exc:
        client.generate("anything", model="h3-turbo", timeout=5)
    assert exc.value.status in (503, 409)
