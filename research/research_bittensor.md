# Bittensor Subnet Economics & Mechanics — State as of 2026-09-11

Research for: TEE-secured video-generation inference subnet with a paid, off-chain-revenue API.

**Method / provenance legend**

- **[CONFIRMED-CHAIN]** — read directly from Bittensor mainnet (finney) storage via JSON-RPC on 2026-09-11, block **9,045,154**, runtime **specVersion 455** (`https://entrypoint-finney.opentensor.ai:443`).
- **[CONFIRMED-CODE]** — read from `opentensor/subtensor` `main` branch source (raw.githubusercontent.com), 2026-09-11.
- **[CONFIRMED-DOCS]** — official docs, which have moved from docs.learnbittensor.org (now 301-redirects) to **https://bittensor.com/docs** (raw markdown at `https://bittensor.com/llms.mdx/docs/<slug>/content.md`).
- **[REPORTED]** — secondary source (news, analysts); not independently verified.
- **[MY CALC]** — my own computation from chain data; reproducible, but not an official figure.
- **[UNVERIFIED]** — claim found but could not be confirmed / conflicting sources.

Important: the docs' *default* values often differ from the *live mainnet* values (governance has changed storage). Where they differ, both are shown. Always re-read live values before launch.

---

## 0. Headline changes in 2026 that matter for a new subnet

