# KunoWorld pricing: cost basis (2026-09-14)

Marks: **[C]** confirmed from a primary page, dataset or repo; **[S]** secondary (aggregator, vendor claim, press, search snippet); **[U]** unverified or inferred; **[E]** my estimate, with the method stated.

All prices are USD. "GPU-h" means GPU-hour. Rental prices come from pages fetched on 2026-09-13/14 unless another date is given. Tables are produced by `costmodel.py` and `extras.py` in this folder; rerun them after editing the inputs.

This builds on `research_market.md` §A3 and `research_models.md` / `research_model_capabilities.md`, and updates them. §7 lists what changed.

---

## 0. Headline findings

1. **The placeholders pay miners 2–6× the customer price.**
   - At $0.01 per VCU-second, `ltx-2.5-fast` earns a miner $0.05/s, but the customer pays $0.024–0.04/s.
   - `h3` earns $0.60/s against $0.12/s, and `h3-reference` $0.64/s against $0.10/s.
   - At my speed estimates that is **$16–122 per GPU-hour at 100% utilization ($10–73 at 60%)**, against confidential rental costs of $1.8–5.6/GPU-h.
   - A replacement value of **$0.0019 per VCU-second** is derived in §8.4.
   - At USD-mode this only matters once customer revenue funds pay. With emission-only pay, every miner is renormalized to the pool anyway.
2. **The `h3` and `h3-reference` customer prices are below cost.**
   - Base case: rented confidential H200/B200/B300 at 60% utilization.
   - `h3` costs $0.08–0.15 per output second against a $0.12 price.
   - `h3-reference` costs $0.12–0.22 against $0.10. Its price is lower than `h3` even though it costs about 1.5× more to run.
   - `ltx-2.5-fast` (price/cost ≈ 3.5–7×) and `ltx-2.5-4k` at 1440p are comfortably priced.
   - `ltx-2.5-pro` at 1080p and `h3-turbo` are thin.
3. **VCU weights are roughly right only at the lowest resolution and 5 s.** They ignore:
   - resolution: LTX 1080p costs 1.7–2.3× 720p per second;
   - H3 duration: a 14 s clip costs 1.45–1.6× a 5 s clip per second;
   - frame rate: 48/50 fps costs ≈2× 24 fps [E];
   - reference-to-video: about 1.5× [C, one measurement].
   The current weights imply 1 VCU ≈ 1 H200 GPU-second per output second for H3 at 5 s.
4. **Capacity pay of $2.00/GPU-h is too high for the cheap SKUs.**
   - Owned-hardware cost is ≈$0.95/GPU-h for an RTX PRO 6000 Server Edition and ≈$2.05 for an H200.
   - At $2.00, an owner's idle confidential RTX PRO 6000 is profitable on capacity pay alone.
   - Recommendation: **$0.80/GPU-h for `ltx-2.5`** and **$1.50/GPU-h for `minimax-h3`**.
5. **The emission subsidy is small for a subnet ranked #30–60, and near zero for a new one.**
   - A subnet just above the gate (rank ~32) sends miners 8.5 TAO/day ≈ **$2.0k/day** of TAO-backed value, about 620 H200-hours/day or 26 GPUs.
   - At rank 35 it is $0.7k/day; at rank 50 about $110/day, or 1.5 GPUs.
   - The alpha paid out is worth 2–10× more at spot price, but it has no TAO behind it.
   - A new subnet starts with emission switched off and a moving price near zero.
6. **LTX-2.5 has almost no public datacenter wall-time measurements.**
   - Every LTX number here beyond the anchors in §3.1 is an estimate with a ±50% band. `ltx-2.5-4k` at 2160p spans 5× between low and high.
   - H3 is well measured on H200 and B300 for 5 s at 50 steps; 10–14 s and Turbo are derived from measured per-step times.
   - **Run `benchmark_ltx_quantized.py` (and the equivalent for H3 and confidential mode) before signing any real card.**

---

## 1. GPU prices (September 2026)

### 1.1 On-demand, $/GPU-h

| GPU | RunPod Community / Secure [C] | Vast.ai [S] | Lambda [C] | Nebius [C] | CoreWeave [C] | Crusoe [C] | Hyperbolic [C] | Together [C] | Lium (SN51) [S] | Chutes rate table [C] | GCP [S] | AWS [S] | Median (GetDeploying) [S] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H100 | 1.99 PCIe / 2.89; SXM 2.69 / 3.49; NVL 2.59 / 3.19 | 1.73 | 3.99–4.29 (SXM); GetDeploying lists 3.29 | 3.85 | 6.16 (8×) | 3.90 | 3.19 (SXM) | 3.99 | 1.41–1.50 | 1.79 PCIe, 2.35 SXM, 2.25 NVL | 11.07 | 6.88 (p5) | **3.29** |
| H200 | 3.59 / 4.59 | 3.63 | not listed | 4.50 | 6.30 (8×) | 4.29 | 3.99 | 5.99 (a GetDeploying snapshot shows 2.99) | 2.75 | 2.75 | 10.62 (a3-ultra) | 7.91 (p5en) | **4.29** |
| B200 | 5.98 / 6.79 | 5.63 | 6.69–6.99 | 7.15 | 8.60 (8×) | contact sales | 5.99 | 8.19 (GetDeploying: 4.09) | n/a | 4.50 | 16.11–16.27 (a4) | 14.24 (p6-b200) | **6.13** |
| B300 | 6.94 / 7.89 | 9.38–13.75 | not listed | 7.85 | contact sales (spot 4.48) | n/a | n/a | contact sales | n/a | 4.50 | n/a | 17.80 (p6-b300) | **7.85** |
| RTX PRO 6000 (96 GB) | 1.69 / 2.09 | 1.06–1.57 | n/a | 1.80 | 2.50 (8× server) | n/a | n/a | n/a | 1.19 | 1.80 | 4.50 (g4-standard-48, whole VM) | 3.36 (G7e) | **2.20** (+22% over 12 months) |
| RTX 5090 | 0.69 / 0.99 | 0.43 | n/a | n/a | n/a | n/a | n/a | n/a | 0.50 | 0.70 | n/a | n/a | **0.63** |
| RTX 4090 | 0.34 / 0.74 | 0.30 | n/a | n/a | n/a | n/a | n/a | n/a | 0.30–0.35 | 0.40 | n/a | n/a | **0.41** |

Notes on the table:
- **Chutes' `hourly_rate`** ([api.chutes.ai/nodes/supported](https://api.chutes.ai/nodes/supported), fetched 2026-09-14) is the price basis for Chutes compute units, not a rental price. B200 and B300 are both $4.50, which is the maximum and the normalizing basis.
- **Nebius'** page carries a stale `2024-12-10` date stamp, but its prices match GetDeploying's September 2026 snapshot.
- **Targon (SN4) rental** "confidential H200s from $1.90/hr", with tiers Small $2.40 / Medium $4.80 / Large $9.60 (March 2026) [S, search snippet]. The live miner payouts below are more useful.
- **Price trend:** GetDeploying's index says on-demand prices rose +3.7% over 12 months and +1.9% over 4 weeks. RTX PRO 6000 rose +22% over 12 months and its card price nearly doubled (§1.4).

**Targon's live miner payouts** ([stats.targon.com/api/miners](https://stats.targon.com/api/miners), 2026-09-14) [C data; the unit is U, read here as per 8-GPU node-hour]:

| compute_type | Payout per 8-GPU node | $/GPU-h |
|---|---|---|
| TDX-VM-NVIDIA-H100 | $32 | 4.00 |
| TDX-VM-NVIDIA-H200 and TDX-HOPPER-NVIDIA-H200 | $28.48 and $28 | 3.50–3.56 |
| TDX-VM-NVIDIA-B300 | $78 | 9.75 |
| TDX-VM-NVIDIA-RTX6000B | $16 | 2.00 |

This is what a competing confidential-compute subnet pays for attested TDX capacity. It is the best benchmark for our capacity pay and total miner revenue.

### 1.2 Reserved and committed prices, $/GPU-h

| GPU | 1-month | 3–6-month | 1-year | 2–3-year | Source |
|---|---|---|---|---|---|
| H100 | HyperAI 1.53; Vast 2.20 | Together 3.09–3.69 (7–180 d) | Novita 2.79 | AWS 2.97 (36 mo); Azure 3.84; GCP 4.86 | GetDeploying [S], Together [C] |
| H200 | – | Vast 4.15 (6 mo); Together 3.99–4.99 | DigitalOcean 3.40; wholesale bare metal ≈2.10 | Verda 3.15 (24 mo); GCP 4.66 (36 mo); Azure 6.86 (36 mo) | [S] |
| B200 | – | Vast 3.95 (3 mo); Together 6.79–7.99 | Hyperstack 5.10 | 36 mo as low as 2.25; GCP 7.16 | IntuitionLabs 2026-07-20 [S], GetDeploying [S] |
| B300 | – | – | – | TheAI Cloud 4.90 (24 mo); Verda 5.68 (24 mo); Civo 5.49 (36 mo); Impossible Cloud 4.32 (60 mo); spot 3.79–6.94 | GetDeploying [S] |
| RTX PRO 6000 | reserved 0.48–1.78 depending on term | | | | GetDeploying [S] |
| RTX 5090 | HyperAI 0.21; Vast 0.41 | Nova 0.50 (6 mo) | Novita 0.46 | Database Mart 0.41 (24 mo) | [S] |
| RTX 4090 | – | – | Vast 0.29; Novita 0.27 | – | [S] |

Rules of thumb:
- A 1-year reservation is ≈ −32% versus on-demand and 3-year ≈ −50% (GetDeploying index) [S].
- Reserved commitments cut 25–50% at the same provider (IntuitionLabs) [S].
- CoreWeave says "up to 60%" [C].

### 1.3 Bare-metal 8-GPU servers, monthly

| Server | $/GPU-h | ≈ $/month for 8 GPUs (730 h) | Source |
|---|---|---|---|
| 8× H200 SXM, wholesale on-demand | 3.50 ($28/node-h) | ≈ $20.4k | gpuaas.com via search [S] |
| 8× H200, 1-year reserved | ≈2.10 | ≈ $12.3k | [S] |
| 8× H200, CoreWeave node on-demand / spot | 6.30 / 2.62 | $36.8k / $15.3k | [C] |
| 8× B200, 36-month (lowest) | 2.25 | ≈ $13.1k | IntuitionLabs [S] |
| 8× B200, Vast 3-month | 3.95 | ≈ $23.1k | [S] |
| 8× B300, 24–36-month | 4.90–5.68 | ≈ $28.6–33.2k | [S] |
| 8× RTX PRO 6000 server, CoreWeave on-demand | 2.50 | ≈ $14.6k | [C] |

