"""Plans through the whole network (PROTOCOL.md "Plans (Director)"): a real gateway routes plan jobs only to confidential
workers that registered `plan/1`, a mock-TEE worker writes, checks and seals the plan, the client opens it with its own
key (Private) or reads it from the gateway (Standard) and renders it as a storyboard, and the main validator's plan
canaries and ledger audit accept an honest worker's plans."""

from __future__ import annotations

import threading
import time
import uuid

import httpx
from kuno_protocol import devkit
from kuno_protocol.attestation import AttestationEvidence, GoldenManifest, MockTEE, verify_endorsed_evidence
from kuno_protocol.canonical import b64d, b64e, sha256_hex
from kuno_protocol.crypto import SenderSession, signing_key_from_bytes
from kuno_protocol.plans import PLAN_FEATURE, PLAN_OPTION, Plan, PlanOptions, open_plan, plan_context, validate
from kuno_protocol.profiles import Mode, load_profiles
from kuno_protocol.receipts import Receipt, verify_receipt
from kuno_protocol.schemas import GenerationParams, JobCreate, SealedPayload, job_aad
from kuno_protocol.sealed_payload import seal_payload
from kuno_validator.plan_canaries import FALLBACK_BRIEFS
from kuno_validator.validator import Validator
from kuno_worker.backends.mock import MockBackend
from kuno_worker.config import WorkerConfig
from kuno_worker.worker import Worker

FAST = load_profiles()["ltx-2.5-fast"]
BRIEF = "A lighthouse keeper climbs the tower at dusk and lights the lamp as a storm rolls in."
PARAMS = GenerationParams(profile_id=FAST.id, mode=Mode.PLAN, duration_s=12, resolution="720p", aspect_ratio="16:9", fps=24, audio=True)
EXACT = {"resolution": "720p", "aspect_ratio": "16:9", "fps": 24}


class NoPlanner(MockBackend):
    """A worker whose backend writes no plans, as every worker from before plans: it doesn't advertise `plan/1`."""

    plans = False


def start_worker_without_planner(network, hotkey: str = "5OldMiner") -> Worker:
    quote_key = signing_key_from_bytes(b64d((network.data_dir / "mock_quote.key").read_text()))
    config = WorkerConfig(gateway_url=network.url, profiles=[FAST.id], image_digest=devkit.DEV_IMAGE_DIGEST, miner_hotkey=hotkey,
                          miner_country="JP", pull_wait_s=1.0)
    worker = Worker(config, MockTEE(quote_key, devkit.DEV_IMAGE_DIGEST), {"*": NoPlanner()})
    threading.Thread(target=worker.run, args=(network.stop,), daemon=True).start()
    assert worker.ready.wait(10), "worker failed to register"
    network.workers.append(worker)
    return worker


def headers(network) -> dict:
    return {"authorization": f"Bearer {network.env['KUNO_DEV_API_KEY']}"}


def wait(network, job_id: str, timeout: float = 120) -> dict:
    deadline = time.time() + timeout
    while True:
        status = httpx.get(f"{network.url}/v1/videos/{job_id}", headers=headers(network)).json()
        if status["status"] in ("succeeded", "failed", "canceled"):
            return status
        assert time.time() < deadline, f"job still {status['status']}"
        time.sleep(0.3)


def plan_route(network, privacy: str = "private") -> httpx.Response:
    return httpx.get(f"{network.url}/v1/route", params={"mode": "plan", "profile_id": FAST.id, "privacy": privacy, **EXACT},
                     headers=headers(network))


def test_a_private_plan_is_sealed_to_a_planning_worker_and_opened_only_with_the_clients_key(network):
    network.start_worker([FAST.id])
    route = plan_route(network)
    assert route.status_code == 200, route.text
    enclave = route.json()["enclaves"][0]
    assert PLAN_FEATURE in enclave["features"] and enclave["tier"] == "confidential"
    manifest = GoldenManifest.model_validate_json((network.data_dir / "manifest.json").read_text())
    evidence = AttestationEvidence.model_validate(enclave["evidence"])
    assert verify_endorsed_evidence(evidence, manifest, enclave.get("endorsements")).ok

    session, job_id = SenderSession(b64d(enclave["hpke_public_key"])), str(uuid.uuid4())
    options = PlanOptions(style="storm light, 35mm")
    payload = SealedPayload(prompt=BRIEF, seed=5, options={PLAN_OPTION: options.model_dump(mode="json", exclude_none=True)})
    ciphertext = seal_payload(session, payload, job_aad(job_id, enclave["enclave_id"], PARAMS, []))
    job = JobCreate(job_id=job_id, params=PARAMS, enclave_id=enclave["enclave_id"], enc=b64e(session.enc), ciphertext=b64e(ciphertext))
    quoted = httpx.post(f"{network.url}/v1/quote", json={"profile_id": FAST.id, "mode": "plan", "duration_s": 12, **EXACT}).json()
    created = httpx.post(f"{network.url}/v1/plans", json=job.model_dump(mode="json"), headers=headers(network))
    assert created.status_code == 201, created.text
    assert created.json()["price_usd"] == quoted["price_usd"] == FAST.pricing.plan_usd

    status = wait(network, job_id)
    assert status["status"] == "succeeded", status
    receipt = Receipt.model_validate(status["receipt"])
    assert receipt.body.video is None and receipt.body.plan is not None
    assert verify_receipt(receipt, b64d(enclave["signing_public_key"]))

    sealed = httpx.get(f"{network.url}/v1/blobs/{status['output_blob_id']}", headers=headers(network)).content
    assert sha256_hex(sealed) == receipt.body.output_digest
    plan, data = open_plan(session.output_key, job_id, sealed)
    assert sha256_hex(data) == receipt.body.content_digest
    validate(plan, FAST, context=plan_context(FAST, PARAMS, options))
    assert (receipt.body.plan.shots, receipt.body.plan.duration_s) == (len(plan.shots), plan.duration_s)
    assert abs(plan.duration_s - 12) <= 0.5 and "lighthouse keeper" in plan.shots[0].prompt


