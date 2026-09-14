# Stage 0 on Bittensor testnet

The same flow as [the localnet](README.md) on the public testnet (`--network test`,
`wss://test.finney.opentensor.ai:443`):
- a subnet with two mechanisms and collateral;
- a validator and two miners registered;
- mock-TEE workers proving their hotkeys;
- a validator setting weights.

`localnet.sh` does not do this. It starts its own chain and pays for everything from `//Alice`, and neither exists on
testnet, so the steps below are manual.

**None of this has been run on testnet.** The parameter values are read-only queries against testnet on 2026-09-14
(block 8,005,330). Testnet then ran runtime spec 458, the same as the pinned localnet image, so every extrinsic
`localnet.sh` sends exists there too.

## 1. Testnet TAO

- **There is no faucet.** btcli 11.1.0 has no `wallet faucet` command. The proof-of-work faucet of older btcli is
  disabled on testnet. The subnet template's testnet guide says: "Faucet is disabled on the testnet. Hence, if you
  don't have sufficient faucet tokens, ask the Bittensor Discord community for faucet tokens"
  ([running_on_testnet.md](https://github.com/latent-to/bittensor-subnet-template/blob/main/docs/running_on_testnet.md)).
- **So you ask on Discord.** Post your coldkey address (never a seed or mnemonic) with the amount and what it is for,
  in the channel that guide links to. Someone grants it by hand, so allow hours to days.
- **How much to ask for.** About 50 test TAO covers:
  - the subnet at today's cost;
  - three registrations;
  - a few TAO of validator stake;
  - a little collateral;
  - fees.

  The creation cost can spike (below), so check it before you ask.

## 2. What it costs

| Item | Testnet, 2026-09-14 | How to check |
|---|---|---|
| Subnet creation | 1 test TAO (`NetworkMinLockCost` = `NetworkLastLockCost` = 1 TAO) | `btcli subnets create-cost --network test` |
| Neuron registration (`burned-register`) | 0.0005 TAO (`Burn`) on the subnets sampled; a new subnet starts at its own initial burn | `btcli subnets burn-cost --netuid <n> --network test` |
| Collateral | `collateral_lock_share` × the registration price, plus any `collateral add` (alpha bought on the subnet's pool) | `btcli collateral show --netuid <n> --network test` |

- **The creation cost moves.** It doubles after each subnet registration anyone makes, and decays back over
  `NetworkLockReductionInterval` (100 blocks, about 20 minutes). The whole amount becomes the new pool's TAO reserve.
- **Subnet registrations are rate-limited.** `NetworkRateLimit` is 720 blocks, about 2.4 hours.
- **Small pool, large slippage.** A 1 TAO creation cost means a 1 TAO pool, so staking or buying collateral moves the
  price a lot. Stake a few TAO, add collateral in fractions of an alpha, and pass `--rate-tolerance` (or
  `--no-slippage-protection`) knowing what it does.

## 3. What differs from the localnet

| Step | Localnet (`localnet.sh up`) | Testnet |
|---|---|---|
| Chain | Docker container, 250 ms blocks | Public chain, 12 s blocks (`Aura.SlotDuration` 12000) |
| Funds | Transfers from `//Alice` | A Discord request (section 1) |
| Wallets | Unencrypted coldkeys regenerated from seeds in `data/localnet/seeds` | Encrypted coldkeys (`btcli wallet create` without `--no-password`); only the miners' hotkey seeds sit on disk (chmod 600) |
| Subnet cost | 1000 TAO | 1 TAO today; check it |
| `start-call` | Immediate (`StartCallDelay` 0) | Also immediate today (`StartCallDelay` 0) |
| TAO emission share | `//Alice`, as root, runs `set-subnet-emission-enabled` | Root only. The newest subnets (564–566) had `SubnetEmissionEnabled` false. Epochs, alpha emission and weights run regardless, which is all Stage 0 checks. |
| Tempo | 10 blocks (2.5 s) | 360 blocks (72 minutes) on new subnets |
| Owner `sudo set` | Retried through the freeze window (10 of 10 blocks) | Refused only in the 10 blocks (2 minutes) before an epoch |
| MEV-shielded calls (`burned-register`, `collateral add`) | Often miss their block (`BadProof`, `Invalid`, `AncientBirthBlock`) and are resubmitted | Expected to land first time at 12 s blocks (not verified) |
| Commit-reveal | Turned off by the script | On by default (`RevealPeriodEpochs` 1). Leave it on: a commit reveals about one tempo later, and only then does `verify.py` see it. `bittensor`'s `timelocked_weight_commits` read shows what is pending. |
| Weights rate limit | 100 blocks (25 s) | 100 blocks (20 minutes). Run the validator with `--interval 1200` or more. |
| Two mechanisms | `max_allowed_uids` 128, then `set-mechanism-count 2` | Same: the runtime refuses more than 256 UIDs across mechanisms (`TooManyUIDsPerMechanism`) |
| Validator permit | At the next epoch (seconds) | At the next epoch (up to 72 minutes) |
| Minimum weights | 1 | Usually 1, but subnet 565 had `min_allowed_weights` 8, which two miners can't meet. Check it with `btcli sudo get --name min_allowed_weights`. |
| Collateral storage | Present (spec 458) | Present (spec 458); lock share 0 until the owner sets it |
| Chain endpoint for the validator | `--network local` with `BT_CHAIN_ENDPOINT` and `KUNO_CHAIN_ENDPOINT` set to `ws://127.0.0.1:9944` | `--network test`, with neither variable set |

## 4. The steps

Use the same pinned btcli as the localnet, and keep the wallets out of `~/.bittensor`:

```bash
BTCLI="uvx --python 3.12 --from bittensor==11.1.0 --with typer==0.27.1 btcli"   # README.md explains the typer pin
T="--network test --wallet-path $PWD/data/testnet/wallets"

$BTCLI wallet create -w owner -H default $T        # prompts for a coldkey password; record the mnemonics
$BTCLI wallet create -w validator -H default $T
$BTCLI wallet new-coldkey -w miner-a $T
$BTCLI wallet new-coldkey -w miner-b $T
```

**Miner hotkeys.** A worker needs its hotkey as a 32-byte seed file (`KUNO_HOTKEY_SEED_FILE`). Make the hotkey from a
seed, as `setup_chain.py` does, so the worker and the wallet hold the same key:

```bash
data/localnet/venv/bin/python - <<'EOF'
import os, secrets
from bittensor import wallets
os.makedirs("data/testnet/seeds", mode=0o700, exist_ok=True)
for name in ("miner-a", "miner-b"):
    path = f"data/testnet/seeds/{name}.hotkey.seed"
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as f:
        f.write("0x" + secrets.token_hex(32))
    hotkey = wallets.regen_hotkey(seed=open(path).read(), name=name, hotkey="default", path="data/testnet/wallets")
    print(name, hotkey.hotkey.ss58_address)
EOF
```

**Chain setup.** Everything is signed by the coldkeys you funded:

```bash
$BTCLI subnets create-cost $T
$BTCLI tx register-subnet -w owner -H default $T                      # prints the netuid
N=<netuid>
$BTCLI tx start-call -w owner --netuid $N $T
$BTCLI sudo set -w owner --netuid $N --name collateral_lock_share --value 39321 $T
$BTCLI sudo get --netuid $N --name collateral_drain_ratio $T         # 1.0 by default; set it if not
$BTCLI sudo set -w owner --netuid $N --name max_allowed_uids --value 128 $T
$BTCLI tx set-mechanism-count -w owner --netuid $N --mechanism-count 2 $T
$BTCLI tx burned-register -w validator -H default --netuid $N $T
$BTCLI tx burned-register -w miner-a -H default --netuid $N $T
$BTCLI tx burned-register -w miner-b -H default --netuid $N $T
$BTCLI tx add-stake -w validator --hotkey <validator hotkey ss58> --netuid $N --amount 5 --rate-tolerance 0.5 $T
$BTCLI collateral add -w miner-a -H default --netuid $N --amount-alpha 0.1 $T
$BTCLI collateral set-min -w miner-a -H default --netuid $N --min-alpha 0.1 $T
# ...the same two collateral commands for miner-b
```

Set the collateral parameters before the miners register, because each registration snapshots them.

**Services.** Run the gateway and workers exactly as `localnet.sh`'s `start_gateway` and `start_worker` do, on a free
port with their own data dir. The validator changes three flags:
- `--network test`;
- `--interval 1200` or more;
- no `KUNO_CHAIN_ENDPOINT`.

```bash
KUNO_DATA_DIR=data/testnet/validator KUNO_GATEWAY_URL=http://127.0.0.1:8090 KUNO_MIN_COLLATERAL_PER_GPU=0.001 \
  data/localnet/venv/bin/kuno-validator run --interval 1200 --netuid $N --network test \
  --wallet-name validator --wallet-hotkey default --wallet-path data/testnet/wallets \
  --canary ltx-2.5-fast --canary ltx-2.5-pro
```

**Paid jobs.** Send them with `drive_jobs.py`, as the localnet does. Without paid jobs every miner scores zero and no
weights are set.

**Verify.** Write a `state.json` shaped like the localnet's:
- `"endpoint": "test"`;
- the netuid;
- each wallet's hotkey under `neurons`.

Then run `data/localnet/venv/bin/python scripts/localnet/verify.py --state state.json --wait 7200`. With commit-reveal
on, expect the weights about one tempo after the validator's first successful commit.

## Sources

- Faucet status: [bittensor-subnet-template, running_on_testnet.md](https://github.com/latent-to/bittensor-subnet-template/blob/main/docs/running_on_testnet.md).
- Testnet participation: [Learn Bittensor, Dynamic TAO testnet](https://learnbittensor.org/guides/participate-in-dynamic-tao-testnet).
- Localnet image and dev accounts: [Bittensor docs, local development](https://www.bittensor.com/docs/guides/local-development).
- Parameter values: read from testnet with bittensor 11.1.0 on 2026-09-14. Nothing was registered or transferred.
