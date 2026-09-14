# Market & Competitive Research: TEE-Secured Video Generation Subnet (Bittensor)

> **2026-09-14:** some prices below are out of date or were read at the wrong resolution (Seedance, Wan 3.0, Grok
> Imagine, Pika, Kling credits, Azure confidential VMs). See [research_pricing.md](research_pricing.md) §9 and
> [pricing/market.md](pricing/market.md).

Research date: 2026-09-11. All prices USD. Sources are inline.

Confidence labels:
- **[C] Confirmed**: read directly on a first-party page (provider pricing page, official docs or repo, CoinGecko).
- **[S] Secondary**: consistent third-party reporting (aggregator blogs, analyst posts) that I did not check against a first-party page.
- **[U] Unverified**: a single source, extrapolated, or my own estimate or inference.

Note: the session's web-search budget ran out near the end. A few items below (confidential-computing market size; SN44, SN93 and SN20 details) could not be re-checked and are marked accordingly.

---

## PART A: VIDEO GENERATION MARKET

### A1. Market size, growth, segments

**Analyst estimates disagree widely, depending on scope.** "AI video generator software" is a narrow category; "AI video" is a broad one.

| Source | Scope | Base | Forecast | CAGR | Conf. |
|---|---|---|---|---|---|
| Research & Markets ([link](https://www.researchandmarkets.com/reports/6061727/ai-video-generator-market-forecasts)) | AI video generator | $1.07B (2025) | $1.97B (2030) | 12.8% | [S] |
| MarkNtel ([link](https://www.marknteladvisors.com/research-library/ai-video-generator-market.html)) | AI video generator | n/a | $2.34B (2030) | 32.8% | [S] |
| Grand View ([link](https://www.grandviewresearch.com/industry-analysis/artificial-intelligence-ai-video-market-report)) | AI video (broad) | n/a | $42.29B (2030) | 32.2% | [S] |
| Market.us ([link](https://market.us/report/ai-video-market/)) | AI video (broad) | n/a | $71.5B (2030) | 36.2% | [S] |
| Market Intelo, via Luma stats page ([link](https://lumalabs.ai/news/ai-video-generation-statistics)) | AI video generation | $6.2B (2025) | $47.8B (2034) | 25.4% | [S] |
| Precedence, via Luma | AI video generation | n/a | $156.6B (2034) | 35.3% | [S] |

**Bottom-up revenue signals are more useful than analyst TAMs.** 2026 run-rates of individual companies already exceed the narrow "generator market" estimates.
- **Kling (Kuaishou):** ARR $500M as of Mar 2026, up 4x YoY. Q2 2026 revenue was above RMB 850M, up more than 200% YoY. Morgan Stanley forecasts $1B ARR by year-end 2026. [S] Sources: [Kuaishou IR Q1](https://ir.kuaishou.com/news-releases/news-release-details/kuaishou-technology-announces-first-quarter-2026-unaudited), [Dealroom](https://app.dealroom.co/news/feed/kuaishou-s-kling-ai-hits-117m-revenue-with-200-growth-in-q2-2026), [BigGo](https://finance.biggo.com/news/96811fd9-a698-41c3-aa5d-d799ab93ca7d)
- **Runway:** ARR went from about $100M (Apr 2026) to $200M (Sep 2026). It expects more than $350M by the end of 2026. [S] Sources: [TechTimes](https://www.techtimes.com/articles/326994/20260908/runway-ai-hits-200m-arr-enterprise-video-adoption-triples-existing-spend.htm), [PYMNTS](https://www.pymnts.com/news/artificial-intelligence/2026/runway-ai-hits-200-million-revenue-and-expands-robotics-capabilities)
- **fal.ai (generative-media inference):**
  - ARR about $400M as of Feb 2026, up from $100M in 2025. [S]
  - Raised $140M at a $4.5B valuation in Dec 2025, and was reportedly raising at about $8B in Mar 2026. [S]
  - Serves Adobe, Canva and Shopify. [S]
  - Sources: [Dealroom](https://app.dealroom.co/news/note/fal-targets-8b-valuation-in-new-raise-as-ai-inference-revenue-doubles-to-400m), [Sacra](https://sacra.com/c/fal-ai/)
- **OpenRouter:** raised $113M at a $1.3B valuation in May 2026. It launched a video API on Apr 15, 2026. [S] Source: [KuCoin](https://www.kucoin.com/news/flash/bittensor-integrates-confidential-routing-layer-with-openrouter-processes-up-to-120-billion-tokens-daily)
- **Volume:** Veo 3 produced about 70M videos in roughly 2 months. Kling has produced about 600M videos. AI video generation volume grew 840% from Jan 2024 to Jan 2026. [S] Source: [Luma stats](https://lumalabs.ai/news/ai-video-generation-statistics)

**Segments** [S]. Sources: [market.us](https://market.us/report/ai-powered-video-generator-market/), [Luma stats](https://lumalabs.ai/news/ai-video-generation-statistics)
- **Marketing and advertising** is the largest segment: 31.2% (Luma, citing others) or 40.6% (market.us). AI video ad spend is projected at $9.1B in 2026, about 12% of digital video ads.
- **Media and entertainment:** about 28.4%.
- **Retail and e-commerce:** 17.6% share, growing at a 28.4% CAGR (product videos across large catalogs).
- **Education:** 19.7%. **Healthcare:** 10.2% share, 28.1% CAGR.
- **Social media** has the fastest CAGR, 20.8–23.5% (short-form content).
- **Gaming:** no clean split was found. It is served mostly by the 3D and animation adjacencies, such as 404-GEN.
- **Regions:** North America has 38.5–41% share; Asia-Pacific has 31–37% and is the fastest-growing.
- **Adoption:** 63% of video marketers used AI tools in 2025, up from 51% in 2024. Enterprise AI-video spend grew 127% YoY in 2025. [S]

**Enterprise privacy and confidentiality demand**
- **Cisco 2026 Data & Privacy Benchmark** (5,200 respondents, 12 markets) [C/S]. Sources: [PDF](https://www.cisco.com/c/dam/en_us/about/doing_business/trust-center/docs/cisco-privacy-benchmark-study-2026.pdf), [newsroom](https://newsroom.cisco.com/c/r/newsroom/en/us/a/y2026/m01/ai-data-privacy-investments-governance-cisco-report.html), [Kiteworks summary](https://www.kiteworks.com/cybersecurity-risk-management/cisco-2026-privacy-ai-governance/)
  - Data leaks through GenAI are the top security concern (34%, up from 22%).
  - Outright GenAI bans fell from 28% to 7%.
  - Organizations are moving from banning GenAI to governing it. That shift creates demand for technical controls such as TEEs.
- **77% of AI leaders cite data privacy as a significant concern.** [S] Source: [secureframe](https://secureframe.com/blog/data-privacy-statistics)
- **Kling terms of service** reportedly grant Kuaishou rights to use submitted content, including for model training, and content is processed under Chinese data law. The TOS grants a "worldwide, royalty-free, perpetual license." For enterprises with unreleased products, client likenesses or GDPR-covered data, that is a real barrier. [S] Sources: [Kling TOS](https://kling.ai/docs/user-policy), [Kling privacy](https://kling.ai/docs/privacy-policy)
- **Video-specific privacy use cases** [U, my inference]: unreleased product shots for e-commerce and ads, celebrity or talent likeness under contract, agency client IP, pre-release entertainment and game assets, medical or education content involving real people, and personalized video from customer photos.

### A2. Closed providers: API pricing (as of Jul–Sep 2026)

| Provider / model | $/second | 5s clip | Notes | Conf. |
|---|---|---|---|---|
| **Google Veo 3.1 Standard** | $0.40 (720p/1080p), $0.60 (4K) | $2.00 | Includes audio. Gemini API ([pricing](https://ai.google.dev/gemini-api/docs/pricing)) | [C] |
| **Veo 3.1 Fast** | $0.10 (720p), $0.12 (1080p), $0.30 (4K) | $0.50 | Includes audio | [C] |
| **Veo 3.1 Lite** | $0.05 (720p), $0.08 (1080p) | $0.25 | Includes audio | [C] |
| Veo 3.1 via Runway API | $0.40 audio / $0.20 no audio; Fast $0.15 / $0.10 | – | [Runway API pricing](https://docs.dev.runwayml.com/guides/pricing/) | [C] |
| **OpenAI Sora 2** | $0.10 (720p); batch $0.05 | $0.50 | **API sunsets Sep 24, 2026.** Consumer app closed Apr 26, 2026 ([costgoat](https://costgoat.com/pricing/sora), [unifically](https://unifically.com/blogs/sora-api)) | [S] |
| **Sora 2 Pro** | $0.30 (720p), $0.50 (1024p), $0.70 (1080p) | $1.50–3.50 | Batch is 50% off. Sunsetting | [S] |
| **Kling 3.0 (official)** | 6 cr/s (720p) and 8 cr/s (1080p) without audio; 9 and 12 cr/s with audio | about $0.45 (720p) | At a reported $1 = 66 credits, that is about $0.091/s at 720p and $0.121–0.182/s at 1080p. Resellers charge $0.067–0.10/s ([evolink](https://evolink.ai/blog/kling-3-o3-api-official-discount-pricing-developers), [costbench](https://costbench.com/software/ai-media-apis/kling-api/)) | [S]; the credit conversion is [U] |
| **Runway Gen-4.5** | 12 credits/s at $0.01/credit = **$0.12** | $0.60 | [Runway API pricing](https://docs.dev.runwayml.com/guides/pricing/) | [C] |
| Runway Gen-4 Turbo | $0.05 | $0.25 | same | [C] |
| Runway Aleph 2 (video-to-video) | $0.28 | $1.40 | same | [C] |
| **Luma Ray 3.2** | 5s blocks: $0.06 (360p), $0.15 (540p), **$0.30 (720p)**, $1.20 (1080p); HDR costs 2x | $0.30 (720p) | [Luma docs](https://docs.agents.lumalabs.ai/guides/pricing/) | [C] |
| **ByteDance Seedance 2.0** | $0.06726 (OpenRouter). BytePlus lists $0.067 (480p) to $0.78 (4K) | $0.34 | [OpenRouter](https://openrouter.ai/collections/video-models), [Atlas](https://www.atlascloud.ai/blog/case-studies/seedance-2.0-pricing-full-cost-breakdown-2026) | [C] (OpenRouter) |
| Seedance 2.0 Fast / Mini | $0.04035 / $0.03363 | $0.20 / $0.17 | OpenRouter | [C] |
| Seedance 2.5 | $0.1028 (OpenRouter); Runway charges $0.30/s at 720p | $0.51 | – | [C] |
| **MiniMax H3** (Hailuo 03) | $0.13/s (OpenRouter); $0.08/s (768p) and $0.13/s (2K) per MiniMax | $0.40–0.65 | [OpenRouter](https://openrouter.ai/minimax/hailuo-3) | [C]/[S] |
| MiniMax H3 Max | $0.05 (480p) to $0.08 (768p) | $0.25–0.40 | OpenRouter | [S] |
| Hailuo 2.3 Fast | 6s 768p = $0.19; 10s 768p = $0.32 | about $0.16 | [MiniMax docs](https://platform.minimax.io/docs/guides/pricing-video) | [S] |
| **xAI Grok Imagine Video** | $0.05 (480p), $0.07 (720p); v1.5 costs $0.08 | $0.35 | [OpenRouter](https://openrouter.ai/x-ai/grok-imagine-video) | [S] |
| **Alibaba Wan 3.0** (closed API) | $0.0425 (OpenRouter); Runway: $0.05 (480p), $0.10 (720p), $0.20 (1080p) | $0.21–0.50 | Launched Aug 2026 as an API-only beta | [C] |
| **Pika 2.5** | Subscription only: 20 credits per 5s 720p. Standard plan is $28/mo for 700 credits | about $0.80 | [eesel](https://www.eesel.ai/blog/pika-ai-pricing) | [S] |
| **Midjourney Video V1** | Subscription GPU time: about 8 fast-GPU-minutes per video job. Plans run $10–120/mo | n/a | [eesel](https://www.eesel.ai/blog/midjourney-pricing) | [S] |

**Takeaways**
- **The price band for a 5s 720p clip from closed frontier models is about $0.17 to $2.00.** The competitive middle of the market is **$0.20–0.50**.
- **Prices are falling fast.**
  - Veo 3.1 Lite is $0.05/s with audio.
  - Seedance Mini is $0.034/s.
  - Wan 3.0 is $0.0425/s.
- **Sora's API shutdown (Sep 24, 2026) frees up customers who need to migrate.**
- **The top closed models are Chinese-origin.** On Artificial Analysis (AA) text-to-video with audio: Wan 3.0 has an Elo of 1242, Gemini Omni Flash 1238, and Seedance 2.0 1220 ([AA leaderboard](https://artificialanalysis.ai/video/leaderboard/text-to-video)). [C]

### A3. Open-model inference providers and GPU unit economics

#### Open-weights model landscape (Sep 2026)
- **Wan 2.1 / 2.2** (Alibaba) are the only flagship Wan models with open weights.
  - License: **Apache 2.0**. Wan 2.2 was released Jul 28, 2025.
  - Wan 2.2 has 27B total parameters, of which 14B are active (a Mixture-of-Experts design). The A14B variants output 16 fps and the TI2V-5B variant outputs 24 fps.
  - **Wan 2.5, 2.6, 2.7 and 3.0 are closed and API-only.**
  - Alibaba still releases Apache-2.0 add-ons: Wan-Dancer-14B (Jul 2026) and Wan2.2-Animate-2-14B (Aug 2026).
  - [S] Sources: [Atlas Cloud](https://www.atlascloud.ai/blog/tips/is-wan-3.0-open-source), [Wan2.2 GitHub](https://github.com/Wan-Video/Wan2.2)
- **LTX-2 / 2.3 / 2.5** (Lightricks) are open-weights models that generate video and audio together.
  - LTX-2.5 was released Aug 11, 2026: 22B parameters, up to 4K HDR.
  - AA text-to-video with audio: LTX-2.5 Fast has an Elo of 1068 (rank 24).
  - [S]. The license terms are **[U]**: I believe commercial use above a revenue threshold needs a Lightricks license, and this needs checking.
- **HunyuanVideo 1.5** (Tencent) is an 8.3B model.
  - **Its license excludes the EU, UK and South Korea.** Deployments above 100M monthly active users need Tencent's permission. [C] Source: [LICENSE](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5/blob/main/LICENSE)
- **MiniMax H3** has partially open weights: H3-Base, 33B dense, 768p only, released Aug 2, 2026.
  - **It is the best open-weights model on AA (Elo 1225, rank 4).**
  - **Its license excludes the US, EU, UK and South Korea, and requires permission above $20M in annual revenue.** For a US-facing subnet it is effectively unusable without a deal. [S] Source: [minimax-ai.chat](https://minimax-ai.chat/models/minimax-h3/)
- **MAGI-2 Preview** (Sand.ai) is open weights with an AA Elo of 1114. License **[U]**.
- **Quality gap:** the best *permissively licensed* open model (LTX-2.5, Elo about 1068) trails the frontier (about 1240) by about 170 Elo. Wan 2.2 no longer appears in AA's current top list. [C] Source: [AA](https://artificialanalysis.ai/video/leaderboard/text-to-video)

#### Hosted pricing for open video models

| Provider | Model | Price | 5s 720p equivalent | Conf. |
|---|---|---|---|---|
| **fal.ai** | Wan 2.2 A14B T2V/I2V | $0.08/s (720p), $0.06/s (580p), $0.04/s (480p); a video second is counted at 16 fps | **$0.40** | [C] [fal](https://fal.ai/models/fal-ai/wan/v2.2-a14b/text-to-video) |
| fal.ai | HunyuanVideo 1.5 | $0.075/s | $0.375 | [S] [fal](https://fal.ai/models/fal-ai/hunyuan-video-v1.5/text-to-video) |
| fal.ai | LTX-2 Fast | $0.04/s (1080p), $0.08/s (1440p), $0.16/s (4K) | about $0.20 (1080p) | [S] [fal](https://fal.ai/models/fal-ai/ltx-2/text-to-video/fast) |
| fal.ai | LTX-2 Pro | $0.06/s (1080p) | $0.30 | [S] |
| LTX official API | LTX-2.5 Fast | $0.09/s (720p), $0.13 (1080p), $0.30 (4K) | $0.45 | [S] [ltx.io](https://ltx.io/model/api/pricing) |
| LTX official API | LTX-2.5 Pro | $0.12/s (720p), $0.17/s (1080p) | $0.60 | [S] |
| **Replicate** | Wan 2.2 T2V **Fast** | $0.05 (480p) and **$0.10 (720p)** per video; about 30s per generation | **$0.10** | [C] [Replicate blog](https://replicate.com/blog/wan-22) |
| Replicate | Wan 2.2 I2V (not optimized) | $0.40 (480p), $1.00 (720p) per video | $1.00 | [C] |
| Replicate | HunyuanVideo (v1) | about $0.70–2.55 per run | – | [S] |
| **WaveSpeed** | Wan 2.2 720p | $0.40 per 5s; Ultra-Fast I2V 720p from $0.10; 5B 720p costs $0.05 | $0.10–0.40 | [S] [WaveSpeed](https://wavespeed.ai/collections/wan-2-2) |
| **SiliconFlow** | Wan2.2 T2V/I2V A14B | $0.29 per video | $0.29 | [S] [SiliconFlow](https://www.siliconflow.com/models/wan2-2-t2v-a14b) |
| **Novita** | Wan 2.1 T2V | about $0.30 per video | $0.30 | [S] [Novita](https://novita.ai/models/video/wan-2.1) |
| **Runware** | Various (2025 post) | from $0.14 per generation (Seedance Lite). Wan and LTX were "planned" at the time | – | [S] [Runware](https://runware.ai/blog/lowest-cost-ai-video-generation-now-on-runware) |
| **Chutes (SN64)** | Wan2.1-14B | Hosted, but no public per-video price found | ? | [C] docs exist [Chutes](https://chutes.ai/docs/examples/video-generation) |
| Together AI / DeepInfra / Fireworks | – | **No video-generation pricing found.** They appear focused on LLMs and images | – | [U] |
| OpenRouter | Wan 2.6/2.7 (closed), Wan 3.0 $0.0425/s | – | – | [C] |

**Market floor for open models:** $0.05–0.10 per 5s clip (Replicate "fast" and WaveSpeed ultra-fast use distilled models). **Standard list price:** $0.29–0.40 (fal, SiliconFlow, WaveSpeed).

#### GPU rental prices (per GPU-hour, on-demand)

| GPU | RunPod Community | RunPod Secure | Lambda | Others | Conf. |
|---|---|---|---|---|---|
| H100 PCIe | $1.99 | $2.89 | $3.29 (1x) | Vast.ai $1.49–1.87 | [C] [RunPod](https://www.runpod.io/pricing), [Lambda](https://lambda.ai/pricing); Vast [S] [IntuitionLabs](https://intuitionlabs.ai/articles/h100-rental-prices-cloud-comparison) |
| H100 SXM | $2.69 | $3.49 | $3.99 (8x) to $4.29 (1x) | AWS about $3.90; CoreWeave $6.16; Azure about $7 | [C]/[S] |
| H100 NVL | $2.59 | $3.19 | – | – | [C] |
| H200 | $3.59 | $4.59 | not listed | GCP a3-ultra about $10.60 | [C]/[S] |
| B200 | $5.98 | $6.79 | $6.69 (8x) to $6.99 (1x) | Spheron $6.02 | [C] |
| RTX 5090 | $0.69 | $0.99 | – | – | [C] |
| RTX 4090 | $0.34 | $0.74 | – | – | [C] |

**Confidential (TEE) GPUs cost more:**

| Provider | GPU | Price/hr | Notes | Conf. |
|---|---|---|---|---|
| **Phala Cloud** | H100 / H200 / B300 | $3.08 / $4.80 / $6.50 on demand; $2.38 / $3.20 / $5.60 reserved | Intel TDX plus NVIDIA CC, dual attestation, 24h minimum | [C] [Phala](https://phala.com/gpu-tee) |
| **Azure** NCC40ads H100 v5 | 1x H100 NVL | $8.90 on demand; $1.64 spot | AMD SEV-SNP plus H100 CC | [S] [Vantage](https://instances.vantage.sh/azure/vm/ncc40adsh100-v5) |
| **GCP** A3 confidential | H100 | not found | Intel TDX plus H100 protected PCIe; Ubuntu support announced Jun 2026 | [S] [Ubuntu](https://ubuntu.com/blog/ubuntu-confidential-vms-now-available-on-google-cloud-a3-with-nvidia-h100-gpus) |
| **Targon (SN4)** | H200 fleet | not public | 1,500+ H200s reported | [S] |

**TEE hardware constraint:** NVIDIA Confidential Computing works only on data-center Hopper and Blackwell GPUs (H100, H200, B200 and similar). It does not work on RTX 4090 or 5090. **[U: from memory, high confidence. Please verify against NVIDIA's CC support matrix. Some RTX PRO Blackwell server SKUs may support it.]** A TEE subnet therefore cannot use the cheapest consumer GPUs that some competitors run on.

**CC performance overhead:**
- For LLMs it is under 5–7% on average, and near zero for large, compute-bound models ([arXiv 2409.03992](https://arxiv.org/pdf/2409.03992), [Phala](https://phala.com/posts/confidential-computing-on-nvidia-h100-gpu-a-performance-benchmark-study)). [C]
- A Jul 2026 study found 17–21% lower throughput and 22–28% higher time-to-first-token (TTFT) for small models under TDX at a fixed request rate ([arXiv 2607.19353](https://arxiv.org/abs/2607.19353)). [S]
- **No diffusion or video benchmark was found.** Video DiT inference is heavily compute-bound, with little CPU-GPU traffic apart from weight loading, so overhead is *expected* to be low (about 5–10%). **[U]**

#### Generation speed

| Setup | Time for 5s 720p | Source | Conf. |
|---|---|---|---|
| Wan 2.2 A14B, stock settings (about 40–50 steps), 1x H100 SXM | about 10–12 min (480p: 4–5 min) | [Spheron](https://www.spheron.network/blog/deploy-wan-2-1-ai-video-generation-gpu-setup/) | [S] |
| Same, 1x H200 | about 8–10 min | Spheron | [S] |
| Wan2.2-I2V-A14B-720P baseline, RTX 5090 | 4,549 s | [TurboDiffusion](https://github.com/thu-ml/TurboDiffusion) | [C] |
| **Wan2.2-I2V-A14B-720P with TurboDiffusion (4 steps, SageAttention, sparse-linear attention (SLA), timestep distillation), RTX 5090** | **38 s** (about 120x faster) | TurboDiffusion. Apache-2.0; checkpoints "not finalized" | [C] |
| Wan2.1-T2V-14B 720p with TurboDiffusion, RTX 5090 | 24 s | same | [C] |
| Replicate Wan 2.2 "fast" | about 30 s per generation | [Replicate](https://replicate.com/blog/wan-22) | [C] |
| Wan 2.2 TI2V-5B, 720p, 1x RTX 4090 | under 9 min (stock) | [Wan2.2 README](https://github.com/Wan-Video/Wan2.2) | [C] |
| LightX2V 4-step distilled Wan 2.2 | "substantially reduced"; no numbers published | [HF](https://huggingface.co/lightx2v/Wan2.2-I2V-A14B-Moe-Distill-Lightx2v) | [S] |

#### Unit economics: cost per 5s 720p clip

Formula: `cost/clip = ($/GPU-hr × gen_seconds / 3600) × (1 + CC_overhead) / utilization`

| Scenario | $/hr | Gen time | CC overhead | Utilization | **Cost/clip** |
|---|---|---|---|---|---|
| A. Wan 2.2 A14B stock, H100 SXM, no TEE (RunPod Community) | 2.69 | 660 s | 0 | 100% | **$0.49** |
| B. Same on a TEE H100 (Phala on demand) | 3.08 | 660 s | 10% | 100% | **$0.62** |
| C. Distilled or TurboDiffusion-class, TEE H100 (Phala) — **[U] assumes about 40 s, like the RTX 5090 figure** | 3.08 | 40 s | 10% | 100% | **$0.038** |
| D. Same as C at 50% utilization | 3.08 | 40 s | 10% | 50% | **$0.075** |
| E. Same as C on a Phala reserved H100 at 60% utilization | 2.38 | 40 s | 10% | 60% | **$0.048** |
| F. Distilled on B200 TEE — **[U] assumes about 20 s** | 6.79 | 20 s | 10% | 60% | **$0.069** |
| G. Stock 50-step on an Azure confidential H100 | 8.90 | 660 s | 10% | 100% | **$1.79** |

**Implications**
- **With stock (undistilled) inference, a TEE clip costs about $0.50–0.60.** That is above fal's $0.40 retail price. Stock inference is not viable.
- **With few-step distilled or accelerated inference, cost is about $0.04–0.08 per clip.** At that cost we could price at $0.10–0.25 per 5s 720p clip, which is:
  - at or below the fast open-model hosts (Replicate $0.10, WaveSpeed $0.10);
  - well below fal ($0.40) and most closed APIs ($0.25–2.00);
  - while keeping a "private" premium.
- **Miners need batching, fast warm starts and high utilization.** Idle time is the biggest cost driver.
- **Distillation lowers quality.** The subnet must decide whether it sells "Wan 2.2 full quality" or "Wan 2.2 turbo". Clear SKUs per model and step count, like Replicate's "fast" SKUs, are advisable.
- **Emissions can subsidize early prices,** but see the Chutes lesson in Part B.

### A4. Confidential and private AI supply (who offers TEE gen-AI)

| Provider | Offering | Image/video? | Conf. |
|---|---|---|---|
| **Phala Cloud** | GPU TEE (TDX plus H100, H200, B300); dstack SDK; LLMs available on OpenRouter | No image or video mentioned | [C] [phala.com/gpu-tee](https://phala.com/gpu-tee) |
| **Confidential Inference Directory** (8 providers: Chutes, NanoGPT, NEAR AI, PPQ.AI, Privatemode, Redpill, Tinfoil, Venice) | TEE LLM inference with attestation | **"No image/video models listed"** | [C] [confidentialinference.net](https://confidentialinference.net/) |
| **Tinfoil** | Verifiable private AI with TDX and H100 CC; Red Hat collaboration | LLMs | [S] [tinfoil.sh](https://tinfoil.sh/) |
| **Fortanix Confidential AI** | NVIDIA CC for protecting model IP in enterprise "AI factories" (Mar 2026) | General, on-premises | [S] [Fortanix](https://www.fortanix.com/company/pr/2026/03/fortanix-confidential-ai-protects-proprietary-model-ip-and-data-for-secure-ai-inference-in-enterprise-ai-factories) |
| **Azure** | NCCads H100 v5 confidential VMs (GA) | General VMs | [C] [MS](https://techcommunity.microsoft.com/blog/azureconfidentialcomputingblog/general-availability-azure-confidential-vms-with-nvidia-h100-tensor-core-gpus/4242644) |
| **Google Cloud** | A3 confidential VMs (TDX plus H100) | General VMs | [S] |
| **Anjuna Seaglass** | Confidential runtime on Azure H100 | General | [S] |
| **Chutes (SN64)** | TEE live (announced on X around Dec 2025); TDX, SEV-SNP and protected PCIe | Hosts image and video models, but TEE coverage of video is **not confirmed** | [S] [X post](https://x.com/chutes_ai/status/1998411097783570552), [docs](https://chutes.ai/docs/core-concepts/security-architecture) |
| **Targon (SN4)**, **KubeTEE (SN90)**, **GM (SN28)** | Bittensor TEE compute and routing | No video product | see Part B |
| Opaque Systems | Confidential AI or data platform | Not researched (search budget) | [U] |

**Conclusion:** I found no provider marketing a *TEE-attested video-generation API* ("private video generation"). The confidential-inference market in 2026 is almost entirely LLMs. This is the core whitespace for us. **[C for the directory; S/U that nobody exists anywhere]**

Confidential-computing market size: **not retrieved** (search budget exhausted). **[U]**

### A5. Distribution channels

1. **OpenRouter Video API** (launched Apr 15, 2026). [C] Sources: [blog](https://openrouter.ai/blog/announcements/video-generation/), [collection](https://openrouter.ai/collections/video-models), [docs](https://openrouter.ai/docs/guides/overview/multimodal/video-generation)
   - It uses one unified asynchronous schema and a discovery endpoint at `/api/v1/videos/models`.
   - Launch models: Seedance 2.0/Fast/1.5 Pro, Veo 3.1, Wan 2.7/2.6, Sora 2 Pro.
   - The current list includes Seedance 2.0 Mini ($0.0336/s), Seedance 2.5 ($0.1028/s), Veo 3.1 Lite ($0.05/s), Veo 3.1 Fast ($0.10/s), Grok Imagine ($0.05/s), Wan 3.0 ($0.0425/s), and MiniMax H3 ($0.13/s) and H3 Max ($0.05/s).
   - Bittensor subnets already route **20–25% of their 100–120B tokens/day through OpenRouter**, and Chutes and Targon are OpenRouter providers ([KuCoin](https://www.kucoin.com/news/flash/bittensor-integrates-confidential-routing-layer-with-openrouter-processes-up-to-120-billion-tokens-daily)). [S]
   - **Becoming an OpenRouter video provider for open models, with a TEE/ZDR label, is the highest-leverage channel.** Whether OpenRouter accepts third-party providers for video models is **[U]**.
2. **Runway API as an aggregator.** Runway's developer API now resells wan3, seedance2/2.5, hailuo3/h3_max, veo3.1, grok_imagine, happyhorse and gemini_omni_flash ([Runway pricing](https://docs.dev.runwayml.com/guides/pricing/)). [C] Even closed labs are becoming distribution channels.
3. **ComfyUI.** [S] Sources: [Comfy pricing](https://comfy.org/pricing/), [Partner Node pricing](https://docs.comfy.org/tutorials/partner-nodes/pricing), [Cloud Nodes](https://comfy.org/cloud-nodes/)
   - "Partner Nodes" are paid API nodes (Kling, Luma, MiniMax H3 and others). All usage is paid in Comfy Credits: free 400/mo, Standard $20/mo for 4,200 credits, Creator $35, Pro $100.
   - "Comfy Cloud Nodes" run open models on Comfy's own GPUs.
   - Kling v1.5–2.1 nodes retire on Sep 15, 2026.
   - **A "Private Video (TEE)" custom node or partner node** would reach the power-user and creator base.
4. **fal, Replicate, WaveSpeed, Atlas Cloud, SiliconFlow, Novita, Runware.** These are mainly *competitors*.
   - Replicate and fal also host community-deployed models: Cog on Replicate, custom apps on fal.
   - Reseller aggregators (Kie.ai, EvoLink, CometAPI, Renderful, APIMart, Unifically, PoYo) resell at a discount and would onboard any cheap API.
5. **Cloud marketplaces.** 404-GEN's Atlas reaches enterprise studios through the Google Cloud Marketplace ([tao.media](https://www.tao.media/404-gen-sn17-introduces-atlas-to-bring-decentralized-3d-ai-into-enterprise-workflows/)). [S]
6. **Direct enterprise.** Target ad agencies, e-commerce catalog tools, and game and film pre-visualization studios with NDA-sensitive assets. Offer an attestation report per job as a compliance artifact.

---

## PART B: BITTENSOR SUBNETS RELATED TO VIDEO, IMAGE AND MEDIA (plus TEE compute)

Context: TAO = $241.12, TAO market cap $2.31B ([CoinGecko](https://www.coingecko.com/en/coins/bittensor), Sep 11, 2026). [C] The network has 128 subnet slots and deregistration has been live since Sep 17, 2025 ([docs](https://docs.learnbittensor.org/subnets/subnet-deregistration)). Subnet list cross-checked against [bittensor.co.in (2026)](https://bittensor.co.in/subnets/). The [taostats subnets.json](https://github.com/taostat/subnets-infos/blob/main/subnets.json) file is stale, with only 75 entries.

### B1. Media subnets

#### SN85 Vidaio: video upscaling and compression (the closest video-native subnet)
- **What it does:**
  - Phase 1 (live): AI super-resolution upscaling, for example HD to 4K.
  - Phase 2: AI compression.
  - Roadmap: streaming, transcoding, API and storage.
  - Recent partners: Manako AI; presence at IBC 2026.
  - [S] Sources: [TAO Desk, Apr 8, 2026](https://thetaodesk.substack.com/p/subnet-deep-dive-sn85-vidaio), [subnetstats](https://subnetstats.app/subnet/85)
- **Incentive mechanism** [C] (from the repo's [docs/incentive_mechanism.md](https://github.com/vidaio-subnet/vidaio-subnet)):
  - **Synthetic tasks:** the validator downscales a known clip, the miner upscales it, and the result is compared against the original (full-reference scoring).
  - **Organic tasks:** real user videos are split into chunks, processed by miners, and scored with ClipIQA+, a no-reference metric.
  - **Upscaling score:**
    - Quality score S_Q = normalized PIE-APP (4 consecutive frames from a random start, sigmoid-normalized), but only if VMAF (harmonic mean over frames) clears a threshold. Otherwise S_Q = 0.
    - Length score S_L = log(1+len) / log(1+320). Currently only 5s and 10s chunks are used.
    - Combined: S_pre = 0.5·S_Q + 0.5·S_L. Final score S_F = 0.1·e^(6.979·(S_pre − 0.5)), an exponential curve that gives about a 16x spread between weak and strong miners.
    - A rolling 10-round window applies a bonus (up to +15%) and penalties (up to −20% and −25%).
  - **Compression score:**
    - Compression rate C = compressed size / original size. Hard fail if C ≥ 0.8 or VMAF is below the threshold minus 5.
    - Above the threshold: 0.7 × compression component + 0.3 × quality component.
  - **Emissions:**
    - Top-5 miners per task pool split that pool equally; rank 6 and below gets 0.
    - Pools: 80% compression and 20% upscaling. Once a competition has finalized, the split becomes 60% compression, 20% upscaling and a 20% competition pool paid to the podium (70/20/10).
    - Optional alpha-stake weighting is off by default; burn is 0%.
    - The TAO Desk earlier reported rewards restricted to the top 50 keys.
- **Performance claim:** ClipIQA+ of 0.4697, vs 0.4658 for Topaz Video AI.
- **Market:** market cap about **$5.9M**, price $1.41 ([CoinGecko](https://www.coingecko.com/en/coins/vidaio)) [S]. Alpha price 0.0048 τ, pool 12.3k τ, 2,861 holders (subnetstats, Sep 10, 2026) [S].
- **Emission history:** emission share touched **zero twice** (Feb and late Mar 2026) before recovering above 2% [S].
- **Revenue:** not disclosed.
- **Lessons for us:**
  1. Reference metrics such as VMAF and PIE-APP work only when a ground-truth output exists. **Text-to-video has no ground truth**, so we need a different verification approach (see B3).
  2. An exponential score curve with top-K payouts creates a winner-take-most competition. That suits a model-improvement competition, but can starve an *inference-capacity* market that needs many miners online.
  3. Low revenue and a volatile emission share show the risk of a niche B2B product without distribution.

#### SN34 BitMind: deepfake and AI-media detection, with generative miners
- **Mechanism: "GAS" (Generative Adversarial Subnet)** [C] ([GitHub](https://github.com/BitMind-AI/bitmind-subnet)).
  - *Discriminative miners* submit detector models, one per hotkey in Safetensors format. They are scored by `sn34_score`, the geometric mean of normalized MCC and Brier scores.
  - Scoring runs as three independent tracks: image, video and audio.
  - *Generative miners* run servers that produce synthetic media for validator prompts. They earn a base reward for valid output, multiplied by how well their output performs against the detectors.
  - Datasets refresh weekly through "GAS-Station".
- **Performance** [S] ([cryptobriefing](https://cryptobriefing.com/bitmind-forensics-top-deepfake-detection/)): BitMind Forensics scores AUC 0.915 on Deepfake-Eval-2024 images and **0.822 on video**, vs 0.79 for the best commercial result.
- **Products:** apps, a browser extension and an API; enterprise KYC partnership with SN54 ([subnetalpha](https://subnetalpha.ai/subnet/bitmind/)).
- **Market cap:** about **$15.1M** ([CoinGecko](https://www.coingecko.com/en/coins/bitmind)). [C]
- **Lessons:**
  - BitMind already pays miners to *generate* synthetic video. Its generative miners are the closest existing "video generation" activity on Bittensor, but the output goes to adversarial datasets, not to customers.
  - **Partnership angle:** feed our outputs, with customer consent or on synthetic prompts only, into BitMind, or use BitMind detectors to check provenance.
  - **The validator checks "valid content to prevent gaming"**, a pattern worth borrowing.

#### SN17 404-GEN: text/image-to-3D (Gaussian splats and meshes)
- **Mechanism: "winner-stays" competition** [S] ([GitHub](https://github.com/404-Repo/404-gen-subnet), [SimplyTao](https://simplytao.ai/blog/what-is-404-gen-sn17-on-bittensor-simple-guide)).
  - Miners submit *open-source solutions* as Docker images.
  - Validators publish prompts and a seed. A **vision-language model (VLM) judges pairwise duels** between rendered outputs and the current leader.
  - **Validators audit winners by regenerating outputs from the miner's Docker image on serverless GPUs.**
  - All competition state lives in a public git repo.
- **Revenue:** Atlas (Apr 2, 2026) is an enterprise app layer with usage-based fees that flow back to the network. Square Enix tested it; it is sold through the GCP Marketplace ([tao.media](https://www.tao.media/404-gen-sn17-introduces-atlas-to-bring-decentralized-3d-ai-into-enterprise-workflows/)). [S]
- **Market cap:** about **$10.9M** ([CoinGecko](https://www.coingecko.com/en/coins/404-gen)). [S]
- **Lessons:**
  - **VLM pairwise preference plus reproducibility audits (seed plus pinned image)** is a proven template for judging generative quality without ground truth.
  - It also separates the "model competition" from the "serving layer" (Atlas).

#### SN24: formerly OMEGA Labs video dataset, **now Quasar**
- **Before:** OMEGA incentivized YouTube scraping into a video-caption dataset of 30M+ clips and 1M+ hours; it was the most-downloaded Hugging Face dataset in its size class ([GitHub](https://github.com/omegalabsinc/omegalabs-bittensor-subnet)).
- **Now:** SN24 is **Quasar** (long-context models and a training marketplace; Quasar-3B, Apr 2026) ([taostats chart "SN24 · Quasar"](https://taostats.io/subnets/24/chart), [KuCoin](https://www.kucoin.com/blog/sn24-quasar-3b-architecture-how-bittensor-tao-challenges-openai-in-long-context-ai)). [S]
- **Lesson:** a dataset-only subnet with weak monetization did not keep its slot or mission.

#### SN19 Nineteen (Rayon Labs): image generation and LLM inference at scale
- Miners are rewarded for speed and correctness on image and text tasks (SDXL-class models, inpainting, upscaling). Validators sell access through API keys, with query allocation proportional to stake ([bittensor123](https://bittensor123.com/subnets/sn19/)). [S]
- Emission share was about 4.77% in Jan 2026 ([Subnet Edge](https://subnetedge.substack.com/p/maestro-strategy-note-012926)). [S/U]
- Rayon Labs also runs Chutes (SN64).
- **Lesson:** a stake-proportional validator-access model is a simple way to monetize.

#### SN23 SocialTensor / NicheImage: image generation scored on prompt accuracy
- Status in 2026 is **unclear**. It is still listed on learnbittensor and bittensor123, but not in the bittensor.co.in media list. **[U]**

#### Other media-adjacent subnets (brief)
- **SN44 Score:** sports computer vision; video frames turned into analytics. Targon customer. [S from list]
- **SN20 ChronoSeek:** semantic video moment retrieval. Miners return timestamps and are scored by IoU against ActivityNet Captions ([GitHub](https://github.com/chronoseek/bittensor-subnet); the repo shows testnet netuid 298, while bittensor.co.in lists SN20). [S]
- **SN93 Bitcast:** pays YouTube creators based on engagement for brand deals. [S from list]
- **SN32 It's AI:** AI-text detection.
- **SN59 Babelbit:** voice translation. **SN78 Vocence:** text-to-speech and voice.
- **TalkHead subnet** (GitHub; netuid 108 is used as an example; mainnet status **unverified**):
  - Talking-head (lip-sync) video generation. Miners submit Dockerized models pinned by `sha256` digest. Validators run them on CelebAHQ faces plus LibriSpeech audio.
  - **It scores latency, not perceptual quality. No TEE.** ([GitHub](https://github.com/talkheadai/talkhead-subnet)). [C repo / U status]
  - It is the only "video generation" subnet found, and it is narrow in scope.

### B2. TEE / compute subnets (potential supply partners or adjacent competitors)

#### SN64 Chutes (Rayon Labs): serverless open-model inference, with TEE
- **Catalog:** runs any open model, including image models (FLUX.1 Dev, HiDream, Qwen Image, Hunyuan Image 3) and **Wan2.1-14B video (T2V/I2V, up to 720p)** ([docs](https://chutes.ai/docs/examples/video-generation)). [C]
- **TEE:** live, using TDX and SEV-SNP plus NVIDIA protected PCIe ([X](https://x.com/chutes_ai/status/1998411097783570552), [security docs](https://chutes.ai/docs/core-concepts/security-architecture)). [S]
- **Market cap:** **$100.3M** ([CoinGecko](https://www.coingecko.com/en/coins/chutes)). [C]
- **Economics** [S] ([OwnYourMind / Pine Analytics](https://ownyourmind.ai/tokenomics/chutes-bittensor-revenue-machine/)):
  - External revenue independently verified at **$1.3–2.4M annualized** (Mar 2026). The team claims ARR "approaching $10M" (Apr 2026).
  - Emissions about **518 TAO/day, 14.39% of all emissions**. **The subsidy is 22–40x customer revenue.**
  - Its unsubsidized break-even is about $1.41 per 1M tokens, vs Together's $0.88.
  - The team admitted heavy users extracted 56–324x their subscription value.
- **Threat:** **Chutes is the most dangerous adjacent competitor.** It already has a TEE, video models and OpenRouter distribution, and could launch "Wan 2.2 in TEE" quickly. What protects us:
  - video-specific optimization (distillation, batching, SKUs);
  - per-job attestation receipts;
  - quality scoring;
  - an enterprise-privacy go-to-market.
- **Lesson:** do not build a business where emissions pay 20–40x revenue. Design for revenue that is recycled into alpha buybacks and burns, and plan for halvings.

#### SN4 Targon (Manifold Labs): confidential GPU compute cloud
- **TEE design:**
  - The Targon Virtual Machine runs on Intel TDX (or AMD SEV-SNP) with NVIDIA CC on Hopper and Blackwell GPUs.
  - Intel co-authored a whitepaper (Mar 23, 2026).
  - **Re-attestation every 72 minutes.** Auction-based pricing.
  - [S] Sources: [tao.media](https://www.tao.media/targon-and-intel-release-whitepaper-on-confidential-compute-for-decentralized-ai/), [CoinGecko](https://www.coingecko.com/en/coins/targon)
- **Scale:** 1,500+ GPUs, mostly H200. Tower Pro is an 8-GPU TDX workstation from $57.5k (reservations opened Jun 2, 2026) ([tao.media](https://www.tao.media/what-is-targon-tower-pro/)).
- **Economics** [S] ([OwnYourMind](https://ownyourmind.ai/tokenomics/targon-bittensor-confidential-compute/)):
  - Self-reported ARR is **$10.4M** (unaudited). Emission-to-revenue ratio about 1.7:1. Emission share about 5.73%.
  - Customers: Dippy, Ridges and Score. No named enterprise customers.
  - The orchestration layer is closed-source.
- **Market cap:** **$79.2M** ([CoinGecko](https://www.coingecko.com/en/coins/targon)). [C]
- **Lessons:**
  - Attestation freshness (periodic re-attestation) and dual CPU+GPU quotes are table stakes.
  - Closed orchestration draws criticism.
  - **Our miners could run on Targon or Phala hardware.** Alternatively, we could require miners to bring their own TDX+CC hosts.

#### SN90 KubeTEE: confidential Kubernetes (Kata and Confidential Containers)
- **Attestation is mandatory:** "no attestation means no emissions" (TDX/SGX plus NVIDIA CC, CoCo Trustee).
- Pricing is benchmarked against Targon, Lium and Chutes.
- **No video workloads** ([GitHub](https://github.com/KubeTEE-AI/kubetee-subnet)). [C]

#### SN28 GM: TEE gateway and marketplace for LLM inference
- Buyers send OpenAI/Anthropic/Gemini-style requests to a TEE gateway. Miners proxy them from inside TDX, and validators score miners from signed usage logs.
- Integrated with OpenRouter (May 30, 2026) ([KuCoin](https://www.kucoin.com/news/flash/bittensor-integrates-confidential-routing-layer-with-openrouter-processes-up-to-120-billion-tokens-daily), [demo](https://demo.saygm.com/)). [S]
- **Lesson:** scoring from *signed usage logs* ties rewards to organic demand.

#### SN53 engy (Hanlin AI): "verified inference"
- Provides cryptographic proof that the exact open model requested actually ran, not a quantized substitute ([GitHub](https://github.com/hanlinai/engy), [tao.media](https://www.tao.media/is-engy-the-breakout-subnet-bittensor-has-been-waiting-for/)). [S]
- **Directly relevant:** customers will ask us to prove that "Wan 2.2 at 40 steps" ran, not a 4-step distilled model.

#### Other compute subnets
SN12 ComputeHorde, SN27, SN46 Instant (GPU inference), SN51 Lium, SN106 Nodexo, SN110 Green Compute, SN128 Byteleap ([bittensor.co.in](https://bittensor.co.in/subnets/)). [S]

### B3. Is there an existing TEE video-generation subnet?

**No, based on everything I checked.** [S]

What I checked:
- the 2026 subnet list on bittensor.co.in;
- the (stale) taostats subnet JSON;
- GitHub searches;
- the Confidential Inference Directory;
- the TEE subnets (Targon, KubeTEE, GM, Chutes).

What I found:
- **No mainnet subnet** does general text-to-video or image-to-video generation as its core commodity.
- **No subnet or provider** offers TEE-attested video generation as a product.

The closest things are:
1. **Chutes**, which hosts Wan 2.1 and has a TEE, as a generic platform;
2. **BitMind's generative miners**, which make synthetic media for adversarial training;
3. **TalkHead**, a narrow lip-sync subnet, likely not on mainnet, with no TEE;
4. **Vidaio**, which does post-processing rather than generation.

### B4. Competitive gap analysis and design lessons

**The gap:**
- Private, attested, open-model video generation for enterprises that cannot send assets to Google, OpenAI, Kuaishou or ByteDance.
- Also for creators who want no logging and no training on their inputs.

**Our advantages:**
- **TEE attestation receipts per job:** a compliance artifact that neither fal nor Replicate offers.
- **Decentralized H100/H200/B200 supply.**
- **Emissions to bootstrap price.**
- **Model neutrality:** Apache-licensed Wan 2.2 and LTX, and possibly a MiniMax H3 deal later.

**Our disadvantages and risks:**
1. **Quality gap.** Permissively licensed open models sit about 170 Elo below frontier closed models. The best open model (MiniMax H3) is *license-excluded in the US and EU*, and HunyuanVideo 1.5 in the EU, UK and South Korea. Privacy has to compensate for the quality gap. Fine-tunes and LoRAs, and bring-your-own-model in TEE, can help.
2. **Price floor.** TEE rules out consumer GPUs [U] and adds 5–20% overhead. Distilled inference on data-center GPUs still lands at about $0.04–0.08 per clip, which is competitive.
3. **Chutes or Targon could copy us.** Our moats would be video-specific quality scoring, SKUs and enterprise go-to-market.
4. **Emissions dependence** (the Chutes lesson). Plan revenue buybacks from day one.
5. **Licensing and compliance.** Deepfake and NSFW policy; TEE privacy vs. abuse monitoring. Consider client-side C2PA or watermarking and policy checks inside the enclave.

**Verification design suggestions** (from the subnets above):
- **Attestation-first:** TDX quote plus GPU CC quote, bound to a pinned container and model digest (Targon, KubeTEE, engy). This proves *which* model and code ran and removes most of the need to re-run jobs.
- **Seeded reproducibility audits:** a validator re-runs a sample of synthetic jobs with the same seed and model and compares the output with a perceptual tolerance, for example LPIPS, SSIM or embedding similarity, because GPU nondeterminism rules out bit-exact matches (404-GEN's audit pattern).
- **Quality scoring without ground truth:**
  - VLM pairwise judging (404-GEN);
  - CLIP/X-CLIP prompt alignment;
  - VBench or VideoScore-style metrics;
  - no-reference quality metrics, like Vidaio's ClipIQA+ for organic jobs;
  - optionally, a human-preference arena.
- **Score throughput and latency too** (Nineteen, TalkHead), but gate them on quality thresholds, like Vidaio's VMAF gate.
- **Organic-demand weighting:** score from signed usage logs (GM).
- **Avoid pure top-5 winner-take-all for a serving market.** Vidaio's design suits competitions; a capacity market needs broader, capacity-weighted rewards.
- **Consider two tracks, like Vidaio's split and 404-GEN's competition-plus-audit:**
  - (a) a *serving* track paid by attested capacity × quality × organic volume;
  - (b) a *model or optimization competition* track for faster distilled pipelines, with the winning pipeline adopted network-wide.

---

## Items to verify later (search budget exhausted)
- The Kling credit-to-USD rate ($1 = 66 credits) and the official Kling developer pricing page.
- Whether consumer RTX GPUs support NVIDIA CC. The expected answer is no; check NVIDIA's CC documentation.
- CC overhead for diffusion and video DiT workloads (no benchmark found).
- The LTX-2.x open-weights commercial license threshold, and the MAGI-2 license.
- Whether OpenRouter accepts third-party providers for video models.
- Chutes' video pricing, and whether Chutes TEE covers image and video chutes.
- SN23 SocialTensor's current status; details for SN44, SN93 and SN20; emission shares for the media subnets. Taostats pages are JavaScript-rendered and could not be fetched.
- Confidential computing market size (not retrieved).
- H100 or B200 timings for TurboDiffusion or LightX2V distilled Wan 2.2. Only RTX 5090 numbers are published; the H100 figures above are extrapolated.
