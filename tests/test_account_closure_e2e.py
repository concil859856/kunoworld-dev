"""Closing an account through the whole network: a customer signed in by email makes a Standard video on a real worker,
downloads a copy of their data (built by the gateway's background loop), closes the account with the typed address,
and is gone: sessions end, the stored video is deleted, the closure is logged and emailed, and the same address signs
in to a new, empty account."""

from __future__ import annotations

import io
import json
import time
import zipfile

import httpx
from test_owner_storage_e2e import OWNER, PROFILE, _blob_rows, _sign_in
from test_standard_mode_e2e import _params, _wait

from kuno_gateway.app import role_command
from kuno_gateway.settings import Settings

CUSTOMER = "grace@example.com"


def test_a_customer_exports_their_data_then_closes_the_account_end_to_end(network):
    network.start_worker([PROFILE])
    url = network.url
    assert role_command("grant-role", OWNER, "admin", Settings.from_env({"KUNO_DATA_DIR": str(network.data_dir)}))[0] == 0
    admin = _sign_in(network, OWNER)

    session = _sign_in(network, CUSTOMER)
    me = httpx.get(f"{url}/v1/me", headers=session).json()
    account_id, user_id = me["account"]["account_id"], me["user"]["user_id"]
    credit = httpx.post(f"{url}/admin/v1/accounts/{account_id}/credits",
                        json={"amount_usd": 20, "idempotency_key": "e2e-closure-credit"}, headers=admin)
    assert credit.status_code == 200
    customer = {**session, "x-kuno-country": "JP"}
    created = httpx.post(f"{url}/v1/standard/videos",
                         json={"params": _params([]).model_dump(mode="json"), "prompt": "a heron wading at dusk"}, headers=customer)
    assert created.status_code == 201, created.text
    job_id = created.json()["job_id"]
    assert _wait(url, customer, job_id)["status"] == "succeeded"
    video = httpx.get(f"{url}/v1/standard/videos/{job_id}/video", headers=customer).content
    assert _blob_rows(network, job_id)

    # A copy of the data: queued here, built by the gateway's background loop.
    assert httpx.post(f"{url}/v1/me/exports", headers=session).status_code == 202
    deadline = time.time() + 60
    while (listed := httpx.get(f"{url}/v1/me/exports", headers=session).json()[0])["status"] != "ready":
        assert listed["status"] in ("queued", "running") and time.time() < deadline, listed
        time.sleep(0.25)
    download = httpx.get(f"{url}/v1/me/exports/{listed['export_id']}/download", headers=session)
    archive = zipfile.ZipFile(io.BytesIO(download.content))
    assert archive.read(f"standard/{job_id}/video.mp4") == video
    assert json.loads(archive.read("account.json"))["user"]["email"] == CUSTOMER
    assert "7 days" in archive.read("README.txt").decode()

    # The session signed in moments ago, so the typed address is the last check.
    preview = httpx.get(f"{url}/v1/me/close", headers=session).json()
    assert preview["reauth_required"] is False
    assert httpx.post(f"{url}/v1/me/close", json={"confirm_email": "not-grace@example.com"}, headers=session).status_code == 422
    closed = httpx.post(f"{url}/v1/me/close", json={"confirm_email": CUSTOMER}, headers=session)
    assert closed.status_code == 200, closed.text
    assert (closed.json()["balance_policy"], closed.json()["retention_policy"]) == (
        "[BALANCE ON CLOSURE POLICY]", "[RETENTION OF RECORDS AFTER CLOSURE]"
    )

    assert httpx.get(f"{url}/v1/me", headers=session).status_code == 401
    assert httpx.get(f"{url}/v1/videos/{job_id}", headers=customer).status_code == 401
    assert _blob_rows(network, job_id) == []
    messages = [json.loads(p.read_text()) for p in sorted((network.data_dir / "outbox").iterdir())]
    assert any(m["to"] == CUSTOMER and m["subject"] == "Your KunoWorld account is closed" for m in messages)
    log = httpx.get(f"{url}/admin/v1/audit-log", params={"target_id": account_id}, headers=admin).json()
    assert [a["operator"] for a in log if a["action"] == "account.close"] == [f"owner:{user_id}"]
    record = httpx.get(f"{url}/admin/v1/accounts/{account_id}", headers=admin).json()
    assert record["name"] == "Closed account" and record["entries"]

    # The same address signs in to a new, empty account.
    again = _sign_in(network, CUSTOMER)
    fresh = httpx.get(f"{url}/v1/me", headers=again).json()
    assert fresh["account"]["account_id"] != account_id and fresh["account"]["balance_usd"] == 0
    assert httpx.get(f"{url}/v1/videos", headers=again).json() == []
