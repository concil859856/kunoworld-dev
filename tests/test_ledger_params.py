"""The validator ledger publishes each job's full params, so validators pay for signed durations, not the gateway's word."""

from __future__ import annotations

import httpx

from kuno_protocol.attestation import GoldenManifest
from kuno_protocol.canonical import b64d, canonical_json, sha256_hex
from kuno_validator.validator import Validator


def test_ledger_rows_carry_params_that_hash_to_the_signed_digest(network):
    network.start_worker(["ltx-2.5-fast"], hotkey="5MinerParams")
    with network.client("US") as client:
        client.generate("Harbour at dawn", model="ltx-2.5-fast", duration_s=2)

    headers = {"authorization": f"Bearer {network.env['KUNO_VALIDATOR_API_KEY']}"}
    rows = [r for r in httpx.get(f"{network.url}/validator/v1/ledger", headers=headers).json() if r["receipt"]]
    assert rows, "the finished job should be in the ledger"
    row = rows[-1]
    assert row["params"]["duration_s"] == 2
    assert sha256_hex(canonical_json(row["params"])) == row["receipt"]["body"]["params_digest"]

    manifest = GoldenManifest.model_validate_json((network.data_dir / "manifest.json").read_text())
    validator = Validator(network.url, network.env["KUNO_VALIDATOR_API_KEY"], manifest, b64d(network.env["KUNO_OWNER_PUBLIC_KEY"]))
    try:
        validator.score(validator.check_enclaves())
    finally:
        validator.close()
    assert validator.last_audit is not None and validator.last_audit.unbound == 0
