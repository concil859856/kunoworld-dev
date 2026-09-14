# Pricing: customer prices, miner pay and launch economics

Research date: 2026-09-14. This page is the synthesis. The evidence, with a URL and a confidence tag for every figure, is in three notes:

| Note | Tags |
|---|---|
| [pricing/market.md](pricing/market.md): video APIs, open-model hosts, consumer plans, privacy premium, trends | [C] vendor page fetched, [S] secondary, [U] unverified or estimate |
| [pricing/subnets.md](pricing/subnets.md): how Lium, Engy, gm, Chutes, Targon, KubeTEE and Basilica price, and the 2026 emission rules | [CONFIRMED-CODE] / [CONFIRMED-DOC] / [3RD-PARTY] / [UNVERIFIED] |
| [pricing/costs.md](pricing/costs.md), [costmodel.py](pricing/costmodel.py), [cost_extras.py](pricing/cost_extras.py): GPU prices, generation speed, cost per output second, emission subsidy, placeholder checks | [C] / [S] / [U] |

Numbers here are rounded from those notes.

**Status: recommendations, not decisions.** LTX-2.5 and H3 speed on data-center GPUs is mostly estimated (±50%); run the benchmarks in §8 before signing a rate card. Prices are per output second unless stated.

---

## 1. Recommendation in one table

Private is priced about 1.3× Standard.

| Profile | Market reference | Miner rate (§3) | Current placeholder | **Standard** | **Private** | Standard ÷ miner rate |
|---|---|---|---|---|---|---|
| LTX-2.5 Fast 720p | Lightricks/fal $0.09, Veo 3.1 Lite $0.05, Replicate $0.03 (possibly stale) | $0.005 | $0.024 | **$0.04** | **$0.05** | 8× |
| LTX-2.5 Fast 1080p | Lightricks $0.13, Veo 3.1 Lite $0.08 | $0.010 | $0.04 | **$0.06** | **$0.08** | 6× |
| LTX-2.5 Pro 720p | Lightricks $0.12 | $0.017 | $0.04 | **$0.055** | **$0.075** | 3.2× |
| LTX-2.5 Pro 1080p | Lightricks $0.17 | $0.040 | $0.07 | **$0.085** | **$0.11** | 2.1× |
| LTX-2.5 4K 1440p | Lightricks $0.19 | $0.042 | $0.12 | **$0.12** | **$0.15** | 2.9× |
| LTX-2.5 4K 2160p | Lightricks $0.30, Veo 3.1 Fast 4K $0.30 | $0.12, provisional | $0.20 | **$0.25**, provisional | **$0.32**, provisional | 2.1× |
| H3 Turbo 768p | fal H3 Max Turbo $0.04, fal H3 $0.06 | $0.033 (5 s) to $0.047 (14 s) | $0.06 | **$0.05** | **$0.065** | 1.1–1.5×, thin |
| H3 768p | MiniMax $0.08, fal $0.06 | $0.11 (5 s) to $0.18 (14 s) | $0.12 | **not offered** | **$0.20** | Private ÷ rate 1.1–1.8× |
| H3 Reference | WaveSpeed $0.125 | $0.17–0.27, provisional | $0.10 | **not offered** | **$0.30, after a benchmark** | Private ÷ rate 1.1–1.8× |

**Why these numbers:**
- **LTX-2.5 Fast** undercuts Lightricks' own API by half or more, sits at or below Veo 3.1 Lite, and still has a wide margin. That margin matters: Stripe takes 4–9% of small top-ups, 4K storage kept forever costs about $0.36 per clip, and the LTX Fast price band is expected to fall to $0.02–0.03 within 6–12 months.
- **LTX-2.5 Pro** is rated *below* Fast on Artificial Analysis. Keep it priced near cost-plus rather than as a premium tier.
- **LTX-2.5 at 2160p** has the widest cost uncertainty (costs.md §3: 160–850 s per 5 s clip). Hold it at the provisional price until measured, or ship 1440p first.
- **H3 Turbo** has no published timings anywhere. At $0.05 it covers miners for 5–10 s clips. If benchmarks show higher cost, move it to $0.06, level with fal H3, or cap H3 Turbo clips at 10 s.
- **Full H3** costs us about $0.08–0.15/s, at or above MiniMax's own $0.08. It can't win in Standard, so sell it where nobody else can: Private. Point Standard customers to H3 Turbo.
- **H3 in general** can't be sold to users in the US, EU, UK or South Korea (§7). The switch already gates regions.

