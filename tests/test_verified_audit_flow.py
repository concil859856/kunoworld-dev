"""Verified mode end to end in one process: a mock-backend enclave commits to every step and
retains the trajectory encrypted, the gateway relays a validator's audit (and refuses one on a
job the validator did not create), the enclave answers from retention through its signed miner
API, and the validator re-executes the step bit for bit."""

from __future__ import annotations

import json
import random
import time
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from kuno_gateway import api_audits
from kuno_gateway.app import create_app
from kuno_gateway.db import Enclave, Job
from kuno_gateway.settings import Settings
from kuno_protocol import devkit
from kuno_protocol.canonical import b64e, canonical_json, sha256_hex
from kuno_protocol.profiles import Mode, load_profiles
from kuno_protocol.receipts import ReceiptBody, VideoInfo, sign_receipt
from kuno_protocol.toy_denoiser import toy_conditioning, toy_noise, toy_state, toy_step, toy_weights
from kuno_protocol.verified import f64_value
from kuno_validator.audits import AuditOutcome, AuditPolicy, Auditor, CanaryRecord, PendingAudit
from kuno_validator.ledger import EnclaveKey
from kuno_worker.audits import AuditCalls, AuditResponder
from kuno_worker.backends.mock import MockBackend
from kuno_worker.gateway_client import GatewayClient
from kuno_worker.identity import EnclaveIdentity
from kuno_worker.plan import build_task, example_task
from kuno_worker.verified import RetentionStore

PROFILE = load_profiles()["ltx-2.5-fast"]


class Clock:
    def __init__(self):
        self.t = time.time()

    def __call__(self):
        return self.t


class CheatsAtStepFour(MockBackend):
    def trajectory(self, transcript, task):
        stage = transcript.stages[0]
        sigmas = [f64_value(s) for s in stage.sigmas]
        honest, cheap = toy_weights(transcript.model_digest), toy_weights("f" * 64)
        cond = toy_conditioning(task.prompt, task.negative_prompt)
        x = toy_noise(transcript.seed, stage.tensors[0])
        yield 0, 0, "init", sigmas[0], toy_state(x)
        for i in range(1, len(sigmas)):
            x = toy_step(x, sigmas[i - 1], sigmas[i], cond, cheap if i == 4 else honest)
            yield i, 0, "denoise", sigmas[i], toy_state(x)


@pytest.fixture
def world(tmp_path):
    env = devkit.init(tmp_path / "data")
    app = create_app(Settings.from_env({"KUNO_DATA_DIR": str(tmp_path / "data")}))
    app.include_router(api_audits.router)
    http = TestClient(app)
    identity = EnclaveIdentity.generate()
    now = time.time()
    with app.state.gw.session() as s, s.begin():
        s.add(
            Enclave(
                id=identity.enclave_id, miner_hotkey="5Miner", tee="mock", image_digest=devkit.DEV_IMAGE_DIGEST,
                hpke_public_key=b64e(identity.hpke_public), signing_public_key=b64e(identity.signing_public),
                profiles=json.dumps([PROFILE.id]), hardware="{}", evidence="{}", capacity=1, inflight=0, status="active",
                verified_at=now, last_seen=now,
            )
        )
    clock = Clock()
    store = RetentionStore(window_s=3600, clock=clock)
    validator_auth = {"authorization": f"Bearer {env['KUNO_VALIDATOR_API_KEY']}"}
    auditor = Auditor(
        lambda method, path, **kw: http.request(method, path, headers=validator_auth, **kw),
        load_profiles(),
        lambda eid: EnclaveKey(identity.enclave_id, "5Miner", identity.signing_public) if eid == identity.enclave_id else None,
        policy=AuditPolicy(rate=1.0, full_rerun_rate=0.0),
        rng=random.Random(5),
    )
    calls = AuditCalls(GatewayClient("http://testserver", identity.signing_key, identity.enclave_id, transport=http._transport))
    return SimpleNamespace(
        app=app, tmp=tmp_path, identity=identity, store=store, clock=clock, auditor=auditor, calls=calls,
        responder=AuditResponder(identity, store),
    )


def run_job(world, backend: MockBackend, account_id: str, seed: int = 9, prompt: str = "A potter shapes wet clay") -> CanaryRecord:
    """What worker.process() does in verified mode: generate, then sign the commitment into the receipt."""
    params = example_task(PROFILE, Mode.TEXT_TO_VIDEO)
    job_id = str(uuid.uuid4())
    task = build_task(PROFILE, params, world.tmp, seed=seed, prompt=prompt, job_id=job_id)
    commitment, _ = backend.verified_trajectory(task)
    now = time.time()
    body = ReceiptBody(
        job_id=job_id, enclave_id=world.identity.enclave_id, profile_id=PROFILE.id, image_digest=devkit.DEV_IMAGE_DIGEST,
        params_digest=sha256_hex(canonical_json(params.model_dump(mode="json"))), input_digest="0" * 64, output_digest="1" * 64,
        output_bytes=1, content_digest=sha256_hex(job_id.encode()), attestation_digest="3" * 64, started_at=now - 5, finished_at=now,
        gpu_seconds=5.0, video=VideoInfo(duration_s=2, width=1280, height=704, fps=24, frames=49, audio=True), miner_hotkey="5Miner",
        step_commitment=commitment,
    )
    receipt = sign_receipt(world.identity.signing_key, body)
    with world.app.state.gw.session() as s, s.begin():
        s.add(
            Job(
                id=job_id, account_id=account_id, profile_id=PROFILE.id, enclave_id=world.identity.enclave_id,
                params=params.model_dump_json(), enc="", ciphertext="", input_blob_ids="[]", status="succeeded", price_usd=0.0,
                receipt=receipt.model_dump_json(), created_at=now - 6, updated_at=now, finished_at=now,
            )
        )
    return CanaryRecord(job_id, PROFILE.id, params.model_dump(mode="json"), prompt, seed, receipt.model_dump(mode="json"))


