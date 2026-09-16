"""Latency-bounded location on a real gateway: an H3 worker proves it runs outside the licence's excluded territories by
timing signed pings to the owner's landmarks from inside its VM; one that can't is refused H3; validators re-check the
published proof themselves."""

from __future__ import annotations

import threading
import time

from kuno_protocol.attestation import GoldenManifest
from kuno_protocol.canonical import b64d, b64e
from kuno_protocol.crypto import generate_signing_key, public_key_bytes, signing_key_from_bytes
from kuno_protocol.location import Landmark, LandmarkList, make_server, sign_landmarks
from kuno_validator.validator import Validator

from conftest import running_network


def landmark_network(tmp_path, clearance_km: float):
    """A landmark on loopback (well under a millisecond away) with the given clearance, and a gateway requiring proofs."""
    key = generate_signing_key()
    server = make_server("loopback-1", key, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    def configure(settings, data_dir):
        owner = signing_key_from_bytes(b64d((data_dir / "owner.key").read_text()))
        landmarks = LandmarkList(issued_at=int(time.time()), landmarks=[Landmark(
            id="loopback-1", url=f"http://127.0.0.1:{server.server_address[1]}", public_key=b64e(public_key_bytes(key)),
            latitude=35.68, longitude=139.69, clearance_km={"minimax-h3": clearance_km})])
        path = data_dir / "landmarks.json"
        path.write_text(sign_landmarks(owner, landmarks).model_dump_json())
        settings.landmarks_path = path
        settings.require_location_proof = True

    return server, running_network(tmp_path, configure)


def validator_for(network) -> Validator:
    manifest = GoldenManifest.model_validate_json((network.data_dir / "manifest.json").read_text())
    return Validator(network.url, network.env["KUNO_VALIDATOR_API_KEY"], manifest, b64d(network.env["KUNO_OWNER_PUBLIC_KEY"]),
                     role="auditor", spot_check_rate=0.0, require_location_proof=True)


def test_an_h3_worker_that_proves_its_location_registers_and_validators_agree(tmp_path):
    server, context = landmark_network(tmp_path, clearance_km=950.0)
    try:
        with context as network:
            worker = network.start_worker(["h3-turbo", "ltx-2.5-fast"], hotkey="5Near")
            validator = validator_for(network)
            try:
                (row,) = [e for e in validator.enclaves() if e["enclave_id"] == worker.identity.enclave_id]
                assert row["location"]["verdicts"]["minimax-h3"]["ok"] and row["location"]["verdicts"]["minimax-h3"]["radius_km"] < 950
                verdicts = validator.published_verdicts()
                assert verdicts[worker.identity.enclave_id].ok, verdicts[worker.identity.enclave_id].reasons
            finally:
                validator.close()
    finally:
        server.shutdown()


def test_an_h3_worker_whose_round_trips_cant_rule_out_excluded_territory_is_refused(tmp_path):
    # A clearance of 0.001 km can't be met by any real round trip: the proof is honest but too weak.
    server, context = landmark_network(tmp_path, clearance_km=0.001)
    try:
        with context as network:
            worker = network.start_worker(["h3-turbo"], hotkey="5Far", wait=False)
            assert not worker.ready.wait(4), "a worker without a sufficient location proof must not register for H3"
            ltx = network.start_worker(["ltx-2.5-fast"], hotkey="5LtxOnly")  # no territory-bound profile: no proof needed
            assert ltx.ready.is_set()
    finally:
        server.shutdown()