---

## 2. Evidence behind the prices

### 2.1 Market (market.md)

**Closed APIs.** For a 5 s 720p clip the floor is $0.15–0.38, the mainstream $0.40–0.80 and premium $1–2. For example:

| Model | Price per second | 5 s clip at 720p |
|---|---|---|
| Veo 3.1 Lite / Fast / Standard | $0.05 / $0.10 / $0.40 at 720p | – |
| Kling 3.0 | $0.084 silent | – |
| Seedance 2.0 | $0.15 at 720p | – |
| MiniMax H3 | $0.08 at 768p | – |
| Wan 3.0 | $0.10 at 720p | – |
| Runway Gen-4.5 | $0.12 | – |
| Luma Ray 3.2 | – | $0.30 |
| Pika 2.5 API | $0.04 | – |

Sora's API is removed on 2026-09-24.

**Open-model hosts:**

| Host | LTX-2.5 Fast | LTX-2.5 Pro | H3 |
|---|---|---|---|
| Lightricks (and fal, same prices) | $0.09 / 0.13 / 0.19 / 0.30 (720p / 1080p / 1440p / 4K) | $0.12 / 0.17 / 0.25 / 0.39 | – |
| Replicate | $0.03 / 0.06 / 0.12 / 0.24 (may be a stale LTX-2.3 price) | – | – |
| WaveSpeed | $0.10 / 0.14 / 0.21 / 0.33 | – | $0.04 (480p) / 0.08 (768p) |
| Segmind | $0.1125 / 0.1625 / 0.2375 / 0.375 | – | – |
| MiniMax official | – | – | $0.08 (768p), $0.13 (2K) |
| fal | – | – | open-weights H3 $0.05–0.06; H3 Max $0.05 / 0.08 / 0.16; H3 Max Turbo $0.025 / 0.04 / 0.08 (not open weights) |

- **Chutes' enclave-run LTX-2.5 chute** bills $0.0005 per GPU-second (about $0.014 per call) and currently has no running instances.
- **Quality:** on Artificial Analysis, H3 is the best open-weights model (Elo 1226). H3 Max is 3rd on text-to-video. LTX-2.5 Fast (Elo 1072) is level with Veo 3.1 Lite and Fast.

**Consumer apps.** Implied $ per 5 s 720p clip ranges from $0.60 on Runway's entry plan down to about $0.07 on Kling's top plan. Other traits:
- Free tiers are small, watermarked and non-commercial.
- Annual plans are about 20% off, and monthly credits rarely roll over.
- Failed jobs are usually refunded. Moderation-blocked jobs vary: Runway and Pika charge; Hailuo, Higgsfield and LTX Studio refund.

**Price trends, Sep 2025 → Sep 2026:**
- The same model at the same resolution: median change 0%. Every real cut came from Google (Veo 3 −47%, Fast −63%, cheapest Veo with audio −67%).
- Successors launch at higher prices: LTX-2 → 2.5 Fast +225% at 1080p, Seedance +200%, Hailuo 02 → H3 +70%.
- Quality-adjusted prices fell 65–80%.
- **The low end is a price war:** fal H3 Max −75% launch promo, Wan 3.0 −30%, $0.03–0.05 first-party tiers, free "unlimited" slow lanes. Show real list prices from day one.

**Privacy premium:**
- The same open model in an enclave costs a median **+31%** more across 53 comparisons (middle half +7% to +104%). Large enclave hosts (Chutes, Phala, NEAR AI) charge 0–10% extra; boutique vendors (Tinfoil, Privatemode, PPQ) +30% to +340%. Venice's encrypted text models cost +22% over its own standard ones.
- Enterprise data residency costs +10% at OpenAI, Anthropic, Google, Azure and Bedrock.
- **Nobody sells private video generation.** The nearest are Chutes' enclave video chutes, sold as raw GPU time, and NEAR AI's attested FLUX images.
- Consumer privacy subscriptions sit at $5–25/month (Proton, Mullvad, Kagi, Tinfoil, Venice).