| Date | Change | Source |
|---|---|---|
| Feb 2025 | dTAO live (first dTAO block 4,920,351) | [docs/emissions](https://bittensor.com/docs/concepts/emissions) |
| Sep 2025 | Price-ranked subnet deregistration returns | [docs/subnets](https://bittensor.com/docs/guides/subnets) |
| Nov 2025 | "TAO Flow" emission model (net staking flow EMA) replaces price | [Opentensor X](https://x.com/opentensor/status/1999071691243429968), [KuCoin](https://www.kucoin.com/news/flash/bittensor-launches-taoflow-restructures-emission-model-around-real-time-staking-flows) |
| Dec 2025 | First halving: 1 → 0.5 TAO/block (~3,600 TAO/day) | [docs/emissions](https://bittensor.com/docs/concepts/emissions), [Grayscale](https://research.grayscale.com/reports/bittensor-on-the-eve-of-the-first-halving-research) |
| Apr 9–10 2026 | Covenant AI (SN3/SN39/SN81) exits, sells ~37k TAO; TAO −27% | [The Block](https://www.theblock.co/post/396959/covenant-ai-exits-bittensor-tao), [tao.media](https://www.tao.media/covenant-ais-bittensor-exit-what-happened-how-bittensor-responded-and-whats-next-for-the-network/) |
| May 8 2026 | Hotfix removes owner's free alpha at subnet registration | [tao.media](https://www.tao.media/bittensors-hotfix-ends-subnet-owners-free-alpha-at-registration/) |
| May 13 2026 | **Conviction** (alpha locks; owner-exit visibility; conviction-based ownership transfer) | [tao.media](https://www.tao.media/the-conviction-upgrade-bittensor-just-made-subnet-owner-exits-a-public-event/), [docs/conviction](https://bittensor.com/docs/guides/conviction) |
| Jun 22 2026 | **PR #2781**: revert to **price-based** shares + **miner-burn penalty**; ~57 subnets' emissions disabled; weekly eligibility review | [PR #2781](https://github.com/opentensor/subtensor/pull/2781), [abittensorjourney](https://www.abittensorjourney.com/p/navigating-bittensor-june-2026) |
| Jul 2026 | **v440 Emission Gate** (Hill gate around rank 32) | [v440 notes](https://www.bittensor.com/releases/v440-upgrade) |
| Jul 2026 | **v441 Root Reborn** (root dividends → validator-curated alpha baskets) | [v441 notes](https://www.bittensor.com/releases/v441-upgrade), [docs/root-reborn](https://bittensor.com/docs/guides/root-reborn) |
| Jul 17 2026 | SDK **bittensor v11** (unified SDK + btcli) | [PyPI](https://pypi.org/project/bittensor/) |
| Aug 2026 | v450: root weights opened, cap 1/16 per destination | [v450 notes](https://www.bittensor.com/releases/v450-upgrade) |
| 2026 (by Sep) | Registration **collateral** (lock share of reg price, drained by earnings) | [docs/collateral](https://bittensor.com/docs/guides/mining/collateral) |

Market context: TAO = **$241.10**, market cap ≈ **$2.31B** (CoinGecko API, 2026-09-11). [CONFIRMED via API]

---

## 1. Dynamic TAO: tokens, pools, and emission allocation

### 1.1 TAO issuance & halving

- Base schedule: 1 TAO / 12-s block, 21M cap. Halvings are **issuance-threshold based**, not block-count based: each time total issuance crosses the midpoint of the remaining supply (10.5M, 15.75M, 18.375M, …). [CONFIRMED-DOCS] https://bittensor.com/docs/concepts/emissions
- **Recycled TAO is subtracted from issuance and can be re-emitted** (registration burns, transaction fees, EVM fees, alpha-paid fees sold for TAO), so recycling pushes halvings out. [CONFIRMED-DOCS]
- First halving: **December 2025** → **0.5 TAO/block ≈ 3,600 TAO/day**. [CONFIRMED-DOCS] Exact date reported as Dec 14 ([bittensor-halving.com](https://www.bittensor-halving.com/)) vs Dec 10 ([Bitrue](https://www.bitrue.com/blog/first-tao-halving)) — [UNVERIFIED exact day].
- Live total issuance: **11,330,335 TAO** (SubtensorModule.TotalIssuance and Balances.TotalIssuance agree). TotalStake: 7,318,081 TAO. [CONFIRMED-CHAIN]
- Next halving at 15.75M issuance → ~4.42M TAO away → ~1,228 days at 3,600/day ≈ **early 2030** (later with recycling) [MY CALC]; secondary sources say ~Dec 2029 ([ownyourmind](https://ownyourmind.ai/tokenomics/chutes-bittensor-revenue-machine/)).
- A TAO halving also halves every pool's injection (`tao_in` halves, `alpha_in = tao_in/price` halves). [CONFIRMED-DOCS] (This "asymmetric halving" issue #1975 was partially fixed Dec 2025 per [ownyourmind](https://ownyourmind.ai/tokenomics/bittensor-dtao-subnet-economics/) [REPORTED].)

### 1.2 Alpha tokens and pools

- Each subnet has its own alpha token, 21M cap, same issuance-threshold halving curve applied to *that subnet's* alpha issuance, starting from subnet launch. [CONFIRMED-DOCS]
- Pools are **Balancer-style weighted pools**; spot price = `(w_alpha / w_tao) × (TAO_reserve / alpha_reserve)`; weights start 0.5/0.5 (constant product), bounded [0.01, 0.99]. Per-block injections shift the **weights**, not the price, so emission doesn't move the market. Pool liquidity is protocol-owned; user LP is off (`user_liquidity_enabled` is root-only, "legacy, always false"). [CONFIRMED-DOCS]
- Staking = swap TAO→alpha in the pool (slippage applies); no unbonding period; min partial stake op 0.002 TAO (`MinStake` 2,000,000 rao). [CONFIRMED-DOCS] https://bittensor.com/docs/guides/staking
- MEV-shielded submission and limit-price variants (`add-stake-limit`) are available. [CONFIRMED-DOCS]

### 1.3 Per-block minting per subnet

Per block, each subnet mints (**[CONFIRMED-DOCS]**):

- `alpha_out` — **up to 1 alpha** (at the subnet's current alpha-halving rate) for participants, accumulated and paid at the next epoch. **This continues even if the subnet gets zero TAO emission** ("an emission-disabled subnet… its participant-side alpha_out continues to accrue").
- `alpha_in` — alpha injected into the pool next to the subnet's TAO emission, normally `tao_in / price` (price-neutral), **capped at `root_proportion × alpha_emission`**:

```
root_proportion_i = (root_tao × tao_weight) / (root_tao × tao_weight + alpha_issuance_i)
```

- When the cap binds (mature subnets), TAO that cannot be injected is used to **buy alpha on the subnet's own pool** ("chain buys"); this alpha accumulates as **protocol-owned alpha**. [CONFIRMED-DOCS]

Live values [CONFIRMED-CHAIN]:
- `TaoWeight` = 0.18 (raw 3320413933267719290 / 2^64); runtime default is ~0.0527 — governance raised it.
- Root TAO (`SubnetTAO[0]`) = **5,298,381 TAO** → `root_tao × tao_weight` ≈ 953.7k.
- `RootProp`: SN4 0.134, SN51 0.140, SN64 0.134, SN120 0.185, SN58 (young) 0.601. My recomputation from the formula matches chain to 9 digits. [MY CALC]
- A brand-new subnet (tiny alpha issuance) has root_proportion ≈ 1.

### 1.4 How TAO emission is split across subnets — CURRENT formula (since Jun 22 / Jul 2026)

**The TAO-flow model is no longer live.** The current `get_shares` in subtensor main ([subnet_emissions.rs](https://github.com/opentensor/subtensor/blob/main/pallets/subtensor/src/coinbase/subnet_emissions.rs)) is [CONFIRMED-CODE + CONFIRMED-DOCS]:

```
Step 1 (price share):     demand_share_i = price_ema_i / Σ_j price_ema_j        (over emission-enabled subnets)

Step 2 (miner-burn):      burn_adj_i = demand_share_i × (1 − MinerBurned_i) / Σ_j demand_share_j × (1 − MinerBurned_j)

Step 3 (emission gate):   gate_i  = 1 / (1 + (θ / burn_adj_i)^h)       ≡  s^h / (s^h + θ^h)
                          final_i = burn_adj_i × gate_i / Σ_j burn_adj_j × gate_j

TAO to subnet i per block = final_i × block_emission   (0.5 TAO today)
```

- `h` = `EmissionGateExponent`, default **3**. [CONFIRMED-CODE]
- `θ` = `EmissionGateBar`, recomputed every **360 blocks** (`EMISSION_BAR_UPDATE_INTERVAL`). Rank mode: θ = the **N-th largest positive adjusted share, `EmissionBarRank` default N = 32**. (A q-mass mode, `EmissionBarQuantile` default 0.61, exists if rank = 0.) [CONFIRMED-CODE]
- Live θ = **0.008843** (≈0.88% share). [CONFIRMED-CHAIN]
- Fallbacks: if all burn-adjusted weights are 0, restore unadjusted price shares; if all gated values underflow, restore ungated shares. [CONFIRMED-CODE]
- `price_ema` is `SubnetMovingPrice`, with **age-dependent smoothing**: `ema_alpha = base_alpha × blocks_since_start / (blocks_since_start + 201,600)`; the spot price fed into the EMA is **capped at 1.0**. New subnets' moving price "starts near zero" and adapts extremely slowly, blunting launch pumps. [CONFIRMED-DOCS]
- `MinerBurned_i` = share of **last tempo's miner incentive** that was directed at the subnet owner's hotkeys (owner hotkey + owner-associated/immune hotkeys) and therefore withheld (burned or recycled). Computed in `run_coinbase.rs` as `withheld_incentive / total_incentive`; choosing Recycle instead of Burn **does not avoid it**. [CONFIRMED-CODE]
- Emission-disabled subnets (root switch `SubnetEmissionEnabled`) are excluded and their share redistributed. **New subnets register with it OFF; owners cannot set it.** [CONFIRMED-DOCS] https://bittensor.com/docs/guides/subnets

**Discrepancy note:** the PR #2781 description stated shares ∝ `root_proportion_i × price_i × (1 − miner_burned_i)` ([PR](https://github.com/opentensor/subtensor/pull/2781)). The code on `main` today (spec 455) has **no root_proportion factor** in `get_shares` — root_proportion is used only for the injection cap and root-dividend share. Docs match the code. Treat the code as authoritative.

v440 rationale: "A slot should cost nothing" — collapse idle subnets' passive yield toward zero. At v440: below-bar emission 38.4% → 12.5%; top-8 32.8% → 52.7%; effective subnet count ~50 → ~22. [CONFIRMED — official release notes] https://www.bittensor.com/releases/v440-upgrade

#### Live snapshot of emission shares (block 9,045,154) — [MY CALC from chain storage]

Reconstructed by applying the formula above to live `SubnetMovingPrice`, `MinerBurned`, `SubnetEmissionEnabled` and θ:
- 128 subnets; **126 emission-enabled, 2 disabled** (the ~57 disabled in June seem mostly re-enabled — [UNVERIFIED interpretation]).
- **71 subnets have MinerBurned > 0; 52 have MinerBurned > 0.5.**
- 33 subnets at/above the bar get **≈97% of TAO emission**.

| Rank | Netuid | EMA price (TAO/α) | MinerBurned | Final share | TAO/day |
|---|---|---|---|---|---|
| 1 | 51 (Lium) | 0.0972 | 0 | 13.4% | 483 |
| 2 | 64 (Chutes) | 0.0703 | 0 | 9.7% | 349 |
| 3 | 107 | 0.0565 | 0 | 7.8% | 280 |
| 4 | 4 (Targon) | 0.0579 | 0.066 | 7.5% | 268 |
| 5 | 120 | 0.0516 | 0 | 7.1% | 256 |
| 6 | 44 (Score) | 0.0389 | 0 | 5.3% | 192 |
| 7 | 3 | 0.0292 | 0 | 3.95% | 142 |
| 8 | 8 (Taoshi/Vanta) | 0.0275 | 0 | 3.7% | 133 |
| 10 | 53 | 0.0237 | 0 | 3.1% | 113 |
| 20 | 5 | 0.0128 | 0 | 1.4% | 50 |
| 32 | 118 | 0.0083 | 0 | 0.58% | 20.8 |
| 34 | **90** | **0.0317** | **0.766** | 0.43% | 15.5 |
| 35 | 105 | 0.0059 | 0 | 0.21% | 7.7 |
| 50 | 26 | 0.0035 | 0 | 0.034% | 1.2 |
| 60 | 1 | 0.0071 | (high) | 0.014% | 0.5 |
| 80+ | … | … | … | ~0 | ~0 |

(Name mapping for 51/64/4/44/3/8 from [ownyourmind](https://ownyourmind.ai/tokenomics/bittensor-dtao-subnet-economics/) and [CoinGecko](https://www.coingecko.com/learn/top-bittensor-subnets-dtao) — others not mapped.)

**Key lesson (SN90):** its EMA price ranks around top-7, but because ~77% of miner incentive is routed to owner hotkeys, its share falls below the gate and collapses to ~0.43% (vs ~4% without burning). **Owner-burning is now very expensive in TAO-emission terms.**

- Median EMA alpha price ≈ 0.00445 TAO; median spot ≈ 0.00463 TAO. Sum of EMA prices ≈ 1.1–1.2 (so root dividends are active; see §2). [MY CALC]
- Earlier "24 subnets above bar collecting ~60.5%" ([ownyourmind, 2026-09-07](https://ownyourmind.ai/tokenomics/bittensor-dtao-subnet-economics/)) uses a different "above bar" definition — [REPORTED].

### 1.5 The TAO-flow model (Nov 2025 – Jun 22 2026) — historical, now dead code

`get_shares_flow` is still in the source, tagged `#[allow(dead_code)]`. [CONFIRMED-CODE]

```
Per block:   SubnetTaoFlow_i += TAO staked in;  −= TAO unstaked         (user flow)
             SubnetProtocolFlow_i += emission + chain buys − root sells   (protocol cost)
EMA:         S_i ← (1 − a)·S_i + a·flow_i ,  a = FlowEmaSmoothingFactor
             default a ≈ 3.209e-6/block ⇒ half-life 216,000 blocks (~30 days),
             time-constant 1/a ≈ 311,600 blocks (~43 days)
Net flow:    if NetTaoFlowEnabled:  net_i = userEMA_i − k·max(protocolEMA_i,0)   (negative protocol EMA kept as a benefit)
             k = min(1, Σ⁺userEMA / Σ⁺protocolEMA)
Offset:      L = max(TaoFlowCutoff, min(min_i net_i, 0));  with default cutoff 0 ⇒ L = 0
             z_i = max(net_i − L, 0)
Shares:      share_i = z_i^p / Σ z_j^p ,  FlowNormExponent p default 1
```

So during the flow era, **only subnets with positive net inflow received TAO**; outflow subnets got zero. Parameter values actually in force on mainnet during that period may have differed from these defaults — [UNVERIFIED] (the storage items are now unset). Secondary sources describe it as a "30-day EMA" ([KuCoin](https://www.kucoin.com/news/flash/bittensor-launches-taoflow-restructures-emission-model-around-real-time-staking-flows)) or an "~86.8/87-day window" ([ownyourmind](https://ownyourmind.ai/tokenomics/bittensor-dtao-subnet-economics/)). Why it was dropped: the flow signal was still gameable and punished subnets during market-wide outflows; price + burn penalty + gate replaced it ([PR #2781](https://github.com/opentensor/subtensor/pull/2781), [abittensorjourney](https://www.abittensorjourney.com/p/navigating-bittensor-june-2026)) [REPORTED rationale]. Flow EMAs are still tracked (`btcli query subnet-tao-flows`).

The original (Feb–Nov 2025) price model was gamed: teams used TAO treasuries to inflate alpha prices, collected outsized emission while prices slowly fell, then repeated ([ownyourmind](https://ownyourmind.ai/tokenomics/bittensor-dtao-subnet-economics/)) [REPORTED]. The slow age-dependent EMA and the gate are the current defences.

---

## 2. Emission split inside a subnet & Yuma Consensus

### 2.1 Split (per tempo)

[CONFIRMED-DOCS/CODE] https://bittensor.com/docs/concepts/emissions
- **18% owner** (`SubnetOwnerCut` = 11796/65535; runtime const `SubtensorInitialSubnetOwnerCut`), **41% miners**, **41% validators + their stakers**. `owner_cut_enabled` is owner-settable.
- A **`root_proportion` share of the validator half** goes to **root (netuid 0) stakers** as root dividends, but only in blocks where the sum of eligible non-root subnets' EMA prices exceeds 1.0 (otherwise that alpha is recycled). For mature subnets that's ~13–18% of the validator half; for a **new subnet it is close to 100%**, because root_proportion ≈ 1 when alpha issuance is tiny. [CONFIRMED-DOCS formula; the magnitude is MY CALC — check this on testnet/localnet before relying on it.]
- Inside a validator's dividends, the TAO-staker portion is `τ·w/(α + τ·w)` and the alpha-staker portion is `α/(α + τ·w)`, with w = 0.18. Validator take (default 18%, max 18%; raising it is rate-limited to once per 216,000 blocks) is deducted first.
- If an epoch has zero total miner incentive, the miner half goes to validators.
- Emission is settled **at epoch end** to whoever holds each UID. A neuron pruned mid-tempo gets nothing for that partial tempo.

Root dividends since **v441 Root Reborn** (July 2026, block 8,922,321) no longer sell alpha to TAO every block. Each root validator runs an escrowed **basket** (index fund of subnet alpha) curated by `set_root_weights`: at least 8 positive destinations, cap 1/16 per destination since v450, so effectively 16+ destinations. Stakers hold **beta** shares. Pre-v441, 936 τ/day of forced sells hit subnet pools (26% of emission); at v441, 47.9% of issuance was on root and base root yield was 6.3%/yr. [CONFIRMED — v441 notes](https://www.bittensor.com/releases/v441-upgrade). **Implication: getting included in root validators' baskets is a new source of alpha demand.**

### 2.2 Yuma Consensus (per mechanism, per epoch)

[CONFIRMED-DOCS] https://bittensor.com/docs/concepts/emissions, https://bittensor.com/docs/internals/consensus
- **Stake weight** = `alpha_stake + tao_stake × 0.18`. Stake below **`StakeThreshold`** counts as zero, and the same threshold is the minimum to set weights. Live value: **1,000** TAO-equivalent [CONFIRMED-CHAIN]; runtime default is 0.
- **Validator permits**: top-K by stake weight, K = `MaxAllowedValidators` (default 128; root-only). The **subnet owner's UID always gets a permit and is exempt from the threshold**. Losing a permit deletes your bonds. (ownyourmind reports "64 validators per subnet" — [UNVERIFIED]; docs and code say 128.)
- **Activity cutoff** = `activity_cutoff_factor` (default 13,889 per-mille) × tempo / 1000 → 5,000 blocks at tempo 360. Inactive validators are masked out.
- **Weight filtering**: self-weights are removed (except the owner's); non-permit weights are dropped; weights set before a target's latest registration are dropped; rows are normalized.
- **Consensus**: per miner j, `W̄_j = argmax_w { Σ_i S_i·1[W_ij ≥ w] ≥ κ }` (stake-weighted median), with κ = 32767/65535 ≈ 0.5 (root-only). Clipping: `W̄_ij = min(W_ij, W̄_j)`.
- **Incentive**: `R_j = Σ_i S_i·W̄_ij`, `I_j = R_j / Σ R`. Validator trust = `Σ_j W̄_ij`. The per-miner "trust" metric is deprecated.
- **Bonds**: `W̃ = (1−β)W + βW̄` with `bonds_penalty` β (default 1). `ΔB_ij = S_i·W̃_ij / Σ_k S_k·W̃_kj`, and `B(t) = a·ΔB + (1−a)·B(t−1)` with `a = 1 − bonds_moving_avg/1e6` (default 900,000 → a = 0.1).
- **Dividends**: `D_i = Σ_j B_ij·I_j`. The emission ratio ξ is fixed at 0.5 when both sides are non-zero.
- **Yuma3** (`yuma3_enabled`, default false, owner-settable): fixed-point bonds with per-pair scaling; dividends are the row-sum of bonds × incentive, scaled by active stake. **Liquid alpha** (`liquid_alpha_enabled`) **only works when Yuma3 is on**: the per-pair EMA rate moves between alpha_low 0.7 and alpha_high 0.9 via a sigmoid on distance from consensus (steepness default 1000).
- If there are no valid weights, emission falls back to stake proportions.
- Security guarantee (Monte Carlo): at weight deviation 0.2–0.4μ, 60% honest stake is retained if honest utility is ≥ ~70%. Worst case is "a 40% stake + 30% utility attack" under high subjectivity. κ = 0.5 is the recommended setting. [CONFIRMED-DOCS internals/consensus]

### 2.3 Commit-reveal weights

[CONFIRMED-DOCS] https://bittensor.com/docs/guides/validating
- `commit_reveal_weights_enabled` **default true**, and `commit_reveal_period` default 1 tempo. Weights are **Drand timelock-encrypted** and **auto-revealed by the chain**: no manual reveal, so selective reveal is no longer possible.
- It only defeats copiers when rankings **change** within the concealment window.
- Rule: **`immunity_period` > `commit_reveal_period × tempo`**, otherwise new miners can be pruned before their first scores reveal.
- `weights_rate_limit` is 100 blocks (root-only). Each submission carries a `weights_version` key, which owners bump to force validators onto new code.

### 2.4 Neuron (miner/validator UID) registration, immunity, pruning

[CONFIRMED-DOCS] https://bittensor.com/docs/guides/mining/burn, /mining, /mining/collateral
- Single floating **registration price** per subnet. It decays with half-life `burn_half_life` (default 360 blocks) and is multiplied by `burn_increase_mult` (default 1.26) on each registration, clamped to [`min_burn` 0.0005 τ, `max_burn` 100 τ]. All of these are owner-settable. PoW/adjustment-interval machinery is legacy, though `max_registrations_per_block` is still enforced.
- The burned TAO is **swapped into the subnet pool and the alpha removed** (recycled). There is no refund.
- **Registration collateral** (new): `collateral_lock_share` p (default 0, max 95%) of the price is locked as alpha on the hotkey, and `collateral_drain_ratio` k (default 1, range (0, 10]) releases `min(locked − min_locked, k × emission)` per tempo. The lock **survives deregistration**, is credited on re-registration, and has **no withdrawal path except earning**. `add_collateral` and `set_min_collateral` support per-machine deposit policies (the Lium pattern). Validators enforce by refusing to score, since there is no on-chain slash. Detection budget: `E* = max(T/(1+k), (1−p)·T)`.
- UID slots: `max_allowed_uids` default **256**, floor 64; `max_allowed_uids × mechanism_count ≤ 256`. `trim-subnet` is limited to once per 216,000 blocks.
- **Pruning** (only when full): lowest emission-based pruning score among non-immune UIDs; ties evict the older UID. If all are immune, the lowest immune UID is pruned anyway. `immunity_period` default **4,096 blocks (~13.7 h)**. Owner-immune UIDs: `immune_owner_uids_limit` default 1, max 10; immune UIDs may not exceed 80% of max.
- Validators should score by **hotkey root** (lineage maps `HotkeyRoot`/`HotkeySuccessor`), not UID. UIDs are recycled.

### 2.5 Subnet registration cost & subnet deregistration

| Parameter | Docs default | **Live mainnet** [CONFIRMED-CHAIN] |
|---|---|---|
| Current registration (lock) cost | — | **590.71 TAO** (runtime API `get_network_registration_cost`) ≈ **$142k** |
| `NetworkLastLockCost` | — | 460.58 TAO |
| `NetworkMinLockCost` (floor) | 1,000 TAO | **1 TAO** |
| `NetworkLockReductionInterval` | 100,800 blocks (~2 wk) | **115,200 blocks (~16 days)** |
| `NetworkRateLimit` | 7,200 blocks (~1 day) | **14,400 blocks (~2 days)** |
| `SubnetLimit` | 128 | **128**; `TotalNetworks` = 129 incl. root → **full** |
| `NetworkImmunityPeriod` | 1,296,000 blocks (~6 mo) | **864,000 blocks (~120 days)** |
| `StartCallDelay` | — | unset → runtime const 0 (no activation delay) |
| Testnet cost / limit | — | **1 TAO**; SubnetLimit 1,024 (562 registered); rate limit 720 blocks |

- Cost mechanics: it **doubles on each subnet registration**, then **decays linearly** back over the reduction interval, floored at `NetworkMinLockCost`. [CONFIRMED-DOCS] Historical range: 10,127 TAO (~$6.7M) in Apr 2026, 1,500 TAO in Jun 2026 ([cryptobriefing](https://cryptobriefing.com/bittensor-subnet-registration-cost-rises/)) [REPORTED]. The v440 gate was designed to push slot value toward ~0.
- **The whole lock goes into the new pool as its initial TAO reserve.** The alpha reserve is sized so the starting price = **median alpha price across subnets**. Nothing is recycled, the lock is not refundable, and **the owner gets no free alpha** (since the May 8, 2026 hotfix v3.3.15-402). [CONFIRMED-DOCS + REPORTED]
- Two-step activation: `register-subnet`, then owner `start-call` (once). Then root must flip **`subnet_emission_enabled`** (root-only, starts OFF) before any TAO flows in. Without it you still get epochs, trading and alpha_out. [CONFIRMED-DOCS]
- **Subnet deregistration**: there is no inactivity-based dereg. When at the 128 limit, the next registration prunes the **non-immune subnet with the lowest EMA alpha price** (ties → oldest) and reuses its netuid. If all are immune, registration fails. On dissolution, the subnet TAO reserve is paid pro-rata to **all** alpha, including protocol-held alpha (whose share returns to the chain, diluting holders). Conviction locks are deleted and owners get no refund. [CONFIRMED-DOCS] Alpha holders can lose most of their value ("up to 96.875%" per [ownyourmind](https://ownyourmind.ai/tokenomics/bittensor-dtao-subnet-economics/)) [REPORTED].
- A dissolve schedule duration of 5 days exists in the runtime (`InitialDissolveNetworkScheduleDuration`). [CONFIRMED-CODE]

---

## 3. Newer features

### 3.1 Multiple incentive mechanisms ("sub-subnets" / mechanisms)
[CONFIRMED-DOCS/CODE] https://bittensor.com/docs/guides/subnets#mechanisms
- `set-mechanism-count`: **max 2** mechanisms (`MaxMechanismCount` default 2). Each runs Yuma independently with its own weight matrix and bonds. Miners keep **one UID across mechanisms**, and total emission is the sum.
- Emission split is a u16 vector summing to 65,535 (e.g., `[13107, 52428]` = 20/80); unset means even. Changing the count resets the split. Count changes are limited to once per 7,200 blocks. Validators target a mechanism with `mechid` on set-weights.
- Constraint: `max_allowed_uids × count ≤ 256`, so 2 mechanisms means ≤128 UIDs.

### 3.2 Owner burning / "burn UID" — now penalized
- Weight sent to owner hotkeys is withheld from miners and **burned or recycled** (`recycle_or_burn`, default burn). [CONFIRMED-DOCS/CODE]
- **Since Jun 22 2026 the withheld proportion (`MinerBurned`) directly scales down the subnet's TAO emission share** (×(1−b)), which can then drop it below the gate. Live example: SN90 (see §1.4). [CONFIRMED-CODE, MY CALC]
- Historical practice: Taoshi (SN8) burned a variable share (e.g., 67%) to cap miner payouts at 30× annualized returns (May 2025) ([Taoshi docs](https://docs.taoshi.io/tips/p20/)). Today SN8's MinerBurned is 0. [CONFIRMED-CHAIN]
- Takeaway: if emissions exceed useful work, burning is no longer "free" for the subnet's TAO inflow. Trade-offs are in §5.

### 3.3 Owner-settable hyperparameters (key ones)
[CONFIRMED-DOCS] https://bittensor.com/docs/hyperparameters, /guides/subnets
- **Owner**: `tempo` (360–50,400), `immunity_period`, `min_allowed_weights`, `weights_version`, `activity_cutoff_factor`, `min_burn`/`max_burn`, `burn_half_life`, `burn_increase_mult`, `collateral_lock_share`, `collateral_drain_ratio`, `bonds_moving_avg`, `bonds_penalty`, `commit_reveal_weights_enabled`, `commit_reveal_period`, `yuma3_enabled`, `liquid_alpha_enabled`, `alpha_low`/`alpha_high`, `alpha_sigmoid_steepness`, `max_allowed_uids`, `serving_rate_limit`, `transfers_enabled`, `owner_cut_enabled`, `owner_cut_auto_lock_enabled`, `min_childkey_take`, `immune_owner_uids_limit`, `bonds_reset_enabled`, `recycle_or_burn`, mechanism count/split.
- **Root-only**: `kappa`, `max_weights_limit`, `weights_rate_limit`, `max_validators`, `registration_allowed` (pausing registration needs root), `activity_cutoff` (legacy), `subnet_emission_enabled`, `subnet_is_active`, `yuma_version`, `target_regs_per_interval`, `max_regs_per_block`.
- Rate limit: each hyperparameter can change about once per 2 tempos (`OwnerHyperparamRateLimit`). There is a **freeze window** in the last ~10 blocks of each tempo.
- Secure the owner coldkey with a **multisig** plus a scoped **Owner proxy** for operations. [CONFIRMED-DOCS]

### 3.4 Conviction (May 13 2026)
[CONFIRMED-DOCS] https://bittensor.com/docs/guides/conviction
- `lock-stake`: an unstake floor that keeps earning and accrues **conviction** to a chosen hotkey. Perpetual locks: `c = m − (m − c₀)e^(−Δt/τ)`. Decaying locks (the default) unlock on `UnlockRate`. `MaturityRate` = 311,622 blocks (~43 d) [CONFIRMED-CHAIN]; `UnlockRate` 934,866 (~130 d). Switching to decaying emits a public event.
- **Ownership transfer**: after the subnet is ≥ 1 year old (2,629,800 blocks), if the single highest-conviction hotkey holds > **18% of eligible alpha** (`SubnetAlphaOut − ProtocolAlpha − AlphaBurned`) on its own, it **becomes the owner**. Locks on the owner hotkey mature instantly. **Owners must hold/lock meaningful alpha to defend ownership.**
- Owner cut auto-lock: news reports say that from May 13 owner emissions were **automatically locked** ([tao.media](https://www.tao.media/the-conviction-upgrade-bittensor-just-made-subnet-owner-exits-a-public-event/)). Current docs list `owner_cut_auto_lock_enabled` as an owner-settable flag with **default false**. [CONFLICT — check the live value for your netuid]

### 3.5 Root claims / root dividends
Covered in §2.1. Stakers claim with `claim-root-with-hotkey`. `set_root_claim_type` (Swap/Keep) was removed in v441, so payouts are TAO restaked to root. Claim threshold is 0.0005 τ. Root seats: 64, burn-based entry (~1 τ baseline). [CONFIRMED-DOCS]
- **Auto-parent delegation**: a new root validator is auto-childkeyed to every subnet owner hotkey (100% stake weight on that subnet), and **a new subnet does the same for every current root validator**, unless they opted out. This bootstraps the owner validator's stake weight. [CONFIRMED-DOCS — verify the effect on testnet]

### 3.6 Alpha buybacks (protocol) & burns
- Protocol "chain buys": excess TAO when the injection cap binds buys alpha → protocol-owned alpha. [CONFIRMED-DOCS]
- User-level: `burn_alpha` and `recycle` extrinsics exist (listed in the unstake guard). `AlphaBurned` is excluded from the conviction-eligible supply. [CONFIRMED-DOCS]

### 3.7 Leasing & crowdloans
[CONFIRMED-DOCS] https://bittensor.com/docs/guides/subnets#financing-leases-and-crowdloans
- `create-crowdloan` → `register-leased-network`; `terminate-lease`. The lease `emissions_share` is a **% of the 18% owner cut** (50% share → 9% of subnet emission to contributors). Contributor dividends are swapped to TAO every 100 blocks, pro-rata. Crowdloans run 7–60 days (50,400–432,000 blocks), and unused cap is refunded. The beneficiary gets a scoped `SubnetLeaseBeneficiary` proxy.

### 3.8 EVM on subtensor
[CONFIRMED-DOCS] https://bittensor.com/docs/guides/evm
- Mainnet EVM chain ID **964** (`https://lite.chain.opentensor.ai`), testnet **945** (`https://test.chain.opentensor.ai`), localnet 42 (setup via `btcli evm setup-localnet`).
- Precompiles: staking v1/v2, alpha, metagraph, subnet, neuron, UID lookup, crowdloan, leasing, proxy, address mapping, voting power, drand, balance transfer, storage query. You can **register subnets/neurons, set weights and stake from an EVM key**. A contract could run on-chain buybacks with staking-v2 + alpha precompiles (design option).
- ink! WASM contracts are also supported (pallet-contracts).

### 3.9 Governance
- Legacy senate removed. Privileged ops go through **sudo held by a multisig of Rao Foundation keys** [CONFIRMED-DOCS validating]. The GitHub org is mirrored at `RaoFoundation/subtensor`.
- Const's roadmap targets full decentralization by **Dec 2027** (June 22, 2026) [REPORTED]. There is weekly subnet-eligibility review for `subnet_emission_enabled` [REPORTED]. **Rule-change risk is high**: 2026 saw flow → price+burn → gate → conviction → root reborn ([tao.media on Creaser](https://www.tao.media/mark-creaser-says-bittensors-rule-changes-are-making-dtao-harder-to-underwrite/)).

---

## 4. Routing off-chain revenue to token value — examples

| Subnet | Revenue claim | Verified? | Emission (live, MY CALC) | Routing |
|---|---|---|---|---|
| **Chutes SN64** (Rayon Labs) | Self-reported ~$10M ARR; $22k/day late Mar 2026; ~$280k per trillion tokens | Pine Analytics (Mar 2026): **$1.3–2.4M ARR**; subsidy **22–40×** | 9.7% ≈ 349 TAO/day ≈ $84k/day ≈ **$31M/yr** | Revenue auto-staked to buy SN64 alpha [REPORTED] ([CoinGecko](https://www.coingecko.com/learn/top-bittensor-subnets-dtao), [ownyourmind](https://ownyourmind.ai/tokenomics/chutes-bittensor-revenue-machine/)) |
| **Targon SN4** (Manifold Labs; $10.5M Series A) | **$10.4M ARR** self-reported; ~$100k/mo committed to buybacks | Unaudited; customers mostly Bittensor-native (Dippy, Ridges, Score) | 7.5% ≈ 268 TAO/day ≈ **$23.6M/yr** | Alpha buybacks/burn [REPORTED] ([taodaily](https://taodaily.io/targon-subnet-4-explained-fast-inference-and-why-theyre-burning-alpha/), [ownyourmind](https://ownyourmind.ai/tokenomics/targon-bittensor-confidential-compute/)). **TEE stack: Intel TDX + NVIDIA Confidential Computing (H100/H200) + proprietary Targon VM; Intel whitepaper Mar 23 2026** |
| **Lium SN51** | $5.3M ARR ([Unsupervised Capital](https://www.unsupervised.capital/writing/bittensors-ai-compute-subnets-collectively-reach-20m-arr)); "revenue outpaces emissions" | Unverified | **#1: 13.4% ≈ 483 TAO/day ≈ $42M/yr**. That claim looks false at current prices [MY CALC] | GPU rental; per-machine collateral pattern (docs) |
| **Gradients SN56** | "50% of revenue to buybacks" | [UNVERIFIED snippet] | 2.0% ≈ 71 TAO/day | Buyback + reinvest |
| **Taoshi SN8** | — | — | 3.7% | Historically burned miner emissions (cap 30× returns) |

- Network-level: the verifiable-revenue floor is ~**6.4% of the emission budget**; Pine estimates network revenue at $3–15M/yr against ~3,559 TAO/day minted ([ownyourmind](https://ownyourmind.ai/tokenomics/bittensor-subnets-where-the-revenue-is/)) [REPORTED]. Chutes cut its free tier after heavy users extracted 56–324× subscription value (Feb 2026) [REPORTED].
- Conflicting claim: "Chutes generated $43M Q1 2026 AI revenue" ([abittensorjourney](https://www.abittensorjourney.com/p/navigating-bittensor-june-2026)) — [UNVERIFIED, inconsistent with Pine].

### Routing options under the CURRENT rules (analysis)
1. **Buy alpha on the pool and hold/stake/lock it** (to the owner hotkey or a treasury). This raises spot → slowly raises `SubnetMovingPrice` → raises TAO emission share, amplified by the gate near θ. It also builds conviction to defend ownership. There are no on-chain penalties. Most aligned with the current formula.
2. **Buy and burn alpha** (`burn_alpha`). This reduces supply and conviction-eligible alpha, and has the same price effect on purchase. It's permanent, so there's no treasury flexibility.
3. **Pay miners directly off-chain** (USD/TAO per job). This makes real revenue flow to suppliers and cuts dependence on emissions, but **does not support the alpha price or the emission share**. Good for unit economics, but miners then sell their emission alpha anyway.
4. **Hybrid (recommended)**: X% of net revenue goes to programmatic alpha buybacks (transparent, on-chain, ideally through an EVM contract or a published address, MEV-shielded, with limit prices), Y% to direct miner job payments for verified work, and the rest is opex.
5. **Avoid owner-hotkey burning of miner weight.** Since June 2026 it scales down your TAO share ×(1−b) and can push you under the gate.
6. **Aim for root basket inclusion**: root validators now actively allocate root dividends across ≥16 subnets. A credible revenue story plus an on-chain buyback is how you attract them.

### Legal/structural considerations — [ANALYSIS, not legal advice; no authoritative source found]
- Corporate buybacks of a token with company revenue can strengthen a "security" characterization (expectation of profit from the efforts of others). Prefer the framing "revenue purchases network capacity / funds miner rewards" to "price support". Document the policy and avoid price promises.
- Entity: set up an operating company for API customers (contracts, KYC/AML for fiat and card payments, taxes, sanctions screening), plus a clear treasury policy for alpha/TAO holdings. Chutes has no disclosed entity, which is flagged as an accountability gap ([ownyourmind](https://ownyourmind.ai/tokenomics/chutes-bittensor-revenue-machine/)). Targon/Manifold is a venture-backed company.
- Data/privacy: miner traffic has "no confidentiality guarantee" by default (docs mining). **TEE attestation is the necessary control for customer prompts and outputs.** Targon's Intel-TDX + NVIDIA-CC stack is the precedent.
- Disclosure: publish revenue with third-party verification (independent dashboards). Unverifiable self-reported ARR is the main criticism of Chutes and Targon.

---

## 5. Incentive-design pitfalls & mitigations

| Pitfall | Evidence | Mitigations |
|---|---|---|
| **Weight copying** | Copiers historically got *better* vtrust than honest validators (docs validating) | Commit-reveal (on by default; timelock auto-reveal); ensure rankings change within the reveal window (fresh prompts, rotating hidden eval sets, organic-traffic scoring); `immunity_period > reveal × tempo` |
| **Validator collusion / cabals** | Yuma worst case: 40% stake + 30% utility attack at high subjectivity | κ-clipping (0.5); bonds_penalty = 1; Yuma3 + liquid alpha; **objective, reproducible scoring** (deterministic seeds, attested outputs, perceptual-hash / VMAF / CLIP-score metrics that validators can recompute); publish validator code; score by hotkey root |
| **Owner validator dominance** | Owner permit is always granted; auto-childkeying from root validators | Transparent scoring; encourage independent validators (childkey partnerships) |
| **Sybil miners / UID squatting** | Pure burn doesn't price post-registration behavior | **Collateral** (`p` 0.5–0.8, `k` ≈ 1); per-hotkey history; winner-take-most curves that make duplicate UIDs unprofitable; dedupe identical outputs; hardware attestation (TEE quotes bound to hotkey) so one GPU can't pose as many |
| **Farming emissions without real demand** | 52/128 subnets route >50% of miner incentive to the owner (live) — a symptom of "no useful work to pay for" | Score = f(verified *organic paid jobs* served + quality + latency); synthetic probes only to verify capacity; don't pay idle capacity; tie rewards to receipts signed by the gateway/validator |
| **Emissions ≫ real revenue** | Chutes 22–40× subsidy (Pine); network revenue ~6.4% of emissions | Track the **emission-to-revenue ratio** as a KPI; revenue → buybacks; set customer prices ≥ true cost; use mechanism #2 (20–30% split) for R&D benchmarks rather than burning (burning now reduces TAO share) |
| **Emission-subsidized GPU markets** | Miners underbid real cost because alpha subsidizes them; supply leaves when alpha falls | Pay for **verified quality-adjusted throughput**; require collateral per machine; make miner revenue partly USD job fees so supply survives alpha drawdowns |
| **Owner-burn penalty trap** | SN90: top-7 price → 0.43% share | Don't route miner weight to owner hotkeys; if needed, keep `MinerBurned` small |
| **Gate cliff** | Rank 32: ~21 TAO/day; rank 35: ~8; rank 50: ~1.2 | Plan for months of ~0 TAO emission after launch (slow EMA ramp); budget runway in USD; the only lever is sustained buy demand for alpha |
| **Deregistration** | Lowest EMA price after 120-day immunity (live) is pruned; holders lose most value | Get out of the bottom tier before immunity ends; buybacks; conviction locks |
| **Rug/exit perception** | Covenant exit → Conviction | Lock the owner cut (enable `owner_cut_auto_lock_enabled`), perpetual lock on the owner hotkey, multisig owner |
| **Rule-change risk** | 5 major economic changes in 2026 | Keep revenue-first unit economics; don't depend on emissions for solvency |
| **Discovery lag / new-miner churn** | Default immunity is only 13.7 h | Raise `immunity_period` (e.g., 7,200–14,400 blocks for heavy video jobs) |

---

## 6. Practical launch checklist (Sept 2026)

### Costs / timing [CONFIRMED-CHAIN unless noted]
- **Mainnet subnet lock: 590.7 TAO (~$142k) right now.** It doubles on each registration and decays linearly over 115,200 blocks (~16 d) to a 1 TAO floor. Re-check with `btcli query subnet-registration-cost --json` right before submitting (`Policy` spend caps block the call until raised). Network rate limit: 1 registration per 14,400 blocks.
- The subnet limit is full (128/128), so your registration **deregisters the lowest-EMA-price non-immune subnet**. Your subnet then has **~120 days (864,000 blocks) of immunity** to climb out of the bottom tier.
- The lock seeds your pool (no owner alpha). Starting price = median alpha price (~0.0046 TAO), so a 590-TAO lock ≈ 127k alpha in the pool [MY CALC].
- **Early economics [MY CALC]**: alpha_out ≈ 7,200 α/day (owner 1,296; miners 2,952; validators 2,952, with a large root_proportion share of the validator half initially going to root). At ~0.0046 TAO/α that is nominally ~33 TAO/day, but on a ~590-TAO-deep pool constant selling would crash the price. TAO injection stays ~0 until your EMA price climbs toward the gate bar (32nd subnet ≈ 0.0083 TAO/α EMA). **Real buy demand (revenue buybacks) is what sustains miner pay.**
- Budget extras: validator stake to clear `StakeThreshold` (1,000 TAO-equivalent stake weight) for any non-owner validator; an operating runway; buyback reserves.
- **Testnet**: lock cost 1 TAO, 1,024-subnet limit, 720-block rate limit. The **localnet** Docker image `ghcr.io/raofoundation/subtensor-localnet:devnet` has fast 0.25-s blocks, Alice pre-funded with 1M TAO, and a faucet at 1,000 TAO per call. [CONFIRMED-DOCS local-development]

### Steps
1. Owner coldkey as a **multisig** plus an Owner proxy for operations. Consider a crowdloan/lease if you want co-funding (contributors' share comes out of the 18% owner cut).
2. `btcli tx register-subnet` (or `register_network_with_identity` via raw call), then `btcli tx start-call --netuid N`. **Ask for `subnet_emission_enabled`** (root-only, starts off).
3. Set identity (`set-subnet-identity`, raw-image logo URL) and the ticker (`update-symbol`).
4. Set hyperparameters (suggested starting points for video inference):
   - `tempo` 360 (default; the minimum owner value).
   - `commit_reveal_weights_enabled` = true, `commit_reveal_period` = 1–2.
   - `immunity_period` ≥ max(commit_reveal_period × tempo + discovery lag, ~7,200 blocks).
   - `yuma3_enabled` = true, `liquid_alpha_enabled` = true (α 0.7/0.9); `bonds_moving_avg` default 900,000 or lower for faster response.
   - `max_allowed_uids` 256 (or 128 if you use 2 mechanisms). Mechanism split, for example 80% production inference / 20% quality benchmark.
   - `collateral_lock_share` 0.5–0.8, `collateral_drain_ratio` 1.0, plus a per-GPU `add_collateral` policy enforced in validator code.
   - `min_burn` raised to deter spam; `burn_increase_mult` 1.26–2.
   - `owner_cut_auto_lock_enabled` = true (signals commitment); `transfers_enabled` as desired.
   - Keep `recycle_or_burn` irrelevant by **not** routing weight to owner hotkeys.
   - Bump `weights_version` on every validator release.
5. Validators: run an owner validator (it always gets a permit). Recruit independent validators or root validators via childkeys. Note that root validators may already be auto-childkeyed to the owner hotkey.
6. **SDK: bittensor 11.1.0** (stable, Aug 14 2026; 11.3.0rc42 on Sep 8 2026; Python 3.10–3.14). v11 unifies the SDK and btcli, with intents: `bt.SetWeights`, `bt.BurnedRegister`, `bt.AddCollateral`, etc. A migration guide from v9/v10 exists (https://bittensor.com/docs/migration). **Signed requests (btauth/1)** is the documented hotkey-signed HTTP protocol between validators and miners (https://bittensor.com/docs/guides/signed-requests). [CONFIRMED PyPI + docs]
7. Validator software pattern: an async loop that reads the metagraph (with collateral fields), dispatches organic plus synthetic video jobs, verifies TEE attestation quotes bound to miner hotkeys, scores quality/latency/throughput by **hotkey root** with persisted history (gaps never improve a score), zeroes blacklisted or under-collateralized hotkeys, then calls `bt.set_weights(...)` once per tempo (respecting the 100-block rate limit) with `mechid` per mechanism. The SDK handles commit-reveal automatically.
8. Revenue loop: API gateway → customer billing (company) → a published buyback policy with an on-chain address or EVM contract, limit prices and MEV shielding → alpha held/locked to the owner hotkey (conviction) → a public dashboard of revenue vs. emission.

---

## Appendix: key raw data

- Mainnet storage read 2026-09-11, block 9,045,154, spec 455: NetworkMinLockCost 1 TAO; NetworkLastLockCost 460.577 TAO; reg cost 590.714 TAO; NetworkLockReductionInterval 115,200; NetworkRateLimit 14,400; SubnetLimit 128; TotalNetworks 129; NetworkImmunityPeriod 864,000; TaoWeight 0.18; StakeThreshold 1,000 TAO; TotalIssuance 11,330,335 TAO; TotalStake 7,318,081 TAO; EmissionGateBar 0.008843; MaturityRate 311,622; root SubnetTAO 5,298,381 TAO.
- Testnet: NetworkMinLockCost 1; reg cost 1 TAO; NetworkRateLimit 720; SubnetLimit 1,024; TotalNetworks 562.
- Code refs: `pallets/subtensor/src/coinbase/subnet_emissions.rs` (get_shares, gate, flow), `coinbase/run_coinbase.rs` L722–802 (MinerBurned), `lib.rs` (EmissionBarRank=32, EmissionGateExponent=3, EmissionBarQuantile=0.61, FlowHalfLife 216,000, MaxMechanismCount 2, SubnetLimit 128), `runtime/src/lib.rs` (MinLockCost 1000 TAO default, NetworkImmunity 1,296,000 default, SubnetOwnerCut 11,796, MaxAllowedValidators 128, ImmunityPeriod 4,096, InitialTaoWeight ~5.27%).
- Paper: Maymin, "Common Risk Factors in Decentralized AI Subnets" (arXiv 2603.29751, Mar 31 2026). Small-minus-big alpha factor of 1.01%/day that fell from 1.17% to 0.51% after the halving; only implementable below ~$10k AUM. https://arxiv.org/abs/2603.29751