- **BIOS access and TDX availability are not listed by any of these.** A confidential-tier miner needs a lessor that lets them enable TDX, set GPU CC mode and run QEMU (§2).
- **OpenMetal** offers bare-metal H200 NVL on dual Xeon 6530P with TDX and GPU CC as an engineered build: "attestation work is in progress" and each workload is validated by their team. No public price [S].
- **Corvex** markets HGX B200 with CC [S].

### 1.4 Owning the hardware: all-in $/GPU-h at 3-year depreciation

Formula per available GPU-hour, with utilization applied later:

`(capex × (1 − residual) / 26,280 h + kW × colo $/kW-month / 730 + financing (9%/yr on ≈60% average balance) + ops) / 8`

| Server | Inputs (low / base / high) | Low | **Base** | High |
|---|---|---|---|---|
| **HGX H200** 8-GPU | capex $320k / $370k / $420k [S Mercatus]; residual 25/25/0%; 8.5/10/10.5 kW; colo $150/$200/$250 per kW-month [S] | 1.36 | **2.05** | 2.90 |
| **HGX B200** | $400k / $450k / $500k [S Mercatus]; 12/14.3/14.3 kW (NVIDIA DGX B200 max 14.3 kW; Mercatus bills 12 kW) | 1.74 | **2.57** | 3.53 |
| **HGX B300** | $450k / $520k / $600k [S: "DGX B300 $400–500k", Aivres HGX B300 "from ~$430k" (late 2025), B300 GPU ≈$53k (Jul 2026)]; 14/15/15 kW [U] | 1.96 | **2.91** | 4.12 |
| **8× RTX PRO 6000 Server Edition** on a TDX Xeon host | cards $8.6k (launch MSRP) / $12k / $16k (NVIDIA marketplace, Sep 2026 [S Thunder Compute]) plus a $42–62k chassis; 6/7/7 kW (5.4 kW at 450 W caps, 6.7 kW at 600 W [S vrlatech]) | 0.55 | **0.95** | 1.42 |

- Mercatus' own figures are $2.29 (H200) and $2.84 (B200) per GPU-h **at 70% utilization**, i.e. $1.60 and $1.99 per available hour, with no financing. That is consistent with my low-to-base range.
- Colocation: GPU-density colo is $150–250/kW-month; CBRE's North American wholesale average is $196 (Northern Virginia $173, Singapore $403) [S].
- Depreciation is 55–70% of owned cost, so **the residual-value assumption dominates**.

### 1.5 Prices used in the cost model

| Tier | Hardware | Low | Base | High | Rationale |
|---|---|---|---|---|---|
| Confidential | RTX PRO 6000 BSE (1 GPU) | 0.95 (owned) | 1.80 | 2.50 | Chutes and Nebius list 1.80; Targon pays 2.00; CoreWeave server 2.50 |
| Confidential | H200 | 2.05 (owned) | 3.20 | 4.80 | Phala reserved 3.20 / on-demand 4.80; Targon pays 3.56; non-CC Lium 2.75 |
| Confidential | B200 | 2.57 | 4.50 | 6.80 | Chutes 4.50; Vast 3-month 3.95; median 6.13; RunPod 6.79 |
| Confidential | B300 | 2.91 | 5.60 | 7.90 | Phala reserved 5.60; 24–36-month 4.90–5.68; RunPod 7.89 |
| Open | RTX 4090 | 0.25 | 0.34 | 0.74 | RunPod Community / Secure; Vast and Lium 0.30 |
| Open | RTX 5090 | 0.40 | 0.65 | 0.99 | Vast 0.43; median 0.63; RunPod Secure 0.99 |
| Open | RTX PRO 6000 (CC off) | 1.06 | 1.69 | 2.20 | Vast; RunPod Community; median |
| Open | H100 | 1.50 | 2.59 | 3.29 | Lium; RunPod NVL; median |

---

## 2. Confidential computing: premiums, availability and overhead

### 2.1 Price premium versus the same GPU without CC

| Offer | CC price | Non-CC comparison | Premium | Notes |
|---|---|---|---|---|
| **Azure** NCC40ads H100 v5 (SEV-SNP + H100 NVL) | $8.90 on-demand, $1.64 spot; no reservations | NC40ads H100 v5 $6.98 | **+27.5%** | [S Vantage]. SEV-SNP is not admitted by KunoWorld |
| **GCP** A3 High confidential (TDX + H100) | GPU CC line item ≈ **$0.98/GPU-h** on-demand, $0.39 spot, $0.46 Flex-start, on top of the A3 price | a3-highgpu $10.98/GPU-h (1-GPU shapes are spot/Flex only) | ≈ **+9%** | [S snippet of GCP confidential VM pricing]. 3 zones only |
| **GCP** G4 confidential (Turin SEV-SNP + RTX PRO 6000) | not found | g4-standard-48 $4.50/h | [U] | SNP, so not admitted |
| **Phala Cloud** (TDX + NVIDIA CC) | H100 $3.08 / H200 $4.80 / B300 $6.50 on-demand; $2.38 / $3.20 / $5.60 reserved; 24 h minimum, 30 days for B300 | medians $3.29 / $4.29 / $7.85 | **−6% / +12% / −17%** | [C phala.com/gpu-tee]. Runs dstack CVMs, not our image |
| **VoltageGPU** (TDX) | H100 CVM $6.95; H200 CVM $6.58–8.08; B200 container $10.60; RTX 6000B VM $3.80 with CC off | medians | **+53–111%** | [S vendor comparison page] |
| **Targon payouts** (supply side) | H200 $3.56, RTX6000B $2.00 per GPU-h | Lium non-CC H200 $2.75, RTX PRO 6000 $1.19; Vast $3.63 / $1.06 | **+0–30% (H200), +18–68% (RTX 6000)** | [C data] |
| **Own bare metal** | same HGX; needs an Emerald Rapids or Granite Rapids Xeon host, BIOS access, the TDX module, QGS/PCCS, GPUs in CC mode | same server | **≈0% hardware; ops premium +5–15% [U]** | AMD EPYC HGX hosts cannot join (SNP not admitted), which shrinks supply |

**Conclusion.**
- Cloud CC premiums range from ≈0 at Phala to +9% (GCP) and +27% (Azure), up to +50–110% at boutique TDX clouds.
- Cloud CVMs don't produce KunoWorld's measurements: `shapes.json` pins QEMU 9.1 ACPI and MRTD layouts, so each platform would need its own golden set (research_tee §6). **Mainnet confidential miners therefore effectively need bare metal they control, owned or leased with BIOS access.**
- That makes the relevant premium a scarcity and ops premium on bare metal, which I put at +0–30% [U]. The base rented prices in §1.5 sit 15–20% above non-CC marketplace prices to reflect it.

### 2.2 Performance overhead

