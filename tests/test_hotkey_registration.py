"""A worker earns for a hotkey only by proving it holds that hotkey, bound to its attested enclave."""

from __future__ import annotations

import os
import threading

import httpx
import pytest

from kuno_protocol import devkit
from kuno_protocol.attestation import MockTEE
from kuno_protocol.canonical import b64d
from kuno_protocol.crypto import signing_key_from_bytes
from kuno_protocol.hotkey import Sr25519Signer, sign_hotkey_proof
from kuno_worker.backends.mock import MockBackend
from kuno_worker.config import WorkerConfig
from kuno_worker.gateway_client import GatewayError
from kuno_worker.worker import Worker


def make_worker(network, hotkey=None, claimed: str | None = None) -> Worker:
    quote_key = signing_key_from_bytes(b64d((network.data_dir / "mock_quote.key").read_text()))
    config = WorkerConfig(
        gateway_url=network.url, profiles=["ltx-2.5-fast"], image_digest=devkit.DEV_IMAGE_DIGEST,
        miner_hotkey=claimed, pull_wait_s=1.0,
    )
    return Worker(config, MockTEE(quote_key, devkit.DEV_IMAGE_DIGEST), {"*": MockBackend()}, hotkey=hotkey)


def registered_hotkey(network, enclave_id: str) -> str | None:
    feed = httpx.get(
        f"{network.url}/validator/v1/enclaves", headers={"authorization": f"Bearer {network.env['KUNO_VALIDATOR_API_KEY']}"}
    ).json()
    rows = feed if isinstance(feed, list) else feed.get("enclaves", [])
    [row] = [r for r in rows if (r.get("enclave_id") or r.get("id")) == enclave_id]
    return row.get("miner_hotkey")


def test_a_worker_that_proves_its_hotkey_is_registered_under_it(network):
    signer = Sr25519Signer.from_seed(os.urandom(32))
    worker = make_worker(network, hotkey=signer)
    threading.Thread(target=worker.run, args=(network.stop,), daemon=True).start()
    assert worker.ready.wait(10), "worker failed to register"
    assert registered_hotkey(network, worker.identity.enclave_id) == signer.ss58_address


def test_a_proof_for_someone_elses_hotkey_or_another_nonce_is_refused(network):
    mine, theirs = Sr25519Signer.from_seed(os.urandom(32)), Sr25519Signer.from_seed(os.urandom(32))
    worker = make_worker(network)
    identity = worker.identity

    # Signed by my key, claiming their hotkey.
    nonce = worker.client.nonce()
    proof = sign_hotkey_proof(mine, nonce, identity.enclave_id, identity.signing_public)
    with pytest.raises(GatewayError, match="hotkey_proof_invalid"):
        worker.client.register(worker.attest(nonce), theirs.ss58_address, 1, proof)

    # A genuine proof, but made for a different registration nonce.
    nonce = worker.client.nonce()
    stale = sign_hotkey_proof(mine, b"\x01" * 32, identity.enclave_id, identity.signing_public)
    with pytest.raises(GatewayError, match="hotkey_proof_invalid"):
        worker.client.register(worker.attest(nonce), mine.ss58_address, 1, stale)