def answer_pending(world) -> None:
    for item in world.calls.pull():
        world.responder.handle(item, world.calls)


def test_a_validator_audits_its_own_canary_through_the_gateway(world):
    canary = run_job(world, MockBackend(retention=world.store), "validator")
    pending = world.auditor.request(canary, step=4, include_leaves=True)
    assert isinstance(pending, PendingAudit)
    assert world.auditor.poll() == []  # the enclave has not answered yet
    answer_pending(world)
    (outcome,) = world.auditor.poll()
    assert outcome.ok, outcome.detail
    assert "step 4 re-executed bitwise" in outcome.detail and "full re-run matches" in outcome.detail


def test_a_substituted_step_is_caught_and_zeroes_the_miner(world):
    canary = run_job(world, CheatsAtStepFour(retention=world.store), "validator")
    world.auditor.request(canary, step=4)
    answer_pending(world)
    (outcome,) = world.auditor.poll()
    assert not outcome.ok and outcome.attributable and "step 4" in outcome.detail
    assert list(world.auditor.penalties(time.time(), 86400)) == ["5Miner"]


def test_a_job_the_validator_did_not_create_is_never_opened(world):
    customer_job = run_job(world, MockBackend(retention=world.store), "dev")
    outcome = world.auditor.request(customer_job, step=2)
    assert isinstance(outcome, AuditOutcome)
    assert not outcome.ok and not outcome.attributable and "403" in outcome.detail
    assert world.calls.pull() == []  # nothing ever reached the enclave


def test_gpu_executors_agree_with_the_worker_on_schedules_and_transcripts(world, monkeypatch):
    """The GPU paths can't run here, but their step selection and transcript checks can."""
    import numpy as np

    from kuno_protocol import torch_verified
    from kuno_protocol.verified import StepCommitment
    from kuno_validator.executors import LTX_DISTILLED_SIGMAS, LtxStepExecutor
    from kuno_worker.backends.ltx_resident import DISTILLED_SIGMAS, LtxResidentBackend

    assert DISTILLED_SIGMAS == LTX_DISTILLED_SIGMAS
    pins = PROFILE.verified.determinism.model_dump(mode="json")
    monkeypatch.setattr(torch_verified, "apply_determinism", lambda settings: {**pins, "torch": "2.x"})

    def pipeline(**call):
        tap = call["kuno_trajectory_tap"]
        for steps in PROFILE.verified.stage_steps:
            x = np.ones((1, 8, 4), dtype=np.float32)
            tap.begin_stage([1.0 - i / steps for i in range(steps)] + [0.0], {"video": x})
            for i in range(steps):
                x = x * np.float32(0.5)
                tap.end_step(i, {"video": x})
        return {"videos": [[np.zeros((16, 16, 3), dtype=np.uint8)] * 4], "audio": None}

    hw = "C1.rtx-pro-6000-bw-se.x1"
    backend = LtxResidentBackend(None, world.tmp, loader=lambda _p: pipeline, hardware_class=hw, retention=world.store, model_digest="d" * 64)
    canary = run_job(world, MockBackend(retention=world.store), "validator")  # only for its params/prompt/seed
    params = example_task(PROFILE, Mode.TEXT_TO_VIDEO, audio=False)
    task = build_task(PROFILE, params, world.tmp, seed=canary.seed, prompt=canary.prompt, job_id=str(uuid.uuid4()))
    result = backend.generate(task, lambda _v, _s: None)
    transcript = world.store.record(task.job_id).transcript

    executor = LtxStepExecutor(loader=lambda _p: None, hardware_class=hw, model_digests={PROFILE.id: "d" * 64})
    assert executor.candidate_steps(result.step_commitment, PROFILE) == list(range(1, 9))  # stage 0 only
    other = StepCommitment(**{**result.step_commitment.model_dump(), "hardware_class": "C2.h200-141gb.x1"})
    assert executor.candidate_steps(other, PROFILE) == []
    assert executor.check_transcript(transcript, canary, PROFILE) is None
    wrong_weights = LtxStepExecutor(loader=lambda _p: None, hardware_class=hw, model_digests={PROFILE.id: "f" * 64})
    assert "model_digest" in wrong_weights.check_transcript(transcript, canary, PROFILE)
    unpinned = transcript.model_copy(update={"determinism": {**transcript.determinism, "allow_tf32": True}})
    assert "determinism" in executor.check_transcript(unpinned, canary, PROFILE)


def test_an_audit_after_the_retention_window_is_the_miners_failure(world):
    canary = run_job(world, MockBackend(retention=world.store), "validator")
    world.clock.t += 3601  # the enclave's retention window passes (the gateway's own check uses real time)
    assert isinstance(world.auditor.request(canary, step=3), PendingAudit)
    answer_pending(world)
    (outcome,) = world.auditor.poll()
    assert not outcome.ok and outcome.attributable and "not_retained" in outcome.detail
    assert canary.job_id not in world.store