| Study | Setup | Result | Mark |
|---|---|---|---|
| arXiv [2608.26575](https://arxiv.org/abs/2608.26575), "Benchmarking Confidential Computing Performance on NVIDIA Blackwell GPUs" (Asad and Grunseid; Aug 27 2026, rev. Sep 1) | 8× B200, Xeon 6 | Well-configured inference **1–3%**: under 1% single-GPU with CUDA graphs, ~1.5% TP4, ~3% TP8. Misconfigured stacks **30–40%**. H2D 3.5 GB/s under CC vs 51.6 GB/s without. NVLink encryption costs ≈10% of NCCL bandwidth. GPU compute, energy and memory unaffected. No diffusion or video tests | [C abstract; details C via research_tee] |
| arXiv 2607.19353 | GCP A3 H100 + TDX | Small-LLM throughput −17.7% / −21.1%; time-to-first-token +21–28% | [C] |
| arXiv 2606.23969 "Serialized Bridge" | TDX + Blackwell CC | LLM serving −13–27%; **model loading 34× slower** | [C via research_tee] |
| arXiv 2409.03992 (Phala) | H100 | under 7% average for LLMs; ≈0 for 70B | [C] |

**Video diffusion: no benchmark exists [C, absence].**
- My estimate is **2–5%** for a resident single-GPU LTX run. Denoising is compute-bound, and only prompt embeddings and the final frames cross the bounce buffer.
- For H3 with Ulysses-4: **+1–3%** on H200 Protected PCIe (NVLink unencrypted) and **+3–8%** on B200/B300 multi-GPU passthrough (NVLink encrypted, all-to-all every layer) [E].
- Model: low 2%, **base 5%**, high 15% (covers a misconfigured stack).

**Loads are the real cost.**
- LTX is 66 GB and H3 124 GB. At 3.5–9.6 GB/s, LTX takes at least 7–19 s to transfer; with the serialized-bridge slowdown, minutes [E].
- Keep profiles resident. A confidential GPU that LRU-swaps `ltx-2.5-fast`, `ltx-2.5-pro` and `ltx-2.5-4k` pays a reload on every swap. Treat that as lost utilization.

---

## 3. Generation speed

### 3.1 Measured and vendor data points

**LTX-2.5 (and LTX-2.3 as a comparable)**

| Setup | Result | Mark |
|---|---|---|
| SGLang CI, **1× H100**, LTX-2.5 diffusion-decoder pipeline, 768×448, 57 frames | **E2E 11.0 s**, decoder 3.35 s | [C sglang PR #39206] |
| SGLang CI, 1× H100, LTX-2.3 dual TI2V | E2E 11.15 s, mean denoise 304 ms/step, **load 44 s** | [C same] |
| SGLang CI, 1× H100, LTX-2.3 HQ | E2E 29.7 s, DiT 24.3 s, **load 108 s** | [C same] |
| SGLang cookbook, LTX-2.5 distilled 8-step at 960×544 | fp8 "denoising time unchanged … bound by memory traffic"; transformer 35.37 → 18.11 GB | [C] |
| SGLang cookbook, diffusion decoder on 2× H200 (Ulysses-2), 960×544, 121 frames | 3.38 s untiled / 4.08 s tiled | [C] |
| **RTX 5090**, LTX-2.3 distilled fp8-cast, 1280×704 × 97 frames | **49.8 s per clip**. Diffusion ≈12 s (8 steps @ 1.58 it/s, 3 refine @ 2.35 s/it); decode, audio and encode ≈35 s; +20 s the first time a shape is seen | [C community dataset witcheer/rtx-5090-benchmarks] |
| Same, 768×512 × 97 frames | 43.5 s (steady ≈39 s) | [C same] |
| RTX 5090, LTX-2.5 distilled, 720p 4 s | ≈25 s; 8 s ≈3 min once weights stream from RAM | [S NVIDIA guide via runaihome] |
| RTX 5090, LTX-2.5 distilled bf16 with offload, 720p 8 s I2V | ≈80 s | [S note.com] |
| RTX 3090, LTX-2.5 int8, 5 s | ≈2.5 min without SageAttention | [S runaihome] |
| **2× GB200**, LTX-2.5, 10 s 720p I2V | **6.8 s** | [S vendor, VentureBeat 2026-08-11] |
| **LTX managed API**, 10 s at 1080p | **23.7 s** end to end (hardware undisclosed) | [S vendor] |
| **1× B200**, LTX-2.3, 5 s 1080p, FastVideo with NVFP4 and custom kernels | **4.55 s**, "3.9× faster than next-fastest" (implies ≈18 s) | [S Hao AI Lab 2026-03-11] |

No public 720p or 1080p wall time exists for LTX-2.5 on H100, H200, B200 or RTX PRO 6000 at 5–10 s [C, absence].

**MiniMax H3**

| Setup | Result | Mark |
|---|---|---|
| **4× H200 Ulysses-4**, SGLang, T2VA 1344×768, 124 frames (5.17 s), 50 steps | **E2E 74.4 s** with a 1344×768 warmup (denoise 71.7 s, decode 1.3 s); 84.1 s with the default warmup. Mean 75.1 s lossless | [C SGLang cookbook] |
| 4× H200 TP2 + Ulysses-2 | 78.3 s | [C] |
| **8× H200 Ulysses-8**, SGLang v0.5.18, 50 steps (49 evaluations), measured 2026-08-18 | T2VA **5 s 39.67 s, 10 s 112.44 s**; FL2VA 41.31 s / 114.02 s. Diffusers CP8 74.34 s / 207.71 s. Cache-DiT conservative 28.0 s (SSIM 0.90) | [C LMSYS 2026-08-27] |
| **8× B300**, FL2VA, 124 frames, 50 steps | **19.04 s** bf16, 18.03 s fp8; **Ref2VA 29.12 s** bf16 (1.53× FL2VA) | [C cookbook] |
| **GB300, 4-GPU host**, FL2VA 5 s, 50 steps | **33.10 s** warm median | [C cookbook] |
| **4× B300 dense FlashAttention baseline**, 4 forward passes | **3.77 s / 9.84 s / 18.45 s** denoise for 124 / 243 / 362 frames, i.e. 0.94 / 2.46 / 4.61 s per evaluation. Decode 0.87 / 1.71 / 2.56 s | [C cookbook, FastH3 table] |
| 4× H100 (TP2 + Ulysses-2) | "13.25 s pipeline latency", which contradicts the H200 figures; workload unknown | [U] |
| 2× RTX 5090, 50 steps, 5 s | 559.7 s | [C] |
| 1× RTX 4090 int8, 20 evaluations, 107 frames | 164–303 s | [C] |
| Load time, B300 bf16 | **114–118 s** | [C] |
| LightX2V H3 Turbo 4/8-step | **no published timings** (repo, HF card and diffusers guide checked) | [C, absence] |

### 3.2 Wall-time model (warm, resident, one clip)

**LTX-2.5 reference: 1× H100, bf16, estimated [E].** Method: anchored on the SGLang CI H100 E2E (11 s for a tiny clip, so ≈8–9 s of fixed text-encode, decode and mux), the RTX 5090 per-step measurements, the vendor B200/GB200/API figures, and token counts.

- 720p runs stage 1 at 640×352 (3.5k tokens) and stage 2 at 1280×704 (14k tokens).
- 1080p runs stage 1 at 8.2k and stage 2 at 32.6k tokens.
- Pro's stage 1 is 30 steps × 3–4 passes (CFG + STG + modality guidance, diffusers defaults) ≈ 90–120 evaluations.

| Profile | 720p 5 s | 720p 10 s | 1080p 5 s | 1080p 10 s |
|---|---|---|---|---|
| `ltx-2.5-fast` (8 + 3 steps) | 12 / **20** / 32 | 25 / **40** / 65 | 22 / **35** / 55 | 50 / **80** / 130 |
| `ltx-2.5-pro` (30 + 3 steps) | 40 / **65** / 100 | 90 / **140** / 210 | 100 / **150** / 220 | 210 / **320** / 480 |

Cross-checks:
- B200 at 2.5× H100 gives fast 1080p 5 s ≈14 s, in line with FastVideo's implied ≈18 s "next-fastest".
- It gives 10 s 720p ≈16 s single-GPU, versus the vendor's 6.8 s on 2× GB200 with optimizations.
- It gives 10 s 1080p ≈32 s single-GPU, versus the LTX API's 23.7 s.

**Hardware speed relative to H100 for single-GPU LTX (slow / base / fast) [E]:**

| GPU | Slow | Base | Fast | Basis |
|---|---|---|---|---|
| H200 | 1.0 | **1.1** | 1.2 | |
| RTX PRO 6000 BSE | 0.7 | **0.85** | 1.0 | SGLang VDN-H3: 1× B200 is 3.4× faster than 1× RTX PRO 6000 per evaluation at mxfp8 [C] |
| B200 | 2.0 | **2.5** | 3.0 | |
| B300 | 2.2 | **2.7** | 3.2 | |
| RTX 5090 (fp8-cast + group offload) | 0.25 | **0.45** | 0.7 | |
| RTX 4090 (int8 weight-only + group offload) | 0.12 | **0.25** | 0.4 | |

**`ltx-2.5-4k` on 1× H200 [E, very uncertain].**
- The DFR detailing stage works on ≈230k tokens at 1440p and ≈518k at 2160p for 5 s (the docs give `sp_max_tokens` 524,288).
- Low assumes linear-cost tiling; high assumes full attention.
- The 10 s case assumes temporal chunking.

| Clip | Low | Base | High |
|---|---|---|---|
| 1440p 5 s | 85 s | **150 s** | 240 s |
| 2160p 5 s | 160 s | **400 s** | 850 s |
| 2160p 10 s | 340 s | **850 s** | 1,800 s |

B200 and B300 are 0.44× and 0.41× of the H200 time.

**MiniMax H3 on 4 GPUs (low / base / high).** The 5 s `h3` figures on H200 and B300 are measured [C]; everything else is derived [E].
- Longer clips use measured per-evaluation frame scaling: ×2.61 at 243 frames and ×4.56 at 345.
- Turbo is 8 evaluations. Its low bound assumes SGLang-class kernels; its high bound assumes the in-process diffusers-modular runtime, since LMSYS measured diffusers at 1.9× SGLang.
- Reference-to-video is 1.0–1.6× `h3`, base 1.5× [C, B300].
- B200 is 1.1× B300 [U].

| Profile | 4× H200 5 s | 10 s | 14 s | 4× B300 5 s | 10 s | 14 s |
|---|---|---|---|---|---|---|
| `h3-turbo` | 16 / **22** / 30 | 38 / **50** / 65 | 63 / **85** / 111 | 9 / **12** / 16 | 23 / **30** / 41 | 38 / **50** / 71 |
| `h3` | 70 / **75** / 85 | 185 / **200** / 230 | 300 / **335** / 380 | 33 / **42** / 50 | 88 / **107** / 130 | 150 / **187** / 225 |
| `h3-reference` | 70 / **112** / 135 | 185 / **300** / 370 | 300 / **500** / 610 | 33 / **63** / 80 | 88 / **160** / 208 | 150 / **280** / 360 |

**Other effects not in the tables:**
- **Frame rate:** 48 or 50 fps doubles frames, so ≈2.0–2.2× the 24 fps cost per output second [E]. The profiles and pricing do not vary by fps.
- **Load times** (once per start, or per LRU swap):
  - LTX-2.3 on H100: 44–108 s [C];
  - H3 on B300: 114–118 s [C];
  - several times longer under CC without tuning [E].
- **Warmup:** the first request at a new shape costs +10–20 s [C: 5090 +20 s; H200 84→74 s after warmup].

---

## 4. Cost per output second

### 4.1 Formula and assumptions

`$/output-s = $/GPU-h × GPUs × wall_s × (1 + CC overhead) / 3600 / clip_s / utilization`

- **Prices:** from §1.5.
- **CC overhead:** 2 / 5 / 15% on the confidential tier, 0 on the open tier.
- **Utilization:** 30%, 60% or 85% of hours spent on paid jobs. It must also absorb validator canaries, admission probes, audit replays, reloads and failed jobs.
- **Clip length:** `clip_s` is the requested duration, taken as the billable seconds. H3's snapped 5.17 s is not credited, which is conservative.
- **Scenario bands:**
  - "Low" = low price × low wall time × low CC;
  - "High" = high price × high wall time × high CC;
  - both shown at 60%, alongside "base" at 30%, 60% and 85%.

### 4.2 Confidential tier, condensed (5 s clips unless noted), $/output-s

| Profile | Res | Hardware | GPU-s per out-s | Low @60% | Base @30% | **Base @60%** | Base @85% | High @60% | Customer price |
|---|---|---|---|---|---|---|---|---|---|
| ltx-2.5-fast | 720p | RTX PRO 6000 BSE | 4.7 | 0.0011 | 0.0082 | **0.0041** | 0.0029 | 0.0122 | 0.024 |
| ltx-2.5-fast | 720p | H200 | 3.6 | 0.0019 | 0.0113 | **0.0057** | 0.0040 | 0.0164 | 0.024 |
| ltx-2.5-fast | 720p | B200 / B300 | 1.6 / 1.5 | 0.0010 | 0.0070 / 0.0081 | **0.0035 / 0.0040** | 0.0025 / 0.0028 | 0.012 | 0.024 |
| ltx-2.5-fast | 1080p | RTX PRO 6000 BSE | 8.2 | 0.0020 | 0.0144 | **0.0072** | 0.0051 | 0.0209 | 0.04 |
| ltx-2.5-fast | 1080p | H200 | 6.4 | 0.0035 | 0.0198 | **0.0099** | 0.0070 | 0.0281 | 0.04 |
| ltx-2.5-fast | 1080p | B200 / B300 | 2.8 / 2.6 | 0.0018 | 0.0123 / 0.0141 | **0.0061 / 0.0071** | 0.0043 / 0.0050 | 0.020 | 0.04 |
| ltx-2.5-pro | 720p | H200 / B200 / B300 | 11.8 / 5.2 / 4.8 | 0.003–0.007 | 0.023–0.037 | **0.0114–0.0184** | 0.008–0.013 | 0.036–0.051 | 0.04 |
| ltx-2.5-pro | 1080p | H200 / B200 / B300 | 27.3 / 12.0 / 11.1 | 0.008–0.016 | 0.053–0.085 | **0.026–0.042** | 0.019–0.030 | 0.080–0.112 | 0.07 |
| ltx-2.5-4k | 1440p | H200 / B200 / B300 | 30 / 13 / 12 | 0.008–0.015 | 0.058–0.093 | **0.029–0.047** | 0.020–0.033 | 0.096–0.135 | 0.12 |
| ltx-2.5-4k | 2160p | H200 / B200 / B300 | 80 / 35 / 33 | 0.014–0.028 | 0.15–0.25 | **0.077–0.124** | 0.054–0.088 | 0.34–0.48 | 0.20 |
| h3-turbo | 768p 5 s | 4× H200 / B200 / B300 | 17.6 / 10.4 / 9.6 | 0.010–0.012 | 0.046–0.055 | **0.023–0.027** | 0.016–0.019 | 0.052–0.061 | 0.06 |
| h3-turbo | 768p 14 s | 4× H200 / B200 / B300 | 24 / 16 / 14 | 0.015–0.017 | 0.069–0.078 | **0.034–0.039** | 0.024–0.028 | 0.081–0.085 | 0.06 |
| h3 | 768p 5 s | 4× H200 / B200 / B300 | 60 / 37 / 34 | 0.035–0.054 | 0.16–0.19 | **0.081–0.093** | 0.057–0.066 | 0.16–0.17 | 0.12 |
| h3 | 768p 10 s | 4× GPUs | 80 / 47 / 43 | 0.047–0.072 | 0.21–0.25 | **0.103–0.124** | 0.073–0.088 | 0.21–0.24 | 0.12 |
| h3 | 768p 14 s | 4× GPUs | 96 / 59 / 53 | 0.057–0.083 | 0.26–0.30 | **0.129–0.149** | 0.091–0.105 | 0.26–0.28 | 0.12 |
| h3-reference | 768p 5 s | 4× GPUs | 90 / 55 / 50 | 0.035–0.054 | 0.24–0.28 | **0.121–0.139** | 0.085–0.098 | 0.26–0.28 | 0.10 |
| h3-reference | 768p 14 s | 4× GPUs | 143 / 88 / 80 | 0.057–0.083 | 0.39–0.44 | **0.193–0.222** | 0.136–0.157 | 0.41–0.45 | 0.10 |

- **Owned hardware at 85% utilization** (the lowest possible floor) is roughly a fifth to a third of the rented base cost at 60%: `ltx-2.5-fast` 720p $0.0007, 1080p $0.0013; `ltx-2.5-pro` 1080p $0.0057; `h3-turbo` 5 s $0.0069; `h3` 5 s / 14 s $0.025 / $0.040; `h3-reference` 5 s $0.025.
- **8 GPUs for one H3 job** (Ulysses-8) gives ≈ the same GPU-seconds per clip (8×H200 39.7 s ≈ 317 GPU-s versus 4×H200 75 s = 300 GPU-s). It lowers latency, not cost.

### 4.3 Open tier (Standard jobs), $/output-s, base price and wall time

| Profile | Res | RTX 4090 | RTX 5090 | RTX PRO 6000 | H100 | Customer |
|---|---|---|---|---|---|---|
| ltx-2.5-fast 5 s | 720p @60% (@85%) | 0.0025 (0.0018) | 0.0027 (0.0019) | 0.0037 (0.0026) | 0.0048 (0.0034) | 0.024 |
| ltx-2.5-fast 5 s | 1080p @60% | 0.0044 | 0.0047 | 0.0064 | 0.0084 | 0.04 |
| ltx-2.5-fast 10 s | 1080p @60% | 0.0050 | 0.0053 | 0.0074 | 0.0096 | 0.04 |
| ltx-2.5-pro 5 s | 720p @60% | – | – | 0.0120 | 0.0156 | 0.04 |
| ltx-2.5-pro 5 s | 1080p @60% | – | – | 0.0276 | 0.0360 | 0.07 |

- **Consumer cards are cheapest per second, but slow.** A 4090 takes 80 s base (30–267 s range) for 5 s of 720p and 140 s for 1080p, and a 5090 44 s / 78 s. The high case is 3–8× the base, so the per-second advantage is fragile.
- **Wall time is a latency SLA problem for Standard jobs.**

### 4.4 Platform costs per clip

**Cloudflare R2** [C]:
- Standard storage $0.015/GB-month; Infrequent Access $0.01 plus $0.01/GB retrieval with a 30-day minimum.
- Class A operations $4.50/M; Class B $0.36/M; **egress free**; free tier 10 GB-month.
- PADMÉ padding adds at most 3.1% (PROTOCOL.md) [C].
- MP4 sizes are estimated at ~7–12 Mbps for 720p–1080p and ~40 Mbps for 4K [E].

| Clip | Size | $/year | 10 years | Kept forever (perpetuity at 5%) |
|---|---|---|---|---|
| LTX 720p 5 s | ≈6 MB | $0.0011 | $0.011 | $0.022 |
| LTX 1080p 10 s | ≈24 MB | $0.0044 | $0.044 | $0.087 |
| LTX 2160p 10 s | ≈100 MB | $0.018 | $0.18 | $0.36 |
| H3 768p 5 s / 14 s | 5 / 14 MB | $0.0009 / $0.0025 | – | $0.018 / $0.051 |

- Writes are ≈$0.00002 per job (4 PUTs). Reads cost $0.00000036 per view.
- Inputs (reference images and videos) add similar amounts.
- **Storage is under 1% of price, except 4K kept forever (≈$0.36 against a $2 clip, 18%).** Offer a retention default, or move older clips to Infrequent Access.

**Payment fees on a top-up** (the card is charged once; credit is spent across many clips):

| Top-up | Stripe US card (2.9% + $0.30) [C] | + international card (1.5%) + currency conversion (1%) [C] | NOWPayments (0.5–1.5% + network fee; $1 assumed [U]) |
|---|---|---|---|
| $5 (`KUNO_TOPUP_MIN_USD` default) | $0.445 = **8.9%** | 11.4% | – |
| $10 | 5.9% | 8.4% | – |
| $20 (`KUNO_NOWPAYMENTS_MIN_USD`) | 4.4% | 6.9% | 5.5–6.5% |
| $50 | 3.5% | 6.0% | 2.5–3.5% |
| $100 | 3.2% | 5.7% | 1.5–2.5% |

- **NOWPayments service fee sources conflict:** the blog says 0.5% for single-currency and 1% for multi-currency payments; the help center says 1% without exchange and 1.5% for multi-currency, fixed-rate or fee-paid-by-user payments. KunoWorld's invoices are fixed-rate, so budget **1.5% plus the network fee** [C both pages].
- Stripe stablecoin payments are 1.5% [C]; ACH is 0.8%, capped at $5 [C].
- TAO transfers cost only chain fees, but **alpha top-ups carry `KUNO_ALPHA_HAIRCUT` = 10%**, which is effectively a 10% fee to the customer [C PAYMENTS.md].
- Refunds and disputes are extra: Stripe keeps the fee, and a dispute costs $15 [U, standard Stripe].
- **Implication:** budget ≈5% of revenue for payments at a $10–20 average top-up, 9% at $5. Raise the card minimum to $10, or add a $0.30 small-top-up surcharge.

---

## 5. Emission subsidy

**Inputs:**
- **TAO price:** $232.45 on 2026-09-14, 24 h −1.2%, 7-day range $229.94–269.72 [C CoinGecko]. It was $268.03 on Sep 7 [S].
- **Total emission:** 0.5 TAO/block ≈ 3,600 TAO/day ≈ **$837k/day**.
- **Split inside a subnet:** 18% owner / 41% miners / 41% validators [C].

**Emission rules since June 22 2026** (research_bittensor.md §1.4, §3.2) [C code]:
- Each subnet's share is its moving price divided by the sum of moving prices, where spot is capped at 1.0 before entering the EMA.
- The EMA's smoothing is age-dependent: `ema_alpha = base × blocks / (blocks + 201,600)`, so **a new subnet's moving price starts near zero and adapts over months**.
- The share is multiplied by **(1 − MinerBurned)**. Recycling instead of burning does not avoid this.
- A **Hill gate** then applies: θ is the 32nd-largest share and the exponent is 3, so subnets below about rank 32 collapse toward zero.
- New subnets register with **emission disabled** until root turns it on.

**Two ways to value the miners' share:**
- **TAO-backed:** 41% × the TAO injected per day. This is what miners can sustainably extract if nobody else buys alpha.
- **Mark-to-market (MTM):** 41% × 7,200 alpha/day × spot or EMA price × TAO/USD. This is what KunoWorld's USD-mode `pool_usd` uses (spot `current_alpha_price`).

Snapshot at block 9,045,154 (≈2026-09-10), from research_bittensor.md:

| Rank (netuid) | EMA price (TAO/α) | TAO/day to subnet | Miners TAO-backed $/day | → GPU-h/day at H200 $3.20 (GPUs 24/7) | at owned H200 $2.05 | Miners MTM $/day | → GPU-h/day at $3.20 |
|---|---|---|---|---|---|---|---|
| 32 (SN118), at the gate | 0.0083 | 20.8 | **$1,982** | 619 (26) | 967 (40) | $5,695 | 1,780 (74) |
| 35 (SN105), just below | 0.0059 | 7.7 | **$734** | 229 (9.6) | 358 (15) | $4,049 | 1,265 (53) |
| 50 (SN26) | 0.0035 | 1.2 | **$114** | 36 (1.5) | 56 (2.3) | $2,402 | 751 (31) |
| 60 (SN1, high burn) | 0.0071 | 0.5 | **$48** | 15 (0.6) | 23 (1.0) | (burned) | – |
| Median subnet | 0.00445 | – | – | – | – | $3,054 | 954 (40) |

- **SN90** shows the burn penalty: its EMA price of 0.0317 would rank it near the top 7, but with MinerBurned 0.766 it falls to rank 34 and 15.5 TAO/day.
- **In H3 terms**, one 8× H200 server uses 192 GPU-h/day. Rank 32 funds ≈3 H3 servers or ≈26 LTX GPUs from TAO-backed emission; rank 50 funds none.
- **In job terms**, $1,982/day pays ≈200k `ltx-2.5-fast` 1080p seconds or ≈13k `h3` seconds at the rates recommended in §8.
- **For KunoWorld at launch:**
  - Emission is off until root enables it, and the moving price starts near zero, so **the TAO-backed subsidy is ≈0 for the first 1–3 months [E]**.
  - Alpha still pays out, and the pool starts at the median alpha price (~0.0045 TAO), so MTM starts ≈$3k/day. Miners selling it with no TAO inflow will push the price down.
  - USD mode values the pool at spot, so `subsidy_ratio` will look healthier than the TAO backing.
  - **Never burn the residual** (`KUNO_PAY_RESIDUAL=renormalize` is right; `recycle` would cut the TAO share by (1 − burned) and can drop the subnet under the gate).

---

## 6. Checking the current placeholders

### 6.1 `PLACEHOLDER_USD_PER_VCU_SECOND` = 0.01, open share 0.5

| Profile | Miner confidential $/s | Miner open $/s | Customer $/s | Miner ÷ customer |
|---|---|---|---|---|
| ltx-2.5-fast (VCU 5) | 0.05 | 0.025 | 0.024 / 0.04 | **1.25–2.1×** |
| ltx-2.5-pro (15) | 0.15 | 0.075 | 0.04 / 0.07 | **2.1–3.75×** |
| ltx-2.5-4k (40) | 0.40 | – | 0.12 / 0.20 | **2–3.3×** |
| h3-turbo (16) | 0.16 | – | 0.06 | **2.7×** |
| h3 (60) | 0.60 | – | 0.12 | **5×** |
| h3-reference (64) | 0.64 | – | 0.10 | **6.4×** |

**Implied miner pay per GPU-hour** (base wall times; output seconds per GPU-hour = 3600 ÷ GPU-s per output second):

| Case | Output s per GPU-h | @100% | @60% | @30% |
|---|---|---|---|---|
| ltx-2.5-fast 720p on RTX PRO 6000 BSE | 765 | $38.2 | $22.9 | $11.5 |
| ltx-2.5-fast 720p on H200 | 990 | $49.5 | $29.7 | $14.9 |
| ltx-2.5-fast 720p on B300 | 2,430 | $121.5 | $72.9 | $36.4 |
| ltx-2.5-fast 1080p on H200 | 566 | $28.3 | $17.0 | $8.5 |
| ltx-2.5-pro 1080p on H200 / B200 | 132 / 300 | $19.8 / $45.0 | $11.9 / $27.0 | $5.9 / $13.5 |
| ltx-2.5-4k 2160p on H200 / B200 | 45 / 102 | $18.0 / $40.9 | $10.8 / $24.5 | $5.4 / $12.3 |
| h3-turbo 5 s on 4× H200 / B300 | 205 / 375 | $32.7 / $60.0 | $19.6 / $36.0 | $9.8 / $18.0 |
| h3 5 s / 14 s on 4× H200 | 60 / 38 | $36.0 / $22.6 | $21.6 / $13.5 | $10.8 / $6.8 |
| h3-reference 5 s / 14 s on 4× H200 | 40 / 25 | $25.7 / $16.1 | $15.4 / $9.7 | $7.7 / $4.8 |
| Open tier: ltx-2.5-fast 720p on RTX 4090 / 5090 / H100 | 225 / 405 / 900 | $5.6 / $10.1 / $22.5 | $3.4 / $6.1 / $13.5 | – |

The placeholders pay **$10–73/GPU-h at 60% utilization**, against confidential rental costs of $1.8–5.6/GPU-h and Targon's $2–9.75. They are also uneven: faster hardware earns proportionally more, which is fine, but 720p earns 1.75× more per GPU-hour than 1080p on the same card.

### 6.2 VCU weights versus GPU-seconds

Reference: 1× H200 for LTX, 4× H200 for H3; base wall times.

| Profile | Res / duration | GPU-s per output s | Current VCU | GPU-s ÷ VCU |
|---|---|---|---|---|
| ltx-2.5-fast | 720p | 3.6 | 5 | 0.73 |
| ltx-2.5-fast | 1080p 5 s / 10 s | 6.4 / 7.3 | 5 | 1.27 / 1.45 |
| ltx-2.5-pro | 720p | 11.8 | 15 | 0.79 |
| ltx-2.5-pro | 1080p | 27.3 / 29.1 | 15 | 1.82 / 1.94 |
| ltx-2.5-4k | 1440p | 30 | 40 | 0.75 |
| ltx-2.5-4k | 2160p | 80 (range 38–170) | 40 | 2.0 (0.9–4.3) |
| h3-turbo | 5 / 10 / 14 s | 17.6 / 20.0 / 24.3 | 16 | 1.10 / 1.25 / 1.52 |
| h3 | 5 / 10 / 14 s | 60 / 80 / 96 | 60 | **1.00** / 1.33 / 1.60 |
| h3-reference | 5 / 10 / 14 s | 90 / 120 / 143 | 64 | 1.40 / 1.88 / 2.23 |

**Verdict:** the weights are proportional within ±30% only at the cheapest resolution and 5 s. Across the whole range they are off by up to 2–4×, because a single weight per profile cannot capture resolution, duration, fps or references.

### 6.3 `PLACEHOLDER_USD_PER_GPU_HOUR` = 2.0

- $2.00 is **above** owned TCO for an RTX PRO 6000 Server Edition ($0.95) and about equal to an owned H200 ($2.05). An owner of idle confidential PRO 6000s profits from capacity pay alone; this is only limited by `capacity_targets`.
- It is below rented H200/B200/B300 cost ($3.2–5.6), so it does not keep a rented H3 server alive by itself, which is correct.
- **It should differ by family** (§8.3).

### 6.4 Customer placeholder prices

Compared with confidential base cost at 60% utilization:
- **Healthy:** `ltx-2.5-fast` (3.5–7×), `ltx-2.5-4k` 1440p (2.6–4×).
- **Thin:** `ltx-2.5-pro` 720p (2.2–3.5×), `ltx-2.5-pro` 1080p (1.7–2.7×), `h3-turbo` (1.5–2.6×).
- **Uncertain, possibly under cost:** `ltx-2.5-4k` 2160p (1.6–2.6× base; 0.4× at the high estimate).
- **Under cost:** `h3` (0.8–1.5×) and `h3-reference` (0.45–0.8×).
- **Market references:**
  - fal (LTX-2.5): Fast $0.09 / $0.13 / $0.19 / $0.30 per second at 720p / 1080p / 1440p / 4K; Pro $0.12 / $0.17 [C fal.ai/ltx-2.5].
  - MiniMax API: H3 768p $0.09/s (beta) [S]; OpenRouter lists H3 at $0.13/s [S].

---

## 7. Updates to existing notes

**research_market.md §A3:**
- **GPU rental table.** RunPod is unchanged. Add:
  - RunPod RTX PRO 6000 $1.69 / $2.09 and B300 $6.94 / $7.89 [C];
  - Lium, Vast, Nebius, CoreWeave, Crusoe, Together, Hyperbolic, the Chutes rate table, GCP and AWS (§1.1).
- **Wrong AWS figure.** "AWS H100 ≈ $3.90" is wrong for on-demand: p5 is **$6.88/GPU-h**, p5en H200 $7.91, p6-b200 $14.24 and p6-b300 $17.80 [S]. $3.90 may be an old Capacity Block price.
- **GCP H200** is still ≈$10.62 [S].
- **RTX PRO 6000 CC.** The "[U] some RTX PRO Blackwell server SKUs may support CC" line is now confirmed for single-GPU RTX PRO 6000 Server Edition (research_tee, R595) [C].
- **Azure NCC** is unchanged at $8.90. Add the non-CC NC40ads at $6.98, a +27.5% premium [S].
- **CC overhead.** Add the Blackwell study: 1–3% well-configured, 30–40% misconfigured [C]. There is still no diffusion benchmark.
- **Generation speed and unit economics.** The Wan 2.2 rows are superseded by §3–4. The old "distilled TEE clip ≈ $0.04–0.08 per 5 s 720p" (Wan on Phala H100) compares with **$0.018–0.029 per 5 s 720p `ltx-2.5-fast` clip** at 60% on rented confidential hardware ($0.0035–0.0057/s × 5 s), about half. A 50-step `h3` 5 s clip is **$0.40–0.47** on the same basis.
- **Owned TCO and bare-metal leases:** add §1.3–1.4.

**research_models.md and research_model_capabilities.md:**
- **H3 "~74 s on 4×H200"** is confirmed; it is 74.4 s with warmup and 84.1 s without [C].
- **"~18 s on 8×B300 FP8"** is confirmed: 18.03 s fp8, 19.04 s bf16 [C].
- **Add:**
  - LMSYS 8×H200 lossless 39.67 s (5 s) and 112.44 s (10 s);
  - Ref2VA/FL2VA = 1.53× on B300;
  - GB300 4-GPU 33.1 s;
  - the 4×B300 dense per-evaluation times 0.94 / 2.46 / 4.61 s at 124 / 243 / 362 frames;
  - load 114–118 s.
- **The 4×H100 "13.25 s"** remains [U].
- **LTX "6.8 s on 2×GB200"** is for **10 s 720p I2V** [S], and the API figure is 23.7 s at 1080p.
- **Add the first H100 CI measurements:** LTX-2.5 at 768×448 × 57 frames E2E 11.0 s; LTX-2.3 load 44 s and 108 s [C].
- **Add** the RTX 5090 LTX-2.3 per-step and E2E data [C community] and FastVideo 4.55 s on B200 [S].
- **No H3 Turbo timings** have been published anywhere [C, absence].

---

## 8. What this means

### 8.1 Cost floors (confidential tier = rented, CC-capable, 60% utilization, base case; open = base)

$/verified output second. "Owned floor" is owned hardware at 85% utilization on the cheapest class, below which no miner can go.

| Profile | Res / duration | Confidential floor (best – median class) | Owned floor @85% | Open floor (4090 / 5090 – H100) |
|---|---|---|---|---|
| ltx-2.5-fast | 720p | 0.0035 – 0.0041 | 0.0007 | 0.0025 – 0.0048 |
| ltx-2.5-fast | 1080p 5–10 s | 0.0061 – 0.0082 | 0.0013 | 0.0044 – 0.0096 |
| ltx-2.5-pro | 720p | 0.0114 – 0.0141 | 0.0023 | 0.0120 (PRO 6000) – 0.0168 |
| ltx-2.5-pro | 1080p | 0.026 – 0.032 | 0.0057 | 0.028 – 0.038 |
| ltx-2.5-4k | 1440p | 0.029 – 0.033 | 0.0053 | n/a |
| ltx-2.5-4k | 2160p | 0.077 – 0.094 (high case up to 0.48) | 0.010 | n/a |
| h3-turbo | 5 / 10 / 14 s | 0.023 / 0.029 / 0.034 – 0.026 / 0.031 / 0.038 | 0.007 / 0.009 / 0.010 | n/a |
| h3 | 5 / 10 / 14 s | 0.081 / 0.103 / 0.129 – 0.092 / 0.117 / 0.145 | 0.025 / 0.033 / 0.040 | n/a |
| h3-reference | 5 / 10 / 14 s | 0.121 / 0.154 / 0.193 – 0.137 / 0.174 / 0.218 | 0.025 / 0.033 / 0.040 | n/a |

### 8.2 Recommended miner rates, USD per verified second

**Rule:** median eligible confidential class, base price, base wall time, 5% CC overhead, at 60% utilization, × 1.25.

Margin at these rates:

| Utilization | Margin |
|---|---|
| 60% | +25% |
| 85% | +77% |
| 40% | −17% |
| 30% | −37% (capacity pay closes this, §8.3) |

**Confidential tier:**

| Profile | Recommended (by resolution / duration) | Single value if the card stays one rate per profile | Placeholder today |
|---|---|---|---|
| ltx-2.5-fast | 720p **$0.005**; 1080p **$0.010** | $0.008 | $0.05 |
| ltx-2.5-pro | 720p **$0.017**; 1080p **$0.040** | $0.035 (assumes mostly 1080p) | $0.15 |
| ltx-2.5-4k | 1440p **$0.042**; 2160p **$0.12** (provisional, measure first) | $0.09 | $0.40 |
| h3-turbo | 5 s **$0.033**; 10 s $0.039; 14 s $0.047 | $0.040 | $0.16 |
| h3 | 5 s **$0.11**; 10 s $0.15; 14 s $0.18 | $0.15 | $0.60 |
| h3-reference | 5 s **$0.17**; 10 s $0.22; 14 s $0.27 (provisional) | $0.22 | $0.64 |

**Open tier** (no capacity pay, elastic supply). Recommended **≈0.75× confidential**, not 0.5×:

| Profile | 720p | 1080p |
|---|---|---|
| ltx-2.5-fast | $0.004 | $0.0075 |
| ltx-2.5-pro | $0.012 | $0.030 |

- At 0.5×, only RTX 4090/5090 break even (at 60% utilization), and H100 and RTX PRO 6000 open miners lose money at 1080p.
- If the owner wants a steeper privacy premium, 0.6× still works for consumer cards at ≥60% and for RTX PRO 6000 at ≥85%.

**Rate-card shape and customer prices:**
1. **Extend the card with a resolution key** (profile → tier → resolution) and **an fps multiplier** (48/50 fps ≈ 2×).
2. For H3, add a **duration factor of about 1 + 0.045 × (d − 5)** (`h3-turbo`: 1 + 0.032 × (d − 5)). Otherwise one rate per profile overpays 720p and 5 s jobs and underpays 1080p, 14 s and 50 fps jobs.
3. **Customer prices must rise for H3.** Keep miner rates at or below ~60% of customer price, leaving ≈5% for payments and the rest for gateway and validators:

| Profile | Customer price today | Suggested customer price |
|---|---|---|
| h3-turbo | $0.06 | ≥ $0.08 |
| h3 | $0.12 | ≥ $0.22 (market MiniMax API ≈ $0.09–0.13, so steer users to Turbo) |
| h3-reference | $0.10 | ≥ $0.35 |
| ltx-2.5-pro 720p / 1080p | $0.04 / $0.07 | $0.05 / $0.09 (fal Pro is $0.12 / $0.17) |
| ltx-2.5-4k 2160p | $0.20 | $0.30 (the same as fal/LTX API 4K) until measured |
| ltx-2.5-fast | $0.024 / $0.04 | can stay |

### 8.3 Capacity pay: `gpu_hour_usd`

| Family | Recommended $/credited GPU-h | Why |
|---|---|---|
| `ltx-2.5` | **$0.80** | Below the owned RTX PRO 6000 BSE TCO ($0.95), so an idle GPU never profits by itself. It covers the 30%-utilization shortfall on a rented PRO 6000 (≈$0.70 at the recommended job rates, including 5% CC). |
| `minimax-h3` | **$1.50** | Below owned H200 TCO ($2.05). It covers the 30%-utilization shortfall on rented H200 and B200 servers (≈$1.30–1.40). B300 servers (shortfall ≈$2.20) need ≥40% utilization. |

**Rule:** `gpu_hour_usd` ≈ 0.35–0.45 × the rented base price of the family's reference class, and ≤ 0.85 × the lowest owned TCO in the family.

**Check against Targon** (competing TDX payouts: RTX PRO 6000 $2.00, H200 $3.56, B300 $9.75), with the recommended rates plus capacity pay:

| Class | Revenue per GPU-h at 30% utilization | at 60% | Targon |
|---|---|---|---|
| RTX PRO 6000 BSE | ≈$1.98 | ≈$3.16 | $2.00 |
| H200 (H3) | ≈$3.60 | ≈$5.70 | $3.56 |
| B300 (H3) | ≈$5.20 | ≈$8.85 | $9.75 (needs ≈70%) |

### 8.4 VCU weights proportional to GPU cost

Anchor: `h3` 5 s = 60, so 1 VCU ≈ $0.000915 of base confidential GPU cost per output second at 100% utilization.

| Profile | Proposed VCU per output second | Current |
|---|---|---|
| ltx-2.5-fast | 720p **3**; 1080p **5** | 5 |
| ltx-2.5-pro | 720p **9**; 1080p **20** | 15 |
| ltx-2.5-4k | 1440p **22**; 2160p **60** (range 25–250 until measured) | 40 |
| h3-turbo | 5 s **17**; 10 s 20; 14 s 25 | 16 |
| h3 | 5 s **60**; 10 s 76; 14 s 95 | 60 |
| h3-reference | 5 s **90**; 10 s 114; 14 s 143 (range 60–145 at 5 s) | 64 |
| Multipliers | 48/50 fps ×2 [E]; H3 duration factor as in §8.2 | none |

If VCUs must stay one per profile, weight them to the likely job mix: fast 4, pro 18, 4k 45, h3-turbo 20, h3 76, h3-reference 115.

With these weights, **$0.0019 per VCU-second** (= $0.000915 ÷ 0.6 × 1.25) reproduces the recommended confidential rates in §8.2 within ±5% on every row except 720p fast, which it pays +14% ($0.0057 against $0.005). That makes it the replacement for `PLACEHOLDER_USD_PER_VCU_SECOND` = 0.01, which is 5.3× too high.

### 8.5 Measure before signing (largest uncertainties, in order)

1. **`ltx-2.5-4k` 2160p** wall time and memory on H200/B200: 5× range.
2. **`h3-reference`** relative to `h3` on NVIDIA with real reference inputs: 1.0–1.6×.
3. **`ltx-2.5-pro` and `ltx-2.5-fast`** at 720p and 1080p, 5 s and 10 s, on RTX PRO 6000 BSE, H200 and B200: ±50%.
4. **`h3-turbo`** through the lightx2v / diffusers-modular runtime on 4× H200: 16–30 s.
5. **CC-mode overhead and cold-load time** in the actual TD shapes (c1, c2, c8), including LRU swaps.
6. **RTX 4090 and 5090 group-offload speed**: currently "unmeasured" in MINING.md.

---

## Appendix A: full per-row model output (`python3 costmodel.py`)

Columns: wall seconds low/base/high; GPU-seconds per output second at base; $/output-s at low@60%, base@30%, base@60%, base@85% and high@60%; customer $/s.

| Profile | Res | Dur s | Tier | Hardware | Wall s (L/B/H) | GPU-s per out-s | $/s low@60% | $/s base@30% | base@60% | base@85% | $/s high@60% | Customer $/s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ltx-2.5-fast | 720p | 5 | conf | RTX PRO 6000 BSE | 12/24/46 | 4.7 | 0.0011 | 0.0082 | 0.0041 | 0.0029 | 0.0122 | 0.024 |
| ltx-2.5-fast | 720p | 5 | conf | H200 | 10/18/32 | 3.6 | 0.0019 | 0.0113 | 0.0057 | 0.0040 | 0.0164 | 0.024 |
| ltx-2.5-fast | 720p | 5 | conf | B200 | 4/8/16 | 1.6 | 0.0010 | 0.0070 | 0.0035 | 0.0025 | 0.0116 | 0.024 |
| ltx-2.5-fast | 720p | 5 | conf | B300 | 4/7/15 | 1.5 | 0.0010 | 0.0081 | 0.0040 | 0.0028 | 0.0122 | 0.024 |
| ltx-2.5-fast | 720p | 5 | open | RTX 4090 | 30/80/267 | 16.0 | 0.0007 | 0.0050 | 0.0025 | 0.0018 | 0.0183 | 0.024 |
| ltx-2.5-fast | 720p | 5 | open | RTX 5090 | 17/44/128 | 8.9 | 0.0006 | 0.0053 | 0.0027 | 0.0019 | 0.0117 | 0.024 |
| ltx-2.5-fast | 720p | 5 | open | RTX PRO 6000 | 12/24/46 | 4.7 | 0.0012 | 0.0074 | 0.0037 | 0.0026 | 0.0093 | 0.024 |
| ltx-2.5-fast | 720p | 5 | open | H100 | 12/20/32 | 4.0 | 0.0017 | 0.0096 | 0.0048 | 0.0034 | 0.0097 | 0.024 |
| ltx-2.5-fast | 1080p | 5 | conf | RTX PRO 6000 BSE | 22/41/79 | 8.2 | 0.0020 | 0.0144 | 0.0072 | 0.0051 | 0.0209 | 0.04 |
| ltx-2.5-fast | 1080p | 5 | conf | H200 | 18/32/55 | 6.4 | 0.0035 | 0.0198 | 0.0099 | 0.0070 | 0.0281 | 0.04 |
| ltx-2.5-fast | 1080p | 5 | conf | B200 | 7/14/28 | 2.8 | 0.0018 | 0.0123 | 0.0061 | 0.0043 | 0.0199 | 0.04 |
| ltx-2.5-fast | 1080p | 5 | conf | B300 | 7/13/25 | 2.6 | 0.0019 | 0.0141 | 0.0071 | 0.0050 | 0.0210 | 0.04 |
| ltx-2.5-fast | 1080p | 5 | open | RTX 4090 | 55/140/458 | 28.0 | 0.0013 | 0.0088 | 0.0044 | 0.0031 | 0.0314 | 0.04 |
| ltx-2.5-fast | 1080p | 5 | open | RTX 5090 | 31/78/220 | 15.6 | 0.0012 | 0.0094 | 0.0047 | 0.0033 | 0.0202 | 0.04 |
| ltx-2.5-fast | 1080p | 5 | open | RTX PRO 6000 | 22/41/79 | 8.2 | 0.0022 | 0.0129 | 0.0064 | 0.0045 | 0.0160 | 0.04 |
| ltx-2.5-fast | 1080p | 5 | open | H100 | 22/35/55 | 7.0 | 0.0031 | 0.0168 | 0.0084 | 0.0059 | 0.0168 | 0.04 |
| ltx-2.5-fast | 1080p | 10 | conf | RTX PRO 6000 BSE | 50/94/186 | 9.4 | 0.0022 | 0.0165 | 0.0082 | 0.0058 | 0.0247 | 0.04 |
| ltx-2.5-fast | 1080p | 10 | conf | H200 | 42/73/130 | 7.3 | 0.0040 | 0.0226 | 0.0113 | 0.0080 | 0.0332 | 0.04 |
| ltx-2.5-fast | 1080p | 10 | conf | B200 | 17/32/65 | 3.2 | 0.0020 | 0.0140 | 0.0070 | 0.0049 | 0.0235 | 0.04 |
| ltx-2.5-fast | 1080p | 10 | conf | B300 | 16/30/59 | 3.0 | 0.0021 | 0.0161 | 0.0081 | 0.0057 | 0.0249 | 0.04 |
| ltx-2.5-fast | 1080p | 10 | open | RTX 4090 | 125/320/1083 | 32.0 | 0.0014 | 0.0101 | 0.0050 | 0.0036 | 0.0371 | 0.04 |
| ltx-2.5-fast | 1080p | 10 | open | RTX 5090 | 71/178/520 | 17.8 | 0.0013 | 0.0107 | 0.0053 | 0.0038 | 0.0238 | 0.04 |
| ltx-2.5-fast | 1080p | 10 | open | RTX PRO 6000 | 50/94/186 | 9.4 | 0.0025 | 0.0147 | 0.0074 | 0.0052 | 0.0189 | 0.04 |
| ltx-2.5-fast | 1080p | 10 | open | H100 | 50/80/130 | 8.0 | 0.0035 | 0.0192 | 0.0096 | 0.0068 | 0.0198 | 0.04 |
| ltx-2.5-pro | 720p | 5 | conf | H200 | 33/59/100 | 11.8 | 0.0065 | 0.0368 | 0.0184 | 0.0130 | 0.0511 | 0.04 |
| ltx-2.5-pro | 720p | 5 | conf | B200 | 13/26/50 | 5.2 | 0.0032 | 0.0228 | 0.0114 | 0.0080 | 0.0362 | 0.04 |
| ltx-2.5-pro | 720p | 5 | conf | B300 | 12/24/45 | 4.8 | 0.0034 | 0.0262 | 0.0131 | 0.0093 | 0.0382 | 0.04 |
| ltx-2.5-pro | 720p | 5 | open | RTX PRO 6000 | 40/76/143 | 15.3 | 0.0039 | 0.0239 | 0.0120 | 0.0084 | 0.0291 | 0.04 |
| ltx-2.5-pro | 720p | 5 | open | H100 | 40/65/100 | 13.0 | 0.0056 | 0.0312 | 0.0156 | 0.0110 | 0.0305 | 0.04 |
| ltx-2.5-pro | 1080p | 5 | conf | H200 | 83/136/220 | 27.3 | 0.0161 | 0.0848 | 0.0424 | 0.0299 | 0.112 | 0.07 |
| ltx-2.5-pro | 1080p | 5 | conf | B200 | 33/60/110 | 12.0 | 0.0081 | 0.0525 | 0.0263 | 0.0185 | 0.0796 | 0.07 |
| ltx-2.5-pro | 1080p | 5 | conf | B300 | 31/56/100 | 11.1 | 0.0086 | 0.0605 | 0.0302 | 0.0214 | 0.0841 | 0.07 |
| ltx-2.5-pro | 1080p | 5 | open | RTX PRO 6000 | 100/176/314 | 35.3 | 0.0098 | 0.0552 | 0.0276 | 0.0195 | 0.0640 | 0.07 |
| ltx-2.5-pro | 1080p | 5 | open | H100 | 100/150/220 | 30.0 | 0.0139 | 0.0719 | 0.0360 | 0.0254 | 0.0670 | 0.07 |
| ltx-2.5-pro | 1080p | 10 | conf | H200 | 175/291/480 | 29.1 | 0.0169 | 0.0905 | 0.0453 | 0.0319 | 0.123 | 0.07 |
| ltx-2.5-pro | 1080p | 10 | conf | B200 | 70/128/240 | 12.8 | 0.0085 | 0.0560 | 0.0280 | 0.0198 | 0.0869 | 0.07 |
| ltx-2.5-pro | 1080p | 10 | conf | B300 | 66/119/218 | 11.9 | 0.0090 | 0.0645 | 0.0323 | 0.0228 | 0.0918 | 0.07 |
| ltx-2.5-4k | 1440p | 5 | conf | H200 | 78/150/264 | 30.0 | 0.0151 | 0.0933 | 0.0467 | 0.0329 | 0.135 | 0.12 |
| ltx-2.5-4k | 1440p | 5 | conf | B200 | 31/66/132 | 13.2 | 0.0076 | 0.0578 | 0.0289 | 0.0204 | 0.0956 | 0.12 |
| ltx-2.5-4k | 1440p | 5 | conf | B300 | 29/61/120 | 12.2 | 0.0080 | 0.0665 | 0.0333 | 0.0235 | 0.101 | 0.12 |
| ltx-2.5-4k | 2160p | 5 | conf | H200 | 147/400/935 | 80.0 | 0.0284 | 0.249 | 0.124 | 0.0878 | 0.478 | 0.2 |
| ltx-2.5-4k | 2160p | 5 | conf | B200 | 59/176/468 | 35.2 | 0.0142 | 0.154 | 0.0770 | 0.0544 | 0.339 | 0.2 |
| ltx-2.5-4k | 2160p | 5 | conf | B300 | 55/163/425 | 32.6 | 0.0151 | 0.177 | 0.0887 | 0.0626 | 0.358 | 0.2 |
| ltx-2.5-4k | 2160p | 10 | conf | H200 | 312/850/1980 | 85.0 | 0.0302 | 0.264 | 0.132 | 0.0933 | 0.506 | 0.2 |
| ltx-2.5-4k | 2160p | 10 | conf | B200 | 125/374/990 | 37.4 | 0.0151 | 0.164 | 0.0818 | 0.0578 | 0.358 | 0.2 |
| ltx-2.5-4k | 2160p | 10 | conf | B300 | 117/346/900 | 34.6 | 0.0161 | 0.189 | 0.0943 | 0.0665 | 0.379 | 0.2 |
| h3-turbo | 768p | 5 | conf | H200 x4 | 16/22/30 | 17.6 | 0.0124 | 0.0548 | 0.0274 | 0.0193 | 0.0613 | 0.06 |
| h3-turbo | 768p | 5 | conf | B200 x4 | 10/13/18 | 10.4 | 0.0097 | 0.0455 | 0.0228 | 0.0161 | 0.0521 | 0.06 |
| h3-turbo | 768p | 5 | conf | B300 x4 | 9/12/16 | 9.6 | 0.0099 | 0.0523 | 0.0261 | 0.0184 | 0.0538 | 0.06 |
| h3-turbo | 768p | 10 | conf | H200 x4 | 38/50/65 | 20.0 | 0.0147 | 0.0622 | 0.0311 | 0.0220 | 0.0664 | 0.06 |
| h3-turbo | 768p | 10 | conf | B200 x4 | 25/33/45 | 13.2 | 0.0121 | 0.0578 | 0.0289 | 0.0204 | 0.0652 | 0.06 |
| h3-turbo | 768p | 10 | conf | B300 x4 | 23/30/41 | 12.0 | 0.0126 | 0.0653 | 0.0327 | 0.0231 | 0.0690 | 0.06 |
| h3-turbo | 768p | 14 | conf | H200 x4 | 63/85/111 | 24.3 | 0.0174 | 0.0756 | 0.0378 | 0.0267 | 0.0810 | 0.06 |
| h3-turbo | 768p | 14 | conf | B200 x4 | 42/55/78 | 15.7 | 0.0146 | 0.0688 | 0.0344 | 0.0243 | 0.0807 | 0.06 |
| h3-turbo | 768p | 14 | conf | B300 x4 | 38/50/71 | 14.3 | 0.0149 | 0.0778 | 0.0389 | 0.0275 | 0.0853 | 0.06 |
| h3 | 768p | 5 | conf | H200 x4 | 70/75/85 | 60.0 | 0.0542 | 0.187 | 0.0933 | 0.0659 | 0.174 | 0.12 |
| h3 | 768p | 5 | conf | B200 x4 | 36/46/55 | 36.8 | 0.0350 | 0.161 | 0.0805 | 0.0568 | 0.159 | 0.12 |
| h3 | 768p | 5 | conf | B300 x4 | 33/42/50 | 33.6 | 0.0363 | 0.183 | 0.0915 | 0.0646 | 0.168 | 0.12 |
| h3 | 768p | 10 | conf | H200 x4 | 185/200/230 | 80.0 | 0.0716 | 0.249 | 0.124 | 0.0878 | 0.235 | 0.12 |
| h3 | 768p | 10 | conf | B200 x4 | 97/118/143 | 47.2 | 0.0471 | 0.207 | 0.103 | 0.0729 | 0.207 | 0.12 |
| h3 | 768p | 10 | conf | B300 x4 | 88/107/130 | 42.8 | 0.0484 | 0.233 | 0.117 | 0.0822 | 0.219 | 0.12 |
| h3 | 768p | 14 | conf | H200 x4 | 300/335/380 | 95.7 | 0.0830 | 0.298 | 0.149 | 0.105 | 0.277 | 0.12 |
| h3 | 768p | 14 | conf | B200 x4 | 165/206/248 | 58.9 | 0.0572 | 0.258 | 0.129 | 0.0909 | 0.257 | 0.12 |
| h3 | 768p | 14 | conf | B300 x4 | 150/187/225 | 53.4 | 0.0589 | 0.291 | 0.145 | 0.103 | 0.270 | 0.12 |
| h3-reference | 768p | 5 | conf | H200 x4 | 70/112/135 | 89.6 | 0.0542 | 0.279 | 0.139 | 0.0984 | 0.276 | 0.1 |
| h3-reference | 768p | 5 | conf | B200 x4 | 36/69/88 | 55.2 | 0.0350 | 0.242 | 0.121 | 0.0852 | 0.255 | 0.1 |
| h3-reference | 768p | 5 | conf | B300 x4 | 33/63/80 | 50.4 | 0.0363 | 0.274 | 0.137 | 0.0968 | 0.269 | 0.1 |
| h3-reference | 768p | 10 | conf | H200 x4 | 185/300/370 | 120.0 | 0.0716 | 0.373 | 0.187 | 0.132 | 0.378 | 0.1 |
| h3-reference | 768p | 10 | conf | B200 x4 | 97/176/229 | 70.4 | 0.0471 | 0.308 | 0.154 | 0.109 | 0.332 | 0.1 |
| h3-reference | 768p | 10 | conf | B300 x4 | 88/160/208 | 64.0 | 0.0484 | 0.348 | 0.174 | 0.123 | 0.350 | 0.1 |
| h3-reference | 768p | 14 | conf | H200 x4 | 300/500/610 | 142.9 | 0.0830 | 0.444 | 0.222 | 0.157 | 0.445 | 0.1 |
| h3-reference | 768p | 14 | conf | B200 x4 | 165/308/396 | 88.0 | 0.0572 | 0.385 | 0.193 | 0.136 | 0.410 | 0.1 |
| h3-reference | 768p | 14 | conf | B300 x4 | 150/280/360 | 80.0 | 0.0589 | 0.436 | 0.218 | 0.154 | 0.433 | 0.1 |

(720p 10 s LTX rows equal the 5 s rows per second, because the model scales 720p linearly, and are omitted here. Pro 720p 10 s is 5–8% above 5 s.)

---

## Sources

**GPU prices** (fetched 2026-09-13/14 unless noted):
- RunPod [runpod.io/pricing](https://www.runpod.io/pricing) (page updated 2026-09-13)
- Lambda [lambda.ai/pricing](https://lambda.ai/pricing)
- Nebius [nebius.com/prices](https://nebius.com/prices)
- CoreWeave [coreweave.com/pricing](https://www.coreweave.com/pricing)
- Crusoe [crusoe.ai/cloud/pricing](https://www.crusoe.ai/cloud/pricing)
- Together [together.ai/pricing](https://www.together.ai/pricing)
- Hyperbolic [hyperbolic.ai/marketplace](https://www.hyperbolic.ai/marketplace)
- Chutes rate table [api.chutes.ai/nodes/supported](https://api.chutes.ai/nodes/supported)
- Targon payouts [stats.targon.com/api/miners](https://stats.targon.com/api/miners)
- GetDeploying: [H100](https://getdeploying.com/gpus/nvidia-h100), [H200](https://getdeploying.com/gpus/nvidia-h200), [B200](https://getdeploying.com/gpus/nvidia-b200), [B300](https://getdeploying.com/gpus/nvidia-b300), [RTX PRO 6000](https://getdeploying.com/gpus/nvidia-rtx-pro-6000), [RTX 5090](https://getdeploying.com/gpus/nvidia-rtx-5090), [RTX 4090](https://getdeploying.com/gpus/nvidia-rtx-4090), [Lium](https://getdeploying.com/lium), [price index](https://getdeploying.com/gpu-price-index)
- IntuitionLabs [data-center GPU pricing 2026](https://intuitionlabs.ai/articles/data-center-gpu-pricing-2026) (2026-07-20)
- Thunder Compute [GCP GPU instances](https://www.thundercompute.com/blog/google-cloud-gpu-instances) and [RTX PRO 6000 pricing](https://www.thundercompute.com/blog/nvidia-rtx-pro-6000-pricing) (2026-09-11)
- AWS via [Vantage p6-b200](https://instances.vantage.sh/aws/ec2/p6-b200.48xlarge) and [p6-b300](https://instances.vantage.sh/aws/ec2/p6-b300.48xlarge); Capacity Blocks via [tech-insider](https://tech-insider.org/aws-ec2-capacity-blocks-price-hike-2026/)
- Vast [vast.ai/pricing](https://vast.ai/pricing) (live page; figures via GetDeploying)

**Confidential computing:**
- Phala [phala.com/gpu-tee](https://phala.com/gpu-tee)
- Azure [Vantage NCC40ads H100 v5](https://instances.vantage.sh/azure/vm/ncc40adsh100-v5) and [NC40ads H100 v5](https://instances.vantage.sh/azure/vm/nc40adsh100-v5)
- [GCP Confidential VM pricing](https://cloud.google.com/confidential-computing/confidential-vm/pricing) (snippet)
- [VoltageGPU comparison](https://voltagegpu.com/compare/gpu-cloud-pricing)
- [OpenMetal H200 TDX](https://openmetal.io/resources/hardware-details/gpu-server-h200/)
- [Corvex B200 CC](https://www.corvex.ai/blog/confidential-computing-meets-nvidia-hgxtm-b200-secure-ai-without-the-performance-trade-off)
- arXiv [2608.26575](https://arxiv.org/abs/2608.26575), [2607.19353](https://arxiv.org/abs/2607.19353), [2409.03992](https://arxiv.org/pdf/2409.03992); 2606.23969 via research_tee.md

**Hardware purchase and colocation:**
- Mercatus [H200 server](https://www.mercatus-ai.com/blog/h200-server-price) and [B200 server](https://www.mercatus-ai.com/blog/b200-server-price)
- B300: [tech-insider Blackwell pricing](https://tech-insider.org/nvidia-blackwell-gpu-pricing/) and [GPUSmith DGX B300](https://gpusmith.com/articles/en/nvidia-dgx-b300-price) (search snippets)
- [vrlatech 8-GPU Blackwell facility requirements](https://vrlatech.com/8-gpu-blackwell-server-facility-requirements/)
- Colocation: [Encor Advisors](https://encoradvisors.com/data-center-colocation-pricing/), [cologpu](https://cologpu.com/blog/colocation-pricing-2026) (snippets incl. CBRE)
- [gpuaas H200 SXM](https://gpuaas.com/blog/h200-sxm-spec-pricing-rent-2026) (snippet)

**Speed:**
- [LMSYS MiniMax-H3 on 8×H200](https://www.lmsys.org/blog/2026-08-27-minimax-h3-h200/) (2026-08-27)
- [SGLang MiniMax-H3 cookbook](https://github.com/sgl-project/sglang/blob/main/docs/cookbook/diffusion/MiniMax/MiniMax-H3.mdx)
- [SGLang LTX2.5 cookbook](https://github.com/sgl-project/sglang/blob/main/docs/cookbook/diffusion/LTX/LTX2.5.mdx)
- [sglang PR #39206](https://github.com/sgl-project/sglang/pull/39206) (CI baselines)
- [witcheer RTX 5090 LTX-2.3](https://huggingface.co/datasets/witcheer/rtx-5090-benchmarks/blob/main/reports/ltx-2.3.md)
- [runaihome LTX-2.5 guide](https://runaihome.com/blog/ltx-2-5-local-ai-video-hardware-guide-2026/)
- [note.com RTX 5090 LTX-2.5](https://note.com/truenorthai/n/nf600b6190507)
- [VentureBeat LTX-2.5](https://venturebeat.com/technology/ltx-2-5-can-generate-a-10-second-ai-video-from-an-image-in-just-6-8-seconds-on-nvidia-superchips-and-its-open-weights) (2026-08-11)
- [Runpod LTX-2.5 blog](https://www.runpod.io/blog/ltx-2-5-the-open-weights-world-model-built-for-speed-and-how-to-run-it-on-runpod)
- [FastVideo 1080p on B200](https://haoailab.com/blogs/fastvideo_realtime_1080p/) (2026-03-11)
- [LTX-2 optimization.md](https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-pipelines/docs/optimization.md)
- [ModelTC Minimax-H3-Turbo](https://github.com/ModelTC/Minimax-H3-Turbo) and [lightx2v/Minimax-h3-Turbo](https://huggingface.co/lightx2v/Minimax-h3-Turbo) (no timings)

**Platform, market and chain:**
- [fal LTX-2.5](https://fal.ai/ltx-2.5)
- [Cloudflare R2 pricing](https://developers.cloudflare.com/r2/pricing/)
- [Stripe pricing](https://stripe.com/pricing)
- NOWPayments [help center fees](https://nowpayments.io/help/about-nowpayments/about/what-are-your-fees) and [blog comparison](https://nowpayments.io/blog/nowpayments-vs-coinpayments)
- [CoinGecko TAO](https://www.coingecko.com/en/coins/bittensor) (2026-09-14)
- Chain emission snapshot and rules: `/video/research/research_bittensor.md` §1.3–1.4, §2, §3.2
- Repo: `profiles.json`, `rate_card.py`, `shapes.json`, `MINING.md`, `VALIDATING.md` (USD mode, capacity pay), `PROTOCOL.md` (PADMÉ), `/video/platform/gateway/PAYMENTS.md` (top-up limits, alpha haircut)
