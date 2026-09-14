# KunoWorld pricing market research: AI video generation (as of 2026-09-14)

Update to `/video/research/research_market.md` sections A2–A5 (prices gathered Jul–Sep 2026). All prices USD unless noted.

**Confidence tags**
- **[C] Confirmed:** read on the vendor's own page, docs or public API, fetched 2026-09-13/14.
- **[S] Secondary:** a third-party source, with its date where known.
- **[U] Unverified:** a single weak source, a search snippet, or an inference.
- **[D] Derived:** my arithmetic from [C] figures.

**Conversions**
- $/5 s = $/s × 5.
- Credit plans: implied $ = plan price ÷ plan credits × credits per clip.
- "M / A" = monthly-billed / annual-billed.
- Where a model has no 720p, the nearest tier is named (e.g. 768p, 480p).
- Veo only allows 4/6/8 s clips, so its "5 s" is a per-second equivalent, not a real clip.

**How this was compiled**
- My own direct checks:
  - OpenRouter public video catalog (`/api/v1/videos/models`, 29 models);
  - OpenRouter per-provider endpoints for TEE vs normal comparisons;
  - Chutes public API (`/chutes`, `/pricing`, `/invocations/usage`, `/chutes/utilization`);
  - Artificial Analysis leaderboards;
  - vendor pages as cited.
- Six research threads' reports: closed APIs, open hosts, two consumer-plan threads, privacy premium, trends and structures. Their figures are carried with their tags.
- Scratch data: `or_video_models.json`, `or_tee_endpoints.json` and `chutes_*.json` in the same scratchpad directory.

---

## 0. Corrections to research_market.md A2–A5

