# Kino: Competitive Feature & UX Research on AI Video Platforms (as of 2026-09-11)

Research date: 2026-09-11. Around 450 web searches and fetches, run across five parallel research passes plus a direct pass on landing pages, provenance and privacy. Related files in this folder: `research_models.md` (H3 / LTX-2.5 specs and licenses) and `research_market.md` (API price benchmarks).

**Legend**
- **[C]**: confirmed on a primary source (vendor site, docs, changelog, help center, official blog).
- **[S]**: secondary source only (review sites, reseller docs, press).
- **[UNVERIFIED]**: single low-trust source, conflicting reports, or a primary page that could not be loaded.
- In matrices: **Y** = yes, **P** = partial or limited, **N** = no, **?** = not verified.

**Method caveats**
- Several primary pages blocked automated fetching (403 or JS-only). These include midjourney.com and docs, sora.com and openai.com, pollo.ai, most of magnific.com, krea.ai's pricing and homepage, kling.ai's pricing and API docs, flow.google.com, and parts of help.runwayml.com. Those details come from secondary sources and are marked.
- The search tool returned almost no first-hand Reddit threads. User sentiment therefore comes mostly from Trustpilot, G2, App Store and editorial reviews, some of which quote Reddit and X.

---

## 0. Executive summary

1. **The market has converged.** Every serious platform now offers these, in this layout:
   - text-to-video (T2V) and image-to-video (I2V)
   - start/end frames
   - native audio
   - @-tagged references or "elements"
   - extend
   - some kind of video-to-video (V2V) edit
   - a prompt enhancer
   - credits priced per second
   - The layout is a prompt composer docked beneath a scrolling feed of results.
   
   Kino must meet this baseline; none of it differentiates.
2. **The #1 user pain across the category is credit trust.** Examples:
   - Trustpilot: Runway 1.1/5, Luma 1.5, Hailuo 1.4, LTX Studio 1.6, Pika 1.7.
   - Credits are consumed by failed or unusable generations.
   - Costs are opaque, credits expire monthly, and "unlimited" plans get walked back (Higgsfield, Freepik, Runway retiring Unlimited on 2026-11-30).
   
   The cheapest high-value differentiators follow directly: honest cost on the Generate button, automatic refunds, cheap drafts, and credits that don't expire monthly.
