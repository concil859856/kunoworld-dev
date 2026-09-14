"""The owner decisions through the whole network: operators bootstrapped from the CLI and signed in by email, a customer
who uses only the web session, videos kept until the owner deletes them (both modes), operators refused a video they
have no legal basis to open, the gateway's NSFW prompt check, and the shared admin token off by default."""

from __future__ import annotations

import json
import re

import httpx
from sqlalchemy import create_engine, text
from test_standard_mode_e2e import _params, _wait

from kuno_gateway.app import role_command
from kuno_gateway.db import NEVER_EXPIRES
from kuno_gateway.settings import Settings

PROFILE = "ltx-2.5-fast"
OWNER = "owner@kunoworld.test"
MODERATOR = "mo@kunoworld.test"
CUSTOMER = "ada@example.com"


def _sign_in(network, email: str) -> dict:
    """The website's server side of sign-in: request a link, follow it, keep the session."""
    assert httpx.post(f"{network.url}/v1/auth/magic-link", json={"email": email}).status_code == 202
    messages = [json.loads(p.read_text()) for p in sorted((network.data_dir / "outbox").iterdir())]
    link = [m for m in messages if m["to"] == email][-1]
    token = re.search(r"token=([A-Za-z0-9_\-]+)", link["text"]).group(1)
    verified = httpx.post(f"{network.url}/v1/auth/verify", json={"token": token})
    assert verified.status_code == 200, verified.text
    return {"authorization": f"Bearer {verified.json()['session_token']}"}


def _blob_rows(network, job_id: str) -> list[tuple[str, float]]:
    engine = create_engine(f"sqlite:///{network.data_dir / 'gateway.db'}")
    try:
        with engine.connect() as conn:
            return [tuple(r) for r in conn.execute(text("select id, expires_at from blobs where job_id = :j"), {"j": job_id}).all()]
    finally:
        engine.dispose()


def test_owner_only_storage_operators_by_email_and_sessions_end_to_end(network):
    network.start_worker([PROFILE])
    url = network.url

    # Operators: the first admin comes from the CLI; the shared admin token doesn't work unless break-glass is on.
    assert role_command("grant-role", OWNER, "admin", Settings.from_env({"KUNO_DATA_DIR": str(network.data_dir)}))[0] == 0
    assert httpx.get(f"{url}/admin/v1/reports", headers={"authorization": f"Bearer {network.env['KUNO_ADMIN_TOKEN']}"}).status_code == 403
    admin = _sign_in(network, OWNER)
    assert httpx.get(f"{url}/v1/me", headers=admin).json()["roles"] == ["admin"]
    assert httpx.post(f"{url}/admin/v1/roles", json={"email": MODERATOR, "role": "moderator"}, headers=admin).status_code == 201
    moderator = _sign_in(network, MODERATOR)

    # A customer signs in on the website; the site's server forwards the session for everything.
    session = _sign_in(network, CUSTOMER)
    account_id = httpx.get(f"{url}/v1/me", headers=session).json()["account"]["account_id"]
    credit = httpx.post(f"{url}/admin/v1/accounts/{account_id}/credits",
                        json={"amount_usd": 20, "idempotency_key": "e2e-welcome-1"}, headers=admin)
    assert credit.status_code == 200 and credit.json()["posted"] is True
    customer = {**session, "x-kuno-country": "JP"}
    assert httpx.post(f"{url}/v1/me/studio-token", headers=session).status_code == 410

    refused = httpx.post(f"{url}/v1/standard/videos", json={"params": _params([]).model_dump(mode="json"), "prompt": "nsfw"},
                         headers=customer)
    assert refused.status_code == 422 and refused.json()["detail"]["code"] == "content_policy"

    created = httpx.post(f"{url}/v1/standard/videos",
                         json={"params": _params([]).model_dump(mode="json"), "prompt": "a heron wading at dusk"}, headers=customer)
    assert created.status_code == 201, created.text
    standard_id = created.json()["job_id"]
    assert _wait(url, customer, standard_id)["status"] == "succeeded"
    video = httpx.get(f"{url}/v1/standard/videos/{standard_id}/video", headers=customer)
    assert video.status_code == 200 and video.content[4:8] == b"ftyp"
    assert httpx.get(f"{url}/v1/standard/videos", headers=customer).json()[0]["expires_at"] is None
    # Stored until the owner deletes it: the job's blobs carry no expiry, and the janitor (every 0.5 s here) leaves them.
    assert {expires for _, expires in _blob_rows(network, standard_id)} == {NEVER_EXPIRES}

    # A report that isn't child sexual abuse material gives operators metadata only.
    report = httpx.post(f"{url}/v1/reports", json={"job_id": standard_id, "reason": "harassment"}).json()
    item = next(i for i in httpx.get(f"{url}/admin/v1/moderation/queue", headers=moderator).json()
                if i["report"]["report_id"] == report["report_id"])
    assert item["content_reviewable"] is False and item["job"]["prompt"] is None
    blocked = httpx.get(f"{url}/admin/v1/moderation/items/{item['item_id']}/video", headers=moderator)
    assert blocked.status_code == 403 and blocked.json()["detail"]["code"] == "content_not_reviewable"
    # Moderators can't read the audit log; the admin sees who did what, by email, and no content views.
    assert httpx.get(f"{url}/admin/v1/audit-log", headers=moderator).status_code == 403
    log = httpx.get(f"{url}/admin/v1/audit-log", headers=admin).json()
    assert ("cli", "role.grant") in {(a["operator"], a["action"]) for a in log}
    assert (OWNER, "role.grant") in {(a["operator"], a["action"]) for a in log}
    assert not [a for a in log if a["action"].startswith("item.view_")]

    # A developer key made with the session runs a private job through the SDK; the owner deletes it with the session.
    api_key = httpx.post(f"{url}/v1/me/keys", json={"name": "e2e"}, headers=session).json()["key"]
    with network.client("JP", key=api_key) as client:
        result = client.generate("A harbour at dawn", model=PROFILE, duration_s=2)
    private_id = result.job_id
    output_blob = httpx.get(f"{url}/v1/videos/{private_id}", headers=customer).json()["output_blob_id"]
    assert httpx.get(f"{url}/v1/blobs/{output_blob}", headers={"authorization": f"Bearer {api_key}"}).status_code == 200
    assert all(expires == NEVER_EXPIRES for _, expires in _blob_rows(network, private_id))
    assert httpx.get(f"{url}/v1/me/keys", headers={"authorization": f"Bearer {api_key}"}).status_code == 401

    for job_id in (private_id, standard_id):
        assert httpx.delete(f"{url}/v1/videos/{job_id}", headers=customer).status_code == 204
    assert _blob_rows(network, private_id) == [] and _blob_rows(network, standard_id) == []
    assert not (network.data_dir / "blobs" / output_blob).exists()
    assert httpx.get(f"{url}/v1/blobs/{output_blob}", headers=customer).status_code == 404
    gone = httpx.get(f"{url}/v1/standard/videos/{standard_id}/video", headers=customer)
    assert gone.status_code == 410 and gone.json()["detail"]["code"] == "deleted"
    # The billing records stay.
    assert httpx.get(f"{url}/v1/videos/{private_id}", headers=customer).json()["price_usd"] > 0