| Item in old notes | Old | Now (2026-09-14) | Source / tag |
|---|---|---|---|
| Seedance 2.0 on OpenRouter | "$0.06726/s" | That is **480p**. **720p = $0.151/s**, 1080p = $0.374/s, 4K = $0.778/s. Tokens = W×H×24×s/1024 at $7/M (1080p $7.7/M, 4K $4/M) | [C] OpenRouter catalog; OpenRouter blog 2026-09-09 |
| Seedance 2.0 Fast / Mini | $0.04035 / $0.03363 | 480p rates. **720p = $0.0907 / $0.0756** | [C]/[D] |
| Seedance 2.5 | $0.1028 | 480p. **720p = $0.231/s** (480/720p only) | [C] OpenRouter blog |
| Wan 3.0 on OpenRouter | $0.0425/s | **$0.05 (480p) / $0.10 (720p) / $0.20 (1080p)**. Alibaba list is the same; launch promo $0.035 / $0.07 / $0.14 until 2026-09-24 | [C] OpenRouter; [S] Alibaba X post and search |
| Grok Imagine v1.5 | "$0.08" | $0.08 is 480p. **720p $0.14, 1080p $0.25** on OpenRouter. docs.x.ai lists only $0.05/s (v1) and $0.08/s (v1.5) with no resolution | [C] both — **conflict** |
| Sora 2 Pro 1080p | $0.70 | OpenRouter lists $0.50 (1024p and 1080p) | [C] OpenRouter |
| Sora API | sunset Sep 24 [S] | **Confirmed.** Notice 2026-03-24, removal 2026-09-24. sora-2, sora-2-pro and all snapshots; "recommended replacement: none" | [C] developers.openai.com/api/docs/deprecations |
| Veo 3.1 Fast / Lite | with-audio only | Silent SKUs exist on OpenRouter: Fast 720p $0.08, Lite 720p $0.03 | [C] OpenRouter |
| Pika Standard | $28/mo, 700 credits | $28/mo (annual) is **Pro** (2,300 credits). Standard is $10 M / $8 A for 700 credits | [C] pika.art/pricing |
| Kling "$1 = 66 credits" | [U] | That is the **consumer top-up** rate ($5 = 330). The API uses separate units at **$0.14/unit** list | [S] eesel, atlascloud |
| LTX-2.5 official API | [S] | **[C]**: Fast $0.09/$0.13/$0.19/$0.30; Pro $0.12/$0.17/$0.25/$0.39 (720p/1080p/1440p/4K) | docs.ltx.io/pricing, ltx.io |
| LTX license | "LTX-2 Community License, <$10M free" | LTX-2.5 is under the **LTX-2.x Community License dated 2026-08-11**. $10M threshold (affiliates aggregated) and SaaS permission kept. **"Competing service" clause** (Attachment A #20) and **no removing watermark/provenance** (§6) | [C] github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x |
| MiniMax H3 prices | $0.08 (768p) / $0.13 (2K) [C]/[S] | **[C]** on platform.minimax.io/docs/guides/pricing-paygo. H3-Max $0.05 (480P) / $0.08 (768P). Regeneration 768P→2K $0.05/s. **H3 not in MiniMax video packages** | [C] |
| "MiniMax H3 Max" | OpenRouter, [S] | A **fal post-trained derivative** of the H3 open weights, sold by fal and MiniMax. Launch promo (75% off) ended 2026-09-14. **List from 2026-09-15: $0.08/s at 768p; Turbo $0.04/s** | [C] fal.ai/minimax-h3-max |
| WaveSpeed Wan 2.2 720p | $0.40 per 5 s | **$0.30 per 5 s** | [C] |
| Novita Wan 2.1 | $0.30 | No longer listed (Wan 2.5/2.6 only) | [C] |
| Chutes video price | "no public per-video price" | **$0.0005 per GPU-second** (RTX PRO 6000, TEE). Observed ≈ $0.014 per LTX-2.5 call and $0.034 per TurboWan I2V call | [C] live API |
| Confidential Azure H100 "$8.90/hr" | premium implied | $8.90 is West Europe. Non-confidential NC40ads is **$9.08** there, so **no premium** (0% to −8% across regions) | [C] prices.azure.com (privacy thread) |
| "No confidential video anywhere" | [C/S/U] | Still true for products. Only raw TEE compute exists: Chutes LTX-25-Video / turbowani2v chutes, and NEAR AI's attested FLUX.2-klein image model ($0.012/image) | [C] |

---

## 1. Closed video APIs

### 1A. Summary: closed video APIs, $ per output second

Rows are first-party prices unless the row names a reseller. "5 s-eq" = $/s × 5, used where 5 s isn't a legal duration.

| Model / tier | Audio | $/s 720p | $/s 1080p | $/5 s 720p | Other resolutions | Durations | Batch / volume | Tag / source |
|---|---|---|---|---|---|---|---|---|
| **Veo 3.1 Standard** (Gemini API) | with | 0.40 | 0.40 | 2.00 (5 s-eq; 4 s = $1.60) | 4K 0.60 | 4/6/8 s; 1080p and 4K are 8 s only | Gemini batch: none. Vertex: batch "not supported", Provisioned Throughput available | [C] ai.google.dev/gemini-api/docs/pricing (updated 2026-09-11); cloud.google.com/vertex-ai/generative-ai/pricing |
| Veo 3.1 Standard (Vertex) | without | 0.20 | 0.20 | 1.00 (5 s-eq) | 4K 0.40 | same | same | [C] Vertex |
| **Veo 3.1 Fast** | with / without | 0.10 / 0.08 | 0.12 / 0.10 | 0.50 / 0.40 (5 s-eq) | 4K 0.30 / 0.25 | same | same | [C] |
| **Veo 3.1 Lite** | with / without | **0.05 / 0.03** | 0.08 / 0.05 | **0.25 / 0.15** (5 s-eq) | no 4K | same | same | [C] |
| Veo 3 / Veo 3 Fast (Vertex) | with / without | 0.40, 0.20 / 0.10, 0.08 | 0.40, 0.20 / 0.12, 0.10 | – | – | 8 s | – | [C]. Retired on the Gemini API 2026-06-30 [C changelog, per trends thread] |
| Veo 2 (Vertex) | none | 0.50 | – | 2.50 | – | – | – | [C] |
| **Gemini Omni Flash** (gemini-omni-1.1-flash) | with | **0.101** | 0.152 (upscaled) | 0.51 | 360p 0.034; 4K 0.304 | 3–10 s | none listed | [C]. $17.50 per 1M video tokens; 5,792 tokens/s at 720p |
| Veo 3.1 / Fast via **Runway API** | with / without | 0.40, 0.20 / **0.15**, 0.10 | same | – | – | – | – | [C]. Runway marks Fast up 50% over Google |
| **Sora 2** | with | 0.10 (batch 0.05) | – | 0.50 | – | 4/8/12 s [U] | Batch −50% | [C] developers.openai.com/api/docs/pricing. **Removed 2026-09-24** |
| **Sora 2 Pro** | with | 0.30 (batch 0.15) | 0.70 (batch 0.35); OpenRouter lists 0.50 | 1.50 | 1024p 0.50 | same | Batch −50% | [C]. Removed 2026-09-24. OpenRouter 1080p **conflict** |
| **Kling 3.0** (official, 1 unit = $0.14) | without | 0.084 | 0.112 | 0.42 | 4K 0.42 | up to 15 s | Packages: trial $9.80 for 100 units ($0.098); $700 for 5,000 units ($0.14, 180 days); $5,670 for 45,000 (−10%). Failed jobs don't deduct units | [C] kling.ai/dev/pricing (embedded JSON); packages [S] atlascloud 2026-07-14 |
| Kling 3.0 | with | 0.126 | 0.168 | 0.63 | – | – | – | [C] |
| Kling 3.0 Omni (no video input) | without / with | 0.084 / 0.112 | 0.112 / 0.14 | 0.42 / 0.56 | – | – | – | [C] |
| Kling 3.0 Turbo | with | 0.112 | 0.14 | 0.56 | – | – | – | [C] |
| Kling 3.0 on fal | without / with / with voice control | 0.084 / 0.126 / 0.154 (Std) | 0.112 / 0.168 / 0.196 (Pro) | 0.42 | – | – | – | [C] fal |
| Kling 3.0 on Replicate | without / with | 0.168 / 0.252 | 0.224 / 0.336 | 0.84 | 4K 0.42 | – | – | [C]. Exactly 2× official |
| Kling 3.0 via Pika API | without / with | 0.068 / 0.101 | 0.09 / 0.135 | 0.34 | 4K 0.336 | – | – | [S] api.dev.pika.art catalog |
| **Runway Gen-4.5** | none | 0.12 | n/s | 0.60 | – | 2–10 s | No volume discount; $0.01/credit | [C] docs.dev.runwayml.com/guides/pricing |
| Runway Gen-4 Turbo / Act-Two | none | 0.05 | – | 0.25 | – | – | – | [C] |
| Runway Aleph 2 (video-to-video) | – | 0.28 | – | 1.40 | – | – | 56-credit minimum | [C] |
| **Luma Ray 3.2** | none listed | 0.06 at 5 s; 0.09 at 10 s | 0.24 at 5 s; 0.36 at 10 s | **0.30** | 360p $0.06, 540p $0.15 per 5 s; HDR 2×; HDR+EXR 3× | 5 or 10 s; **10 s = 3× the 5 s price** | "Subject to change ahead of GA" | [C] docs.agents.lumalabs.ai/guides/pricing |
| **Seedance 2.0** (BytePlus) | with | 0.15 | 0.37 | 0.76 | 480p 0.07; 4K 0.78 | 4–15 s | $7 per 1M tokens; $4.30 with video input. Resource packs valid 90 days | [C] BytePlus article 2026-07-22 (price page is JS-only); OpenRouter matches: 720p $0.151, 1080p $0.374 |
| Seedance 2.0 Fast | with | 0.12 (BytePlus); 0.091 (OpenRouter) | n/a | 0.60 / 0.45 | 480p 0.06 / 0.040 | 4–15 s | – | [C] both. **Conflict** ($5.60/M implied vs $4.20/M) |
| **Seedance 2.0 Mini** (2026-08-12) | with | **0.08** (BytePlus); 0.0756 (OpenRouter) | n/a | **0.38** | 480p 0.04 / 0.0336 | 4–15 s | – | [C] |
| Seedance 2.5 (2026-08-07) | with | 0.231 (OpenRouter); 0.30 (Runway) | n/a; 0.68 (Runway) | 1.16 | 480p 0.103 | 4–30 s | Plans ~1:1.8 token offset, valid 3 months | [C] OpenRouter blog 2026-09-09; [S] plans |
| Seedance 2.0 on fal | with | 0.3034 (fast 0.2419) | 0.682 | 1.52 | – | – | – | [C] fal page. $0.014 per 1k tokens, 2× OpenRouter |
| Seedance 1.5 Pro (OpenRouter) | with / without | 0.052 / 0.026 | 0.117 / 0.058 | 0.26 | – | 4–12 s | – | [C]/[D] $2.4/M with audio, $1.2/M without |
| **MiniMax H3** (official) | with | 0.08 (768P) | 0.13 (2K) | 0.40 | 2K regeneration $0.05/s | 4–15 s | **Not in video packages.** Reference images: 5 free, then $0.04 | [C] platform.minimax.io/docs/guides/pricing-paygo |
| MiniMax H3-Max (official; fal post-trained) | yes per fal, no per OpenRouter | 0.08 (768P) | – | 0.40 | 480P 0.05 | 5–15 s | – | [C] |
| fal H3 Max Director / H3 Max | native audio | 0.08 list (promo 0.02 to Sep 14) | 0.16 | 0.40 | Turbo: 768p 0.04, 480p 0.025 | 5–15 s | $1.20 minimum per session | [C] fal |
| Hailuo 2.3 / 2.3 Fast / 02 (official, legacy) | none | 768P, 6 s: $0.28 / $0.19 (0.047 / 0.032 per s) | 1080P, 6 s: $0.49 / $0.33 (0.082 / 0.055 per s) | n/a (6 s or 10 s) | 02 at 512P: $0.10 per 6 s | 6/10 s | Packages $1k–6k/month, −5% to −20%, 1-month validity | [C] |
| MiniMax China | – | H3 ¥0.50 (768P); H3-Max ¥0.50 | H3 ¥0.80 (2K) | – | H3-Max 480P ¥0.33 | – | – | [C] platform.minimax.cn |
| **xAI Grok Imagine** | yes | 0.07 | n/a | 0.35 | 480p 0.05; image input $0.002; video input $0.01/s | ≤15 s | Batch API, no discount | [C] docs.x.ai (model JSON) |
| xAI Grok Imagine 1.5 | yes | 0.14 | 0.25 | 0.70 | 480p 0.08; image input $0.01 | ≤15 s | none | [C] |
| **Alibaba Wan 3.0** (2026-08-06, API-only) | with | 0.10 (Singapore); 0.0825 (global) | 0.20 / 0.165 | 0.50 | 480p 0.05 / 0.041 | ≤30 s | Launch promo −30% (0.035 / 0.07 / 0.14) until ~Sep 23–24 | [C] alibabacloud.com/help/en/model-studio/wan3-0-video; promo [S] |
| Wan 3.0 Prime | with | 0.14 | 0.28 | 0.70 | 480p 0.068 | ≤30 s | – | [C] |
| HappyHorse 1.1 (Alibaba) | – | 0.14 (Alibaba); 0.0988 (OpenRouter) | 0.18 / 0.1278 | 0.70 / 0.49 | 480p 0.07 | 3–15 s | Batch unsupported | [C] both. **Conflict** |
| Wan 2.7 / 2.6 T2V | with | 0.10 | 0.15 | 0.50 | – | 2–10 s / 5 or 10 s | – | [C] Alibaba; OpenRouter: 2.7 flat 0.10, 2.6 T2V 0.08/0.12 |
| Wan 3.0 via Pika API | – | 0.065 | 0.13 | 0.33 | 480p 0.0325 | – | – | [S]. −35% vs Alibaba |
| **Vidu Q3-turbo** / Q3-pro | yes [S] | 0.055 / 0.10 (off-peak 0.03 / 0.05) | 0.065 / 0.12 | 0.275 / 0.50 | 540p 0.035 / 0.045 | 1–16 s | **Off-peak −50%**; volume by email | [C] platform.vidu.com/docs/pricing ($0.005/credit) |
| **PixVerse V6** | without / with | 0.09 / 0.12 (Business plan 0.050 / 0.067) | 0.18 / 0.23 | 0.60 (with) | 360p 0.05 | – | Memberships $100–6,000/month: $0.0067–0.0056/credit vs $0.01 packs (−33% to −44%) | [C] docs.platform.pixverse.ai |
| **Pika 2.5** (own API) | none | **0.04** | 0.06–0.09 | **0.20** | – | 5 s tier | – | [C] api.dev.pika.art/catalog/apis |
| Midjourney Video | none | ≈0.027 SD / ≈0.087 HD (derived) | – | ≈0.13 SD / ≈0.43 HD | – | 5 s ×4 per job | **No API**; ≈8 / ≈26 GPU-min per job; extra Fast hours $4/hr; plans $10–120/mo | [S] eesel 2026-06-05; [U] derived |
| Amazon Nova Reel | none | 0.08 | – | 0.40 (6 s = $0.48) | – | 6 s shots [U] | – | [C] AWS price list 2026-09-11 |
| **BFL FLUX.3 Video** (2026-08-04) | with | 0.17 (OpenRouter) | 0.29 | 0.85 | Continuation 720p 0.41, 1080p 0.53; BFL list "$0.06–0.54/s" incl. drafts | 5–20 s | – | [C] OpenRouter; [S] BFL range (digitalapplied) |
| HeyGen Avatar IV (OpenRouter) | – | 0.05 | 0.05 | 0.25 | – | – | – | [C] |
| HiDream-O1-Video (Aug 2026) | yes | – | – | – | AA says $5.80/min ≈ $0.097/s | – | **No API or price page found** | [S] AA |
| Agnes-Video-2.5 (Sapiens AI, Aug 2026) | – | – | – | – | AA $1.50/min ≈ $0.025/s | – | – | [S] AA |
| SkyReels V4 (Skywork) | – | – | – | – | AA $21/min ≈ $0.35/s | – | – | [S] AA |
| MAGI-2 Preview (Sand.ai, open weights) | – | – | – | – | pricing "coming soon" | – | – | [S] |
| Unifically (reseller), Veo 3.1 Lite "Relaxed" | with | ≈0.009 | – | ≈0.047 | $0.075 per 8 s at 720p | 8 s | – | [S] unifically.com/blogs/veo-3.1, updated 2026-08-28 |

### 1B. Sora API sunset [C developers.openai.com/api/docs/deprecations]
- **Notice:** 2026-03-24.
- **Removal:** 2026-09-24. Covers the Videos API plus `sora-2`, `sora-2-pro`, `sora-2-2025-10-06`, `sora-2-2025-12-08` and `sora-2-pro-2025-10-06`.
- **Replacement:** none; the "recommended replacement" column is blank.
- **Consumer apps:** Sora web and app closed 2026-04-26; export at sora.chatgpt.com/sunset. [S help.openai.com, 403; search snippet]
- **Migration help:** no migration credits or guidance found.
- **Who picks up the traffic:** third parties are courting migrants — Spheron (self-hosted), apiyi, byteiota. [S]
- **Implication:** the $0.10/s (720p) Sora 2 buyer and the $0.30–0.70/s Sora 2 Pro buyer must move within 10 days. Nearest like-for-like options:
  - Veo 3.1 Fast at $0.10.
  - Gemini Omni Flash at $0.10.
  - Kling 3.0 at $0.084–0.168.

### 1C. Closed-API price bands for a 5 s 720p clip (Sep 2026)
- **Floor, under $0.30:**
  - Veo 3.1 Lite: $0.25 with audio, $0.15 silent.
  - fal H3 Max Turbo: $0.20 at 768p.
  - Pika 2.5: $0.20, silent.
  - Vidu Q3-turbo: $0.275.
  - Grok Imagine: $0.35.
  - Seedance 2.0 Mini: $0.38.
  - Kling via Pika: $0.34.
  - Resellers: under $0.05.
- **Mainstream, $0.40–0.80:**
  - H3 (768p): $0.40.
  - Veo 3.1 Fast: $0.50.
  - Wan 3.0: $0.50.
  - Gemini Omni Flash: $0.51.
  - Gen-4.5: $0.60.
  - Kling 3.0 with audio: $0.63.
  - Wan 3.0 Prime: $0.70.
  - Seedance 2.0: $0.76.
- **Premium, $1–2+:**
  - Seedance 2.5: $1.16.
  - Sora 2 Pro: $1.50.
  - Veo 3.1: $2.00.
  - Luma at 1080p: $1.20.

---

## 2. Open-model hosts: LTX-2.5, MiniMax H3, and references

### 2A. LTX-2.5 (Lightricks, open weights; audio included unless noted)

| Host | SKU | $/s 720p | $/s 1080p | $/s 1440p | $/s 4K | $/5 s 720p | $/5 s 1080p | Latency (published) | Tag / URL |
|---|---|---|---|---|---|---|---|---|---|
| **Lightricks LTX API** | ltx-2-5-fast (T2V/I2V; A2V billed on input audio) | 0.09 | 0.13 | 0.19 | 0.30 | 0.45 | 0.65 | 10 s I2V at 1080p in 23.7 s via API; 10 s in 6.8 s on 2×GB200 (vendor) | [C] docs.ltx.io/pricing, ltx.io/model/api/pricing |
| Lightricks LTX API | ltx-2-5-pro (6/8/10 s) | 0.12 | 0.17 | 0.25 | 0.39 | 0.60 | 0.85 | – | [C] same |
| **fal.ai** | lightricks/ltx-2.5 fast | 0.09 | 0.13 | 0.19 | 0.30 | 0.45 | 0.65 | not listed | [C] fal.ai/models/lightricks/ltx-2.5/text-to-video/fast |
| fal.ai | lightricks/ltx-2.5 pro (720p/1080p only) | 0.12 | 0.17 | – | – | 0.60 | 0.85 | – | [C] fal.ai/ltx-2.5 |
| **Replicate** | lightricks/ltx-2.5-fast (official, created 2026-08-10) | **0.03** | **0.06** | 0.12 (2k) | 0.24 | 0.15 | 0.30 | – | [C] replicate.com/lightricks/ltx-2.5-fast. **Conflict:** identical to LTX-2.3 Fast list, likely a stale billing config. ltx-2.5-pro not on Replicate |
| **WaveSpeed** | wavespeed-ai/ltx-2.5 (no Fast/Pro split) | 0.10 | 0.14 | 0.21 | 0.33 | 0.50 | 0.70 | median ≈74 s | [C] wavespeed.ai/models/wavespeed-ai/ltx-2.5/text-to-video |
| **Segmind** | LTX 2.5 Fast | 0.1125 | 0.1625 | 0.2375 (2K) | 0.375 | 0.5625 | 0.8125 | 6 s 1080p 33.0 s; 6 s 4K 60.1 s; 20 s 720p 37.3 s | [C] blog.segmind.com (LTX 2.5 guide) |
| Segmind | LTX 2.5 Pro (≤10 s) | 0.15 | 0.2125 | – | – | 0.75 | 1.0625 | 6 s 1080p 47.8 s | [C] same |
| Comfy partner nodes | LTX-2.5 Fast: 27.16 / 39.22 / 57.33 / 90.52 credits/s | ≈0.129 | ≈0.186 | ≈0.272 | ≈0.429 | ≈0.64 | ≈0.93 | – | [C] docs.comfy.org partner-node pricing; [D] at 211 credits = $1, ≈1.43× Lightricks list |
| Comfy partner nodes | LTX-2.5 Pro: 36.21 / 51.29 credits/s | ≈0.172 | ≈0.243 | – | – | ≈0.86 | ≈1.22 | – | [C]/[D] |
| **Chutes (SN64), TEE** | `LTX-25-Video` community chute (vonkaiser NVFP4/FP8 distilled, 8+3 steps; ≤20 s to 1080p, 13 s 1440p, 6 s 4K) | $0.0005 per GPU-second; observed avg **$0.0136 per call** (140 calls, Sep 3–8; daily avg $0.004–0.055) | | | | ≈0.01–0.05 per call (resolution unknown) | | frame budget "finishes inside ~6 minutes"; **0 instances, not hot** on 2026-09-14 | [C] api.chutes.ai |
| Runware | LTX-2.5 Fast/Pro pages | example runs: Fast $0.48–0.96, Pro $0.72 | | | | | | – | [C] examples only; per-second table unreadable [U] |
| Kie.ai | blog quoting third parties | 0.09 | 0.15 | 0.19 (2K) | 0.37 | – | – | "23.7 s via API" | [S] kie.ai/blog/what-is-ltx-2-5 |
| Invideo (consumer credits) | LTX 2.5 720p, 6 s = 6.24 credits | ≈0.02–0.05 by plan | – | – | – | 0.10–0.26 | – | – | [C] invideo.io/help/billing/video-model-pricing. Below Lightricks list, so possibly a lower tier |
| Not listed | Novita, SiliconFlow, DeepInfra, Together, Fireworks, Baseten, RunPod, HF Inference Providers, OpenRouter | | | | | | | | [C] |

**Previous LTX generations**
- **Lightricks LTX-2.3 Fast:** $0.03 / 0.06 / 0.12 / 0.24.
- **Lightricks LTX-2.3 Pro:** $0.04 / 0.08 / 0.16 / 0.32. A2V $0.06 / 0.10 / 0.18 / 0.34; Retake/Extend $0.10/s at 1080p; HDR upscale $0.20–0.80/s. [C]
- **fal LTX-2 Fast:** 1080p $0.04, 1440p $0.08, 4K $0.16. Page carries a deprecation notice dated 2026-08-15. [C]
- **fal LTX-2 Pro:** $0.06 / 0.12 / 0.24. [C]
- **fal LTX-2.3 Fast:** 1080p $0.06. [C]
- **Replicate:** ltx-2-distilled $0.02/s; ltx-2.3-fast $0.06 at 1080p. [C]
- **WaveSpeed LTX-2.3:** $0.10 / $0.15 / $0.20 per 5 s at 480/720/1080p, median ≈32 s. [C]
- **Magnific (Freepik):** LTX 2 Fast 80 credits/s at 1080p, i.e. $0.08/s monthly or ≈$0.054/s annual on Premium+. [C]/[D]

### 2B. MiniMax H3 (Hailuo 03): official API, open weights, derivatives

| Host | SKU | Weights | $/s 480p | $/s 768p | $/s 1080p/2K | $/5 s 768p | Latency | Tag / URL |
|---|---|---|---|---|---|---|---|---|
| **MiniMax official** | MiniMax-H3 | closed hosted API | – | **0.08** | 0.13 (2K) | 0.40 | – | [C] platform.minimax.io/docs/guides/pricing-paygo. Reference images: 5 free, then $0.04. Regeneration 768P→2K $0.05/s. Not in video packages ($1k–6k/mo packs cover Hailuo 2.x only) |
| MiniMax official | MiniMax-H3-Max | closed | 0.05 | 0.08 | – | 0.40 | – | [C] same |
| OpenRouter | minimax/hailuo-3 (2K only) / hailuo-3-max | closed | Max 0.05 | Max 0.08 | 0.13 (2K) + $0.04/ref | 0.40 | – | [C] catalog. Max flagged generate_audio=false (**conflict** with fal "native audio") |
| Replicate | minimax/h3 | closed resale | – | 0.08 | 0.13 (2K) | 0.40 | – | [C] |
| **fal.ai** | minimax/h3 T2V/I2V/reference | **open-weight base**; 2K/4K are upscales of 768p | 0.05 | **0.06** | 0.13 (2K), 0.16 (4K) | 0.30 | not listed | [C] fal.ai/models/minimax/h3/text-to-video. Reference images: 5 free, then $0.08 |
| **fal.ai** | **H3 Max** (post-trained by fal from H3 open weights; weights not released) | derivative | promo 0.0125 → **list 0.05** | promo 0.02 → **list 0.08** | promo 0.04 → **list 0.16** (1080p) | 0.10 promo → **0.40** | 5 s 768p "under 3 s" end-to-end; 5 s 480p 0.75 s; 15 s 1080p 17.6 s | [C] fal.ai/minimax-h3-max. "75% below list until September 14, 2026"; native audio; 5–15 s; free 5 generations/day |
| fal.ai | **H3 Max Turbo** (fal distill) | derivative | promo 0.00625 → list 0.025 | promo 0.01 → **list 0.04** | promo 0.02 → list 0.08 | 0.05 → **0.20** | 0.44 s for 5 s 480p | [C] same |
| **WaveSpeed** | wavespeed-ai/minimax-h3 T2V/I2V ("open-weights edition… own GPU infrastructure") | open weights | 0.04 | 0.08 | 0.16 (1080p) | 0.40 | median T2V ≈149 s, I2V ≈82 s | [C] model page. Landing page says "50% OFF… from $0.10 (was $0.20)" — **conflict** |
| WaveSpeed | minimax-h3 reference-to-video | open | 0.05 | 0.125 | 0.25 | 0.625 | ≈150 s | [C] +$0.02 per reference image or audio |
| WaveSpeed | LoRA / edit / extend | open | – | from $0.10–0.15 (50% off) | – | – | – | [C] |
| Segmind | minimax-h3 | closed resale | – | 0.1125 (listed, "not reachable") | 0.1625 (2K) | 0.5625 | – | [C] blog |
| Atlas Cloud | H3 / Fast / Max / "H3-Developer (self-hosted)" | mixed | – | Max 0.05 | H3 0.038 (2K)?; Aug blog: 2K $0.14 | ≈0.19–0.25 | – | [C] model page vs [C] blog — **units don't reconcile** |
| Runway API | hailuo3 (768p) / h3_max (480p) | closed resale | h3_max 0.05 | hailuo3 **0.10** + 2 credits/ref | – | 0.50 | – | [C] docs.dev.runwayml.com/guides/pricing |
| Comfy partner nodes | H3 / H3 Max | closed API | Max ≈0.072 | H3 ≈0.129; Max ≈0.114 | H3 ≈0.186 (2K) | ≈0.64 | – | [C] credits / [D] $ |
| Runware | h3@0, h3@max, Max Turbo, H3 Fast | unclear | – | ≈0.05–0.08 | – | – | – | [C] examples, [U] mapping |
| HF | lightx2v/Minimax-h3-Turbo; Turbo-SLA; alibaba-pai MiniMax-H3-Acc-LoRAs | open (card tagged apache-2.0, but bound by the H3 licence) | – | no host serves it by name | – | – | – | [C] |
| Chutes | – | – | – | no H3 chute | – | – | – | [C] |
| Not listed | Novita, SiliconFlow, DeepInfra, Together, Fireworks, Baseten, Modal, RunPod, ElevenLabs | | | | | | | [C] |

**Consumer-app credits for H3** [C magnific.com/ai/docs/ai-video-generator-credits]
- Magnific: H3 75 / 92 / 110 credits/s at 480p / 768p / 2K.
- H3 Max 55 / 80 / 150; H3 Max Turbo 12 / 20. So an H3 5 s 768p clip ≈ $0.46 M / $0.31 A on Premium+, and H3 Max Turbo ≈ $0.10 / $0.07.
- Invideo: H3 Max Turbo 480p 5 s = 6 credits ($0.12–0.30); H3 Max 480p = 12; H3 2K 5 s = 31.2. [C]

### 2C. Wan 2.2 reference (Apache-2.0 open weights)

| Host | SKU | Price | $/5 s 720p | Latency | Tag |
|---|---|---|---|---|---|
| fal | wan/v2.2-a14b T2V | $0.08 per video-second at 720p (16 fps counting); $0.06 580p, $0.04 480p | ≈0.40 | – | [C] |
| Replicate | wan-2.2-t2v-fast / i2v-fast | $0.10 / $0.11 per 720p video; $0.05 at 480p | 0.10–0.11 | ≈30 s (2025 blog) | [C] |
| WaveSpeed | wan-2.2 t2v/i2v 720p | $0.30 per 5 s; LoRA Ultra Fast $0.15 | 0.30 | median ≈118 s / 150 s | [C] |
| SiliconFlow | Wan2.2 T2V/I2V A14B | $0.29 per video (5 s, 480P/720P) | 0.29 | – | [C] |
| DeepInfra | Wan2.2-T2V-A14B (480P); FastWan2.2-TI2V-5B | $0.075/s; FastWan $0.0225 per 5 s 720p | 0.0225 (5B) | – | [C] |
| RunPod public endpoints | Wan 2.2 / 2.1 720p | $0.30 per 5 s request | 0.30 | – | [C] |
| Comfy Cloud | Wan 2.2 I2V template (81 frames, 640²) | Pro $100 ≈ 1,915 videos | ≈0.052 | – | [C]/[D] |
| Chutes (TEE) | turbowani2v (TurboDiffusion 4-step A14B 720P I2V) | $0.0005/GPU-s; observed avg $0.034 per call, busy days $0.050–0.057 (≈100–114 GPU-s) | ≈0.05 | – | [C] |

### 2D. Chutes (SN64) live pricing: the raw-compute floor [C api.chutes.ai, 2026-09-14 ~14:48 UTC]

**Prices**
- `/pricing`: TAO = $233.35.
- Per-GPU prices:

  | GPU | $/hr |
  |---|---|
  | RTX PRO 6000 | 1.80 ($0.0005/s) |
  | H100 | 1.79 |
  | H100 SXM | 2.35 |
  | H200 | 2.75 |
  | B200 / B300 | 4.50 |
  | RTX 5090 | 0.70 |

- All 491 public chutes are `tee=true`.
- The user price is basis $4.50 × `compute_multiplier` 0.4 = $1.80/hr, whatever the `tee: 2.25` factor says. That factor sits in `compute_multiplier_factors`, which looks like a miner-side weighting. **Users pay no visible TEE premium on Chutes** [C numbers; U interpretation].

**`LTX-25-Video`**
- Created 2026-08-13; bounty 86,400.
- Effective multiplier 1.35 (base 0.4 × bounty 1.5 × tee 2.25).
- Usage: 140 calls and $1.90 over Sep 3–8, then no usage Sep 9–14.
- Utilization 0; instance count 0.

**`turbowani2v`**
- 1 active verified instance.
- Usage: 359 calls and $12.07 over Sep 3–14.

**Lesson:** Chutes proves TEE video is cheap to *serve* (≈$0.01–0.06 per clip at GPU-second prices). But it is a synchronous, community-deployed, cold-start-prone raw endpoint with almost no demand. It is not a product.

### 2E. Licences and pricing implications

**LTX-2.x Community License** (2026-08-11; covers LTX-2.5) [C github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x]
- **Revenue threshold, §2.1:** "Entities with annual revenues of at least $10,000,000 (the "Commercial Entities") are required to obtain a paid license for any use… of LTX-2.x and Derivatives". §1.6 aggregates affiliates.
  - No published fee: "Do you charge per generation? Not on a license." Path is a 30-day pilot, then terms "that match your scale" [C ltx.io/model/licensing].
- **SaaS permitted, §3:** "You may host for third parties remote access purposes (e.g. software-as-a-service)…". Conditions: pass through the use restrictions (§3.1) and retain attribution notices (§3.4).
- **Outputs, §5:** "Licensor claims no rights in the Output you generate".
- **Watermarks and provenance, §6:** you "shall not remove, disable, alter, or circumvent, any… metadata, watermarking, content provenance…". This applies to Private mode too.
- **Competing services, Attachment A #20:** prohibited "in any product, service, or application that directly competes with Licensor's commercial products or services… without obtaining a separate commercial license".
  - **This is the main commercial risk for a paid LTX API, regardless of revenue.**
- **Older LTX-2 licence** (2026-01-05): same $10M threshold and SaaS clause, but breach damages were **2×** fees. [C]

**MiniMax H3 Community License** (2026-08-02; file unchanged since 2026-08-03) [C huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE]
- **Excluded territories:** "the European Union, the United Kingdom, the Republic of Korea and the United States of America".
- **Outputs can't leave the territory either:** "You may not use, reproduce, modify, distribute, or display the MiniMax H3 Works or any of their Outputs or results outside the Applicable Territory."
- **Revenue gate:** "separate, prior written authorization… if your commercial products and services generate more than 20 million US dollars… in yearly revenue".
- **Mandatory UI branding:** "MiniMax H3".
- **Pass-through of use restrictions** and an abuse-report mechanism are required.
- **Distills are derivatives** and stay bound by the licence.
- **No authorization price is published.**
  - Application form: platform.minimax.io/h3-license.
  - Comfy says it is "the only official reseller of MiniMax commercial-use licenses" (Professional and Enterprise tiers; price not captured). [C]

**Pricing implications** (not legal advice)
- **LTX-2.5 anchors:** Lightricks list is $0.09/s (720p) and $0.13/s (1080p) for Fast.
  - Resellers sit at list or above: fal 1.0×, WaveSpeed ≈1.1×, Segmind 1.25×, Comfy ≈1.43×.
  - Replicate at $0.03/$0.06 is the low outlier.
  - Lightricks sells its own model at a healthy margin over compute (Chutes: ≈$0.01–0.05 per call).
- **H3 open weights:** without MiniMax authorization, H3 can legally be sold only by operators outside the US, EU, UK and South Korea, and only to users there.
  - US-facing H3 today flows through MiniMax's own API at $0.08 per 768p second, or partner deals (fal H3 Max is jointly listed by MiniMax).
  - The open-weights price floor among hosts is $0.04–0.08/s at 768p: fal H3 $0.06, fal H3 Max Turbo $0.04 list, WaveSpeed $0.08 list with 50% promo.

---

## 3. Quality vs price: Artificial Analysis video arena [C artificialanalysis.ai, fetched 2026-09-14; page as of ~Aug 2026; "with audio" boards]

AA's price column is AA's own pick of SKU, in $/min. $/s = ÷ 60.

**Text-to-video**

| Rank | Model | Elo | Open weights | AA $/min | ≈$/s |
|---|---|---|---|---|---|
| 1 | Wan 3.0 | 1242 | no | 12.00 | 0.20 |
| 2 | Gemini Omni Flash | 1238 | no | 6.00 | 0.10 |
| 3 | **MiniMax H3 Max (fal)** | 1231 | no | **2.40** | **0.04** (promo-era) |
| 4 | **MiniMax H3** | 1226 | **yes** | 7.80 | 0.13 |
| 5 | Seedance 2.0 720p | 1220 | no | 9.07 | 0.151 |
| 6 | Wan 2.7 | 1158 | no | 9.00 | 0.15 |
| 7 | HappyHorse 1.1 | 1146 | no | 9.90 | 0.165 |
| 8 | HappyHorse 1.0 | 1124 | no | 13.20 | 0.22 |
| 10 | Kling 3.0 1080p Pro | 1108 | no | 20.16 | 0.336 |
| 13 | Kling 3.0 720p Std | 1102 | no | 15.12 | 0.252 |
| 14 | Sora 2 (Dec) | 1096 | no | 6.00 | 0.10 |
| 17 | Veo 3.1 | 1089 | no | 24.00 | 0.40 |
| 19 | Veo 3.1 Lite | 1087 | no | 4.80 | 0.08 |
| 20 | Veo 3.1 Fast | 1084 | no | 9.00 | 0.15 (stale; list now $0.10–0.12) |
| 23 | Sora 2 Pro | 1074 | no | 30.00 | 0.50 |
| 24 | **LTX-2.5 Fast** | 1072 | **yes** | 7.80 | 0.13 (= 1080p list) |
| 25 | Grok Imagine | 1062 | no | 4.20 | 0.07 |
| 26 | **LTX-2.5 Pro** | 1058 | **yes** | 10.20 | 0.17 |

**Image-to-video**
- H3 Max (fal) 1206 at $2.40 · Seedance 2.0 1197 · **H3 1190** · **HiDream-O1-Video 1186 at $5.80 (≈$0.097/s; no public API found)** · Gemini Omni Flash 1181 · Wan 3.0 1179 · Grok Imagine 1.5 1116 at $8.40 · Veo 3.1 Fast 1076 · Kling 3.0 720p 1072 · Veo 3.1 Lite 1072 · **LTX-2.5 Fast 1048** · **LTX-2.5 Pro 1012**.

**Read-across**
- **H3 is the top open-weights model**, in the same quality band as Seedance 2.0, Gemini Omni Flash and Wan 3.0 ($0.10–0.20/s).
- **fal's H3 Max** sells top-3 quality at $0.08/s list ($0.04 Turbo).
- **LTX-2.5 sits with Veo 3.1 Lite/Fast, Grok Imagine and Sora 2 Pro** in quality (Elo ≈1060–1090). That band's 720p prices are $0.05–0.10/s, yet Lightricks lists LTX-2.5 at $0.09–0.13/s.
  - LTX-2.5 therefore has to win on price, openness, 4K/50 fps/20 s, or privacy, not on quality.

---

## 4. Consumer and prosumer plans

### 4A. Cross-product summary: implied $ per 5 s 720p clip

"Entry" = cheapest paid plan, monthly billing. "Best" = the plan with the lowest per-clip cost, usually top tier on annual billing.

| Product | Entry plan (price, credits) | Cheapest model, entry → best | Flagship, entry → best | LTX / H3 price where offered | Free tier | Annual discount | Rollover | Failed gen refunded? | Moderation-blocked charged? | Tag |
|---|---|---|---|---|---|---|---|---|---|---|
| **Runway** | Standard $15 ($12 A), 625 cr | Gen-4 Turbo: $0.60 → $0.20 | Gen-4.5: $1.44 → $0.48 | – | 125 one-time credits, watermark | 20% | No (Max: 1 month); bought credits never expire | Yes, on generation error [S] | **Yes**: "moderated generations have the same credit cost as successful generations" [S excerpt] | [C] plans |
| **Kling app** | Standard $10 ($6.60 A), 660 cr | 2.5 Turbo: $0.23 → $0.07 | 3.0 silent: $0.45 → $0.14; with audio $0.68 | – | 66 cr/day, 360–540p, watermark, non-commercial | 34% | No; top-ups valid 2 years | No official text; secondaries say no auto-refund (conflict) | not found | [S] |
| **Hailuo app** (6 s 768p) | Standard $14.99, 1,000 cr | 2.3 Fast: $0.22–0.30 → $0.15–0.20 | 2.3: $0.37–0.52 → $0.25–0.35; H3 30–80 cr [S] | H3 ≈$0.45–1.20 per clip (Standard) [U] | watermark; 200 one-time or daily bonus (conflict) | not found | No; top-ups to Dec 31 of year 2 | **Yes** | **No**: refunded if content "does not pass the review" | [C-dated 2025-07-14] + [S] prices (4 conflicting ladders) |
| **Pika** | Standard $10 ($8 A), 700 cr | Pika 2.5: $0.29 → $0.23 (higher tiers are *not* cheaper per clip) | same | – | 80 cr/mo, 480p only, watermark, non-commercial | 20% | No; top-ups never expire | No: "charged regardless of success or failure" [S] | not found | [C]/[S] |
| **Luma Dream Machine** | Plus $30 ($25 A), 10,000 cr | Ray3.14 Draft: $0.06 → $0.033 | Ray3.14 720p: $0.30 → $0.167 | – | none on current page (old: draft-only) | 16.7% | No; top-ups 12 months | **Yes** [C billing policy] | not found | [C] |
| **Higgsfield** | Starter $19, 270 cr | Kling 3.0: $0.49 → $0.23; **$0 on "Unlimited" models** (web, 1 at a time, ≤15 s) | Seedance 2.0: $1.08 (Plus) → $0.73 | – | limited models; $3 for 40 cr | 20–23% | No; packs 90 days, need subscription | **Yes**, except Grok [C] | **No** for most models: NSFW-flag credits returned [C] | [S] plans, [C] help |
| **Krea** | Basic $9 ($5.25 A), 5,000 CU | Seedance 2.0 ≈240 CU: $0.43 → $0.25 | Veo 3: $1.78 → $1.07 [U] | – | 100 CU/day | 40% | No (Business: yes); packs 90 days | App: not found; API: not debited [U] | not found | [C]/[S] |
| **LTX Studio** | Lite $15 ($12 A), 8,000 cr | per-clip credits **not published**. Snippet: LTX-2.5 Fast 3/4/5/6 cr/s at 720p/1080p/2K/4K → **≈$0.014–0.028 per 5 s 720p** [U] | Veo 3.1 on Pro only | LTX-2.5 [U] as left | 800 one-time credits, personal use | 20% | No | **Yes**: "Blocked or failed generation won't cost you anything" [C] | **No** [C] | [C] plans |
| **OpenArt** | Starter $14 ($13 A), 4,000 cr (~50 videos) | ~80-cr video: $0.28 → $0.13 | Kling 5 s = 500 cr: $1.75 → $0.83 [S, stale] | LTX 2.3 offered [U] | small grant | 7–27% | No; add-ons roll over | Yes, "in most cases" [C] | not stated | [C] |
| **Freepik → Magnific** | Premium $20 ($14.50 A), 20,000 cr | Kling 2.5 720p (140 cr): $0.14 → $0.09; **$0 on unlimited models** (Premium+) | Veo 3.1 720p (1,000 cr): $1.00 → $0.66 | **LTX 2 Fast 1080p $0.40 → $0.26; H3 768p $0.46 → $0.31; H3 Max Turbo 768p $0.10 → $0.07** | 20 images/day, no video | 25–27.5% | No; annual credits 1 year; extras 3 years | not found | not found | [C] magnific.com docs |
| **Invideo** | Starter $20 (A), 400 cr | LTX 2.5 720p (5.2 cr per 5 s-eq): $0.26 → $0.10 | Veo 3.1: $2.00 → $0.80 | **LTX 2.5 $0.26 → $0.10; H3 Max Turbo 480p $0.30 → $0.12; H3 2K $1.56 → $0.62** | weekly-reset quota | 17–33% | No | not found | not found | [C]; plan-lineup conflicts |
| **Hedra** | Basic $15, 1,500 cr | Hailuo 2.3 Fast (20 cr): $0.20 → $0.10 | Veo 3.1 (275 cr): $2.75 → $1.43 | LTX-2.3 via API only | 100 cr, watermark [U] | not found | No; packs never expire | "may be refunded automatically" [C] | not found | [C] docs / [S] credits |
| Vidu (consumer) | Standard $8 (A), 800 cr | ~4-cr cheapest video ≈$0.04; Q3 720p off-peak 75 cr ≈ $0.75 [U] | – | – | 10 references or 40 cr/mo | – | 30 days; purchased 2 years | not found; no refunds at all | not found | [C] |
| PixVerse (consumer) | Standard $10 ($8 A), 1,200 cr [S] | 720p 5 s ≈60 cr: $0.50 → $0.19 [U] | – | – | 60 + 30/day, 540p, watermark | 20–40% | No; bonus credits never expire | not found | not found | [C]/[S] |
| Midjourney | Basic $10 ($8 A), 3.3 fast GPU-hr | SD video ≈$0.13 per 5 s clip (derived) | HD ≈$0.43 | – | none | 20% | Relax mode unlimited on Standard+ | – | – | [S] |

### 4B. Plan details: prices and credit costs

**Runway** [C runway.com/pricing]
- **Plans:**

  | Plan | Monthly | Annual (per month) | Credits |
  |---|---|---|---|
  | Free | $0 | – | 125 one-time |
  | Standard | $15 | $12 | 625 |
  | Pro | $35 | $28 | 2,250 |
  | Max | $95 | $76 | 9,500 |

- **Top-up:** minimum 1,000 credits at $10 per 1,000 [S].
- **Credit costs:**
  - Gen-4.5: 60 credits per 5 s.
  - Gen-4 Turbo: 25 per 5 s [S].
  - Aleph 2: 140 per 5 s.
  - Seedance 2.0 Pro 1080p: 160 per 4 s.
  - Seedance 2.0 Fast: 116 per 4 s.
- **Max vs old Unlimited:** Max replaced the old Unlimited plan in 2026 [S creatify 2026-09-10]. Parallel generations: 5 / 15 / 20 (Standard / Pro / Max).

**Kling app** [S techsifted 2026-09-07; eesel 2026-06-05; aitoolanalysis 2026-07-03]
- **Plans:**

  | Plan | Monthly | Annual (per month) | Credits |
  |---|---|---|---|
  | Standard | $10 | $6.60 | 660 |
  | Pro | $37 | $24.42 | 3,000 |
  | Premier | $92 | $60.72 | 8,000 |
  | Ultra | $180 | – (annual availability conflicts) | 26,000 |

- **Credit costs, Kling 3.0:**

  | | 720p | 1080p |
  |---|---|---|
  | No audio | 6 cr/s | 8 cr/s |
  | Audio | 9 cr/s | 12 cr/s |

  Voice control adds 2 cr/s. 2.5 Turbo 720p 5 s = 15 credits.
- **Top-ups:** $5 = 330 credits up to $1,200 = 96,000 credits ($0.0152–0.0125 per credit).
- **Price history:** Ultra went from $128 (Aug 2025) to $180 (Jan 2026), +41% [S].

**Hailuo app** [C-dated hailuoai.video/doc/payment-policy.html]
- **Plans:**

  | Plan | Monthly | Credits |
  |---|---|---|
  | Standard | $14.99 | 1,000 |
  | Pro | $54.99 | 4,500 |
  | Master | $119.99 | 10,000 |
  | Ultra | $124.99 | 12,000 |
  | Max | $199.99 | 20,000 plus unlimited Relax |

- **Top-up:** $1 = 70 credits.
- **Conflicting 2026 price ladders** [S]:
  - atlascloud: $7.99 / $27.99 / $63.99 / $199.99, with ~47–49% annual discount.
  - costbench: $7.99 / $24.99 / $63.99 / $199.99.
  - imagine.art: $9.99 / $34.99 / $79.99 / $124.99 / $199.99.
  - aiarty: $14.99 / $54.99 / $119.99, plus Max $216 for 27,000 credits.

**Pika** [C pika.art/pricing]
- **Plans:**

  | Plan | Monthly | Annual (per month) | Credits |
  |---|---|---|---|
  | Standard | $10 [S] | $8 | 700 |
  | Pro | $35 | $28 | 2,300 |
  | Fancy | $95 | $76 | 6,000 |

- **Pika 2.5, 5 s clip:** 480p 12 credits, 720p 20, 1080p 40.
- **Top-ups:** $10 = 375 credits [S].

**Luma** [C]
- **Plans:**

  | Plan | Monthly | Annual (per month) | Credits |
  |---|---|---|---|
  | Plus | $30 | $25 | 10,000 |
  | Pro | $90 | $75 | 40,000 |
  | Ultra | $300 | $250 | 150,000 |

- **Ray3.14 credit costs:** Draft 4 cr/s, 540p 10, 720p 20, 1080p 80.
- **Ray3.2:** text-to-video 720p = 100 credits per 5 s.
- **Top-up:** $4 = 1,200 credits.
- **Refund policy:** "Credits used for failed generations will be automatically returned to your account." (lumalabs.ai/legal/billing-policy)

**Higgsfield**
- **Plans** [S creatify 2026-09-10; scopeful 2026-08-07]:

  | Plan | Monthly | Annual (per month) | Credits |
  |---|---|---|---|
  | Starter | $19 | – | 270 |
  | Plus | $59 | $47 | 1,200 |
  | Ultra | $129 | $99 | 3,000 |
  | Team | $79 per seat | – | – |

- **Credit costs per 5 s:** Kling 3.0 720p 7 credits; Seedance 2.0 720p 22–23; Wan 2.7 ~8.
- **Unlimited models** [C help center 2026-08-28]: "365-day Unlimited access" on most; newest flagships "7 days".

**Krea** [C krea.ai/pricing; S pikes.ai 2026-08-11]
- **Plans:**

  | Plan | Monthly [S] | Annual (per month) [C] | Compute units |
  |---|---|---|---|
  | Basic | $9 | $5.25 | 5,000 |
  | Pro | $35 | $21 | 20,000 |
  | Max | $105 | $63 | 60,000 |
  | Business | $200 | $160 | 80,000 |

- **Krea API prices** [C krea.ai/app/api/pricing]:
  - Veo 3.1: from $0.84.
  - Kling 3.0: from $0.1764/s.
  - Seedance 2.0: from $0.0849/s.
  - Hailuo 2.3: from $0.28 per video.

**LTX Studio** [C ltx.io/studio/pricing; help.ltx.io]
- **Plans:**

  | Plan | Monthly | Annual (per month) | Credits |
  |---|---|---|---|
  | Free | $0 | – | 800 one-time |
  | Lite | $15 | $12 | 8,000 |
  | Standard | $35 | $28 | 28,000 (+28,800 computing seconds for 3 months) |
  | Pro | $125 | $100 | 110,000 |

- **Commercial use:** Standard and above.
- **Refund policy:** "Blocked or failed generation won't cost you anything. Any credits deducted are returned to your account automatically."
- **Subscription refund:** within 14 days if usage is ≤1,200 credits.

**OpenArt** [C openart.ai/pricing]
- **Plans:**

  | Plan | Monthly | Annual (per month) | Credits |
  |---|---|---|---|
  | Starter | $14 | $13 | 4,000 |
  | Plus | $34 | $27 | 12,000 |
  | Pro | $56 | $44 | 24,000 |
  | Wonder | $240 | $175 | 106,000 |

- **Add-on:** $15/mo for 5,000 credits; rolls over.
- **Refund policy:** "Do I lose credits if a generation fails? No. In most cases… refunded automatically."

**Magnific (Freepik)** [C magnific.com/pricing and /ai/docs]
- **Plans:**

  | Plan | Monthly | Annual (per month) | Credits |
  |---|---|---|---|
  | Premium | $20 | $14.50 | 20,000/mo |
  | Premium+ | $45 | $33.75 | 45,000/mo |
  | Pro Starter | $110 | $82.50 | 112,500/mo |

- **Credits per second** (resolutions in brackets):

  | Model | Credits/s |
  |---|---|
  | LTX 2 Fast | 80 / 160 / 320 (1080p / 1440p / 2160p) |
  | LTX 2 Pro | 120 / 230 / 480 |
  | MiniMax H3 | 75 / 92 / 110 (480p / 768p / 2K) |
  | H3 Max | 55 / 80 / 150 |
  | H3 Max Turbo | 12 / 20 |
  | Kling 3.0 | 70 / 90 / 400 (720p / 1080p / 4K) |
  | Veo 3.1 | 200 / 200 / 340 |
  | Veo 3.1 Lite | 40 |
  | Seedance 2.0 | 145 / 280 / 700 / 1,400 (480p / 720p / 1080p / 4K) |
  | Wan 3.0 | 60 / 120 / 240 |

- **Unlimited on Premium+ and above:** Kling 2.5 720p, Hailuo 2.3 / 2.3 Fast 768p, Seedance 1.5 Pro draft.
  - Fair use: "no cap… only speed varies".
- **Subscription refund:** 30 days, but not if any credits were used.

**Invideo** [C invideo.io/pricing; invideo.io/help/billing/video-model-pricing]
- **Plans:**

  | Plan | Monthly | Annual (per month) | Credits |
  |---|---|---|---|
  | Starter | – | $20 | 400 |
  | Plus | $60 | $50 | 2,000 |
  | Max | $150 | $100 | 5,000 |

- **Credit cost ranges** (cheapest to dearest setting):
  - LTX 2.5: 6.24–288 (720p–1440p, 6–20 s).
  - LTX 2.3 Pro: 4.80–308.
  - H3 Max Turbo: 6.00–57.60 (480p–1080p, 5–15 s).
  - H3 Max: 12.00–115.20.
  - MiniMax-H3: 31.20–93.60 (2K).
  - Veo 3.1 Lite: 4.80–25.60.
  - Kling 3.0: 10.08–252.

**Hedra** [C hedra.com docs; S usagepricing 2026-08-28]
- **Plans:**

  | Plan | Monthly | Credits |
  |---|---|---|
  | Basic | $15 | 1,500 |
  | Creator | $30 | 5,400 |
  | Professional | $75 | 14,400 |

- **Credits per second:**

  | Model | Credits/s |
  |---|---|
  | Hailuo 2.3 Fast Std | 4 |
  | Character-3 | 6 |
  | Hailuo 2.3 Std | 6 |
  | Kling 2.5 Turbo | 10 |
  | Veo 3.1 Fast | 20 |
  | Veo 3.1 | 55 |
  | Sora 2 Pro | 70 |

### 4C. Consumer-plan patterns
- **Entry-plan price points:** $8–20/mo. Annual discounts are 16.7–40%, typically 20%.
- **What a 5 s 720p clip costs on entry plans:**
  - Cheapest decent model: $0.14–0.60 (median ≈ $0.30).
  - Flagship (Veo 3.1, Kling 3.0 with audio, Seedance 2.0): $0.45–2.75.
  - Best annual top tiers: $0.07–0.25 for cheap models.
- **"Unlimited" slow lanes are table stakes at the top end:** Hailuo Max Relax, Higgsfield Unlimited, Magnific Premium+ unlimited models, Midjourney Relax. The marginal price of old or cheap models there is $0.
- **Monthly credits almost never roll over.** Exceptions: Runway Max (1 month), Krea Business. Purchased packs last from 90 days (Higgsfield, Krea) to 12 months (Luma) to never (Runway, Pika, Hedra).
- **Top-up premium vs plan-included credits ranges from −5% to +120%** [D]:
  - Pika: top-up $0.0267/cr vs Standard $0.0143 (+87%).
  - Kling: top-up $0.0152 vs Ultra $0.0069 (+120%).
  - Luma: $0.00333 vs Plus $0.003 (+11%).
  - Hailuo: $0.0143 vs Standard $0.015 (−5%).
  - Runway: top-up $0.01 vs Standard $0.024 (−58%; top-ups are cheaper than the entry plan).
- **Failed generations:** refunded at Luma, LTX Studio, Hailuo, Higgsfield, OpenArt, Hedra and Runway (errors only). Charged at Pika [S] and, per secondaries, the Kling app.
- **Moderation-blocked prompts:** refunded at LTX Studio, Hailuo and Higgsfield (most models). **Charged at Runway** [S]. Not published elsewhere.

---

## 5. The privacy premium

### 5A. Same open model: TEE vs normal providers ($ per 1M tokens, input/output) [C public APIs, 2026-09-14]

**Method:** the privacy thread compared 53 TEE rows against the median of all non-TEE OpenRouter endpoints for the same model. Blend weights input 3 : output 1.

| Model | TEE provider | TEE price | Non-TEE median (n) · cheapest | Premium vs median (blend) | vs cheapest |
|---|---|---|---|---|---|
| gpt-oss-120b | Phala (OpenRouter) = Tinfoil = Redpill | 0.15 / 0.60 | 0.12 / 0.60 (22) · AkashML 0.03 / 0.17 | **+9%** | +304% |
| gpt-oss-120b | Venice E2EE / PPQ / Privatemode | 0.13 / 0.65 · 0.16 / 0.63 · €0.43 / €1.70 | same | **+8% / +16% / +260%** | – |
| GLM-5.3 | Phala | 1.12 / 3.52 | 1.35 / 4.40 (25) · Morph 0.92 / 3.14 | **−19%** | +17% |
| GLM-5.3 | Redpill / NanoGPT · Venice E2EE · Tinfoil · PPQ · Privatemode | 1.40 / 4.40 · 1.75 / 5.50 · 1.80 / 5.75 · 1.90 / 6.07 · €1.55 / €7.74 | same | **+2% · +27% · +32% · +39% · +69%** | – |
| Kimi K3 | Chutes / NanoGPT / Redpill · Phala · NEAR AI · Venice · Tinfoil · PPQ | 3 / 15 · 2.85 / 14.25 · 3.30 / 16.50 · 3.75 / 18.75 · 4 / 20 · 4.22 / 21.10 | 3.00 / 15.00 (18) | **0% · −5% · +10% · +25% · +33% · +41%** | – |
| Kimi K2.6 | Chutes (int4) · NEAR AI · Venice · Phala · NanoGPT · Privatemode | 0.58 / 3.40 · 0.81 / 3.85 · 0.87 / 4.12 · 1.09 / 4.60 · 1.50 / 5.25 · €1.55 / €7.74 | 0.785 / 3.50 (18) | **−12% · +7% · +15% · +34% · +66% · +144%** | – |
| DeepSeek V3.2 | Phala / Chutes · NEAR AI | 1.00 / 1.00 · 1.10 / 1.10 | 0.269 / 0.42 (13) | **+226% · +259%** | +327% |
| Llama 3.3 70B | Tinfoil / Redpill / NanoGPT / PPQ | 1.75–2.00 / 2.00–2.90 | 0.371 / 0.72 (12) · DeepInfra 0.10 / 0.32 | **+336% to +361%** | ≈+1,200% |
| DeepSeek V4 Flash | NEAR AI · Venice · Phala · NanoGPT · Tinfoil | 0.17 / 0.35 · 0.18 / 0.37 · 0.20 / 0.40 · 0.20 / 0.40 · 0.30 / 0.70 | 0.13 / 0.268 (15) | **+31% · +40% · +52% · +52% · +143%** | – |
| Gemma 4 31B | Chutes · Redpill · Tinfoil · PPQ | 0.12 / 0.37 · 0.15 / 0.46 · 0.40 / 1.00 · 0.42 / 1.05 | 0.145 / 0.40 (12) | **−13% · +9% · +163% · +177%** | – |
| Qwen3.8 27B | Phala · Chutes · NanoGPT · NEAR AI · Venice | 0.24 / 2.20 · 0.32 / 2.50 · 0.40 / 3.00 · 0.44 / 3.30 · 0.47 / 3.53 | 0.30 / 2.55 (11) | **−15% · 0% · +22% · +34% · +43%** | – |
| GLM-5.3 Flash | Phala / NEAR AI / NanoGPT · Venice · Tinfoil | 0.15 / 0.50 · 0.16 / 0.54 · 0.40 / 1.25 | 0.15 / 0.50 (26) | **0% · +7% · +158%** | – |

**Summary**
- **Median premium over all 53 TEE rows: +31%.** Middle half +7% to +104%; full range −19% to +733% (NanoGPT's gpt-oss outlier).
- **Big TEE hosts** (Chutes, Phala, NEAR AI): **0% to +10%**, sometimes below median. Some rows use lower-precision (int4/fp4) weights.
- **Boutique enclave vendors** (Tinfoil, Privatemode, PPQ): **+30% to +340%**.
- **Venice E2EE vs Venice's own standard twin:** 0% to +104%, **median ≈ +22%**.
- **My independent Phala-only check** (17 models): median ≈ 0–10% over the non-TEE median, typically +50% to +150% over the cheapest provider. Consistent with the above.
- Source data: `or_tee_endpoints.json` in the scratchpad.

### 5B. Confidential AI providers: what "private" means and what it costs

| Provider | Mechanism | Prices | Image / video? | Tag |
|---|---|---|---|---|
| Tinfoil | Hardware enclaves with client-side attestation (NVIDIA CC GPUs [S]) | Private Chat **$20/mo** ("up to 1M tokens/hour"). API: gpt-oss-120b 0.15/0.60; GLM-5.3 1.80/5.75; Kimi K3 4/20. Containers: H200 $2,000/GPU-month (≈$2.74/hr), B200 $5,000/GPU-month, $20/mo base | No | [C] tinfoil.sh/pricing (embedded JSON), inference.tinfoil.sh |
| Privatemode (Edgeless) | End-to-end encryption plus confidential computing | Free: 5M tokens at signup + 1M/mo. PAYG from €1.27 per 1M output. Kimi-K2.6 / GLM-5.3 €1.55 / €7.74; gpt-oss-120b €0.43 / €1.70 | No | [C] privatemode.ai/pricing |
| NEAR AI Cloud | Intel TDX + H200; some models proxied from Chutes TEE | Kimi K3 3.30/16.50 (= 1.1× Chutes). **FLUX.2-klein-4B attested image generation $0.012/image** | **Image: yes** | [C] cloud-api.near.ai |
| Venice | "Private" = no logs; "anonymized" = proxied; E2EE/TEE on text models only | Free · Pro $18 · Pro Plus $68 · Max $200. E2EE 0% to +104% over standard. Images $0.01–0.29. Video per second, "under 80 credits (~$0.80) per ~5 s video" | Images and video, **not TEE** | [C] venice.ai/pricing, docs.venice.ai |
| Redpill (Phala) | TEE gateway over Phala, Chutes, NEAR, Tinfoil, SecretAI | Pass-through prices; Pro $35/mo [S] | No | [C] api.redpill.ai |
| Phala Cloud | TDX + NVIDIA CC | GPU TEE: H100 $3.08/hr (reserved $2.38), H200 $4.80 ($3.20), B300 $6.50; 24h / 30-day minimums. CPU TDX $0.06–0.23/hr | – | [C] phala.com/gpu-tee |
| Chutes (SN64) | All 491 public chutes `tee=true` | Plus $10 / Pro $20 per month; $0.0005/GPU-s for media chutes; private RTX PRO 6000 $1.80/hr + $5.40 setup | **TEE image and video chutes exist** (z-image-turbo, imageclassic, turbowani2v, LTX-25-Video) | [C] |
| NanoGPT / PPQ.AI | "TEE/" model prefixes; PPQ resells Tinfoil at ≈+5.5% | See 5A | No | [C] |
| Apple Private Cloud Compute | Apple silicon, Secure Enclave, stateless, published images | **Free** with Apple Intelligence; no per-request cost to developers | Image Playground on device/PCC | [C] |
| Darkbloom (OpenRouter) | Encrypted inference on Apple-silicon Macs (not GPU TEE) | 30–46% **below** median | No | [C] |
| Proton Lumo | Zero-access storage, no logs; no TEE claim | Lumo Plus ≈$12.99/mo | Images (no TEE) | [S] factually.co; [C] proton.me/lumo |

### 5C. Confidential GPU / VM vs normal ($/hr on demand)

| Offering | Confidential | Normal equivalent | Premium | Tag |
|---|---|---|---|---|
| Azure NCC40ads H100 v5 vs NC40ads H100 v5, East US 2 | $6.98 | $6.98 | **0%** | [C] prices.azure.com |
| same, Central US / South Central US / West Europe | $7.89 / $7.89 / $8.90 | $8.585 / $8.38 / $9.08 | **−8% / −6% / −2%** | [C] |
| Phala H100 TEE | $3.08 | RunPod H100 SXM $2.69 (Community) / $3.49 (Secure) | +14.5% / −12% | [C] |
| Phala H200 TEE | $4.80 | RunPod H200 $3.59 / $4.59 | +34% / +5% | [C] |
| GCP a3-highgpu-1g confidential (TDX + H100) | surcharge $0.439/hr Spot, $0.512/hr Flex-Start; **no on-demand option** | base not obtained | – | [C] |
| GCP G4 confidential (RTX PRO 6000) | +$0.45/hr, plus $0.08/GPU-hr NVIDIA CC licence | – | – | [C] |
| Chutes RTX PRO 6000 (TEE) | $1.80 | Chutes non-TEE: n/a (all TEE) | 0% visible | [C] |
| AWS | no GPU confidential-computing product | – | – | [C] |

### 5D. Zero-data-retention, residency and enterprise privacy surcharges

| Vendor | Zero data retention | Residency / regional | Other | Tag |
|---|---|---|---|---|
| OpenAI | By approval (sales); no price | **+10%** on data-residency endpoints for models released ≥2026-03-05 (US, EU, AU, CA, JP, IN, SG, KR, UK, UAE) | Fast (ex-Priority) ≈2×; Batch/Flex −50% | [C] developers.openai.com pricing and your-data docs |
| Anthropic | Not priced on the page | `inference_geo:"us"` = **1.1×** (Claude 4.6+); Bedrock/Vertex regional **+10%** over global (4.5+) | Fast mode 2× (Opus 5) | [C] platform.claude.com pricing |
| Google Vertex | No price; exception request needed; Search grounding keeps logs | **+10%** on non-global endpoints for Gemini 3+ from 2026-07-01 | – | [C] |
| Azure OpenAI | – | Data Zone **+10%** and Regional **+10%** over Global | – | [C] prices.azure.com |
| AWS Bedrock | – | Regional +10% (per Anthropic docs) | Priority +75%; Flex −50% | [C]/[S] |
| Claude seats | Team: no training by default | – | Pro $20 (M) / $17 (A); Team Standard $25 / $20; privacy bundled, not surcharged | [C] claude.com/pricing |

### 5E. Private or confidential image and video generation
- **No private-video product exists anywhere.** [C for the providers checked; search coverage limited]
- **Raw TEE compute exists:**
  - Chutes `LTX-25-Video` (0 instances, 0 calls since Sep 8).
  - Chutes `turbowani2v` (≈30/day).
  - NEAR AI attested FLUX.2-klein image generation at **$0.012/image**.
- **No hardware guarantee:** Venice's video and image generation is no-log only. Its docs say "TEE and E2EE are currently available on text models only".
- **No image or video models:** Tinfoil, Privatemode, Redpill/Phala, NanoGPT TEE, PPQ TEE, Fortanix, Opaque, Super Protocol.

### 5F. Positioning analogues (privacy as a product)

| Product | Price | Non-private alternative | Tag |
|---|---|---|---|
| Proton Mail Plus / Unlimited | $4.99 M ($3.99 A) / $12.99 M ($9.99 A) | Gmail: free | [S] costbench, Jul 2026 |
| Lumo Plus (Proton AI) | ≈$12.99/mo | ChatGPT free tier | [S] |
| Mullvad VPN | €5/mo flat since 2009; **10% off for crypto**; cash accepted | – | [C] |
| Kagi | $5 / $10 / $25 per month | Google: free | [C] |
| Signal | Free, donation-funded non-profit | WhatsApp: free | [C] |
| Apple PCC | Free, bundled | – | [C] |
| Private AI chat | Venice Pro $18 · Tinfoil $20 · Chutes Pro $20 · Redpill Pro $35 [S] | Claude Pro $20 [C] | [C] |
| Enterprise residency | +10% (OpenAI, Anthropic, Google, Azure, Bedrock) | global endpoint | [C] |

### 5G. Conclusions on the privacy premium
- **What buyers already pay for the same model, private vs normal:**
  - LLM tokens: **+0–10%** at scale TEE hosts; **+22–31%** median across all TEE offerings; **+30–340%** at boutique privacy brands.
  - Enterprise residency and sovereignty: **+10%** is the industry standard.
  - Confidential GPUs themselves cost 0% (Azure) to +34% (Phala vs RunPod).
- **Consumers pay for privacy brands in absolute dollars:** $4–20/mo (Proton, Kagi, Mullvad, Tinfoil, Venice), but the big platforms bundle privacy for free (Apple PCC, Signal, Claude Team).
- **For video there is no reference price because there is no product.** KunoWorld's Private mode would be uncontested. The only substitute is self-hosting on a TEE GPU: Phala H200 at $4.80/hr with a 24h minimum (≥$115/day), or ≈$2.74/hr per H200 on Tinfoil containers ($2,000/GPU-month).

---

## 6. Price trends (≈ Sep 2025 → Sep 2026) and the low-end price war

### 6A. Before/after pairs

| Model / vendor | Before (date) | After (date) | Resolution | Change | Tag / source |
|---|---|---|---|---|---|
| **Google Veo 3** | $0.75/s with audio (2025-07-17 launch) | $0.40/s (2025-09-08) | 720p (1080p added) | **−46.7%** | [C] developers.googleblog.com (launch and price-cut posts); Wayback 2025-09-16 |
| **Veo 3 Fast** | $0.40/s (before 2025-09-08) | $0.15/s (2025-09-08) | 720p/1080p | **−62.5%** | [C] same |
| **Veo 3.1 Fast** | $0.15/s (Wayback 2025-10-26) | $0.10 at 720p / $0.12 at 1080p (by 2026-04-02; "Apr 7" per Medium) | 720p / 1080p | **−33% / −20%** | [C] Wayback + current; [S] date |
| Google's cheapest Veo with audio | Veo 3 Fast $0.15 (Sep 2025) | Veo 3.1 Lite $0.05 (launched 2026-03-31) | 720p | **−66.7%** | [C] changelog |
| Veo 3.1 Standard | $0.40 (Oct 2025) | $0.40 (+4K $0.60) | 720p/1080p | 0% | [C] |
| Veo 2 | $0.35/s (Wayback 2025-07-10) | Retired on Gemini API 2026-06-30 (Vertex still lists $0.50) | – | exit | [C] |
| **Sora 2 / Sora 2 Pro** | $0.10 / $0.30 per s (Oct 2025 launch) | Same, then **removed 2026-09-24** | 720p | 0%, then exit | [S] launch; [C] deprecation |
| Runway Gen-4 Turbo | $0.05 (Wayback 2025-07-15) | $0.05 | – | 0% | [C] |
| Runway Aleph → Aleph 2 | $0.15/s (Wayback 2025-10-06) | $0.28/s + 56-credit minimum | – | **+87%** (successor) | [C] |
| Runway resale of Veo 3.1 Fast | $0.15 (Apr 2026) | $0.15 (Google cut to $0.10, not passed on) | – | 0% | [C] |
| **LTX-2 → 2.3 → 2.5 Fast** (Lightricks API) | LTX-2 Fast $0.04/s (fal Nov 2025; ltx.io Wayback 2026-01-07) | 2.3 Fast $0.06 (May 2026) → **2.5 Fast $0.13 (Aug 2026)** | 1080p | **+50% / +225%** | [C] |
| LTX-2 → 2.3 → 2.5 Pro | $0.06 | $0.08 → **$0.17** | 1080p | **+33% / +183%** | [C] |
| Same SKU, fal LTX-2 Fast | $0.04 (Nov 2025) | $0.04 (deprecation notice 2026-08-15) | 1080p | 0% | [C] |
| fal LTXV-13B 0.9.8 distilled | $0.02/s (Wayback 2025-09-04) | $0.02/s | – | 0% | [C] |
| **Kling** | 2.5 Turbo launch (2025-09-23): ≈$0.07/s (fal), $0.35 per 5 s 1080p (Novita). Kuaishou: 1080p 5 s dropped 35 → 25 credits (−29% vs 2.1) | Kling 3.0 official: $0.112/s silent at 1080p; 3.0 Turbo with audio $0.14 | 1080p | **+60%** (successor, silent); 2.1 → 2.5 Turbo **−29%** | [S] ir.kuaishou.com, Novita blog; [C] kling.ai/dev |
| Kling app Ultra plan | $128/mo (Aug 2025) | $180/mo (Jan 2026) | – | **+41%** | [S] |
| **MiniMax Hailuo → H3** | Hailuo 02 Standard 768p $0.045/s (fal, mid-2025); official Hailuo-02 768P 6 s $0.28 ($0.047/s, still listed) | H3 768P $0.08/s (2026-07-29); **fal H3 Max Turbo $0.04/s list** (2026-09-15) | 768p | H3 **+70%** (successor); H3 Max Turbo **−11%** with a large quality jump (AA 1231) | [S] fal 2025; [C] MiniMax, fal |
| **ByteDance Seedance** | Seedance 1.0 Pro 1080p 5 s ≈ $0.62 ($2.5/M tokens, 2025) | Seedance 2.0 1080p 5 s **$1.87** (Apr 2026); **2.0 Mini 720p 5 s $0.38** (2026-08-12); 1.5 Pro 1080p 5 s $0.58 with audio | 1080p / 720p | 2.0: **+200%** (successor); Mini is the new floor | [S] BytePlus 2025 blog; [C] OpenRouter, BytePlus 2026 |
| **Alibaba Wan** | Wan 2.5 (2025-09-24): $0.05 / $0.10 / $0.20 per s | Wan 3.0 (2026-08-06): $0.05 / $0.10 / $0.20; launch promo $0.035 / $0.07 / $0.14; global region −17.5% | 480p / 720p / 1080p | **0%** list (−30% promo) | [S] 2025; [C] 2026 |
| WaveSpeed Wan 2.2 720p | $0.40 per 5 s (old notes, [S]) | $0.30 per 5 s | 720p | −25% (date uncertain) | [S] → [C] |
| xAI Grok Imagine → 1.5 | $0.05 (480p) / $0.07 (720p) | 1.5: $0.08 / $0.14 / $0.25 (2026-07-20) | 480p / 720p | **+60% / +100%** (successor) | [C] |
| Frontier-quality video with audio | Veo 3 $0.40/s (Sep 2025; top of arena then [U]) | AA top-3 H3 Max $0.08/s list; Gemini Omni Flash $0.10; Wan 3.0 $0.10 at 720p | 720p | **−75% to −80%** | [C] current; [U] 2025 rank |
| Cheapest good 5 s 720p clip with audio (first party) | Veo 3 Fast $0.75 (5 s-eq, Sep 2025) | Veo 3.1 Lite $0.25; fal H3 Max Turbo $0.20 (768p) | 720p | **−67% to −73%** | [C] |

### 6B. Summary statistics
- **Same model, same resolution:** 13 pairs from the trends thread plus Wan and Kling. Median change **0%**. Every real cut came from Google: −20%, −33%, −47%, −63%; median of cuts ≈ −40%.
- **Successor models launch at higher per-second prices:**
  - LTX 2 → 2.5: +183–225%.
  - Seedance 1.0 → 2.0: +200%.
  - Hailuo 02 → H3: +70%.
  - Aleph → Aleph 2: +87%.
  - Kling 2.5 Turbo → 3.0: +60%.
  - Grok Imagine → 1.5: +60–100%.
- **Quality-adjusted prices fell sharply.** Cheap tiers of new models (Veo 3.1 Lite, Seedance 2.0 Mini, H3 Max Turbo, Wan 3.0) now deliver 2025-frontier quality or better at **$0.04–0.10/s**. That is −65% to −80% versus Sep 2025's $0.15–0.40/s for top quality with audio.

### 6C. Is there a price war at the low end? **Yes. At the premium end, no.**
- **Launch promos are deep:**
  - fal H3 Max / Turbo: 75% off list until 2026-09-14.
  - Wan 3.0: −30% until ~Sep 24.
  - fal H3 Max free tier: 5 generations/day.
- **Sub-$0.05/s first-party tiers:**
  - Veo 3.1 Lite silent: $0.03.
  - Seedance Mini 480p: $0.034–0.04.
  - H3 Max Turbo 768p: $0.04.
  - Pika 2.5 720p: $0.04.
  - Vidu Q3-turbo off-peak: $0.03.
- **Resellers undercut first-party prices:**
  - Pika API resells Wan 3.0 at −35% and Kling 3.0 at −19%.
  - Unifically resells Veo 3.1 Lite "relaxed" at ≈$0.047 per 5 s [S].
  - Replicate lists LTX-2.5 Fast at a third of Lightricks list (possibly an error).
- **Consumer apps give away cheaper models:** "unlimited" slow lanes at Magnific Premium+, Higgsfield, Hailuo Max and Midjourney Relax.
- **Where prices hold or rise:**
  - Runway marks up resold models: Veo Fast +50%, Grok 1.5 +14% at 720p, Seedance Mini ≈2×.
  - Replicate charges 2× on Kling.
  - Comfy marks up 1.43× on LTX-2.5.
  - Veo 3.1 Standard stayed at $0.40.
  - Kling raised its top consumer plan by 41%.
- **OpenAI exited rather than cutting.** Chinese labs price flagship tiers normally ($0.08–0.15/s) and fight with "mini / turbo / max" SKUs.

---

## 7. Pricing structures, minimums, fees, crypto discounts, failed-job policies, tier positioning

### 7A. Pricing structures that work for video (with real numbers)

| Structure | Examples | Numbers | Assessment |
|---|---|---|---|
| **Per second × resolution multiplier** (the dominant API structure) | Google, Lightricks, Alibaba, xAI, MiniMax, Kling, fal, OpenRouter | **Resolution multipliers:** Veo 3.1 Fast 720p→1080p ×1.2, 4K ×3; Veo Lite 1080p ×1.6; LTX-2.5 Fast 1 : 1.44 : 2.1 : 3.3 (720p : 1080p : 1440p : 4K); LTX-2.3 1 : 2 : 4 : 8; Wan 480 : 720 : 1080 = 0.5 : 1 : 2; H3 768P→2K ×1.63; Kling 1080p ×1.33, 4K ×5. **Audio multipliers:** Veo Standard ×2, Fast ×1.25, Lite ×1.67; Kling ×1.5 | Transparent; matches cost. The market standard for developers |
| Per clip / fixed blocks | Luma (5 s / 10 s; 10 s = 3×), MiniMax Hailuo (6 s / 10 s), Replicate Wan fast ($0.10 per video), SiliconFlow ($0.29), RunPod ($0.30), Unifically ($0.075 per 8 s) | – | Simple for consumers; hides duration economics |
| Token-based | Seedance (W×H×24×s/1024 tokens), Gemini Omni Flash (tokens/s by resolution) | $3.5–10.7 per 1M video tokens | Confusing; aggregators convert to $/s |
| Transparent credits | Runway API 1 cr = $0.01; Vidu $0.005; PixVerse $0.01; Kling units $0.14 | – | Fine if 1 credit = a round cent value |
| Opaque consumer credits | Luma, Krea CU, Higgsfield, Magnific, OpenArt, Invideo, Hedra | per-model credit tables, often unpublished | Obscures price; enables differential margins; users complain about "burn" |
| Per-generation minimums | Runway Aleph 2 (56 cr), Seedance Mini (64 cr), Seedance 2.5 (80 cr); fal H3 Max Director $1.20/session | – | Protects against micro-jobs and fixed costs |
| GPU-time | Chutes $0.0005/GPU-s; Midjourney GPU-minutes | – | Honest but unpredictable for users |
| Subscription + PAYG discount | Chutes Plus $10 (−6% PAYG), Pro $20 (−10%); Nous Plus $20 → $22 credits (+10%); io.net ≈−10% | – | Works for dev and prosumer loyalty |
| Consumer subscription + top-ups | Runway, Kling, Luma, Pika, Higgsfield, Krea, Magnific | Entry $8–20/mo; top-up premium −5% to +120% vs plan credits | The consumer norm |
| Off-peak / relaxed lanes | Vidu off-peak −50%; Hailuo Relax; Midjourney Relax; Magnific "unlimited" slow queue; Higgsfield Unlimited | – | Soaks up idle GPUs; strong fit for a network with spare capacity |
| Volume / commitment | Kling −10% at ≥$5,670; MiniMax packages −5/−10/−15/−20% at $1k/2.5k/4.5k/6k per month (1-month validity); PixVerse memberships −33% to −44%; Luma provisioned throughput −26% (3 mo) / −45% (1 yr); OpenAI Batch −50% (Sora); xAI batch 0%; Runway, Google none listed | – | Enterprise-only; developers expect a published tier at ≥$1k/mo |

### 7B. Developer API minimums, fees, credit expiry

| Host | Minimum purchase | Card fee | Crypto | Credit expiry | Free credit | Tag |
|---|---|---|---|---|---|---|
| OpenRouter | not stated | **5.5%** ($0.80 min) | USDC **5%**; never refundable | "may expire after one year" | 50 free-model requests/day (1,000 with $10+) | [C] openrouter.ai/docs/faq |
| fal | minimum purchase required (amount not found) | – | – | purchased credits 365 days | one-time signup credits | [S] fal FAQ via search |
| Replicate | card billing (prepaid for some accounts) | – | – | – | – | [S] |
| Runway API | not stated | sales tax may apply | – | – | – | [C] |
| Kling API | trial $9.80 (100 units, 30 days) | – | – | 30 or 180 days, no rollover | – | [C]/[S] |
| MiniMax | packages from $1,000/mo (Hailuo only); PAYG otherwise | – | – | package 1 month | – | [C] |
| Nous Portal | $10 | Stripe | none | – | – | [C] |
| Chutes | "no minimum" | Stripe | TAO, no discount; non-refundable | – | – | [C] |
| NanoGPT | $1 card / $0.10 crypto | "no deposit fees" | many coins | – | – | [C] |
| PPQ.AI | Lightning $0.10; BTC $10; XMR $5 | Stripe | **+5% Lightning bonus** | – | – | [C] |
| io.net | $1 | provider fee | $IO 0% vs USDC 2% | – | – | [C] |
| **KunoWorld today** | card and USDT $5; NOWPayments $20; max $5,000; alpha max $500 per deposit | – | – | – | – | [C] platform/gateway/PAYMENTS.md |

**Processor costs** [C stripe.com/pricing; nowpayments.io]
- Stripe US card: 2.9% + $0.30.

  | Top-up | Stripe fee (share of top-up) |
  |---|---|
  | $5 | **8.9%** |
  | $10 | 5.9% |
  | $20 | 4.4% |
  | $50 | 3.5% |

- Stripe surcharges: international +1.5%; FX +1%; stablecoin payments 1.5%.
- NOWPayments: 1% single-currency (1.5% with conversion, per the trends thread) plus network fees; per-coin minimums ≈$2–5.
- At $10–20 top-ups, card processing costs 3–5 points more than crypto.

### 7C. Crypto payment discounts at crypto-native AI and privacy sites

| Service | Crypto terms | Tag |
|---|---|---|
| Venice | Crypto paid at the same rate as USD. DIEM = $1/day of API credit forever (at DIEM ≈ $1,738 that is ≈21%/yr at full use). Staking 100 VVV unlocks Pro (≈9.9%/yr implied) | [C]/[S] |
| Chutes | TAO accepted; no discount or bonus | [C] |
| NanoGPT | Nano/Lightning "incentive if enabled", size unstated; $0.10 minimum | [C] |
| PPQ.AI | **+5% bonus** for Lightning | [C] |
| OpenRouter | 5% crypto vs 5.5% card (−0.5 pt) | [C] |
| io.net | $IO 0% fee vs USDC 2% | [C] |
| Mullvad | **10% off** for crypto ("due to lower fees") | [C] |
| Proton | BTC accepted, no discount | [C] |

**Pattern:** most sites price crypto at parity. Where incentives exist they are 0.5–10%, framed as fee pass-through or bonus credit. None discount deeply.

### 7D. Failed and blocked job charging

**Developer APIs**
- Gemini: "You will only be charged if your video is successfully generated" [C].
- OpenRouter video: "failed generations are not billed" [C].
- Kling API: failed generations don't deduct units [C].
- Replicate: "if a run fails, we don't charge you" for public and official models; private deployments are billed for instance time [S docs summary].
- fal: HTTP 5xx never charged; HTTP 422 may be charged if GPU time was used [S fal FAQ].
- Runway API: not stated.

**Consumer apps** (see 4C)
- **Refund failed jobs:** Luma, LTX Studio, Hailuo, Higgsfield, OpenArt, Hedra, Runway (errors only).
- **Charge failed jobs:** Pika [S], Kling app [S].
- **Moderation-blocked:**
  - Refunded: LTX Studio, Hailuo, Higgsfield.
  - Charged: Runway [S].

### 7E. How to position a private tier: observed patterns

| Pattern | Who | Evidence consumers pay |
|---|---|---|
| **Privacy included free** as brand differentiator | Apple PCC, Signal, WhatsApp E2EE, Chutes (all-TEE), Azure confidential VMs at parity | Drives adoption, not direct revenue |
| **Privacy company with paid tiers** (Proton-style) | Proton ($4.99–12.99), Mullvad (€5), Kagi ($5–25), Tinfoil ($20), Venice ($18), Lumo Plus ($12.99) | Yes: millions of Proton paid users [U]; Kagi and Mullvad sustain flat fees |
| **Private variant at a small premium** | Venice E2EE (+0–104%, median +22%); scale TEE hosts (+0–10%) | Yes, but volume is on the cheap tiers |
| **Private variant at a large premium** | Privatemode, Tinfoil, PPQ TEE (+30–340%) | Niche (compliance-driven EU/enterprise) |
| **Enterprise add-on** | +10% residency/sovereignty (OpenAI, Anthropic, Google, Azure); ZDR by approval | Yes: enterprises accept +10% routinely |

---

## 8. KunoWorld today: placeholder prices and cost basis

### 8A. Current placeholder customer prices vs market

Source: `/video/platform/web/lib/profiles.json`, "launch estimates pending Phase 0 benchmarks". No Standard vs Private price difference exists in code. The subnet rate card pays open-tier miners 0.5× the confidential rate (placeholder).

| Profile | KunoWorld placeholder | $/5 s | Nearest market prices (same weights) | Nearest quality peers (closed) |
|---|---|---|---|---|
| ltx-2.5-fast | 720p **$0.024/s**; 1080p **$0.04** | $0.12 / $0.20 | Lightricks/fal $0.09 / $0.13; WaveSpeed $0.10 / $0.14; Segmind $0.1125 / $0.1625; Replicate $0.03 / $0.06; Chutes raw ≈$0.003/output-s | Veo 3.1 Lite $0.05 / $0.08 (audio); Grok Imagine $0.07; Pika 2.5 $0.04 (silent); Vidu Q3-turbo $0.055 |
| ltx-2.5-pro | 720p $0.04; 1080p $0.07 | $0.20 / $0.35 | Lightricks/fal $0.12 / $0.17; Segmind $0.15 / $0.2125 | Veo 3.1 Fast $0.10 / $0.12; Kling 3.0 $0.084–0.168 |
| ltx-2.5-4k | 1440p $0.12; 2160p $0.20 | $0.60 / $1.00 | Lightricks Fast $0.19 / $0.30, Pro $0.25 / $0.39; WaveSpeed $0.21 / $0.33; Replicate 4K $0.24; fal LTX-2 Fast 4K $0.16 | Veo 3.1 Fast 4K $0.30 (silent $0.25); Kling 3.0 4K $0.42; Seedance 2.0 4K $0.78; Veo 3.1 4K $0.60 |
| h3-turbo | 768p $0.06 | $0.30 | fal H3 $0.06; fal **H3 Max Turbo $0.04** (derivative, better); WaveSpeed H3 $0.08 list | Seedance Mini 720p $0.08; Veo Lite $0.05 |
| h3 | 768p $0.12 | $0.60 | MiniMax official $0.08; fal $0.06; WaveSpeed $0.08; Runway $0.10; Comfy ≈$0.129 | Seedance 2.0 $0.151; Omni Flash $0.10; Wan 3.0 $0.10 |
| h3-reference | 768p $0.10 (**cheaper than h3 despite VCU 64 vs 60: inconsistent**) | $0.50 | WaveSpeed reference $0.125 (+$0.02 per ref); MiniMax $0.08 + $0.04 per image over 5; fal $0.06 + $0.08 per image over 5; Runway $0.10 + $0.02 per ref | Kling Omni with reference $0.126+ |

### 8B. Cost basis per clip (TEE hardware, derived) [U unless noted]

**Timings**
- H3 full, 50 steps, 5 s 1344×768 on 4×H200: ≈74 s [S Spheron].
- LightX2V 4-step: ≈3.4× faster than 20-step [S].
- LTX-2.5: 10 s in 6.8 s on 2×GB200 [S vendor].
- LTX API at 1080p: 23.7 s end-to-end [C].
- Chutes LTX-2.5 (RTX PRO 6000): ≈27 GPU-s per call on average [C, usage-derived].

**Prices**
- Phala TEE H100: $3.08 on demand / $2.38 reserved per hour.
- Phala TEE H200: $4.80 / $3.20 [C].
- Chutes H200: $2.75; RTX PRO 6000: $1.80 [C].

**Estimated cost per clip**

| Profile (5 s) | Setup | Cost per clip | $/output-s |
|---|---|---|---|
| LTX-2.5 Fast 720p | ≈20–30 GPU-s on a TEE H100 ($3.08/hr) | $0.017–0.026 at 100% utilization; **$0.03–0.043 at 60%** | ≈$0.006–0.009 |
| LTX-2.5 Pro (33 steps, ≈3× Fast) | ≈60–90 GPU-s | $0.05–0.08 at 100%; **$0.09–0.13 at 60%** | ≈$0.018–0.026 |
| LTX-2.5 4K (≈5× 1080p pixels) | ≈120–200 GPU-s on a TEE H200 ($4.80/hr) | $0.16–0.27 at 100%; **$0.27–0.44 at 60%** | ≈$0.05–0.09 |
| H3 Turbo 8-step | ≈20 s wall on 4×H200 TEE ($19.20/hr) | $0.107 at 100%; **$0.18 at 60%** (reserved: $0.071 / $0.12) | ≈$0.024–0.036 |
| H3 full 50-step | 74 s on 4×H200 TEE | $0.39 at 100%; **$0.66 at 60%** (reserved: $0.26 / $0.44) | ≈$0.09–0.13 |

**Other costs**
- Confidential-computing overhead on diffusion: unbenchmarked; assumed +5–10%.
- Payment fees: 1–9%.
- Storage and egress.
- Miner margin, and emissions that currently subsidize it.

---

## 9. What this means for KunoWorld

### 9A. Standard-mode price bands (recommended ranges, per output second)

**LTX-2.5 Fast** (720p / 1080p)
- **Competes with:** Veo 3.1 Lite ($0.05 / $0.08 with audio), Grok Imagine ($0.07), Pika 2.5 ($0.04, silent), Vidu Q3-turbo ($0.055 / $0.065), Kling 3.0 silent ($0.084 / $0.112). These share LTX-2.5's quality band (AA Elo 1060–1090). Lightricks and fal sell the same weights at $0.09 / $0.13, Replicate at $0.03 / $0.06.
- **Band:** **$0.03–0.05/s at 720p ($0.15–0.25 per 5 s); $0.05–0.08/s at 1080p ($0.25–0.40 per 5 s).**
- **Suggested list:** $0.04 / $0.06. That is 55% below Lightricks' list, at or under Veo 3.1 Lite with audio, and ≈5× compute cost at 60% utilization.
- **Against the placeholder:** $0.024 / $0.04 is at the floor. It is below Replicate at 1080p, and on a $5 card top-up Stripe takes 9%. It works as a launch promo but leaves little room for miner pay.

**LTX-2.5 Pro** (720p / 1080p)
- **Competes with:** Lightricks and fal $0.12 / $0.17; Segmind $0.15 / $0.21.
- **Quality caveat:** AA rates Pro *below* Fast (T2V 1058 vs 1072; I2V 1012 vs 1048), so a large Pro premium is hard to justify to informed buyers.
- **Band:** **$0.05–0.08/s at 720p ($0.25–0.40 per 5 s); $0.08–0.12/s at 1080p ($0.40–0.60 per 5 s).**
- **Pricing rule:** keep Pro at ≈1.3–1.5× Fast, matching Lightricks' own 1.33× ratio. **Suggested:** $0.055 / $0.085.
- **Against the placeholder:** $0.04 / $0.07 is fine at the low end, but cost at 60% utilization is ≈$0.02–0.026/s, so margins are thinner than on Fast.

**LTX-2.5 4K** (1440p / 2160p)
- **Competes with:** LTX-2.5 Fast 1440p $0.19 / 4K $0.30 and Pro $0.25 / $0.39 (Lightricks); WaveSpeed $0.21 / $0.33; Replicate 4K $0.24.
- **Closed 4K peers:** Veo 3.1 Fast 4K $0.30 ($0.25 silent), Kling 3.0 4K $0.42, Veo 3.1 4K $0.60, Seedance 2.0 4K $0.78.
- **Band:** **$0.10–0.14/s at 1440p; $0.16–0.24/s at 2160p ($0.80–1.20 per 5 s).**
- **Against the placeholder:** $0.12 / $0.20 sits inside the band, ≈33% under Veo 3.1 Fast 4K, and above the est. $0.05–0.09/s cost at 60% utilization. **Keep it.** Native 4K at 50 fps with audio from an open model is a real differentiator; few closed models offer 4K below $0.30/s.

**H3 Turbo** (768p, 8-step)
- **Competes with:** fal H3 Max Turbo **$0.04/s** list, a post-trained derivative with top-3 AA quality and sub-3-second latency; fal base H3 $0.06; MiniMax H3-Max $0.08; Seedance 2.0 Mini 720p $0.08; Veo 3.1 Lite $0.05.
- **Band:** **$0.035–0.05/s ($0.18–0.25 per 5 s).**
- **Against the placeholder:** $0.06 is above fal's faster, better-rated H3 Max Turbo, so cut to ≈$0.045.
- **Cost constraint:** cost at 60% utilization is ≈$0.024–0.036/s on 4×H200 TEE. Margins depend on reserved GPUs and batching.

**H3** (768p, full 50-step)
- **Competes with:** MiniMax official $0.08, fal (same open-weight base) $0.06, WaveSpeed $0.08, Runway $0.10, Segmind $0.1125, Comfy ≈$0.13.
- **Quality peers:** Seedance 2.0 at 720p ($0.151), Gemini Omni Flash ($0.10), Wan 3.0 ($0.10).
- **Band:** **$0.08–0.12/s ($0.40–0.60 per 5 s).**
- **The problem:** estimated TEE cost at realistic utilization ($0.09–0.13/s) is at or above what MiniMax charges for the same model. The placeholder $0.12 is defensible on cost but 50% above MiniMax's own price.
- **Recommendation:** list Standard at $0.10, or offer full H3 **only in Private mode**, and make Turbo the Standard H3 SKU.

**H3 Reference** (768p)
- **Competes with:** WaveSpeed reference-to-video $0.125 (+$0.02 per reference); MiniMax $0.08 + $0.04 per image over 5; fal $0.06 + $0.08 per image over 5; Runway $0.10 + $0.02 per reference.
- **Band:** **$0.10–0.14/s,** optionally plus $0.02–0.04 per reference image beyond 3–5.
- **Fix:** the placeholder prices h3-reference ($0.10) *below* h3 ($0.12) despite higher compute. Price it ≥ h3, e.g. h3 $0.10 and h3-reference $0.12.

**Market-access constraint for all H3 SKUs:** without MiniMax authorization, H3 cannot be sold to users in the US, EU, UK or South Korea, and outputs can't be displayed there. The bands above apply only in permitted territories. Mandatory "MiniMax H3" UI branding also applies.

### 9B. What premium Private mode can carry

**Evidence**
1. Scale TEE LLM hosts charge **0–10%** more for the same model. The median across all TEE offerings is **+31%**; Venice's E2EE twins average **+22%**; boutique confidential vendors get **+30% to +340%**.
2. Enterprises routinely pay **+10%** for residency and sovereignty.
3. Confidential GPUs cost KunoWorld's miners about **0–35%** more per hour, plus unmeasured CC overhead (assumed 5–10%).
4. **Nobody sells private video generation.** The alternative for an agency or brand with NDA content is self-hosting on TEE GPUs: ≥$115/day minimum on Phala, or ≈$2.74/hr per H200 on Tinfoil containers with ops burden.
5. The closed APIs Private mode would displace for sensitive work carry ToS or data-use concerns, e.g. Kling's perpetual license to inputs. They cost $0.25–2.00 per 5 s 720p clip.

**Conclusion.** Private mode can plausibly carry **+25–50% over Standard for consumers and prosumers**. That sits at or above the TEE median, well above the +10% enterprise norm, and covers the real hardware uplift. For **API and enterprise buyers** who get a per-job attestation report, **+50–100%** is defensible, as boutique confidential vendors show. Even at +50%, Private LTX-2.5 Fast 720p ($0.06/s, $0.30 per 5 s) is still **below Lightricks' own non-private list price ($0.45)** and near Veo 3.1 Lite ($0.25). **"Private for about the price of public" is itself the headline.**

### 9C. Positioning: Proton-style vs Signal-style
- **Signal-style (Private at parity):**
  - Strongest message and aligned with Apple PCC and Chutes.
  - But it gives up the one uncontested premium, and Standard has no reason to exist except features that need server access: moderation-scanned sharing, galleries, re-download.
- **Proton-style (recommended):**
  - Private is the brand and the default. Priced at the market rate for the model's quality peers, e.g. LTX Fast 720p ≈$0.05/s.
  - **Standard is presented as a discount** (≈0.7–0.8× Private) for convenience features and platform-readable storage.
  - The premium becomes a "Standard discount" in copy, avoiding a "privacy tax" framing while capturing +25–40%.
  - This fits the code's placeholder that pays open-tier miners 0.5× confidential.
- **Illustrative list prices** (Standard / Private, $/s):

  | Profile | Standard | Private |
  |---|---|---|
  | LTX Fast 720p | $0.04 | $0.05 |
  | LTX Fast 1080p | $0.06 | $0.08 |
  | LTX Pro 720p | $0.055 | $0.075 |
  | LTX Pro 1080p | $0.085 | $0.11 |
  | 4K 1440p | $0.12 | $0.15 |
  | 4K 2160p | $0.20 | $0.25 |
  | H3 Turbo | $0.045 | $0.06 |
  | H3 | $0.10 | $0.13 |
  | H3 Reference | $0.12 | $0.15 |

  API enterprise tier: Private + attestation reports at ≈1.5–2× Standard with volume discounts.

### 9D. Structure recommendations
- **Metering:** bill per output second × resolution tier, audio included, like Lightricks, Google and Alibaba. Show $ per 5 s clip in the UI.
- **Credits:** use **1 credit = $0.01**, transparent like the Runway API, and publish the rate card. Opaque credits read as untrustworthy for a privacy brand.
- **Per-generation minimum:** ≈$0.10 (e.g. 2 s LTX jobs), like Runway and fal minimums, to cover fixed and payment costs.
- **Top-ups:**
  - Consider a **$10 card minimum**: Stripe fees are 8.9% at $5 vs 5.9% at $10. Otherwise pass through a small fee.
  - Keep the $20 NOWPayments minimum.
  - Offer a **3–5% bonus for crypto, TAO or alpha**, funded by the processor-fee gap. PPQ gives +5% and Mullvad −10%; deep crypto discounts aren't the norm.
- **Expiry:** credits don't expire (Runway, Pika, Hedra packs), or at most 12 months (fal, OpenRouter, Luma). Expiry breakage is a poor fit for a trust brand.
- **Refunds:**
  - Automatically refund failed jobs **and** moderation-blocked prompts (LTX Studio, Hailuo, Higgsfield, Gemini and OpenRouter norm). Runway is the outlier that charges.
  - For Private mode the in-enclave filter can't be audited by the platform, so charging for blocks would look punitive. Use the existing strike system for abuse instead.
- **Volume:**
  - Published API tiers: e.g. −10% at $1k/mo, −20% at $5k/mo (MiniMax −5% to −20% at $1–6k; Kling −10% at $5.7k).
  - An **off-peak or relaxed queue at −30–50%** (Vidu −50%) to monetize idle miner capacity. Consumer apps' "unlimited slow lanes" show demand.
- **Launch promos:** 30–75% off list for 2–4 weeks is now normal (Wan 3.0 −30%, fal H3 Max −75%). Emissions can fund this, but list the real price from day one so the cut is visible.
- **Subscriptions (later):** a $10–20/mo prosumer plan with ≈20% annual discount and a relaxed lane is the consumer norm. Credits roll over at least one month (Runway Max) to differentiate from use-it-or-lose-it competitors.

### 9E. Licence and market risks that affect price
- **LTX-2.x competing-service clause** (Attachment A #20): a paid public LTX API arguably competes with Lightricks' LTX API and LTX Studio. Budget for a Lightricks commercial licence; its price is unpublished. Watermark and provenance metadata must survive Private mode (§6).
- **H3 territory ban and $20M revenue gate:** the addressable H3 market excludes US, EU, UK and KR users until MiniMax authorizes. fal and WaveSpeed already sell H3 open-weight SKUs at $0.04–0.08/s and would undercut any Standard H3 price.
- **Price-war trajectory:** quality-adjusted prices fell 65–80% in 12 months, and low-end SKUs are at $0.03–0.05/s. Expect the LTX-2.5 Fast band to fall to ≈$0.02–0.03/s within 6–12 months as LTX-2.6+ ships and Lightricks' own prices on older SKUs hold at $0.03–0.06. Plan miner economics on reserved-GPU costs, not today's list prices.

---

## Conflicts summary (all sections)
1. **Replicate LTX-2.5 Fast** $0.03 / $0.06 vs Lightricks and fal $0.09 / $0.13. Replicate's figures equal LTX-2.3 Fast, so possibly a stale config.
2. **MiniMax H3 Max audio:** fal says "native audio"; OpenRouter says generate_audio=false. AA's $0.04/s is promo-era vs $0.08 list from Sep 15.
3. **WaveSpeed H3:** model page $0.04 (480p) / $0.08 (768p) vs landing page "50% off, from $0.10 (was $0.20)".
4. **Atlas Cloud H3:** model page $0.038/s (2K) and Developer $0.02–0.05 vs its blog's $0.14 (2K) and pricing page "from $0.16/s". Units unclear.
5. **Seedance 2.0 Fast:** BytePlus $0.12/s at 720p vs OpenRouter $0.091 ($5.60/M vs $4.20/M tokens).
6. **HappyHorse 1.1:** Alibaba $0.14 / $0.18 vs OpenRouter $0.0988 / $0.1278.
7. **Grok Imagine:** docs.x.ai summary table says "$0.05 / $0.08" (starting prices) vs per-resolution JSON ($0.07 / $0.14 at 720p). OpenRouter matches the JSON.
8. **Sora 2 Pro at 1080p:** OpenAI $0.70 vs OpenRouter $0.50.
9. **Veo 3.1 Fast $0.10 cut date:** "Apr 7 2026" (Medium) vs already on Wayback 2026-04-02.
10. **Kling app:** Ultra annual availability; refund policy (secondaries disagree); free-tier resolution.
11. **Hailuo app:** four conflicting 2026 price ladders; official terms dated 2025-07-14.
12. **Luma:** two plan ladders (Plus/Pro/Ultra vs Free/Lite/Plus/Unlimited); refund policy says yes but secondaries say no.
13. **Magnific:** H3 Max Turbo 768p 20 cr/s (docs) vs 200 cr per 5 s (pricing page); Veo 3.1 4K credits.
14. **Invideo:** plan lineups differ across pages. LTX 2.5 credits imply ≈$0.02/s, below Lightricks list.
15. **LTX Studio per-second credits** (3–6 cr/s) come from a search snippet only [U]. They would imply ≈$0.014–0.028 per 5 s 720p, far below the API.
16. **Venice:** "E2EE at standard rates" (docs summary) vs 0–104% surcharges (API). Video "$0.085 per 10 s 1080p" vs "under $0.80 per 5 s".
17. **Phala GPU pricing:** "GPU TEE from $3.80/hr" (pricing page) vs H100 $3.08 (gpu-tee page).
18. **NOWPayments fee:** 1% (vendor) vs 0.5% (third-party reviews).
19. **Chutes `tee: 2.25` multiplier:** appears miner-side (the user price is unchanged). Interpretation [U].

## Not found
- **Pricing pages or official prices:**
  - HiDream-O1-Video API and price.
  - Veo 4 (not on Google pages).
  - Runway Gen-5 (doesn't exist).
  - BytePlus ModelArk official price page (JS-only).
  - Lightricks commercial-licence price.
  - MiniMax H3 authorization price; Comfy MiniMax licence tiers.
- **Per-clip credit costs or plan prices:**
  - LTX Studio official credits per clip.
  - Krea credit units per LTX, Hailuo or Kling clip.
  - Official Kling consumer and Hailuo 2026 plan prices (JS-rendered).
  - ElevenLabs credits per LTX clip.
  - Hedra annual prices.
- **Policies and fees:**
  - Official refund text for the Kling app, Pika, Magnific and Invideo.
  - Moderation charging at most apps.
  - fal, Replicate, MiniMax and WaveSpeed minimum top-up amounts.
  - NOWPayments per-coin minimums.
- **Market data:** ChatGPT plan prices (403); GCP A3 base price, needed for a confidential surcharge %.
- **Benchmarks:** confidential-computing overhead for video diffusion; H3 Turbo and LTX-2.5 timings on H100/H200 TEE.
- **Other providers:** Adobe Firefly Video API, Meta, Baidu, StepFun, closed Hunyuan (not checked).
