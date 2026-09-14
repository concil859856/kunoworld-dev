"""Every blob the network writes is padded (blob format version 2): inputs sealed by the Python and JS SDKs, outputs
sealed by the enclave, and everything the gateway seals in Standard mode. Receipts still digest the plaintext video
and size the padded ciphertext."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

import httpx
import pytest

from kuno_protocol.blobs import MAGIC, V2, blob_version, sealed_size
from kuno_protocol.canonical import sha256_hex
from kuno_protocol.profiles import InputRole, Mode, load_profiles
from kuno_protocol.schemas import GenerationParams

SDK = Path(__file__).resolve().parents[1] / "sdk" / "js"
STANDARD_PROFILE = "ltx-2.5-fast"


def _stored_blob_versions(network) -> list[int | None]:
    """The version of every KunoWorld blob on disk, including one wrapped in a short at-rest envelope header."""
    versions = []
    for path in (network.data_dir / "blobs").rglob("*"):
        data = path.read_bytes() if path.is_file() else b""
        at = data.find(MAGIC, 0, 64)
        if at >= 0:
            versions.append(blob_version(data[at:]))
    return versions


def test_a_private_job_stores_its_input_and_output_padded(network, images):
    network.start_worker(["h3-turbo"])
    with network.client("JP") as client:
        result = client.generate("a red kite over the dunes", model="h3-turbo", first_frame=images["red"])
    versions = _stored_blob_versions(network)
    assert len(versions) >= 2 and set(versions) == {V2}
    body = result.receipt.body
    assert body.content_digest == sha256_hex(result.video)
    assert body.output_bytes == sealed_size(len(result.video))


def test_standard_mode_sealing_is_padded(network, images):
    network.start_worker([STANDARD_PROFILE])
    dev = {"authorization": f"Bearer {network.env['KUNO_DEV_API_KEY']}", "x-kuno-country": "JP"}
    limits = load_profiles()[STANDARD_PROFILE].limits
    resolution = next(iter(limits.sizes))
    params = GenerationParams(
        profile_id=STANDARD_PROFILE, mode=Mode.IMAGE_TO_VIDEO, duration_s=max(2.0, limits.min_duration_s), resolution=resolution,
        aspect_ratio="16:9" if "16:9" in limits.sizes[resolution] else next(iter(limits.sizes[resolution])),
        fps=limits.default_fps, audio=False, input_roles=[InputRole.FIRST_FRAME],
    )
    upload = httpx.post(f"{network.url}/v1/standard/uploads", params={"role": "first_frame"}, content=images["red"],
                        headers={**dev, "content-type": "image/png"})
    assert upload.status_code == 201, upload.text
    created = httpx.post(
        f"{network.url}/v1/standard/videos", headers=dev,
        json={"params": params.model_dump(mode="json"), "prompt": "a red paper boat on a pond", "seed": 7,
              "inputs": [{"upload_id": upload.json()["upload_id"], "index": 0, "role": "first_frame"}]},
    )
    assert created.status_code == 201, created.text
    job_id = created.json()["job_id"]
    deadline = time.time() + 180
    while (status := httpx.get(f"{network.url}/v1/videos/{job_id}", headers=dev).json())["status"] not in ("succeeded", "failed", "canceled"):
        assert time.time() < deadline, f"job still {status['status']}"
        time.sleep(0.5)
    assert status["status"] == "succeeded", status
    video = httpx.get(f"{network.url}/v1/standard/videos/{job_id}/video", headers=dev)
    assert video.status_code == 200

    versions = _stored_blob_versions(network)
    assert len(versions) >= 2 and set(versions) == {V2}
    body = status["receipt"]["body"]
    assert body["content_digest"] == sha256_hex(video.content)
    assert body["output_bytes"] == sealed_size(len(video.content))


@pytest.mark.skipif(shutil.which("node") is None or not (SDK / "dist" / "index.js").exists(), reason="build sdk/js first")
def test_js_sdk_inputs_are_stored_padded_and_its_output_opens(network, images, tmp_path):
    network.start_worker(["h3-turbo"])
    image = tmp_path / "first.png"
    image.write_bytes(images["red"])
    out = subprocess.run(
        ["node", str(SDK / "scripts" / "interop.mjs"), network.url, network.env["KUNO_DEV_API_KEY"], str(network.data_dir / "manifest.json"), str(image)],
        capture_output=True, text=True, timeout=90,
    )
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout.strip().splitlines()[-1])["digestMatches"] is True
    versions = _stored_blob_versions(network)
    assert len(versions) >= 2 and set(versions) == {V2}