3. **Privacy is either a paid add-on or absent at competitors:**
   - Runway trains on Inputs and Outputs by default on all non-Enterprise plans, with no opt-out ([terms](https://runway.com/terms-of-use), [S](https://terms.law/ai-output-rights/runway/)).
   - Kling's ToS licenses content "to create, test, improve, train" models ([Kling ToS §4.7.3(f)](https://kling.ai/docs/user-policy)).
   - Midjourney makes everything visible on Explore unless you pay $60+/mo for Stealth ([S](https://www.eesel.ai/blog/midjourney-pricing)).
   - The only "private AI" brand doing video, Venice, routes video to closed third-party models via an anonymizing proxy. Its TEE/E2EE modes cover **text models only** ([Venice blog](https://venice.ai/blog/venice-launches-end-to-end-encrypted-ai)).
   - **As far as this research found, nobody offers verifiably sealed (TEE, end-to-end encrypted) video generation.**
4. **Provenance is weak everywhere:**
   - Google uses invisible SynthID and checks it by upload to Gemini.
   - Sora had C2PA plus a moving watermark naming the creator, but the app is dead.
   - Midjourney writes unsigned IPTC metadata.
   - Adobe Firefly attaches Content Credentials but is not a video-first competitor here.
   - **No platform gives the creator a signed, shareable, verifiable certificate page per video.** Kino can own this.
5. **Model access is not a moat.** Krea launched MiniMax H3, H3 Max and H3 Max Turbo on 2026-08-27, with reference-to-video (image, video and audio) on H3 Max and native 1080p on H3 and H3 Max ([Krea changelog](https://www.krea.ai/docs/changelog)). Pika's API also resells H3 ([dev.pika.art](https://dev.pika.art/)). Kino wins on privacy, provenance and craft, not on having H3.
6. **The best UX ideas to copy:**
   - Kling's Element Library with voice binding.
   - Dreamina and Kling's auto-labelled `@Image1` reference slots with @-autocomplete.
   - Luma's Draft→Master and named strength bands (Adhere / Flex / Reimagine).
   - Hailuo's bracket camera commands and auto-refunds.
   - Higgsfield's cost-on-Generate-button and camera-preset gallery.
   - Flow's Scenebuilder "+ Extend / Jump to".
   - LTX Studio's Retake on a scrubbed range.
   - Midjourney's hover-to-play grid and one-click Animate/Loop.
   - Sora's likeness-consent model.
7. **Where the market is heading (v2/v3 for Kino, not v1):** everyone is moving to agents, canvases and node workflows.
   - Runway: Agent, Workflows→Apps.
   - Luma: Agents, infinite canvas.
   - Krea: Agent, Nodes, App Builder.
   - Also OpenArt Director, Higgsfield Supercomputer, Freepik/Magnific Spaces, and LTX Studio Canvas/Flows.
8. **H3 and LTX-2.5 fit together as a two-model product.**
   - **LTX-2.5** is the fast, high-resolution, multi-shot draft-and-finish engine: up to 4K, 24–50 fps, 6–20 s Fast, camera_motion parameter, first/last frame, IC-LoRA control, retake/extend pipelines.
   - **H3** is the "omni-reference, native stereo dialogue" engine: 768p, 4–15 s, 9 image / 3 video / 3 audio references, first/last frame, multi-shot, V2V motion transfer.
   - **Constraint:** H3's 2K "Regenerate" stage and Context-IR prompt compiler are closed and API-only, so a sealed H3 is **768p**.
9. **Critical business constraint.** The MiniMax H3 Community License excludes the USA, EU, UK and South Korea, requires a prominent "MiniMax H3" label in the UI, and needs authorization above $20M revenue ([LICENSE](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE), see `research_models.md`). Unless MiniMax grants an authorization, H3 cannot be offered to US/EU/UK/KR users. This shapes the whole v1 plan: LTX-2.5 must be able to carry the product alone in those markets.
10. **Timely opportunity.** The Sora API shuts down on **2026-09-24** with no replacement ([OpenAI deprecations](https://developers.openai.com/api/docs/deprecations)). Sora had the only mainstream video API with **webhooks**; Google, Runway, Luma (current API) and LTX are poll-only. A privacy-first API with webhooks, cost quotes and attestation receipts is a clean migration story.

---

## 1. Feature matrix

### 1a. Generation modes (platforms × features)

| Platform (flagship models, Sep 2026) | T2V | I2V | Start+End frame | Multi-keyframe | References / characters | Multi-shot | Extend | V2V edit / restyle | Motion transfer | Lip-sync | Native audio | Upscale / HDR | Loop | Effects / templates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Runway** (Gen-4.5, Aleph 2.0, Act-Two + 3rd-party) | Y | Y | P (Veo via API; Gen-4.5 keyframes "coming") | N | Y (Gen-4 References, 3 imgs) | Y (1-min multi-shot) [S] | Y | **Y (Aleph 2: 30 s, 1080p, edit one frame → propagate)** | Y (Act-Two) | P | Y | Y (Magnific 4K, "Ruby" SDR→HDR, ProRes/EXR) | ? | P (Apps) |
| **Kling** (3.0, 3.0 Omni, 3.0 Turbo) | Y | Y | Y | N | **Y (Elements: ≤7 imgs/Elements; voice binding)** | **Y (≤6 cuts, per-shot fields)** | Y [S] | Y (Omni text edits) | Y (Motion Control 3–30 s) | Y | Y (5 langs) | Y (native 4K on 3.0) | ? | Y |
| **Google Flow** (Veo 3.1 Lite/Fast/Quality, Gemini Omni Flash) | Y | Y | Y | N | Y (Ingredients ≤3, `@Name`, `@me`, voice refs) | P (Scenebuilder "Jump to") | Y (API ≤148 s) | Y (Omni Flash conversational, ≤10 s) + insert/remove objects | N | P (dialogue) | Y | Y (1080p free, 4K Ultra) | N | N |
| **MiniMax Hailuo** (H3, H3 Max, 2.3, 02) | Y | Y | Y | N | **Y (H3 Omni Reference: 9 img + 3 vid + 3 audio, ≤12)** | Y (H3 native) | ? | Y (H3 editing / motion transfer) | Y | Y (11 langs) | Y (32 kHz stereo) | Y (768p→2K Regenerate, API-only) | ? | Y (templates, Agent) |
| **Luma** (Ray3.2, Ray3.14 + 3rd-party) | Y | Y | Y | **Y (≤16 in app, ≤64 via API)** | P (8-face performance tracking) | ? | Y | **Y (Modify: Adhere/Flex/Reimagine, ≤20 s)** | Y (face + pose) | N | N (ElevenLabs via Agents) | **Y (Draft→Master 4K HDR, EXR/ACES)** | Y | N |
| **Pika** (2.5; pivoted to agents) | Y | Y | Y | **Y (Pikaframes ≤5 kf, ≤25 s)** | P (Pikascenes) | N | ? | Y (Pikaswaps / additions / twists) | N | Y (Pikaformance ≤30 s) | P | ? | ? | **Y (Pikaffects)** |
| **Higgsfield** (aggregator: Kling, Seedance, Veo, Wan, Hailuo, Sora, own DOP) | Y | Y | Y | N | Y (Soul ID; Popcorn 4 refs → 8 frames) | P (Popcorn storyboard) | via models | Y | Y | Y (Speak 2.0) | via models | Y (images) | ? | **Y (≈50 VFX presets, 50+ camera presets, apps)** |
| **Krea** (aggregator, 40+ models incl. H3; Realtime) | Y | Y | Y | P (3D keyframing in Seedance Studio) | Y (Elements, LoRA, H3 Max refs) | via models | Y (hover → Extend) | Y | Y | Y | via models | Y (to 8K video) [S] | ? | N (**Realtime video** unique) |
| **Magnific** (formerly Freepik; 36+ models) | Y | Y | Y | ? | ? | via models | ? | ? | Y (Kling Motion Control) | ? | via models | P (Magnific brand) [UNVERIFIED for video] | ? | P |
| **Pollo AI** (aggregator + Pollo 2.5) | Y | Y | ? | ? | Y (consistent characters) | ? | ? | Y | ? | Y (15+ langs) | via models | ? | ? | **Y (200+ effects)** |
| **OpenArt** (aggregator) | Y | Y | ? | ? | **Y (Character Builder)** | Y (Director: ≤5-min multi-shot) | Y | Y (anime/clay presets, relight, BG swap) | Y (Motion Sync) | Y | Y (SFX) | Y (4K) | ? | Y (One-Click Story templates) |
| **Midjourney Video** (V1, Jun 2025) | **N** | Y (Animate any image) | Y (`--end`) | N | N | N | Y (≈4 s × 4 → ~21 s) | N | N | N | N | N (SD/HD only) | **Y (`--loop`)** | N |
| **Dreamina / Seedance** (2.0, 2.0 Fast/Mini, 2.5) | Y | Y | Y | P (2.5: 3D blockout staging) | **Y (2.0: 9/3/3 ≤12; 2.5: 30 img + 10 vid + 10 aud)** | Y | Y (2.5: 30 s single pass, 3-min beta) | Y (2.5: timestamp-level local edits) | ? | Y | Y (stereo, multi-track) | Y (+60 fps interpolation) | ? | P |
| **LTX Studio** (LTX-2.5/2.3 + Veo, Kling, Seedance) | Y | Y | Y (keyframes) | P | **Y (Elements: characters with voice, locations, objects, styles, logos, fonts)** | Y (storyboard + LTX multishot) | Y (4–12 s steps, ≤60 s) | Y (pose/depth/edge V2V) | Y | Y (audio-to-video) | Y | Y (Topaz 4K/8K, SDR→HDR) | ? | P ("starting points") |
| **OpenAI Sora** (Sora 2; app closed 2026-04-26, API ends 2026-09-24) | Y | Y | N | N | **Y (Cameos/"characters", consent-gated)** | P (Storyboard, Pro web) | Y (API ≤120 s) | Y (**Remix**; API edits) | N | via audio | Y | N | N | N |
| **CapCut** (Seedance 2.5 inside the editor) | Y | Y | ? | ? | Y (≤50 refs via Seedance 2.5) | Y | Y (180 s beta) | Y ("Intelligent Edit Mode") | ? | Y (OmniHuman avatars) | Y | Y | ? | **Y (templates; full editor)** |

Sources: platform profiles in §8 (every cell is sourced there).

### 1b. Controls, workflow, business

| Platform | Camera control | Motion brush / annotate | Seed | Neg. prompt | Prompt enhancer | Draft / fast tier | Outputs per gen | Storyboard / timeline | Canvas / nodes / agent | Community feed | Cost shown before gen | Auto-refund on failure | "Unlimited" / relaxed | API (async) | Webhooks | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Runway | P (numeric panel [S]) | ? | Y | ? | Y (LLM nodes) | Gen-4 Turbo | ? | Y (Studio editor, Agent timeline) | **Y (Workflows→Apps, Agent 2.0)** | P (Home inspiration) | Y (API Task Cost) | N (top complaint) | Retiring 2026-11-30 | Y (poll `/v1/tasks`) | N (undocumented) | ? |
| Kling | P (per-shot moves; Motion Brush [UNVERIFIED on 3.0]) | ? | ? | P (older UI) | ? | Std/Pro, 3.0 Turbo | ≤4 (2.6) | P (Custom Multi-Shot) | N | Y ("Recreate" others' public works) | Y (credits/s tables) | N (complaints) | N | Y | Y (`callback_url`) | ? |
| Google Flow | Y (pan/zoom, Feb 2026) | Y (lasso + draw) | API (Veo 3 only) | ? | Y (Gemini) | Lite/Fast/Quality | ≤4 [UNVERIFIED] | **Y (Scenebuilder)** | P (Flow Tools, Omni chat edits) | **Y (Flow TV, prompts visible)** | **Y (in settings menu)** | P (15–30 min delay) | Free 50 cr/day | Y (`predictLongRunning` + poll) | **N** | SynthID + C2PA verify in Gemini |
| Hailuo | **Y (15 bracket commands, e.g. `[Pan left]`, ≤3 combined)** | N | N | N | Y (`prompt_optimizer`, Context-IR) | 768p→2K; Fast models | ? | Y (Storyboard tool, Agent) | Y (Video Agent) | Y (feed, reuse creations) | ? | **Y (failed + moderated)** | Relax (legacy Max) | Y | Y (callback + challenge echo) | ? |
| Luma | **Y (Camera Concept chips)** | **Y (scribble on keyframes)** | ? | ? | P (Brainstorm) | **Y (Draft 360p → Master)** | ? | P (keyframe indexes) | **Y (infinite canvas, Agents)** | ? | Y (model-page price table) | Y (API, by failure code) | Legacy Unlimited only | Y (one `/generations` endpoint) | N (new API); Y (legacy) | ? |
| Pika | N | N | ? | ? | ? | ? | ? | P (Pikaframes) | Y (Pika Agent, MCP) | P | Y (API micro-USD quotes; per-feature table) | N | N | Y (dev.pika.art multi-model) | ? | ? |
| Higgsfield | **Y (50+ presets; Cinema Studio body/lens/focal)** | Y (Draw-to-Video app) | ? | ? | ? | via models | ? | Y (Popcorn) | Y (Canvas, Supercomputer agent) | Y | **Y (on Generate button)** | N (7-day, zero-use refunds only) | Controversial "unlimited" | MCP / CLI | ? | ? |
| Krea | Y (Seedance Studio) | Y (annotations) | ? | ? | ? | cheap/fast labelled models | ? | P | **Y (Nodes + App Builder, Agent, Realtime Director)** | ? | **Y (upfront estimate, 2026-09-07)** | ? | N | Y | ? | ? |
| Magnific | Y (presets, 2024 UI) | ? | ? | ? | ? | ? | ? | N | **Y (Spaces nodes, List batch node)** | ? | Y (cost in model dropdown) | ? | Unlimited on cheap models only | Y | ? | ? |
| Pollo | Y (Pro) | ? | ? | ? | ? | ? | batch | ? | N | ? | ? | ? | N | Y | ? | ? |
| OpenArt | ? | ? | ? | ? | Y (Director asks questions) | ? | ? | **Y (Director: script → storyboard → 5 min)** | Y (Director agent "Ori") | ? | P ("≈N videos" on pricing; Director cost opaque) | ? | N | ? | ? | ? |
| Midjourney | N | N | N | N | Y ("Auto" motion prompt) | SD vs HD | **4 clips per job** (`--bs` 1/2/4) | N | N | **Y (Explore, public by default)** | P (GPU-minutes) | ? | Relax on Pro/Mega | N (no official API) | – | IPTC only (unsigned) |
| Dreamina / Seedance | P (1.x `camera_fixed`; 2.5 3D blockout) | ? | Y (API) | ? | ? | **Y (2.0 Fast / Mini)** | ? | P | P (CapCut Video Studio canvas) | Y (showcase) | **Y** | ? | "Queue-free" | Y (BytePlus ModelArk) | P (`callback_url` [UNVERIFIED]) | Invisible watermark |
| LTX Studio | Y (dolly, crane, pan, tilt, handheld, static) | Y (brush edit on images) | ? | ? | ? | LTX Fast vs Pro | ? | **Y (script → scenes → shots → timeline → pitch deck)** | Y (Canvas, Flows) | N | P (live balance) | N (14-day refund rule) | N | Y (sync `/v1`, async `/v2` poll) | **N** | ? |
| Sora (RIP) | N | N | N | N | N | – | – | Y (Storyboard) | N | **Y (TikTok-style feed, remix leaderboards)** | N (gens/day) | ? | 30→6 free/day | Y | **Y (`video.completed`)** | **C2PA + moving watermark naming creator** |
| CapCut | – | – | – | – | – | – | variations | **Y (full NLE)** | Y (Video Studio) | via TikTok | Y | ? | free daily credits | – | – | Invisible watermark (Seedance) |

### 1c. Price reference (per second, Sep 2026)

| Offer | Price | Source |
|---|---|---|
| MiniMax H3 API | ≈$0.08/s at 768p, ≈$0.13/s at 2K [S] | [Segmind](https://blog.segmind.com/minimax-h3-release-date-open-weights-and-api-pricing-explained/), [OpenRouter](https://openrouter.ai/minimax/hailuo-3) |
| LTX-2.5 Fast API | $0.09 (720p) / $0.13 (1080p) / $0.19 (1440p) / $0.30 (4K) [C] | [LTX docs pricing](https://docs.ltx.io/pricing.md) |
| LTX-2.5 Pro API | $0.12 / $0.17 / $0.25 / $0.39 [C] | same |
| Kling 3.0 in-app | 6–12 credits/s (≈$0.09–0.18/s); 4K 30 cr/s [C/S] | [Kling 3.0 guide](https://kling.ai/quickstart/klingai-video-3-model-user-guide) |
| Runway Gen-4.5 | 12 credits/s = $0.12/s [C] | [Runway API pricing](https://docs.dev.runwayml.com/guides/pricing/) |
| Veo 3.1 Fast / Lite (with audio) | $0.10–0.12 / $0.05–0.08 per s [C] | [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing) |
| Seedance 2.0 (BytePlus) | $0.07 (480p) → $0.78 (4K) per s [S] | [DataCamp](https://www.datacamp.com/tutorial/seedance-2-0-api-guide) |
| Dreamina consumer promo | ≈$0.05–0.08/s effective [C] | [Dreamina pricing](https://dreamina.capcut.com/seedance/seedance-2-0-pricing) |

Consumer subscriptions cluster at **$8–15 (entry), $28–40 (pro), $76–120 (max), $160–300 (ultra)**:

| Platform | Plans | Source |
|---|---|---|
| Runway | $15 / $35 / $95 | [pricing](https://runway.com/pricing) |
| Luma | $30 / $90 / $300 | [pricing](https://lumalabs.ai/pricing) |
| Kling | $8.80 / $32.56 / $80.96 / $159.99 renewal | [S](https://magichour.ai/blog/kling-ai-pricing) |
| Pika | $8 / $28 / $76 | [pricing](https://pika.art/pricing) |
| LTX Studio | $15 / $35 / $125 | [pricing](https://ltx.io/studio/pricing) |
| Google AI | Pro $19.99 / Ultra $100 / $200 | [S](https://www.engadget.com/2176060/the-google-ai-ultra-plan-now-starts-at-100-a-month/) |

---

## 2. Table stakes in 2026 (every serious platform has these)

Missing any of these makes Kino feel like a demo, not a product.

| # | Table-stakes feature | Evidence (who has it) | Kino v1 coverage via H3 / LTX-2.5 |
|---|---|---|---|
| 1 | **T2V and I2V** | All except Midjourney (I2V only) | Both models |
| 2 | **Start + end frame** | Runway (partial), Kling, Flow, Hailuo, Luma, Pika, Midjourney, Seedance, LTX | H3 FL2VA (first, last, or both); LTX-2.5 `last_frame_uri` / keyframe pipeline |
| 3 | **Native audio (SFX, ambience, dialogue) with an on/off toggle** | Kling, Veo, Hailuo H3, Seedance, Runway Gen-4.5, LTX, Sora | H3 32 kHz stereo; LTX-2.5 24 kHz stereo, `generate_audio` toggle |
| 4 | **Aspect ratios**: at least 16:9, 9:16, 1:1; most also 21:9, 4:3, 3:4 | All | H3: 21:9, 16:9, 4:3, 1:1, 3:4, 9:16; LTX: landscape and portrait |
| 5 | **Durations of 5–15 s** per generation; 10 s is the norm, 15 s the new high end | Kling 3–15, H3 4–15, Seedance 4–15, Veo 4–8, Runway 5–10 | H3 4–15 s; LTX-2.5 Fast 6–20 s, Pro 6–10 s |
| 6 | **1080p output**, plus a 4K path (native or upscale) | Kling 4K native, Veo 4K, Runway, Luma, LTX, Seedance | LTX-2.5 up to 4K; H3 sealed is 768p only (gap) |
| 7 | **References / characters with @-tagging in the prompt** | Kling, Flow, Dreamina, LTX Studio, Krea, Higgsfield, Runway | H3 Ref2VA 9 img / 3 vid / 3 aud |
| 8 | **Extend** a clip | All majors | Last-frame chaining on both; LTX extend pipeline [needs validation on 2.5 open weights] |
| 9 | **Prompt enhancer** | Flow, Hailuo, Runway, Midjourney Auto | In-enclave LLM (must run sealed) |
| 10 | **Camera control** via presets, chips or syntax | Hailuo, Luma, Higgsfield, Kling, Flow, LTX | LTX `camera_motion`; H3 via prompt vocabulary |
| 11 | **Fast/draft vs quality tiers** | Veo Lite/Fast/Quality, Kling Turbo, Seedance Mini, Luma Draft, LTX Fast/Pro | LTX distilled vs full; H3 Turbo 4/8-step distills vs full |
| 12 | **Multiple outputs per prompt (1–4)** | Midjourney 4, Kling ≤4, Flow ≤4 | Parallel jobs |
| 13 | **Library with folders/collections, search, favorites, download without watermark on paid plans** | Flow (Collections), Runway (Assets, Sessions), Midjourney (Organize) | Encrypted library |
| 14 | **Several jobs at once, with visible progress** | Hailuo 2 running / 8–12 waiting; Dreamina "queue-free"; OpenArt 8–32 parallel | Queue UI |
| 15 | **Credit balance always visible; cost shown before generating** | Flow, Higgsfield, Krea, Dreamina, Kling | Must have |
| 16 | **Multi-shot generation (cuts inside one clip)** | Kling, H3, Seedance, LTX-2.5, Runway | Both models natively |
| 17 | **Video-to-video edit / restyle** (rapidly becoming table stakes) | Runway Aleph, Kling Omni, Flow Omni, Luma Modify, Seedance, LTX, Pika | H3 V2V motion transfer; LTX IC-LoRA |
| 18 | **Async API** (create → poll; webhooks optional) | Runway, Luma, Google, Kling, MiniMax, LTX, BytePlus | Kino API |
| 19 | **Mobile app or responsive mobile web** | Kling, Hailuo, Flow (Android beta), Luma (iOS), Higgsfield, Pika | Responsive web in v1 |

---

## 3. Differentiators worth copying, ranked by value for Kino

**Scoring:** Value = user pain solved × fit with Kino's privacy and provenance story × feasible on H3 / LTX-2.5 ÷ effort. The rank reflects that judgment.

| Rank | Differentiator | Who does it best | Why it matters for Kino | Model fit | Effort |
|---|---|---|---|---|---|
| **1** | **Honest-cost system.** Exact cost on the Generate button (credits plus ≈$ plus seconds). Automatic refund on failure or moderation. No Enter-to-submit accidents. Credits don't expire monthly; use annual pools. | Higgsfield (cost on button), Krea (upfront estimate), Hailuo (auto-refund incl. moderated), Magnific (annual pool, no monthly reset), OpenArt ("≈N videos"), Runway API Task Cost | Solves the #1 complaint in the category (Trustpilot 1.1–1.7 at Runway, Luma, Hailuo, LTX, Pika). Trust is Kino's brand, and billing is where users feel it first. | Any | Low |
| **2** | **Private by default, with visible proof.** A per-job "Sealed" indicator showing the attestation receipt. An encrypted library decrypted in the browser. Share links that carry the key in the URL fragment. | Venice (per-model privacy badge plus verification icon that opens the attestation report); NEAR AI (signed responses); Tinfoil ("trust the hardware, not the pinky-promises") | This is Kino's reason to exist. Competitors charge for privacy (Midjourney Stealth $60+) or train on user content by default (Runway, Kling). | Both (TEE) | Medium–High |
| **3** | **Provenance certificate for every video.** C2PA-compatible manifest signed by the enclave key, bound to the attestation. Public `kino.com/verify` page with drag-and-drop checking. A CR-style pin on the player. Optional tail slate. | Nobody complete. Parts exist: Sora (C2PA plus moving watermark with creator name), Adobe (3-level disclosure: pin → popover → Inspect), Leica ("chain of authenticity from camera to cloud"), SynthID Detector (segment highlighting) | Unique and defensible. Brands, agencies and journalists increasingly need provenance, and TikTok, LinkedIn and YouTube read C2PA. | Both | Medium |
| **4** | **Draft → Final pipeline.** Cheap, fast drafts, then promote the chosen take to full quality with the same seed and settings. | Luma Draft→Master; Hailuo 768p→2K Regenerate; Dreamina Mini; Veo Lite; Runway Aleph image preview | Cuts wasted spend. Also plays to LTX-2.5's speed (10 s clip in ~7 s on 2× GB200, vendor claim). | LTX distilled draft → LTX full or 4K; H3 Turbo 4-step → H3 full-step | Medium |
| **5** | **Omni-reference composer.** Auto-labelled slots (`@Image1…9`, `@Video1…3`, `@Audio1…3`), @-autocomplete in the prompt, slot counters, per-slot role. | Dreamina/Seedance, Kling Omni, Flow (`@Name`), LTX Studio Elements | H3 Ref2VA supports exactly this 9/3/3 (≤12). It is the richest input surface in the market, and Kino offers it privately, which matters for faces and voices. | H3 | Medium |
| **6** | **Element Library** of reusable characters, voices, props, locations and styles, stored encrypted | Kling (Elements plus voice binding), LTX Studio (Elements with voices, logos, fonts), Krea Elements, Higgsfield Soul ID, OpenArt Character Builder | Consistency is the top creative need after quality. Private Elements (your face, your client's product) are a strong privacy use case. | H3 (Element expands into reference slots); LTX via I2V keyframes or LoRA (v2) | Medium |
| **7** | **Multi-shot builder** with per-shot fields (shot size, camera move, duration, action, dialogue) | Kling Custom Multi-Shot (≤6 cuts); LTX-2.5 multishot prompting guidance (2–4 shots in 8–10 s) | Both models do multi-shot natively. Structured input raises the success rate. | Both | Low–Medium |
| **8** | **Camera language**: preset chips with preview loops plus bracket commands in the prompt | Higgsfield (50+ presets, gallery with a video per preset), Luma Camera Concepts, Hailuo `[Pan left]` syntax, LTX `camera_motion` | Cinematic identity. Cheap to build. Preset pages are also SEO assets. | LTX param (dolly, jib, static, focus_shift); H3 prompt tokens | Low |
| **9** | **Result action rail**: Extend, Retake a range, Use last frame as next start, Loop, Upscale, Interpolate fps, Replace audio, Reframe | Dreamina (post-gen enhance panel), LTX Studio Retake/Extend, Midjourney hover Extend/Loop, Flow "+" | Keeps users iterating on one good take instead of re-rolling. | LTX pipelines (retake, extend, temporal upscaler); chaining on both | Medium |
| **10** | **Scenebuilder-lite timeline**: arrange shots, "+ Extend / + Jump to", trim, stitch, export | Flow Scenebuilder, LTX Studio timeline, Runway Studio, CapCut | Moves users from clips to films, which the "Kino" name promises. | Both | Medium–High |
| **11** | **Likeness consent and control**: record consent for real people in Elements; revocable; listed in the certificate | Sora cameos (Only me / Approved / Mutuals / Everyone; see and delete every use) | Combines ethics, privacy and provenance. Also helps meet H3 license "safeguards" duties. | Both | Medium |
| **12** | **Visible, editable prompt compiler**: show the enhanced prompt before spending | Hailuo Context-IR (as an explicit step), Flow/Gemini, Midjourney Auto | Transparency and fewer failed spends. Context-IR itself is closed, so run an open LLM in the enclave. | Both | Low |
| **13** | **Compare mode**: same prompt on H3 and LTX side by side | Higgsfield (side-by-side), Pollo (multi-model) | With only two models, comparing is simple and teaches users which model fits which job. | Both | Low |
| **14** | **Developer API**: webhooks, cost quotes, attestation receipts, E2EE SDK | Sora (webhooks, dying 09-24), Runway (Task Cost, Model Router), Luma (auto-refund by failure code), Pika (micro-USD quotes) | Sora API migration; enterprise privacy buyers. | Both | Medium |
| **15** | **Hover-to-play grid**, one-click Animate on any image, one-click Loop | Midjourney | Cheap delight. | Both (loop = same start/end frame) | Low |
| **16** | **Named strength bands** for V2V (Adhere / Flex / Reimagine) instead of a 0–1 slider | Luma Modify | Better UX than a raw slider. | H3 V2V, LTX IC-LoRA strength | Low |
| **17** | **Opt-in showcase** ("Premieres") with certificates and optional prompt reveal | Flow TV (prompts visible), Midjourney Explore, Hailuo feed | Community helps growth, but must be opt-in for Kino. Publishing is an explicit act of unsealing. | – | Medium |
| **18** | **Agents, node workflows, realtime** | Runway, Luma, Krea, OpenArt, Higgsfield | Market direction, but heavy, and they conflict with sealed processing. The agent LLM would also have to run in the TEE. v3. | – | High |

**Anti-patterns to avoid:**
- **"Unlimited" plans that get throttled or walked back.** Higgsfield saw mass bans and an X suspension ([Caimera](https://www.caimera.ai/blogs/higgsfield-ai-twitter-ban-case-study-how-platform-trust-collapses)). Freepik walked back its unlimited offer, and Runway is retiring Unlimited.
- **Introductory prices that jump at renewal** (Kling).
- **Refund rules keyed to zero usage** (Higgsfield: 7 days; LTX: ≤1,200 credits within 14 days).
- **Charging for failed generations.**
- **A public feed by default** (Midjourney).
- **Enter-to-submit.** One Hailuo user lost 105 credits because Shift+Enter submitted the prompt ([Trustpilot](https://www.trustpilot.com/review/hailuoai.video)).
- **Stale promo banners** (LTX Studio pricing page).
- **Aggressive face blocking with no explanation** (Seedance), and blanket "similarity" refusals (Sora).

---

## 4. UX patterns for the Kino creation studio

### 4.1 What the leaders converged on

**Composer placement.** Four of the leaders put the prompt at the center or bottom, with settings attached to it and results flowing above:
- Flow: central prompt box; settings and credit cost at the top right of the box ([Flow help](https://support.google.com/flow/answer/16353333?hl=en)).
- Krea: prompt in the center, settings below, model picker bottom-left, sessions in a left panel ([Krea docs](https://www.krea.ai/docs/user-guide/features/video)).
- Midjourney: prompt bar at the top, results feed below.
- Luma: composer holding keyframe "chiclets", a Draft toggle and a settings panel.

Runway and Kling instead use a left tool panel with a prompt box, a media slot, and settings grouped beside it. Neither pattern clearly wins. For Kino, a bottom-docked composer over a results feed is the best fit: familiar from chat, with the output as the hero.

**Mode switching.** Flow's model-name dropdown opens Image/Video and then Frames or Ingredients. Dreamina offers "Omni reference" vs "First/Last frames". Kling has separate Video and Omni tools. **This matches an H3 constraint exactly: frames and references cannot be combined in one request** ([MiniMax docs](https://platform.minimax.io/docs/guides/video-generation)). The FL2VA and Ref2VA checkpoints are separate. Kino therefore needs a mode switch (Frames / References) rather than one combined upload panel.

**References.** The consensus pattern:
- auto-labelled chips (`@Image1`)
- `@` autocomplete in the prompt
- a persistent library (Kling Element Library, LTX Elements, Flow `@Name` characters, Krea Elements)

**Start/end frames.** Flow uses "+ Add start frame" and "+ Add end frame" drop zones. Luma uses keyframe chiclets that accept drags from boards. LTX sets keyframes at frame indexes. Midjourney makes "Animate" a button on every image.

**Cost display.** Higgsfield shows cost on the Generate button, Krea gives an upfront estimate, Flow shows cost in the settings menu, and Dreamina shows cost before you generate.

**Queue.** Hailuo shows concurrency limits (2 running, 8–12 waiting). Dreamina advertises "queue-free" submission. OpenArt sells parallelism (8/16/32) as a plan feature. Runway's own reason for killing Unlimited was that relaxed mode "led to queuing".

**Results.**
- Midjourney: hover-to-play grid, Extend and Loop on hover, 4 variations per job.
- Flow: every output is its own tile; Collections; multi-select with shift-drag.
- Dreamina: enhancement actions in a right panel after generation (upscale, interpolate, soundtrack).
- LTX Studio: Retake a scrubbed range.
- Runway: comments pinned to a timestamp.

### 4.2 Recommended Kino studio layout (v1)

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│ KINO   Create  Library  Elements  Projects            ◉ Sealed · 3 GPUs attested │  ← top bar: seal status (click → attestation)
├────────┬───────────────────────────────────────────────────────┬─────────────────┤
│Projects│  RESULTS FEED (newest at bottom, grouped by session)  │  INSPECTOR       │
│ ▸ Spot │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                  │  (selected clip) │
│ ▸ Film │  │ ▶ 4s │ │ ▶ 4s │ │ ░░░░ │ │ ░░░░ │ ← in-progress   │  ▶ player        │
│Sessions│  └──────┘ └──────┘ │ 62%  │ │Queued│   placeholder   │  Prompt · seed   │
│  today │  hover = play · ★ · ⋯ (Extend, Retake, Loop, Upscale,│  Model · 768p    │
│  ...   │  Use last frame, Variations, Certificate, Download)   │  [Reuse settings]│
│        │                                                       │  [Certificate ✓] │
│        │                                                       │  Actions rail    │
├────────┴───────────────────────────────────────────────────────┴─────────────────┤
│ COMPOSER  [ Text | Frames | References ]           Model: [H3 ▾] [LTX-2.5 ▾]     │
│ ┌ Frames mode ─────────────────────────┐   ┌ References mode ───────────────────┐ │
│ │ [ Start frame ] ──⇄──▶ [ End frame ] │   │ @Image1 @Image2 +  Img 2/9 Vid 0/3 │ │
│ └──────────────────────────────────────┘   │ Aud 1/3 · 3/12 total  ⚠ audio needs│ │
│ Prompt… (@ to tag · [ ] camera · Shift+Enter = newline, ⌘↵ = generate)  image/vid│ │
│ [16:9▾] [10s▾] [768p▾] [Audio ●] [×2] [Camera: Dolly in ▾] [Enhance ✦] [Advanced▾]│
│                                    ≈ 1m20s  [ Draft · 12 cr ]  [ Generate · 90 cr ]│
└───────────────────────────────────────────────────────────────────────────────────┘
```

**Composer rules**

1. **Mode tabs: Text | Frames | References.** Switching tabs keeps the prompt.
   - With H3 selected, References shows the 9/3/3 slot counters. With LTX-2.5 selected, References is hidden or disabled with a tooltip ("References are an H3 feature; use Frames with LTX").
   - Model capability chips follow Hailuo's pattern ([H3 tool page](https://hailuoai.video/tools/minimax-h3)). For example: "H3 · 4–15 s · 768p · stereo audio · 12 refs" and "LTX-2.5 · 6–20 s · to 4K · 50 fps · fast".
2. **Frames.** Two drop zones side by side with an arrow between them, plus a swap button (⇄) and a "loop" shortcut that copies Start into End.
   - Accept drags from the library and from any result ("Use last frame as start" is the cheapest extend).
   - Show the thumbnail's aspect ratio and warn if it doesn't match the chosen ratio.
3. **References.**
   - Show auto-labelled chips in the order uploaded (`@Image1…`, `@Video1…`, `@Audio1…`).
   - Typing `@` opens an autocomplete that includes saved Elements.
   - Show slot counters and the 12-file total.
   - Validate inline, before any upload, against MiniMax's limits: video 2–15 s and ≤15 s in total; audio references need an image or video present ([MiniMax docs](https://platform.minimax.io/docs/guides/video-generation), [H3 open-source note](https://www.minimax.io/news/minimax-h3-open-source)).
   - Show an "Encrypted on this device" micro-label under the tray.
4. **Settings as chips** in one row: ratio, duration, resolution, audio toggle, count (1–4), camera preset, Enhance.
   - Seed, negative prompt (if supported), fps and the strength band go under "Advanced".
   - **Adapt the chips to the model**, e.g. LTX-2.5 Pro caps at 10 s, and 48/50 fps or 1440p/4K caps Fast at 10 s ([LTX docs](https://docs.ltx.io/models/ltx-2-5)).
   - Grey out invalid combinations, and don't silently change settings.
5. **Two generate buttons: "Draft · N cr" and "Generate · N cr".** Both show the cost in credits, with a hover showing ≈$ and seconds, plus an ETA.
   - **Shortcuts: ⌘/Ctrl+Enter generates. Enter never generates**, which avoids the Hailuo lost-credits complaint.
6. **Enhance ✦** opens the rewritten prompt in a diff view before generating (Accept / Edit / Revert). The rewrite is never silent. It runs in the enclave.

**Queue and progress** (Kino's pipeline has more steps than most, so show them, because they tell the privacy story)
- **In-feed placeholder cards** step through the stages below. Each stage is real and cheap to report without revealing content, and the "Attesting" step makes the privacy tangible.
  1. `Encrypting` (client)
  2. `Queued · #3`
  3. `Attesting GPU` (✓ H100 CC · image hash …)
  4. `Generating 62%` (step counter, or preview frames if the model supports latent previews [UNVERIFIED for H3/LTX])
  5. `Sealing & signing`
  6. `Ready`
- **Global queue drawer** shows "2 running · 5 waiting (plan limit 2/8)", plus cancel, priority (paid), and "notify me" via browser notification or email with no content in it.
- **On failure:** show a clear reason and an automatic refund toast: "Refunded 90 cr: GPU dropped out before completion." Content-policy blocks say which rule was hit and are refunded too, as Hailuo does ([payment policy](https://hailuoai.video/doc/payment-policy.html)).

**Result view**
- **Grid:** hover to play with sound muted. ★ to favourite. The ⋯ menu mirrors the action rail. Multi-select for bulk download or move.
- **Inspector / lightbox:**
  - Player with frame scrubbing.
  - Prompt, model, seed, settings, and **Reuse settings** (one click back into the composer, including frames and references).
  - **Action rail:** Variations (same settings, new seed); Extend (+N s); Use last frame; Retake range (v2); Loop; Upscale / 4K (LTX); Interpolate to 48/50 fps (LTX temporal upscaler, v2); Replace audio (v2); Download (MP4; ProRes in v2).
  - **Certificate tab:** a seal badge, then signer, model and version, enclave measurement, GPU attestation, time, input hashes (not inputs), and a "Copy verify link" button.
- **Compare:** select 2 → side-by-side synced playback (H3 vs LTX).

**Privacy-specific UX (Kino-only)**
- **Seal status pill in the top bar.** Green "Sealed" means the current session keys are bound to attested enclaves. Clicking opens the attestation report in human language first ("Your prompts are encrypted to hardware we can't open"), with raw evidence expandable. Venice's verification icon works this way ([Venice](https://venice.ai/blog/venice-launches-end-to-end-encrypted-ai)).
- **Library search runs on the device** from a local, encrypted index, and the UI says so: "Search runs on your device." Server-side search over prompts would break the promise.
- **Sharing:**
  - "Share sealed link": the key lives in the URL `#fragment`, the pattern Firefox Send and Excalidraw use for end-to-end encrypted share links.
  - "Publish" is a separate, explicit step that makes a video public, with a confirm dialog listing what becomes visible (video yes, prompt optional, references never).
- **Key recovery.** Passkey-based vault keys, plus a recovery kit at signup. Say plainly that if the user loses both, Kino cannot recover their films. Being honest about this is part of the brand.
- **Features that would normally run on a server** (prompt enhancer, moderation, thumbnails, captions/ASR, upscaling) must run **in the enclave or on the client**. Label any feature that can't as "Not sealed" with a toggle. Venice disables features in E2EE mode and says so.

---

## 5. Landing-page patterns, and how Kino should present itself

### 5.1 What the category does now (fetched 2026-09-11)

| Platform | Hero copy | Structure and devices | Pricing on homepage? |
|---|---|---|---|
| Runway | "Building Real-World Intelligence" / "…understand, simulate and act in the world." | Corporate/research positioning. Three pillars (Creative "60m+ creatives", Dev, Robotics). Research block (GWM-1, Gen-4.5). Case study ("$200K on a single clip"). Summit banner ([runway.com](https://runway.com/)) | No |
| Luma | "You have the idea. Luma helps make it real." / "Creative agents for creative professionals" | Agency logos (Publicis, Dentsu, Serviceplan, Mazda), "What's due this week?" use-case tiles. The model page ("Direct any frame. Finish every cut.") has the **pricing table on the model page** and dual CTA "Try in Luma" / "Build with API" ([lumalabs.ai](https://lumalabs.ai/dream-machine), [Ray page](https://lumalabs.ai/ray)) | Model page |
| Kling | "Kling AI: Next-Gen AI Video & Image Generator"; 3.0 = "All in One, One for All" | Tool list (Omni, Video, Image, Sound, Effects, Motion Control, Avatar, Editor), "Create Now", app QR codes ([kling.ai](https://kling.ai/)) | No |
| Hailuo | "H3 LIVE NOW" · "Bring Inspiration to Creation" · "Top-Tier Quality, Versatile References" | Template strip plus a community feed with view counts ([hailuoai.video](https://hailuoai.video/)) | "From $X" |
| Dreamina | "Make Anything, Any Style with AI" | Model launch banner (Seedance 2.5), example-prompt thumbnails ([dreamina](https://dreamina.capcut.com/)) | No |
| Higgsfield | "AI-native creative suite" | Launch carousel ("Cinema Studio 4.0", "Seedance 2.5"), community gallery with creator credit ([higgsfield.ai](https://higgsfield.ai/)) | No |
| OpenArt | "Where Ideas Become Visual Stories" | Cinematic stills, big-brand logos, "TOP AI MODELS. ALL IN ONE PLATFORM" carousel, "UP TO 27% OFF" ([openart.ai](https://openart.ai/)) | Discount banner |
| LTX Studio | "The AI platform for video production" | Audience-split CTAs (networks / agencies / studios), "Choose your starting point" (Script / Concept / Image / Video), testimonials (Taika Waititi, McCann) ([ltx.io/studio](https://ltx.io/studio)) | No |
| Venice (private AI) | "Private AI for Unlimited Creative Freedom" | Four-tier privacy architecture (Anonymized → Private → TEE → E2EE) ([venice.ai](https://venice.ai/)) | Yes |
| Tinfoil (TEE AI) | "We build verifiably private AI so that you can trust the hardware, not the pinky-promises." / "Privacy of local. Power of cloud." | Contrast table (local vs cloud vs Tinfoil); no diagrams; SOC 2 trust center; auditors ([tinfoil.sh](https://tinfoil.sh/)) | No |
| Privatemode (TEE AI) | "The always encrypted AI service" | Three pillars: E2E Confidentiality / E2E Verifiability / External Confirmation, plus compliance badges ([privatemode.ai](https://www.privatemode.ai/)) | No |

**Patterns worth keeping**
1. **A full-bleed autoplay reel of the best outputs** in the hero, silent by default, with a "sound on" affordance. This is now more common on model pages than on corporate homepages. It is still the most persuasive element for creators.
2. **A "new model live" banner** (Hailuo "H3 LIVE NOW", Dreamina, Higgsfield).
3. **Starting-point or use-case tiles** (LTX "Choose your starting point", Luma "What's due this week?").
4. **Model cards with honest one-line trade-offs** (Krea: "Cheapest medium-quality model" ([models](https://www.krea.ai/models))).
5. **Pricing that translates credits** into "≈N videos" (OpenArt) and per-model rate tables on model pages (Luma).
6. **Dual CTA**: Create / Build with API.
7. **Social proof** from the film world, not only tech logos (LTX: Taika Waititi).

**Patterns to avoid**
- Walls of 40 model logos: an aggregator look that commoditizes.
- Research-lab abstraction (Runway now reads like a robotics company).
- Discount-banner clutter.
- Stale promo banners (LTX pricing).

**What privacy brands do (and the gap).** Tinfoil and Privatemode explain TEEs with contrasts, pillars and badges, and **no visuals of the product doing its job**. Venice is the only one with creative media, and its video is not sealed. **Nobody has made privacy cinematic.** That is Kino's white space.

### 5.2 Concrete ideas: communicating "sealed, verified, decentralized" cinematically, not like a crypto site

**Principles**
- Show, don't diagram.
- Film-industry metaphors, not blockchain metaphors.
- Proof over claims.
- The only visible "tech" texture should be precise monospace details (hashes, timestamps) used as typographic ornament, like film edge codes.
- No coins, token tickers, neon gradients, glowing node graphs or "web3" words above the fold. The Bittensor / TAO story lives on a `/network` page for people who want it.

**Vocabulary map** (use the left column in marketing; keep the right column for docs)

| Say (brand) | Means (tech) |
|---|---|
| Sealed / the Darkroom | TEE / confidential computing enclave |
| Encrypted before it leaves your device | Client-side end-to-end encryption to attested keys |
| Proof of hardware / sealed receipt | Remote attestation report (CPU TEE + NVIDIA CC GPU) |
| Certificate / credits (as in film credits) | C2PA manifest signed by an enclave key, bound to the attestation |
| Independent stages / a global crew | Bittensor miners running attested GPUs |
| No single company holds your footage | Decentralized network; no plaintext at Kino |

**Hero concepts** (pick one; each is buildable with video, CSS and WebGL)

1. **"The Darkroom."** The page opens in near-black with a faint red safelight glow. A reel of Kino films "develops" out of the dark: grain resolves into image, the way a print appears in a developer tray.
   - Headline: **"Films develop in the dark."**
   - Sub: "Kino generates video inside sealed hardware. Your prompts, images and footage are encrypted on your device and opened only inside the enclave. Not even the GPU owner can see them. Not even us."
   - CTA: "Start creating" / "See the proof".
   - The metaphor is exact: no one opens the darkroom door while a print develops.
2. **"Sealed until you say cut."** A full-bleed reel plays behind a wax-seal or film-can motif in the corner. When the user clicks "Play with sound", the seal breaks with an audible, satisfying crack and the film unmutes. Privacy becomes a tactile moment.
3. **"Every frame has a signature."** A hero video with a small **CR-style certificate pin** in the corner, like the C2PA pin ([C2PA icon](https://c2pa.org/introducing-official-content-credentials-icon/)). Hovering opens a certificate card styled like end credits:
   ```
   DIRECTED BY  you
   MODEL        MiniMax H3 · FL2VA
   STAGE        Sealed enclave · NVIDIA H100 CC · attested 2026-09-11 14:02 UTC
   SIGNATURE    0x9f3c…a41e  ✓ verified
   ```
   This follows Adobe's three-level disclosure (pin → popover → full Inspect) ([Adobe Design](https://adobe.design/ideas/behind-the-design-adobe-content-authenticity-app)).

**Sections below the hero**

- **"Chain of custody", told as a film strip.** A horizontal filmstrip scrolls past with five frames, each a stage:
  1. *Your device* (lock closes)
  2. *In transit* (only ciphertext)
  3. *The stage* (enclave; hardware proof ✓)
  4. *Sealed print* (output encrypted and signed)
  5. *Back to you* (only you can open it)

  One sentence per frame. No boxes-and-arrows diagram. This is a cinematic version of Leica's "chain of authenticity from camera to cloud" ([CAI blog](https://contentauthenticity.org/blog/leica-launches-worlds-first-camera-with-content-credentials)).
- **Live verification widget ("Check any Kino film").** A drop zone on the landing page: drag a video in and get the certificate or "No Kino certificate found". It works like verify.contentauthenticity.org and SynthID Detector's segment view ([Google](https://blog.google/innovation-and-ai/products/google-synthid-ai-content-detector/)). Proof beats claims, and it gives journalists and brand-safety teams a reason to bookmark Kino.
- **"The stages tonight."** A slow night-map of the world with small warm lights (think city lights from a plane window, not a network graph). Each light is an attested GPU "stage". A quiet monospace ticker underneath: `412 sealed stages online · last attestation 00:00:07 ago · 0 plaintext bytes seen by operators`.
  - This communicates decentralization and verification as ambience. Link: "How the network works →" to `/network` (Bittensor explained there).
  - Only publish live numbers that are true and auditable [design decision].
- **Two film stocks, not a model wall.** Present the two models as film-stock boxes (Kodak Vision3-style labels):
  - **H3** "The Ensemble Stock": 768p · 4–15 s · native stereo dialogue in 11 languages · up to 9 images, 3 videos and 3 voices as references.
  - **LTX-2.5** "The Fast Stock": to 4K · up to 50 fps · drafts in seconds · multi-shot.
  - Each box flips to show sample clips, per-second price, and "best for".
  - This also meets H3's license requirement to display "MiniMax H3" prominently.
- **"What happens to your footage elsewhere."** A calm, sourced comparison, legally reviewed and phrased as facts with links:
  - "Trains on your uploads by default": Runway (non-Enterprise plans) ([terms](https://runway.com/terms-of-use))
  - "License to use your content for model training": Kling (ToS §4.7.3(f)) ([ToS](https://kling.ai/docs/user-policy))
  - "Public gallery unless you pay for Stealth": Midjourney
  - "Operator can technically see prompts": most platforms
  - Kino: "Can't see them. Here's the proof."
- **Pricing that states privacy isn't a tier.** "Every plan is sealed. Every film gets a certificate." Show per-second prices per model and "≈N ten-second films" per plan (OpenArt pattern). Include an auto-refund guarantee badge ("Failed renders are refunded automatically").
- **Film-world proof.** Early-access filmmakers, agencies and newsrooms whose work is confidential before launch: unreleased campaigns, NDA'd pitches, investigative reconstructions. Kino's buyer is the person who *cannot* upload a client's unreleased product to a platform that trains on it.

**Visual system**
- **Palette:** near-black, a tungsten/amber accent (safelight or projector warmth), bone white. Avoid cyan/purple gradients.
- **Type:** an editorial serif or condensed grotesk for display (film-poster energy), and a monospace for proofs and hashes (film edge-code energy).
- **Texture:** 35 mm grain, gate weave on hover, letterboxed 2.39:1 hero crops, sprocket-hole dividers, slate and clapper micro-interactions ("Take 3").
- **Motion:** slow, confident fades and match-cuts. No particle swarms.
- **Sound:** optional, a projector purr on hover over the reel. Muted by default.

**Candidate taglines** (brand options, not research findings)
- "Films develop in the dark."
- "Sealed until you say cut."
- "Private by physics, not by policy."
- "We can't see your film. Not won't. Can't."
- "Every frame signed. Every secret kept."

---

## 6. Recommended MVP: Kino v1 and v2, mapped to H3 and LTX-2.5

### 6.1 What the two models can actually do (sealed, self-hosted open weights)

| Capability | MiniMax H3 (open weights, Aug 2026) | LTX-2.5 (open weights, 2026-08-11) |
|---|---|---|
| Checkpoints / modes | **FL2VA**: T2V, first frame, last frame, first+last. **Ref2VA**: omni-reference. **Frames and references cannot be combined in one request** [C] ([HF README](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/README.md), [MiniMax docs](https://platform.minimax.io/docs/guides/video-generation)) | T2V, I2V, keyframe interpolation (first/last), audio-to-video, V2V via IC-LoRA, inpaint/outpaint [C] ([GitHub](https://github.com/Lightricks/LTX-2), [docs llms.txt](https://docs.ltx.io/llms.txt)) |
| References | ≤9 images, ≤3 videos (2–15 s each, ≤15 s total), ≤3 audio (2–15 s each, ≤15 s total; needs an image or video alongside), ≤12 total [C] | No multi-image "reference" mode like H3's. Consistency comes from keyframes, IC-LoRA control (pose/depth/canny via Union Control) or LoRAs [C/S] |
| Resolution | **768p native** (short side 768). 2K only via the closed H3-Regenerate-2K API [C] | Sources conflict: HF card says 1920×1088 native plus a 2× upscaler to 3840×2176; LTX's own fact page says "native 4K HDR"; `research_models.md` notes stage 1 at 544×960 with ×2 upscale [conflict, verify in engineering]. The API offers 720p, 1080p, 1440p and 4K [C] ([docs](https://docs.ltx.io/models/ltx-2-5)) |
| Duration | 4–15 s, whole seconds [C] | Open weights: frame count must be 8k+1. API Fast: 6–20 s (720p/1080p, 24/25 fps); Pro: 6–10 s [C] |
| FPS | 24 [C] | 24 / 25 / 48 / 50; temporal upscaler ×2 or ×4 [C] |
| Aspect ratios | 21:9, 16:9, 4:3, 1:1, 3:4, 9:16 (+ adaptive) [C] | Landscape and portrait; width and height divisible by 32 [C] |
| Audio | Native **32 kHz stereo**, dialogue in 11 languages [C] | Native **24 kHz stereo**, toggleable; Foley; Dub-It; text-to-audio [C/S] |
| Multi-shot | Native [C] ([blog](https://www.minimax.io/blog/minimax-h3)) | Native (best at 2–4 shots in 8–10 s; cut timing set by prose) [C/S] ([Runware guide](https://runware.ai/docs/models/lightricks-ltx-2-5-pro/guides/multi-shot)) |
| Camera | Prompt language only. The bracket syntax is documented for Hailuo API models; whether H3 honors `[Pan left]`-style tokens is [UNVERIFIED] | API `camera_motion`: dolly_in/out/left/right, jib_up/down, static, focus_shift [C] (open-weights equivalent is LoRA- or prompt-based [UNVERIFIED]) |
| V2V / edit | Motion transfer and multimodal editing via reference video [C] | Union Control IC-LoRA; Motion-Track; Video-Editing IC-LoRA (beta: object removal, environment swap); HDR IC-LoRA (EXR) [C] |
| Retake / Extend | Extend by last-frame chaining (FL2VA) [design inference] | Hosted API offers Retake/Extend/Reframe on **ltx-2-3-pro only**. Whether the open pipelines support these on 2.5 is [UNVERIFIED], so validate |
| Speed and cost | ≈74 s per 5 s 1344×768 50-step clip on 4× H200 BF16 [S]. LightX2V **4- and 8-step Turbo** distills give ≈3.4–5× speedup (still under the H3 license) [S] | 10 s I2V in 6.8 s on 2× GB200 (vendor claim) [S]. Distilled 8-step; FP8 variants fit ~32 GB [C/S] |
| License | **MiniMax H3 Community License:** excludes US/EU/UK/KR; prominent "MiniMax H3" UI attribution; >$20M revenue needs authorization; no training other models on outputs; hosted services must keep AUP safeguards [C] | **LTX-2.x Community License:** free under $10M revenue; SaaS hosting allowed; AUP [C] |

### 6.2 Kino v1: "Sealed studio" (launch)

**Goal:** match table stakes on two models, and ship the three things nobody else has: sealed processing, certificates, and honest billing.

**Generation**
- **T2V:** both models.
- **I2V (start frame):** both.
- **Start + End frame:** H3 FL2VA; LTX-2.5 keyframe interpolation.
- **References mode, H3 only:** 9 image / 3 video / 3 audio slots with auto-labels and @-autocomplete, plus inline validation.
- **Settings:**
  - Audio on/off: both.
  - Aspect ratio: H3 six ratios; LTX 16:9 and 9:16 (plus others if the pipeline allows).
  - Duration: H3 4–15 s; LTX 6–20 s draft / 6–10 s quality. Must be verified against the open pipeline.
  - Resolution: H3 768p; LTX 1080p, with 1440p/4K on paid plans.
  - Outputs per prompt: 1–4.
  - Seed (Advanced).
- **Multi-shot:** a simple "Shots" toggle that inserts a structured template ("Shot 1 (wide, dolly in): …; Hard cut to Shot 2 (close-up): …"). Both models. Warn about lip-sync across cuts ([Runware](https://runware.ai/docs/models/lightricks-ltx-2-5-pro/guides/multi-shot)).
- **Camera chips:** about 12 presets with preview loops, mapped to LTX `camera_motion` and to prompt phrases for H3: static, dolly in/out, truck left/right, pedestal/jib up/down, pan, tilt, orbit, handheld, crash zoom, focus shift.
- **Prompt enhancer:** an open LLM in the enclave, shown as an editable diff. This replaces Context-IR, which is closed.
- **Draft → Final:**
  - LTX: distilled at 720p → full at 1080p or 4K, same seed.
  - H3: 4-step Turbo → full-step, same seed.
  - Label drafts honestly ("Drafts are ≈80% cheaper; final may differ slightly") [ratio to be measured].
- **Extend (basic):** "Use last frame as start" plus a one-click "Extend +N s", which chains the last frame and optionally the previous prompt. Both models.
- **Loop:** start frame = end frame. H3 FL2VA; LTX keyframes.

**Studio and library**
- The layout in §4.2: composer with Text / Frames / References tabs, results feed, inspector, queue drawer.
- **Encrypted library:** projects and folders, favorites, on-device search, hover-to-play grid, multi-select, Reuse settings, download MP4 without watermark on paid plans.
- **Compare:** two clips side by side.
- **Seal status pill and per-job attestation receipt.**

**Provenance**
- A **certificate for every video**: a C2PA manifest embedded in the MP4, signed by a key that lives only in attested enclaves, and bound to the attestation evidence (model and version hash, container measurement, GPU CC report, timestamp, hashes of inputs; never the inputs themselves).
- A **public verify page** (`kino.com/verify`, drag and drop) plus a "Copy verify link".
- A **CR-compatible pin** in Kino's player.
- An optional 1-second end slate ("Made with MiniMax H3 on Kino · Verified"), off by default on paid plans.
- Note: social platforms strip C2PA on upload. Offer an **opt-in public registry** keyed by content hash so re-uploads can still be checked. It publishes hashes only [design].

**Billing and trust**
- Cost on the Generate button, credits → ≈$ → seconds.
- **Automatic refunds** for failed, timed-out or moderated jobs, with the reason shown.
- ⌘+Enter to generate.
- **Annual credit pools with no monthly expiry**, or at least a 2-month rollover.
- "≈N ten-second films" on the pricing page.
- No "unlimited" plan.
- Per-second pricing anchored to the market: H3 768p ≈$0.08/s at MiniMax; LTX-2.5 Fast $0.09–0.30/s by resolution; Kling 3.0 ≈$0.09–0.18/s ([§1c](#1c-price-reference-per-second-sep-2026)).

**Moderation (required)**
- The H3 license obliges hosted services to keep AUP safeguards, and E2EE means Kino can't moderate server-side in plaintext.
- So: **in-enclave classifiers** on prompt, reference images and output. Publish the policy. Refund blocked jobs.
- Record in the certificate that the policy check ran, without revealing content [design].

**API v1**
- `POST /v1/generations` (polymorphic by `mode`: text, frames, references) → `202 {id}`.
- `GET /v1/generations/{id}`.
- **Webhooks** with signed payloads (`generation.completed` / `failed` / `refunded`) and no content in the payload.
- `POST /v1/estimate` returns the exact cost.
- `GET /v1/attestation` returns the current enclave evidence.
- An E2EE client SDK (TypeScript and Python) that encrypts to attested keys.
- Market this to Sora API refugees before and after 2026-09-24.

**Compliance gating**
- **H3 geofence:** H3 is unavailable to US/EU/UK/KR users unless MiniMax authorizes it. Launch with LTX-2.5 as the default model for everyone, and H3 where licensed.
- Apply for MiniMax's authorization before launch; the model card links a form. This is the single biggest v1 risk (see `research_models.md` §1.3).
- The "MiniMax H3" name must appear prominently in the UI wherever H3 is used.

**Explicitly not in v1**
- Community feed, agent, nodes, timeline editor.
- Lip-sync to user audio, beyond what H3 audio references do natively.
- 2K H3. The closed Regenerate step would break the sealed promise. If ever offered, it must be labelled "Leaves the enclave".

### 6.3 Kino v2: "Sealed production" (about 3–6 months after launch)

| Feature | Models | Borrowed from |
|---|---|---|
| **Element Library.** Encrypted, reusable characters, voices, props, locations and styles. An Element expands into H3 reference slots; for LTX, into keyframes or a LoRA | H3 (native), LTX (via LoRA training in the enclave) | Kling Elements, LTX Studio, Krea, Higgsfield Soul ID |
| **Likeness consent.** Real-person Elements need a consent capture (a Sora-style one-time recording or signed consent), stored as a revocable record and shown in the certificate as "consent on file" | Both | Sora cameos |
| **Multi-shot builder.** Per-shot fields (duration, shot size, camera, action, dialogue, speaker), up to about 4–6 shots | Both | Kling Custom Multi-Shot |
| **Scenes timeline (Scenebuilder-lite).** Arrange clips, "+ Extend" / "+ Jump to (new shot, same Elements)", trim, stitch, audio bed, export MP4 or ProRes, XML for NLEs | Both | Flow Scenebuilder, LTX Studio timeline, CapCut |
| **Retake a range.** Regenerate 2–16 s of a clip; replace video, audio or both | LTX (validate 2.5 open pipeline; else 2.3) | LTX Studio Retake |
| **V2V / Restyle.** Named strength bands (Adhere / Flex / Reimagine); motion transfer from a reference video; pose/depth/edge control | H3 Ref2VA with video references; LTX Union Control IC-LoRA | Luma Modify, Kling Motion Control, Runway Aleph |
| **Object edit (beta).** Remove, replace or swap an environment | LTX Video-Editing IC-LoRA (beta) | Flow insert/remove, Pika swaps |
| **Audio tools.** Replace or regenerate audio, Foley, dub or lip-match to uploaded voice | LTX A2V / Foley / Dub-It; H3 audio references | Kling lip sync, LTX Studio |
| **Upscale and finish.** 4K spatial upscale, 48/50 fps interpolation, HDR / EXR export | LTX upscalers and HDR IC-LoRA (applied to H3 768p output too [UNVERIFIED quality]) | Luma Draft→Master HDR, Runway Ruby, Dreamina |
| **Captions and reframe.** Auto captions via in-enclave ASR; auto-reframe 16:9 ↔ 9:16 ↔ 1:1 | Enclave ASR; LTX outpaint | CapCut |
| **Camera preset gallery.** A page per preset with a preview video ("Use this move") | Both | Higgsfield |
| **Teams.** Shared encrypted vaults (key wrapping per member), timestamp-pinned comments, brand kits | – | Runway Team plan, comments |
| **"Premieres."** Opt-in public showcase; every film carries a verified certificate; optional prompt reveal; "remix" only if the author allows | – | Flow TV, Sora remix, Midjourney Explore |
| **Mobile apps** | – | Kling, Hailuo, Higgsfield |

### 6.4 v3 and later (watch list)
- **Script → storyboard → shots:** LTX Studio, OpenArt Director.
- **Agent that plans multi-shot projects:** Runway Agent, Luma Agents. Needs an LLM in the enclave.
- **Node workflows → shareable "Apps":** Runway, Krea, Magnific Spaces.
- **Realtime preview:** Krea Realtime.
- **3D blockout camera staging:** Seedance 2.5, Krea Seedance Studio.
- **Long-form (30 s+ single pass):** Seedance 2.5; depends on future open models.

---

## 7. Risks and open questions

1. **H3 license territory** (US/EU/UK/KR excluded) and the ">$20M" and attribution clauses. Get written authorization or geofence. Legal review needed.
2. **LTX-2.5 open-pipeline parity.** Verify in engineering: native resolution (1088p vs 4K), maximum duration, retake/extend availability on 2.5, and a camera-motion equivalent. The hosted API documents Retake/Extend on 2.3-pro only ([LTX docs](https://docs.ltx.io/models.md)).
3. **H3 is 768p while competitors default to 1080p and offer 4K** (Kling 4K native, Veo 4K, Seedance 4K). Mitigations: an LTX upscale pass (quality unverified) and positioning H3 as the "reference and dialogue" engine rather than the resolution engine.
4. **Latency.** H3 full-step is slow (≈74 s per 5 s on 4× H200 [S]) and TEE adds overhead. Draft modes and honest ETAs are essential.
5. **Moderation under E2EE.** It must be in-enclave. False positives are a known pain (Seedance face blocking, Sora "similarity" refusals). Publish the policy and refund.
6. **Provenance durability.** C2PA gets stripped by social platforms, and watermark removers exist ([GitHub](https://github.com/wiltodelta/remove-ai-watermarks)). Pair the embedded manifest with an opt-in hash registry. Consider an invisible watermark as a third layer, which is also privacy-neutral.
7. **Krea already sells H3, H3 Max and Turbo at 1080p.** Kino's moat is privacy, provenance and trust, not model access. Marketing must lead with that.
8. **Competitor facts that conflicted or couldn't be verified:** Seedance 2.5 maximum resolution; Kling Ultra price; whether Kling still has Motion Brush on 3.0; Higgsfield pricing (two conflicting snapshots); Midjourney pricing (docs 403); Flow Extend availability by model (help pages disagree).

---

## 8. Platform profiles (condensed; sources inline)

### 8.1 Runway ([runway.com](https://runway.com/); runwayml.com redirects)

**Where it stands**
- **Models and releases:**
  - Gen-4.5: 2025-12-01 ([research](https://runway.com/research/introducing-runway-gen-4.5)); I2V 2026-01-21.
  - Aleph 2.0 + Edit Studio: 2026-05-21 ([news](https://runway.com/news/introducing-aleph-2-and-edit-studio)).
  - Agent: 2026-05-13 (2.0 on 06-25); Studio editor 06-18; Team plan 09-04; Premiere/After Effects plugins 09-08 ([changelog](https://runway.com/changelog)).
  - Also resells Veo 3.1, Kling 3.0, Sora 2 Pro, Seedance 2.0/2.5, Wan 3.0, Hailuo 3.0.
- **No Gen-5.**

**Modes**
- Gen-4 References: 3 tagged images ([help](https://help.runwayml.com/hc/en-us/articles/40042718905875-Creating-with-Gen-4-Image-References)).
- Aleph 2: V2V edits up to 30 s at 1080p. Edit one frame and the change propagates across shots ([Aleph](https://runway.com/product/aleph-2)).
- Act-Two: performance capture ([help](https://help.runwayml.com/hc/en-us/articles/42311337895827-Performance-Capture-with-Act-Two)).
- Native audio on Gen-4.5; Seed Audio; ElevenLabs TTS.
- Magnific 4K upscale; "Ruby" SDR→HDR; ProRes/EXR export; SAM3 segmentation.
- Start/end on Gen-4.5 is [UNVERIFIED]. Loop not found.

**Controls**
- Durations 5/8/10 s [S]; 6 ratios (Gen-4 Turbo) [S].
- Seed lock; numeric camera panel [S, possibly Gen-3-era].

**UX**
- Left sidebar: Home, Assets, Sessions, All Tools (pinnable), Video Editor Projects.
- Model dropdown above the prompt; image slot beside it; settings bottom-right [S].
- Three modes: Tool, Agent (timeline, Skills), Workflows (nodes → publish as workspace "Apps").
- Timestamp-pinned comments; Brand Kits.

**Pricing** ([pricing](https://runway.com/pricing))
- Free: 125 credits once.
- Standard $15 (625), Pro $35 (2,250), Max $95 (9,500).
- Gen-4.5 costs 12 credits/s. Unlimited/Explore Mode is being retired; legacy users keep it to 2026-11-30.

**API** ([docs](https://docs.dev.runwayml.com/))
- `X-Runway-Version` header. Create returns an id; poll `GET /v1/tasks/{id}` (PENDING→THROTTLED→RUNNING→SUCCEEDED/FAILED/CANCELLED).
- SDK `waitForTaskOutput`. No documented webhooks.
- Task Cost API, Model Router with fallback and cost caps, MCP.

**Sentiment**
- Trustpilot 1.1/5 (328 reviews). Themes: "a month of credits at $35… less than 60 seconds of usable content", no refunds for failed renders, bot-only support ([Trustpilot](https://www.trustpilot.com/review/runwayml.com)).
- Praised for Gen-4.5 prompt adherence and Aleph.

**Data use:** trains on Inputs/Outputs by default except Enterprise ([terms](https://runway.com/terms-of-use)).

**Copy:** Aleph's image preview before the video render, Task Cost, Workflows→Apps, pinned comments.

### 8.2 Kling ([kling.ai](https://kling.ai/))

**Where it stands**
- Models: O1/Omni (2025-12-02); 2.6 (first native audio); 3.0 and 3.0 Omni (2026-02-05) ([PR](https://www.prnewswire.com/news-releases/kling-ai-launches-3-0-model-ushering-in-an-era-where-everyone-can-be-a-director-302679944.html)); 3.0 Turbo (2026-06-17) [S].
- Scale: 60M+ creators, 600M+ videos.

**Modes** ([3.0 guide](https://kling.ai/quickstart/klingai-video-3-model-user-guide), [Omni guide](https://kling.ai/quickstart/klingai-video-3-omni-model-user-guide))
- 3–15 s at 720p/1080p; native 4K on the 3.0 series.
- Start/end frames.
- **Multi-Shot / Custom Multi-Shot:** up to 6 cuts, with per-shot duration, shot size, perspective, narrative and camera ([blog](https://kling.ai/blog/kling-video-3-omni-multi-shot-native-audio-guide)).
- **Elements:**
  - Omni takes ≤7 images or Elements, or 4 when a video reference is used.
  - An Element is 4 angle images or a 3–8 s clip.
  - **Voice binding** from 5–30 s of audio.
- **Motion Control:** 3–30 s reference video ([guide](https://kling.ai/quickstart/motion-control-user-guide)).
- Lip sync ([guide](https://kling.ai/quickstart/ai-lip-sync-guide)); native audio in 5 languages; Effects; AI Avatar.
- Motion Brush on 3.0 and virtual try-on are [UNVERIFIED].

**UX**
- Left sidebar of creation modes; prompt, upload zone and settings grouped together; "My Creatives" [S].
- **@-tagging** `@Image` / `@Video` / `@Element`; persistent Element Library ([O1 guide](https://kling.ai/quickstart/klingai-video-o1-user-guide)).
- Up to 4 outputs (2.6). Desktop and mobile apps.

**Pricing**
- Standard $6.99 → $8.80 at renewal, 660 credits; Pro $32.56, 3,000; Premier $80.96, 8,000; Ultra $159.99, 26,000 [S] ([Magic Hour](https://magichour.ai/blog/kling-ai-pricing)).
- 3.0 costs 6/8 credits/s (720p/1080p), 9/12 with audio, 30 at 4K.

**API:** async with `callback_url`; about $0.112–0.168/s [S].

**Sentiment**
- Loved for motion quality and I2V; less censored than Seedance.
- Hated for failures that still consume credits (30–40% at peak reported), waits up to 15 minutes, and renewal price jumps ([Roborhythms](https://www.roborhythms.com/kling-ai-review-2026/)).

**Data use:** ToS §4.7.3(f) permits using content to train models; §4.8 lets others "Recreate" published works; visibility is user-controlled (§3.6) ([ToS](https://kling.ai/docs/user-policy)).

### 8.3 Google Flow and Veo 3.1 / Gemini Omni Flash ([flow.google.com](https://flow.google.com/))

**Models** ([Flow models help](https://support.google.com/flow/answer/16352836?hl=en))
- Veo 3.1 Lite/Fast/Quality: 4/6/8 s, 16:9 or 9:16.
- Gemini Omni Flash (I/O, 2026-05-19): 4–10 s, any-to-video, conversational editing ([blog](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-omni/)).
- No Veo 4 [S].

**Modes**
- "+ Add start frame / + Add end frame" ([help](https://support.google.com/flow/answer/16353334?hl=en)).
- Ingredients (API ≤3 images), `@Name` characters, `@me`, voice references.
- Extend (API +7 s × 20 = 148 s at 720p) and Jump to ([API](https://ai.google.dev/gemini-api/docs/veo)).
- Insert/remove objects; lasso select and draw (Feb 2026) ([blog](https://blog.google/innovation-and-ai/models-and-research/google-labs/flow-updates-february-2026/)).
- Upscale: 1080p free, 4K on Ultra (50 credits).

**UX**
- Central prompt box. The model name opens Image/Video → Frames/Ingredients. Settings and credit costs at the top right of the box ([Get started](https://support.google.com/flow/answer/16353333?hl=en)).
- Library grid with Collections, search and filter; each output is its own tile.
- Scenebuilder: "+" → Extend / Jump to; Arrange.
- **Flow TV:** curated channels that show every clip's prompt.
- Flow Tools: text-to-utility builder. Android beta.

**Pricing** ([credits help](https://support.google.com/flow/answer/16526234?hl=en))
- Free 50 credits/day; Pro $19.99 (+1,000); Ultra $100 (+10,000) / $200 (+25,000).
- Veo 3.1 Lite 10, Fast 20, Quality 100 credits; Omni Flash 4–15.

**API:** `predictLongRunning` + poll, **no webhooks**; 1 video per request; results stored 2 days. Veo 3.1 costs $0.40/s, Fast $0.10–0.30, Lite $0.05–0.08 ([pricing](https://ai.google.dev/gemini-api/docs/pricing)).

**Provenance**
- SynthID on all outputs; visible watermark optional ([help](https://support.google.com/flow/answer/16353333?hl=en)).
- Checking is done by uploading to Gemini (≤100 MB, <90 s) ([Gemini help](https://support.google.com/gemini/answer/16722517?hl=en)). C2PA verification in the Gemini app since I/O 2026 ([blog](https://blog.google/innovation-and-ai/products/identifying-ai-generated-media-online/)).
- Whether Veo files carry signed C2PA manifests is [UNVERIFIED].

**Sentiment**
- Loved: native dialogue, Scenebuilder consistency.
- Hated: "Something went wrong" failures that take credits (refunds delayed), confusion over which model has which feature, Chromium-only, region locks ([Google forum](https://discuss.ai.google.dev/t/veo-flow-generation-issues-lost-credits-consistency-problems-and-excessive-failed-generations/147374)).

### 8.4 MiniMax Hailuo ([hailuoai.video](https://hailuoai.video/))

**Models**
- H3 (see §6.1).
- H3 Max (with fal): 480p/768p, 5–15 s.
- Hailuo 2.3 / 2.3-Fast, 02, S2V-01 (single-face subject reference) ([S2V API](https://platform.minimax.io/docs/api-reference/video-generation-s2v)).
- Also resells Veo 3.1 and Sora 2 [S].

**Controls**
- **15 bracket camera commands:** `[Truck left/right]`, `[Pan left/right]`, `[Push in]`, `[Pull out]`, `[Pedestal up/down]`, `[Tilt up/down]`, `[Zoom in/out]`, `[Shake]`, `[Tracking shot]`, `[Static shot]`; up to 3 combined ([T2V API](https://platform.minimax.io/docs/api-reference/video-generation-t2v)).
- `prompt_optimizer` on by default.
- H3 app: 5–15 s, 768p/2K, six ratios, capability tags per model ([H3 page](https://hailuoai.video/tools/minimax-h3)).

**UX**
- Top nav: Create Video / Image / Agent / Design / Assets / Tools / Audio; template strip; home feed with view counts.
- Video Agent: templates → semi-custom → autonomous, showing its reasoning steps ([news](https://www.minimax.io/news/video-agent)).
- Queue limits: 1–2 running, 3–12 waiting depending on plan.
- **Automatic refunds on failed or moderated jobs** ([payment policy](https://hailuoai.video/doc/payment-policy.html)).

**Pricing:** Standard ≈$10.50–14.99, Pro ≈$38–54.99, Master ≈$89–119.99, Max ≈$216 (two card versions) [C/S].

**API** ([docs](https://platform.minimax.io/docs/guides/video-generation))
- `POST /v2/video_generation` with `content[]` roles (`first_frame`, `last_frame`, `reference_image`/`_video`/`_audio`).
- `callback_url` with a challenge echo within 3 s; poll every 10 s.
- Extra tasks: H3-Context-IR (prompt compiler) and H3-Regeneration (2K; resend the full original request plus `base_video`).

**Sentiment**
- H3 loved for instruction following, physical interaction and integrated audio ([virse](https://www.virse.ai/blog/minimax-h3-reddit-review)).
- Hated: slow local runs, softer output in reference mode, slow-motion feel, unwanted music. Trustpilot 1.4/5, including the Shift+Enter credit loss ([Trustpilot](https://www.trustpilot.com/review/hailuoai.video)).

### 8.5 Luma ([lumalabs.ai](https://lumalabs.ai/); "Dream Machine" brand deprecated per [llm-info](https://lumalabs.ai/llm-info))

**Models:** Ray3 (2025-09-18), Ray3.14 (2026-01-26), **Ray3.2 (2026-06-09)** ([news](https://lumalabs.ai/news/introducing-ray-3-2)). Also resells Veo, Kling, Seedance and others.

**Modes**
- **Up to 16 keyframes** (API up to 64 via `keyframe_indexes`) ([API](https://docs.agents.lumalabs.ai/guides/model)).
- Modify Video: 9 strength levels in bands **Adhere / Flex / Reimagine** ([help](https://lumaai-help.freshdesk.com/support/solutions/articles/151000214475-what-does-strength-do-on-modify-video-)); Modify V2 up to 20 s at 1080p, keeps the audio and performance.
- Reframe; loop (T2V); extend.
- **Native 16-bit HDR, EXR/ACES** ([Ray](https://lumalabs.ai/ray)).
- Draft 360p → Master 4K HDR "without changing identities, motion, or composition" ([guide](https://lumalabs.ai/learning-hub/ray3-user-guide)).
- No native audio or lip-sync.

**Controls**
- **Camera Concepts** chips: Pull Out, Orbit, Dolly Zoom, Tiny Planet, Bolt Cam, Aerial Drone, and more ([news](https://lumalabs.ai/news/camera-motion-concepts)).
- **Scribble annotations on keyframes.**

**UX:** Luma App: infinite canvas; Agents explore several directions in parallel; semantic search; real-time collaboration ([learning hub](https://lumalabs.ai/learning-hub/the-new-luma-app-creative-multimodal-agent)).

**Pricing** ([pricing](https://lumalabs.ai/pricing))
- Plus $30 (10k credits), Pro $90 (40k), Ultra $300 (150k); no free tier.
- Ray3.2 per 5 s: 20 (draft) / 50 / 100 / 400 (1080p) credits. HDR costs ×2, EXR ×3.

**API** ([FAQ](https://docs.agents.lumalabs.ai/guides/faq/))
- One `POST /v1/generations` polymorphic endpoint; poll; URLs expire after 1 h and are re-issued.
- **Auto-refunds by failure code**; no webhooks. The legacy API had `callback_url`.

**Sentiment:** Trustpilot 1.5/5, e.g. "used 10k credits… on 1.5 videos" ([Trustpilot](https://www.trustpilot.com/review/lumalabs.ai)). Praised for HDR and prompt adherence.

### 8.6 Pika ([pika.art](https://pika.art/))

**Where it stands:** Pika has pivoted to "Pika Universe": agents, MCP, the Pika Video App, AI Trendmaker. There is an iOS social app (Oct 2025) and a "Pika – AI Agent" app with PikaStream live video ([App Store](https://apps.apple.com/us/app/pika-ai-agent/id6758411447)).

**Modes**
- Pika 2.5 T2V/I2V.
- **Pikaframes:** ≤5 keyframes, per-transition prompt and 1–10 s duration, ≤25 s total ([fal](https://fal.ai/models/fal-ai/pika/v2.2/pikaframes)).
- Pikaswaps / Pikadditions / Pikatwists / Pikaffects / Pikascenes.
- Pikaformance lip-sync, ≤30 s at 3 credits/s.

**Pricing** ([pricing](https://pika.art/pricing))
- $8 / $28 / $76 per month.
- **A per-feature × per-resolution credit table.**

**API:** [dev.pika.art](https://dev.pika.art/) is a multi-model API (it includes H3) that quotes every operation "in micro-USD".

**Sentiment:** Trustpilot 1.7/5, citing credit burn and unresponsive support ([Trustpilot](https://www.trustpilot.com/review/pika.art)).

### 8.7 Higgsfield ([higgsfield.ai](https://higgsfield.ai/))

**Where it stands:** $5.4B valuation; about $700M annualized revenue; 30M users ([TechCrunch](https://techcrunch.com/2026/08/17/higgsfield-raises-400m-series-b-quadrupling-its-valuation-in-8-months-to-5-4b/)). Aggregates Kling, Seedance, Veo, Wan, Sora, Hailuo, Grok, and its own DOP model.

**Controls**
- **50+ camera presets** ([camera-controls](https://higgsfield.ai/camera-controls)): Crash Zoom, Dolly Zoom, Bullet Time, 360 Orbit, FPV Drone, Snorricam, Whip Pan, Through Object, Robo Arm, and more.
- **Cinema Studio:** camera body, lens and focal length; stacked moves.
- About 50 VFX presets ([viral-presets](https://higgsfield.ai/viral-presets)) and many apps.

**Workflow**
- Soul ID for trained faces.
- Popcorn: 4 numbered references → 8 consistent frames, **cost shown on the Generate button** ([help](https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-popcorn)).
- Side-by-side model comparison; Canvas; Supercomputer agent; MCP/CLI.

**Pricing:** conflicting snapshots ($39–59 Plus, $99–129 Ultra) [UNVERIFIED]. "Unlimited" is time-boxed and web-only.

**Sentiment**
- Trustpilot 4.0 from 4,303 reviews.
- The "unlimited" controversy included mass bans, an X suspension on 2026-02-09 ([Caimera](https://www.caimera.ai/blogs/higgsfield-ai-twitter-ban-case-study-how-platform-trust-collapses)), and backlash over a "put an end to more than 20 creative jobs" post ([The Register](https://www.theregister.com/software/2026/02/06/ai-video-startup-boasts-it-ended-jobs-gets-backlash/5059063)).

### 8.8 Krea ([krea.ai](https://www.krea.ai/))

**Models:** 40+, grouped by type, each with an honest trade-off label ([models](https://www.krea.ai/models)). **H3, H3 Max and H3 Max Turbo, with 1080p and H3 Max multimodal references** (2026-08-27 → 09-09) ([changelog](https://www.krea.ai/docs/changelog)).

**Features**
- Hover → Extend; start/end frames ([docs](https://www.krea.ai/docs/user-guide/features/video)).
- **Realtime video:** Krea Realtime 14B, Apache-2.0, 11 fps on a B200 ([GitHub](https://github.com/krea-ai/realtime-video)); Realtime Director (2026-09-07).
- Elements (09-09); Seedance Studio with camera control, annotations and 3D keyframing.
- Nodes + App Builder; Agent (09-10).
- **Upfront cost estimates** (09-07).

**Pricing:** Free 100 compute units/day; Max $105 (60k); Business $200 (80k); Basic and Pro [S].

**Sentiment:** "compute unit system stresses me out" [S].

### 8.9 Magnific, formerly Freepik (rebranded 2026-04-28 [S])

**Features**
- 36+ video models [S].
- **Spaces** node canvas with a "List" batch node ([docs](https://www.freepik.com/ai/docs/utility-nodes)).
- Kling Motion Control ([blog](https://www.magnific.com/blog/kling-2-6-motion-control/)).

**Pricing** ([pricing](https://www.magnific.com/pricing))
- Premium $20 (240k credits/yr), Premium+ $45 (600k, unlimited on Nano Banana and Kling 2.5 at 720p/5 s), Pro Starter $110.
- **"Credits valid for 1 year, no monthly resets."**

**Lesson:** the walk-back of "unlimited" on 30+ models burned annual subscribers [S] ([eesel](https://www.eesel.ai/blog/freepik-ai-pricing)).

### 8.10 Pollo AI ([pollo.ai](https://pollo.ai/))

**Features**
- HIX.AI-owned aggregator plus its own Pollo 2.5/1.6 models ([PR](https://www.prnewswire.com/news-releases/pollo-ai-releases-multi-model-support-offering-all-in-one-video-generation-capabilities-302348811.html)).
- **200+ effects templates** (AI Hug, Squish, Melt…) used as SEO pages.
- Lip-sync in 15+ languages; consistent characters; batch; unified API.

**Pricing:** Lite $10 / Pro $25 [UNVERIFIED].

**Sentiment:** Trustpilot 4.3 from 5,318 reviews ([Trustpilot](https://www.trustpilot.com/review/pollo.ai)).

### 8.11 OpenArt ([openart.ai](https://openart.ai/))

**Features**
- Aggregator with Character Builder.
- **Director** (2026-06): chat with "Ori" to go from script → storyboard → multi-shot video up to 5 minutes ([blog](https://openart.ai/blog/how-to-use-openart-director/)).
- One-Click Story templates.

**Pricing** ([pricing](https://openart.ai/pricing))
- $14–240 per month.
- **"≈N videos / ≈N characters" per plan**; parallel generations (8/16/32) as a plan feature.

**Sentiment:** hated for opaque Director costs ("20,000 credits instantly") [S].

### 8.12 Midjourney Video

**Where it stands:** V1, launched 2025-06-18 ([MJ](https://updates.midjourney.com/introducing-our-v1-video-model/)). I2V only; a video V2 is on the roadmap [UNVERIFIED].

**Modes and controls**
- **4 × 5 s clips per job**; Animate Auto/Manual × Low/High motion.
- `--end`, `--loop` ([PiAPI](https://piapi.ai/blogs/midjourney-update-august-2025-video-loops-start-end-frames-and-api-access)); Extend ≈4 s × 4.
- SD/HD resolution; `--bs` batch size.

**UX:** hover-to-play; Explore Video tab; Rooms shut down 2026-02-26 ([Releasebot](https://releasebot.io/updates/midjourney)).

**Pricing:** $10–120 in GPU time; video ≈8× an image job.

**Privacy and provenance**
- Public on Explore unless **Stealth (Pro $60 / Mega $120 only)** ([S](https://www.eesel.ai/blog/midjourney-pricing)).
- Unsigned IPTC metadata only ([IPTC](https://iptc.org/news/midjourney-and-shutterstock-ai-sign-up-to-use-of-iptc-digital-source-type-for-generated-ai-content/)).

**Sentiment:** loved for its aesthetic and price; hated for low resolution and no audio.

### 8.13 ByteDance Dreamina / Seedance ([dreamina.capcut.com](https://dreamina.capcut.com/))

**Models**
- Seedance 1.5 Pro (2025-12-16): audio.
- **2.0 (2026-02):** 9 images / 3 videos / 3 audio, 15 s multi-shot, stereo multi-track ([Seed](https://seed.bytedance.com/en/blog/official-launch-of-seedance-2-0)).
- **2.5 (2026-07-31):** 30 s single pass, up to 50 references, timestamp-level editing, 3D blockout camera ([Seed](https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5)). Resolution is disputed [UNVERIFIED].

**UX**
- Model dropdown → mode (Omni reference / First-Last) → "+" add files → **auto-labelled `@Image1…` with @ autocomplete** ([vicsee](https://vicsee.com/blog/seedance-2-0-omni-reference)).
- Cost shown before generating.
- **Post-generation panel:** upscale, 60 fps interpolation, soundtrack ([guide](https://dreamina.capcut.com/seedance/how-to-use-seedance-2-0-mini)).
- **"Queue-FREE creation"** ([pricing](https://dreamina.capcut.com/seedance/seedance-2-0-pricing)).

**Pricing**
- Promo $5 / $11 / $42 per month (≈$0.05–0.08/s).
- API (BytePlus ModelArk) $0.04–0.78/s by tier and resolution [S].

**Sentiment**
- Loved for omni-reference and price.
- **Hated for aggressive face blocking** ([Efficienist](https://efficienist.com/users-are-unhappy-with-dreamina-seedance-2-0s-censorship-and-pricing/)); copyright backlash from Disney and the MPA.

### 8.14 LTX Studio ([ltx.io/studio](https://ltx.io/studio))

**Structure:** Project → Gen Space (Sessions) → Storyboard → Timeline → Pitch Deck; plus Canvas and Flows ([blog](https://ltx.io/blog/top-ltx-studio-features)).

**Storyboard flow** ([storyboard](https://ltx.io/studio/platform/ai-storyboard-generator)):
1. Paste an idea or a whole script.
2. Elements are extracted automatically.
3. The script is broken into scenes and shots.
4. Frame cards are generated.
5. Edit at project, board or frame level.

**Features**
- **Elements** (characters with voices, locations, objects, styles, logos, fonts) tagged with `@`.
- **Retake** a 2–16 s range ([blog](https://ltx.io/blog/retake-ai-directing-tool-ltx-studio)).
- Extend 4–12 s per step, up to 60 s ([blog](https://ltx.io/blog/how-to-extend-ai-videos)).
- Audio-to-video lip-sync; Motion Control; pose/depth/edge V2V; Topaz 4K/8K; SDR→HDR.
- Camera presets.
- Timeline with transitions and blend modes; export MP4, XML or PDF pitch deck.

**Pricing** ([pricing](https://ltx.io/studio/pricing))
- Free: 800 credits once.
- Lite $15 (8k), Standard $35 (28k; adds commercial license), Pro $125 (110k).
- Enterprise: no training on your data.

**Sentiment**
- G2 4.4, but **Trustpilot 1.6/5** ([Trustpilot](https://www.trustpilot.com/review/ltx.studio)): credit burn ("$140 just trying to produce a basic 10 sec video"), a confusing UI, "slideshows with voiceover".

**Landing page:** "The AI platform for video production", with "Choose your starting point" tiles.

### 8.15 OpenAI Sora app (closed)

**Timeline:** closure announced 2026-03-24; app and web closed **2026-04-26**; API ends **2026-09-24** with no replacement ([OpenAI deprecations](https://developers.openai.com/api/docs/deprecations), [The Decoder](https://the-decoder.com/openai-sets-two-stage-sora-shutdown-with-app-closing-april-2026-and-api-following-in-september/)).

**Why it closed:** OpenAI said it was moving compute to other priorities. Reported: about $1M/day in costs [UNVERIFIED], downloads collapsing, and the Disney deal falling through ([TechCrunch](https://techcrunch.com/2026/03/24/openais-sora-was-the-creepiest-app-on-your-phone-now-its-shutting-down/)).

**What users loved**
- **Cameos** of yourself and friends, gated by consent: Only me / Approved / Mutuals / Everyone. You could see and delete every video that used your likeness.
- Remix, and remix leaderboards.
- Physics and audio.
- Storyboard and Stitch ([TechCrunch](https://techcrunch.com/2025/10/23/sora-update-to-bring-ai-videos-of-your-pets-new-social-features-and-soon-an-android-version)).

**What users hated:** "slop", deepfakes of dead public figures, over-blocking even of public-domain characters ([404 Media](https://www.404media.co/sora-2-content-violation-guardrails-error/)), and free quota cut to 6 per day.

**Provenance:** C2PA plus a **visible moving watermark that included the creator's name**. It was easily removed ([No Film School](https://nofilmschool.com/sora-2-watermarks)).

**API:** it had **webhooks** (`video.completed` / `video.failed`) ([guide](https://developers.openai.com/api/docs/guides/video-generation)).

**Lessons for Kino:** copy the consent model and webhooks. Don't build an AI-only social feed as the core business.

### 8.16 CapCut (with Seedance)

**Generation in the editor**
- Seedance 2.0 in CapCut from 2026-03-26, in limited markets, with real faces blocked ([TechCrunch](https://techcrunch.com/2026/03/26/bytedances-new-ai-video-generation-model-dreamina-seedance-2-0-comes-to-capcut/)).
- **Seedance 2.5 in the editor (global 2026-07-31):** up to 50 references, 4K, 30 s (180 s beta), "Intelligent Edit Mode", and **clips land directly on the timeline** ([CapCut](https://www.capcut.com/features/seedance-2-5-for-video-editor)).

**Post-production features worth borrowing**
- Auto captions (130+ languages), speaker ID ([bibigpt](https://bibigpt.co/en/features/capcut-2026-ai-suite-explained)).
- Transcript editing and filler-word removal ([CapCut](https://www.capcut.com/resource/edit-video-with-text)).
- Auto Cut / beat sync ([help](https://www.capcut.com/help/auto-cut-in-capcut)); auto-reframe.
- TTS voices; long → short clips; publish direct to TikTok.

---

## 9. Key source index (selection)

**Privacy and provenance references**
- Venice E2EE: https://venice.ai/blog/venice-launches-end-to-end-encrypted-ai
- Tinfoil: https://tinfoil.sh/
- Privatemode: https://www.privatemode.ai/
- Apple PCC: https://security.apple.com/blog/private-cloud-compute/
- NEAR AI verification: https://docs.near.ai/cloud/verification/
- C2PA icon: https://c2pa.org/introducing-official-content-credentials-icon/
- Adobe CA app design: https://adobe.design/ideas/behind-the-design-adobe-content-authenticity-app
- Leica/CAI: https://contentauthenticity.org/blog/leica-launches-worlds-first-camera-with-content-credentials
- SynthID Detector: https://blog.google/innovation-and-ai/products/google-synthid-ai-content-detector/
- Platform AI labels: https://billo.app/blog/ai-labeling/

**Data-use terms**
- Runway: https://runway.com/terms-of-use
- Kling: https://kling.ai/docs/user-policy
- Midjourney Stealth: https://docs.midjourney.com/hc/en-us/articles/32019750070669-Stealth-Mode (403 on fetch; via search)

**Model specs**
- H3: https://huggingface.co/MiniMaxAI/MiniMax-H3 · https://platform.minimax.io/docs/guides/video-generation · https://www.minimax.io/blog/minimax-h3
- LTX-2.5: https://huggingface.co/Lightricks/LTX-2.5 · https://docs.ltx.io/models/ltx-2-5 · https://github.com/Lightricks/LTX-2 · https://ltx.io/llm-info

**Platform changelogs**
- Runway: https://runway.com/changelog
- Krea: https://www.krea.ai/docs/changelog
- Luma: https://lumalabs.ai/changelog
- LTX: https://ltx.io/release-notes
- Flow: https://blog.google/innovation-and-ai/models-and-research/google-labs/flow-updates-february-2026/
