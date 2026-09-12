from __future__ import annotations

import os
import time

import pytest

from kuno_protocol import devkit
from kuno_protocol.attestation import GoldenManifest, MockTEE, build_evidence, verify_evidence
from kuno_protocol.blobs import decrypt_blob, encrypt_blob
from kuno_protocol.canonical import b64d, b64e
from kuno_protocol.crypto import (
    DecryptionError,
    RecipientSession,
    SenderSession,
    generate_hpke_keypair,
    generate_signing_key,
    public_key_bytes,
    signing_key_from_bytes,
)
from kuno_protocol.profiles import (
    InputRole,
    Mode,
    ParamError,
    h3_num_frames,
    load_profiles,
    ltx_num_frames,
    validate_params,
    validate_roles,
)
from kuno_protocol.receipts import ReceiptBody, VideoInfo, sign_receipt, verify_receipt
from kuno_protocol.schemas import GenerationParams
from kuno_protocol.switch import RouteError, SwitchConfig, resolve_route

PROFILES = load_profiles()


def test_hpke_round_trip_and_shared_export_keys():
    private, public = generate_hpke_keypair()
    sender = SenderSession(public)
    ciphertext = sender.seal(b"a lighthouse at dusk", b"aad")
    recipient = RecipientSession(private, sender.enc)
    assert recipient.open(ciphertext, b"aad") == b"a lighthouse at dusk"
    assert (recipient.input_key, recipient.output_key) == (sender.input_key, sender.output_key)
    with pytest.raises(DecryptionError):
        RecipientSession(private, sender.enc).open(ciphertext, b"different aad")
    with pytest.raises(RuntimeError):
        sender.seal(b"second message", b"aad")


def test_blob_round_trip_detects_tampering_truncation_and_relabeling():
    key = os.urandom(32)
    data = os.urandom(3 * 1024 + 17)
    sealed = encrypt_blob(key, "job/input/0", data, chunk_size=1024)
    assert decrypt_blob(key, "job/input/0", sealed) == data
    with pytest.raises(DecryptionError):
        decrypt_blob(key, "job/input/1", sealed)
    with pytest.raises(DecryptionError):
        decrypt_blob(key, "job/input/0", sealed[: 18 + 2 * (1024 + 16)])
    flipped = bytearray(sealed)
    flipped[40] ^= 1
    with pytest.raises(DecryptionError):
        decrypt_blob(key, "job/input/0", bytes(flipped))
    assert decrypt_blob(key, "empty", encrypt_blob(key, "empty", b"")) == b""


def test_frame_grids():
    assert h3_num_frames(5) == 124
    assert h3_num_frames(14) == 345
    assert (h3_num_frames(10) - 5) % 17 == 0
    assert ltx_num_frames(5, 24) == 121
    assert (ltx_num_frames(7, 25) - 1) % 8 == 0


def test_h3_reference_input_rules():
    profile = PROFILES["h3-reference"]
    R = InputRole
    validate_roles(profile, Mode.REFERENCE_TO_VIDEO, [R.REFERENCE_IMAGE] * 9 + [R.REFERENCE_VIDEO] * 3)
    with pytest.raises(ParamError, match="at most 3"):
        validate_roles(profile, Mode.REFERENCE_TO_VIDEO, [R.REFERENCE_VIDEO] * 4)
    with pytest.raises(ParamError, match="image or video"):
        validate_roles(profile, Mode.REFERENCE_TO_VIDEO, [R.REFERENCE_AUDIO])
    with pytest.raises(ParamError, match="needs"):
        validate_roles(profile, Mode.VIDEO_EDIT, [R.REFERENCE_IMAGE])


def test_params_validation():
    good = GenerationParams(
        profile_id="h3-turbo", mode=Mode.TEXT_TO_VIDEO, duration_s=6, resolution="768p", aspect_ratio="21:9", fps=24
    )
    validate_params(PROFILES["h3-turbo"], good)
    for change, message in [
        ({"duration_s": 15}, "duration"),
        ({"fps": 30}, "fps"),
        ({"resolution": "1080p"}, "does not support"),
        ({"mode": Mode.KEYFRAMES}, "does not support"),
    ]:
        with pytest.raises(ParamError, match=message):
            validate_params(PROFILES["h3-turbo"], good.model_copy(update=change))


