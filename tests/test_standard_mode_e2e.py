"""Standard mode through the whole network: the gateway seals the job, a mock-TEE worker renders it unchanged,
and the owner downloads plaintext the gateway only ever stored encrypted."""

from __future__ import annotations

import time

import httpx
from kuno_protocol.canonical import sha256_hex
from kuno_protocol.profiles import InputRole, Mode, load_profiles
from kuno_protocol.schemas import GenerationParams

PROFILE = "ltx-2.5-fast"


def _params(roles: list[InputRole]) -> GenerationParams:
    limits = load_profiles()[PROFILE].limits
    resolution = next(iter(limits.sizes))
    return GenerationParams(
        profile_id=PROFILE, mode=Mode.IMAGE_TO_VIDEO if roles else Mode.TEXT_TO_VIDEO, duration_s=max(2.0, limits.min_duration_s),
        resolution=resolution, aspect_ratio="16:9" if "16:9" in limits.sizes[resolution] else next(iter(limits.sizes[resolution])),
        fps=limits.default_fps, audio=False, input_roles=roles,
    )


def _wait(url: str, headers: dict, job_id: str, timeout: float = 180) -> dict:
    deadline = time.time() + timeout
    while True:
        status = httpx.get(f"{url}/v1/videos/{job_id}", headers=headers).json()
        if status["status"] in ("succeeded", "failed", "canceled"):
            return status
        assert time.time() < deadline, f"job still {status['status']}"
        time.sleep(0.5)


def _stored_files(network) -> list[bytes]:
    return [p.read_bytes() for p in (network.data_dir / "blobs").rglob("*") if p.is_file()]


def test_standard_job_round_trip_through_a_real_worker(network, images):
    network.start_worker([PROFILE])
    dev = {"authorization": f"Bearer {network.env['KUNO_DEV_API_KEY']}", "x-kuno-country": "JP"}
    validator = {"authorization": f"Bearer {network.env['KUNO_VALIDATOR_API_KEY']}"}
    url = network.url

    upload = httpx.post(f"{url}/v1/standard/uploads", params={"role": "first_frame"}, content=images["red"],
                        headers={**dev, "content-type": "image/png"})
    assert upload.status_code == 201, upload.text
    assert all(images["red"] not in data for data in _stored_files(network))

    params = _params([InputRole.FIRST_FRAME])
    created = httpx.post(
        f"{url}/v1/standard/videos",
        json={"params": params.model_dump(mode="json"), "prompt": "a red paper boat on a pond", "seed": 1234,
              "inputs": [{"upload_id": upload.json()["upload_id"], "index": 0, "role": "first_frame"}]},
        headers=dev,
    )
    assert created.status_code == 201, created.text
    job_id = created.json()["job_id"]
    assert created.json()["privacy"] == "standard"

    status = _wait(url, dev, job_id)
    assert status["status"] == "succeeded", status
    assert status["privacy"] == "standard"

    video = httpx.get(f"{url}/v1/standard/videos/{job_id}/video", headers=dev)
    assert video.status_code == 200 and video.content[4:8] == b"ftyp"
    assert sha256_hex(video.content) == status["receipt"]["body"]["content_digest"]
    # A standard video has the same public provenance as a private one.
    assert httpx.get(f"{url}/v1/provenance/{sha256_hex(video.content)}").status_code == 200

    thumbnail = httpx.get(f"{url}/v1/standard/videos/{job_id}/thumbnail", headers=dev)
    assert thumbnail.status_code == 200 and thumbnail.content.startswith(b"\xff\xd8")

    # Nothing the customer or the worker saw is on disk in the clear.
    stored = _stored_files(network)
    assert all(video.content not in data and thumbnail.content not in data for data in stored)

    feed = httpx.get(f"{url}/validator/v1/standard-jobs/{job_id}", headers=validator).json()
    assert (feed["prompt"], feed["seed"], feed["inputs"][0]["sha256"]) == ("a red paper boat on a pond", 1234, sha256_hex(images["red"]))

    listed = httpx.get(f"{url}/v1/standard/videos", headers=dev).json()
    assert listed[0]["job_id"] == job_id and listed[0]["has_video"] is True

    assert httpx.delete(f"{url}/v1/standard/videos/{job_id}", headers=dev).status_code == 204
    assert httpx.get(f"{url}/v1/standard/videos/{job_id}/video", headers=dev).status_code == 410


def test_a_blocked_standard_prompt_is_refused_by_the_gateway_and_counts_as_a_strike(network):
    network.start_worker([PROFILE])
    dev = {"authorization": f"Bearer {network.env['KUNO_DEV_API_KEY']}", "x-kuno-country": "JP"}
    created = httpx.post(
        f"{network.url}/v1/standard/videos",
        json={"params": _params([]).model_dump(mode="json"), "prompt": "jailbait"},
        headers=dev,
    )
    # The gateway can read a Standard prompt, so the content policy refuses it before anything is sealed or charged.
    assert created.status_code == 422, created.text
    assert created.json()["detail"] == {
        "code": "content_policy", "message": "This prompt isn't allowed. Sexual and NSFW content is not permitted.",
    }
    eligibility = httpx.get(f"{network.url}/v1/account/eligibility", headers=dev).json()
    # The seeded dev account collects the strike but stays exempt from restrictions.
    assert eligibility["strikes_24h"] == 1 and eligibility["restricted_until"] is None
