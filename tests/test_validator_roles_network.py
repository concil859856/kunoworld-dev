"""One main validator and an auditor on a real gateway: the main validator's signed findings reach the auditor through
the gateway, and the auditor, which sends no jobs, reaches the same weights from published evidence and receipts."""

from __future__ import annotations

import os
import time

import pytest

from kuno_protocol.attestation import GoldenManifest
from kuno_protocol.canonical import b64d
from kuno_protocol.hotkey import Sr25519Signer
from kuno_validator.validator import CanaryResult, Validator


def test_an_auditor_follows_the_main_validator_through_the_gateway(network):
    a = network.start_worker(["ltx-2.5-fast"], hotkey="5MinerA")
    network.start_worker(["ltx-2.5-fast"], hotkey="5MinerB")
    with network.client("US") as client:
        for _ in range(2):
            client.generate("Morning market", model="ltx-2.5-fast", duration_s=2)
    manifest = GoldenManifest.model_validate_json((network.data_dir / "manifest.json").read_text())
    owner = b64d(network.env["KUNO_OWNER_PUBLIC_KEY"])
    key = network.env["KUNO_VALIDATOR_API_KEY"]
    signer = Sr25519Signer.from_seed(os.urandom(32))
    main = Validator(network.url, key, manifest, owner, role="main", findings_signer=signer)
    auditor = Validator(network.url, key, manifest, owner, role="auditor", main_validator_hotkey=signer.ss58_address, spot_check_rate=1.0)
    try:
        before_main, before_auditor = main.step(), auditor.step()
        assert before_auditor == pytest.approx(before_main)
        assert auditor.last_divergence == pytest.approx(0.0, abs=1e-6)

        # The main validator catches 5MinerA on a canary; the auditor never saw that job, and applies the finding.
        caught = CanaryResult("ltx-2.5-fast", False, "output does not match the request", "job-caught",
                              a.identity.enclave_id, "5MinerA", True, time.time())
        main.canary_results.append(caught)
        after_main = main.step()
        after_auditor = auditor.step()
        assert "5MinerA" not in after_main and after_auditor == pytest.approx(after_main)
        assert auditor.last_divergence == pytest.approx(0.0, abs=1e-6)
    finally:
        main.close()
        auditor.close()