def test_routing_applies_switch_region_and_fallback():
    auto = SwitchConfig()
    assert resolve_route(PROFILES, auto, Mode.TEXT_TO_VIDEO, "JP").profile.id == "h3-turbo"

    us = resolve_route(PROFILES, auto, Mode.TEXT_TO_VIDEO, "US", requested_profile_id="h3-turbo")
    assert us.profile.family == "ltx-2.5" and us.fallback_reason == "region"
    assert resolve_route(PROFILES, auto, Mode.TEXT_TO_VIDEO, None).profile.family == "ltx-2.5"

    with pytest.raises(RouteError) as exc:
        resolve_route(PROFILES, auto, Mode.REFERENCE_TO_VIDEO, "DE")
    assert exc.value.status == 451

    ltx_only = SwitchConfig(mode="ltx")
    switched = resolve_route(PROFILES, ltx_only, Mode.IMAGE_TO_VIDEO, "JP", requested_profile_id="h3")
    assert switched.profile.id == "ltx-2.5-fast" and switched.fallback_reason == "switched_off"

    authorized = SwitchConfig(h3_authorized_everywhere=True)
    assert resolve_route(PROFILES, authorized, Mode.TEXT_TO_VIDEO, "US").profile.id == "h3-turbo"

    strict = SwitchConfig(mode="both")
    with pytest.raises(RouteError) as exc:
        resolve_route(PROFILES, strict, Mode.TEXT_TO_VIDEO, "JP", has_capacity=lambda _p: False)
    assert exc.value.status == 503


def _evidence(tmp_path, image_digest=devkit.DEV_IMAGE_DIGEST, profiles=("h3-turbo",)):
    devkit.init(tmp_path)
    manifest = GoldenManifest.model_validate_json((tmp_path / "manifest.json").read_text())
    quote_key = signing_key_from_bytes(b64d((tmp_path / "mock_quote.key").read_text()))
    _, hpke_pk = generate_hpke_keypair()
    sign_key = generate_signing_key()
    nonce = os.urandom(32)
    evidence = build_evidence(MockTEE(quote_key, image_digest), nonce, hpke_pk, public_key_bytes(sign_key), image_digest, list(profiles))
    return manifest, evidence, nonce


def test_attestation_accepts_the_pinned_image(tmp_path):
    manifest, evidence, nonce = _evidence(tmp_path)
    verdict = verify_evidence(evidence, manifest, expected_nonce=nonce)
    assert verdict.ok, verdict.reasons


def test_attestation_rejects_wrong_nonce_swapped_keys_unknown_image_and_forged_quotes(tmp_path):
    manifest, evidence, nonce = _evidence(tmp_path / "a")
    assert not verify_evidence(evidence, manifest, expected_nonce=os.urandom(32)).ok

    _, other_pk = generate_hpke_keypair()
    swapped = evidence.model_copy(update={"hpke_public_key": b64e(other_pk)})
    assert any("REPORTDATA" in r for r in verify_evidence(swapped, manifest).reasons)

    stale = evidence.model_copy(update={"created_at": time.time() - 10_000})
    assert not verify_evidence(stale, manifest).ok

    manifest2, rogue, _ = _evidence(tmp_path / "b", image_digest="sha256:rogue-image")
    assert any("golden manifest" in r for r in verify_evidence(rogue, manifest2).reasons)

    # A quote signed by a key the manifest doesn't trust.
    manifest3, _, _ = _evidence(tmp_path / "c")
    assert not verify_evidence(evidence, manifest3).ok


def test_receipt_signatures():
    key = generate_signing_key()
    body = ReceiptBody(
        job_id="j", enclave_id="e", profile_id="h3", image_digest="d", params_digest="p", input_digest="i",
        output_digest="o", output_bytes=1, content_digest="c", attestation_digest="a", started_at=0, finished_at=1,
        gpu_seconds=4, video=VideoInfo(duration_s=5, width=1344, height=768, fps=24, frames=124, audio=True),
    )
    receipt = sign_receipt(key, body)
    assert verify_receipt(receipt, public_key_bytes(key))
    forged = receipt.model_copy(update={"body": body.model_copy(update={"profile_id": "ltx-2.5-fast"})})
    assert not verify_receipt(forged, public_key_bytes(key))
