# Stage 0 localnet: the whole subnet on one CPU machine

`localnet.sh` runs Stage 0 of the test plan end to end:
- a real subtensor chain in Docker;
- a KunoWorld subnet with its owner, a validator and two miners;
- miner hotkeys proven to the gateway, and collateral posted;
- a gateway and two workers with the simulated TEE (`KUNO_TEE=mock`);
- a validator that challenges, sends canaries, scores, and sets weights on chain.

It ends by checking the chain: the validator's weights must include both miners.

```bash
scripts/localnet/localnet.sh up        # about 3–5 minutes on a warm machine; exits non-zero if the check fails
scripts/localnet/localnet.sh status    # processes, chain head, and the validator's weights right now
scripts/localnet/localnet.sh verify 60 # exit 0 only if the weights include both miners (polls up to 60 s)
scripts/localnet/localnet.sh down      # stop everything it started and remove the chain container
scripts/localnet/localnet.sh reset     # down, then delete data/localnet (the chain venv is kept)
```

To run the same flow on the public testnet, see [TESTNET.md](TESTNET.md).

**Requirements.**
- Docker, `uv`, and the workspace venv (`uv sync` in the repo root). The gateway, workers and devkit come from
  `.venv/bin`.
- Network access the first time, to pull the image and the pinned bittensor.
- `ss`, `setsid`, `curl` and `python3`, which any Ubuntu has.

## What `up` does

