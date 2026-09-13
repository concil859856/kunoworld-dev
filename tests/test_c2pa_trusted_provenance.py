"""End-to-end: a C2PA worker gets its signing certificate from the gateway's CA after attesting,
and the video a customer receives verifies as trusted against GET /v1/c2pa/trust."""

from __future__ import annotations

import threading

import httpx
import pytest
from cryptography import x509

from kuno_gateway.ca import IssuanceLog
from kuno_protocol import c2pa_certs, devkit
from kuno_protocol.attestation import MockTEE
from kuno_protocol.c2pa_certs import EnclaveBinding
from kuno_protocol.canonical import b64d
from kuno_protocol.crypto import signing_key_from_bytes
from kuno_worker.backends.mock import MockBackend
from kuno_worker.config import WorkerConfig
from kuno_worker.worker import Worker


def test_a_video_signed_under_a_gateway_issued_certificate_verifies_as_trusted(network):
    pytest.importorskip("c2pa")
    from kuno_worker.provenance import read_provenance, verify_provenance

    quote_key = signing_key_from_bytes(b64d((network.data_dir / "mock_quote.key").read_text()))
    config = WorkerConfig(
        gateway_url=network.url, profiles=["ltx-2.5-fast"], image_digest=devkit.DEV_IMAGE_DIGEST,
        miner_hotkey="5MinerHotkey01", pull_wait_s=1.0, provenance="c2pa",
    )
    worker = Worker(config, MockTEE(quote_key, devkit.DEV_IMAGE_DIGEST), {"*": MockBackend()})
    threading.Thread(target=worker.run, args=(network.stop,), daemon=True).start()
    assert worker.ready.wait(15), "worker failed to register"
    certificate = worker._provenance_signer.certificate
    assert certificate.source == "gateway"

    with network.client("JP") as client:
        result = client.generate("A lighthouse keeper lights the lamp at dusk", model="ltx-2.5-fast", duration_s=2)

    trust = httpx.get(f"{network.url}/v1/c2pa/trust").json()
    anchors = trust["trust_anchors_pem"]
    assert verify_provenance(result.video, result.receipt, worker.identity.signing_public, trust_anchors_pem=anchors) == []
    provenance = read_provenance(result.video, anchors)
    assert provenance.ok and provenance.trusted and provenance.state == "Trusted"
    assert provenance.signer.get("common_name") == worker.identity.enclave_id

    # Without the anchor the same file is intact but unidentified; another root does not vouch for it.
    untrusted = read_provenance(result.video)
    assert untrusted.ok and not untrusted.trusted
    _, stranger_root = c2pa_certs.generate_root("someone else's root")
    assert not read_provenance(result.video, c2pa_certs.certificate_pem(stranger_root)).trusted

    # The certificate that signed is on the gateway's issuance record, bound to the evidence it verified.
    leaf = x509.load_pem_x509_certificates(certificate.chain_pem.encode())[0]
    records = IssuanceLog(network.data_dir / "c2pa" / "issuance.jsonl").records()
    [record] = [r for r in records if r["serial"] == format(leaf.serial_number, "x")]
    binding = EnclaveBinding.from_certificate(leaf)
    assert record["enclave_id"] == binding.enclave_id == result.receipt.body.enclave_id
    assert record["evidence_digest"] == binding.evidence_digest
    assert binding.image_digest == result.receipt.body.image_digest and binding.profiles == ["ltx-2.5-fast"]
