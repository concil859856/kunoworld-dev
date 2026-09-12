# Research: Model Selection for a TEE-Secured Video-Generation Bittensor Subnet

Research date: 2026-09-11. All web sources were fetched on this date unless noted.

Legend:
- **[CONFIRMED]**: verified on a primary source (official HF repo / license file / official blog / GitHub repo / Artificial Analysis page).
- **[SECONDARY]**: from reputable secondary sources (ComfyUI Wiki, cloud-provider blogs, arXiv abstracts), not cross-checked on a primary source.
- **[UNVERIFIED]**: single low-trust source, conflicting reports, or from prior knowledge that was not re-checked.

Warning: many sites rank for "Wan 2.7 open source", "HappyHorse open weights" and similar queries. They are SEO pages with no official release behind them. One analysis says so explicitly ([localaimaster.com](https://localaimaster.com/blog/wan-2-7-open-source)). Only official org pages were trusted for open-weight status.

---

## 0. TL;DR

1. **The user's "MiniMax H3" is real, and it IS open-weight.** MiniMax H3, also called "Hailuo 3.0" or "Hailuo 03", launched July 31, 2026 ([MiniMax blog](https://www.minimax.io/blog/minimax-h3)). Weights went up on Hugging Face in early August 2026 at [`MiniMaxAI/MiniMax-H3`](https://huggingface.co/MiniMaxAI/MiniMax-H3). It is a 33B dense transformer with native stereo audio. It is **the #1 open-weights model** on the Artificial Analysis T2V and I2V arenas. **[CONFIRMED]**
2. **The license is the problem for Bittensor.** The MiniMax H3 Community License (dated Aug 2, 2026) **excludes the USA, EU, UK and South Korea**. It says: *"You may not use, reproduce, modify, distribute, or display the MiniMax H3 Works or any of their Outputs or results outside the Applicable Territory."* It also:
   - requires written authorization above $20M yearly revenue,
   - requires a visible "MiniMax H3" attribution in the UI,
   - bans using Outputs to improve any other AI model.
   ([LICENSE](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE)) **[CONFIRMED]**
   A permissionless, global miner set cannot comply unless MiniMax grants a separate authorization. The model card lists an "Application form (only for USA/EU/UK/South Korea)".
3. **The open release is not the full product.** The open checkpoints generate **768p natively**. The 2K path (H3-Regenerate-2K) and the multimodal preprocessor (H3-Context-IR) are **not open-sourced** and are API-only ([GitHub MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3)). **[CONFIRMED]**
4. **Earlier Hailuo models (Hailuo 01 / 02 / 2.3) were closed and API/app-only.** Hailuo 02 (June 18, 2025) was announced for web, app and API only, with no weights ([MiniMax news](https://www.minimax.io/news/minimax-hailuo-02)). **[CONFIRMED]**
5. **Best license-clean open alternatives (Sept 2026):**
   - **MAGI-2 Preview** (Sand.ai, Apache-2.0, 114B MoE / 6B active, 1080p, 10s, audio, 8x Hopper; #2 open-weights on AA)
   - **LTX-2.5** (Lightricks, 22B, audio, distilled 8-step, single GPU; LTX-2.x Community License is free under $10M revenue and allows SaaS hosting)
   - **Wan 2.2** (Apache-2.0, mature ecosystem, but older, no audio, 720p/5s)
   - Wan 2.5 through 3.0 and HappyHorse are **not** open-weight.
6. **Determinism:** bitwise reproducibility of diffusion video inference is achievable only under tight conditions: same GPU SKU, same GPU count and parallel layout, pinned software image, deterministic kernels, no autotuning, and no data-dependent caching. TEE attestation of the container image is a natural fit for pinning the stack. MAGI-2 ships an explicit `MAGI2_DETERMINISTIC=1` bit-exact mode **[CONFIRMED]**. The best verification design is per-step latent commitments plus random single-step re-execution, not full re-runs.

---

## 1. MiniMax video lineup and other MiniMax open models

### 1.1 Video models

| Model | Release | Access | Key specs | Source |
|---|---|---|---|---|
| Video-01 / I2V-01 / T2V-01 ("Hailuo 01") | 2024 | API/app only | 720p, ~6s | [UNVERIFIED, prior knowledge] |
| Hailuo 02 | 2025-06-18 | **API/app only** | 768p 6s/10s, 1080p 6s; "Noise-aware Compute Redistribution (NCR)" architecture; about 3x the params of its predecessor | [MiniMax news](https://www.minimax.io/news/minimax-hailuo-02) **[CONFIRMED: no open-source statement; "integrated into the Hailuo Video web platform, mobile application, and our API platform"]** |
| Hailuo 2.3 | late 2025 | API only | (not researched in depth) | [minimax-ai.chat](https://minimax-ai.chat/models/minimax-hailuo-23/) [UNVERIFIED] |
| **MiniMax H3 (Hailuo 3.0 / "Hailuo 03")** | announced 2026-07-31; weights early Aug 2026 | **Open weights (restricted license)** + API | See 1.2 | [MiniMax blog](https://www.minimax.io/blog/minimax-h3), [HF](https://huggingface.co/MiniMaxAI/MiniMax-H3) **[CONFIRMED]** |
| "H3 Max" | Aug 2026 | Closed (fal post-trained) | Listed on AA as "Minimax H3 Max (post-trained by fal)", not open | [AA T2V](https://artificialanalysis.ai/video/leaderboard/text-to-video), [OpenRouter](https://openrouter.ai/minimax/hailuo-3-max) **[CONFIRMED on AA]** |

The official blog's July 31 wording was: *"We plan to open up the model weights in the coming days, subject to applicable laws and regulations."* **[CONFIRMED]**

### 1.2 MiniMax H3 details

**Architecture:** **[CONFIRMED, HF card / GitHub]**
- "H3-Omni-Transformer", a **33B-parameter dense, single-stream Transformer**.
- About 13B of those parameters sit in AdaLN branches, which can be cached or precomputed for inference-only use.
- Text/multimodal encoder: **Qwen3VL-32B** (48 GB BF16; INT8 and NVFP4 variants exist) ([ComfyUI Wiki](https://comfyui-wiki.com/en/news/2026-08-03-minimax-h3-open-weights-comfyui)) **[SECONDARY]**.
- Separate video VAE (4.9 GB) and audio VAE (0.6 GB).

**Checkpoints (BF16):** **[CONFIRMED]**
- **FL2VA**: text-to-video, first-frame, last-frame and first+last-frame modes. About 61.7 GB BF16.
- **Ref2VA**: omni-reference mode (≤9 images, ≤3 video clips, ≤3 audio clips, ≤12 files total).
- CFG-distilled weights were released.

**Output:** **[CONFIRMED on HF card]**
- 4 to 15 seconds, 24 fps.
- Stereo audio at 32 kHz.
- Default 768p (short side 768).
- Aspect ratios 21:9, 16:9, 4:3, 1:1, 3:4, 9:16.
- "Up to 2K" only with the non-open H3-Regenerate-2K stage.

**Not open:** **[CONFIRMED, GitHub]**
- **H3-Regenerate-2K** ("Due to the complexity of the system, this module is not yet open-sourced").
- **H3-Context-IR** (multimodal preprocessing, API only).

**Frameworks:** **[CONFIRMED]**
- Diffusers, SGLang, vLLM (vLLM-Omni) and ComfyUI.
- Official SGLang recipe: `sglang serve --model-path MiniMaxAI/MiniMax-H3 --num-gpus 4 --ulysses-degree 4 --performance-mode speed --model-variant fl2va`.

**Hardware and speed** (test conditions: 5 s, 50 steps, 1344x768, per [Spheron](https://www.spheron.network/blog/deploy-minimax-h3-gpu-cloud/)) **[SECONDARY]**:

| Setup | Precision | Peak VRAM/GPU | Time per clip |
|---|---|---|---|
| 4x H200 | BF16 | 94.3 GB | 74.38 s end-to-end |
| 4x H100 | BF16 | 66.04 GB | "13.25 s pipeline latency" (inconsistent with the H200 figure; treat as **[UNVERIFIED]**) |
| 8x B300 | FP8 | not given | 18.03 s |
| 8x B300 | BF16 | not given | 19.04 s |
| 1x MI355X | BF16 | 137.7 GB | 313 s |
| 2x RTX 5090 + offload | BF16 | not given | ~560 s |

- SGLang Cache-DiT profiles on 4x H200: 75.10 s lossless, then 53.70 s, 30.23 s and 25.81 s at more aggressive settings (search summary of SGLang recipes) **[SECONDARY]**.
- vLLM-Omni online FP8 at 768x448: 152.9 s warm, 80.6 s with Cache-DiT. **Quality vs BF16: SSIM 0.881, PSNR 26.6 dB.** This is a useful calibration for how far FP8 drifts from BF16 ([awesome-minimax-H3 perf guide](https://github.com/wildminder/awesome-minimax-H3/blob/main/guides/minimax-h3-performance.md)) **[SECONDARY]**.
- Full BF16 bundle is about 123.6 GB. Pruned INT8 plus NVFP4 text encoder is about 42.5 GB.

**Acceleration** **[CONFIRMED that the repos exist]**:
- LightX2V / ModelTC released **4-step and 8-step "Turbo" distills** in early August 2026: [lightx2v/Minimax-h3-Turbo](https://huggingface.co/lightx2v/Minimax-h3-Turbo), [lightx2v/Minimax-h3-Turbo-SLA](https://huggingface.co/lightx2v/Minimax-h3-Turbo-SLA) (sparse-linear attention), [GitHub ModelTC/Minimax-H3-Turbo](https://github.com/ModelTC/Minimax-H3-Turbo).
- Default sampling is about 20 steps in ComfyUI; the 4-step LoRA gives about a 3.4x to 5x speedup.
- Note: the license forbids using H3 Outputs to improve other models, but distills of H3 itself count as "Model Derivatives". These LoRAs are therefore H3 derivatives and stay bound by the H3 license.

**Rankings** (Artificial Analysis, fetched 2026-09-11; Elo values move over time) **[CONFIRMED]**:
- [T2V leaderboard](https://artificialanalysis.ai/video/leaderboard/text-to-video), default view: Wan 3.0 1242 (closed) > Gemini Omni Flash 1238 > H3 Max (fal) 1232 > **MiniMax H3 1225 (open)** > Seedance 2.0 720p 1220.
- A separate search snapshot of AA reported H3 leading open-weights **without audio at Elo 1302** and **with audio at 1228** (AA runs separate audio and no-audio arenas).
- [I2V leaderboard](https://artificialanalysis.ai/video/leaderboard/image-to-video): H3 Max 1206 > Seedance 2.0 1196 > **MiniMax H3 1190 (open)** > HiDream-O1-Video 1186 > Gemini Omni Flash 1180 > Wan 3.0 1178.

**API pricing** **[SECONDARY]**: about $0.13/s at 2K and $0.09/s at 768p (768p reported as closed beta) ([MiniMax pricing docs](https://platform.minimax.io/docs/guides/pricing-video), [EvoLink](https://evolink.ai/hailuo-3)). AA lists $7.80/min for MiniMax H3.

### 1.3 MiniMax H3 Community License: key clauses

Source: [LICENSE, dated August 2, 2026](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE). Quotes below are verbatim. **[CONFIRMED]**

- **Territory:** "'Applicable Territory' means worldwide, excluding the Excluded Territories." and "'Excluded Territories' means the European Union, the United Kingdom, the Republic of Korea and the United States of America."
- **Use restriction:** "You may not use, reproduce, modify, distribute, or display the MiniMax H3 Works or any of their Outputs or results outside the Applicable Territory."
- **Revenue threshold:** separate prior written authorization is required "if your commercial products and services generate more than 20 million US dollars … in yearly revenue" (contact api@minimax.io).
- **Attribution:** "You must prominently display 'MiniMax H3' on the user interface of commercial product or service that uses MiniMax H3 or MiniMax H3 Works."
- **No output-based training of other models:** "You may not use the MiniMax H3 Works or any of their Outputs or results to improve any other artificial intelligence model (other than MiniMax H3 or its Model Derivatives)."
- **Hosted services:** anyone who makes H3 generation available to third parties must "implement, maintain, test, and periodically review reasonable and proportionate technical and organizational safeguards" against violations of Section V (Use Restrictions) and Exhibit A (Acceptable Use Policy).
- **Derivatives:** "Model Derivatives" includes "any other machine learning model created by transferring the patterns of weights, parameters, operational patterns, or Outputs".
- **Governing law:** Hong Kong SAR.
- **Termination:** on any breach.

**What this means for a Bittensor subnet:**
1. Miners located in the US, EU, UK or Korea cannot lawfully run the weights. That is a large share of the world's TEE-capable H100/H200/B200 capacity.
2. Validators in those regions cannot lawfully re-run H3 for spot checks.
3. The "Outputs … display" clause arguably bars serving generated videos to end users in those regions via locally-hosted weights. MiniMax's own hosted API stays globally available ([explainx.ai](https://explainx.ai/blog/minimax-h3-open-video-model-hailuo-july-2026)) **[SECONDARY]**.
4. The subnet cannot use H3 outputs as training data for any non-H3 model (for example, a subnet-owned model).
5. TEE attestation proves code and hardware identity, not geography. A permissionless subnet cannot enforce the territory restriction technically.
6. A lawful path exists: a written authorization from MiniMax covering the network. The HF card links an application form for USA/EU/UK/South Korea. Contacts: model@minimax.io and api@minimax.io.

**Legal review needed. This is not legal advice.**

### 1.4 Other MiniMax open models

Source: [HF MiniMaxAI org](https://huggingface.co/MiniMaxAI) (21 models).

| Model | Type | License | Notes |
|---|---|---|---|
| MiniMax-Text-01 / VL-01 (Jan 2025) | LLM, 456B MoE | "MiniMax Model Agreement" | [UNVERIFIED, prior knowledge] |
| MiniMax-M1 (Jun 2025) | Reasoning LLM | Apache-2.0 | [UNVERIFIED, prior knowledge] |
| MiniMax-M2 / M2.1 / M2.5 (Oct 2025 to Mar 2026) | LLM, 229B MoE | HF tag shows **"modified-mit"**; model card text says "MIT". Some secondary sources say plain MIT with no attribution ([layer3labs](https://www.layer3labs.io/guides/minimax-explained)). | [HF M2](https://huggingface.co/MiniMaxAI/MiniMax-M2), [HF M2.5](https://huggingface.co/MiniMaxAI/MiniMax-M2.5). **[CONFIRMED tag; exact terms UNVERIFIED]** |
| MiniMax-M2.7 (Apr 2026) | LLM | **Modified-MIT, effectively non-commercial**: prior written authorization needed for any commercial use; "Built with MiniMax M2.7" attribution. Changed after release, which caused community backlash. | [LetsDataScience](https://letsdatascience.com/news/minimax-revises-license-after-releasing-m27-weights-04b47c74), [HF discussion](https://huggingface.co/MiniMaxAI/MiniMax-M2.7/discussions/5) **[SECONDARY]** |
| MiniMax-M3 (Jul 2026) | Multimodal LLM, ~428B total / ~23B active | **"MiniMax Community License"**: >$20M yearly revenue needs authorization; below that a one-time notice email; "Built with MiniMax M3" attribution; no territory exclusion found | [HF M3 LICENSE](https://huggingface.co/MiniMaxAI/MiniMax-M3/blob/main/LICENSE) **[CONFIRMED via fetch summary]** |
| MiniMax-Music3 (Aug 2026) | Music generation, up to 5 min, 32 kHz stereo | License not determined | [HF](https://huggingface.co/MiniMaxAI/MiniMax-Music3) **[UNVERIFIED license]** |
| Speech-02 / Speech 2.x | TTS | **Closed, API only** | [MiniMax news](https://www.minimax.io/news/minimax-speech-02) **[SECONDARY]** |
| VTP-Base/Large | Image feature extraction | not checked | HF org |

**Pattern:** MiniMax's licenses have moved from permissive (MIT/Apache) toward restrictive "community" licenses. These add revenue thresholds, attribution and, for H3, territory exclusions. Expect H3 terms to stay restrictive or get stricter.

---

## 2. Open-weight video generation models as of September 2026

### 2.1 Status of the "famous" names (open vs. closed)

| Family | Latest **open** | Latest overall | Evidence |
|---|---|---|---|
| Alibaba Wan | **Wan 2.2** (Jul 2025, Apache-2.0), plus Wan2.2-Animate-2 (Aug 2026) and Wan-Dancer-14B (Jul 2026) | Wan 3.0 (API public beta 2026-08-06; #1 on AA T2V); Wan 2.7 (Jun 2026) | [HF Wan-AI org](https://huggingface.co/Wan-AI) shows **no Wan 2.5/2.6/2.7/3.0 video models** **[CONFIRMED]**. Wan 2.5 was announced as open but never shipped; Wan 2.6 is closed ([wan27.org](https://wan27.org/blog/wan-2-6-open-source-guide), [atlascloud](https://www.atlascloud.ai/blog/tips/is-wan-3.0-open-source), [wavespeed](https://wavespeed.ai/blog/video-model-access/is-wan-3-0-open-source/)). **AA lists Wan 3.0 / 2.7 / 2.6 as not open** **[CONFIRMED]** |
| Alibaba-ATH HappyHorse 1.0/1.1 | none | HappyHorse-1.1 (Jun 2026) | Many "open-source" claim sites, but AA marks it as **not open weights**; weights not published ([rctv.com](https://rctv.com/posts/happyhorse-open-source-claim/)) **[CONFIRMED on AA]** |
| Tencent Hunyuan | HunyuanVideo 1.5 (Nov 2025) | same | [GitHub](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5). No "HunyuanVideo 2.0" found **[CONFIRMED]** |
| Lightricks LTX | **LTX-2.5** (Aug 2026) | same | [HF Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5) **[CONFIRMED]** |
| Sand.ai MAGI | **MAGI-2 Preview** (Aug 5, 2026) | same | [HF sand-ai/MAGI-2-preview](https://huggingface.co/sand-ai/MAGI-2-preview) **[CONFIRMED]** |
| Skywork SkyReels | SkyReels V2 / V3 (older) | SkyReels V4 (closed on AA) | AA **[CONFIRMED V4 closed]**; V2/V3 openness [UNVERIFIED] |
| Kling, Veo, Sora, Seedance, Vidu, PixVerse, Gemini Omni | none | closed | AA |

### 2.2 Comparison table (open-weight candidates)

| Model | Params | License (commercial?) | Output | Audio | AA open-wts Elo (T2V / I2V) | VRAM / GPUs | Speed (reported) | Accel / serving |
|---|---|---|---|---|---|---|---|---|
| **MiniMax H3** (FL2VA, Ref2VA) | 33B dense + Qwen3VL-32B encoder | **MiniMax H3 Community**: excludes US/EU/UK/KR; >$20M needs auth; attribution; no output→other-model training **[CONFIRMED]** | 768p native (2K closed), 4–15 s, 24 fps | Yes, stereo 32 kHz | **1225 / 1190** (#1 open) | Official: 4x H100/H200 BF16 (66–94 GB/GPU); community INT8/NVFP4 on 1 GPU | ~74 s per 5 s 1344x768 50-step on 4x H200; ~18 s on 8x B300 FP8 [SECONDARY] | SGLang (Ulysses SP, Cache-DiT), vLLM-Omni, diffusers, ComfyUI; LightX2V 4/8-step Turbo |
| **MAGI-2 Preview** (Sand.ai) | 114B MoE, ~6B active; Qwen3.5-27B text encoder | **Apache-2.0** (commercial OK) **[CONFIRMED]** | 1080p (512x896 preview → 1088x1920 refiner), **10 s only** | Yes (joint) | **1114 / 1101** (#2 open) | **8x Hopper** required; repo ~307 GB | 100 preview steps + 5 refiner steps, **not step-distilled** (distill "coming soon"); wall time not published | Custom PyTorch (torchrun). **`MAGI2_DETERMINISTIC=1` makes "the MoE scatter and the attention kernels bit-exact at some cost in speed"** **[CONFIRMED, GitHub]** |
| **LTX-2.5** (Lightricks) | 22B asymmetric dual-stream DiT + Gemma 4 12B encoder | **LTX-2.x Community License**: free for entities <$10M annual revenue (affiliates aggregated); paid above that; **SaaS hosting for third parties allowed**; no claim on outputs; AUP **[CONFIRMED for LTX-2 license text; LTX-2.5 card says "LTX-2.x Community License"]** | Stage 1 544x960, x2 upscale; up to 4K HDR; 24 fps (up to 50); multishot; `num_frames % 8 == 1` | Yes | **1068 (Fast) / 1059 (Pro)**; I2V 1050 / 1011 | Distilled BF16 ~66 GB on disk; 80–96 GB recommended for BF16 distilled; 32–48 GB with INT8/FP8; 16–24 GB quantized | **10 s clip in 6.8 s on 2x GB200** (vendor claim, [VentureBeat](https://venturebeat.com/technology/ltx-2-5-can-generate-a-10-second-ai-video-from-an-image-in-just-6-8-seconds-on-nvidia-superchips-and-its-open-weights), [Runpod](https://www.runpod.io/blog/ltx-2-5-the-open-weights-world-model-built-for-speed-and-how-to-run-it-on-runpod)); distilled 8 steps | ltx-pipelines (PyTorch), diffusers (`LTX-2.5-Diffusers`), ComfyUI; FP8-cast, fp8-scaled-mm (Hopper), NVFP4 |
| LTX-2 / LTX-2.3 | 19B (14B video + 5B audio) | LTX-2 Community (Jan 5, 2026) | up to 4K, 50 fps, up to 20 s | Yes | 941/918 (LTX-2), 979/961 (LTX-2.3) | 1 GPU | fast | [HF LTX-2](https://huggingface.co/Lightricks/LTX-2), [GlobeNewswire](https://www.globenewswire.com/news-release/2026/01/06/3213304/0/en/Lightricks-Open-Sources-LTX-2-the-First-Production-Ready-Audio-and-Video-Generation-Model-With-Truly-Open-Weights.html) |
| **Wan 2.2** A14B (T2V/I2V), TI2V-5B, S2V-14B, Animate | A14B: 27B MoE (2 experts), 14B active; 5B dense | **Apache-2.0** **[CONFIRMED]** | 480p/720p, 5 s (81 frames), 24 fps at 720p | No (S2V is speech-driven animation) | not in current AA top list (older) | 80 GB single GPU unoptimized; 5B runs on consumer GPUs | **8x H100, 720p, 81 frames, 40 steps: 250.7 s baseline → 109.8 s** (FA3 + TF32 + MagCache + compile) ([Morphic](https://morphic.com/blog/boosting-wan2-2-i2v-56-faster)) [SECONDARY]; LightX2V 4-step: ~20x fewer steps; TurboDiffusion claims 100–200x on RTX 5090 ([arXiv 2512.16093](https://arxiv.org/abs/2512.16093)) | FSDP + Ulysses (`--ulysses_size`), diffusers, ComfyUI, LightX2V, FastVideo, DiffSynth, Cache-DiT, SGLang-Diffusion, vLLM-Omni ([GitHub Wan2.2](https://github.com/Wan-Video/Wan2.2)) |
| HunyuanVideo 1.5 | 8.3B DiT | **Tencent Hunyuan Community**: *"DOES NOT APPLY IN THE EUROPEAN UNION, UNITED KINGDOM AND SOUTH KOREA"*; >100M MAU needs license; no outputs to improve other models **[CONFIRMED]** | 480p/720p (1080p SR), 121 frames (~5 s), 24 fps | No | not on AA top list | 14 GB min with offload | step-distilled 480p I2V (8–12 steps): ~75 s on RTX 4090; standard 50 steps | SSTA sparse attention, SP (`--sp_size`), FP8 GEMM, DeepCache/TeaCache/TaylorCache, diffusers, ComfyUI, LightX2V ([GitHub](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5)) |
| Kandinsky 5.0 Video Pro | 19B | Reported Apache-2.0 **or** MIT (conflicting) [UNVERIFIED] | up to 10 s | No | n/a | n/a | n/a | diffusers ([GitHub](https://github.com/kandinskylab/kandinsky-5), [HF](https://huggingface.co/kandinskylab/Kandinsky-5.0-T2V-Pro-sft-10s)) |
| LongCat-Video (Meituan) | 13.6B | **MIT** [SECONDARY] | T2V/I2V/video continuation; long-form (minutes) | No (Avatar variants are audio-driven) | n/a | n/a | n/a | [HF](https://huggingface.co/meituan-longcat/LongCat-Video) |
| Older (2024–25): Mochi 1 (10B, Apache-2.0), CogVideoX (2B Apache / 5B CogVideoX license), Open-Sora 2.0 (11B, Apache-2.0), Step-Video-T2V (30B, MIT), MAGI-1 (24B, Apache-2.0), SkyReels V2 | — | mostly permissive | ≤720p | No | far below current frontier | — | — | [UNVERIFIED, prior knowledge; not re-checked] |

### 2.3 Serving and acceleration ecosystem

- **SGLang-Diffusion**: supports Wan, Hunyuan, Qwen-Image, Flux and MiniMax H3. Features: token-level sequence sharding, parallel folding, distributed VAE, Cache-DiT integration. Reported 1.2x to 5.9x speedups ([LMSYS Nov 2025](https://www.lmsys.org/blog/2025-11-07-sglang-diffusion/), [LMSYS Feb 2026](https://www.lmsys.org/blog/2026-02-16-sglang-diffusion-advanced-optimizations/)). **[CONFIRMED blog]**
- **vLLM-Omni**: disaggregated any-to-any serving. About 1.26x over diffusers on Wan2.2 ([arXiv 2602.02204](https://arxiv.org/pdf/2602.02204), [docs](https://docs.vllm.ai/projects/vllm-omni/en/latest/user_guide/examples/offline_inference/image_to_video/)). Runs H3 in online FP8. **[SECONDARY]**
- **LightX2V** (ModelTC): 4-step step+CFG distills for Wan 2.1/2.2, HunyuanVideo 1.5 and H3 ([docs](https://lightx2v-en.readthedocs.io/en/latest/method_tutorials/step_distill.html), [HF](https://huggingface.co/lightx2v/Wan2.2-I2V-A14B-Moe-Distill-Lightx2v)).
- **FastVideo** (Hao AI Lab): distilled Wan with sparse attention ([GitHub](https://github.com/hao-ai-lab/fastvideo)).
- **xDiT**: Ulysses/Ring/PipeFusion parallelism for DiTs ([arXiv 2411.01738](https://arxiv.org/pdf/2411.01738)).
- **TurboDiffusion** (Tsinghua/Berkeley, Dec 2025): SageAttention plus sparse-linear attention, rCM step distillation and W8A8. Claims 100–200x on Wan 2.1/2.2 ([arXiv](https://arxiv.org/abs/2512.16093)).
- **Caching**: TeaCache, MagCache, Cache-DiT, DeepCache and TaylorCache give 1.5x to 3x speedups, but make skipping decisions **data-dependent** (see §3).

### 2.4 TEE considerations for model choice

- **Single-GPU confidential computing (CC)** on H100/H200 is the most mature path. Overhead is below 5% for most LLM workloads ([arXiv 2409.03992](https://arxiv.org/html/2409.03992v2)).
- **Multi-GPU CC** is harder:
  - Hopper HGX multi-GPU CC uses protected-PCIe modes with bounce-buffer encryption.
  - Blackwell B200 adds **NVLink encryption** for multi-GPU CC workloads ([Spheron CC guide](https://www.spheron.network/blog/confidential-gpu-computing-nvidia-tee-encrypted-vram/)).
  - A 2026 paper reports serialized-bridge slowdowns for LLM serving under Blackwell CC ([arXiv 2606.23969](https://arxiv.org/pdf/2606.23969)). **[SECONDARY]**
- Consequence:
  - H3 needs 4 GPUs officially and MAGI-2 needs 8, so **both require multi-GPU CC nodes**, and the collective traffic of Ulysses sequence parallelism will cost extra under CC.
  - **LTX-2.5 distilled fits on a single 80–141 GB GPU**, which is the simplest TEE story.
  - Community INT8/NVFP4 builds of H3 fit on one GPU, but quantized paths change outputs (SSIM 0.88 vs BF16), so they would need their own verification reference.

---

## 3. Determinism, reproducibility, and verification

### 3.1 What the frameworks guarantee

- PyTorch: *"Completely reproducible results are not guaranteed across PyTorch releases, individual commits, or different platforms."* Results may also differ between CPU and GPU with identical seeds ([PyTorch randomness notes](https://docs.pytorch.org/docs/2.14/notes/randomness.html)). **[CONFIRMED]**
- SDPA backends: MATH, FLASH_ATTENTION, EFFICIENT_ATTENTION and CUDNN_ATTENTION are all **deterministic in the forward pass**. Nondeterminism is in the backward pass, which inference does not use. `torch.use_deterministic_algorithms(True)` and `torch.backends.cudnn.benchmark = False` are the key switches. **[CONFIRMED]**
- LLM world: Thinking Machines showed that most "temperature-0 nondeterminism" comes from **batch-size-dependent reduction kernels**. Batch-invariant RMSNorm, matmul and attention kernels give bit-identical outputs ([Thinking Machines](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/)).
- SGLang deterministic mode: batch-invariant kernels, FA3 with `num_splits=1`, fixed split-KV. Cost is about a 34% slowdown. LLM-only; TP1–TP2 are reliable, larger TP needs more kernel work ([LMSYS](https://www.lmsys.org/blog/2025-09-22-sglang-deterministic/)). **[CONFIRMED]**
- **MAGI-2** exposes `MAGI2_DETERMINISTIC=1` for bit-exact MoE scatter and attention ([GitHub](https://github.com/SandAI-org/MAGI-2-preview)). **[CONFIRMED]** It is the only candidate found that ships a first-class deterministic mode.

### 3.2 Sources of nondeterminism in video diffusion inference

These are an engineering synthesis, grounded in the sources above.

1. **Initial noise generation.** Device RNG output can differ across GPU types or library versions (reported in the literature). Fix: generate noise on CPU with a fixed-algorithm generator from a validator-supplied seed, or have the validator supply the noise tensor hash.
2. **Kernel autotuning**:
   - `cudnn.benchmark` (VAE 3D convolutions),
   - torch.compile/Inductor and Triton autotuning,
   - FA3 split heuristics that depend on shape and SM count.
   Different kernels mean different reduction orders and different bits.
3. **Atomics / scatter-add**: MoE token dispatch in MAGI-2 and Wan2.2 expert routing; some sparse-attention kernels.
4. **Multi-GPU collectives**:
   - Ulysses all-to-all only moves data, so it is fine.
   - **Ring attention** changes the softmax accumulation order with ring size.
   - **TP all-reduce** order depends on NCCL algorithm and topology.
   - So changing GPU count, parallel degrees or topology changes bits.
5. **Precision paths**:
   - TF32 on/off (Morphic's biggest Wan speedup was TF32).
   - FP8 recipe (per-tensor vs per-block scaling; fp8-cast vs fp8-scaled-mm).
   - INT8/NVFP4 community quantizations. The H3 FP8 vs BF16 result (SSIM 0.881, PSNR 26.6 dB) shows these are **not** small perturbations.
6. **Data-dependent caching** (TeaCache, MagCache, Cache-DiT). A step-skip decision based on a relative-change threshold can flip because of a 1-ulp difference, which then changes the whole trajectory. These must be off or deterministic in verified mode.
7. **Chaotic amplification.** Differences of ~1e-4 in one step compound over 20–50 denoising steps. Final frames can visibly diverge even when every step is "numerically close". So tolerance checks on the final video are much weaker than per-step checks.
8. **Hardware SKU.** H100 SXM and H100 PCIe have different SM counts, which changes split heuristics. So do H200, B200 and consumer cards. Reproducibility must be defined per hardware class.

**Conclusion:** bitwise reproducibility is feasible **within a hardware class** when all of the following hold:
- The exact container image is pinned: driver, CUDA, cuDNN, PyTorch, kernels, model weights. The TEE attestation measurement can enforce this.
- GPU SKU, GPU count and parallel layout are fixed.
- Deterministic flags are on and autotuning is off.
- Noise is generated deterministically.
- Data-dependent caching is off.

It is **not** feasible across GPU types. The expected cost is roughly 10–35% slowdown in deterministic mode (analogous to the SGLang LLM figure; not measured for video) [UNVERIFIED for video].

### 3.3 Verification approaches (research and design options)

| Approach | Idea | Cost to validator | Strength | Source |
|---|---|---|---|---|
| **TEE attestation (primary)** | Attest CPU+GPU CC mode, container image digest and weight hashes; bind output to attestation report | ~0 | Strong if the TEE holds; weak against TEE bugs and side channels | NVIDIA CC docs |
| Full re-execution spot-check | Validator re-runs k% of jobs with the same seed on the same hardware class; bitwise compare | 100% of a job each time (H3 ~75 s on 4x H200) | Strong if deterministic | — |
| **Per-step commitment + random single-step re-execution** | Miner commits a hash chain or Merkle root of latents x_T..x_0 and the decoded video; validator picks a random step k, gets x_k, runs one step, compares with x_{k-1} (bitwise or within tolerance), then checks the Merkle path and VAE decode | ~1/N of a job (N = step count) plus data transfer (latents are MBs) | Strong; catches substituted models and skipped steps | Design synthesis; analogous to TAO dispute game |
| **TAO** (EuroSys 2026) | Tolerance-aware optimistic verification. Operator-level acceptance regions from IEEE-754 bounds plus empirical profiles; Merkle-anchored dispute game bisects to a single operator. **Shown on CNNs, Transformers and diffusion models across A100, H100, RTX6000 and 4090.** 0.3% overhead on Qwen3-8B | Low unless disputed | Works **across** GPU types | [arXiv 2510.16028](https://arxiv.org/abs/2510.16028) **[CONFIRMED abstract]** |
| Bit-exact verification via rounding signatures | Accumulated rounding errors act as an auditable signature of the HW/SW setup; bit-exact recomputation without determinism flags (LLM-focused) | re-exec | Detects software modifications | [arXiv 2606.00279](https://arxiv.org/abs/2606.00279) **[CONFIRMED abstract]** |
| Proof of Sampling (PoSP) | Nash-equilibrium random auditing with slashing | tunable | Economic, not cryptographic | [arXiv 2405.00295](https://arxiv.org/html/2405.00295) |
| Adaptive thresholds | For nondeterministic workflows, "the binding constraint is the threshold rather than the sample size"; per-execution adaptive thresholds beat constant thresholds | — | Guidance for tolerance tuning | [arXiv 2609.10601](https://arxiv.org/abs/2609.10601) (Sep 7, 2026) **[CONFIRMED abstract]** |
| Perceptual comparison (SSIM/LPIPS/CLIP/video embeddings) | Compare the miner's output with the validator's re-run | 100% re-run | Robust to tiny drift but gameable; honest FP8-vs-BF16 is already only SSIM 0.88, so thresholds are hard to set | H3 perf guide |
| Watermark / fingerprint | Model-conditioned watermark (e.g., WaDiff) | ~0 | Attribution, not proof of computation | [ECCV 2024](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/08694.pdf) |

**Recommended verification stack:**
1. TEE attestation on every request: image digest, weight hash and GPU CC mode in the report nonce-bound to the job.
2. Deterministic "verified mode" profile per model and hardware class.
3. Miner returns a Merkle root of per-step latents.
4. Validators run random single-step re-execution on about 1–5% of jobs, plus occasional full re-runs on reference hardware.
5. Slash or zero-weight on mismatch.
6. Performance-mode optimizations (caching, FP8) are allowed only if they are part of the pinned, attested profile. They must never be miner-chosen.

---

## 4. Recommendation

### 4.1 Which model(s) to launch with

**Do not make MiniMax H3 the sole or mandatory launch model unless MiniMax grants written authorization first.**
- Quality: it is the best open-weights model, about 110 Elo above the next open model on AA T2V.
- But its license bars the US/EU/UK/KR and output use there.
- It bans using outputs to improve other models.
- It needs 4-GPU nodes (multi-GPU CC).
- Its open release tops out at 768p because the 2K stage is closed.

**Action item for the subnet owner:** contact MiniMax (model@minimax.io, api@minimax.io, subject "MiniMax H3 licensing - authorization request"; an application form is linked for US/EU/UK/KR) for a network-wide authorization. This is especially important if the subnet or its customers could exceed $20M revenue.

**Launch plan (proposed):**

| Tier | Model | Why | Hardware |
|---|---|---|---|
| **Tier A, default at launch** | **LTX-2.5 distilled** (8-step) T2V/I2V with audio | Open weights; license allows SaaS hosting; free for entities <$10M revenue; AA #3–4 open-weights; single-GPU fit (simplest CC/TEE); fast (seconds to tens of seconds per clip); diffusers/ComfyUI/ltx-pipelines; deterministic on single GPU is the easiest case | 1x H100/H200/B200 (80–141 GB) in CC mode |
| **Tier B, premium (phase 2)** | **MAGI-2 Preview** (Apache-2.0), or its distilled release when available | Best **fully permissive** open model (#2 open-weights, 1080p, 10 s, audio); built-in bit-exact mode | 8x H100/H200 (or B200 with NVLink encryption) in multi-GPU CC; heavy (100 + 5 steps, undistilled) |
| **Tier C, gated** | **MiniMax H3** (FL2VA/Ref2VA, 768p) | Top open quality, 15 s, reference-to-video | Enable only (a) after MiniMax authorization, or (b) as an opt-in lane for miners attesting location outside the Excluded Territories, after legal review (geography is not provable by TEE). 4x H100/H200 |
| Fallback | **Wan 2.2** A14B / TI2V-5B (Apache-2.0) | Cleanest license, largest tooling ecosystem, many distills | 1–8 GPUs |

Caveats:
- **LTX-2.x license**: the <$10M threshold applies per licensee entity including affiliates. Each miner is a licensee. Whether the subnet operator or a large enterprise customer counts as "using" the model needs legal review. Lightricks offers paid licenses.
- **HunyuanVideo 1.5** is not recommended: it has the EU/UK/KR exclusion and lower quality than the options above.

### 4.2 Model-upgrade policy (proposed)

1. **Admission criteria for a new model:**
   - Open weights on an official org repo, with a license that permits (a) worldwide use including the US and EU, (b) hosting for third parties, and (c) commercial use at the subnet's scale. Otherwise a written authorization must be on file.
   - Quality: at least +30 Elo over the incumbent on the AA open-weights arena (T2V and I2V, audio and no-audio as relevant), confirmed by the subnet's own blind eval set.
   - A deterministic "verified mode" profile is reproducible bit-exactly on each supported hardware class.
   - Fits the supported TEE footprints (1-GPU, 4-GPU, 8-GPU CC).
2. **Pinning:** each model ID maps to exact weight SHA-256s, container image digest (attested by the TEE), framework version, precision, step count and scheduler. Acceleration variants (e.g., LightX2V 4-step, FP8) are **separate model IDs** with their own golden references. Miners never pick optimizations ad hoc.
3. **Announcement and overlap:** announce at least 2–4 weeks ahead with a public validator reference implementation. Run a dual-scoring overlap period in which the incoming model's share of emissions ramps 25% → 50% → 75% → 100% over 2–4 weeks. Keep the outgoing model at least 2 weeks for customer continuity.
4. **Golden-set regeneration:** for each hardware class, validators publish golden per-step latent hashes for a fixed prompt/seed set. These are used to certify miner images before they can earn.
5. **Emergency path:** immediate removal of a model if its license changes adversely (MiniMax changed M2.7's license after release) or if a verification bypass is found.
6. **License watch:** re-check license files on every upstream commit. Hash the LICENSE file as part of the model ID.

---

## 5. Source index

- MiniMax H3: [HF model](https://huggingface.co/MiniMaxAI/MiniMax-H3) · [LICENSE](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE) · [GitHub](https://github.com/MiniMax-AI/MiniMax-H3) · [MiniMax blog](https://www.minimax.io/blog/minimax-h3) · [ComfyUI Wiki](https://comfyui-wiki.com/en/news/2026-08-03-minimax-h3-open-weights-comfyui) · [explainx license analysis](https://explainx.ai/blog/minimax-h3-open-video-model-hailuo-july-2026) · [Spheron deploy](https://www.spheron.network/blog/deploy-minimax-h3-gpu-cloud/) · [perf guide](https://github.com/wildminder/awesome-minimax-H3/blob/main/guides/minimax-h3-performance.md) · [LightX2V Turbo](https://huggingface.co/lightx2v/Minimax-h3-Turbo) · [pricing docs](https://platform.minimax.io/docs/guides/pricing-video)
- MiniMax other: [HF org](https://huggingface.co/MiniMaxAI) · [Hailuo 02 news](https://www.minimax.io/news/minimax-hailuo-02) · [M3 LICENSE](https://huggingface.co/MiniMaxAI/MiniMax-M3/blob/main/LICENSE) · [M2](https://huggingface.co/MiniMaxAI/MiniMax-M2) · [M2.7 license change](https://letsdatascience.com/news/minimax-revises-license-after-releasing-m27-weights-04b47c74) · [Speech-02](https://www.minimax.io/news/minimax-speech-02)
- Leaderboards: [AA T2V](https://artificialanalysis.ai/video/leaderboard/text-to-video) · [AA I2V](https://artificialanalysis.ai/video/leaderboard/image-to-video)
- MAGI-2: [HF](https://huggingface.co/sand-ai/MAGI-2-preview) · [GitHub](https://github.com/SandAI-org/MAGI-2-preview) · [ComfyUI Wiki](https://comfyui-wiki.com/en/news/2026-08-05-magi-2-preview)
- LTX: [LTX-2.5 HF](https://huggingface.co/Lightricks/LTX-2.5) · [LTX-2 LICENSE](https://huggingface.co/Lightricks/LTX-2/blob/main/LICENSE) · [Runpod](https://www.runpod.io/blog/ltx-2-5-the-open-weights-world-model-built-for-speed-and-how-to-run-it-on-runpod) · [VentureBeat](https://venturebeat.com/technology/ltx-2-5-can-generate-a-10-second-ai-video-from-an-image-in-just-6-8-seconds-on-nvidia-superchips-and-its-open-weights)
- Wan: [HF Wan-AI](https://huggingface.co/Wan-AI) · [Wan2.2 HF](https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B) · [GitHub](https://github.com/Wan-Video/Wan2.2) · [Morphic benchmarks](https://morphic.com/blog/boosting-wan2-2-i2v-56-faster) · [Wan 3.0 status](https://www.atlascloud.ai/blog/tips/is-wan-3.0-open-source) · [Wan 2.7 status](https://localaimaster.com/blog/wan-2-7-open-source)
- Hunyuan: [GitHub 1.5](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5) · [LICENSE](https://huggingface.co/tencent/HunyuanVideo-1.5/blob/main/LICENSE) · [tech report](https://arxiv.org/html/2511.18870v1)
- Others: [Kandinsky 5](https://github.com/kandinskylab/kandinsky-5) · [LongCat-Video](https://huggingface.co/meituan-longcat/LongCat-Video) · [HappyHorse claim analysis](https://rctv.com/posts/happyhorse-open-source-claim/)
- Serving: [SGLang-Diffusion](https://www.lmsys.org/blog/2025-11-07-sglang-diffusion/) · [SGLang-Diffusion 2026](https://www.lmsys.org/blog/2026-02-16-sglang-diffusion-advanced-optimizations/) · [vLLM-Omni](https://arxiv.org/pdf/2602.02204) · [FastVideo](https://github.com/hao-ai-lab/fastvideo) · [LightX2V docs](https://lightx2v-en.readthedocs.io/en/latest/method_tutorials/step_distill.html) · [TurboDiffusion](https://arxiv.org/abs/2512.16093) · [xDiT](https://arxiv.org/pdf/2411.01738)
- Determinism/verification: [PyTorch randomness](https://docs.pytorch.org/docs/2.14/notes/randomness.html) · [Thinking Machines](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/) · [SGLang deterministic](https://www.lmsys.org/blog/2025-09-22-sglang-deterministic/) · [TAO](https://arxiv.org/abs/2510.16028) · [Bit-exact verification](https://arxiv.org/abs/2606.00279) · [PoSP](https://arxiv.org/html/2405.00295) · [Adaptive thresholds](https://arxiv.org/abs/2609.10601)
- TEE: [H100 CC benchmark](https://arxiv.org/html/2409.03992v2) · [Blackwell CC serving](https://arxiv.org/pdf/2606.23969) · [NVIDIA CC](https://www.nvidia.com/en-us/data-center/solutions/confidential-computing/)
