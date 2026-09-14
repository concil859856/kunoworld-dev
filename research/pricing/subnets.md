# How Bittensor compute and inference subnets set customer prices and miner pay (as of 2026-09-14)

Research for KunoWorld: a video-generation subnet (LTX-2.5, MiniMax H3) with Private mode (TDX + NVIDIA CC, E2E) and Standard mode (also served by a no-TEE open tier at a lower rate).

These notes **extend**, not repeat:
- `/video/research/research_tee_subnets.md` (Lium, Engy, gm, Targon, KubeTEE, Basilica; TEE and mechanism design);
- `/video/research/research_chutes.md` (Chutes teardown);
- `/video/research/research_bittensor.md` (dTAO rules, the June 2026 burn penalty and the emission gate);
- `/video/research/research_market.md` (video API and GPU prices).

Facts already in those files are cited briefly. New facts carry dates and sources.

**Legend**
- **[CONFIRMED-CODE]**: read in the repo at HEAD on 2026-09-14 (file path given).
- **[CONFIRMED-DOC]**: the team's own docs, pricing page, live official API or dashboard, fetched 2026-09-14.
- **[CONFIRMED-CHAIN]**: read from finney storage or a public artifact that mirrors chain values.
- **[3RD-PARTY]**: analysts, aggregators, news, podcasts. Not independently verified.
- **[UNVERIFIED]**: conflicting, single-sourced, or from a search-engine summary whose page I could not open.
- **[MY CALC]** / **[MY INFERENCE]**: my own arithmetic or interpretation.

**Method and limits**
- Repos read at HEAD via raw.githubusercontent.com and the GitHub API:
  - `Datura-ai/lium-io` (HEAD e6ce534, 2026-09-14)
  - `hanlinai/engy` (9dc14b4, 2026-09-13)
  - `taostat/gm-validator` (6993bb2, 2026-09-05) and `gm-miner`
  - `chutesai/chutes-api`
  - `manifold-inc/targon` (9fb0722, 2026-08-23)
  - `KubeTEE-AI/kubetee-subnet`
  - `one-covenant/basilica` (last commit 2026-08-27)
  - `RaoFoundation/subtensor` (spec 456)
- Live endpoints: `api.engy.ai/v1/models`, `provider.engy.ai/*`, `openrouter.ai/api/v1/models/*/endpoints`, the gm public S3 bucket, `stats.targon.com/api/miners`, `lium.io/api/*`, `api.chutes.ai/*`, `saygm.com`.
- The WebSearch budget (200 calls, shared with helper agents) ran out mid-session, so a few secondary claims remain search-snippet-only and are marked [UNVERIFIED].
- TAO/USD used in my calculations: **$233**. The gm finalizer used CoinGecko $233.36 at block 9,059,655 (2026-09-13); Coinbase showed $233.27 on 2026-09-14.

---

## 0. Summary table

| Subnet | Who sets the customer price | Customer price vs market | What miners are paid, and from what | Unused miner emission | Revenue (best available) | Emission value ÷ revenue |
|---|---|---|---|---|---|---|
| **SN51 Lium** (GPU rental) | **Provider** asks in USD/GPU-hr, inside a platform band of 0.5×–2.5× a reference price (the 30-day rental median) | Median asks ~10–30% below RunPod Community, 20–50% below Vast median | **95% of rental fees** (paid in alpha) **plus** emissions. Idle eligible GPUs get about the reference price per hour in alpha (capped); rented GPUs get a small emission top-up | Weight to UID 47 ("burn"). Chain `MinerBurned` for SN51 read 0 on 09-11 | $964K billed Aug 2026 (team claim via tao.media) | ~1.5–3.6× [MY CALC, depends on emission share] |
| **SN53 Engy** (LLM API) | **Platform** price card | **Undercuts** the OpenRouter median by 27–70% on 4 of 5 shared models (−10% on GLM-5.3-Flash) | **Emissions only**: billed tokens × team-set `score_rate`, independent of buyer price | All weight to owner (burn) if no billed traffic | Not disclosed. Buyback-and-burn of $49.5K from 2026-08-12 to 09-13 is public | Unknown (buyback ≈ 1/17 of emission value) |
| **SN28 gm / sayGM** (LLM API resale) | Each **miner** declares a % discount off gm "retail" (= first-party list price). Buyers see 8–70% off list | Below list by construction ("never more than list"; "30% cheaper on average") | **Emissions only**: weight = USD at discounted retail ÷ USD miner pool. Miners pay their upstream bills themselves | Burn to owner uid 3 when undersubscribed | Buyer-side ≈ $13.8–16.3K/day (public S3, 09-03→09-13) [MY CALC] | Miner pool ÷ miner earnings ≈ 1.12. All emission ÷ spend ≈ 2.3–2.7× [MY CALC] |
| **SN64 Chutes** (serverless inference) | **Platform**: $4.50/hr basis × GPU multiplier, per-model overrides | Formula is cheap. Overrides (GLM-5.x, Kimi) are at market. Video is pure GPU time ($0.0005/s on PRO 6000) | **Emissions only**: attested GPU-time × multiplier (TEE ×2.25, urgency and revenue boosts) | No burn; weights normalized | PAYG ≈ $9.15K/day, 2026-09-04→13 (live endpoint, excludes subscriptions) | ~5.7–8.9× [MY CALC]; Pine (Mar 2026) 22–40× |
| **SN4 Targon** (confidential GPU rental) | **Platform** (Tower) sets customer prices; miner-side "auction" prices set by Tower | Third-party: confidential H200 "from $1.90/hr" [UNVERIFIED] | **Emissions only**: per card-hour min(target_price×target_cards ÷ cards, max_price), in USD | Burned via Tower burn keys, residual to uid 28 | $10.4M ARR self-reported, unaudited | Pine 1.7×; ~2.2× on the self-reported figure [MY CALC] |
| **SN90 KubeTEE** (confidential K8s) | Customers buy SN90 alpha on the open market; spent alpha recycled. Price card only for miner pay | n/a (resells idle capacity through sayGM at sayGM prices) | **Emissions only**: USD card × capacity × tenure ÷ pool, clamped down to Targon's live payouts | Recycled via owner UID → `MinerBurned` 0.766 → share ~0.43% | Free window 14.8B tokens, then paid via sayGM | n/a |
| **SN39 Basilica** (GPU rental) | **Miner bid** per GPU-hr; validator picks the lowest eligible; customer price = bid + platform markup | Not public | CU: min(bid, per-CU budget) × vested hours; RU: revenue × revenue_share_pct (emissions) | Burn uid (default 204) + optional forced burn | Not found. Covenant announced its exit 2026-04-10, but the repo is still active in Aug 2026 | n/a |

**Three archetypes**
1. **Revenue-share marketplace.** Lium: the miner sets the price and keeps 95%; emissions are a capped idle subsidy.
2. **Emission-paid USD target, capped by the pool.** gm, Targon, KubeTEE, Basilica CU. Miner pay is USD-denominated, but the money is emissions. Customer revenue stays with the platform (or goes to buybacks).
3. **Team-set work units, normalized.** Engy `score_rate`, Chutes GPU-time × multiplier. Customer price is decoupled from miner pay; pay is relative share of the pool.

---

## 1. SN51 Lium (Datura): miner-set prices inside a platform band, 95% fee share, idle-GPU emission floor