So Private can carry **+25–50% for consumers** and **+50–100% for API buyers who get per-job attestation**. At +25–35%, Private LTX Fast 720p ($0.05) is still well below Lightricks' non-private $0.09.

### 2.2 Cost (costs.md)

**GPU prices, Sep 2026, median $ per GPU-hour** (GetDeploying):
- H100 $3.29
- H200 $4.29
- B200 $6.13
- B300 $7.85
- RTX PRO 6000 $2.20
- RTX 5090 $0.63
- RTX 4090 $0.41

Lium and Vast run 30–50% below the median, e.g. RTX PRO 6000 at $1.06–1.19 and H200 at $2.75. Reserved capacity is about −32% on 1-year terms. Owning a server costs, all-in over 3 years:
- HGX H200: $2.05 per GPU-hour
- HGX B200: $2.57
- 8× RTX PRO 6000: $0.95

**Confidential computing:**
- **Hardware premium:** about 0% on owned bare metal; clouds range from −8% to +34%.
- **Mainnet needs bare metal with BIOS access.** Cloud confidential VMs can't reproduce our measurements, so they're for testing only.
- **Overhead:** assumed 2% / 5% / 15% (low / base / high). No diffusion benchmark exists.
- **Keep profiles loaded:** reloading weights inside an enclave was measured 34× slower.

**Speed:**
- **H3, measured:** a 5 s clip takes 74 s warm on 4×H200 and 19 s on 8×B300. No H3 Turbo timings are published.
- **LTX-2.5:** there's almost no data-center measurement. Estimates for a 5 s clip on 1×H100:
  - Fast: 20 s at 720p, 35 s at 1080p.
  - Pro: 65 s at 720p, 150 s at 1080p.

**Cost per output second**, base estimate at 60% utilization, confidential tier, 5 s clips:

| Profile | Cost per second | With low–high speed and price assumptions |
|---|---|---|
| Fast 720p | $0.004–0.006 | $0.001–0.016 |
| Fast 1080p | $0.006–0.010 | – |
| Pro 1080p | $0.026–0.042 | – |
| 4K 2160p | $0.08–0.12 | $0.014–0.48 |
| H3 Turbo | $0.023–0.027 (14 s: $0.034–0.039) | – |
| H3 | $0.08–0.09 (14 s: $0.13–0.15) | – |
| H3 Reference | $0.12–0.14 (14 s: $0.19–0.22) | – |

At 30% utilization costs double; at 85% they fall by about 30%. A 48/50 fps clip costs about twice a 24 fps clip per second.

**Platform costs:**

| Item | Cost |
|---|---|
| R2 storage | $0.015/GB-month, free egress |
| 1080p 10 s clip kept forever | about $0.09 |
| 4K 10 s clip kept forever | about $0.36 |
| Stripe | 8.9% of a $5 top-up, 5.9% of $10, 4.4% of $20 |
| NOWPayments | about 1–1.5% plus network fees |
| Alpha top-ups | the 10% haircut acts as a 10% fee |

### 2.3 How other subnets price (subnets.md)

