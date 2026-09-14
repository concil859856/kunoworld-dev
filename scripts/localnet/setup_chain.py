"""Chain setup for the Stage 0 localnet: wallets, funding, the subnet and its hyperparameters, neurons, stake, collateral.

Run by localnet.sh inside the localnet's chain venv (bittensor 11.1.0 as uv.lock pins it). Wallets are made with the
SDK; every transaction goes through btcli ($KUNO_LOCALNET_BTCLI, bittensor 11.1.0's btcli), so the commands MINING.md
and VALIDATING.md document are the ones exercised. Writes <data>/state.json for the services and verify.py.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

import bittensor as bt
from bittensor import wallets
from kuno_protocol.hotkey import Sr25519Signer

# //Alice's sr25519 mini-secret: the dev account every localnet funds with 1,000,000 TAO, and the chain's sudo key.
ALICE_SEED = "0xe5be9a5092b81bca64be81d212e7f2f9eba183bb7a90954f7b76361f6edb5c0a"
NEURONS = ("owner", "validator", "miner-a", "miner-b")
MINERS = ("miner-a", "miner-b")
FUNDING_TAO = {"validator": 300, "miner-a": 100, "miner-b": 100}  # the owner gets the subnet creation cost plus 100
VALIDATOR_STAKE_TAO = 100
LOCK_SHARE = 39321  # 0.6 of the registration price locked as collateral, VALIDATING.md's recommendation
U64F64_ONE = 2**64

# MEV-shielded extrinsics (burned_register and add_collateral must be shielded) are encrypted to a recent block's
# MevShield key and signed against a recent era. At 250 ms blocks both often move before inclusion: the pool answers
# with one of these names, or the shield decrypts the extrinsic after its era ran out (matched by message). The
# extrinsic was not included either way, so resubmitting is safe.
SHIELD_RETRY = frozenset({"BadProof", "Invalid", "AncientBirthBlock", "Stale", "Future", "not included before its era expired"})
# The runtime caps MaxAllowedUids x mechanism count at this (TooManyUIDsPerMechanism).
MAX_UIDS_ACROSS_MECHANISMS = 256
# Owner hyperparameter changes are refused inside the admin freeze window before each epoch. A new localnet subnet has a
# 10-block tempo and a 10-block window, so a change lands only in the block right after an epoch.
TOO_EARLY = frozenset({"AdminActionProhibitedDuringWeightsWindow", "too_early", "rate_limited"})


class SetupError(RuntimeError):
    pass


def log(message: str = "") -> None:
    print(message, flush=True)


def _tao(amount: float) -> str:
    return f"{amount:.9f}".rstrip("0").rstrip(".")


def _parse(stdout: str) -> Any:
    """The JSON document btcli --json printed (anything before it, such as a notice, is skipped)."""
    lines = stdout.strip().splitlines()
    for index, line in enumerate(lines):
        if line.lstrip().startswith(("{", "[")):
            try:
                return json.loads("\n".join(lines[index:]))
            except json.JSONDecodeError:
                continue
    return None


def _matches(retry: frozenset[str], name: str | None, code: str | None, message: str) -> bool:
    """An error name or code in `retry`, or a message containing one of its phrases."""
    return name in retry or code in retry or any(" " in phrase and phrase in message for phrase in retry)


def _error(answer: Any) -> tuple[str | None, str | None, str]:
    """(name, code, message) of a failed btcli --json answer."""
    if not isinstance(answer, dict):
        return None, None, ""
    error = answer.get("error")
    if isinstance(error, dict):
        return error.get("name"), error.get("code"), str(error.get("message") or answer.get("message") or "")
    if isinstance(error, str):
        return None, None, f"{error} {answer.get('help') or ''}".strip()
    return None, None, str(answer.get("message") or "")


class Btcli:
    def __init__(self, command: str, endpoint: str, wallet_path: Path):
        self.command, self.endpoint, self.wallet_path = shlex.split(command), endpoint, wallet_path

    def available(self, *group: str) -> bool:
        return subprocess.run([*self.command, *group, "--help"], capture_output=True, timeout=300).returncode == 0

    def version(self) -> str:
        out = subprocess.run([*self.command, "--version"], capture_output=True, text=True, timeout=300).stdout.strip()
        return out.splitlines()[-1] if out else "unknown"

    def run(
        self,
        *args: Any,
        write: bool = True,
        retry: frozenset[str] = frozenset(),
        attempts: int = 1,
        pause: float = 3.0,
        check: bool = True,
    ) -> Any:
        """One btcli command with --json. A write succeeds when btcli says so; anything named in `retry` is resubmitted."""
        argv = [*self.command, *map(str, args), "--network", self.endpoint, "--wallet-path", str(self.wallet_path), "--json"]
        if write:
            argv.append("-y")
        label = " ".join(map(str, args[:2]))
        detail, name, code, message = "", None, None, ""
        for attempt in range(1, attempts + 1):
            try:
                proc = subprocess.run(argv, capture_output=True, text=True, timeout=300)
                answer, stderr, returncode = _parse(proc.stdout), proc.stderr, proc.returncode
            except subprocess.TimeoutExpired:
                answer, stderr, returncode = None, "btcli timed out after 300 s", -1
            if write and isinstance(answer, dict) and answer.get("success") is True:
                return answer
            if not write and returncode == 0 and answer is not None:
                return answer
            name, code, message = _error(answer)
            detail = f"{name or code or 'failed'}: {message or stderr.strip()[-400:]}"
            if _matches(retry, name, code, message) and attempt < attempts:
                log(f"    {label}: {name or code or message[:80]}, resubmitting ({attempt}/{attempts})")
                time.sleep(pause)
                continue
            break
        if check:
            raise SetupError(f"btcli {' '.join(map(str, args))} -> {detail}")
        return {"success": False, "error": detail, "name": name, "code": code, "message": message}


class Chain:
    """Reads through the SDK (bittensor 11.1.0)."""

    def __init__(self, endpoint: str):
        self.subtensor = bt.Subtensor(network=endpoint)

    def storage(self, name: str, params: list | tuple = (), pallet: str = "SubtensorModule") -> tuple[bool, Any]:
        """(True, value), or (False, why) when the runtime has no such storage item."""
        try:
            return True, self.subtensor.query((pallet, name), list(params))
        except Exception as exc:  # an unknown storage item, most likely
            return False, f"{type(exc).__name__}: {exc}"

    def uid(self, netuid: int, hotkey: str) -> int | None:
        ok, value = self.storage("Uids", [netuid, hotkey])
        return int(value) if ok and value is not None else None


def _bits(value: Any) -> int:
    return int(value.get("bits") or 0) if isinstance(value, dict) else int(value or 0)


def _seed(path: Path) -> str:
    if not path.exists():
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as handle:
            handle.write("0x" + secrets.token_hex(32) + "\n")
    return path.read_text().strip()


def make_wallets(data: Path) -> dict[str, dict[str, Any]]:
    """alice (the dev account) and owner, validator, miner-a and miner-b, each regenerated from seeds kept in <data>/seeds.

    A miner's hotkey seed file is what its worker reads as KUNO_HOTKEY_SEED_FILE. The worker's sr25519 key from that
    seed is checked against the wallet hotkey, so the enclave proves the same hotkey the chain registers."""
    wallet_path, seeds = data / "wallets", data / "seeds"
    wallet_path.mkdir(parents=True, exist_ok=True)
    seeds.mkdir(mode=0o700, parents=True, exist_ok=True)
    wallets.regen_coldkey(seed=ALICE_SEED, name="alice", path=str(wallet_path), use_password=False, overwrite=True)
    found: dict[str, dict[str, Any]] = {}
    for name in NEURONS:
        coldkey = wallets.regen_coldkey(
            seed=_seed(seeds / f"{name}.coldkey.seed"), name=name, path=str(wallet_path), use_password=False, overwrite=True
        )
        seed_file = seeds / f"{name}.hotkey.seed"
        seed = _seed(seed_file)
        hotkey = wallets.regen_hotkey(seed=seed, name=name, hotkey="default", path=str(wallet_path), overwrite=True).hotkey
        enclave = Sr25519Signer.from_seed(bytes.fromhex(seed.removeprefix("0x"))).ss58_address
        if enclave != hotkey.ss58_address:
            raise SetupError(f"{name}: a worker with this seed would sign as {enclave}, but the wallet hotkey is {hotkey.ss58_address}")
        found[name] = {"coldkey": coldkey.coldkeypub.ss58_address, "hotkey": hotkey.ss58_address, "hotkey_seed_file": str(seed_file)}
    return found


def owner_set(btcli: Btcli, netuid: int, name: str, value: Any, check: bool = True) -> bool:
    answer = btcli.run(
        "sudo", "set", "-w", "owner", "--netuid", netuid, "--name", name, "--value", value, retry=TOO_EARLY, attempts=60, pause=1.0, check=check
    )
    ok = answer.get("success") is True
    log(f"  btcli sudo set --name {name} --value {value}: {'ok' if ok else answer['error']}")
    return ok


def register(btcli: Btcli, chain: Chain, netuid: int, name: str, hotkey: str, attempts: int = 40) -> int:
    """btcli tx burned-register, resubmitted while the shielded extrinsic misses its block; done once the hotkey has a UID."""
    detail = ""
    for attempt in range(1, attempts + 1):
        uid = chain.uid(netuid, hotkey)
        if uid is not None:
            return uid
        answer = btcli.run("tx", "burned-register", "-w", name, "-H", "default", "--netuid", netuid, check=False)
        if answer.get("success") is True:
            for _ in range(40):
                uid = chain.uid(netuid, hotkey)
                if uid is not None:
                    return uid
                time.sleep(0.5)
            continue
        detail = answer["error"]
        if not _matches(SHIELD_RETRY, answer["name"], answer["code"], answer["message"]):
            raise SetupError(f"btcli tx burned-register -w {name} -> {detail}")
        log(f"    burned-register {name}: {answer['name'] or answer['message'][:80]}, resubmitting ({attempt}/{attempts})")
        time.sleep(1.0)
    raise SetupError(f"btcli tx burned-register -w {name} never landed: {detail}")


def wait_for_permit(chain: Chain, netuid: int, uid: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        ok, permits = chain.storage("ValidatorPermit", [netuid])
        if ok and isinstance(permits, (list, tuple)) and uid < len(permits) and permits[uid]:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(2)


def setup(args: argparse.Namespace, command: str) -> dict[str, Any]:
    data: Path = args.data
    chain = Chain(args.endpoint)
    btcli = Btcli(command, args.endpoint, data / "wallets")
    state: dict[str, Any] = {
        "endpoint": args.endpoint,
        "spec_version": chain.subtensor.spec_version,
        "bittensor": bt.__version__,
        "btcli": btcli.version(),
        "wallet_path": str(data / "wallets"),
    }
    log(f"chain {args.endpoint}: runtime spec {state['spec_version']}, block {chain.subtensor.block}")
    log(f"SDK bittensor {state['bittensor']}, {state['btcli']}")

    log("\n1. wallets (in the scratch wallet dir; seeds in <data>/seeds)")
    neurons = make_wallets(data)
    for name, keys in neurons.items():
        log(f"  {name:9} coldkey {keys['coldkey']}  hotkey {keys['hotkey']}")

    log("\n2. funding from //Alice")
    create_cost = float(btcli.run("subnets", "create-cost", write=False)["tao"])
    for name, tao in {"owner": create_cost + 100, **FUNDING_TAO}.items():
        btcli.run("tx", "transfer", "-w", "alice", "--dest", neurons[name]["coldkey"], "--amount", _tao(tao), retry=SHIELD_RETRY, attempts=3)
        log(f"  {name}: {_tao(tao)} TAO")

    log(f"\n3. subnet (creation cost {_tao(create_cost)} TAO)")
    netuid = int(btcli.run("tx", "register-subnet", "-w", "owner", "-H", "default")["data"]["netuid"])
    state["netuid"] = netuid
    log(f"  btcli tx register-subnet: netuid {netuid}")
    btcli.run("tx", "start-call", "-w", "owner", "--netuid", netuid, retry=TOO_EARLY, attempts=60, pause=2.0)
    log("  btcli tx start-call: active (epochs run, alpha trades)")
    ok, enabled = chain.storage("SubnetEmissionEnabled", [netuid])
    if not ok:
        state["emission_enabled"] = f"not in this runtime ({enabled})"
    else:
        if not enabled:
            btcli.run("tx", "set-subnet-emission-enabled", "-w", "alice", "--netuids", netuid, "--enabled")
            log("  btcli tx set-subnet-emission-enabled as root (//Alice)")
            enabled = chain.storage("SubnetEmissionEnabled", [netuid])[1]
        state["emission_enabled"] = bool(enabled)
    log(f"  TAO emission share enabled: {state['emission_enabled']}")

    log("\n4. hyperparameters")
    ok_share, share = chain.storage("CollateralLockShare", [netuid])
    ok_ratio, ratio = chain.storage("CollateralDrainRatio", [netuid])
    collateral: dict[str, Any] = {"supported": ok_share and ok_ratio}
    if collateral["supported"]:
        # Before any miner registers: each registration snapshots the policy.
        if int(share or 0) != LOCK_SHARE:
            owner_set(btcli, netuid, "collateral_lock_share", LOCK_SHARE)
        if _bits(ratio) != U64F64_ONE:
            owner_set(btcli, netuid, "collateral_drain_ratio", "1.0")
        else:
            log("  collateral_drain_ratio is already 1.0 (the runtime default)")
        share, ratio = chain.storage("CollateralLockShare", [netuid])[1], chain.storage("CollateralDrainRatio", [netuid])[1]
        collateral.update(lock_share=int(share), lock_share_fraction=round(int(share) / 65535, 4), drain_ratio=_bits(ratio) / U64F64_ONE)
        log(f"  collateral: lock share {collateral['lock_share']} ({collateral['lock_share_fraction']}), drain ratio {collateral['drain_ratio']}")
    else:
        collateral["reason"] = f"no CollateralLockShare/CollateralDrainRatio storage: {share if not ok_share else ratio}"
        log(f"  WARNING: this runtime has no registration collateral ({collateral['reason']}); collateral steps are skipped")
    state["collateral"] = collateral

    ok, reveal = chain.storage("CommitRevealWeightsEnabled", [netuid])
    if ok and reveal and not args.commit_reveal:
        # Timelocked commits reveal only when the chain has drand pulses; plain weights keep Stage 0 independent of drand.
        owner_set(btcli, netuid, "commit_reveal_weights_enabled", "false")
        reveal = chain.storage("CommitRevealWeightsEnabled", [netuid])[1]
    state["commit_reveal_enabled"] = bool(reveal) if ok else None
    log(f"  commit-reveal weights: {state['commit_reveal_enabled']}")

    ok, count = chain.storage("MechanismCountCurrent", [netuid])
    count = int(count) if ok and count is not None else 1
    if args.mechanisms > count:
        # KunoWorld runs two mechanisms, and the runtime refuses more than 256 UIDs across them: a new subnet's 256 UIDs
        # have to come down first (on mainnet too).
        limit = MAX_UIDS_ACROSS_MECHANISMS // args.mechanisms
        ok_uids, max_uids = chain.storage("MaxAllowedUids", [netuid])
        if ok_uids and int(max_uids or 0) > limit:
            owner_set(btcli, netuid, "max_allowed_uids", limit, check=False)
        answer = btcli.run(
            "tx", "set-mechanism-count", "-w", "owner", "--netuid", netuid, "--mechanism-count", args.mechanisms,
            retry=TOO_EARLY, attempts=60, pause=1.0, check=False,
        )
        if answer.get("success") is True:
            count = int(chain.storage("MechanismCountCurrent", [netuid])[1] or count)
        else:
            log(f"  WARNING: could not run {args.mechanisms} mechanisms: {answer['error']}")
    state["mechanism_count"] = count
    log(f"  mechanisms: {count} (0 serving, 1 Turbo)")

    log("\n5. neurons (btcli tx burned-register)")
    for name in ("validator", *MINERS):
        neurons[name]["uid"] = register(btcli, chain, netuid, name, neurons[name]["hotkey"])
        log(f"  {name}: uid {neurons[name]['uid']}")
    neurons["owner"]["uid"] = chain.uid(netuid, neurons["owner"]["hotkey"])

    log(f"\n6. stake {VALIDATOR_STAKE_TAO} TAO on the validator (btcli tx add-stake)")
    # add_stake need not be shielded, and a new subnet's pool is too thin for the default 5% slippage protection.
    btcli.run(
        "tx", "add-stake", "-w", "validator", "--hotkey", neurons["validator"]["hotkey"], "--netuid", netuid,
        "--amount", VALIDATOR_STAKE_TAO, "--no-mev-shield", "--no-slippage-protection", retry=SHIELD_RETRY, attempts=5,
    )
    log("  ok")

    log(f"\n7. miner collateral, {args.collateral_alpha} alpha each (btcli collateral add / set-min)")
    has_commands = btcli.available("collateral")
    for name in MINERS:
        entry: dict[str, Any] = {}
        if not collateral["supported"]:
            entry["skipped"] = "the runtime has no registration collateral"
        elif not has_commands:
            entry["skipped"] = f"{state['btcli']} has no collateral commands"
        else:
            common = ("-w", name, "-H", "default", "--netuid", netuid)
            added = btcli.run("collateral", "add", *common, "--amount-alpha", args.collateral_alpha, retry=SHIELD_RETRY, attempts=40, pause=1.0, check=False)
            entry["add"] = "ok" if added.get("success") is True else added["error"]
            floor = btcli.run("collateral", "set-min", *common, "--min-alpha", args.collateral_alpha, retry=SHIELD_RETRY, attempts=5, check=False)
            entry["set_min"] = "ok" if floor.get("success") is True else floor["error"]
            shown = btcli.run("collateral", "show", *common, write=False, check=False)
            entry["position"] = shown.get("collateral") if isinstance(shown, dict) else None
        neurons[name]["collateral"] = entry
        log(f"  {name}: {json.dumps(entry)}")

    log("\n8. validator permit")
    state["validator_permit"] = wait_for_permit(chain, netuid, neurons["validator"]["uid"], timeout=120)
    log(f"  validator holds a permit: {state['validator_permit']}")
    state["neurons"] = neurons
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description="Chain setup for the Stage 0 localnet (run by localnet.sh up).")
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--collateral-alpha", default="2", help="alpha each miner adds and keeps as its floor")
    parser.add_argument("--mechanisms", type=int, default=2, help="mechanisms to run (1 skips Turbo)")
    parser.add_argument("--commit-reveal", action="store_true", help="leave commit-reveal weights on (reveals need drand pulses)")
    args = parser.parse_args()
    command = os.environ.get("KUNO_LOCALNET_BTCLI")
    if not command:
        parser.error("KUNO_LOCALNET_BTCLI is not set (localnet.sh sets it)")
    try:
        state = setup(args, command)
    except SetupError as exc:
        log(f"\nchain setup failed: {exc}")
        return 1
    (args.data / "state.json").write_text(json.dumps(state, indent=2) + "\n")
    log(f"\nwrote {args.data / 'state.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
