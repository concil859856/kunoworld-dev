"""The owner's rule through the whole network, in both privacy modes: when the safety check inside the enclave blocks text
a model wrote there (an enhanced prompt, a plan's shot prompts) or the planner refuses a brief, the job fails as
`safety_blocked` and is refunded, and the customer gets no strike; a prompt of the customer's own that the enclave blocks
still strikes. A real gateway, the SDK, and a mock-TEE worker whose mock backend's enhancer and planner (its test hooks)
write what the check blocks."""

from __future__ import annotations

import threading

import httpx
import pytest
from kuno_protocol import devkit
from kuno_protocol.attestation import MockTEE
from kuno_protocol.canonical import b64d
from kuno_protocol.crypto import signing_key_from_bytes
from kuno_worker.backends.mock import MockBackend
from kuno_worker.config import WorkerConfig
from kuno_worker.worker import PROMPT_BLOCKED, Worker
from kunoworld import KunoError

FAST = "ltx-2.5-fast"
PROMPT = "A lighthouse keeper lights the lamp at dusk"
BRIEF = "A lighthouse keeper climbs the tower at dusk and lights the lamp as a storm rolls in."
BLOCKED = "a naked woman on a bed"  # the shared content policy's "sexual" category


def start_worker(network, backend: MockBackend) -> Worker:
    """Network.start_worker with a backend of this test's own."""
    quote_key = signing_key_from_bytes(b64d((network.data_dir / "mock_quote.key").read_text()))
    config = WorkerConfig(gateway_url=network.url, profiles=[FAST], image_digest=devkit.DEV_IMAGE_DIGEST, miner_hotkey="5MinerHotkey01",
                          miner_country="JP", pull_wait_s=1.0)
    worker = Worker(config, MockTEE(quote_key, devkit.DEV_IMAGE_DIGEST), {"*": backend})
    threading.Thread(target=worker.run, args=(network.stop,), daemon=True).start()
    assert worker.ready.wait(10), "worker failed to register"
    network.workers.append(worker)
    return worker


def standing(network) -> tuple[float, int]:
    """The dev account's balance and strikes in the last 24 h. It collects strikes, and is exempt from restrictions."""
    dev = {"authorization": f"Bearer {network.env['KUNO_DEV_API_KEY']}"}
    balance = httpx.get(f"{network.url}/v1/account", headers=dev).json()["balance_usd"]
    return balance, httpx.get(f"{network.url}/v1/account/eligibility", headers=dev).json()["strikes_24h"]


def refused(call) -> KunoError:
    with pytest.raises(KunoError) as exc:
        call()
    return exc.value


def test_model_written_text_the_enclave_blocks_is_refunded_without_a_strike_and_the_customers_own_strikes(network):
    start_worker(network, MockBackend(
        enhancer=lambda prompt: f"{prompt}, {BLOCKED}",
        plan_reply=lambda reply: reply.replace("The camera slowly pushes in.", f"{BLOCKED}."),
    ))
    before = standing(network)
    assert before[1] == 0
    with network.client("JP") as client:
        for privacy in ("private", "standard"):
            enhanced = refused(lambda: client.generate(PROMPT, model=FAST, duration_s=2, options={"enhance_prompt": True}, privacy=privacy,
                                                       timeout=60))
            # The customer sees what any blocked prompt gets; nothing says a model wrote it.
            assert (enhanced.code, enhanced.message) == ("safety_blocked", PROMPT_BLOCKED), privacy
            planned = refused(lambda: client.plan(BRIEF, target_s=12, privacy=privacy, timeout=60))
            assert planned.code == "safety_blocked", privacy
        assert standing(network) == before

        # The customer's own prompt, blocked inside the enclave (the gateway can't read a Private one): a strike.
        own = refused(lambda: client.generate(BLOCKED, model=FAST, duration_s=2, options={"enhance_prompt": True}, timeout=60))
        assert (own.code, own.message) == ("safety_blocked", PROMPT_BLOCKED)
    assert standing(network) == (before[0], 1)


def test_a_planner_that_refuses_a_brief_the_checks_passed_is_no_strike_in_either_mode(network):
    start_worker(network, MockBackend(plan_reply=lambda _reply: '{"refusal": "I can\'t plan this brief."}'))
    before = standing(network)
    with network.client("JP") as client:
        for privacy in ("private", "standard"):
            assert refused(lambda: client.plan(BRIEF, target_s=12, privacy=privacy, timeout=60)).code == "safety_blocked", privacy
    assert standing(network) == before
