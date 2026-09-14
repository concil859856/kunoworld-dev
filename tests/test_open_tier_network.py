"""The open tier on a real local network: an open-tier worker with no TEE registers with its hotkey proof,
shows up as tier "open", and no private job can reach it, whether through routing, the client SDK, or a
private job sealed to it by hand. Standard jobs (when the gateway serves them) run on it."""

from __future__ import annotations

import os
import threading
import time
import uuid

import httpx
import pytest

from kuno_gateway.settings import Settings
from kuno_gateway.state import GatewayState
from kuno_protocol import devkit
from kuno_protocol.attestation import OpenTEE
from kuno_protocol.canonical import b64d, b64e
from kuno_protocol.crypto import SenderSession
from kuno_protocol.hotkey import Sr25519Signer
from kuno_protocol.profiles import Mode
from kuno_protocol.schemas import GenerationParams, JobCreate, SealedPayload, job_aad
from kuno_worker.backends.mock import MockBackend
from kuno_worker.config import WorkerConfig
from kuno_worker.worker import Worker
from kunoworld import KunoError

PROFILE = "ltx-2.5-fast"
PARAMS = GenerationParams(profile_id=PROFILE, mode=Mode.TEXT_TO_VIDEO, duration_s=2, resolution="720p", aspect_ratio="16:9", fps=24)


def start_open_worker(network) -> tuple[Worker, Sr25519Signer]:
    signer = Sr25519Signer.from_seed(os.urandom(32))
    config = WorkerConfig(gateway_url=network.url, profiles=[PROFILE], tee="open", image_digest=devkit.DEV_IMAGE_DIGEST, pull_wait_s=1.0)
    worker = Worker(config, OpenTEE(), {"*": MockBackend()}, hotkey=signer)
    threading.Thread(target=worker.run, args=(network.stop,), daemon=True).start()
    assert worker.ready.wait(10), "open-tier worker failed to register"
    network.workers.append(worker)
    return worker, signer


def wait_terminal(network, job_id: str, headers: dict, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    while True:
        status = httpx.get(f"{network.url}/v1/videos/{job_id}", headers=headers).json()
        if status["status"] in ("succeeded", "failed", "canceled") or time.time() > deadline:
            return status
        time.sleep(0.3)


def test_an_open_tier_worker_registers_and_no_private_job_reaches_it(network):
    worker, signer = start_open_worker(network)
    enclave_id = worker.identity.enclave_id
    validator = {"authorization": f"Bearer {network.env['KUNO_VALIDATOR_API_KEY']}"}
    (row,) = [r for r in httpx.get(f"{network.url}/validator/v1/enclaves", headers=validator).json() if r["enclave_id"] == enclave_id]
    assert (row["tier"], row["tee"], row["miner_hotkey"], row["hardware_ids"]) == ("open", "open", signer.ss58_address, [])

    # The gateway's routing helper: nothing for private jobs, the open worker for standard ones.
    state = GatewayState(Settings.from_env({"KUNO_DATA_DIR": str(network.data_dir)}))
    with state.session() as s:
        assert state.routable_enclaves(s, PROFILE, "private") == []
        assert [e.id for e in state.routable_enclaves(s, PROFILE, "standard")] == [enclave_id]

    # The client SDK never seals a private job to an enclave that attests no TEE.
    client = network.client()
    with pytest.raises(KunoError):
        client.generate("A lighthouse keeper climbs the stairs at dusk", model=PROFILE, duration_s=2, timeout=20)

    # Sealed to the open enclave by hand: refused at creation, or failed before the worker ever gets it.
    customer = {"authorization": f"Bearer {network.env['KUNO_DEV_API_KEY']}", "x-kuno-country": "JP"}
    job_id = str(uuid.uuid4())
    session = SenderSession(b64d(row["hpke_public_key"]))
    ciphertext = session.seal(SealedPayload(prompt="a private prompt", seed=7).model_dump_json().encode(), job_aad(job_id, enclave_id, PARAMS, []))
    request = JobCreate(job_id=job_id, params=PARAMS, enclave_id=enclave_id, enc=b64e(session.enc), ciphertext=b64e(ciphertext))
    response = httpx.post(f"{network.url}/v1/videos", json=request.model_dump(mode="json"), headers=customer)
    if response.status_code >= 300:
        assert response.status_code == 409 and response.json()["detail"]["code"] == "enclave_unavailable", response.text
    else:
        status = wait_terminal(network, job_id, customer)
        assert status["status"] == "failed" and status["receipt"] is None and status["error_code"] == "enclave_unavailable"


def test_a_standard_job_runs_on_the_open_tier_worker(network, monkeypatch):
    # A brand-new open-tier miner would still be in admission; that rule has its own tests (test_open_tier_admission.py).
    monkeypatch.setenv("KUNO_OPEN_TIER_ADMISSION_JOBS", "0")
    worker, _ = start_open_worker(network)
    customer = {"authorization": f"Bearer {network.env['KUNO_DEV_API_KEY']}", "x-kuno-country": "JP"}
    response = httpx.post(
        f"{network.url}/v1/standard/videos",
        json={"params": PARAMS.model_dump(mode="json"), "prompt": "A paper boat drifts down a rain gutter", "seed": 11},
        headers=customer,
    )
    if response.status_code in (404, 405):
        pytest.skip("this gateway does not serve standard jobs yet")
    assert response.status_code == 201, response.text
    status = wait_terminal(network, response.json()["job_id"], customer, timeout=60)
    assert status["status"] == "succeeded", status
    assert status["enclave_id"] == worker.identity.enclave_id and status["privacy"] == "standard"
    assert status["receipt"]["body"]["miner_hotkey"] == worker.miner_hotkey
