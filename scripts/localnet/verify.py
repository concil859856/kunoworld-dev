"""Stage 0 check: do the validator's weights on chain include both miners?

Reads the subnet from the chain through bittensor 11.1.0 (the metagraph and the Weights storage), prints what it found
as JSON, and exits 0 only when the validator's serving weights (mechanism 0) give each miner a nonzero share. With
--wait it polls until they do or the time runs out.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import bittensor as bt

MINERS = ("miner-a", "miner-b")


def read(subtensor: Any, state: dict) -> dict[str, Any]:
    netuid = state["netuid"]
    graph = subtensor.subnets.metagraph(netuid, commitments=False)
    if graph is None:
        return {"ok": False, "netuid": netuid, "error": "the subnet does not exist on this chain (was the chain restarted?)"}
    by_hotkey = {neuron.hotkey: neuron for neuron in graph.neurons}
    names = {by_hotkey[keys["hotkey"]].uid: name for name, keys in state["neurons"].items() if keys["hotkey"] in by_hotkey}
    validator = by_hotkey.get(state["neurons"]["validator"]["hotkey"])
    mechanisms = int(subtensor.query(("SubtensorModule", "MechanismCountCurrent"), [netuid]) or 1)
    weights: dict[str, dict[str, float]] = {}
    for mechid in range(mechanisms):
        row = subtensor.read("weights", netuid=netuid, mechid=mechid).get(validator.uid, {}) if validator else {}
        weights[f"mechanism {mechid}"] = {names.get(uid, f"uid {uid}"): round(share, 6) for uid, share in sorted(row.items())}
    serving = weights.get("mechanism 0", {})
    missing = [miner for miner in MINERS if serving.get(miner, 0) <= 0]
    neurons = {
        name: {
            "uid": neuron.uid,
            "hotkey": neuron.hotkey,
            "validator_permit": neuron.validator_permit,
            "last_update": neuron.last_update,
            "incentive": round(neuron.incentive, 6),
            "dividends": round(neuron.dividends, 6),
            "collateral_locked": None if neuron.collateral_locked is None else str(neuron.collateral_locked),
        }
        for neuron in graph.neurons
        for name in [names.get(neuron.uid)]
        if name is not None
    }
    report: dict[str, Any] = {
        "ok": validator is not None and not missing,
        "block": graph.block,
        "netuid": netuid,
        "neurons": neurons,
        "validator_weights": weights,
    }
    if missing:
        report["missing"] = missing
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Check that the validator's on-chain weights include both miners.")
    parser.add_argument("--state", type=Path, required=True, help="state.json written by setup_chain.py")
    parser.add_argument("--wait", type=float, default=0.0, help="seconds to keep polling before giving up")
    args = parser.parse_args()
    state = json.loads(args.state.read_text())
    subtensor = bt.Subtensor(network=state["endpoint"])
    deadline, last = time.monotonic() + args.wait, None
    while True:
        try:
            report = read(subtensor, state)
        except Exception as exc:  # the chain is down or restarting
            report = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        if report["ok"] or time.monotonic() >= deadline:
            break
        progress = json.dumps(report.get("validator_weights") or report.get("error"))
        if progress != last:
            print(f"block {report.get('block', '?')}: validator weights {progress}", file=sys.stderr, flush=True)
            last = progress
        time.sleep(5)
    print(json.dumps(report, indent=2))
    if report["ok"]:
        print("OK: the validator's weights on chain include both miners", file=sys.stderr)
        return 0
    print(f"NOT OK: {report.get('error') or 'no weight for ' + ', '.join(report.get('missing', []))}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
