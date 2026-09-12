# TEE / Confidential-Compute / Verifiable-Inference Subnets on Bittensor (as of 2026-09-11)

Research for designing a **TEE-secured video-generation inference subnet**.
Chutes SN64 is covered elsewhere and appears here only for comparison.

**Legend**
- **[CONFIRMED-CODE]**: I read it in the subnet's public source code or repo docs (raw.githubusercontent.com / GitHub API) on 2026-09-11.
- **[CONFIRMED-DOC]**: stated in the team's own docs, whitepaper or release page.
- **[3RD-PARTY]**: from analyst, aggregator or news sites (tao.media, ownyourmind.ai, SubnetRadar, Subnet Alpha, KuCoin community posts). Not independently verified.
- **[UNVERIFIED]** / **[MY INFERENCE]**: conflicting or unconfirmable claims, or my own interpretation.

---

## 0. What subnets 28, 90 and 53 actually are (the user's names were approximate)

| User's name | Actual subnet (Sept 2026) | Operator | Repo | Is it TEE? |
|---|---|---|---|---|
| "GM sn28" | **SN28 "gm" / sayGM**, a confidential **LLM-API resale marketplace** (saygm.com). Previously the SN28 S&P 500 price-oracle subnet. | GitHub org **`taostat`** (the Taostats team), which also runs SN19 BlockMachine. Subnet Alpha instead says "Foundry Accelerate" **[conflict, see §1]** | https://github.com/taostat/gm-miner, https://github.com/taostat/gm-validator, https://github.com/taostat/gm-mcp | Yes. Miner workers are Intel TDX CVMs on **Phala Cloud (dstack)**. The TEE protects buyer prompts and miners' upstream API keys, not GPU inference. |
| "SN90 kuberTEE" | **SN90 KubeTEE AI**: confidential Kubernetes multi-cluster "AI factory" (Kata + Confidential Containers on Intel TDX + NVIDIA CC) | KubeTEE AI LTD | https://github.com/KubeTEE-AI/kubetee-subnet | Yes: Kata/CoCo TDX, NVIDIA CC, Intel Trust Authority |
| "engy SN53" | **SN53 Engy**: "verified inference" for frontier open-weight LLMs on consumer GPUs | Hanlin AI (founder "Ning"; also runs TrajectoryRL SN11) | https://github.com/hanlinai/engy | **No** for the main path ("No TEEs, no trusted hardware. The proof pins the math, not the machine"). It uses TOPLOC fingerprints and sampled recompute. The repo also contains a `tee_miner.py` "TEE-attested worker" tier (see §3). |

Other subnets in scope:
- **SN4 Targon** (Manifold Labs): the most complete TEE design (TVM, Intel whitepaper).
- **SN51 Lium** (Datura): GPU rental with an optional dstack-TDX executor and NVIDIA NRAS checks.
- **SN39 Basilica** (Covenant/Templar team): GPU rental marketplace with bids, CU/RU ledgers and slashing. No TEE found in its code.
- **SN19 is no longer "Nineteen"** (Rayon Labs). It is now **BlockMachine**, a decentralized RPC-node network run by Taostats. No TEE. It matters here only because gm reuses its weight math.
- **SN120 Affine**: RL/distillation. Inference runs on Chutes and it has no TEE of its own.
- Also noted: SN2 Inference Labs (zk; SGX/TDX proof-of-concept archived), SN96 Verathos (sampled GEMM proofs, no TEE).

---

## 1. SN28, gm (sayGM): TEE-gated LLM API marketplace

**What it does.** Buyers point their OpenAI, Anthropic or Gemini SDK at the gm gateway (`api.saygm.com/v1`). The gateway routes each request to the cheapest eligible miner worker. That worker proxies the request to an upstream provider (Anthropic, OpenAI, Google, Chutes, Z.ai, Moonshot, DeepInfra, KubeTEE, Engy, Moonmath, NEAR AI Cloud, or Azure/Foundry) using **the miner's own API keys**. Miners earn the spread. The subnet is netuid 28 on mainnet and 482 on testnet. **[CONFIRMED-DOC]** https://github.com/taostat/gm-miner (README)

