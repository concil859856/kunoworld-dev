"""End to end: one simulated machine can't register under two miner hotkeys at once.

Both workers run a MockTEE with the same machine id, so their signed quotes carry the same
simulated platform id and their GPU evidence the same simulated GPU ueids, exactly the way
two confidential VMs on one real host would share a PPID.
"""

from __future__ import annotations

import threading
import time

import httpx
import pytest

from kuno_protocol import devkit
from kuno_protocol.attestation import MockTEE
from kuno_protocol.canonical import b64d
from kuno_protocol.crypto import signing_key_from_bytes
from kuno_worker.backends.mock import MockBackend
from kuno_worker.config import WorkerConfig
from kuno_worker.gateway_client import GatewayError
from kuno_worker.worker import Worker


def worker_on(network, machine_id: str, hotkey: str) -> Worker:
    quote_key = signing_key_from_bytes(b64d((network.data_dir / "mock_quote.key").read_text()))
    config = WorkerConfig(
        gateway_url=network.url, profiles=["ltx-2.5-fast"], image_digest=devkit.DEV_IMAGE_DIGEST,
        miner_hotkey=hotkey, pull_wait_s=1.0,
    )
    return Worker(config, MockTEE(quote_key, devkit.DEV_IMAGE_DIGEST, machine_id=machine_id), {"*": MockBackend()})


def feed(network) -> dict[str, dict]:
    rows = httpx.get(
        f"{network.url}/validator/v1/enclaves", headers={"authorization": f"Bearer {network.env['KUNO_VALIDATOR_API_KEY']}"}
    ).json()
    return {row["enclave_id"]: row for row in rows}


def register(worker: Worker, hotkey: str, capacity: int = 1) -> dict:
    return worker.client.register(worker.attest(worker.client.nonce()), hotkey, capacity)


def test_a_second_hotkey_on_the_same_machine_is_refused(network):
    first = worker_on(network, "rig-1", "5MinerA")
    threading.Thread(target=first.run, args=(network.stop,), daemon=True).start()
    assert first.ready.wait(10), "first worker failed to register"

    row = feed(network)[first.identity.enclave_id]
    assert row["gpu_count"] == 4
    assert {h["kind"] for h in row["hardware_ids"]} == {"cpu_platform", "gpu"} and len(row["hardware_ids"]) == 5
    assert all(h["token"].startswith("hw1:") and "rig-1" not in h["token"] for h in row["hardware_ids"])

    sybil = worker_on(network, "rig-1", "5MinerB")
    with pytest.raises(GatewayError, match="hardware_in_use"):
        register(sybil, "5MinerB")
    assert sybil.identity.enclave_id not in feed(network)

    # Another machine registers under that hotkey without trouble.
    register(worker_on(network, "rig-2", "5MinerB"), "5MinerB")


def test_the_same_hotkey_on_the_same_machine_replaces_its_old_enclave(network):
    old = worker_on(network, "rig-1", "5MinerA")
    register(old, "5MinerA")
    new = worker_on(network, "rig-1", "5MinerA")
    assert register(new, "5MinerA")["replaced"] == [old.identity.enclave_id]
    rows = feed(network)
    assert rows[old.identity.enclave_id]["status"] == "stale" and rows[new.identity.enclave_id]["status"] == "active"

    # The replaced enclave holds nothing any more, so the machine can change hands once the new one leaves too.
    new.client.retire()  # what Worker.retire sends on shutdown (the worker loop isn't running here)
    register(worker_on(network, "rig-1", "5MinerB"), "5MinerB")


def test_an_enclave_whose_challenge_answer_shows_other_hardware_goes_stale(network):
    worker = worker_on(network, "rig-4", "5MinerA")
    threading.Thread(target=worker.run, args=(network.stop,), daemon=True).start()
    assert worker.ready.wait(10), "worker failed to register"
    # Its keys now answer from a different machine: a relay, as far as anyone can tell.
    quote_key = signing_key_from_bytes(b64d((network.data_dir / "mock_quote.key").read_text()))
    worker.tee = MockTEE(quote_key, devkit.DEV_IMAGE_DIGEST, machine_id="rig-5")

    validator = {"authorization": f"Bearer {network.env['KUNO_VALIDATOR_API_KEY']}"}
    created = httpx.post(
        f"{network.url}/validator/v1/challenges", headers=validator,
        json={"enclave_id": worker.identity.enclave_id, "nonce": "ab" * 32},
    )
    assert created.status_code == 201
    challenge = f"{network.url}/validator/v1/challenges/{created.json()['challenge_id']}"
    deadline = time.time() + 15
    while httpx.get(challenge, headers=validator).json()["status"] != "answered":
        assert time.time() < deadline, "the worker did not answer the challenge"
        time.sleep(0.2)
    assert feed(network)[worker.identity.enclave_id]["status"] == "stale"


def test_capacity_cannot_exceed_the_attested_gpus(network):
    worker = worker_on(network, "rig-3", "5MinerA")
    with pytest.raises(GatewayError, match="capacity_exceeds_hardware"):
        register(worker, "5MinerA", capacity=5)  # four simulated GPUs, one per ltx-2.5-fast job
    assert register(worker, "5MinerA", capacity=4)["status"] == "active"