### 1.1 Who sets rental prices
- **Providers set `price_per_gpu`** (USD/GPU-hr) through the portal or the CLI route `/executors/{id}/update-price` [CONFIRMED-CODE `lium/provider/_routes.py`, `neurons/miners/src/models/executor.py`]. Docs: "Providers set their own hourly USD rates" [CONFIRMED-DOC https://docs.lium.io/providers/rewards/rental-fees].
- **Platform band around a per-GPU-model reference price** (live `https://lium.io/api/v1/shared-config`) [CONFIRMED-DOC]:
  - Floor 0.5× (`machine_min_price_rate`); hard cap 2.5× (`machine_max_price_rate`).
  - The validator zeroes a node priced above reference × max [CONFIRMED-CODE `neurons/validators/src/services/task/score_calculator.py`].
  - **Soft limit:** an unrented node priced above `machine_prices_p90 × 1.1` loses the unrented incentive but stays listed (`incentive/rental_price.py`, `SOFT_LIMIT_PRICE_RATE = 1.1`). A code comment says p90 is "raw Vast.ai p90 $/GPU-hour" [CONFIRMED-CODE].
- **The reference price is now a market median.**
  - Hard-coded table from 2025-12-09; **re-anchored to the "30d rental median" on 2026-06-26** (lium-core commit 10e7446011) [CONFIRMED-CODE].

    | GPU | Before | After |
    |---|---|---|
    | H100 HBM3 | $1.26 | $1.494 |
    | H200 | $1.90 | $2.85 |
    | B200 | $2.99 | $4.25 |
    | B300 | $3.67 | $5.10 |
    | RTX 5090 | $0.17 | $0.65 |
    | RTX 4090 | $0.14 | $0.30 |
    | PRO 6000 WS | $0.84 | $1.00 |

  - Live today: H200 $3.10, B300 $5.88 [CONFIRMED-DOC live API].
- **Platform fee:** live `rental_fees_rate` 0.95. Docs: "You earn 95% of every rental payment". The packaged lium-core default is still 0.9 (stale) [CONFIRMED-DOC/CODE].
- **Payout currency:** rental fees reach the provider coldkey **daily, in alpha at the going rate**, with a 2-day delay at 17:00 UTC. A misbehaviour penalty cancels that rental's fees and refunds the renter [CONFIRMED-DOC https://docs.lium.io/providers/rewards/payouts]. Whether that alpha is **bought on the market with renter payments** is [UNVERIFIED].
- **Renter billing:** per second, no minimum; storage $0.00005/GB-hr [CONFIRMED-DOC https://lium.io/pricing].

### 1.2 Current prices per GPU-hour (2026-09-14)
- **Lium:** 139 listed nodes / 450 GPUs from `lium.io/api/executors`.
- **RunPod:** https://www.runpod.io/pricing (page dated 2026-09-13), Secure / Community.
- **Vast:** `console.vast.ai/api/v0/bundles`, verified on-demand offers; `dph_total` may include default storage. [CONFIRMED-DOC for all three]

| GPU | Lium live asks (median) | Lium reference | RunPod Secure / Community | Vast min / median |
|---|---|---|---|---|
| H100 80GB HBM3 (SXM) | $1.41–2.75 ($2.08) | $1.494 | $3.49 / $2.69 | $2.00 / $2.93 |
| H100 PCIe | $1.50–2.24 | $1.1988 | $2.89 / $1.99 | — |
| H200 | $2.75–4.20 ($3.20) | $3.10 | $4.59 / $3.59 | $3.98 / $5.00 |
| B200 | none listed (49 GPUs, 100% rented, median $5.60) | $4.25 | $6.79 / $5.98 | $5.63 / $8.14 |
| B300 | none listed (73 GPUs, 100% rented, median $8.00) | $5.88 | $7.89 / $6.94 | $9.38 / $11.48 |
| RTX PRO 6000 SE / WS | $1.19–1.85 ($1.29) / $1.25–1.46 | $1.00 | $2.09 / $1.69 | WS $1.28 / $1.64 |
| RTX 4090 | $0.30–0.58 ($0.35) | $0.30 | $0.74 / $0.34 | $0.30 / $0.61 |
| RTX 5090 | $0.50–0.69 ($0.59) | $0.65 | $0.99 / $0.69 | $0.44 / $0.75 |

- Utilization (from `/api/machines`): H200 89%, H100 HBM3 73%, PRO 6000 SE 61%, 5090 59%, 4090 46% [CONFIRMED-DOC].
- **Takeaway:** Lium does *not* set prices far below market. Asks sit 10–30% below RunPod Community, and the fleet is heavily rented. Below-market pricing is bounded by the 0.5× floor.

### 1.3 How emissions subsidize prices [CONFIRMED-CODE `incentive/rental_price.py`, `burn_service.py`, `core/config.py`; live API]
- **Two pools:**
  - Rented ("mining") pool = `1 − total_burn_emission`.
  - Unrented pool: `rental_share = Σ(unrented eligible GPU-hour reference cost × 1.2 h) / 0.41 / epoch_subnet_emission_USD`, capped at `total_burn_emission`.
  - Burn = `total_burn_emission − rental_share`, sent as weight to **UID 47** (pinned coldkey). Whether UID 47 actually burns can't be checked from code.
- **What an idle eligible GPU earns:** roughly its **reference price per hour in alpha**, times cap, sysbox and driver multipliers. Live `usd_per_epoch_unrented` = reference × 1.2 exactly for H100 HBM3 ($1.49/hr) and B200 ($4.25/hr). Lower for H200 ($2.04), B300 ($5.10), PRO 6000 ($0.59), 5090 ($0.26), 4090 ($0.25), which looks like cap dilution [MY INFERENCE].
- **What a rented GPU earns:** 95% of its ask **plus** a small rented-pool emission: H100 HBM3 $0.18/hr, H200 $0.50, B200 $0.80, B300 $1.15, PRO 6000 SE $0.12, 5090 $0.055, 4090 $0.029.
- **Rented scoring:** `score × gpu_portion × gpu_count / total_gpu_count_of_model`. `gpu_portion` is a backend-pushed **EMA of revenue per GPU type** (`portion += 0.01 × (revenue − portion)`). The `GPU_MODEL_RATES` table in `const.py` (H200 0.56 …) is **only a fallback** when Redis is empty. This corrects the reading in research_tee_subnets.md.
- **Burn-share history:**
  - `TOTAL_BURN_EMISSION` went 0.90 → 0.95 → 0.91 (all 2025-12-10), then 0.87 on 2026-06-25 ("raise rented mining-pool share to 0.13"), then moved to the backend on 06-26.
  - **Live 2026-09-14: 0.90** (rented pool 10%).
  - **Conflict:** docs still say "Rented pool 13% — fixed".
- **Caps and gates for idle pay:**
  - Caps raised on 2026-06-29: {1: 10, 8: 64} GPUs per model; B300 {1: 10, 8: 32}. Only 1× and 8× configurations are eligible.
  - Gates: sysbox, disk ≥ 1.5× VRAM, power-cap capability, the soft price limit. 8× H200/B200/B300 also need NCU counters, GPU splitting, or a **verified TDX quote**.
- **Idle-node filler jobs:** Lium-owned default jobs (PEARL / DPHN / **ENGY**) run on idle nodes, and "Lium keeps the unrented incentive" (`const.py` comments) [CONFIRMED-CODE]. Cross-subnet demand exists: idle Lium GPUs mine Engy (SN53).

### 1.4 Collateral
- Formula: `required_deposit_amount[model]` (TAO) × gpu_count × 7 days (`collateral_contract_service.py`). Per GPU: H100 HBM3 0.721 τ (~$168), H200 1.106 τ (~$258), B200 1.561 τ, B300 1.918 τ, PRO 6000 SE 0.2975 τ (~$69), 5090 0.098 τ, 4090 0.07 τ [CONFIRMED-CODE].
- **Not enforced:** `ENABLE_NO_COLLATERAL = True` (`core/config.py:203`). `IS_NOT_DEPOSITED_SCORE_MULTIPLIER = 0.5` is a dead constant. Only 4 of 139 listed nodes show `collateral_deposited=true` [CONFIRMED-CODE/live]. This corrects research_tee_subnets.md §5.

### 1.5 Revenue and subsidy
- **Reported revenue:**
  - $432K/month, traced to team reports; 4.44–6.2% emission share; subsidy **3.5–4.9×**. ownyourmind (2026-05-13, updated 08-17: SN51 at 5.72%) [3RD-PARTY https://ownyourmind.ai/tokenomics/lium-bittensor-subsidy-ratio/].
  - **$964K billed in August 2026** (+36% MoM), 1,187 renters, 7,697 rentals, 63% started by agents, median rental 1.15 h. Plus **"$1M worth of alpha burned using product revenue"** [3RD-PARTY citing the team: https://www.tao.media/lium-reports-964k-month-as-it-tops-bittensors-subnet-market-cap-rankings/, 2026-09-11].
- **Conflicts:**
  - pctechmag (Sept 2026) says 7,549 rentals and 900 paying accounts, and "no floors or caps", which code and docs contradict.
  - Unsupervised Capital's Q2 letter says $12M annualized (2026-08-05), against $5.2M annualized in May.
- **Emission share conflict:** 5.72% (ownyourmind, Aug 17) vs **13.4%** from my chain reconstruction of final shares on 2026-09-11 (research_bittensor.md §1.4).
- **[MY CALC]** At $964K/month ≈ $31.1K/day and TAO $233, emission value is $48K–$112K/day, giving **~1.5–3.6×**. Part of the miner emission is routed to UID 47, so emissions actually paid to miners are lower.

### 1.6 Observations for KunoWorld
- The **burn weight goes to UID 47, not an owner hotkey**. The chain's `MinerBurned` for SN51 read **0** in the 2026-09-11 snapshot, so Lium's large "burn" pool does not trigger the June 2026 penalty [MY INFERENCE from code + chain; unverified whether UID 47 is owner-associated]. It relies on a detail of how the chain defines owner hotkeys and could be closed by a rule change. **Do not copy it.**
- Lium is the only large subnet where **miners earn customer revenue directly** (95%). Emissions are an explicit, capped, idle-capacity floor. That design is the least dependent on emissions of those studied.

---

## 2. SN53 Engy: platform undercuts the market; miners paid by team-set score_rate; revenue funds a public buyback-and-burn

### 2.1 Customer prices vs OpenRouter (all fetched 2026-09-14)
- Engy live list `https://api.engy.ai/v1/models` = https://engy.ai/pricing [CONFIRMED-DOC]: "Per-token, pay as you go. No subscriptions and no minimums."
- OpenRouter endpoints API, excluding `fast` tags [CONFIRMED-DOC https://openrouter.ai/api/v1/models/<id>/endpoints]. Prices are $ per 1M tokens, input / output.

| Model | Engy | OR median (n) | OR cheapest | Engy vs median | Engy vs cheapest |
|---|---|---|---|---|---|
| GLM-5.2 | $0.68 / $1.50 (cache $0.18) | $1.40 / $4.40 (25) | $0.487 / $1.531 | **−51% / −66%** | +40% / −2% |
| Qwen3.6-35B-A3B | $0.045 / $0.30 | $0.133 / $1.00 (11) | $0.05 / $0.70 | **−66% / −70%** | −10% / −57% |
| Kimi-K3 | $1.95 / $9.75 | $3.00 / $14.63 (18) | $2.10 / $10.95 | **−35% / −33%** | −7% / −11% |
| GLM-5.3 | $0.98 / $3.08 | $1.35 / $4.40 (27) | $0.92 / $3.14 | −27% / −30% | +7% / −2% |
| GLM-5.3-Flash | $0.135 / $0.45 | $0.15 / $0.50 (28) | $0.075 / $0.25 (possibly a batch endpoint) | −10% / −10% | +80% / +80% |

- Engy also lists deepseek-v4.1-flash ($0.04 / $0.08), deepseek-v4-flash-0731 ($0.045 / $0.09) and qwen3.8-27b ($0.045 / $0.32).
- **Deliberate undercut?** No explicit pricing-strategy statement was found. The pattern suggests yes: at or below the *cheapest* OpenRouter provider on output for GLM-5.2, Qwen3.6 and Kimi-K3, and ~35% below Chutes' Kimi-K3 price ($3 / $15) [MY INFERENCE].
- **Cost basis is genuinely low:** GLM-5.2 NVFP4 on RTX 5090 clusters; Qwen3.6 on 8× 4090-48G at ~4,500 tok/s [CONFIRMED-DOC `docs/ANNOUNCEMENT.md`]. So the undercut is at least partly real cost advantage (consumer GPUs, FP4), not only emissions [MY INFERENCE].
- **Free tier:** none on the pricing page. Any free, internal or probe traffic scores nothing (below).

### 2.2 How miner pay is set [CONFIRMED-DOC `docs/SN53_ONE_PAGER.md`, `docs/ANNOUNCEMENT.md`]
- Score per (miner, model) = `floor(Σ tokens × score_rate[model] / 1000)` if all gates pass; normalized to 65535; **no billed traffic → 100% to the owner hotkey (burn)**.
- **`score_rate`** is "a per-model blended µUSD-per-1k-tokens rate **we set**, deliberately *not* the buyer-facing price card … immune to buyer discounting".
  - How it changes: "Expect score rates, gate targets, and sampling to move as they meet real traffic; we announce changes before they land."
  - **The actual `score_rate` values are not published.** They're absent from the repo, and `provider.engy.ai` pages show requests but not rates or billed USD [CONFIRMED-DOC absence].
  - The validator repo only mirrors master-signed results; no rate arithmetic is present [CONFIRMED-CODE `validator/validator.py`].
- **Billed-only:** only HTTP 2xx **and** `cost_micro > 0` count ("free-tier, internal, and probe traffic cannot mint weight").
- **Relation to customer price:** none by design. Miners get emission share ∝ tokens × score_rate. Customer revenue goes to Engy, which publishes a **buyback and burn**:
  - Totals: **7,688.28 α = $49,501.65 burned, 2026-08-12 → 2026-09-13**, each with a Finney block link.
  - Examples: 2026-09-13 1,758.69 α ($10,546.58, block 9,057,890); 09-07 845.22 α ($5,636.21); 09-04 760.31 α ($5,175.00).
  - Source: [CONFIRMED-DOC https://provider.engy.ai/buyback]. The share of revenue used is **not stated**.
- **Epoch length:** now **7 days**. `provider.engy.ai/epochs`: epoch 13 = 2026-09-09 08:00 → 09-16 08:00 [CONFIRMED-DOC]. This resolves the daily-vs-weekly conflict in research_tee_subnets.md: weekly is live.

### 2.3 Traffic and revenue signals
- Requests, last 30 days: **25,427,167**; yesterday 646,887 (`provider.engy.ai/requests`, 2026-09-14 14:05 UTC) [CONFIRMED-DOC].
  - By model: qwen3.6-35b 9.42M, qwen3.8-27b 7.42M, deepseek-v4-flash 3.87M, glm-5.2 3.36M, kimi-k3 0.94M.
  - 24-hour success rate 89.5%.
- Miners per epoch:
  - Epoch 12 (09-02→09): 72 miners, 3,654,747 requests. Epoch 11: 159 miners, 4,478,389 requests.
  - Epoch 13 (open): 69 miners; only **27 of 223** miner rows had requests in the current epoch [CONFIRMED-DOC].
- **Revenue: not disclosed anywhere I could reach.**
  - tao.media (2026-07-28): no figures, "alpha up ~300% in the past month" [3RD-PARTY].
  - KuCoin community post repeats the prices [3RD-PARTY].
- **[MY CALC]** SN53 had ~3.1% of TAO emission (≈113 TAO/day ≈ $26K/day) on 2026-09-11, so miners' 41% ≈ $10.8K/day. Buyback ≈ $1.55K/day ≈ **1/17 of emission value**.

### 2.4 Anti-wash-trading analysis [MY INFERENCE]
- "Billed-only" stops *free* traffic from minting weight, not **paid self-dealing**.
- A miner can buy tokens at $0.045 / M and serve them. That is profitable whenever the emission value per scored token exceeds price plus GPU cost, which is likely while paid traffic is small relative to a ~$10K/day miner pool.
- Engy's real defences:
  1. The gateway routes by **fair round-robin across all eligible workers including the first-party cluster**, so a buyer can't target its own miner and captures only its capacity share of its own spend.
  2. Admission probes and SLA gates.
  3. Collateral/slashing in the one-pager (enforcement not verified).

---

## 3. SN28 gm / sayGM: miners declare discounts off list; paid in emissions; buyers keep the discount

### 3.1 Mechanism [CONFIRMED-CODE/DOC `gm-miner/cli/src/pricing.rs`, `README.md`, `docs/sourcing.md`; `gm-validator/.../alpha_economics.py`, `scoring.py`]
- **`--discount-pct`** is in [0, 99.90]. `MAX_DISCOUNT_BP = 9_990` "keeps per-request revenue strictly positive". Integer nano-dollar arithmetic.
- **What gets sent:** the discount in basis points, not absolute prices. "The registry resolves them against its own retail when it records the offer, so … a retail change in between moves what you are paid."
- **Retail definition:** settlement is on the **buyer product's retail**, whichever upstream route served it: `your rate per Mtok = buyer_retail[dim] × (10000 − discount_bp)/10000`, over up to 10 dimensions.
  - Worked example in docs: `zai/glm-5.2` at retail $1.40 / $4.40, 5% discount → $1.33 / $4.18.
  - $1.40 / $4.40 equals Z.AI's own list on OpenRouter; Claude Opus 5 retail $5 / $25 equals Anthropic list. So **retail = the first-party list price** [CONFIRMED-DOC + my check against the OpenRouter API].
- **Routing:** the gateway keeps each worker's **cheapest surviving route**, and each worker gets **one lottery entry** per request.
- **Miner cost:** "Your spread is that figure minus whatever the upstream charges you." The docs explicitly discuss upstreams sold "by subscription or prepaid pack" and warn that a route can be unprofitable (DeepInfra cache price above buyer cache retail, 2026-08-26).
- **Miner terms:** miners warrant their provider accounts permit reselling; gm disclaims liability (`docs/miner-terms.md`) [CONFIRMED-DOC].
- **Weights:** `weight_i = consumed_usd_i / pool_usd`, `pool_usd = emissions_alpha × 0.41 × alpha_price_usd`. Under-subscription remainder → owner uid (mainnet `SUBNET_OWNER_UID=3`) as burn; over-subscription renormalized down [CONFIRMED-CODE].
- **Who pays miners:** "miners earn **alpha emission, not dollars**" [CONFIRMED-DOC https://saygm.com/miners].

### 3.2 Buyer prices [CONFIRMED-DOC https://saygm.com, 2026-09-14]
- 49 models; "30% cheaper than list, on average"; "≤ Retail: never more than list"; no subscription; "start instantly, no card required" (whether free credits come with signup is not stated).
- Examples (list → sayGM, per 1M tokens, input / output):

  | Model | List | sayGM | Discount |
  |---|---|---|---|
  | Claude Opus 5 | $5 / $25 | $4.15 / $20.75 | −17% |
  | GPT-5.5 | — | — | −16.1% |
  | Gemini 3.5 Flash | — | — | −8% |
  | DeepSeek-V4-Flash | $0.44 / $1.32 | $0.13 / $0.40 | −70% |

- The discounts match the declared miner discounts in the S3 data (mostly 700–1650 bp). Buyers most likely pay about **the routed miner's discounted price** [MY INFERENCE].

### 3.3 Actual traffic and pay, from gm's public S3 [CONFIRMED-CHAIN / public artifacts]
- **Source:** `https://gm-mainnet.s3.gra.io.cloud.ovh.net/v1/finalized/epoch=<N>/{epoch_summary.json,aggregated.jsonl}`. Epochs are 361 blocks.
- **Snapshot:** epoch 25095 (finalized 2026-09-13T16:03Z): alpha 0.021804 τ = **$5.088**; `emissions_alpha` 360 per epoch; TAO $233.36 (CoinGecko).
- **[MY CALC]** over 196 epochs (epochs 24900–25095, 2026-09-03T20:51Z → 09-13T16:03Z; one aggregated file missing):

| Window | Miner earnings (discounted retail) | Implied buyer retail | Miner pool (0.41 × α × price) | Pool ÷ earnings | Requests | Distinct miner hotkeys |
|---|---|---|---|---|---|---|
| Last 20 epochs (~1 day) | $12,759 | $15,276 | $14,698 | 1.15 | 231,337 | 47 |
| Last 140 (~7 days) | $96,794 | $112,871 | $108,156 | 1.12 | 1,589,998 | 83 |
| All 196 (~9.8 days) | **$134,969 (~$13.8K/day)** | $159,631 | $150,848 | **1.12** | 2,406,288 | 88 |

- **Earnings by upstream:** Anthropic $77.4K (57%), OpenAI $26.2K (19%), Moonshot $16.2K (12%), "gm" $7.1K, Z.ai $5.5K, Gemini $1.3K, Qwen $1.0K.
- **Live miners page:** epoch 25,113 traffic value $654.67, 11,053 requests, 40 active miners [CONFIRMED-DOC https://saygm.com/miners].
- **Conflict:** Subnet Alpha ("~1 active miner", alpha 0.017 τ, ~19K τ market cap; https://subnetalpha.ai/subnet/gm/) is **stale**. Subnet Alpha also still names Foundry Accelerate as operator; the code points to Taostats [conflict kept from prior notes].
- **What this implies [MY INFERENCE/CALC]:**
  - **Near-full subscription.** gm's miner pool is only ~12% larger than what miners are owed, so ~11% of miner emission goes to the burn uid → `MinerBurned` ≈ 0.1 → the TAO share is multiplied by ≈ 0.9.
  - **Miner pay is 100% emission-funded, at close to what buyers pay.** The emission subsidy ratio on the miner pool ≈ 1.1. Counting all participants (miner pool ÷ 0.41 ≈ $37.5K/day), emission value ÷ buyer spend ≈ **2.3–2.7×**.
  - **Who keeps buyer USD:** not disclosed. No buyback page or policy was found [UNVERIFIED].
  - **How miners can profit when paid ≤ retail and 57% of earnings are Anthropic models:** they must source below list (credits, enterprise discounts, subscription or prepaid packs). The docs name that and the terms push the ToS risk onto miners. Supply depends on upstream arbitrage that providers can shut off.
  - **Wash trading is roughly zero-sum.** A self-dealer pays ≈ X and earns ≈ X of alpha (no renormalization upward, because the residual is burned), then loses upstream cost. That makes gm structurally resistant, **but only because it burns the residual**, which the June 2026 rule now taxes.
- **KubeTEE (SN90)** supplies idle GPU capacity to gm and **swaps SN28 alpha earnings into SN90 alpha and recycles it**. First fill 2026-08-23: 134.45 SN28 α → 52.58 SN90 α (~τ2.24), extrinsic `8907772-0011` [CONFIRMED-DOC https://github.com/KubeTEE-AI/kubetee-subnet/blob/main/docs/SN28-SN90-ALPHA-RECYCLE.md].

---

## 4. SN64 Chutes: $4.50/hr compute-unit basis; subsidies wound down in 2026

(Architecture, scoring and TEE are in research_chutes.md. This section adds pricing-specific findings.)

### 4.1 The formula at HEAD [CONFIRMED-CODE `chutesai/chutes-api`]
- **Basis:** `COMPUTE_UNIT_PRICE_BASIS` lives in `api/gpu.py` (not `api/constants.py`) and equals the highest `hourly_rate`: B200 = B300 = **$4.50**. Per-GPU multiplier = own rate ÷ 4.50.
- **Hourly rates at HEAD:** 3090 $0.25, 4090 $0.40, 5090 $0.70, A6000 $0.50, L40S $0.85, A100-80 $1.20, **pro_6000 $1.80**, H100 $1.79, H100 NVL $2.25, **H200 $2.75**, MI300X $3.00, B200/B300 $4.50.
- **History of the basis:**

  | Commit | Date | Change | B200 (basis) | H200 | H100 | pro_6000 |
  |---|---|---|---|---|---|---|
  | 81d5c15993 | 2025-08-04 | — | $4.00 | $2.70 | $1.40 | — |
  | b40094eec6 | 2025-09-10 | — | $3.50 | $2.30 | $1.50 | $1.10 |
  | 976fa3da9e | 2025-10-03 | "hourly rate adjustments to market rates" | $4.50 | $2.75 | $1.79 | $1.80 |
  | — | 2025-12-22 | B300 added at $4.50 | — | — | — | — |

  **No rate changes in 2026.**
- **LLM pricing:**
  - Per 1M tokens = hourly × gpu_count × 0.01358695 (in) / × 0.05434782 (out), floor $0.01.
  - Cache discount 0.9 (added 2026-02-03).
  - **Correction to the existing notes:** the ×16/concurrency surcharge applies only when the chute also has a non-zero `chute.discount` (`get_mtoken_price`).
- **Diffusion (per step):** hourly × 0.002.
- **Per-model DB `PriceOverride`s** (per user or all users) take precedence over the formula:
  - Formula-priced: Mistral-Nemo $0.0245 / $0.0978.
  - Override-priced: Kimi-K3 $3 / $15, GLM-5.2 $1.25 / $3.95, GLM-5.1 $0.98 / $3.08, Kimi-K2.6 $0.58 / $3.40, DeepSeek-V3.2 $1 / $1. GLM-5.1 ≈ 3.3× the 8×H200 formula price [MY CALC].
  - Source: `https://llm.chutes.ai/v1/models` [CONFIRMED-DOC].
  - Chutes is a provider on only 6 OpenRouter models, at the same prices as direct [CONFIRMED-DOC OpenRouter API].
- **No TEE surcharge to users.** TEE ×2.25 is a miner-side multiplier only. Chutes absorbs the TEE cost premium with emissions [CONFIRMED-CODE; framing is MY INFERENCE].

### 4.2 Video chutes: pure GPU time
- `LTX-25-Video` and `turbowani2v` have no `standard_template`, so neither per-token nor per-step pricing applies.
- Charge per request = `ceil(wall-clock s) × compute_multiplier × chute.boost × manual_boost × $4.50/3600`, minus any discount. The **autoscaler urgency boost is charged to users** too [CONFIRMED-CODE `api/chute/util.py` ~L1515–1645].
- Live values: price $1.80/hr ($0.0005/s), multiplier 0.4, boost 1.0, `tee: true` [CONFIRMED-DOC live API].
- **Usage:**
  - `LTX-25-Video` (created 2026-08-13): concurrency 3; up to 20 s 1080p / 13 s 1440p / 6 s 4K. **0 instances, 0 invocations.**
  - `turbowani2v`: 1 hot instance.
    - Sept 3–14: $12.07 over 359 calls ≈ $0.034/call ≈ 67 billed GPU-seconds. Subscription-covered calls are billed $0.
    - Media-agent read of `invocation_count` at another time: 26 (window unknown) [CONFLICT: different counters and windows].
- **Cost per output second at $0.0005 per GPU-second** [MY INFERENCE; PRO 6000 ≈ 5090 speed assumed]:

  | Model | Benchmark (3rd-party) | GPU-s per output s | Cost per output s |
  |---|---|---|---|
  | LTX-2.3 distilled, 1280×704 | 49.8 s per 97 frames on a 5090 | 12.3 | ≈ $0.0062 |
  | LTX-2.3 distilled, 768×512 | — | 10.8 | ≈ $0.0054 |
  | TurboWan2.2-I2V-A14B-720P | 38 s per 5 s clip, excluding encode/decode | ≥ 7.6 | ≥ $0.0038 |
  | TurboWan, observed billing | ~67 GPU-s per call (5 s clip assumed) | ~13 | ~$0.0067 |

  - Sources: https://huggingface.co/datasets/witcheer/rtx-5090-benchmarks; https://github.com/thu-ml/TurboDiffusion.
  - That is **≈15–20× cheaper than the LTX official API** ($0.09–0.12/s) before any margin, which Chutes doesn't take on raw GPU time.

### 4.3 Subscriptions and free tier timeline

| Date | Change | Source |
|---|---|---|
| 2025-07 | Free access ended; $5 deposit → 200 free messages/day | [3RD-PARTY rpwithai]; code still knows "Quota-200 users (one-time $5 payment)" [CONFIRMED-CODE `api/invocation/util.py`] |
| 2025-08-04 | Base $3 (300 req/day), Plus $10 (2,000), Pro $20 (5,000), Enterprise; $5 route closed to new users. `SUBSCRIPTION_TIERS = {300: 3.0, 2000: 10.0, 5000: 20.0}` still at HEAD | [CONFIRMED-CODE `api/config/__init__.py`], [3RD-PARTY] |
| 2025-11-01 | Free (100%-discount) models capped at 100 calls/day unless balance ≥ $10 or quota > 2,000 | [CONFIRMED-CODE cb835cf073] |
| 2026-02-10 | "prevent demand boosts on free models to avoid manipulation": sponsored/free chutes no longer raise miner pay | [CONFIRMED-CODE fa46a2509a] |
| Feb 2026 | "Heavy users were extracting **56x to 324x** their subscription value at equivalent pay-as-you-go costs"; GLM-5, Kimi K2.5, Qwen 3.5, MiniMax M2.5 removed from Base | [3RD-PARTY ownyourmind, attributing it to Chutes' Feb announcement; primary post not readable] |
| 2026-02-27 | **USD-equivalent caps:** monthly cap 5× plan price in PAYG value ($15 / $50 / $100); 4-hour cap price/180 × 75 ($1.25 / $4.17 / $8.33); Base blocked from premium chutes; Quota-200 users blocked from TEE models; max bounty boost 4× → 2.5×. Post: request-based model "no longer viable"; Early Access retired Mar 15 | [CONFIRMED-CODE 7be40c83e6, 90e25c5b10]; post via snippets [3RD-PARTY] |
| 2026-03-02 → 03-12 | Overage discounts 3/6/10% (`SUBSCRIPTION_PAYGO_DISCOUNTS`); caps follow billing date; header-triggered "magic discount" (50% default) | [CONFIRMED-CODE 2dec7fa19d, e5ac6bf56f, 69a9cd9c2a] |
| 2026-05-15 | 7 models removed; premium-chute gate removed; **Base closed to new signups and renewals** | [CONFIRMED-CODE bf588e1a95]; [3RD-PARTY SimplyTao 2026-05-20] |
| Sept 2026 | chutes.ai/pricing shows **Plus $10 (6% off overage), Pro $20 (10%)**, Enterprise; "no subscription, no minimum, no markup" for PAYG. Private PRO 6000 deployments $1.80/hr + $5.40 one-time. No free tier | [CONFIRMED-DOC https://chutes.ai/pricing]; **conflict:** https://chutes.ai/llms.txt still lists Base $3 |

### 4.4 "From Volume to Value" (2026-03-20)
- Figures (post via snippets and secondary sources) [3RD-PARTY]:
  - **45% fewer tokens** over 6 weeks.
  - Tokens per dollar −27.4% (9.8M → 7.1M).
  - **Revenue per 1M tokens +37.7%** since Feb 1.
  - Revenue per GPU $4.05 → $5.89 (+44.9%).
  - Organic PAYG +20% in the last 10 days.
  - "Sharpest inflection at the start of March when the last major subsidy programs wound down."
- The "~25% revenue decline" is arithmetic (0.55 ÷ 0.725 ≈ 0.76), not a quote [MY CALC].
- **What changed:** subsidies ended (caps, tier gating, Early Access retirement, free-model caps). **List prices did not rise** [CONFIRMED-CODE for mechanisms].
- **Later:** SimplyTao (2026-05-20): $286K revenue per trillion tokens (7-day), trailing-90-day $1.41M, latest day $16,451 [3RD-PARTY].

### 4.5 Buybacks [CONFIRMED-CODE `api/autostaker.py`, `api/payment/watcher.py`]
- **What the code does:**
  - Incoming **TAO payments** are staked to `settings.validator_ss58` on netuid 64 (TAO → SN64 alpha).
  - Alpha paid in by stake transfer is moved there too.
  - After staking, **`burn_alpha`** burns it.
  - Execution: random chunks ≤ 25 τ via MEV-shield, 0.3% slippage.
- **What's missing:** no card-payment code in the files checked, and no amounts, addresses or dashboard found. "All revenue auto-staked" (OAK Research, CoinGecko) overstates what the code shows: a buy-and-burn of *crypto* payments [3RD-PARTY vs CODE].

### 4.6 Revenue and subsidy (latest)
- **Live PAYG charges** `https://api.chutes.ai/invocations/usage`: **$91,533 over 2026-09-04→13, ≈ $9.15K/day**. Excludes subscription fees; subscription-covered calls count $0 [CONFIRMED-DOC; reading MY INFERENCE].
- **Emission share conflict:**
  - 6.55% (ownyourmind, 2026-08-15).
  - 9.7% (my 09-11 reconstruction of final shares).
  - 6.21% of `SubnetTaoInEmission` at block 9,066,605 (09-14, media agent) [CONFIRMED-CHAIN]. `SubnetTaoInEmission` likely excludes chain-buy TAO for mature subnets [MY INFERENCE].
- **[MY CALC]** Emission value $52K–$81K/day ÷ PAYG $9.15K/day ≈ **5.7–8.9×**, an upper bound because subscriptions are excluded. Pine (Mar 2026) estimated 22–40× [3RD-PARTY https://pineanalytics.substack.com/p/the-bear-case-for-bittensor-tao].

---

## 5. SN4 Targon: Tower-set per-card USD targets, capped by the emission pool, remainder burned

### 5.1 Mechanism [CONFIRMED-CODE `internal/validator/callbacks/weights.go`; CONFIRMED-DOC `docs/miner/miner.md`]
- Miners **do not bid**. Tower publishes per compute type `target_price`, `max_price`, `target_cards` and `min_cluster_size` at `https://tower.targon.com/api/v2/auctions`. "All prices are in USD per hour per card, reported in cents — e.g. a `max_price` of 350 means $3.50/hour."
  - The doc's example values: 290/350 and 420/650, TAO $215.13.
  - The endpoint returned **502 Bad Gateway** on 2026-09-14; `/api/v1/auctions` returns 410 "deprecated".
- **Pay per card-hour:**
  - `pool = TargetPrice × TargetCards`; `perMiner = min(pool / cards_online, MaxPrice)`.
  - Below the card target, every card earns up to the cap. Above it, per-card pay falls toward the target.
  - `minerIncentive = perMiner × 1.2 h × cards / (EmissionPool_USD_per_tempo × 100)`. If the sum exceeds 1, scale down pro-rata; otherwise **"Any emissions not allocated to auctions are burned"** (BurnDistribution keys, residual to uid 28).
- **Conflict:** KubeTEE's doc says "Targon no longer uses a bidding/auction system". Code and docs at HEAD still use Tower-set "auctions". They were never miner bids, so both readings describe the same fixed-price-with-cap mechanism.

### 5.2 Live payouts (`https://stats.targon.com/api/miners`, 2026-09-14) [CONFIRMED-DOC; units from code: `bid.Payout = perMiner × cards / 100` = USD per node-hour]

| Compute type | Nodes | Cards | Payout per node-hour | Per card-hour |
|---|---|---|---|---|
| TDX-VM-NVIDIA-B300 | 8 | 64 | $78 | **$9.75** |
| TDX-VM-NVIDIA-H200 | 13 | 104 | $28.48 | **$3.56** |
| TDX-HOPPER-NVIDIA-H200 | 2 | 16 | $28 | $3.50 |
| TDX-VM-NVIDIA-H100 | 3 | 24 | $32 | **$4.00** |
| TDX-VM-NVIDIA-RTX6000B (RTX PRO 6000) | 2 | 16 | $16 | **$2.00** |
| SEV-CPU-AMD-EPYC-V4 | 9 | 9 | $0.20 | — |

- **[MY CALC]** Total ≈ **$1,180/hr ≈ $28.3K/day ≈ $10.3M/yr** of emission-paid miner compensation.
- SN4's 7.5% share (09-11) ≈ 270 τ/day ≈ $62.9K/day, so the miner 41% ≈ $25.8K/day. Payouts are roughly fully subscribed, consistent with SN4 `MinerBurned` 0.066 on 09-11.
- Coincidence worth noting: annualized miner payouts ≈ the self-reported $10.4M ARR.

### 5.3 Customer prices and revenue
- **Customer prices:** targon.com, `/pricing`, `/inventory` and docs.targon.com rendered **no prices** to my fetchers.
  - A search summary said confidential H200s "from $1.90/hr", with tiers H200 Small $2.40 / Medium $4.80 / Large $9.60 (March 2026) [UNVERIFIED: source page not identified].
  - If "Small" is one H200, **the customer price is below the $3.50–3.56/card-hr miner payout**, an emission-funded discount [MY INFERENCE; tier-to-GPU mapping unknown].
- **Revenue:** $10.4M ARR self-reported, unaudited; Pine subsidy ≈ 1.7:1; ~5.73% share; named customers all Bittensor-native (Dippy, Ridges, Score) [3RD-PARTY https://ownyourmind.ai/tokenomics/targon-bittensor-confidential-compute/, updated 2026-06-23].
- **Buybacks:**
  - A search summary said "repurchased 2000 TAO of SN4 alpha using organic revenues … over the past month" (date and source unidentified) [UNVERIFIED].
  - Prior notes: a 550 τ buyback.
  - No buyback dashboard or addresses found.
- Dippy's podcast (2025-12-01): its text inference moved to Targon in a "six-figure deal" [3RD-PARTY].

---

## 6. SN90 KubeTEE: USD price card clamped by Targon; the burn penalty in action

### 6.1 Price card and clamp [CONFIRMED-CODE `validator/price_card.py`, `targon_payout_feed.py`, `miner_scoring.py`; CONFIRMED-DOC `docs/COMPETITIVE-PRICING.md`, README]
- **Compiled-in trust-root card (USD/GPU-hr):** H100 $4.00, H200 $5.50, B200 $8.00, B300 $10.00, RTX6000 $2.50.
- **Published card:** the owner publishes `price-card.json` to Hippius (SN75) S3. Every validator clamps it to **[0.8×, 1.25×] of the compiled card** (`clamp_to_envelope`); classes the card omits fall back to the compiled price.
- **Targon clamp:** takes the **highest** Targon miner $/card per class, then `clamped = min(card, max(0.75 × card, live))`. It only pulls pay **down** toward SN4.
  - Fails **soft**: live → cache → card, never skips a cycle.
  - The TAO/USD compensation feed (Taostats) fails **closed**.
- **Example published card** (`docs/examples/price-card.json`, published 2026-08-03): H100 3.0, H200 3.5, B200 6.5, B300 8.0, RTX6000 2.25.
  - **Internal inconsistency:** H100 3.0 and H200 3.5 are below the 0.8× envelope of the compiled card ($3.20 / $4.40). A validator would clamp them up. Which card is live is [UNVERIFIED].
- **Weight:** `usd_target_per_hour × tenure × window_hours ÷ pool_usd`. Unearned → owner UID, `recycle_or_burn=recycle`.

### 6.2 Planned price formula (not built)
- `target[c] = mean(targon_payout[c], mean(lium[c], chutes[c])) × (1 + α·demand_pressure[c]) × confidential_premium[c]`. `confidential_premium` is bounded by the observed Targon-payout-vs-Lium-rental gap.
- **Scoring rule:** at or below target = full credit; "modestly above" = reduced; far above = zero. **Undercutting below target earns nothing extra**, explicitly to avoid a "below-cash-cost race".
- **Open question the team flags:** `demand_pressure` can be gamed by a miner submitting its own jobs ("wash consumption"). Candidate fixes: charge the submitter the target price, exclude a miner's own jobs from its demand signal, or cap α low enough that the gain never exceeds the spend. **Unresolved** [CONFIRMED-DOC].

### 6.3 Customer side and outcome
- **Customers:** buy SN90 alpha on the open pool (no discounts, no treasury, no customer balances); spent alpha is **recycled** [CONFIRMED-DOC `docs/TOKENOMICS.md`].
- **Actual demand route:** a **free window closed at 14,812,329,857 tokens**; after that, paid offers go only through sayGM (SN28), from 2026-08-19 [CONFIRMED-DOC README, `docs/SN28-SAYGM.md`].
- **Outcome:** ~77% of miner incentive went to the owner UID (`MinerBurned` 0.766 on 2026-09-11). Its EMA price ranks ~top-7, but its share collapsed to **~0.43% (~15.5 τ/day) vs ~4% without burning** [MY CALC, research_bittensor.md §1.4]. The clearest live example of the June 2026 penalty.

---

## 7. SN39 Basilica: miner bids, validator picks the cheapest, USD budget per GPU category

- **Bids** [CONFIRMED-CODE/DOC `crates/basilica-miner/docs/bidding-strategy.md`, `migrations/003_add_gpu_pricing.sql`]:
  - Miners register nodes with a **static per-GPU hourly price** per GPU category (`hourly_rate_cents`, e.g. 250 = $2.50).
  - Validators "select the lowest-priced eligible node for rentals".
  - `UpdateBid` / `RemoveBid` RPCs exist. Dynamic strategies (cost-plus, utilization, time-of-day) are **not implemented**.
- **Validator floor:** `BiddingConfig.min_bid_floor_fraction` default **0.1** ("minimum bid as fraction of baseline"), `price_cache_ttl_secs` 60 [CONFIRMED-CODE `crates/basilica-validator/src/config/bidding.rs`]. What "baseline" is was not traced [UNVERIFIED].
- **Miner pay** [CONFIRMED-CODE `incentive/incentive_pool.rs`]:
  - **CU:** `vested_fraction × cu_amount × min(bid_price, per_CU_budget)`, where `per_CU_budget = target_count × 8 GPUs × window_hours × price / category_supply`. Oversupply dilutes, like Targon.
  - **RU:** `ru_amount × revenue_share_pct` (tests use 25–30).
  - Total USD owed vs USD emission capacity: scale down if over; residual + optional **forced burn %** → `burn_uid`.
- **Customer price:** `billing.proto`: `base_price_per_gpu … (already includes markup)`, `markup_percent`; additive GPU + CPU + RAM + storage pricing [CONFIRMED-CODE `crates/basilica-protocol/proto/billing.proto`]. **Customer price = miner bid + platform markup.** Actual numbers not public (basilica.ai pages show no prices).
- **Status conflict:**
  - Covenant AI announced its exit and "shut down" SN3/SN39/SN81 on **2026-04-10** (Basilica token −62%) [3RD-PARTY https://www.tao.media/covenant-ais-bittensor-exit-what-happened-how-bittensor-responded-and-whats-next-for-the-network/].
  - Yet `one-covenant/basilica` has commits through **2026-08-27** (SDK 0.34.0) [CONFIRMED-CODE].
  - Who operates SN39 now, and whether the marketplace is live, is [UNVERIFIED].

---

## 8. Other subnets selling image, video or media generation

**Headline:** no Bittensor subnet has **verifiable revenue from selling generated images or video**. Every media-generation product was free or unpriced, and most slots have since been handed to other projects. Paying customers exist only for detection (BitMind), analytics (Score), 3D (404-GEN) and upscaling claims (Vidaio). Emission shares below are `SubnetTaoInEmission` at block 9,066,605 (2026-09-14) [CONFIRMED-CHAIN].

| Subnet / product | What was sold | Price | Anyone paying? | What happened |
|---|---|---|---|---|
| **SN19 Nineteen** (Rayon Labs) | SDXL Turbo / DreamShaper / ControlNet image + LLM API; first subnet on OpenRouter | "zero cost to use — no per-query fee"; 100K+ weekly tasks [3RD-PARTY asymmetricjump 2025-04-26]. FLUX and "payments operational" [UNVERIFIED] | No revenue figures anywhere | SN19 is now Blockmachine (RPC, Taostats), share 0.91%. Same 2024 registration, so a handover. Why and when not found |
| **SN34 BitMind** | Deepfake **detection** API; consumer app with some image creation | API: Free (100 req/mo), Pro $100/mo (10K+ req), Custom. App "BitMind Plus" $1.99 [CONFIRMED-DOC https://bitmind.ai/product/api] | 50K+ MAU, 2.5M+ API req/week (Sep 2025 memo); no revenue [3RD-PARTY] | Share 1.14%. Generative miners exist only to train detectors |
| **SN85 Vidaio** | Video upscaling / compression | Site shows no prices. Team: "~$0.05/min, ~75% margins"; Enterprise Track fiat ~75% miners / 25% Vidaio; "AlphaBond" escrow of ~50% of payout [3RD-PARTY podcast 2025-10-22] | "No fiat, SaaS, or API monetization yet" (May 2025); none disclosed (Apr 2026) | Share 0.16%; emission "touched zero" Feb and late Mar 2026 [3RD-PARTY TAO Desk] |
| **SN11 Dippy Studio** | FLUX.1-dev / Kontext image generation for the Dippy app | No public price | App ~$40–60K/month, 8.6M users; SN11 served "~2% of Dippy images"; planned $5–10K/month buybacks [3RD-PARTY podcast 2025-12-01] | SN11 now TrajectoryRL, share 0.78% |
| **SN23 NicheImage** | Image generation API | "$10 per 1000 images … as low as $0.1 per 1000" [UNVERIFIED snippet; page 404]; studio usable without an account | None found | README: 71% of emission burned, 29% to categories [CONFIRMED-CODE `SocialTensorSubnet/README.md`]. SN23 now Trishool, 0.00% |
| **Eclair / Leoma** (video generation competitions) | No customer product: miners compete, king takes most (LPIPS or LLM judge) | None | None | Eclair's claimed SN66 and Leoma's SN99 are now other projects |
| **SN17 404-GEN** (3D) | Atlas, via Google Cloud Marketplace, "usage-based pricing" | No numbers | Square Enix test [3RD-PARTY tao.media 2026-04-02] | Share 0.90% |
| **SN44 Score** (video analytics) | Vision platform (Manako), PwC France partnership | None found | Enterprise pilots claimed | Share 3.36% |
| **SN64 Chutes media chutes** | z-image-turbo, Qwen-Image-2512/Edit, ACE-Step music, turbowani2v, **LTX-25-Video** | GPU time $0.0005/s | Tiny: invocation counts 805 / 250 / 160 / 13 / 26 / **0** (window unknown) | Live, all TEE |

**Market reference prices per output second** (2026-09-14; details in research_market.md plus media-agent fetches):
- **LTX official** [CONFIRMED-DOC https://docs.ltx.io/pricing.md]:

  | Model | 720p | 1080p | 1440p | 4K |
  |---|---|---|---|---|
  | ltx-2-5-fast | $0.09 | $0.13 | $0.19 | $0.30 |
  | ltx-2-5-pro | $0.12 | $0.17 | $0.25 | $0.39 |
  | ltx-2-3-fast | $0.03 | $0.06 | $0.12 | $0.24 |
  | ltx-2-3-pro | $0.04 | $0.08 | $0.16 | $0.32 |

- **fal / Replicate** LTX-2 / 2.3 Fast: $0.04 (1080p), $0.08 (1440p), $0.16 (4K) [CONFIRMED-DOC].
- **MiniMax PAYG:** H3 768P $0.08/s, 2K $0.13/s; H3-Max 480P $0.05 / 768P $0.08 [CONFIRMED-DOC https://platform.minimax.io/docs/guides/pricing-paygo]. OpenRouter charges $0.13/s for H3 at any resolution [CONFIRMED-DOC].
- **Closed floor:** Veo 3.1 Lite $0.03–0.05 (720p); Seedance 2.0 Mini $0.034; Wan 3.0 $0.05 (480p) / $0.10 (720p); Grok Imagine $0.07–0.14.

---

## 9. Cross-cutting evidence

### 9.1 Emission rules in 2026: updates to research_bittensor.md [CONFIRMED-CODE `RaoFoundation/subtensor` unless noted]
- **Repo move:** the GitHub org moved from `opentensor` to **`RaoFoundation/subtensor`** (PR #2834, 2026-07-07). Runtime spec 456 at HEAD.
- **Timeline:**
  - Price-EMA shares from Feb 2025.
  - **Flow-based** (net TAO stake inflow EMA, half-life 216,000 blocks ≈ 30 days) from PR #2160 (merged 2025-10-29; brief revert #2174 / #2179 in early Nov 2025) until **#2779 (merged 2026-06-22) "Switch subnet emissions to price-based shares"**, deployed ~2026-06-24.
  - `get_shares_flow` remains as dead code.
- **Current share formula** (`coinbase/subnet_emissions.rs`):
  1. `p_i / Σp` with p = `SubnetMovingPrice`.
  2. × (1 − `MinerBurned_i`), renormalized.
  3. Hill gate `1/(1+(θ/s)^3)` with θ = 32nd-largest share, recomputed every 360 blocks.
  - #2781 added a root_proportion factor; **#2800 (2026-06-30) removed it**; v431 notes: "allocated purely in proportion to each subnet's moving-average price" [CONFIRMED-DOC https://www.bittensor.com/releases/v431-upgrade].
- **Moving price:**
  - α_eff = 0.000003 × b / (b + 201,600), with b = blocks since subnet start ("30 days to reach 50% … 3.5 months to reach 90%").
  - **Spot price fed into the EMA is capped at 1.0 τ.** New subnets ramp extremely slowly.
- **Miner-burn penalty history:**
  - Introduced #2781 (2026-06-22). **Removed in v444 (#3058, 2026-08-10). Restored (#3071, 2026-08-12).** No rationale found for the flip-flop.
  - Recycle counts the same as burn: code comment says "the emission penalty cannot be dodged by choosing Recycle" (`run_coinbase.rs` L739-742) [CONFIRMED-CODE, CONFIRMED-DOC https://learnbittensor.org/concepts/tokenomics/miner-burn].
- **Possible gap [MY INFERENCE]:** with zero total miner incentive in an epoch, `MinerBurned` falls back to 0 (`run_coinbase.rs` L799-801) and the miner half goes to validators. A weekly Const review ("inactive and exploitative subnets", ~57 disabled at the June change [3RD-PARTY]) is the only guard found.
- **New subnets:** register with **emission disabled** (root-only switch, #2787, 2026-06-23).
- **Open proposals** that would change pricing incentives: #3029 "1τ/1α pool seed + depth-graduated emission price cap"; #3017 "Cap chain buys".

### 9.2 Can a subnet raise its emission share with revenue or buybacks?
- **Showing revenue: no direct effect.** Nothing on chain reads revenue. Indirectly, it attracts stakers and root-basket validators (v441 "Root Reborn") [DOC in research_bittensor.md].
- **Buying back alpha: yes, slowly.** Any TAO→alpha stake swap raises spot price, which the EMA follows. `update_moving_price` and `get_shares` don't check who the buyer is; **no rule against owner-funded buys**.
  - Limits: slow age-scaled EMA, 1.0 τ spot cap, normalization against all subnets, gate cadence.
  - In the flow era every add-stake (owner or not) counted as inflow; chain buys were subtracted in net-flow mode.
- **Burning or recycling miner emission: sharply reduces share** (×(1−b)), and can push a subnet under the gate (SN90).
- **Implied optimal strategy [MY INFERENCE]:**
  1. **Never** route unused miner emission to owner hotkeys.
  2. Put surplus emission into useful work (capacity pay, a second mechanism) instead of burning.
  3. Convert revenue into **alpha buys**: buy-and-burn (Engy, Chutes crypto payments), buy-and-hold/lock, or pay miners' USD share in market-bought alpha (Lium pays fees in alpha).
  4. The price EMA is the **only** emission lever, and it rewards *sustained* buying far more than bursts.
  - This also argues against pricing below cost to chase volume: unprofitable volume consumes revenue that could buy alpha.

### 9.3 Subsidy ratios (emission value ÷ revenue)

| Subnet | Revenue used | Emission value used | Ratio | Date | Source |
|---|---|---|---|---|---|
| SN64 Chutes | $1.3–2.4M/yr verified external | ~518 τ/day (14.4%) | **22–40×** | 2026-03-23 | [3RD-PARTY Pine] |
| SN64 Chutes | PAYG $9.15K/day (excl. subscriptions) | 6.2–9.7% × 3,600 τ × $233 = $52–81K/day | **5.7–8.9×** | 2026-09-04→14 | [MY CALC; revenue CONFIRMED-DOC live] |
| SN51 Lium | $432K/mo | 4.44–6.2% | 3.5–4.9× | 2026-05 | [3RD-PARTY ownyourmind] |
| SN51 Lium | $964K billed Aug 2026 | 5.72–13.4% | **1.5–3.6×** | 2026-08/09 | [MY CALC; revenue is a team claim] |
| SN51 Lium | "revenue exceeds emissions" | — | <1× claimed | Aug 2026 | [UNVERIFIED] |
| SN4 Targon | $10.4M ARR self-reported | ~5.73% | 1.7× | 2026-06 | [3RD-PARTY Pine via ownyourmind] |
| SN4 Targon | $10.4M ARR self-reported | 7.5% (09-11) | ~2.2× | 2026-09 | [MY CALC] |
| SN28 gm | Buyer spend $13.8–16.3K/day | 360 α/epoch × $5.09 (all participants) ≈ $37.5K/day | **2.3–2.7×** (miner pool ÷ miner earnings 1.12) | 2026-09-03→13 | [MY CALC from public S3] |
| SN53 Engy | Not disclosed; buyback $49.5K/32 d | ~3.1% (09-11) ≈ $26K/day | Unknown (~17× the buyback) | 2026-09 | [MY CALC] |
| Top 3 combined (Chutes, Targon, Lium) | $20M ARR | $2.25M/day (pre-halving) | ≈41× | 2025-09-24 | [3RD-PARTY Unsupervised Capital; ratio MY CALC] |
| Network | $3–15M identifiable | ~3,600 τ/day | TAO valued ~175–200× revenue | 2026-03-23 | [3RD-PARTY Pine] |

- **Methodology warning:** analysts value "emission" as the subnet's **TAO emission share × 3,600 τ × TAO price**. gm's figure uses **alpha minted × alpha price**. KunoWorld's `emission_to_revenue` uses the latter. The two can differ widely; state which one you publish.
- **Conflicts:**
  - ownyourmind's rankings list Chutes' emission value at "~$189M" and Targon's at "~$209M", inconsistent with Pine's $52M.
  - "Chutes $43M Q1 2026 revenue" (taoprotocol.org, abittensorjourney) is almost certainly wrong [UNVERIFIED].

### 9.4 Who priced below cost using emissions, and what happened
1. **Chutes (the clearest case).**
   - Free → $5 deposit (Jul 2025) → $3/$10/$20 request-based subscriptions (Aug 2025) → free-model caps (Nov 2025).
   - Heavy users extracted **56–324×** subscription value (Feb 2026) → USD-equivalent caps (5× price per month), tier gating, Early Access retired (Mar 2026) → **tokens −45%, revenue per token +37.7%, revenue ≈ −24%** → Base closed and 7 models cut (May 2026).
   - Emission share 14.4% (Mar) → 6.2–9.7% (Aug–Sep).
   - Pine: unsubsidized cost ~$1.41/M vs Together ~$0.88/M. OpenRouter-visible volume (6.8–42B tokens/day) was far below the self-reported 160B/day.
   - **Abuse:** miners or chute owners **manufactured demand on free models to inflate autoscaler boosts**, fixed 2026-02-03 / 02-10 / 03-01 (research_chutes.md §2.2).
2. **Targon.** Customer prices reportedly below its own per-card miner payout; customer base Bittensor-internal (Dippy, Ridges, Score): **circular demand risk** [3RD-PARTY + MY INFERENCE].
3. **KubeTEE.** Free window of 14.8B tokens before any paid offer; the owner-UID residual then cut its emission share ~10× (§6.3).
4. **gm.** Buyers get 8–70% off list, funded entirely by emissions. Supply relies on miners sourcing upstream below list. Near-full subscription (1.12) means the model stays solvent only while alpha price × emission ≥ demand at discounted retail [MY INFERENCE].
5. **Flow era (Nov 2025–Jun 2026).** Subnets with net outflows (Ridges, Gradients, Hippius, Dippy) got 0% emission regardless of product [3RD-PARTY Macrocosmos 2025-12-19]. Covenant AI (SN3/39/81) exited on 2026-04-10 after emission suspension disputes; TAO −15–27% [3RD-PARTY].
6. **Media subnets.** Nineteen (free image API), NicheImage (71% burn, unverified $0.10–$10 per 1,000 images), Dippy Studio (2% of images on-subnet) never reached verifiable paid demand, and their slots changed hands (§8).

### 9.5 Revenue-to-alpha buybacks and how verifiable they are

| Subnet | Practice | Verifiability |
|---|---|---|
| **SN53 Engy** | Revenue buys and **burns** SN53 alpha; public page with per-burn block links; 7,688 α / $49.5K, 2026-08-12→09-13 | **Best found:** each burn on chain. Share of revenue not stated |
| **SN64 Chutes** | Code: TAO/alpha **payments** staked to SN64 then `burn_alpha` | Mechanism verifiable in code; amounts and addresses not published; card revenue not covered |
| **SN51 Lium** | Providers paid rental fees in alpha; "$1M worth of alpha burned using product revenue"; burn weight to UID 47 | Team claims only; UID 47's disposal unverifiable from code |
| **SN4 Targon** | "Committed to buybacks"; 550 τ and "2000 τ in a month" claims | No addresses or dashboard [UNVERIFIED] |
| **SN90 KubeTEE** | Swaps SN28 earnings → SN90 alpha → `recycle_alpha`; coldkey and first extrinsic published | Verifiable on chain (tao.app / taostats) |
| **SN28 gm** | None found | — |
| **SN11 Dippy** | Planned $5–10K/month (2025) | Team claim |

Critique (ownyourmind, updated 2026-08-18): "most subnet revenue data traces back to internal … team reports"; "external revenue is structurally difficult to verify for inference subnets". An owner `add_stake` buyback is indistinguishable on chain from any other stake unless the coldkey is published and tied to revenue attestations [MY INFERENCE].

---

## 10. KunoWorld's placeholders against this evidence

**Current placeholders** (`protocol/src/kuno_protocol/profiles.json`, `rate_card.py`, `switch.py`):
- **Customer $/output s:**

  | Profile | Resolution | Price |
  |---|---|---|
  | ltx-2.5-fast | 720p / 1080p | $0.024 / $0.04 |
  | ltx-2.5-pro | 720p / 1080p | $0.04 / $0.07 |
  | ltx-2.5-4k | 1440p / 2160p | $0.12 / $0.20 |
  | h3-turbo | 768p | $0.06 |
  | h3 | 768p | $0.12 |
  | h3-reference | 768p | $0.10 |

- **Miner card:** `PLACEHOLDER_USD_PER_VCU_SECOND` $0.01 × `vcu_per_output_second` (fast 5, pro 15, 4k 40, h3-turbo 16, h3 60, h3-ref 64); open tier 0.5×.
- **Capacity:** `PLACEHOLDER_USD_PER_GPU_HOUR` $2.00, `capacity_share` 0.25, targets 8 (H3) / 4 (LTX).

**Calibration: 1 VCU ≈ 1 H200-second of cost** [MY CALC]
- H3 50-step: ~74 s for a 5 s 1344×768 clip on 4× H200 (research_models.md, secondary) = 59 GPU-s per output s vs 60 VCU.
- LTX fast: ~12 PRO-6000-seconds per output s. At the PRO 6000 / H200 price ratio (~0.35) that is ≈ 4.3 H200-s vs 5 VCU.
- So **$0.01/VCU-s ≈ $36 per H200-hour** of work.

**Market reference for confidential H200-hours:**
- Targon miner payout $3.56; KubeTEE card $3.50–5.50; Phala TEE $3.20 reserved / $4.80 on demand.
- Non-TEE: Lium reference $3.10, RunPod Community $3.59.
- Raw cost ≈ **$0.0009–0.0013 per H200-second.**

| Profile | Customer placeholder | Est. raw GPU cost/s (TEE, 100% util) | Miner card placeholder (confidential) | Card ÷ customer | Market $/s |
|---|---|---|---|---|---|
| ltx-2.5-fast 720p | $0.024 | $0.004–0.007 | $0.05 | 2.1× | LTX-2.5 Fast $0.09; LTX-2.3 Fast $0.03; Veo Lite $0.03–0.05 |
| ltx-2.5-fast 1080p | $0.04 | ~$0.01 (unmeasured) | $0.05 | 1.25× | LTX-2.5 Fast $0.13; fal/Replicate LTX Fast $0.04 |
| ltx-2.5-pro 720p / 1080p | $0.04 / $0.07 | unmeasured (30+3 steps; ~3–5× fast) | $0.15 | 2.1–3.8× | LTX-2.5 Pro $0.12 / $0.17 |
| ltx-2.5-4k 1440p / 2160p | $0.12 / $0.20 | unmeasured | $0.40 | 2–3.3× | LTX-2.5 Fast $0.19 / $0.30; fal 4K $0.16 |
| h3-turbo 768p | $0.06 | ~$0.011–0.027 (8 steps; unmeasured) | $0.16 | 2.7× | H3-Max 768P $0.08; 480P $0.05 |
| h3 768p (50 steps) | $0.12 | **$0.053–0.079** (59 GPU-s/s); ~$0.02–0.03 with aggressive Cache-DiT (25.8 s per clip) | $0.60 | 5× | **MiniMax H3 768P $0.08**; OpenRouter $0.13 |
| h3-reference | $0.10 | ≈ h3 | $0.64 | 6.4× | — |

**Observations**
1. **The rate card pays 1.25–6.4× what the customer pays** and ~10× the market GPU-hour. With `renormalize`, card dollars only set *relative* shares, and the whole pool goes out anyway. "USD-denominated pay" behaves as USD only when oversubscribed.
2. **The capacity placeholder of $2.00/GPU-hr** is below every confidential H200 benchmark ($3.20–5.50) but at Targon's RTX PRO 6000 payout ($2.00) and above Lium's PRO 6000 reference ($1.00).
3. **H3 full 50-step at $0.12 is at or below loaded cost** once utilization is under ~60–70%, and MiniMax's own API is $0.08. Price competitiveness depends on step caching or turbo variants.
4. **LTX-fast 720p at $0.024 undercuts the LTX official API by 73%.** It is still ~3–6× raw GPU cost at full utilization, close to Chutes' pure-GPU-time floor.
5. **The pay report counts canaries as revenue and can't see credits or refunds** (VALIDATING.md). The `emission_to_revenue` KPI will look better than reality.
6. **Alpha deposits** (`KUNO_ALPHA_NETUIDS`) and TAO from linked coldkeys mean a miner could pay for jobs with its own emission. That is a circular flow unless related-party deposits are excluded from pay and KPIs.

---

## 11. Lessons for KunoWorld

### 11.1 Customer price relative to cost and market: parity for Standard, premium for Private, never below cash cost
- **Compute a fully loaded cost floor per profile and never list below it:**
  `cost/s = GPU-s per output s × $/GPU-s × (1 + TEE overhead ~5–10%) / expected utilization + gateway/storage/payment overhead`.
  - Chutes shows what happens otherwise: a free or cheap tier funded by emissions, 56–324× extraction, then forced caps, tier closures, −45% tokens.
  - Pine: Chutes' unsubsidized cost was 1.6× Together's price.
- **Standard mode: at or slightly under parity with open-model hosts, not a deep undercut.**
  - Engy's 30–70% undercut is backed by a *real* cost edge (FP4 on consumer GPUs) plus a public buyback.
  - gm's 8–70% undercut is paid entirely by emissions and depends on miners' upstream arbitrage.
  - KunoWorld's open tier (consumer GPUs) is the one place an Engy-style cost edge exists.
  - **Suggested ranges [MY INFERENCE, to be validated with measured GPU-s]:**
    - LTX-fast: $0.03–0.05/s (720p) and $0.05–0.08/s (1080p), versus LTX-2.3 Fast $0.03, fal $0.04, LTX-2.5 Fast $0.09 / $0.13.
    - H3: $0.08–0.10/s at 768p, and only with Cache-DiT or turbo economics.
- **Private mode: charge a premium; don't undercut.**
  - Confidential GPU-hours cost 15–55% more (Targon H200 $3.56 vs Lium $3.10; Phala $4.80 vs RunPod $3.59).
  - No competitor sells end-to-end-encrypted video generation.
  - Chutes chose to absorb its TEE cost with a ×2.25 miner-side emission bonus and no user surcharge. That is one reason its subsidy ratio stayed high [MY INFERENCE].
  - A 1.5–2× Standard price (e.g. LTX-fast 720p $0.05–0.08, H3 $0.12–0.18) is defensible for the privacy buyer.
- **Watch the reference prices move.** Lium re-anchored to a 30-day rental median in June 2026; KubeTEE clamps to Targon's live feed. Re-price quarterly against a published benchmark basket (LTX official, fal, MiniMax, OpenRouter), rather than chasing every cut.

### 11.2 Miner USD pay relative to customer price: cost-anchored rates, a visible platform spread, emissions as a capped top-up
- **Anchor the rate card to the GPU-hour market, not to the customer price.** Engy's `score_rate` is decoupled from buyer price, so discounts don't distort pay; KubeTEE's card is anchored to Targon.
  - Proposal [MY CALC]: confidential job rate ≈ $/H200-second (≈ $0.0009–0.0013) × (1 + miner margin 20–40%) ÷ target utilization (~0.6) ≈ **$0.0018–0.0030 per VCU-second**, versus the placeholder $0.01.
  - Open tier: ≈ 0.4–0.5× that (Lium PRO 6000 $1.00 vs Targon RTX6000B $2.00; consumer-GPU rates), consistent with `KUNO_OPEN_TIER_RATE` 0.5.
- **Keep customer price ≥ card rate × (1 + platform take 15–30%) at steady state**, so revenue *could* pay miners with no emissions.
  - Lium's split is 95/5; Basilica applies `markup_percent` on the bid; Vidaio claims 75/25 on fiat jobs.
  - At the proposed rate, **H3 50-step needs ≥ ~$0.17/s** and is not competitive with MiniMax at $0.08. Push H3 turbo or caching, or reserve full H3 for Private.
- **Emission surplus should not flow pro-rata to job pay.**
  - Under `renormalize`, any undersubscription hands the whole pool to whoever served jobs. That makes self-bought jobs profitable (§11.3).
  - Prefer routing the surplus to (a) capacity pay with targets (already built; raise `gpu_hour_usd` toward the confidential market of $3.20–3.60/H200-hr) and (b) the Turbo track / a second mechanism via `MechanismEmissionSplit`. Neither counts as `MinerBurned`.
  - Keep `recycle` refused: SN90's 0.43% share is the proof.
- **Consider paying miners' revenue share in market-bought alpha** (Lium pays rental fees in alpha) or running a **public buy-and-burn** (Engy). Either way customer USD becomes steady alpha buying, which is the only thing that raises the price-EMA emission share (§9.2).
  - Publish the coldkey, schedule and per-transaction links, as Engy's `/buyback` page and KubeTEE's recycle doc do.
  - Use a fixed, formulaic rule, not discretion; KubeTEE's securities posture argues against a discretionary treasury.

### 11.3 Wash trading and subsidy abuse
- **The core risk [MY CALC]:** with pool P and organic paid work O, a miner who buys S of jobs routed to itself earns ≈ P × S / (O + S) under `renormalize`. It profits whenever that exceeds S × price + GPU cost.
  - At launch O ≈ 0, so any S captures nearly the whole pool.
  - gm avoids this only by burning the residual; Engy's "billed-only" rule does not stop *paid* self-dealing.
- **Mitigations, most important first:**
  1. **Customers never choose the miner.** Random or least-loaded routing across all eligible enclaves, including owner-run capacity if any (gm's one lottery entry per worker, Engy's round-robin with its first-party cluster). A self-dealer then captures only its capacity share of its own spend.
  2. **Cap pay from jobs relative to revenue:** e.g. Σ job-owed ≤ k × net customer revenue (k ≈ 1–1.5). Send anything above to capacity pay, which is target-capped and not driven by self-bought traffic (KubeTEE's "score capacity, not utilization").
  3. **Cap each miner's job share by its verified capacity share** (e.g. ≤ 2× its share of attested GPU-hours in the family), so a small miner can't absorb a large self-bought job stream.
  4. **Pay only on net-paid jobs.** Promo credits, trial credits, refunds, charge-backs and canaries must not earn job pay or count as revenue.
     - The ledger's `credit: false` path already exists (`scoring.billable_seconds`). Use it for every non-cash job (Engy `cost_micro > 0`).
     - Publish `price_usd` **net** of discounts so validators see real revenue.
  5. **No free tier that pays miners.** Serve free trials unpaid on miner capacity as a cost of admission (Engy probes earn nothing), or on a small owner-run pool, with hard per-account caps.
     - Never boost pay for demand on free or sponsored work (Chutes' Feb 2026 fix).
  6. **Related-party signals:**
     - Flag top-ups whose TAO/alpha sender coldkey (or its funding source) owns a miner hotkey on the subnet, and zero-credit their jobs *for that miner*.
     - Velocity-limit large card or USDT top-ups on new accounts.
     - Hold `needs_review` deposits (already built in PAYMENTS.md).
  7. **Collateral that can actually be enforced** (Lium's is switched off, KubeTEE's only freezes) plus probation for new hotkeys (already built for the open tier).
  8. **Never let a demand signal set price or pay without a wash defence.** KubeTEE left `demand_pressure` unbuilt for this reason.

### 11.4 Subscriptions: not at launch
- Every subnet with a working business (Lium, Engy, gm, Targon, Basilica) is **pay-as-you-go / prepaid credits**. The one subscription experiment (Chutes) under-priced heavy users by 56–324× and needed USD caps, rolling 4-hour limits, tier gating and finally closing its cheapest tier.
- Video jobs are lumpy and expensive (seconds × resolution), which makes flat plans riskier than for LLM chat.
- **If subscriptions come later:**
  - Sell **credit bundles**, not "N requests/day", priced at or above PAYG cost with a small discount (Chutes' 3–10% overage discounts).
  - Hard monthly USD-equivalent caps (Chutes: 5× plan price), no unlimited tier, short rollover.
  - **Miner pay per subscription job must be pro-rated from what the subscription actually paid**, not list price, or subscription heavy users become a wash-trade channel.

### 11.5 Using emissions at launch without depending on them
- **Expect little emission value early.** Emission is disabled at registration until root enables it; the price EMA starts near zero and ramps over months; the gate cuts off below rank ~32.
  - Participant `alpha_out` still accrues, but its value is thin and volatile.
  - Budget miner economics in USD and treat emissions as upside.
- **Use emissions for capacity, not for discounts.**
  - Pay for ready, attested capacity against published targets (Chutes' GPU-time model, Lium's capped idle floor, KubeTEE's capacity scoring) so confidential miners survive cold start.
  - Don't use emissions to push customer prices below cost (Chutes, Targon, gm).
  - Customer launch promotions should be funded from the **owner's** share and marked `credit: false`, never from the miner pool.
- **Publish the KPIs you already compute** (`subsidy_ratio`, `emission_to_revenue`, net of canaries and credits) with a **glide path**. The benchmarks today:
  - Lium ~1.5–3.6×, Targon ~1.7–2.2×, gm ~2.3–2.7× (all-participant), Chutes 6–9× (40× at worst).
  - A target of <3× by month 6 and <1.5× by month 12 would put KunoWorld with Lium and Targon, not Chutes [MY INFERENCE].
- **Don't burn, and don't route surplus to owner-controlled UIDs.**
  - The penalty is ×(1 − burned share) and was restored within two days of its August removal.
  - Lium's non-owner "burn UID" relies on a loophole a rule change could close.
- **Turn revenue into alpha demand on a fixed rule** (a % of net revenue each week, market buys through MEV-shield with published transactions). That is the only lever on emission share that survives the 2026 rules, and it makes the subnet look like Engy (verifiable) rather than Targon or Chutes (claimed).
- **Keep the mechanism stable and versioned.**
  - Chutes rewrote scoring six times in 18 months, and Lium's docs still say a 13% rented pool while the live value is 10%.
  - The owner-signed, monotonic rate card and switch are the right tool: change rates rarely and announce first (Engy: "we announce changes before they land").

---

## 12. Sources

**Code (HEAD 2026-09-14)**
- Lium: https://github.com/Datura-ai/lium-io (`neurons/validators/src/services/const.py`, `task/score_calculator.py`, `incentive/rental_price.py`, `incentive/default.py`, `burn_service.py`, `core/config.py`, `collateral_contract_service.py`, `clients/compute_client.py`; lium-core `shared_config/model.py`)
- Engy: https://github.com/hanlinai/engy (`docs/SN53_ONE_PAGER.md`, `docs/ANNOUNCEMENT.md`, `docs/MINER.md`, `docs/VALIDATOR.md`, `validator/validator.py`)
- gm: https://github.com/taostat/gm-validator (`validator/src/gm_validator/alpha_economics.py`, `scoring.py`, `CLAUDE.md`); https://github.com/taostat/gm-miner (`cli/src/pricing.rs`, `README.md`, `docs/sourcing.md`, `docs/miner-terms.md`)
- Chutes: https://github.com/chutesai/chutes-api (`api/gpu.py`, `api/constants.py`, `api/chute/util.py`, `api/config/__init__.py`, `api/invocation/util.py`, `api/autostaker.py`, `api/payment/watcher.py`; commits cited inline)
- Targon: https://github.com/manifold-inc/targon (`internal/validator/callbacks/weights.go`, `docs/miner/miner.md`)
- KubeTEE: https://github.com/KubeTEE-AI/kubetee-subnet (`validator/price_card.py`, `targon_payout_feed.py`, `miner_scoring.py`; `docs/COMPETITIVE-PRICING.md`, `docs/TOKENOMICS.md`, `docs/SN28-SAYGM.md`, `docs/SN28-SN90-ALPHA-RECYCLE.md`, `docs/examples/price-card.json`, README)
- Basilica: https://github.com/one-covenant/basilica (`crates/basilica-miner/docs/bidding-strategy.md`, `crates/basilica-validator/src/config/bidding.rs`, `incentive/incentive_pool.rs`, `incentive/cu_generator.rs`, `migrations/003_add_gpu_pricing.sql`, `crates/basilica-protocol/proto/billing.proto`)
- Subtensor: https://github.com/RaoFoundation/subtensor (`pallets/subtensor/src/coinbase/subnet_emissions.rs`, `run_coinbase.rs`, `block_emission.rs`, `staking/stake_utils.rs`; PRs #2160, #2779, #2781, #2787, #2800, #2834, #2990, #3017, #3029, #3058, #3071)
- NicheImage: https://github.com/SocialTensor/SocialTensorSubnet (README)

**Live endpoints and official pages (2026-09-14)**
- Lium: https://lium.io/api/v1/shared-config, https://lium.io/api/executors, https://lium.io/api/machines, https://lium.io/pricing, https://docs.lium.io/providers/rewards/rental-fees, https://docs.lium.io/providers/rewards/payouts, https://docs.lium.io/providers/rewards
- Engy: https://api.engy.ai/v1/models, https://engy.ai/pricing, https://provider.engy.ai/epochs, https://provider.engy.ai/requests, https://provider.engy.ai/miners, https://provider.engy.ai/buyback
- OpenRouter: https://openrouter.ai/api/v1/models, https://openrouter.ai/api/v1/models/z-ai/glm-5.2/endpoints (and qwen/qwen3.6-35b-a3b, moonshotai/kimi-k3, z-ai/glm-5.3, z-ai/glm-5.3-flash), https://openrouter.ai/api/v1/videos/models
- gm: https://saygm.com/, https://saygm.com/miners, https://gm-mainnet.s3.gra.io.cloud.ovh.net/v1/finalized/epoch=25095/epoch_summary.json (and `aggregated.jsonl`, epochs 24900–25095)
- Targon: https://stats.targon.com/api/miners, https://tower.targon.com/api/v2/auctions (502 on 09-14)
- Chutes: https://api.chutes.ai/chutes/LTX-25-Video, https://api.chutes.ai/chutes/turbowani2v, https://api.chutes.ai/invocations/usage, https://llm.chutes.ai/v1/models, https://chutes.ai/pricing, https://chutes.ai/llms.txt
- RunPod and Vast: https://www.runpod.io/pricing, https://console.vast.ai/api/v0/bundles
- Video APIs: https://docs.ltx.io/pricing.md, https://platform.minimax.io/docs/guides/pricing-paygo, https://fal.ai/models/fal-ai/ltx-2.3/text-to-video, https://bitmind.ai/product/api
- Bittensor: https://www.bittensor.com/releases/v431-upgrade, https://www.bittensor.com/releases/v440-upgrade, https://learnbittensor.org/concepts/tokenomics/miner-burn

**Third-party**
- ownyourmind:
  - https://ownyourmind.ai/tokenomics/lium-bittensor-subsidy-ratio/
  - https://ownyourmind.ai/tokenomics/chutes-bittensor-revenue-machine/
  - https://ownyourmind.ai/tokenomics/targon-bittensor-confidential-compute/
  - https://ownyourmind.ai/tokenomics/bittensor-subnets-where-the-revenue-is/
  - https://ownyourmind.ai/tokenomics/templar-bittensor-covenant-exit/
- tao.media:
  - https://www.tao.media/lium-reports-964k-month-as-it-tops-bittensors-subnet-market-cap-rankings/
  - https://www.tao.media/is-engy-the-breakout-subnet-bittensor-has-been-waiting-for/
  - https://www.tao.media/covenant-ais-bittensor-exit-what-happened-how-bittensor-responded-and-whats-next-for-the-network/
  - https://www.tao.media/404-gen-sn17-introduces-atlas-to-bring-decentralized-3d-ai-into-enterprise-workflows/
- Analysts: https://pineanalytics.substack.com/p/the-bear-case-for-bittensor-tao, https://www.unsupervised.capital/writing/bittensors-ai-compute-subnets-collectively-reach-20m-arr, https://simplytao.ai/blog/chutes-sn64-last-week-7-models-cut-294k-trillion-tokens, https://macrocosmosai.substack.com/p/from-tao-price-to-flow-emissions, https://www.abittensorjourney.com/p/navigating-bittensor-june-2026, https://thetaodesk.substack.com/p/subnet-deep-dive-sn85-vidaio
- Other: https://rpwithai.com/chutes-new-subscription-plans/, https://subnetalpha.ai/subnet/gm/, https://www.kucoin.com/news/community/TAO/6a606f607d4c720007969ff2, https://asymmetricjump.substack.com/p/nineteenai-subnet-19-bittensor, https://creators.spotify.com/pod/profile/revenue-search/episodes/Subnet-Session-with-Mog--Gareth-from-Vidaio-SN-85-e39slpn, https://creators.spotify.com/pod/profile/revenue-search/episodes/Subnet-Session-with-Akshat-Jagga-from-Dippy-SN-11-e35ucoh
- Benchmarks: https://huggingface.co/datasets/witcheer/rtx-5090-benchmarks, https://github.com/thu-ml/TurboDiffusion
- Existing notes: `/video/research/research_tee_subnets.md`, `research_chutes.md`, `research_bittensor.md`, `research_market.md`, `research_models.md`