**Team and history.**
- The repos live under GitHub org `taostat`, and miners log in with **Taostats device-code OAuth** **[CONFIRMED-CODE]**.
- gm-validator's weight math is "ported from bm-validator", i.e. the SN19 BlockMachine validator that Taostats also runs **[CONFIRMED-CODE]** (`validator/src/gm_validator/alpha_economics.py`).
- Subnet Alpha says gm "operates under Foundry Accelerate", that SN28 was previously an S&P 500 forecasting oracle, and that mainnet beta started 2026-05-28. It also reports ~1 active miner, ~14 validators, alpha at ~0.017–0.018 TAO and a ~19K TAO market cap **[3RD-PARTY]** https://subnetalpha.ai/subnet/gm/
- **The ownership attribution conflicts.** The code clearly points to the Taostats team. Foundry may have been the previous SN28 owner (its snpOracle repo is https://github.com/foundryservices/snpOracle) **[UNVERIFIED]**.

**TEE approach [CONFIRMED-CODE/DOC]** (`dstack/docker-compose.yaml`, `docs/reproducibility.md`, `CLAUDE.md`, `docs/sourcing.md`):
- **Hardware.** Intel TDX CVMs provisioned by **Phala Cloud** (dstack), which also runs the KMS. Miners need a funded Phala Cloud account and do not own the hardware.
- **Measured workload.**
  - The primary measurement is the **compose_hash** (SHA-256 of the dstack `docker-compose.yaml`), plus the **os_image_hash**.
  - `gmcli deploy` checks that the deployed compose_hash and os_image_hash exactly match a **registry-approved ImageVersion** before registering the worker.
  - Everything behavior-relevant is rendered as a literal into the compose file so it is measured: network, node secret, allowed env names (`CANONICAL_ALLOWED_ENVS`). A miner who changes any of it moves the compose_hash, and the registry rejects the worker.
  - The image is pinned by digest. Docker layers are **not** bit-reproducible, which the team accepts ("compose-hash is the primary attestation anchor").
- **Secrets.** Provider keys are encrypted client-side to the CVM key by `phala deploy` and only ever decrypted inside the TEE.
- **Identity and transport.**
  - Mechanism 1: a per-worker **node secret**, enforced by Envoy through an `x-gm-node-key` header.
  - Mechanism 2: an **RA-TLS** certificate minted by dstack. The gateway must connect through the dstack TLS-passthrough URL (`<app-id>-8080s.<node>.phala.network`) so it actually sees the RA-TLS certificate.
  - `gm-miner-attestd` serves `/attestation/info`, backed by the dstack guest-agent `get_quote` / `get_key`.
- **Model-substitution defenses** (the risk here is upstream model swap, not GPU cheating):
  - A per-response **model echo** check at the gateway.
  - For Azure/Foundry, an in-TEE ARM check that deployment X really serves model X. It is fail-closed at boot and re-polled every 60 s.
  - For NEAR routes, an in-image verifier opens a fresh TLS connection per request and requests nonce-bound evidence. It validates the TDX quote, the exact model id, the live TLS public-key fingerprint, the compose-measurement binding and **NVIDIA's GPU verdict** before forwarding. There is no unattested fallback. This is a neat **TEE-to-TEE chained attestation** pattern.

**Incentive mechanism [CONFIRMED-CODE]** (`gm-validator/README.md`, `scoring.py`, `alpha_economics.py`):
- **Pricing.** Miners declare a `--discount-pct` in [0, 99.90] off retail. Payout is `buyer_retail[dim] × (10000 − discount_bp)/10000` for each of 10 price dimensions (input, output, cache, audio, image, long-context, and so on).
- **Routing.** The gateway keeps each worker's cheapest surviving route and gives each worker **one lottery entry**.
- **Epochs and data.** Epochs last ~72 min. A **gm-operated epoch-finalizer** publishes `aggregated.jsonl` and `epoch_summary.json` to a public-read S3 bucket. Validators mirror these files.
- **Weight formula.** `weight_i = consumed_usd_i / pool_usd`, where `pool_usd = emissions_alpha × 0.41 × alpha_price_usd`.
- **Under-subscription:** the leftover weight goes to the **subnet-owner uid (burn)**. **Over-subscription:** weights are renormalized down.
- **Validators do not re-verify.** "The validator treats the published artifact set as authoritative and does not re-derive cost or re-verify hashes or signatures." All trust sits with the finalizer.

**Lessons.**
- Nice points: dstack compose-hash pinning, RA-TLS, in-TEE key custody, and a USD-denominated cap-and-burn.
- Weak point: validation is fully centralized in the owner's finalizer.
- Tiny miner set: ~1 active miner per Subnet Alpha **[3RD-PARTY]**.
- KubeTEE plugs its idle GPU capacity into gm as a provider (live 2026-08-19) and references "SN28↔SN90 alpha swaps" **[CONFIRMED-DOC]** https://github.com/KubeTEE-AI/kubetee-subnet/blob/main/docs/SN28-SAYGM.md

---

## 2. SN90, KubeTEE AI: confidential Kubernetes "AI factory"

**What it does.** It turns decentralized multi-cluster GPU nodes into confidential Kubernetes (RKE2, FIPS-140-2 baseline) running inference, fine-tuning and batch jobs in TEEs. It serves an OpenAI-compatible LiteLLM gateway at `llm.kubetee.ai` with GLM-5.2/5.3, Kimi-K3 on B300, and Ornith-1.5-397B ("first worldwide", 2026-08-20). Its TEE-only fallback backends are Chutes, Phala and NEAR AI. **[CONFIRMED-DOC]** https://github.com/KubeTEE-AI/kubetee-subnet

**Status.**
- Phase 0 "Early Access": **two USA miner clusters**, one hotkey each. Validator v1 is live on Finney.
- Market data from SubnetRadar (Aug 2026): token $5.64, market cap ~$1.1M, "health 44/100" **[3RD-PARTY]** https://subnetradar.com/subnet/90

**TEE approach [CONFIRMED-DOC]:**
- **Stack.** Kata Containers 4.1.0 plus CNCF Confidential Containers (CoCo). The runtime classes are `kata-qemu-nvidia-gpu-tdx-runtime-rs` (GPU + TDX) and `kata-qemu-tdx-runtime-rs` (CPU-only).
- **Hardware.**
  - Intel TDX with **H100/H200/B200/B300** in CC mode. AMD SEV-SNP is planned.
  - Minimum **8 nodes per cluster** (5 control-plane/etcd plus 3+ dedicated 8-GPU workers per GPU type), all in a single data center.
  - TDX/SGX enabled in BIOS and kernel.
  - They achieved 8×B300 passthrough into a single Kata TDX guest (a 2.5 TB Kimi-K3 pod) and filed upstream bugs such as kata-containers#13535 (slow TDX OVMF eager memory acceptance).
- **Attestation.**
  - CoCo **Trustee (KBS)** validates guest evidence and releases secrets only to attested guests (when debug is off).
  - **Attestation-gated TLS**: the in-guest TLS public key is embedded in the TDX `report_data`, the quote is verified via **Intel Trust Authority**, and a certificate is issued only against a valid quote. The design explicitly treats the host as the adversary.
  - The **validator itself runs in a Kata+CoCo TEE pod**, so its code integrity is attestable.
- **Caveat.** "No attestation, no emissions" is the stated principle, but **TEE attestation evidence is only scheduled for validator scoring in Phase 1**. Validator v1 is a binary infrastructure-readiness gate: hotkey label binding, Rancher readiness, HA topology, capacity, GPU passthrough wiring, and presence of the confidential runtime handler.

**Incentive mechanism [CONFIRMED-DOC]** (`README.md`, `docs/COMPETITIVE-PRICING.md`):
- **Per-miner weight.** A USD compensation target is converted to alpha: `usd_target_per_hour × tenure × window_hours ÷ usd_per_alpha`.
- **Unearned allocation** goes to the owner UID and is **recycled** (`recycle_or_burn=recycle`), not paid to the owner.
- **Default price card** (USD per GPU-hour): H100 $4.00, H200 $5.50, B200 $8.00, B300 $10.00, RTX6000 $2.50.
  - This card is **clamped downward only (floor 75%) using Targon's live payouts** from `stats.targon.com/api/miners`.
  - Designed but not yet built: `target = mean(Targon, mean(Lium, Chutes)) × (1+α·demand_pressure) × confidential_premium`.
  - Final weight = capacity score × price-competitiveness score.
- **Feed-failure policy.** The TAO/USD and alpha→TAO compensation feeds **fail closed** (the cycle is skipped and previous weights persist). The Targon price feed **fails soft** (live → cached → price card).
- **Anti-self-dealing.** It scores **provable available capacity, not utilization**. Utilization scoring would let a related-party consumer wash-trade.
- **Collateral** (`docs/MINER-DEPOSIT.md`):
  - A 100 TAO deposit is held on the miner's **own hotkey** using Subtensor v437 registration-collateral hyperparameters (`collateral_lock_share`, `collateral_drain_ratio`).
  - It is **not slashable**: it only freezes. Today it is measured but not enforced; enforcement comes in Phase 1.

**Tokenomics [CONFIRMED-DOC]** (`docs/TOKENOMICS.md`):
- Standard 41% miners / 41% validators / 18% owner split.
- Consumers buy SN90 alpha on the open market (no discount). Spent alpha is **recycled** into unissued supply, described as a "Bitcoin-fee model".
- The owner's value comes only through the 18% owner emission. Owner conviction is **auto-locked in perpetuity**. There is no treasury.
- Stated KPI: the **subsidy ratio** (emission value ÷ total miner compensation) should trend down until consumer spend fully funds miners.

**Lessons.**
- The best public write-up of **Kubernetes-native confidential containers** on Bittensor.
- The honest roadmap shows TEE-in-scoring is hard. Today the "TEE subnet" pays for readiness, not for attested runtime evidence.
- Very concentrated supply (2 clusters) and very high miner capital requirements (≥8 nodes in one DC).

---

## 3. SN53, Engy: verified inference without TEEs (proof-based alternative)

**What it does.** OpenAI- and Anthropic-compatible gateway (`api.engy.ai`) serving open-weight models (GLM-5.2 NVFP4 on RTX 5090 clusters; Qwen3.6-35B-A3B FP8). It claims Kimi K3 (2.8T parameters) running on 80 RTX 5090s **[3RD-PARTY]** https://www.tao.media/is-engy-the-breakout-subnet-bittensor-has-been-waiting-for/
- Reported pricing: GLM-5.2 $0.68/M input, $1.50/M output; Qwen3.6-35B $0.045/M input, $0.30/M output **[3RD-PARTY]** (KuCoin community post, https://www.kucoin.com/news/community/TAO/6a606f607d4c720007969ff2).

**Verification (not TEE) [CONFIRMED-DOC]** (https://github.com/hanlinai/engy, `docs/SN53_ONE_PAGER.md`, `docs/ANNOUNCEMENT.md`):
- **Model pinning.** Architecture, weights and quantization are pinned by a 32-byte **`model_root`** Merkle root (files under `specs/`).
- **TOPLOC** activation fingerprint on every response, at zero extra GPU cost (an asynchronous tap off the response path).
  - A validator holding the canonical checkpoint re-runs sampled prompts and compares top-k activations. The score is the mean top-k mismatch normalized by k=128, with a cheat threshold at P99.
  - **Experiment:** honest FP8 on RTX 4090 scored ~0.18 and on RTX 5090 ~0.23 (pass). An INT4 miner claiming the FP8 root scored ~0.55 (caught). There were zero false positives across mixed consumer GPUs.
- **Sampled GEMM recompute** (Freivalds-style, CommitLLM-like) is built but **not yet the enforcement gate**.
- **Two-phase audits.** The nonce is revealed only after the master validator holds the miner's commitment. Verdicts are `pass`, `cheat` or `unproven`, and `unproven` never costs the miner.
- **What is not proven:** serving at *higher* precision.
- **Privacy is policy, not hardware.** The gateway keeps zero data retention (only metadata is logged). TOPLOC proofs, which contain buyer tokens, live in expiring RAM only.

**Emerging TEE tier [CONFIRMED-CODE, purpose partly UNVERIFIED].** `miner/tee_miner.py` is "the gateway leg for a TEE-attested worker". A provider "declare" step bakes worker ids into a confidential VM, and activation flips the worker row to `type='tee'`. The attestation details are not in the public repo.

**Incentive mechanism [CONFIRMED-DOC]:**
- **Score formula.** Per (miner, model): `score = floor(Σ(prompt_tokens+completion_tokens) × score_rate[model] / 1000)` if **all gates pass**, else 0.
  - **Only billed 2xx requests count** (`cost_micro > 0`). This is the explicit **anti-wash-trading** rule: free, internal and probe traffic never scores.
  - `score_rate` is set by the team, not by buyer price, so discounts cannot distort scoring.
- **Gates:**
  - Acceptance below 99% fails.
  - TTFT p99 or TPOT p99 above the model's target fails.
  - More than 1% `cheat` verdicts fails.
  - Each gate passes automatically below its minimum sample size. Gates are stateless: a failure costs one epoch and there are no bans.
  - Miner-attributable failures are exactly HTTP 502 and 504.
- **Normalization and burn.** Scores normalize to 65535. With no billed traffic, all weight goes to the owner hotkey (burn). New keys start at zero, which makes registration churn unprofitable.
- **Epochs.** Settlement is integer-only fixed-point so every validator implementation computes the same result. The one-pager says **weekly** epochs in production; the announcement says **daily** **[conflict, UNVERIFIED which is current]**.
- **Admission.**
  - New miners must pass **synthetic probe traffic** (≥99% HTTP success, TOPLOC pass, latency ceilings) before any buyer traffic reaches them.
  - A circuit breaker pulls degraded miners within ~1 minute.
  - Miners **dial out** to the gateway, so they expose no inbound port.
  - The 1st-party cluster is always eligible and shares load equally with qualified miners.
  - The one-pager says miners post collateral to register and a proven cheat is slashed.
- **Validators.**
  - An engy-run **GPU "master validator"** does the verification and publishes a signed epoch result.
  - Third-party "light" validators are CPU-only. They verify the sr25519 signature against the pinned master hotkey and mirror the weights.
  - This centralization is acknowledged as temporary. Phase 2 plans to distribute verification.

**Lessons for video.** Engy shows a cheap, hardware-agnostic way to catch model substitution in LLMs. It does not transfer directly to diffusion or video models: stochastic sampling across many denoising steps makes activation fingerprints much harder **[MY INFERENCE]**. It also lacks hardware-backed privacy. Its **economic design** (billed-only scoring, team-set score_rate, SLA gates, probe admission, dial-out miners, integer settlement) is highly reusable.

---

## 4. SN4, Targon (Manifold Labs): the reference TEE architecture

**Team.** Manifold Labs Inc., Austin TX; CEO Robert Myers (ex-Opentensor Foundation) **[3RD-PARTY]**. Repo (Go): https://github.com/manifold-inc/targon. Product: "Secure Targon Compute", H200 and CPU nodes rented inside TVM, launched 2025-10-28 **[3RD-PARTY]**.

**TEE approach [CONFIRMED-DOC]** (Intel whitepaper, 2026-03-23: https://www.manifold.inc/releases/intel-whitepaper; TVM pages https://www.manifold.inc/releases/targon-v6 and https://www.manifold.inc/releases/targon-v7):
- **Hardware.** Intel 5th/6th Gen Xeon (Emerald/Granite Rapids) with TDX, or AMD SEV-SNP. NVIDIA Hopper (H100/H200) or Blackwell (B200/B300) with CC / Protected PCIe (PPCIe). TPM 2.0 and Secure Boot required. TargonOS is installed on the host.
- **Encrypted CVM provisioning.**
  - An "Image Gateway" builds an Ubuntu 24.04 CVM with a **random per-VM disk key**.
  - It deterministically **precomputes the expected TDX measurement** of the boot chain and stores it in the Targon **Key Broker Service (KBS)**.
- **Key release.**
  1. An initramfs Attestation Agent collects TDX measurements and generates a quote, which goes to the KBS.
  2. The KBS forwards the quote to **Intel Trust Authority (ITA)**, which returns a signed JWT.
  3. The KBS checks the JWT, the measurements, and the embedded **NVIDIA nvTrust GPU attestation** (GPU plus NVSwitch).
  4. Only then is the disk key released, bound to that instance. Any modification leaves the disk encrypted.
- **Continuous attestation.** Re-attestation roughly **every 72 minutes** using validator-issued nonces. A failure removes the node from scheduling.
- **Non-migratability.** The first attestation **binds the CVM to the provider's source IP**, and later attestations must come from that IP.
- **Orchestration.** Attested CVMs join a WireGuard mesh as Kubernetes workers. Only continuously verified nodes get workloads.
- **Stated limitations:** the early-boot (initramfs) attestation window, brittle IP binding, **no user-facing verification yet**, trust in ITA and NVIDIA keys, and unquantified overhead.

**Validator code [CONFIRMED-CODE]:**
- **Validator environment.** The validator runs as a VM, recommended on an AMD SEV-SNP host (for example Latitude m4.metal.medium) (`docs/validator/validator.md`).
- **Collecting evidence.**
  - The validator discovers a miner's CVMs via `GET http://<miner>/cvm`, then fetches evidence from `http://<cvm>:<port>/api/v1/evidence` with a hotkey-derived nonce.
  - The evidence includes the TDX quote, optional TPM evidence (AK, PCRs), NVCC `gpu_remote` and `switch_remote` tokens, gpu_cards, `auction_name` and `cvm_id` (`internal/attest/types.go`).
- **Verification is delegated to Manifold's central "Tower".** The validator POSTs to `<towerURL>/api/v1/verify-attestation`, or `/api/v2` with TPM evidence, signed with Epistula headers, and gets back only `valid`/`error` (`internal/attest/cvm/cvm.go`). Validators do not verify quotes themselves.
- **Duplicate detection.** A repeated `cvm_id` is rejected (`callbacks/cvms.go`).
- **Auction mechanism** (`callbacks/weights.go`, `callbacks.go`):
  - Tower also supplies the **auctions** (TargetPrice, TargetCards, MaxPrice, MinClusterSize per compute type), the TAO price and the **BurnDistribution**.
  - The miner emission pool in USD per tempo = `alphaOut × 0.41 × 360 × TAO_price × alpha_price`.
  - For each auction, `pool = TargetPrice × TargetCards` and `perNode = min(pool / nodes, MaxPrice)`. So per-GPU pay falls as supply exceeds the target count.
  - Miner fraction of emission = `perNode × 1.2 × cards / (EmissionPool × 100)`. If the total exceeds 1, it is scaled pro-rata. Otherwise **the remainder is burned** via Tower's burn keys, with any residual going to uid 28.
  - Weights are set once per 360-block tempo.
- **Live auction snapshot** from my fetch of `https://stats.targon.com/api/miners` on 2026-09-11. **Only 37 nodes from 4 UIDs**:

  | Compute type | Nodes | Cards | Payout per node |
  |---|---|---|---|
  | TDX-VM-NVIDIA-H200 | 14 | 112 | 26.48 |
  | TDX-HOPPER-NVIDIA-H200 | 2 | 16 | 28 |
  | TDX-VM-NVIDIA-H100 | 3 | 24 | 32 |
  | TDX-VM-NVIDIA-B300 | 8 | 64 | 78 |
  | SEV-CPU-AMD-EPYC-V4 | 9 | 9 | 0.2 |
  | TDX-VM-NVIDIA-RTX6000B (RTX PRO 6000 Blackwell) | 1 | 8 | 16 |

  If payout is USD per node-hour, that implies ~$3.3/GPU-hr for H200, $4/GPU-hr for H100 and ~$9.75/GPU-hr for B300 **[MY INFERENCE: units not documented]**. KubeTEE uses this same feed as its price benchmark.

**Revenue and tokenomics [3RD-PARTY]:**
- About $100K/month in 2025, "fully committed to alpha buybacks". Later claims of eight-figure annualized revenue, with ~$10.4M ARR as a self-reported, unaudited figure.
- A reported 550 TAO buyback.
- ~5.73% emission share and a subsidy ratio of ~1.7:1 (Pine Analytics).
- Named customers are Bittensor-native (Dippy, Ridges, Score).
- Sources: https://ownyourmind.ai/tokenomics/targon-bittensor-confidential-compute/ and https://x.com/zinceth/status/2033676873230881185
- The "Targon Tower Pro" workstation (8 GPUs plus a TDX CPU, from $57,500, reservations opened 2026-06-02) earns on SN4 when idle **[3RD-PARTY]** https://www.tao.media/what-is-targon-tower-pro/

**Problems and critiques.**
- **Centralized trust.** Tower verifies attestations and sets auctions and burn, and the TVM orchestration runtime is proprietary **[3RD-PARTY + CODE]**.
- Revenue figures are unaudited and there is no public revenue dashboard.
- Supply is highly concentrated (4 UIDs in my snapshot).
- Historical: a "Kill Weight Copying" update in Nov 2025 and heavy alpha burning while the auction model was built out **[3RD-PARTY]**.

---

## 5. SN51, Lium (formerly Celium; Datura AI): GPU rental with optional dstack-TDX

**What it does.** A peer-to-peer GPU rental marketplace (SSH/containers). A provider (CPU coordinator signing with the hotkey) manages executor GPU nodes. Validators probe the nodes, create rental containers and set weights. Repo: https://github.com/Datura-ai/lium-io; docs: https://docs.lium.io/providers/architecture

**Hardware verification without TEE [CONFIRMED-CODE]:**
- The Sysbox runtime is mandatory.
- Per-job obfuscated hardware-scrape scripts.
- Closed binary challenge libraries (`libverifyx.so`, `libinspector.so`, `libdmcompverify.so`).
- An allow-list of libnvidia-ml digests.
- An **Inspector gate**: if the host reaches into a renter's pod (exec, nsenter, memory access), the score is zeroed.

**TEE path, dstack TDX executor [CONFIRMED-CODE]** (`neurons/executor/dstacktee/README.md`, `executor/src/services/tdx_service.py`, `validators/src/services/attestation_service.py`, `services/const.py`):
- **CVM setup.**
  - The executor runs in an Intel TDX CVM using the dstack QEMU 9.2.1 build.
  - An **SGX key-provider enclave** derives deterministic sealing keys from the VM's measurements, so secrets persist across reboots.
  - The **validator hotkey is measured into an RTMR** by `init_script.sh`. `EXECUTOR_RUNNER_IMAGE_DIGEST` is required.
- **Quote binding.** `report_data = sha256("SSH_HOST_KEY:" + ssh_host_key) ‖ 32-byte validator nonce`. This ties the SSH identity to the TEE and makes each quote fresh. Nonce-bound quotes are never cached.
- **Verification.** The validator POSTs the quote to its configured `TDX_VERIFIER_URL`. It then checks report_data (identity half plus nonce echo) and a whitelist in code:
  - `OS_IMAGE_HASH`: a single-image policy, dstack-nvidia 0.5.11.
  - `COMPOSE_HASH` per environment, each with a **monotonically increasing release version** and a `TDX_MINIMUM_COMPOSE_VERSION` floor. A bad release is retired by raising the floor.
- **GPU CC attestation** goes through **NVIDIA NRAS**. The code decodes the JWT claims **without signature verification** and relies on the TLS connection to NRAS, described as an "interim posture" until a local nv-verifier replaces NRAS.
- **TCB/advisory enforcement** is warn-only unless `ENABLE_TCB_ENFORCEMENT` is set.
- **Ratchet.** Once an executor has presented a valid TDX quote, omitting one later is treated as a **bypass attempt** (fail-closed).
- **Incident.** One compose version was "burned" because its runner baked in the **staging validator hotkey** and returned 401 to every production validator. Staging images can leak into production measurements.

**Scoring [CONFIRMED-CODE]** (`task/score_calculator.py`, `const.py`):
- **Zero-score gates:** a CVM-flagged executor without passing TDX+GPU attestation, a CPU-truth mismatch, an Inspector detection, a missing VerifyX bandwidth EMA while unrented, or missing collateral (when required).
  - Collateral is TAO deposited through an EVM collateral contract, with reclaim flows. An old contract version gives a 0 score portion.
  - `IS_NOT_DEPOSITED_SCORE_MULTIPLIER = 0.5`.
- **Relative reward share by GPU type** (the GPU-type weights table in `const.py`): H200 0.56, H200 NVL 0.49, H100 SXM 0.10, B200 0.05, H100 PCIe/NVL 0.01.
- **Pools.** Emission is split between a "rented" mining pool and an "unrented + burn" pool, configured from the backend. `FIXED_RATIO = 0.41`.

**Revenue [3RD-PARTY]:**
- ~$432K/month rental revenue (single-sourced to the team), ~500 H100s, prices from $0.24/hr (L40) to $3.15/hr (H100).
- 4.4–6.2% emission share and a subsidy ratio of 3.5–4.9×.
- Claimed "60% of miner emissions burned", which I could not verify on-chain.
- Source: https://ownyourmind.ai/tokenomics/lium-bittensor-subsidy-ratio/

---

## 6. SN39, Basilica (Covenant AI / Templar team): bid-based GPU marketplace, no TEE

Repo (Rust): https://github.com/one-covenant/basilica (the old URL github.com/tplr-ai/basilica redirects there). Products: SSH GPU rentals ("secure cloud" and "community cloud"), serverless deployments, a Python SDK and TAO top-ups **[CONFIRMED-DOC]**.

**Mechanism [CONFIRMED-CODE]:**
- **Bids.** Miners register nodes with a **per-GPU hourly bid** (`hourly_rate_cents`) via `RegisterBid` and keep them alive with `HealthCheck`. Validators pick the **lowest-priced eligible node** for rentals. Only static pricing is implemented (`crates/basilica-miner/docs/bidding-strategy.md`).
- **Validation.** SSH-driven checks of hardware, docker, network, speedtest, storage and NAT, a misbehaviour table and a ban system. It uses a "validator binary" for hardware attestation; secondary sources describe P-256 ECDSA-signed GPU capability proofs **[3RD-PARTY]**. **No TDX, SEV or NVIDIA-CC code** turned up in the hardware-validation modules I grepped.
- **Incentives** (`incentive/incentive_pool.rs`):
  - The API publishes **CU (compute-unit)** and **RU (revenue-unit)** ledger rows. Slashed rows are excluded.
  - CU payout = `vested_fraction × cu_amount × min(bid_price, per_CU_budget)`, where the budget is `target_gpus × window_hours × price` per GPU category.
  - RU payout = `ru_amount × revenue_share_pct`.
  - The total USD owed is compared with the USD emission capacity: oversubscription is scaled down, and **the remainder is burned** to `burn_uid` (default 204). An optional forced burn percentage also exists.
- **Slashing.** Rental loss from node failure (for example health-check timeout) is slashable. A container that is itself unhealthy is not (`incentive/slashing.rs`).

**Lesson.** A clean USD-budgeted, bid-capped, vesting ledger design with slashing. It is not a confidential design.

---

## 7. SN19: no longer Nineteen; now BlockMachine (Taostats)

- By 2026, taostats, tao.app and SimplyTao label SN19 "**blockmachine**": a decentralized RPC/archive-node network run by the Taostats team (repos `taostat/blockmachine`, `blockmachine-miner`, `blockmachine-validator`) **[CONFIRMED-CODE]**. Sources: https://blockmachine.io/bittensor, https://github.com/taostat/blockmachine-validator
- Validators read gateway logs from public storage and check correctness against reference nodes. A quality gate at 0.6 applies, payouts are "proportional to work served", and failures lead to permanent ejection or bans **[CONFIRMED-DOC]**.
- It has no TEE. It is relevant because gm's cap-and-burn weight code was ported from it.
- Rayon Labs' Nineteen (SDXL/LLM inference) is no longer on SN19. When and why it left is **[UNVERIFIED]**.

## 8. SN120, Affine

- Decentralized RL. The repo description now reads "teacher-anchored distillation subnet". https://github.com/AffineFoundation/affine
- Miners submit models, validators evaluate them in containerized environments (affinetes) using the **Chutes API for inference**, and winners are auto-deployed on Chutes. A Pareto-frontier / winner-takes-most scheme applies **[3RD-PARTY]** https://simplytao.ai/blog/your-simple-guide-to-affine-sn120
- It has **no TEE of its own**. Any TEE comes indirectly from Chutes TEE chutes. The README could not be fetched, so current mechanism details are **[UNVERIFIED]**.

## 9. Others worth knowing

- **Chutes SN64 (comparison only).**
  - sek8s: TDX CVMs with H100/H200 in CC/PPCIe mode.
  - The **validator** performs remote attestation (TD quote plus NVIDIA reports), compares **RTMRs against golden sek8s values**, and only then releases the **LUKS** root-disk key.
  - `report_data = SHA256(nonce ‖ instance ML-KEM pubkey)`, enabling end-to-end post-quantum encryption into the instance.
  - Integrity tools: cfsv (filesystem hash), graval (GPU matmul proof), cllmv (per-token model/revision binding), inspecto (bytecode), and a watchtower that hashes **random weight-file slices** to stop post-launch model swaps.
  - Sources: https://github.com/chutesai/sek8s, https://chutes.ai/docs/core-concepts/security-architecture
- **SN2 Inference Labs.** zk-proof verified inference. Its SGX/TDX TEE proof-of-concept (https://github.com/inference-labs-inc/subnet-2-tee) was **archived 2026-01-02**.
- **SN96 Verathos.** Sampled GEMM proofs ("Gleipnir" protocol) over Merkle-committed weights, with a CPU verifier and no TEE. https://github.com/verathos-ai/verathos

---

## 10. Comparative table

| | SN4 Targon | SN90 KubeTEE | SN28 gm | SN51 Lium | SN53 Engy | SN39 Basilica | (SN64 Chutes) |
|---|---|---|---|---|---|---|---|
| Product | Confidential GPU/CPU rental (TVM), inference | Confidential K8s jobs + LLM gateway | LLM API resale marketplace | GPU rental (SSH/pods) | Verified LLM inference API | GPU rental + serverless | Serverless inference |
| TEE hardware | TDX or SEV-SNP + Hopper/Blackwell CC/PPCIe, TPM | TDX + H100–B300 CC (Kata/CoCo) | TDX CVMs on Phala Cloud (no GPU) | Optional TDX (dstack) + optional NVIDIA CC | None (a TEE worker tier is emerging) | None | TDX + H100/H200 PPCIe |
| Attestation verifier | **Manifold Tower** (central) + ITA + nvTrust; KBS gates disk key | CoCo Trustee KBS + ITA; validator in TEE | gm registry (compose/os hash approval) | Validator → configurable TDX verifier + NVIDIA NRAS | n/a (master validator recomputes TOPLOC) | n/a | Validator (Intel DCAP), RTMR golden values |
| Exact image/model proof | Precomputed TDX measurement + encrypted disk | Kata/CoCo measured guest | compose_hash + os_image_hash whitelist, RA-TLS | OS_IMAGE_HASH + versioned COMPOSE_HASH whitelist, RTMR with validator hotkey | model_root Merkle + TOPLOC | none | LUKS + RTMR + cfsv/cllmv/weight-slice hashing |
| User data protection | Encrypted CVM memory/disk, PPCIe; no user-side verification yet | RA-TLS in-guest keys, Trustee secrets | Keys and prompts decrypted only in TEE; RA-TLS | TDX memory; Inspector detects host intrusion | Policy ZDR only | none | E2E ML-KEM to instance key |
| Scoring basis | Auction: attested capacity, pay/node = min(pool/nodes, MaxPrice) | Binary readiness gate × USD target × price competitiveness | USD consumed ÷ USD miner pool | Attestation/collateral gates × GPU-type share × rental state | Billed tokens × score_rate, SLA + cheat gates | CU/RU ledger × min(bid, budget), slashing | (n/a here) |
| Unused emission | Burned (Tower burn keys) | Recycled via owner UID | Burned to owner uid | Backend-set burn pool | Burned to owner | Burned (uid 204) | — |
| Revenue loop | Revenue → alpha/TAO buybacks (claimed) | Consumers buy alpha, spend is recycled | Buyers pay USD; miners earn spread | Rentals in USD + emissions | Prepaid API credits | TAO/credit top-ups | — |
| Verification decentralization | Low (Tower) | Low (owner control plane, Phase 0) | Low (owner finalizer; validators mirror) | Medium (validators verify quotes) | Low (master validator) | Medium | Medium |
| Miner-set size signal | 4 UIDs / 37 nodes (my snapshot) | 2 clusters | ~1 active miner [3RD-PARTY] | ~500 H100 [3RD-PARTY] | Permissionless, 1st-party heavy | ? | — |

---

## 11. Patterns to copy for a TEE video-generation subnet

1. **Pin the entire workload by measurement and release secrets only after attestation.**
   - Chutes/Targon style: a LUKS or encrypted disk whose key a KBS releases only when the TDX measurement matches a **precomputed golden value** and ITA/DCAP plus NVIDIA attestation pass.
   - dstack style (gm, Lium): whitelist `os_image_hash` and `compose_hash`.
   - Keep a **versioned, append-only whitelist with a minimum-version floor** so a bad release can be revoked instantly (Lium).
   - Put the **video model weights on the encrypted disk** and include their hash in the measured config. Add random **weight-slice hash challenges** (Chutes watchtower) so a miner cannot swap weights after boot.
2. **Bind identity and freshness into `report_data`.** Use `H(enclave pubkey or TLS key or SSH key) ‖ validator nonce` (Lium, Chutes, KubeTEE, gm RA-TLS). That one binding gives you:
   - (a) anti-replay,
   - (b) proof that the endpoint you talk to *is* the attested enclave,
   - (c) a key to which clients can **encrypt prompts, reference images and audio end-to-end**, with **output videos encrypted back to a client-supplied key** so miners and the gateway never see plaintext.
3. **Nest GPU attestation inside CPU attestation, including NVSwitch.** Targon checks `gpu_remote` and `switch_remote` tokens. Multi-GPU video models using sequence or tensor parallelism need PPCIe/NVSwitch attestation too. Prefer a **local NVIDIA verifier with JWT signature checks** over trusting NRAS on TLS alone.
4. **Keep re-attesting on a randomized cadence.** Targon re-attests about every 72 minutes and randomizes validator polling. Add Lium's **ratchet**: once attested, always required. **Deduplicate on hardware or CVM identity** (Targon `cvm_id`) to stop one machine being counted twice.
5. **Denominate the miner budget in USD and cap-and-burn the rest.** `weight_i = usd_owed_i / (alpha_emission × 0.41 × alpha_price_usd)`, with the residual burned or recycled (Targon, gm, Basilica, BlockMachine, KubeTEE). Emissions then track real work, and oversubscription renormalizes automatically.
6. **Pay for paid work plus attested capacity, never for self-generated traffic.**
   - Engy counts only **billed 2xx** requests, with a **subnet-set `score_rate` per model/SKU**. For video that would be something like credits per second of 720p/1080p output at N steps.
   - KubeTEE shows the complementary fix: pay a floor for **attested available capacity** so miners survive the cold-start before demand arrives.
   - Consider a hybrid: an auction-style capacity floor (Targon) plus a demand-proportional share (Engy/gm).
7. **Use gates, not fragile continuous scores.** Engy-style stateless per-epoch gates: success rate ≥99%, p99 job latency (time to finished clip) per SKU, attestation pass, and cheat rate ≤1%. Each gate needs a minimum sample, a failure costs one epoch with no permanent ban, and all settlement uses integer fixed-point for validator agreement.
8. **Admit new miners with probe jobs, and have miners dial out.** Synthetic probe traffic must pass before paid traffic arrives, a circuit breaker pulls degraded miners in about a minute, and outbound-only miner connections remove inbound attack surface (Engy).
9. **Keep verification off the hot path** (Engy). Proof and attestation checks run out-of-band so validator slowness never adds latency to user jobs.
10. **Run validators in TEEs too.** Targon validators run in SEV-SNP VMs and KubeTEE's validator runs in a CoCo pod. This makes the validator's code attestable and eases decentralizing verification.
11. **Use a price benchmark feed and fail closed on economics feeds** (KubeTEE: fail closed on TAO/alpha price, fail soft on competitor price).
12. **Require collateral.** Lium uses an EVM TAO collateral contract, Basilica slashes node loss, and Engy requires registration collateral. Size it for the damage a miner could do, such as dropping a user's job or failing attestation mid-rental.
13. **Offer a hybrid supply tier.** Engy's 1st-party cluster (always eligible) plus permissionless miners gives SLA stability at launch. Only confidential-capable SKUs should be allowed to serve privacy-flagged jobs.

## 12. Pitfalls to avoid

1. **Nominal decentralization with a centralized verifier.** Targon's Tower, Engy's master validator, gm's finalizer ("validators do not re-verify") and KubeTEE's owner-run gates all concentrate trust in the owner. Publish the verifier, let validators check quotes themselves (the Lium model), and publish attestation logs.
2. **A "TEE subnet" that doesn't score TEE evidence.** KubeTEE v1 pays for readiness, not runtime attestation. Make attestation a hard gate from day one.
3. **Weak GPU attestation handling.** Lium decodes NRAS JWT claims without verifying signatures (interim). Early-boot attestation windows (Targon whitepaper), debug-mode guests, and staging images leaking into production (Lium's burned compose v3) are all real risks. Keep separate prod and staging measurement sets, and reject debug TDs.
4. **Non-reproducible builds.** gm relies on the compose hash because Docker layers aren't reproducible. Invest in reproducible or Nix-built images so third parties can recompute golden measurements.
5. **Brittle identity binding.** Targon's IP binding kills a CVM when the provider's network changes. Prefer binding to TEE-sealed keys plus hotkey registration.
6. **Supply concentration from hardware requirements.** TDX + CC Hopper/Blackwell means data-center operators only. My snapshot showed 37 Targon nodes from 4 UIDs; KubeTEE has 2 clusters; gm has ~1 miner. Consumer GPUs (RTX 4090/5090) have **no CC mode**. The RTX PRO 6000 Blackwell does appear as a Targon TDX auction class. Plan SKUs and expected miner counts accordingly, and consider per-UID caps.
7. **TEE proves "right code on genuine hardware", not "good video".** Diffusion outputs are stochastic. Also score quality with sampled spot checks: re-render with a fixed seed inside the validator's own TEE and compare with perceptual or latent metrics, or run CLIP/VBench-style scoring. **[MY INFERENCE]**: no Bittensor subnet has published TOPLOC-style fingerprints for video diffusion.
8. **Wash trading and self-dealing.** Utilization-only scoring rewards related-party buyers (KubeTEE's warning). Capacity-only scoring rewards idle farming. Use billed-only work with a team-set score rate plus a capped capacity floor.
9. **Unverifiable revenue claims.** Targon's $10.4M ARR and Lium's $432K/month are unaudited. Publish an on-chain or verifiable revenue and buyback dashboard, and track the **subsidy ratio** as the headline KPI (KubeTEE).
10. **TEE overhead and cold starts.** KubeTEE hit slow TDX memory acceptance (kata-containers#13535) and multi-GPU passthrough complexity. Big video models on encrypted disks mean slow boots, so keep warm pools and measure time-to-first-job.
11. **Price oracles and feeds** can stall weight setting. Define fail-closed or fail-soft behavior explicitly (KubeTEE).
12. **Owner burn to uid-0/owner as the default** hides a lack of demand. The June 2026 subnet-emission formula reportedly penalizes miner-burn shares **[3RD-PARTY, coinmarketcap/bittensor docs search snippet]**. Heavy burn-to-owner may therefore reduce the subnet's TAO emission share. Verify before relying on it.

## 13. Key sources

- gm: https://github.com/taostat/gm-miner · https://github.com/taostat/gm-validator · https://subnetalpha.ai/subnet/gm/
- KubeTEE: https://github.com/KubeTEE-AI/kubetee-subnet (docs/TOKENOMICS.md, docs/COMPETITIVE-PRICING.md, docs/MINER-DEPOSIT.md, docs/SN28-SAYGM.md) · https://subnetradar.com/subnet/90
- Engy: https://github.com/hanlinai/engy (docs/SN53_ONE_PAGER.md, docs/ANNOUNCEMENT.md, miner/tee_miner.py) · https://www.tao.media/is-engy-the-breakout-subnet-bittensor-has-been-waiting-for/
- Targon: https://github.com/manifold-inc/targon (internal/validator/callbacks/weights.go, callbacks.go, cvms.go; internal/attest/cvm/cvm.go, types.go) · https://www.manifold.inc/releases/intel-whitepaper · https://www.manifold.inc/releases/targon-v7 · https://stats.targon.com/api/miners · https://ownyourmind.ai/tokenomics/targon-bittensor-confidential-compute/
- Lium: https://github.com/Datura-ai/lium-io (neurons/executor/dstacktee/, neurons/validators/src/services/attestation_service.py, const.py, task/score_calculator.py) · https://ownyourmind.ai/tokenomics/lium-bittensor-subsidy-ratio/
- Basilica: https://github.com/one-covenant/basilica (crates/basilica-validator/src/incentive/*, crates/basilica-miner/docs/bidding-strategy.md)
- Chutes: https://github.com/chutesai/sek8s · https://chutes.ai/docs/core-concepts/security-architecture
- BlockMachine SN19: https://blockmachine.io/bittensor · https://github.com/taostat/blockmachine-validator
- Affine: https://github.com/AffineFoundation/affine · SN2 TEE PoC: https://github.com/inference-labs-inc/subnet-2-tee · Verathos: https://github.com/verathos-ai/verathos