| Subnet | Customer price | Miner pay | Emission ÷ revenue | Lesson |
|---|---|---|---|---|
| **SN51 Lium** (GPU rental) | Providers set prices within 0.5–2.5× of a 30-day median reference; 10–30% below RunPod Community | 95% of rental fees, plus an idle subsidy of about the reference price in alpha | 1.5–3.6× (August revenue $964K, team claim) | A market price and a revenue share work for rentals; its "burn" to UID 47 dodges the burn penalty (don't copy) |
| **SN53 Engy** (LLM inference) | 33–70% below the OpenRouter median; no free tier, no subscriptions | Team-set `score_rate` on paid, successful requests only, deliberately unlinked from buyer price; weekly epochs | Revenue undisclosed; published buyback-and-burn of about 1/17 of its emission value, with block links | The undercut is backed by a real cost edge (FP4 on RTX 5090); only paid requests score; buybacks can be made verifiable |
| **SN28 gm** (LLM resale) | Miners declare 8–70% off first-party list prices | Emissions pay discounted retail in alpha; USD pool with surplus burned (about 11%) | 2.3–2.7× (about $13.8K/day owed to 88 miners) | A USD-denominated pool works; burning is now penalized |
| **SN64 Chutes** | $4.50/h basis × GPU multiplier; per token, per step; no TEE surcharge; subscriptions were exploited at 56–324× plan value, then capped, and Base closed | GPU-time × multipliers | 5.7–8.9× on pay-as-you-go ($9.15K/day); Pine's March estimate 22–40× | Subsidized volume collapsed once subsidies were wound down (tokens −45%, revenue about −24%); list prices didn't rise |
| **SN4 Targon** (confidential GPUs) | Not published | Owner-set target and max price per card-hour, e.g. H200 $3.56, B300 $9.75, RTX PRO 6000 $2.00; unallocated emission burned | Self-reported $10.4M ARR, about 1.7× | Pay per attested card-hour, in USD |
| **SN90 KubeTEE** | Price card clamped by Targon's payouts | – | Recycling the unused pool cut its share to about 0.43% | Don't recycle or burn |
| **SN39 Basilica** | Miner bids plus a platform markup | Min(bid, budget), plus a revenue share; rest burned | Shutdown announced April 2026; repo still active | – |
| Media subnets (Nineteen, NicheImage, Dippy, video competitions) | Mostly free or unverified | – | – | **No subnet has verifiable revenue from paid image or video generation.** What people do pay for on-chain: detection, analytics, 3D |

### 2.4 Emission rules that change the strategy
- **Share follows price, not revenue.** Since 2026-06-22 a subnet's share follows its moving-average alpha price, × (1 − share of miner emission burned or recycled), through a gate at about rank 32.
  - The burn penalty was removed in v444 and restored two days later.
  - New subnets start with emission switched off.
- **Revenue is invisible on chain.** Buying alpha is the only lever on emission share, and it moves the average slowly.
- **Expect about $0 of TAO-backed subsidy for the first 1–3 months.**
- **Later, at rank 32:** miners' TAO-backed share is about $2,000/day, roughly 26 H200s running 24/7. At rank 35 it's about $730/day; at rank 50 about $114/day.
- **Keep `KUNO_PAY_RESIDUAL=renormalize`.** Recycling would cut the share through the burn penalty.

---

## 3. Miner pay

**Rule:** the recommended rate is the median eligible hardware's base cost at 60% utilization × 1.25. That gives miners +25% margin at 60% utilization, +77% at 85% and −37% at 30%; capacity pay covers the gap at low utilization.

| Profile | Confidential rate, USD per verified second | One rate per profile |
|---|---|---|
| `ltx-2.5-fast` | 720p $0.005, 1080p $0.010 | $0.008 |
| `ltx-2.5-pro` | 720p $0.017, 1080p $0.040 | $0.035 |
| `ltx-2.5-4k` | 1440p $0.042, 2160p $0.12 (provisional) | $0.09 |
| `h3-turbo` | 5 / 10 / 14 s: $0.033 / $0.039 / $0.047 | $0.040 |
| `h3` | 5 / 10 / 14 s: $0.11 / $0.15 / $0.18 | $0.15 |
| `h3-reference` | 5 / 10 / 14 s: $0.17 / $0.22 / $0.27 (provisional) | $0.22 |

**Adopted 2026-09-14, all still placeholders** (subnet `VALIDATING.md`, "Job pay" and "USD-denominated pay"):
- Items 1–4 below are in the code:
  - GPU-cost `vcu_weights` per profile in `profiles.json`, with the per-resolution weights in the table in item 2 and 48/50 fps ×2;
  - the rate card's `usd_per_vcu_second`, with `PLACEHOLDER_USD_PER_VCU_SECOND` 0.0019;
  - the open tier at 0.75 (`KUNO_OPEN_TIER_RATE`);
  - `gpu_hour_usd` `ltx-2.5` $0.80 and `minimax-h3` $1.50.
- **Duration factor** is `1 + slope × max(0, seconds − 5)` per profile, not one H3 slope of 0.045: `h3-turbo` 0.05, `h3` 0.06, `h3-reference` 0.065 (fitted to the 5/10/14 s rows), and LTX 0.03, provisional.
- **From §5 and §6:**
  - Validators pay only jobs with `billable_usd` above 0; canaries still count for every gate.
  - USD mode caps job pay at `KUNO_JOB_PAY_REVENUE_MULTIPLE` (default 1.0) × billable revenue per tempo, pays jobs at face value, and sends the rest of an undersubscribed pool to capacity miners, not to jobs.
- **Not built:** the per-miner cap by share of verified capacity, and flagging top-ups from miner coldkeys.

**Changes to the placeholders** (`protocol/.../rate_card.py`, `profiles.json`):
1. **`PLACEHOLDER_USD_PER_VCU_SECOND` 0.01 → about 0.0019.**
   - Today's 0.01 pays miners $10–73 per GPU-hour at 60% utilization, against $2–5 real cost. For `h3` it pays miners $0.60/s while the customer pays $0.12.
   - The subnets research independently lands on $0.0018–0.0030.
2. **Make VCU weights follow cost, including resolution and duration.** One weight per profile can't capture them: 1080p is under-weighted 1.3–1.9× and 2160p about 2×.

   | Profile | Proposed VCU |
   |---|---|
   | `ltx-2.5-fast` | 720p 3, 1080p 5 |
   | `ltx-2.5-pro` | 720p 9, 1080p 20 |
   | `ltx-2.5-4k` | 1440p 22, 2160p 60 |
   | `h3-turbo` | 5 / 10 / 14 s: 17 / 20 / 25 |
   | `h3` | 5 / 10 / 14 s: 60 / 76 / 95 |
   | `h3-reference` | 5 / 10 / 14 s: 90 / 114 / 143 |

   - **Multipliers:** 48/50 fps ×2, and an H3 duration factor of about 1 + 0.045 × (seconds − 5).
   - **If weights stay one per profile:** fast 4, pro 18, 4k 45, h3-turbo 20, h3 76, h3-reference 115.
   - **The rate card needs a resolution key and an fps multiplier.**
3. **Open-tier rate: 0.75× confidential, not 0.5×.** At 0.5× only RTX 4090/5090 cards break even at 60% utilization.
4. **Capacity pay `gpu_hour_usd`: `ltx-2.5` $0.80, `minimax-h3` $1.50** (placeholder today: $2.00).
   - Both stay below owned cost, so an idle GPU never profits on its own.
   - They close the gap at 30% utilization: an H3 H200 then earns about $3.60 per GPU-hour and an RTX PRO 6000 about $1.98, close to Targon's payouts.
5. **Keep the customer price ≥ 1.15–1.3× the miner rate,** so revenue alone could pay miners (the last column of §1).

---

## 4. Pricing structure

**Units and minimums:**
- **1 credit = $0.01.** Per-second prices with fixed resolution steps, on a published rate card.
- **Minimum charge $0.10 per job.**
- **Card top-up minimum $10** ($5 loses 8.9% to Stripe).

**Payment incentives and terms:**
- **+5% credits for TAO or alpha payments.** They can fund alpha buys (§6). Revisit the 10% alpha haircut, which works as a fee.
- **Credits don't expire.**
- **Refund failed and moderation-blocked jobs automatically.** The strike system already handles abuse.
- **No subscriptions at launch.** Every subnet with a working business is pay-as-you-go, and Chutes' plans were exploited at 56–324× their value. Offer volume bonuses instead, e.g. +10% credits at $100 and +20% at $1,000. If subscriptions come later, sell credit bundles with USD caps and pay miners only for what was actually paid.
- **No free tier that pays miners.** Any sign-up credit comes from the owner's share and is marked not billable.

**Later and positioning:**
- **Later:** an off-peak queue at −30–50%, like Vidu, once the fleet has idle hours.
- **Positioning (Proton-style):** Private is the headline product at market price for its quality peers. Standard is presented as the cheaper option with server-side conveniences (about 0.75× Private). Pricing Private at parity, Signal-style, would give the premium away.

---

## 5. Guardrails against subsidy abuse

At launch, emissions dwarf revenue. A miner who buys jobs that land on itself can take most of the pool.
- **Customers never choose the miner.** Already true: least-loaded routing, plus validator coverage ordering.
- **To build:** cap total job pay at k × net customer revenue in the window.
- **To build:** cap each miner's share of job pay by its share of verified capacity.
- **To fix:** validator test jobs, promos, trials and refunded jobs must be `credit: false`. The USD pay report currently counts canaries as revenue and can't see credits.
- **Flag** top-ups from coldkeys that own miner hotkeys.
- **Enforce collateral.** It's configured per GPU; the requirement must actually be set.

---

## 6. Launch emissions
- **Plan for no subsidy in months 1–3.** Emission starts off, and the moving price ramps slowly.
- **Spend emissions on attested capacity, not customer discounts.** Fund promotions from the owner's share.
- **Publish the subsidy ratio** (emission value ÷ customer revenue, net of canaries and credits), with a glide path: under 3× by month 6, under 1.5× by month 12.
- **Turn TAO and alpha revenue into steady, published alpha buys,** Engy-style: a page listing each buy with its block link. It is the only lever on emission share.
- **Keep the rate card stable,** and announce changes before they take effect.

---

## 7. Blockers and risks that affect price
- **LTX license.** LTX-2.5 falls under the LTX-2.x Community License (2026-08-11). Above $10M revenue, and for "directly competing" services, a commercial license from Lightricks is required, at an unpublished price. **Ask Lightricks before charging for LTX-2.5.** The license also forbids stripping watermarks or provenance data, which applies in Private mode too.
- **H3 license.** H3 can't be served, and its outputs can't be shown, in the US, EU, UK or South Korea. Above $20M annual revenue it needs MiniMax's written permission, and the UI must name "MiniMax H3".
- **Speed data.** Speed is mostly estimated, so every cost-based number carries about ±50% until §8 is done.
- **Price decline.** Expect the LTX Fast band to fall to $0.02–0.03 within 6–12 months. Keep the margin that absorbs it.

---

## 8. Benchmarks to run first

This is the stage-1 GPU test, on rented GPUs without a TEE; the confidential overhead needs the later TDX stage.
1. `ltx-2.5-4k` at 2160p: the widest cost range.
2. `h3-reference` against `h3`.
3. LTX Fast and Pro at 720p and 1080p on RTX PRO 6000, H200 and B200.
4. `h3-turbo` through its lightx2v runtime: no public timings.
5. Confidential-mode overhead and load times in the real VM shapes.
6. RTX 4090/5090 speed with offload, for the open tier.

---

## 9. Corrections to research_market.md (2026-09-11)
- **Seedance on OpenRouter:** the $0.067/s figure was the 480p rate. At 720p it is $0.151/s, and $0.374 at 1080p. Mini is $0.076, Fast $0.091, 2.5 $0.231 at 720p.
- **Wan 3.0:** $0.05 / $0.10 / $0.20 at 480p / 720p / 1080p, not $0.0425.
- **Grok Imagine 1.5:** $0.08 was the 480p rate; 720p is $0.14 and 1080p $0.25.
- **Pika:** $28/month is the Pro plan; Standard is $10 for 700 credits.
- **Kling:** "$1 = 66 credits" is the consumer rate; the developer API bills units at $0.14 each.
- **Azure confidential H100:** no premium. $8.90/h is West Europe, where the normal VM is $9.08.
- **LTX API:** Lightricks' LTX-2.5 Fast is $0.09 / 0.13 / 0.19 / 0.30 per second (720p / 1080p / 1440p / 4K), and Pro is $0.12 / 0.17.