def test_a_standard_plan_is_read_back_and_renders_as_a_standard_storyboard(network):
    network.start_worker([FAST.id])
    created = httpx.post(f"{network.url}/v1/standard/plans",
                         json={"params": PARAMS.model_dump(mode="json"), "brief": BRIEF, "seed": 9}, headers=headers(network))
    assert created.status_code == 201, created.text
    assert created.json()["price_usd"] == FAST.pricing.standard_plan_usd
    status = wait(network, created.json()["job_id"])
    assert status["status"] == "succeeded", status
    got = httpx.get(f"{network.url}/v1/standard/plans/{status['job_id']}", headers=headers(network))
    assert got.status_code == 200 and sha256_hex(got.content) == status["receipt"]["body"]["content_digest"]
    plan = Plan.model_validate_json(got.content)
    validator = {"authorization": f"Bearer {network.env['KUNO_VALIDATOR_API_KEY']}"}
    feed = httpx.get(f"{network.url}/validator/v1/standard-jobs/{status['job_id']}", headers=validator).json()
    assert (feed["prompt"], Plan.model_validate(feed["plan"])) == (BRIEF, plan)

    # The plan is a storyboard: its params and shot prompts go to the existing Standard video route.
    board = plan.storyboard_params()
    rendered = httpx.post(
        f"{network.url}/v1/standard/videos",
        json={"params": board.model_dump(mode="json"), "prompt": plan.scene, "shots": [{"prompt": shot.prompt} for shot in plan.shots]},
        headers=headers(network),
    )
    assert rendered.status_code == 201, rendered.text
    video = wait(network, rendered.json()["job_id"], timeout=240)
    assert video["status"] == "succeeded", video
    assert abs(video["receipt"]["body"]["video"]["duration_s"] - plan.duration_s) < 1e-3


def test_plans_never_reach_a_worker_without_a_planner(network):
    old = start_worker_without_planner(network)
    for privacy in ("private", "standard"):
        refused = plan_route(network, privacy)
        assert (refused.status_code, refused.json()["detail"]["code"]) == (503, "no_capacity"), privacy
    standard = httpx.post(f"{network.url}/v1/standard/plans", json={"params": PARAMS.model_dump(mode="json"), "brief": BRIEF},
                          headers=headers(network))
    assert (standard.status_code, standard.json()["detail"]["code"]) == (503, "no_capacity")
    quote = httpx.post(f"{network.url}/v1/quote", json={"profile_id": FAST.id, "mode": "plan", "duration_s": 12})
    assert (quote.status_code, quote.json()["detail"]["code"]) == (503, "no_capacity")
    # A client that seals to it anyway is refused before anything is charged.
    job = JobCreate(job_id=str(uuid.uuid4()), params=PARAMS, enclave_id=old.identity.enclave_id, enc="AAAA", ciphertext="AAAA")
    direct = httpx.post(f"{network.url}/v1/plans", json=job.model_dump(mode="json"), headers=headers(network))
    assert (direct.status_code, direct.json()["detail"]["code"]) == (409, "enclave_unavailable")
    videos = httpx.get(f"{network.url}/v1/route", params={"mode": "text_to_video", "profile_id": FAST.id}).json()
    assert [e["features"] for e in videos["enclaves"]] == [[]]

    planner = network.start_worker([FAST.id], hotkey="5NewMiner")
    assert [e["enclave_id"] for e in plan_route(network).json()["enclaves"]] == [planner.identity.enclave_id]


def test_the_main_validators_plan_canaries_and_ledger_audit_accept_an_honest_worker(network):
    network.start_worker([FAST.id])
    manifest = GoldenManifest.model_validate_json((network.data_dir / "manifest.json").read_text())
    validator = Validator(network.url, network.env["KUNO_VALIDATOR_API_KEY"], manifest, b64d(network.env["KUNO_OWNER_PUBLIC_KEY"]))
    try:
        # Private, before any challenge this round: the route's published evidence is verified instead.
        validator.plan_briefs = [FALLBACK_BRIEFS[4]]
        private = validator.run_plan_canary(FAST.id, "private", sleep=lambda _s: time.sleep(0.3))
        assert private.ok and private.attributable and private.miner_hotkey == "5MinerHotkey01", private.detail
        verdicts = validator.check_enclaves()
        validator.plan_briefs = [FALLBACK_BRIEFS[2]]
        standard = validator.run_plan_canary(FAST.id, "standard", sleep=lambda _s: time.sleep(0.3))
        assert standard.ok and standard.attributable, standard.detail
        assert validator.canary_penalties(time.time(), 3600) == {}

        validator.score(verdicts)
        plans = [e for e in validator.last_audit.entries if e["job_id"] in (private.job_id, standard.job_id)]
        assert len(plans) == 2 and all(e["credit"] and e["plan"] and e["billable_s"] == 0.0 for e in plans)
        assert validator.last_audit.dropped_total == 0
    finally:
        validator.close()
