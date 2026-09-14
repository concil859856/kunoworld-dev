"""Paid customer jobs for the Stage 0 localnet, one per profile.

Only jobs a customer paid for earn job pay (VALIDATING.md, "Only paid jobs earn"), and a dev gateway's seeded balance
counts as paid. Canaries alone would leave every miner at zero weight. worker-a serves only ltx-2.5-fast and worker-b
only ltx-2.5-pro, so one job per profile lands one on each miner.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from kuno_protocol.attestation import GoldenManifest
from kunoworld import KunoClient

PROMPT = "A lighthouse on a cliff at dawn, waves rolling in"


def read_env(path: Path) -> dict[str, str]:
    pairs = (line.split("=", 1) for line in path.read_text().splitlines() if "=" in line and not line.startswith("#"))
    return {key.strip(): value.strip() for key, value in pairs}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--gateway", required=True)
    parser.add_argument("--data", type=Path, required=True, help="the gateway's data dir (its dev.env holds the dev API key)")
    parser.add_argument("--profile", action="append", required=True)
    parser.add_argument("--timeout", type=float, default=300.0, help="seconds to keep retrying each profile")
    args = parser.parse_args()

    env = read_env(args.data / "dev.env")
    manifest = GoldenManifest.model_validate_json(Path(env["KUNO_MANIFEST"]).read_text())
    with KunoClient(env["KUNO_DEV_API_KEY"], args.gateway, manifest=manifest, country="US") as client:
        for profile in args.profile:
            deadline = time.monotonic() + args.timeout
            while True:
                try:
                    video = client.generate(PROMPT, model=profile, duration_s=2, timeout=args.timeout)
                    break
                except Exception as exc:  # the worker hasn't registered yet (no capacity), or a job failed: try again
                    if time.monotonic() >= deadline:
                        print(f"{profile}: no paid job succeeded within {args.timeout:.0f}s: {exc}", file=sys.stderr)
                        return 1
                    print(f"{profile}: {type(exc).__name__}: {exc}; retrying", flush=True)
                    time.sleep(3)
            print(f"{profile}: paid job {video.job_id} served by {video.receipt.body.miner_hotkey}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