| # | Step | How |
|---|---|---|
| 1 | Chain venv | `data/localnet/venv`: `kuno-validator[chain,canary]` synced from `uv.lock` (bittensor 11.1.0), with `UV_PROJECT_ENVIRONMENT`. The workspace `.venv` and default installs are untouched. |
| 2 | Local subtensor | `docker run` of the pinned image with fast blocks (250 ms), RPC on `127.0.0.1:9944`. The container id goes to `run/chain.cid`. |
| 3 | Wallets | `alice` (the `//Alice` dev account: 1,000,000 TAO and sudo) plus `owner`, `validator`, `miner-a` and `miner-b`, regenerated with the SDK from random seeds in `data/localnet/seeds` (chmod 600). Wallets live in `data/localnet/wallets`; nothing goes to `~/.bittensor`. |
| 4 | Funding | `btcli tx transfer` from alice: the owner gets the subnet creation cost plus 100 TAO, the validator 300, each miner 100. |
| 5 | Subnet | `btcli tx register-subnet` as owner, then `btcli tx start-call`. If `SubnetEmissionEnabled` is off, `btcli tx set-subnet-emission-enabled` as alice (root). |
| 6 | Hyperparameters | Owner `btcli sudo set`: `collateral_lock_share` 39321, `collateral_drain_ratio` 1.0 (VALIDATING.md's recommendations; set only if different), `commit_reveal_weights_enabled` false. For mechanism 1 (Turbo), `max_allowed_uids` 128, then `btcli tx set-mechanism-count 2`. The collateral storage is detected first; if the runtime lacks it, the report says so and collateral steps are skipped. |
| 7 | Neurons | `btcli tx burned-register` for the validator and both miners, then `btcli tx add-stake` of 100 TAO on the validator. |
| 8 | Collateral | `btcli collateral add` of 2 alpha, then `btcli collateral set-min` of 2 alpha, per miner. `btcli collateral show` goes into `state.json`. |
| 9 | Permit | Waits for the validator's `ValidatorPermit`, which is assigned at an epoch. |
| 10 | Gateway | `kuno-devkit init --data data/localnet/gateway`, then `kuno-gateway` on `127.0.0.1:8090`. |
| 11 | Workers | `worker-a` for miner-a serves `ltx-2.5-fast`; `worker-b` for miner-b serves `ltx-2.5-pro`. Both mock TEE and mock backend. `KUNO_HOTKEY_SEED_FILE` is the miner's hotkey seed, so each registration carries a hotkey proof by the key registered on chain. |
| 12 | Paid jobs | `drive_jobs.py` sends one customer job per profile with the dev API key. Only paid jobs earn job pay; canaries alone leave every miner at weight 0. |
| 13 | Validator | `kuno-validator run --role main --interval 30 --netuid <n> --network local --wallet-name validator --wallet-path data/localnet/wallets`, with canaries on both profiles and `KUNO_MIN_COLLATERAL_PER_GPU=0.001`, so the collateral gate reads the chain. The Turbo track runs too. |
| 14 | Verify | `verify.py` reads the metagraph and the `Weights` storage until the validator's mechanism 0 row gives both miners a nonzero share (600 s at most), prints it as JSON, and exits 0 or 1. It prints the mechanism 1 row as well, which stays empty: a dev gateway serves no Turbo spec (`/turbo/v1/spec` answers 404), so the Turbo track has no qualifying miners and leaves mechanism 1 alone. |

`setup_chain.py` writes `data/localnet/state.json`: netuid, addresses, UIDs, collateral policy and positions,
commit-reveal and emission flags, mechanism count, and versions. The later steps and `verify.py` read it.

## Observed run (2026-09-14)

`localnet.sh up` from a stopped state finished in 114 s and exited 0: the image and venv were cached, and the data dir
was kept from an earlier run, so the wallets were the same. What `verify.py` read from the chain at block 355:

| Neuron | UID | Validator's weight (mechanism 0) | Incentive | Dividends | Collateral locked |
|---|---|---|---|---|---|
| owner | 0 | — | 0 | 0 | 0 |
| validator | 1 | — | 0 | 0.499992 | 0 |
| miner-a (`ltx-2.5-fast`) | 2 | **0.25** | 0.249989 | 0 | 2 alpha |
| miner-b (`ltx-2.5-pro`) | 3 | **0.75** | 0.749996 | 0 | 2 alpha |

- **The split is the VCU weights.** Each miner served one paid 2 s job, and `ltx-2.5-pro` weighs 9 at 720p against
  `ltx-2.5-fast`'s 3. The canaries passed but earned nothing, as designed.
- **Weights were plain, not commit-reveal.** The validator set them with `set_mechanism_weights` through
  `bt.set_weights`, using a wallet in `data/localnet/wallets`. Yuma consensus turned them into the miners' incentive
  at the next epoch.
- **The collateral gate read `MinerCollateral` through bittensor's RPC client.** No miner was zeroed.
- **Mechanism 1 stayed empty.** The dev gateway has no Turbo spec.
- **Chain setup:**
  - `collateral_lock_share` is 39321, `collateral_drain_ratio` 1.0, commit-reveal off, and the subnet runs two
    mechanisms with `max_allowed_uids` 128.
  - `start-call` and `set-subnet-emission-enabled` both succeeded.
  - Every shielded registration needed 1–3 resubmits.
- **One collateral top-up failed.** miner-b's `collateral add` failed with `AmountTooLow` after its first shielded
  attempts missed their block (in an earlier run it was miner-a's). Its `set-min 2` landed, and emission refilled its
  lock to the floor within the first rounds. The validator's first reading of miner-b was 0.48 alpha, still above the
  0.001 required.

## Isolation from what already runs here

- **Ports.** The chain is on `127.0.0.1:9944` and the gateway on `127.0.0.1:8090`. The dev gateway (8080) and Next
  (3000, 3001) are never used. `up` refuses to start if either port is taken; set `KUNO_LOCALNET_RPC_PORT` or
  `KUNO_LOCALNET_GATEWAY_PORT` to move them.
- **Data.** Everything lives in `data/localnet/` (gitignored):
  - `gateway/` with its own `dev.env` and SQLite database;
  - `validator/`, `worker-a/`, `worker-b/` (the workers' `KUNO_WORKDIR`);
  - `wallets/`, `seeds/`, `logs/`, `run/`;
  - `home/`: `HOME` for every process started here, which keeps btcli's config and the SDK's runtime cache out of
    `~/.bittensor`.
- **Environment.** Every process is started with `env -i` and an explicit environment. Nothing inherited reaches the
  services, such as a `KUNO_DATABASE_URL` or the dev gateway's `KUNO_GATEWAY_URL`. `dev.env`'s
  `KUNO_GATEWAY_URL=…8080` is overridden for each service.
- **Stopping.** `down` stops only what `run/*.pid` records:
  - each file holds the PID and its kernel start time, and a PID reused by someone else is left alone;
  - services run under `setsid`, so the signal goes to their own process group (a worker's ffmpeg children);
  - the chain container is removed by the id `up` recorded.

  Nothing matches by name or pattern. A container named `kuno-localnet` that this data dir has no record of is left
  in place, and `up` refuses to start.

## Pinned versions

| What | Pin | Why |
|---|---|---|
| Localnet image | `ghcr.io/raofoundation/subtensor-localnet:main@sha256:450981f12515af0d7368af2beac8aeb773646f7f90154094f397ce032b9840f7` | The image moved from `opentensor/` to `raofoundation/`. The opentensor tags stop at `v3.4.9-424` (June 2026, before the collateral pallet); RaoFoundation's version tag stops at `v432`. `main` on 2026-09-14 (subtensor `a7ae07e`) runs spec 458, with `MinerCollateral`, `CollateralLockShare`, `CollateralDrainRatio`, `add_collateral` and `set_min_collateral`, the same as testnet. The digest pins it; `KUNO_LOCALNET_IMAGE` overrides. |
| bittensor SDK | 11.1.0 | `uv.lock`'s pin for `kuno-validator[chain]`; the validator and `verify.py` use it |
| btcli | bittensor 11.1.0's `btcli`, through `uvx --from bittensor==11.1.0 --with typer==0.27.1` | btcli 9.x (`/usr/local/bin/btcli` here) has no collateral commands. Under the typer 0.27.2 that `uv.lock` resolves, btcli 11.1.0 does its work and then crashes on exit: typer 0.27.2 removed `typer._click.exceptions.Exit`, which `bittensor/cli/prompt.py` catches, so every command exits 1. btcli was run under 0.27.1. 0.26.0, 0.26.8 and 0.27.0 still have `Exit` too. bittensor declares `typer>=0.12.0` without an upper bound. |
| Python for btcli | 3.12 | the workspace's interpreter |

## Configuration

| Variable | Default | |
|---|---|---|
| `KUNO_LOCALNET_DIR` | `data/localnet` | everything `up` creates |
| `KUNO_LOCALNET_RPC_PORT` | 9944 | host port for the chain RPC |
| `KUNO_LOCALNET_GATEWAY_PORT` | 8090 | |
| `KUNO_LOCALNET_CONTAINER` | `kuno-localnet` | container name |
| `KUNO_LOCALNET_IMAGE` | the pin above | |
| `KUNO_LOCALNET_FAST_BLOCKS` | `True` | `False` runs 12 s blocks, which makes epochs, rate limits and permits 48× slower |
| `KUNO_LOCALNET_VALIDATOR_INTERVAL` | 30 | seconds between validator rounds; the weights rate limit is 100 blocks (25 s) |
| `KUNO_LOCALNET_MIN_COLLATERAL_PER_GPU` | 0.001 | alpha, passed as `KUNO_MIN_COLLATERAL_PER_GPU`; `0` turns the gate off |
| `KUNO_LOCALNET_COLLATERAL_ALPHA` | 2 | `collateral add` and `set-min` per miner |
| `KUNO_LOCALNET_MECHANISMS` | 2 | 1 skips the Turbo mechanism |
| `KUNO_LOCALNET_COMMIT_REVEAL` | unset | `1` leaves commit-reveal weights on; reveals then need the chain's drand pulses |
| `KUNO_LOCALNET_VERIFY_WAIT` | 600 | seconds `up` waits for the weights |

## What a real chain changed

**Validator code.** These broke against the chain and are fixed, with tests in
`subnet/validator/tests/test_bittensor11_chain_reads.py`:
- **Wallet directory (`chain.py`, `main.py`).** Given a wallet *name*, bittensor 11.1.0's `bt.set_weights` always
  looks in `~/.bittensor/wallets`. `set_weights` now takes `wallet_path` and passes a `Wallet` object, and
  `kuno-validator` has `--wallet-path` (default `$BT_WALLET_PATH`).
- **Commitments (`chain.py`).** `Subtensor().subnets.commitments(netuid)` returns `{hotkey: NeuronCommitment}` in
  11.1.0, not a list of dicts, so the Turbo track's commitment reader raised on every round. It now reads each
  `NeuronCommitment`'s `value`, and skips it while `is_revealed` is false.
- **Missing subnet (`chain.py`).** `subnets.metagraph()` returns `None` for a netuid that doesn't exist; that is now
  named in the error.
- **Chain client (`collateral.py`, used by `emission.py` too).** bittensor 11 ships neither `substrate-interface` nor
  `async-substrate-interface`, so under `kuno-validator[chain]` the collateral and emission readers raised
  `CollateralUnavailable`. They now fall back to bittensor's own `RpcSubstrate`, through a small blocking adapter
  (`BittensorRpcSubstrate`). On the localnet it read `MinerCollateral`, `SubnetAlphaOutEmission` and the pool price.
  The storage names and shapes the reader assumed were right.

**Chain behaviour.** These are handled in `setup_chain.py`, and they matter for mainnet too:
- **Two mechanisms need fewer UIDs.** The runtime refuses `max_allowed_uids` × mechanism count above 256
  (`TooManyUIDsPerMechanism`). A new subnet has 256 UIDs, so a two-mechanism subnet must drop to 128 before
  `set-mechanism-count 2`.
- **MEV shielding is mandatory for `burned_register` and `add_collateral`.** btcli refuses `--no-mev-shield` for them.
  On 250 ms blocks the shielded extrinsic often misses its block: `BadProof`, `Invalid`, `AncientBirthBlock`, or
  "decrypted extrinsic … was not included before its era expired". It is resubmitted (up to 40 times), and
  registration re-checks the UID first. In the prototype, miner-b's `collateral add` missed ten times in a row, so a
  collateral top-up that never lands is reported but doesn't fail `up`. Registration already locked 0.6 of the
  price, and `set-min` (not shielded) keeps it from draining.
- **Owner hyperparameters wait for the freeze window.** A new localnet subnet has tempo 10 and `AdminFreezeWindow` 10,
  so `sudo set` succeeds only in the block after an epoch (`AdminActionProhibitedDuringWeightsWindow` otherwise).
  `sudo set` is retried every second.
- **Staking on a new pool.** `add-stake` of 100 TAO trips the default 5% slippage protection, so it runs with
  `--no-slippage-protection` (unshielded, which `add_stake` allows).
- **Read commands.** `btcli sudo get`, `collateral show` and `collateral list` reject `-y`.

## Troubleshooting

- **Logs.** Everything is in `data/localnet/logs/`: `setup-chain.log`, `gateway.log`, `worker-a.log`,
  `worker-b.log`, `validator.log`, `drive-jobs.log`. Chain logs: `docker logs $(cat data/localnet/run/chain.cid)`.
- **"already up".** A previous run didn't stop cleanly: run `down`, which is safe to repeat.
- **A miner gets no weight.** Look for `miner <hotkey>: score=0.0000 … <reasons>` in `validator.log`. Common reasons:
  no paid job in the window (run `drive_jobs.py` again), `collateral … below` (raise `collateral add` or lower
  `KUNO_LOCALNET_MIN_COLLATERAL_PER_GPU`), or no permit yet.
- **`down` loses the chain.** It removes the container, and with it the subnet. The next `up` builds a new chain and
  re-registers the same wallets (the seeds are kept). `reset` makes new wallets.

## Files

| File | |
|---|---|
| `localnet.sh` | `up`, `status`, `verify`, `down`, `reset` |
| `setup_chain.py` | wallets and every chain transaction (btcli), writes `state.json` |
| `drive_jobs.py` | paid customer jobs through the localnet gateway |
| `verify.py` | reads weights and the metagraph; exit 0 only if both miners have weight |
| `TESTNET.md` | the same flow on `--network test` |
