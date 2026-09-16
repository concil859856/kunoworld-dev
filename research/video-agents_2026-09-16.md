# Video agents: what the big platforms ship, and what KunoWorld should add

Research date: 2026-09-16. Web sources were fetched on this date unless a fact carries an older date.

**Method.** Five research passes ran in parallel, one per group of platforms, followed by direct spot checks of the
claims the recommendations depend on. Those checks re-fetched the Flow Agent help page, the Runway Agent launch post,
the fal Agent docs, Gemini API webhooks, the HeyGen MCP docs, the Kling MCP blog, the Krea Agent blog, the OpenArt
Director page and Adobe's 2026-06-18 release.
- **Search limit:** the session's web-search budget (200 calls) ran out partway through four of the passes. Later facts
  in those passes come from fetching known official URLs directly, so some rows are thinner.
- **Blocked pages** (403, Cloudflare or JavaScript-only): help.openai.com, openai.com, the Runway help centre, Midjourney
  docs, the Moonvalley help centre, magnific.com, genspark.ai, the Canva newsroom, docs.byteplus.com, wan.video, and the
  Krea and Higgsfield pricing pages. Facts about these come from search snippets or press and say so.

Related notes in this folder:
- `research_platforms.md` (2026-09-11): the general feature and UX survey. This note corrects parts of it; see below.
- `long-video_ltx-av-extend_2026-09-16.md`: our chained LTX-2.5 storyboard test.
- `research_models.md`: H3 and LTX-2.5 specs and licences.

**Legend**
- **[C]** = [CONFIRMED]: a primary source (vendor page, docs, official blog, changelog, help centre, official GitHub,
  official app-store listing, vendor press release).
- **[C\*]** = official wording seen only as a search snippet, because the page blocked fetching.
- **[S]** = [SECONDARY]: press, reviews, resellers, third-party guides.
- **[U]** = [UNVERIFIED]: could not be confirmed, conflicting, or an absence we could not prove.

---

## 0. Corrections to `research_platforms.md` (2026-09-11)

| 09-11 note said | Status on 09-16 |
|---|---|
| Google's video API is poll-only, with no webhooks | **Wrong now.** The Gemini API has webhooks with a `video.generated` event (docs updated 2026-09-02) [C] ([docs](https://ai.google.dev/gemini-api/docs/webhooks)) |
| Runway has a "Task Cost API" | No such endpoint. Tasks return an `estimatedCost` field [C] ([API](https://docs.dev.runwayml.com/api.md)) |
| Runway Workflows publish as workspace "Apps" | Not confirmed. Apps are use-case templates (changelog 2025-10-14) [C] |
| MiniMax Video Agent: templates → semi-custom → autonomous | That roadmap dates from **2025-06-20**. The product became "Media Agent" on 2025-10-28. MiniMax's 2026 agent product is Hub, now "MiniMax Design" [C] |
| H3 Max is a larger H3 | It is a **speed-tuned H3 post-trained by fal**, at 480p/768p [C] ([fal](https://blog.fal.ai/introducing-h3-max-by-fal/), [MiniMax docs](https://platform.minimax.io/docs/guides/video-generation)) |
| Freepik → Magnific rebrand on 2026-04-28 [S] | Now [C] ([PR Newswire](https://www.prnewswire.com/news-releases/freepik-becomes-magnific-hits-230m-arr-and-introduces-the-no-collar-creative-economy-302755376.html)) |
| LTX API has docs `llms.txt`; poll-only | Both confirmed. Its MCP server only searches docs (`searchDocs`); there is no generation MCP [C] |
| Moonvalley listed as a competitor | Moonvalley merged into Reka on 2026-06-09 [C] ([Reka](https://reka.ai/news/reka-and-moonvalley-join-forces-to-advance-models-and-infrastructure-for-physical-ai)) |
| MiniMax Music API | No new users from 2026-08-20; Music models marked discontinued [C] ([pricing](https://platform.minimax.io/docs/guides/pricing-paygo)) |
| "Veo 4" | Does not exist. Only SEO and reseller sites mention it. Google's newest video model is Gemini Omni Flash [C] |

---

## 1. Summary

In September 2026, a "video agent" on the major platforms is a chat layer over a catalogue of models. It turns a brief
into a plan (concept, script, storyboard or shot list), picks a model for each shot, and renders 5-30 s multi-shot
clips. It then assembles them on a timeline with voiceover, music and captions, and lets you revise by chat.

**Who ships one:**
- **Generally available or public beta:**
  - Runway Agent (2026-05-13)
  - Google Flow Agent (2026-05-19)
  - Luma Agents (2026-03)
  - Higgsfield Supercomputer (2026-05)
  - OpenArt Director (2026-06)
  - Magnific Agents (2026-06)
  - Krea Agent (2026-09-08)
  - InVideo Agent Two (2026-07-29)
  - HeyGen Video Agent
  - MiniMax Media Agent and MiniMax Design
  - Adobe Firefly AI Assistant (public beta)
- **Early access:** fal Agent (2026-08-12).
- **Closed beta or invite-only:** ByteDance's Octo and Pika's Director's Suite.
- **No chat agent:** Kling and LTX Studio.
- **Gone:** OpenAI closed the Sora app on 2026-04-26 and removes the Sora API on 2026-09-24.

**Length.** The per-generation ceiling is now a 30 s single pass: Seedance 2.5, Wan 3.0 and Higgsfield Cinema Studio
4.0. Anything longer is assembled:
- by extension: Veo to 148 s, Omni Flash to 40 s;
- on timelines: LTX Studio to 60 s, CapCut's Long Video Mode beta to 180 s;
- by agents: OpenArt up to 5 min, Higgsfield Faceless Video up to 15 min, InVideo up to 30 min.

**Consistency** comes from reusable "Elements": characters, products and locations, often with a bound voice. Kling,
Krea, Higgsfield, LTX Studio, fal and Adobe (private beta) have them, and Flow has `@` characters.

**The agent-facing side standardised within months.** The common pattern is a remote OAuth MCP server billed to plan
credits, plus `npx skills add` skill packs, a CLI and `llms.txt`. Runway, Kling, Higgsfield, Krea, Magnific, OpenArt,
HeyGen, Pika, fal, Replicate, Descript, OpusClip and Canva all offer the MCP server.
- Only HeyGen exposes its multi-turn agent itself over MCP and API.
- Only fal exposes a price-estimate API.
- Runway, LTX and Luma's Agents API are still poll-only.

**Privacy.** Nobody processes privately. Every agent sends briefs, faces and voices in plaintext to the vendor's LLM and
often to third-party models. The best on offer is a no-training promise or a zero-retention flag (Adobe, Google's paid
API, Krea Enterprise, HeyGen Enterprise).

**What this means for KunoWorld.** The dominant architecture routes plaintext through outside LLMs and model vendors,
which KunoWorld cannot copy. Its opening is a plan-first agent whose planner, renderer and receipt all live inside the
enclave.

---

## 2. Per-platform tables

Columns:
- **Agent**: agent or assistant features.
- **Length**: how multi-shot and long-form video is made, and the maximum length.
- **Consistency**: tools for characters, products, locations and voices.
- **Edit/post**: editing and post-production.
- **Agent-facing**: API, MCP, SDK, skills, `llms.txt`, webhooks.
- **Pricing**: where visible.

Sources are linked inside each cell. Section 5 lists them again by platform.

### 2a. Big labs and model makers

| Platform | Agent | Length | Consistency | Edit/post | Agent-facing | Pricing |
|---|---|---|---|---|---|---|
| **Google** (Flow, Veo 3.1, Gemini Omni Flash, Vids) | **Flow Agent** (announced at I/O 2026-05-19, all Flow users, web/PC only) [C] ([blog](https://blog.google/innovation-and-ai/models-and-research/google-labs/flow-updates/)). It outlines storyboards and mood boards, turns concepts into prompts, generates video and images "and select[s] the best model", edits selected media, makes batch variations, and renames and groups assets. Chat queries are free under a daily quota; the media it makes costs Flow credits [C] ([help](https://support.google.com/flow/answer/17093911?hl=en)). **Gemini Omni Flash** (2026-05-20): edit video by chat (swap characters, relight, change the background) in the Gemini app, Flow, YouTube Shorts Remix and YouTube Create [C] ([blog](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-omni/)). **Google Vids** "Help me create": prompt → draft video with a script and AI voiceover per scene [C] ([Workspace](https://workspaceupdates.googleblog.com/2025/03/new-capabilities-for-google-vids-help-me-create.html)). Spark (general agent, US Ultra beta) has no video features [C] | Veo 3.1: 4/6/8 s clips, extend +7 s up to 20 times = 148 s, 720p only; Lite cannot extend [C] ([API](https://ai.google.dev/gemini-api/docs/veo)). Omni 1.1 Flash (GA 2026-08-27): ≤10 s per generation, extendable to 40 s, extension reads up to 10 s of earlier footage [C] ([API](https://ai.google.dev/gemini-api/docs/omni)). Scenebuilder arranges, trims and extends [C] ([help](https://support.google.com/flow/answer/16935718?hl=en)) | Up to 3 reference images (Ingredients); reusable `@` characters; `@me` avatar; voice references on Ingredient generations (30 voices, experimental, Ultra) [C] ([help](https://support.google.com/flow/answer/16353334?hl=en)). Omni personal avatars ("only you can use your avatar"); in Vids from 2026-07-16, English, not in EEA/CH/UK [C] ([Workspace](https://workspaceupdates.googleblog.com/2026/07/cast-yourself-in-ai-video-clips-using-your-personal-avatar-with-Gemini-Omni-in-Vids.html)) | Lasso edits in natural language, insert/remove objects, camera motion (2026-02-25) [C]. Start/end frames, 1080p/4K export, 360p drafts (2026-08-27) [C] ([blog](https://blog.google/innovation-and-ai/models-and-research/google-labs/new-creative-controls-google-flow/)). Omni API: stateful chat edits via `previous_interaction_id`; cannot edit voices; editing uploaded video is blocked in EEA/CH/UK [C]. Vids: Lyria 3 music, 30 s-3 min [C] | Gemini API for Veo and Omni. **Webhooks** (`video.generated`, Standard Webhooks or JWT signatures) [C] ([docs](https://ai.google.dev/gemini-api/docs/webhooks)). `llms.txt` [C]. Outputs kept 2 days [C]. Vertex remote MCP GA 2026-06-30 has no dedicated video tool [C] ([blog](https://cloud.google.com/blog/products/ai-machine-learning/gemini-enterprise-agent-platform-remote-mcp-server/)). `mcp-genmedia` (local; Veo, Lyria, TTS, FFmpeg AVTool; producer / video-editor / story skills) is "not an officially supported Google product" [C] ([GitHub](https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio/tree/main/experiments/mcp-genmedia)) | Veo 3.1: $0.40/s; Fast $0.10-0.12/s (720p/1080p); Lite $0.05-0.08/s. Omni 1.1 Flash ≈$0.10/s at 720p [C] ([pricing](https://ai.google.dev/gemini-api/docs/pricing)). Flow: 50 free credits/day; Veo Fast 20 credits, Quality 100 [C] ([help](https://support.google.com/flow/answer/16526234?hl=en)). The paid API tier does not use prompts for training [C] ([terms](https://ai.google.dev/gemini-api/terms)) |
| **OpenAI** (Sora 2) | **No current product.** Sora app and web closed 2026-04-26 [S] ([The Decoder](https://the-decoder.com/openai-sets-two-stage-sora-shutdown-with-app-closing-april-2026-and-api-following-in-september/)). Videos API and all `sora-2*` models are removed 2026-09-24 with no replacement listed [C] ([deprecations](https://developers.openai.com/api/docs/deprecations)). No official sign that ChatGPT makes video; a "Spud" successor appears only on SEO sites [U]. Before closure the app had storyboards (web, Pro, 2025-10-15) [C] ([@OpenAI](https://x.com/OpenAI/status/1978661828419822066)), character cameos, stitching and leaderboards (2025-10-29) [S] ([MacRumors](https://www.macrumors.com/2025/10/30/openai-sora-app-character-cameos-video-stitching/)), and remix [S] | App: 15 s for all users, 25 s for Pro on web [C]. API: 16 or 20 s clips, extended up to 6 times to **120 s** [C] ([guide](https://developers.openai.com/api/docs/guides/video-generation)) | Cameo consent levels: Only me / People I approve / Mutuals / Everyone [S] ([Engadget](https://www.engadget.com/ai/openais-character-cameos-will-let-you-put-pets-and-original-personas-in-sora-videos-123043189.html)). API characters are **non-human only**, from 2-4 s clips, at most 2 per video; human faces rejected [C] | `POST /v1/videos/edits` replaced `/remix` (2026-03-12) [C] ([changelog](https://developers.openai.com/api/docs/changelog)) | API with webhooks (`video.completed`, `video.failed`); not usable with zero data retention [C] ([your data](https://developers.openai.com/api/docs/guides/your-data)) | sora-2 $0.10/s (720p); sora-2-pro $0.30-0.70/s [C] ([model](https://developers.openai.com/api/docs/models/sora-2-pro)) |
| **Meta** (Vibes, Meta AI, Muse Video) | No video agent. **Vibes** feed (2025-09-25): create, or remix feed videos with new visuals, music and styles; cross-post to Instagram and Facebook [C] ([Meta](https://about.fb.com/news/2025/09/introducing-vibes-ai-videos/)). Standalone Vibes app tested in Brazil and Mexico (2026-02-04) [S] ([Social Media Today](https://www.socialmediatoday.com/news/metas-testing-a-standalone-ai-video-app/811380/)). Meta AI app: prompt a video, refine over several turns [C] ([App Store](https://apps.apple.com/us/app/meta-ai/id1558240027)). **Muse Video** (2026-07-07) is an "early preview", "coming soon": announced, not shipped [C] ([Meta AI](https://ai.meta.com/blog/introducing-muse-image-muse-video-msl/)). Muse personal agent (2026-09-08) has no video features [C] | Extend "up to 21 seconds" in the Meta AI app [C] | None found | Edits app: AI animation of images, auto captions, green screen [C] ([App Store](https://apps.apple.com/us/app/edits-an-instagram-app/id6738967378)) | No video API or MCP found. The Meta Model API preview (2026-07-09) does not mention video [C] ([blog](https://ai.meta.com/blog/introducing-muse-spark-meta-model-api/)) | Meta One (2026-09-15): bundles from $7.99; includes "more media generation … generating videos"; limits not stated [C] ([Meta](https://about.fb.com/news/2026/09/introducing-meta-one-subscription-service-more-features-ai/)) |
| **Adobe** (Firefly) | **Firefly AI Assistant**, formerly Project Moonlight. Announced 2026-04-15; public beta 2026-04-27 [C] ([blog](https://blog.adobe.com/en/publish/2026/04/27/firefly-ai-assistant-public-beta)). It plans and runs multi-step work across Firefly, Photoshop, Premiere, Express and more, using "creative skills" [C] ([blog](https://blog.adobe.com/en/publish/2026/04/15/introducing-firefly-ai-assistant-new-way-create-with-our-creative-agent)). 2026-06-18 skills (beta): storyboards, **video from storyboards**, Quick Cut (auto first cut), product videos [C] ([Adobe](https://news.adobe.com/news/2026/06/adobe-unveils-major-expansion)). Free tier with daily limits, and Omni Flash added, on 2026-08-20 [C] | Firefly plans count output in 5 s videos [C] ([plans](https://www.adobe.com/products/firefly/plans.html)). 30+ partner models (Veo 3.1, Kling 3.0, Runway Gen-4.5, Luma Ray3, Omni Flash) [C] ([partners](https://www.adobe.com/products/firefly/partner-models.html)). Premiere Generative Extend: up to 2 s of video or 10 s of audio [S] | **Elements** (save characters, locations, objects) in the "creative AI studio", **private beta / waitlist** [C]. Custom models, public beta 2026-03-19 [C] | Browser Firefly Video Editor: multi-track timeline, transcript editing, Quick Cut [C]. Generate Music, Speech (ElevenLabs option) and Sound Effects GA 2026-08-20 [C] ([blog](https://blog.adobe.com/en/publish/2026/08/20/adobe-firefly-expands-its-creative-ai-studio-generate-music-speech-and-sound-effects-in-one-place)). Translate Video in 20+ languages; lip-sync for enterprise only [S] | "Adobe for creativity" Claude connector (2026-04-28; MCP `adobe-creativity.adobe.io/mcp`; 50+ tools, video resize and trim, no generation) [C] ([Claude](https://claude.com/connectors/adobe-creativity)). Adobe for ChatGPT (2026-08-06; 70+ tools; long video → highlight reel) [C]. Firefly Services APIs (Generate Video, Translate & Lip Sync, Reframe, Avatar) [C]; enterprise contract needed [S]. `llms.txt` returns 404 [C] | Standard $9.99 (2,000 credits ≈ 20 × 5 s videos), Pro $19.99, Pro Plus $49.99, Premium $199.99 [C]. "Never trained Adobe Firefly on user content"; IP indemnity for Firefly models (enterprise) [C] ([approach](https://www.adobe.com/ai/overview/firefly/gen-ai-approach.html)) |
| **xAI** (Grok Imagine) | No agent found [U] | Grok Imagine Video 1.5 API: 1-15 s, 480p/720p/1080p; first/last frame; extension continues from the last frame [C] ([docs](https://docs.x.ai/developers/model-capabilities/video/generation)). 1.5 launch date 2026-05-31 [S] | References (2026-07-31): up to **7 reference images** ("a face, a product, a location") and **voice references** paired with characters, on grok.com/imagine and iOS. API has image references now; voice references on request [C] ([xAI](https://x.ai/news/grok-imagine-video-1-5-references)) | Video editing (output capped at 720p); native audio with up to 3 preset voices [C] | API launched 2026-01-28 [C] ([xAI](https://x.ai/news/grok-imagine-api)); polling only, no webhooks documented [C] | ≈$0.05/s at 720p [S] ([imagine.art](https://www.imagine.art/blogs/xai-grok-imagine-video-1-5-guide)) |

### 2b. Creative video studios

| Platform | Agent | Length | Consistency | Edit/post | Agent-facing | Pricing |
|---|---|---|---|---|---|---|
| **Runway** | **Runway Agent** (2026-05-13, available immediately) [C] ([news](https://runway.com/news/introducing-runway-agent)). You describe a concept and add references, aspect ratio, duration and audio settings. The agent proposes a concept and story structure, you refine by chat, and it generates a full multi-shot video with voiceover, dialogue and music, then hands it to a timeline. **Agent 2.0** (2026-06-25, marketing): imports ad metrics from Meta, YouTube, TikTok and Google; makes variants, week-long batches and localized versions in 9:16, 16:9 and 1:1 [C] ([news](https://runway.com/news/introducing-agent-2)). Picks models (Gen-4.5, Aleph 2.0, Seedance 2.5, Kling 3.0 Pro, Nano Banana Pro) or uses yours [C] ([product](https://runway.com/product/agent)). **Skills** (2026-07-02): called with "/"; the agent can turn a conversation into a custom Skill and share it with the workspace [C\*]. Timeline inside Agent from 07-09 [C] ([changelog](https://runway.com/changelog)). LLM not disclosed [C] | Gen-4.5 2-10 s; Seedance 2.5 4-30 s (2026-08-07) and Wan 3.0 ≤30 s via API [C] ([API changelog](https://docs.dev.runwayml.com/api-details/api_changelog/)). Aleph 2.0 edits clips ≤30 s, carrying an edit across cuts [C]. No overall agent maximum published [U] | Brand kits (1 Pro, 3 Max); custom voice clones (1 Pro, 3 Max) [C] ([pricing](https://runway.com/pricing)). Agent uses "your brand context" [C] | Studio editor (06-18) [C]. Aleph 2.0: swap products or characters, replace backgrounds, remove objects [C] ([news](https://runway.com/news/introducing-aleph-2-and-edit-studio)). Act-Two performance capture. API: ElevenLabs dubbing (29 languages), Eleven v3 TTS, Magnific upscaler, Ruby SDR→HDR [C]. Premiere and After Effects plugins (2026-09-08) [C] | Consumer remote MCP: OAuth, plan credits, Pro and up; ChatGPT, Claude, Cursor, Replit [C] ([MCP](https://runway.com/mcp)); launch ≈2026-05-27 [S]. Dev MCP `dev.runwayml.com/mcp` (2026-09-02) [C]. Open-source local MCP (MIT) [C] ([GitHub](https://github.com/runwayml/runway-api-mcp-server)). REST API (58 operations), SDKs, `/v1/workflows`, Model Router with credit ceilings (2026-07-23), `runwayml/skills` (MIT) [C]. `llms.txt`, `llms-full.txt`, `ai-context.md` [C] ([ai-context](https://docs.dev.runwayml.com/ai-context.md)). **Poll only**, no webhooks; `estimatedCost` on tasks [C] | Free 125 credits once; Standard $15 (625), Pro $35 (2,250), Max $95 (9,500). Agent runs on plan credits [C]. API credit = $0.01: Gen-4.5 12 cr/s, Seedance 2.5 at 1080p 68 cr/s, `h3_max` at 480p 5 cr/s [C] ([pricing](https://docs.dev.runwayml.com/guides/pricing.md)) |
| **Luma** | **Luma Agents** launched 2026-03-05 on the Uni-1 model [S] ([TechCrunch](https://techcrunch.com/2026/03/05/exclusive-luma-launches-creative-ai-agents-powered-by-its-new-unified-intelligence-models/)). Luma App: Brainstorm Mode (ideas only) and Create Mode (generates; picks models automatically or manually). Infinite boards; the agent explores several directions in parallel with shared context; shared canvases with roles [C] ([app](https://lumalabs.ai/app)). Models include Ray3.2, Uni-1, Veo 3.1, Kling 3.0, Seedance 2.0 and ElevenLabs music/SFX [C]. Layers (2026-07-29): images split into layers and edited by chat [C] | Ray3.2 (2026-06-09): "up to 16 keyframes within a single clip", 1080p HDR/EXR [C] ([news](https://lumalabs.ai/news/introducing-ray-3-2)); the API page says 64 anchors [conflict]. API: 5 or 10 s generations, extend ≤30 s, edits ≤18 s [C] ([FAQ](https://docs.agents.lumalabs.ai/guides/faq/)). Episode boards and story arcs in the App; no agent maximum stated [U] | "Master Reference Assets" for characters, products, logos [C]. Uni-1.1 takes ≤9 references [C] ([llm-info](https://lumalabs.ai/llm-info)) | App: captions, localization with voiceover, lip-sync, reframe, extend [C]. Modify Video V2 ≤20 s at 1080p [C]. Ray has no native audio [C] | Agents API: one `POST /v1/generations`; Python, TypeScript and Go SDKs; CLI [C] ([docs](https://docs.agents.lumalabs.ai/)). Poll only. Agents docs `llms.txt` returns 404 (legacy docs have one) [C]. Only official MCP is a legacy local server for Ray-2 [C] ([GitHub](https://github.com/lumalabs/luma-api-mcp)) | Plus $30 (10k credits), Pro $90 (40k, 4× agent usage), Ultra $300 (150k, 15×) [C] ([pricing](https://lumalabs.ai/pricing)). API Ray3.2: $0.15 (540p, 5 s) to $3.60 (1080p, 10 s) [C] ([API](https://lumalabs.ai/api)) |
| **Kling** (Kuaishou) | **No chat or storyboard agent found** [U]. "AI Director" marketing refers to multi-shot inside one generation. The agentic surface is Kling MCP, CLI and Skills, which let outside agents drive Kling. Kuaishou's Q2 report says they launched for batch creation by AI agents [C] ([Q2 results](https://www.prnewswire.com/news-releases/kuaishou-technology-announces-second-quarter-and-interim-2026-unaudited-financial-results-302855081.html)) | Kling 3.0 / 3.0 Omni (2026-02-05): 3-15 s, **up to 6 cuts** per generation with per-shot prompt and duration [C] ([blog](https://kling.ai/blog/kling-3-subject-binding-character-consistency), [llms.txt](https://kling.ai/llms.txt)). 3.0 Turbo and Omni editing upgrade in Q2 (2026-06-17 [S]); native 4K [C] | **Elements** from ≤4 multi-angle images, or a 3-8 s video capturing appearance, motion and voice. **Voice binding** from 5-30 s of audio. 30-500 Element slots by plan. Motion library [C] ([blog](https://kling.ai/blog/kling-video-3-omni-native-lip-sync-audio-guide)) | Native lip-synced dialogue, with different languages per character in one scene; lip-sync tool for existing video; Motion Control; Omni editing up to 4K [C/S] | **Remote MCP** `kling.ai/mcp`: OAuth, paid credits from the Personal workspace, blog 2026-08-27 [C] ([blog](https://kling.ai/blog/claude-code-kling-mcp-food-promo-workflow)). CLI plus skill `npx skills add klingai-tech/skills`: 19 commands including element create/list and motion control; no separate multi-shot or lip-sync command [C] ([SKILL.md](https://raw.githubusercontent.com/klingai-tech/skills/main/SKILL.md)). REST API with `llms.txt` [C]; `callback_url` [S] | Standard $6.99 first month, $8.80 after (660 credits); Ultra $127.99 / $159.99 (26,000). API 3.0: $0.084/s (standard, no audio) to $0.168/s (pro, with audio) [C] ([llms.txt](https://kling.ai/llms.txt)) |
| **MiniMax** (Hailuo, H3) | **Hailuo Video Agent** beta (2025-06-20): 8 templates, reasoning shown live [C] ([news](https://www.minimax.io/news/video-agent)). Became **Media Agent** (2025-10-28): one-click generation that picks models, plus a pro step-by-step mode [C] ([news](https://www.minimax.io/news/minimax-hailuo-23)). **MiniMax Hub** (2026-06-15): reads a brief, PDF, reference video or asset pack; splits the work into tasks, selects models, checks quality, and **pauses at key decisions** [S] ([Variety via Yahoo](https://tech.yahoo.com/ai/articles/minimax-launches-one-ai-video-193031165.html)). Now **MiniMax Design**, a desktop app: four parallel agents (copy, image, video, audio) on a node canvas, a skills marketplace, and a "Local-First Asset Center" [C] ([hub](https://hub.minimax.io/)). MiniMax Agent added H3 in August 2026 [C] ([changelog](https://agent.minimax.io/docs/changelog)) | H3 (2026-07-31): 4-15 s, native multi-shot, 768p (2K only through the closed Regenerate API) [C] ([blog](https://www.minimax.io/blog/minimax-h3)). Agents assemble longer videos; no maximum stated [U] | H3 references: ≤9 images, ≤3 videos, ≤3 audio clips, carrying character, motion, camera, style and voice [C]. Voice clone and voice design [C] | TTS speech-2.8 [C]. Music API closed to new users from 2026-08-20 [C] | Official local MCP `MiniMax-AI/MiniMax-MCP` (`generate_video`, `query_video_generation`, TTS, voice clone/design, image). Last release notes 2025-07 name Hailuo-02, so it is stale for H3 [C] ([GitHub](https://github.com/MiniMax-AI/MiniMax-MCP)). `mmx-cli` with H3 and a skill install [C] ([GitHub](https://github.com/MiniMax-AI/cli)). `llms.txt` [C]. v2 API `callback_url` [C]. H3-Context-IR prompt compiler as its own task [C] | H3 $0.08/s (768p), $0.13/s (2K); H3-Max $0.05/s (480p), $0.08/s (768p) [C] ([pricing](https://platform.minimax.io/docs/guides/pricing-paygo)) |
| **ByteDance** (Seedance, Dreamina, Jimeng, CapCut) | **Octo**, the Dreamina/Jimeng creative agent (China 2026-04-09 [S]). A chat agent on one canvas: makes images and characters (Seedream 5.0), turns them into video (Seedance 2.0/2.5), lays clips on a timeline. **"Closed beta at no cost"** [C] ([Dreamina](https://dreamina.capcut.com/ai-video/ai-creative-agent)). Dreamina storyboard: script → up to 40 frames [C, SEO-style page]. **CapCut Video Studio** (2026-03-25): AI Screenwriter agent drafts the script, which is split into shot cards rendered with Seedance 2.0; select markets first [C] ([CapCut on X](https://x.com/capcutapp/status/2036943209956344181)); details [S]. BytePlus `ark-director`: an 8-stage pipeline (brief lock → reference preflight → dialogue audio → cheap prototype → review → final render → QA), described as "an internal workspace" [C] ([GitHub](https://github.com/byteplus-sa/ark-director)) | Seedance 2.0 (2026-02-12): 15 s multi-shot [C]. **Seedance 2.5** (2026-07-31): **30 s single pass** plus rounds of extension; multi-shot arcs [C] ([Seed](https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5)). CapCut Long Video Mode (beta) ≤180 s [C, SEO-style page] ([CapCut](https://www.capcut.com/features/seedance-2-5-for-video-editor)). Jimeng ≤3 min [S] | Seedance 2.5: 30 images, 10 videos, 10 audio clips (≤50 total); clay-render / textureless-3D references for layout, poses and camera [C] | Seedance 2.5 timestamp-level edits to audio and video; green screen [C]. CapCut "Intelligent Edit Mode" [C, SEO-style page]. CapCut auto captions and transcript editing (see 09-11 note) | BytePlus ModelArk API with Seedance 2.5 [C\*]. `byteplus-sa/ark-mcp` (Seedance tasks, speech-to-text, VOD subtitles); official support unclear [C] ([GitHub](https://github.com/byteplus-sa/ark-mcp)). No `llms.txt` found | Token-based API; ≈$1.16 for a 5 s 720p clip [S] ([CometAPI](https://www.cometapi.com/seedance-2-5-api-pricing/)). Invisible watermark, C2PA and visible labels; unauthorised real faces banned [C] ([Dreamina](https://dreamina.capcut.com/resource/seedance-2-5-launch)) |
| **Alibaba Wan** | No agent confirmed; wan.video is JavaScript-only [U]. Video in the Qwen app [U] | Wan2.7 (2026-04-03, API only): 2-15 s, multi-shot [C] ([docs](https://www.alibabacloud.com/help/en/model-studio/use-video-generation)). **Wan3.0-Video** (China, 2026-08-06): ≤30 s; faster Prime version 2026-08-20 [C] ([release notes](https://www.alibabacloud.com/help/en/model-studio/newly-released-models)). No weights beyond Wan 2.2 (plus Wan-Animate-2, Apache-2.0, 2026-08-07) [C] ([GitHub](https://github.com/Wan-Video)) | Wan2.7 R2V: ≤5 image/video references plus voice-timbre cloning. Wan 3.0: "production-grade character consistency" [C] | Wan2.7 VideoEdit (local and global edits by prompt) [C] | Model Studio async API. `Wan-skills` covers images and PPTX only; no video MCP found [C] ([GitHub](https://github.com/Wan-Video/Wan-skills)) | Wan 3.0 price not shown [U] |
| **Pika** | Pivoted to "Pika Experiments" (2026-05-26) [C] ([blog](https://experiment.pika.art/blog/pika-experiments)). **Pika Agent ("AI Self")**: a persistent agent with its own face, voice and memory. It makes video with Pika, Kling, MiniMax, Sora and Veo, and joins Slack, WhatsApp, iMessage and Zoom. Described as "intentionally rough around the edges" [C] ([page](https://experiment.pika.art/ai-self)). PikaStream real-time video chat (2026-04-02) [C]. **Director's Suite** is invite-only: concept → cast → storyboard → clips → sound [C] ([X](https://x.com/pika_labs/status/2074911533159858183/photo/1)); details [S] | Pikaframes up to 20-25 s [C] ([pricing](https://pika.art/pricing)). No agent maximum [U] | Persistent agent identity and memory [C] | MCP tools: extend, re-cut, modify, lip-sync, inpainting, face swap, TTS, voice cloning, music, auto-captions, stitching [C] ([MCP](https://experiment.pika.art/mcp)). Own audio models (2026-08-18) [C] | Experimental MCP (58 tools; the page says `experiment-mcp.pika.art`, the repo says `mcp.pika.me`) billed from the Agent Wallet, with skills (Explainer, Podcast, UGC Ads) [C]. **dev.pika.art**: multi-vendor API (includes H3) with 155 operations, micro-USD quotes, OpenAPI, signed webhooks and `llms.txt` [C] ([llms.txt](https://dev.pika.art/llms.txt)) | $8 / $28 / $76 per month billed yearly [C] |
| **Higgsfield** | **Supercomputer** (2026-05-13 [S]; 2.0 on 2026-06-19 [S]). A chat agent that splits a request into steps, picks a model per step and assembles the result. Skills: Product UGC, Faceless Video (≤15 min), Shorts Maker, TV Commercials, Localization. You choose the LLM or let it route; connectors to Slack, TikTok, Drive, Notion [C] ([help](https://higgsfield.ai/creator-hub/help-center/tools/how-do-i-use-supercomputer)). Guide flow: brief → character image → **cost preview → approval** → animation; a full job ≈200 credits (~$10) [C] ([guide](https://higgsfield.ai/blog/higgsfield-supercomputer-guide)). AI Employees and scheduled tasks [C] | Cinema Studio 4.0 (2026-08-12): ≤30 s per generation at 1080p, automatic montage cuts [C] ([blog](https://higgsfield.ai/blog/cinema-studio-4-0)); the landing page claims 1 min at 4K [conflict]. Popcorn storyboards of 8 frames [C]. Video via MCP ≤15 s [C] | Soul ID, AI Cast, Cinematic Locations, ≤50 references; `@` Elements inside Supercomputer [C] ([how built](https://higgsfield.ai/blog/how-we-built-supercomputer)) | TTS, voice change, lip-sync translation in 18 languages (2026-08-10); motion transfer and object swap (09-01); upscaler [C] ([changelog](https://higgsfield.ai/creator-hub/changelog)) | Remote MCP `mcp.higgsfield.ai/mcp` (account sign-in, subscription required) [C] ([help](https://higgsfield.ai/creator-hub/help-center/integrations/how-do-i-connect-higgsfield-to-ai-agent)). CLI plus skills; "unlimited" plans don't apply through MCP/CLI [C]. ChatGPT plugin [C]. Public REST API [U] | Starter $19 (270 credits), Plus $59 (1,200), Ultra $129 (3,000) [S] ([Blotato](https://www.blotato.com/blog/higgsfield-pricing)) |
| **Krea** | **Krea Agent** (blog 2026-09-08). Reads the brief, plans, picks from 150+ models, generates, reviews, edits, and files results. It has a private computer with FFmpeg, ImageMagick and Python for trimming, reframing and captions. Context library at session, personal and workspace level; LLM selectable [C] ([blog](https://www.krea.ai/blog/what-is-krea-agent)). Availability conflicts: the blog says beta on Max and above; the 2026-09-10 changelog says everyone, including Free [C] ([changelog](https://www.krea.ai/docs/changelog)). Runs on web, Slack, ChatGPT plugin and MCP [C]. Node Agent (2026-03-18): chat → a wired node pipeline with cost estimates [C] | Depends on the model [U]. Realtime Director (2026-09-07): steer live video with prompts [C]; runs on fal's H3 Max Director [S] | **Elements** (2026-09-09): up to 8 references per `@` tag for characters, locations and objects [C]. LoRA training [C] | Agent-side FFmpeg edits and captions [C]. Seedance Studio: camera, annotations, 3D camera [C] | Remote MCP `api.krea.ai/mcp` (OAuth or token): `list_models`, `get_model_schema`, `generate`, `execute_node_app`, `get_job`, `cancel_job`, `get_upload_url` [C] ([docs](https://www.krea.ai/docs/developers/mcp.md)). `llms.txt` [C]. Upfront cost estimates in the app (2026-09-07) [C] | Pro ≈$30; Max $105 (60k units) [C]; Free 100 units/day [S]. No separate agent bill [C]. **Enterprise API zero-retention header** (2026-06-16) [C] |
| **LTX Studio** (Lightricks) | **No chat agent found**; product updates run to 2026-08-11 [C] ([updates](https://ltx.io/blog-category/product-updates)). Storyboard Generator rebuilt 2026-01-06: upload a script or brief → Elements extracted automatically → scenes and shots → frames [C] ([blog](https://ltx.io/blog/ltx-storyboard-generator-update)). Then add motion, music and SFX, and export MP4 or a pitch deck [C] ([page](https://ltx.io/studio/platform/script-to-video)). Canvas (2026-04-20) and Flows node pipelines (2026-05-07) [C] | LTX-2.5 (2026-08-11): "Native Multishot", ≤20 s, auto duration, prompt enhancer [C] ([llm-info](https://ltx.io/llm-info)). Studio: Extend in 4-12 s steps to 60 s [C]; Retake a 2-16 s range [C]. API: Extend 2-20 s (≤505 frames) and Retake on `ltx-2-3-pro` only [C] ([docs](https://docs.ltx.io/api-documentation/api-reference/async-video-generation/submit-extend.md)) | Elements (characters, objects, locations) tied to voices [C\*]. Brand Kit is Enterprise-only [C\*] | Timeline; SDR→HDR, EXR, reframe, keyframes [C] | API V2 async, **poll only, no webhooks, no cost endpoint**; `llms.txt`; MCP only searches docs [C] ([llms.txt](https://docs.ltx.io/llms.txt)). LTX Desktop (Apache-2.0) [C] | API LTX-2.5 Fast $0.09-0.30/s, Pro $0.12-0.39/s; retake/extend $0.10/s [C] ([pricing](https://docs.ltx.io/pricing.md)). Studio Lite $15, Standard $35, Pro $125; Elements and AI storyboards from Standard [C] ([pricing](https://ltx.io/studio/pricing)) |
| **Magnific** (formerly Freepik) | **Agents + MCP + Flows** launched 2026-06-03 [C] ([X](https://x.com/magnific/status/2062304741842137144)). Starter agents: Magnific Agent, Ad Creator, Script Writer. Custom agents with knowledge bases and project memory, shareable [C\*] ([agents](https://www.magnific.com/agents)). Agents deliver an **editable Space (node workflow)**, not a flat file [C\*]. Flows turn a Space into a process runnable from any chat [C\*] | No maximum documented [U] | Trained characters (via MCP) [C\*] | Model-dependent | Remote MCP `mcp.magnific.com`: OAuth, 40+ tools (`video_generate`, TTS, character training) [C] ([docs](https://docs.magnific.com/modelcontextprotocol)). API with HMAC-signed webhooks and `llms.txt` [C]. No cost-quote endpoint; "unlimited" plans cover the web app only [C] | Credits (see 09-11 note) |
| **OpenArt** | **Director** (2026-06-21/23) [C] ([what's new](https://openart.ai/whats-new)). Describe the idea (optionally attach images, soundtrack, voice or video) → chat with "Ori" about characters, story, environment and scenes → watch and request changes by chat or in a structured editor [C] ([guide](https://openart.ai/blog/how-to-use-openart-director/)). "Powered by Seedance 2.0, GPT Image 2, and more" [C] ([page](https://openart.ai/features/director/)). Lite qualities "up to 50% cheaper" [C\*] | Multi-shot film **up to 5 minutes** [C]. Smart Shot: 10-20 s with 3-5 cuts [C\*] | Claims consistent faces, voices, environments and products; logos and fonts uploaded once [C]. Character Builder (2026-03-27) [C] | Video Dubbing (2026-08-27) [C] | Remote MCP `mcp.openart.ai/mcp` (OAuth, async); **Director is not exposed** [C] ([MCP](https://openart.ai/mcp/)). CLI [C]. No webhooks or `llms.txt` found [U] | Starter $14 (4,000 credits) to Wonder $240; Director on all plans [C] ([pricing](https://openart.ai/pricing)). **No published credit cost per Director minute** [S] ([Rundown](https://www.therundown.ai/tools/openart-director)) |
| **Moonvalley** (Marey) | None; merged into Reka 2026-06-09 [C] | 5 or 10 s at 1080p (on fal) [C] | Separate reference image per character [C] ([Marey](https://www.moonvalley.com/marey)) | Camera control, motion transfer, pose, trajectories, keyframes on a timeline, extension; no audio mentioned [C] | fal endpoint; direct API waitlisted [C] | ≈$0.30/s on fal [C] ([fal](https://fal.ai/models/moonvalley/marey/t2v)). "Trained only on licensed … footage" [C] |
| **Midjourney** | None. Still Video V1 (2025-06-18); 2026 releases were image models V8-V8.2 [C] ([updates](https://updates.midjourney.com/rss/)) | 4 × 5 s clips per job; extend ≈4 s up to 4 times (~21 s) [C] | None | Loop, end frame, HD 720p [C] | No public API [C] | GPU-time plans; pages blocked [U] |
| **Vidu** (Shengshu) | "Vidu Agent: from a single sentence to a complete work" [C] ([vidu.com](https://www.vidu.com/)). Steps, dates, pricing [U] | Vidu Q3: 16 s audio-video; "Smart Cuts" multi-shot [C] | Reference-to-video from 3+ images of a character, object or scene [C] | Templates, upscaling [C] | API (Q1-Q3, avatar, editing) [C] ([docs](https://platform.vidu.com/docs/introduction)); MCP [U] | [U] |

### 2c. Avatar, editor and general-purpose agents

| Platform | Agent | Length | Consistency | Edit/post | Agent-facing | Pricing |
|---|---|---|---|---|---|---|
| **HeyGen** | **Video Agent** (public September 2025) [C] ([release](https://www.heygen.com/blog/heygen-september-2025-release)). Prompt plus attachments → a **video plan you can revise for free** → generate on "Proceed". Chat Mode or Autopilot Mode; optional Brand System; "Incognito Mode" [C] ([help](https://help.heygen.com/en/articles/12402907-how-to-get-started-with-video-agent)). July 2026: HyperFrames motion graphics written as code; storyboard "director mode" that pitches 5 angles, then sketches keyframes for approval; website/Figma-to-video [C] ([release](https://www.heygen.com/blog/heygen-july-2026-release)). Standard mode or **Seedance mode** (Seedance 2.0 footage) [C] | **30 min single-pass avatar video** (July 2026) [C]. Plan caps: 30 min (Creator/Pro), 60 min (Business) [C] ([pricing](https://www.heygen.com/pricing)) | Avatar III/IV/V; Instant voice clone; Professional clone (private beta) [C] ([models](https://developers.heygen.com/models)) | Captions, music, voiceover, translation in 175+ languages, lip-sync batches, AI clipping [C] | **Remote MCP** `mcp.heygen.com/mcp/v1/` (OAuth, all plans, plan credits) with Video Agent tools `create_video_agent` and `send_video_agent_message` (follow-up edits in chat) [C] ([docs](https://developers.heygen.com/mcp/overview)). API v3, CLI, `llms.txt` with a "For AI Agents" section, skills, ChatGPT app, Claude connector, Stripe Projects [C]. HyperFrames renderer is open source (Apache-2.0) [C] ([GitHub](https://github.com/heygen-com/hyperframes)) | Creator $29 (600 credits), Pro $49, Business $149 [C]. Agent: Standard ≈30-40 credits/min, Seedance ≈90-120/min [C] ([FAQ](https://help.heygen.com/en/articles/16007192-video-agent-faq)). API Video Agent **$2/min** [C] ([API pricing](https://help.heygen.com/en/articles/10060327-heygen-api-pricing-explained)). Only Enterprise data is excluded from training by default [C] ([security](https://www.heygen.com/security)) |
| **Synthesia** | **Assistant** (2026-07-15): prompt plus files (PPT, PDF, DOC) or URLs → editable outline → scenes with script and visuals → changes by chat; no credits used [C] ([docs](https://docs.synthesia.io/docs/assistant)). "Video Agents" means real-time conversational avatars: Interactive Avatar API (2026-07-22) and Roleplay Sessions (2026-07-29) [C] ([page](https://www.synthesia.io/features/video-agents)) | Short/Medium/Long presets [C] | Personal avatars, Express-Voice cloning [C] | Dubbing 2.0 (2026-07-15): 70+ languages on self-serve, 140+ Enterprise; Veo 3 B-roll [C] ([pricing](https://www.synthesia.io/pricing)) | Video, Interactive Avatars and Dubbing APIs; `llms.txt` [C]. **No official MCP** (Zapier/community only) [C] | Starter $29, Creator $89 (API from here), Enterprise custom; interactive avatars $0.12/min [C]. SOC 2 Type II, ISO 42001 [C] |
| **InVideo AI** | v4 agent (2025-08-20) [C]. **Agent Two** (2026-07-29): "Agent Intelligence" with long-running project memory. A "Context" holds project-wide rules (characters, world, tone); "Briefs" are individual deliverables. Assignable expert roles (Creative Director, DOP, Storyboard Artist); Playbooks; multitrack timeline; multiplayer [C] ([Agent Two](https://invideo.io/agent-two/)). Uses Veo 3.1, Sora 2, Kling, Wan, Hailuo, Seedance, ElevenLabs [C] | "Up to 30 minutes from one prompt" (v4 agent) [C\*] | Context holds characters and locations; picks a model per shot [C\*] | Timeline, stock (16M assets), voiceover, music [C] | MCP page with no endpoint or tool list [C] ([MCP](https://invideo.io/ai/mcp/)). ChatGPT app [C\*]. No public API [U] | Starter $20/seat (Agent Two Lite), Plus $60, Max $150, billed annually; credits don't roll over [C] ([pricing](https://invideo.io/pricing)) |
| **Captions / Mirage** | Company renamed Mirage (2025-09-04) [C]. "Captions is Mirage Agent in your hands": plans, creates, edits and designs; performance, cuts, graphics and score stay editable [C] ([mirage.app](https://mirage.app/)) | [U] | AI twins/avatars; outfit, background and product swaps [C] | Chat editor, auto cuts, B-roll, translation and subtitles in 100+ languages [C] ([overview](https://captions.ai/overview)) | API (AI Ads endpoint); `llms.txt`; no MCP found [C/U] | Max $24.99 … Scale 8x $279.99. "Training data exclusion" is an **Enterprise feature** [C] ([pricing](https://captions.ai/pricing)) |
| **Genspark** | AI Video agent across Kling, Veo, Sora, Runway, Hailuo, Vidu and Seedance, routing each prompt to a model automatically; AI Storyboard Generator [C\*] ([agents](https://www.genspark.ai/agents?type=video_generation_agent)). No dedicated long-form agent confirmed [U] | [U] | [U] | Clip Genius (2025-09-02): edits uploaded video from one prompt [C\*] | No video API or MCP found [U] | Plus $24.99, Pro $249.99 [S] |
| **Manus** | Video generation: one prompt → scene plan → visuals → animated "video story"; default model at 30 credits/s, or Veo 3 at 600 credits per 8 s (help updated 2025-12-15) [C] ([help](https://help.manus.im/en/articles/11711172-what-can-manus-video-generation-feature-do)). No 2026 video updates confirmed [U]. Meta's acquisition (December 2025) was blocked by China and is being unwound [S] ([CNBC](https://www.cnbc.com/2026/08/11/manus-china-meta-acquisition.html)) | [U] | [U] | [U] | Listed as an MCP client of HeyGen [C] | Pro $20-200 [S] |
| **Descript** | **Underlord** (still beta): captions, clip splitting, transitions, translation, music, slides-to-video; user picks the LLM [C] ([help](https://help.descript.com/hc/en-us/articles/36803785502221-Underlord-beta-Your-AI-co-editor-in-Descript)) | n/a (editor) | [U] | Dubbing in 30+ languages (Business) [C] | API is a single agentic Underlord endpoint (beta). **MCP** `api.descript.com/v2/mcp` in the Claude and ChatGPT directories since late May 2026; Descript says the listing alone grew usage 10× [C] ([blog](https://www.descript.com/blog/article/dont-ship-your-api-as-an-mcp)) | $16-65/month [C] |
| **VEED** | In-app AI Video Agent [C]. **OpenEdit** (2026-08-19, beta): a timeline-free editing pipeline driven by a coding agent, installed with `npx skills add veedstudio/open-edit`; pipeline Apache-2.0, renderer closed but free; macOS only [C] ([post](https://www.veed.io/learn/openedit-by-veed)) | [U] | [U] | Editing pipeline [C] | Skills; Fabric API [C] | Credits [U] |
| **OpusClip** | **Agent Opus**: prompt, script, URL, audio or images → finished video, **≤10 min**; voice clone from 30 s in ~39 languages [C] ([FAQ](https://help.opus.pro/agent-opus/article/ao-faq)) | ≤10 min [C] | Voice clone [C] | Clipping, transcripts, editing scripts, scheduled publishing [C] | Remote MCP `mcp.opus.pro/mcp` (OAuth, ~27 tools, beta, in the MCP Registry) [C] ([MCP](https://www.opus.pro/mcp)) | Pro, billed per render minute [C] |
| **Canva** | "Create a Video Clip" (Veo 3, 8 s with audio) [C\*]. No 2026 video agent confirmed [U] | 8 s [C\*] | Brand kits | Full editor | Remote MCP `mcp.canva.com/mcp` (design generation and editing, MP4 export) [C] ([docs](https://www.canva.dev/docs/mcp/)) | Pro and above |
| **ElevenLabs** | Image & Video (beta) reselling Seedance 2.0, Kling 3.0, Veo 3.1, Sora 2, Gen-4.5, LTX-2, Wan 2.6 and lip-sync models [C] ([docs](https://elevenlabs.io/docs/overview/capabilities/image-video.md)) | Model-dependent | Avatars paired with any voice, including clones [C] | Studio 3.0 timeline (video, captions, narration, music, SFX); dubbing in 90+ languages [C] | Hosted MCP (OAuth) manages conversational agents, not video; `llms.txt` [C] | Paid plans |
| **Hedra** | Hedra Agent: collaborative canvas with reusable skills [C] ([llms.txt](https://www.hedra.com/llms.txt)) | Model-dependent | [U] | [U] | API v3, MCP `mcp.hedra.com/mcp`, CLI, SDKs, prepaid wallet; **deployable on customer-owned or air-gapped hardware** [C] | 100 models priced per second, including **MiniMax H3 at $0.05-0.16/s** [C] ([catalog](https://api.hedra.com/v3/models)) |

### 2d. Developer platforms

| Platform | Agent | Length | Consistency | Edit/post | Agent-facing | Pricing |
|---|---|---|---|---|---|---|
| **fal** | **fal Agent**, Early Access (2026-08-12) [C] ([PR](https://www.prnewswire.com/news-releases/fal-launches-fal-agent-a-creative-partner-for-frontier-generative-media-302850038.html)). It writes **editable plan cards**: rename or reorder steps, pin models, add **approval checkpoints**. It picks models, writes inputs and "repairs failed runs" [C] ([docs](https://fal.ai/docs/documentation/agent/index.md)). Per-media-type **USD spending caps**; ~60 tool calls per turn [C] ([FAQ](https://fal.ai/docs/documentation/agent/faq.md)). **No agent API yet**, which contradicts the press release [C] | "Video sequences": an ordered cut with audio layers, exported as one MP4; off by default; no maximum stated [C] ([docs](https://fal.ai/docs/documentation/agent/tools/video-sequences.md)) | Projects hold characters and shared memory; skills for cinematography and character consistency; LoRA training in chat [C] | Python sandbox with FFmpeg and a compositing renderer; timestamped video understanding [C] | Remote MCP `mcp.fal.ai/mcp` with 11 tools, including `get_pricing` and `recommend_model` [C] ([docs](https://fal.ai/docs/documentation/setting-up/mcp.md)). `llms.txt` at root, docs, full and per model [C]. genmedia CLI plus skills [C]. **Signed webhooks** (ED25519) [C]. **Price lookup and `/pricing/estimate` APIs** [C] ([estimate](https://fal.ai/docs/platform-apis/v1/models/pricing/estimate.md)) | Per output (per video second, etc.). Agent credit tiers $50/$200/$1,000; reasoning and sandbox free "for now" [C]. H3 on fal: $0.05-0.16/s [C] ([llms.txt](https://fal.ai/models/minimax/h3/image-to-video/llms.txt)) |
| **Replicate** (Cloudflare acquisition announced 2025-11-17) | None | Model-dependent | Model-dependent | Model-dependent | Remote MCP `mcp.replicate.com` (2025-08-10) plus npm `replicate-mcp` [C] ([blog](https://replicate.com/blog/remote-mcp-server)). `replicate/skills` (5 skills, including prompt-videos) [C]. `llms.txt`, webhooks [C]. No cost-quote API [C]. Catalogue includes `lightricks/ltx-2.5-fast` and MiniMax H3 [C] ([Lightricks](https://replicate.com/lightricks)) | Per output second [C] |

### 2e. Agent-facing integrations across vendors

"Poll" means no webhook was found in the docs that were read.

| Vendor | Official MCP | `llms.txt` | Skills / CLI / chat-app | Webhooks | Cost quote before spend |
|---|---|---|---|---|---|
| fal | Remote, 11 tools [C] | Yes, incl. per model [C] | genmedia CLI, skills, ChatGPT/Codex plugin [C] | Yes, ED25519 [C] | **Yes: pricing + estimate API** [C] |
| Replicate | Remote + local [C] | Yes [C] | 5 skills [C] | Yes [C] | No [C] |
| Runway | Remote consumer MCP, Dev MCP, local open-source [C] | Yes (3 files + `ai-context.md`) [C] | `runwayml/skills`, ChatGPT plugin [C] | **Poll** [C] | `estimatedCost` on tasks; agent docs say "Do not state or estimate credit costs" [C] |
| Google (Gemini API) | Docs MCP; `mcp-genmedia` unofficial [C] | Yes [C] | `gemini-skills` [C] | **Yes** [C] | No |
| Kling | Remote `kling.ai/mcp` [C] | Yes, with prices [C] | CLI + skill [C] | `callback_url` [S] | Price table only |
| MiniMax | Local, stale [C] | Yes [C] | `mmx-cli` + skill [C] | `callback_url` [C] | No |
| Luma | Legacy local only [C] | Agents docs 404 [C] | CLI [C] | Poll [C] | No |
| LTX | Docs search only [C] | Yes [C] | None | Poll [C] | No |
| Krea | Remote, 7 tools [C] | Yes [C] | ChatGPT plugin, Slack [C] | [U] | In-app estimates [C] |
| Higgsfield | Remote [C] | App directory only [C] | CLI, skills, ChatGPT plugin [C] | [U] | In-agent cost preview [C] |
| Magnific | Remote, 40+ tools [C] | Yes [C] | None found | Yes, HMAC [C] | No |
| OpenArt | Remote [C] | Not found | CLI [C] | Not found | No |
| Pika | Experimental remote, 58 tools [C] | dev API yes [C] | Skills [C] | dev API yes [C] | **Micro-USD quotes** [C] |
| HeyGen | Remote, 60+ tools, **multi-turn Video Agent** [C] | Yes [C] | CLI, skills, ChatGPT app, Stripe Projects [C] | Yes [C] | No |
| Adobe | Claude connector (edit/resize, not generation) [C] | 404 [C] | ChatGPT plugin [C] | [U] | No |
| Descript / OpusClip / Canva / Hedra | Remote [C] | Descript [U], Hedra yes [C] | Directory listings [C] | [U] | Hedra per-second catalogue [C] |
| OpenRouter | Remote, no video tool [C] | Yes [C] | Agent SDK [C] | **Yes**, HMAC `callback_url` on `/api/v1/videos` [C] ([docs](https://openrouter.ai/docs/cookbook/video-generation/video-generation-webhooks.md)) | `usage.cost` after the fact |

**Agent payments.** Stripe Projects lets an agent provision a service and receive an API key with a spend-limited
Shared Payment Token. HeyGen, ElevenLabs and OpenRouter are listed providers; fal, Replicate, Runway and LTX are not
[C] ([Stripe](https://docs.stripe.com/projects)). No video vendor was confirmed using x402 [U].

**Protocol state that matters for video.**
- **MCP Tasks.** Introduced as experimental in spec 2025-11-25 and now an official extension
  (`io.modelcontextprotocol/tasks`). A tool call can return a durable task handle to poll or subscribe to, which suits
  minute-long renders [C] ([MCP](https://modelcontextprotocol.io/extensions/tasks/overview)).
- **MCP Apps.** Launched 2026-01-26. Servers can return sandboxed HTML UI (media viewers, forms) that renders in
  Claude, ChatGPT, Goose and VS Code [C] ([MCP blog](https://blog.modelcontextprotocol.io/posts/2026-01-26-mcp-apps/)).
- **WebMCP.** A W3C Community Group draft. Chrome runs an origin trial (149-156). The API moved from
  `navigator.modelContext` to `document.modelContext` in mid-2026. No mainstream agent consumed WebMCP tools as of July
  2026 [S] ([Spronta](https://www.spronta.com/blog/state-of-webmcp-july-2026/)).

### 2f. Open-source video agent frameworks

Stars and dates are from the GitHub API on 2026-09-16.

| Project | Licence | What it does | Activity |
|---|---|---|---|
| [HKUDS/ViMax](https://github.com/HKUDS/ViMax) | MIT | Idea/script/novel → characters → storyboard → shots → assembly; v1.2.0 (2026-07-20) added a web UI and an agent loop [C] | 12.4k stars |
| [HITsz-TMG/VideoClaw](https://github.com/HITsz-TMG/VideoClaw) (the FilmAgent URL redirects here) | MIT | Script → character/scene design → storyboard → reference frames → video (Wan, Kling) → edit [C] | 1.8k stars |
| [HBAI-Ltd/Toonflow-app](https://github.com/HBAI-Ltd/Toonflow-app) | Apache-2.0 | Novel or script → animated short drama [C] | 15.7k stars |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | Apache-2.0 | HTML/CSS → MP4 renderer with agent skills (a composition layer, not a video model) [C] | 50.6k stars |
| [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) | **AGPL-3.0** | Turns a coding agent into a production pipeline, with a storyboard approval gate showing per-asset cost [C] | 59.5k stars; unusually high for a repo created 2026-03-29 |
| [chatfire-AI/huobao-drama](https://github.com/chatfire-AI/huobao-drama) | **CC BY-NC-SA** | One sentence → short drama (non-commercial) [C] | 15.3k stars |
| [waooAI/waoowaoo](https://github.com/waooAI/waoowaoo) | **Elastic 2.0** | Film production agent platform (source-available) [C] | 14.1k stars |
| [harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) | MIT | Topic → short video from stock footage, TTS and subtitles (no generative video) [C] | 124k stars |

ViMax, VideoClaw and Toonflow are the licence-clean references for a script → storyboard → shots pipeline.

### 2g. Other notable

- **Microsoft 365 Copilot / Clipchamp.** Describe a video (optionally with files and a brand kit) and Copilot drafts
  the script, picks stock visuals, and adds narration, transitions and titles. Output is typically under a minute.
  "Edit with AI" changes the narration voice or music. Commercial Entra users only [C]
  ([support](https://support.microsoft.com/en-us/microsoft-365-copilot/create-a-video-with-the-microsoft-365-copilot-app)).
  This is stock assembly, not generative video.
- **Amazon.**
  - Nova Reel 1.1 (2025-04) makes multi-shot videos of 6 s shots, up to 2 min. In automated mode one prompt sets the
    total length; in manual mode you give a prompt and image per shot [C]
    ([AWS](https://aws.amazon.com/blogs/aws/amazon-nova-reel-1-1-featuring-up-to-2-minutes-multi-shot-videos)).
  - Amazon Ads Video Generator (2025-06): product images → multi-scene ads with text animation and music, 6 options per
    request [C] ([Amazon Ads](https://advertising.amazon.com/library/news/video-generator)).
  - No 2026 updates were checked.
- **Tavus.** "Video agents" also means real-time conversational avatars (Tavus CVI, Synthesia Interactive Avatars,
  Runway Characters API, PikaStream) [C] ([Tavus](https://www.tavus.io/cvi)). That is a different product category from
  generation agents.
- **H3 is now widely resold:**
  - Krea (2026-08-27)
  - fal (Day-0 partner; H3 Max, H3 Max Turbo)
  - Runway API (`h3_max`, 2026-09-03)
  - Replicate
  - Pika's dev API
  - Hedra
  
  All sources [C]. Model access is not a moat.

---

## 3. Cross-platform feature matrix

**Y** = yes, **P** = partial, beta, limited or unofficial, **N** = no, **?** = not verified. Cells rest on the
sourced facts in section 2.

| Feature | Flow | Runway | Luma | Kling | MiniMax | ByteDance | Adobe | Higgsfield | Krea | LTX Studio | OpenArt | Magnific | Pika | HeyGen | InVideo | fal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Chat agent: brief → multi-shot video | Y | Y | Y | N | Y | P (Octo closed beta; CapCut Studio) | P (beta skills) | Y | Y | N (script → storyboard, no chat) | Y | Y | P (invite-only) | Y | Y | P (early access) |
| Editable plan / storyboard before render | P | Y | P | N | Y | Y | Y | Y | ? | Y | Y | P (editable Space) | ? | Y | P | Y |
| Explicit approval gate / cost preview for the whole plan | N | N | ? | N | P | P | ? | Y | P (estimates) | N | N | ? | ? | P (plan free) | ? | Y (checkpoints + caps) |
| Picks models automatically | Y (own) | Y | Y | N | Y (own) | P | ? | Y | Y | N | P | ? | Y | P | Y | Y |
| Native multi-shot in one generation | Y | Y (via models) | P (keyframes) | Y (6 cuts) | Y | Y | via models | Y | via models | Y | Y | via models | P | N | via models | via models |
| Single generation ≥30 s | N | Y (Seedance/Wan) | N | N | N | Y | N | Y | via models | N | ? | ? | N | Y (avatar) | via models | via models |
| Assembled film ≥1 min | Y (148 s extend) | Y (timeline) | ? | N | ? | P (180 s beta) | Y (editor) | Y (15 min skill) | ? | Y (60 s extend) | Y (5 min) | ? | ? | Y (30 min) | Y (30 min) | Y (sequences) |
| Reusable characters / Elements | Y | P (brand kits) | Y | Y | P (per-request refs) | P | P (private beta) | Y | Y | Y | Y | Y | P | Y (avatars) | Y (Context) | Y |
| Bound or cloned voice per character | P (experimental) | Y | P | Y | Y | P | P | Y | ? | Y | Y | P | Y | Y | ? | P |
| Timeline with voiceover + music | P | Y | Y | N | Y | Y | Y | Y | P | Y | Y | ? | P | Y | Y | Y |
| Captions | ? | ? | Y | N | ? | Y | P | ? | Y | ? | ? | ? | Y | Y | ? | P |
| Localization / dubbing with lip-sync | N | Y | Y | P | ? | ? | P (enterprise) | Y | ? | ? | Y | ? | P | Y | ? | ? |
| Edit a clip by instruction | Y (Omni) | Y (Aleph 2) | Y | Y (Omni) | P | Y | ? | Y | P | Y (retake) | Y | ? | Y | P | P | P |
| Official remote MCP | N | Y | N | Y | P (local) | P | P | Y | Y | N | Y | Y | P | Y | P | Y |
| Agent itself callable over MCP/API | N | N | N | N | P (template API) | N | N | N | P (node apps) | N | N | N | N | **Y** | N | N |
| Skills / CLI | P | Y | P | Y | Y | ? | P | Y | ? | N | Y | N | Y | Y | N | Y |
| `llms.txt` | Y | Y | P | Y | Y | N | N | P | Y | Y | N | Y | Y | Y | ? | Y |
| Webhooks | Y | N | N | P | Y | ? | ? | ? | ? | N | N | Y | Y | Y | N | Y |
| No training on customer content by default | Y (paid API) | N | ? | N | ? | ? | Y | ? | P (enterprise ZDR) | P (enterprise) | ? | ? | ? | N (enterprise only) | ? | ? |
| Confidential / attested processing | N | N | N | N | N | N | N | N | N | N | N | N | N | N | N | N |

### Table stakes (a video product without these looks behind in late 2026)

1. **A plan step before rendering.** A storyboard, shot list or "video plan" that the user can edit. Seen at Flow,
   Runway, MiniMax, ByteDance, Adobe, Higgsfield, LTX Studio, OpenArt, HeyGen and fal.
2. **Native multi-shot generation of 10-15 s.** Kling (6 cuts), H3, Seedance, LTX-2.5, Wan 2.7 and Omni. Every
   serious model has it.
3. **Assembling past a single clip.** Through extend, a timeline or an agent. Everyone except Kling and Midjourney.
4. **Reusable characters / Elements, usually `@`-tagged.** Flow, Luma, Kling, Higgsfield, Krea, LTX, OpenArt, Magnific,
   fal and HeyGen. More and more of them bind a voice to the character.
5. **Edit an existing clip by instruction.** Omni, Aleph 2, Luma Modify, Kling Omni, Seedance 2.5 and LTX Retake.
6. **A remote MCP server tied to account credits, plus `llms.txt`.** Runway, Kling, Higgsfield, Krea, Magnific,
   OpenArt, HeyGen, fal, Replicate, Descript, OpusClip and Canva.
7. **Automatic model choice** (for multi-model platforms). Runway, Luma, Higgsfield, Krea, InVideo, fal and Genspark.

### Differentiators (few have them)

1. **A price for the whole plan before it spends, with caps.** fal (estimate API, USD caps, checkpoints), Higgsfield
   (cost preview → approval) and Pika (micro-USD quotes). The opposite is common: OpenArt publishes no Director cost,
   and Runway's agent docs tell agents not to estimate cost.
2. **Human-in-the-loop checkpoints as a stated design.** fal plan cards, MiniMax Hub, HeyGen director mode and
   `ark-director`.
3. **The agent itself exposed to other agents.** Only HeyGen has multi-turn agent sessions over MCP and API. fal Agent,
   OpenArt Director and Magnific Agents are UI-only.
4. **Single-pass 30 s+ generation.** Seedance 2.5, Wan 3.0 and Cinema Studio 4.0, plus long avatar video (HeyGen, 30
   min).
5. **Performance-driven variants from ad metrics.** Runway Agent 2.0.
6. **Code-rendered motion graphics for agents.** HeyGen HyperFrames and VEED OpenEdit.
7. **Realtime steering.** Krea Realtime Director and PikaStream.
8. **Privacy-leaning designs.** MiniMax Design's local-first assets, Krea's enterprise zero-retention header, Hedra's
   air-gapped deployment, Adobe's no-training stance.

### Gaps nobody fills

- **Agent pipelines that run in private.** Nobody runs the planner, the renderer and the post-processing in attested
  enclaves.
- **Provenance that survives agent edits.** Nobody documents a C2PA chain that covers all of an agent's edits: the
  per-shot ingredients, stitching, captions and music.
- **Consent tracking for likeness since Sora closed.** Sora's cameo permission levels have no successor. Google's
  avatars are personal-only.

---

## 4. Recommendations for KunoWorld

**Where we start** (from the repos, 2026-09-16):
- **Modes:** text/image-to-video, last frame, first+last frame, keyframes, retake, audio-to-video, reference-to-video
  (H3), video edit, extend.
- **Output:** native audio; C2PA provenance.
- **Studio and web:** creation modes, plus one WebMCP tool, `stage_video_prompt`, which fills the prompt without
  submitting. The site serves `/llms.txt` and `/llms-full.txt`.
- **Developers:** API keys; webhooks with rotatable secrets; JavaScript and Python SDKs that encrypt on the client. The
  SDKs are not yet on npm or PyPI.
- **Pricing:** placeholder prices. No cost-quote endpoint was found among the gateway's public routes.
- **Storyboards:** proven on a GPU (35 s seamless single take from 8 × 5 s shots) and being built as a job type.
- **Not yet run:** a confidential GPU worker.

**Constraints on every recommendation:**
- **Private mode:** every planner, captioner, TTS, music or QA model runs **inside the enclave or on the client**, never
  on a third-party API. Standard mode may relax this, but it must be labelled.
- **H3 licence:** H3 is not available to US, EU, UK or KR users, so every agent feature must work on LTX-2.5 alone.
- **Joins:** storyboard joins need latents that must not leave the enclave. A storyboard is one job with one receipt.
- **Safety:** the safety gate must run on every prompt the planner writes, not only on the user's brief.

### 4.1 Ranking

| Rank | Feature | Value | Effort | Main dependency |
|---|---|---|---|---|
| 1 | Storyboard job + shot-card editor | Very high | Medium (under way) | `ltx_extend` pipeline, listening test |
| 2 | Private agent contract: local E2EE MCP server, skill, cost quote, MCP Tasks | High | Low-medium | SDKs on npm/PyPI, quote endpoint |
| 3 | Plan-first Director: brief → editable shot list → fixed quote → render, planner in enclave | Very high | Medium | 1, an in-enclave LLM profile |
| 4 | Encrypted Elements: characters, products, locations, voices, with consent | High | Medium | 1, key sync |
| 5 | Private captions and transcripts | Medium | Low | None (client-side first) |
| 6 | Storyboard templates / skills (ad, explainer, story, loop) | Medium | Low | 1 (and 3 for briefs) |
| 7 | Chat revisions of a finished take (retake a shot, extend, restyle) | High | Medium | 3, retake on LTX-2.5 |
| 8 | Format variants and localization (9:16/1:1 re-renders, translated dialogue and captions) | Medium | Medium-high | 3, 5, audio-to-video quality |
| 9 | Soundtrack and narration layer (music bed, voiceover mix) | Medium | Medium | Licence-clean open models, mixing |
| 10 | In-enclave QA judge with automatic retakes and refunds | Medium | Medium-high | VLM profile, GPU budget |

### 4.2 Details

#### 1. Storyboard job type and shot-card editor

**What it is**
- **The job:** an ordered list of shots, each with prompt, duration, join (`continue` / `cut` / `fresh`) and optional
  first frame or references.
- **The receipt:** one enclave, one receipt, per-shot progress.
- **The price:** the sum of the shots minus overlaps, shown before submit.
- **The studio:** shot cards with a join chip, running length and running cost, plus "retake this shot".
- **The output:** export the stitched film and, optionally, the per-shot clips.

**Why**
- **The plan is the common interface.** Every agent in section 2 produces a storyboard or shot list first: Runway,
  Flow, OpenArt, LTX Studio, CapCut Video Studio, Adobe's storyboard skill, HeyGen director mode and fal plan cards.
- **Single-generation limits are 10-30 s.** Our 35 s seamless take already exceeds the 30 s single-pass leaders
  (Seedance 2.5, Wan 3.0, Cinema Studio 4.0) on hardware we serve.
- **A shot card is also the unit every later feature edits:** Director, Elements, retakes, localization.

**Privacy fit**
- A storyboard is native to our design. Joins pin latents that must stay in the enclave (see the long-video note), so
  the shot list is encrypted to the worker like any prompt.
- The C2PA manifest can list each shot as a component ingredient. C2PA defines parent, component and input
  ingredients [C] ([C2PA explainer](https://spec.c2pa.org/specifications/specifications/2.2/explainer/Explainer.html)).

**Dependencies**
- Protocol shot schema; the `ltx_extend.py` pinning pipeline in the worker; per-shot safety gate and output scan.
- Verified-mode commitments per shot.
- A listening test of `cut` joins before offering a carried voice.
- A memory check for `ltx-2.5-pro` and 10 s shots.
- The shot list is LTX-2.5 only at first.

#### 2. Private agent contract: local E2EE MCP server, skill and cost quote

**What it is**
- **A local MCP server** (`npx`/`uvx`) that wraps the existing SDK, so encryption happens on the user's machine.
- **Tools:**
  - `list_models`
  - `quote` (exact price for a job or storyboard)
  - `create_video`
  - `create_storyboard`
  - `get_job`, returned as an **MCP Task** handle so minute-long renders don't block
  - `download` (decrypt to a local path)
  - `verify_receipt`
  - `share_link`
- **A skill** (`npx skills add`) with LTX-2.5 and H3 prompting guides and the storyboard JSON schema.
- **A "For AI agents" section** in `/llms.txt`, plus an OpenAPI file.
- **Later:** an MCP Apps widget that plays the decrypted video locally and shows the receipt.
- **Also:** extend the studio's WebMCP tools to `stage_storyboard` and `quote`.

**Why**
- **This is the standard way to reach agents now.** Remote MCP plus skills plus `llms.txt` is standard at Runway,
  Kling, Higgsfield, Krea, Magnific, OpenArt, HeyGen, fal and Replicate (section 2e).
- **Distribution is proven.** Descript reports that directory listings alone grew usage 10×.
- **Cost quotes are rare and wanted.** Only fal offers a quote API, and Runway tells agents not to estimate cost, so an
  exact quote is a real differentiator.
- **Timing.** OpenAI removes the Sora Videos API on 2026-09-24. That API was one of the few with webhooks and
  extensions to 120 s.

**Privacy fit**
- **Remote MCP breaks Private mode.** A remote MCP server hosted by KunoWorld would receive plaintext prompts, so
  Private mode must use the local server.
- **A remote OAuth MCP (the kind the ChatGPT and Claude directories list) can serve Standard mode only.** Every tool
  description must say so.
- **The agent host is outside the guarantee.** The host (Claude, ChatGPT, Cursor) and its model provider still see the
  prompt the user types. The guarantee covers KunoWorld, miners and GPU operators, not the user's chosen agent. Say
  this in the tool descriptions and in `llms.txt`.

**Dependencies**
- Publish `@kunoworld/sdk` and `kunoworld`.
- A quote endpoint (none found in the gateway's public routes).
- The storyboard job type for `create_storyboard`.
- MCP Tasks support in target clients varies [C] (MCP client matrix).
- WebMCP has almost no consuming agents yet [S], so keep that work small.

#### 3. Plan-first Director: brief → editable shot list → fixed quote → render

**What it is**
1. The user writes a brief and attaches references or Elements.
2. **An LLM inside the enclave returns a shot list:** shots, durations, joins, camera, dialogue lines, which Elements
   appear, and a suggested model per shot (LTX-2.5 everywhere; H3 only where licensed).
3. The plan comes back encrypted to the client, where the user edits the cards. Planning is free or nearly free.
4. **The user sees one fixed price and approves.** Then a single storyboard job renders.
5. **Chat edits re-plan only the affected shots.** For example, "make shot 3 a close-up, darker".
6. **Optional:** a spend cap per Director session.

**Why**
- **This is the core loop of Runway Agent, Flow Agent, OpenArt Director, HeyGen Video Agent, Higgsfield Supercomputer,
  Krea Agent and fal Agent.**
- **The best versions put an approval step before spending:**
  - HeyGen's plan revisions are free.
  - fal has approval checkpoints and USD caps.
  - Higgsfield shows a cost preview before approval.
  - MiniMax Hub pauses at key decisions.
- **Cost is where users are angriest.** OpenArt publishes no Director cost per minute, and our 09-11 note recorded
  complaints about opaque agent spend.
- **A fixed quote for a whole film is rare, and it fits our honest-billing position.**

**Privacy fit**
- **Planner model.** Private mode rules out every hosted LLM. Candidate planners:
  - An Apache-2.0 open-weight multimodal model, such as Qwen3.5-27B (image and video input, 262k context) [C]
    ([HF](https://huggingface.co/Qwen/Qwen3.5-27B)).
  - The Gemma-4-E2B prompt enhancer already bundled with LTX-2.5 [C] (`research_model_capabilities.md`). It is a
    candidate for a minimal v0 planner, with quality untested.
- **The planner's prompts pass the same safety gate as user prompts.**
- **The plan goes in the receipt** as an input ingredient (a hash, not the text).
- **Users who prefer their own agent** (Claude, ChatGPT) can plan there and send the shot list through recommendation
  2, accepting that their agent host sees the brief.

**Dependencies**
- Recommendation 1.
- **An LLM worker profile on confidential GPUs.** A 27B model at BF16 (~54 GB) cannot share a 96 GB card with an
  LTX-2.5 render that peaks at 87 GB. Options:
  - run a separate planning job,
  - run it sequentially on the same worker,
  - use FP8,
  - use a smaller model.
- **Structured-output validation.**
- **Prompt guides** (the open `h3-prompt-writing` guides for H3; LTX multishot guidance).
- **Pricing for planner tokens.**

#### 4. Encrypted Elements: characters, products, locations and voices

**What it is**
- **An Element** is a named set of reference images plus an optional 5-15 s voice clip. It is stored encrypted with
  the user's keys and mentioned in shot cards with `@name`.
- **How it is used:**
  - On H3, it expands into Ref2VA slots (≤9 images, ≤3 audio).
  - On LTX-2.5, it becomes each shot's first frame or keyframes, and later a LoRA trained in the enclave.
- **Real people need a consent record** that can be revoked and is noted in the receipt.

**Why**
- **Elements are table stakes:** Kling Elements with voice binding, Flow `@` characters and `@me`, Krea Elements
  (2026-09-09), Higgsfield Soul ID / AI Cast, LTX Studio Elements with voices, fal project characters, OpenArt
  Character Builder, Adobe Elements (beta), and xAI's 7 image references plus voice references.
- **Consent has had no successor since Sora closed.** Sora's cameo permission levels are gone, and Google's avatars are
  personal-only.

**Privacy fit**
- Faces, voices and unreleased products are the most sensitive inputs a video platform holds.
- Keeping them encrypted and usable only inside attested workers is a concrete reason to choose KunoWorld over every
  platform in section 2, all of which store them in plaintext.

**Dependencies**
- Recommendation 1 (per-shot references); cross-device key sync (exists through website sign-in).
- **LTX-only path quality.** H3 is geofenced, so how well first frames and keyframes hold identity on LTX-2.5 needs
  measuring.
- **Voice carry.** The long-video note found the voice not yet proven past a few shots.

#### 5. Private captions and transcripts

**What it is**
- **Output:** word-timed captions (VTT/SRT sidecar, optional burned-in style) and a transcript of the native dialogue.
- **v1 on the client:** Whisper large-v3-turbo (MIT, 809M, 99 languages, word timestamps) [C]
  ([HF](https://huggingface.co/openai/whisper-large-v3-turbo)), run in the browser via transformers.js WebGPU [S]
  ([Remotion](https://www.remotion.dev/docs/whisper-webgpu)).
- **v2 in the enclave:** the same model as a post-step, with burn-in recorded as a C2PA edit action.
- **Translation of captions** comes later, through the planner.

**Why**
- **Captions are standard in agent pipelines:** CapCut, the Luma App, Krea Agent, Pika MCP, HeyGen, Descript, Captions
  and Adobe.
- **Both our models generate dialogue,** so captions come almost free.

**Privacy fit**
- **Client-side adds no new party.** The video is already decrypted there.
- **In the enclave,** captions stay covered by the receipt.

**Dependencies**
- None heavy for the client-side v1.
- Burn-in inside the enclave needs a manifest update.

#### 6. Storyboard templates and skills

**What it is**
- **Templates:** product ad (3-5 shots), explainer with narrator, short story, seamless loop, "one continuous take".
  Each is a shot-list skeleton with join types and prompt slots, optionally filled from a brief by the Director.
- **Publishing:** templates are public, non-sensitive structure, published in the studio and in the agent skill.

**Why**
- **Everyone packages workflows:** Runway Skills, Higgsfield skills (Product UGC, TV Commercials), MiniMax Design's skills
  marketplace, InVideo Playbooks, Krea and Magnific apps and flows, HeyGen styles.
- **Templates cut failed spends** for new users.

**Privacy fit:** templates contain no user content. Filled templates are ordinary encrypted jobs.

**Dependencies:** recommendation 1; recommendation 3 for "fill from brief".

#### 7. Chat revisions of a finished take

**What it is:** instructions such as "retake shot 4", "extend the ending by 5 s", "make it night" or "swap the jacket
colour". The planner maps each one to an existing mode (retake, extend_video, video_edit, keyframes) on the affected
shots only. The price is shown before each revision.

**Why**
- **Edit-by-instruction is standard:** Omni Flash chat edits, Aleph 2, Luma Modify, Seedance 2.5 timestamp edits,
  OpenArt Director revisions, HeyGen `send_video_agent_message`.
- **Revising beats re-rolling the whole film,** which is where credit complaints start.

**Privacy fit**
- Revisions need the source take inside the enclave again: re-upload it encrypted from the client, or keep per-job
  latents only as long as the user's session.
- Nothing is held in plaintext outside the enclave.

**Dependencies**
- Recommendation 3.
- Retake and extend validated on the LTX-2.5 open pipeline. The hosted LTX API still offers them on `ltx-2-3-pro` only.

#### 8. Format variants and localization

**What it is**
- **Re-render** a storyboard at 9:16 or 1:1 from the same shot list and seeds.
- **Localize:** translate dialogue and captions, then regenerate or retake audio with lip-sync using LTX-2.5
  audio-to-video or retake-audio.

**Why**
- **Runway Agent 2.0** sells exactly this: localized versions and 9:16/16:9/1:1 cuts.
- **Localization is common elsewhere:**
  - HeyGen translation in 175+ languages
  - Higgsfield lip-sync translation in 18 languages
  - Synthesia Dubbing 2.0
  - OpenArt dubbing
  - Adobe Translate Video
- **Marketing teams buy it.**

**Privacy fit**
- All steps run in the enclave. Translation uses the planner LLM.
- **Fallback lip-sync:** LatentSync 1.6 (Apache-2.0, 512×512 mouth region, 18 GB) [C]
  ([GitHub](https://github.com/bytedance/LatentSync)) could run in the enclave if native audio-to-video lip-sync falls
  short.

**Dependencies**
- Recommendations 3 and 5.
- Measuring lip-sync quality of LTX-2.5 audio-to-video in non-English languages.

#### 9. Soundtrack and narration layer

**What it is**
- **Music bed:** a generated track under a storyboard.
- **Narration:** a voiceover track, mixed with the native audio (ducking).
- **Candidate open models:**
  - ACE-Step 1.5 (MIT, 10 s-10 min songs, 50+ languages) [C] ([GitHub](https://github.com/ace-step/ACE-Step-1.5)).
  - Chatterbox Multilingual (MIT, 23+ languages, voice cloning, Perth watermark on every file) [C]
    ([GitHub](https://github.com/resemble-ai/chatterbox)).
  - Or LTX-2.5 audio-to-video, for narration the picture should react to.

**Why**
- Runway Agent adds voiceover and music; Adobe's Generate Music and Speech went GA on 2026-08-20; fal sequences have
  audio layers; Google Vids adds Lyria music; HeyGen has a music library.
- **Ranked lower** because LTX-2.5 and H3 already generate ambience and dialogue.

**Privacy fit:** runs in the enclave. Mixing can run on the client.

**Dependencies**
- A licence review of each model.
- A worker profile for audio models.
- A C2PA ingredient for the added tracks.
- MiniMax's hosted Music API is closed to new users, so the hosted path would not exist anyway.

#### 10. In-enclave QA judge with automatic retakes

**What it is:** a vision-language model inside the enclave checks each shot before delivery: prompt adherence, Element
identity, artefacts, join seams. Failing shots are retaken automatically within a pre-approved budget, and the checks
are recorded in the receipt.

**Why**
- **Several agents already self-check:** Krea Agent reviews its output, fal "repairs failed runs", MiniMax Hub checks
  quality, `ark-director` has a QA stage, and Luma's Uni-1 critiques its own output.
- **Failed generations that still cost money are the category's top complaint** (09-11 note).

**Privacy fit**
- Must run in the enclave.
- It pairs with automatic refunds: we can refund what our own judge rejects.

**Dependencies**
- A VLM profile (the Qwen3.5 family takes video input).
- GPU time per shot; a policy for how many retakes a quote includes.
- A measured false-reject rate.

### 4.3 Not recommended now

- **A hosted remote MCP or ChatGPT/Claude directory app for Private mode.** It cannot keep the end-to-end promise. Offer
  it for Standard mode only, clearly labelled.
- **Agents that pull ad-platform metrics (Runway Agent 2.0).** They need third-party data connectors, which conflict
  with the privacy position and are far from our core.
- **Real-time steering (Krea Realtime Director, PikaStream).** No open realtime model fits our stack or our confidential
  hardware yet.
- **A social remix feed (Vibes, Sora).** Sora closed. Publishing is an explicit act of unsealing, so keep any showcase
  opt-in (see the 09-11 note).
- **Adopting an AGPL, non-commercial or Elastic-licensed agent framework as the base** (OpenMontage, huobao-drama,
  waoowaoo). Use MIT or Apache references (ViMax, VideoClaw, Toonflow) for design ideas only.

### 4.4 Open-weight building blocks for private agent features

| Role | Candidate | Licence | Notes | Source |
|---|---|---|---|---|
| Planner / translator / QA judge | Qwen3.5-27B | Apache-2.0 | Image and video input; 262k context; Feb 2026. Newer Qwen flagships (3.8) reportedly moved to a custom licence [S], so check each release | [HF](https://huggingface.co/Qwen/Qwen3.5-27B) [C] |
| Minimal planner / prompt enhancer | Gemma-4-E2B-it (bundled with LTX-2.5) | Gemma terms | Already inside our LTX worker image | `research_model_capabilities.md` [C] |
| Captions / transcripts | Whisper large-v3-turbo | MIT | 809M, 99 languages, word timestamps; also runs in the browser via transformers.js | [HF](https://huggingface.co/openai/whisper-large-v3-turbo) [C] |
| Music | ACE-Step 1.5 | MIT | 10 s-10 min; XL needs ≥20 GB without offload | [GitHub](https://github.com/ace-step/ACE-Step-1.5) [C] |
| Narration / voice clone | Chatterbox (Multilingual V3, Turbo) | MIT | 23+ languages; built-in Perth watermark | [GitHub](https://github.com/resemble-ai/chatterbox) [C] |
| Lip-sync fallback | LatentSync 1.6 | Apache-2.0 | 512×512 mouth region; 18 GB inference | [GitHub](https://github.com/bytedance/LatentSync) [C] |
| Long-running tool calls | MCP Tasks extension | Open spec | Durable task handle, polling or notifications | [MCP](https://modelcontextprotocol.io/extensions/tasks/overview) [C] |
| In-chat player / receipt UI | MCP Apps | Open spec | Sandboxed iframe UI in Claude, ChatGPT, VS Code, Goose | [MCP blog](https://blog.modelcontextprotocol.io/posts/2026-01-26-mcp-apps/) [C] |
| Provenance of composed films | C2PA ingredients (parent / component / input) | Open spec | Per-shot components, the plan as an input, edit actions for captions and music | [C2PA](https://spec.c2pa.org/specifications/specifications/2.2/explainer/Explainer.html) [C] |

---

## 5. Sources

**Google**
- Flow updates (I/O 2026): https://blog.google/innovation-and-ai/models-and-research/google-labs/flow-updates/
- Flow Agent help: https://support.google.com/flow/answer/17093911?hl=en
- Flow Tools help: https://support.google.com/flow/answer/17104535?hl=en
- Flow February 2026 updates: https://blog.google/innovation-and-ai/models-and-research/google-labs/flow-updates-february-2026/
- Flow new creative controls: https://blog.google/innovation-and-ai/models-and-research/google-labs/new-creative-controls-google-flow/
- Scenebuilder help: https://support.google.com/flow/answer/16935718?hl=en
- Characters and voices help: https://support.google.com/flow/answer/16353334?hl=en
- Flow credits: https://support.google.com/flow/answer/16526234?hl=en
- Gemini Omni: https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-omni/
- Build with Omni 1.1 Flash: https://blog.google/innovation-and-ai/technology/developers-tools/build-with-gemini-omni-1-1-flash/
- I/O 2026 announcements: https://blog.google/innovation-and-ai/technology/ai/google-io-2026-all-our-announcements/
- Gemini app video: https://gemini.google/overview/video-generation/
- Veo API: https://ai.google.dev/gemini-api/docs/veo
- Omni API: https://ai.google.dev/gemini-api/docs/omni
- Gemini API webhooks: https://ai.google.dev/gemini-api/docs/webhooks
- Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini API terms: https://ai.google.dev/gemini-api/terms
- Gemini API changelog: https://ai.google.dev/gemini-api/docs/changelog
- Vids "Help me create": https://workspaceupdates.googleblog.com/2025/03/new-capabilities-for-google-vids-help-me-create.html
- Vids Lyria and Veo: https://blog.google/products-and-platforms/products/workspace/google-vids-updates-lyria-veo/
- Vids personal avatars: https://workspaceupdates.googleblog.com/2026/07/cast-yourself-in-ai-video-clips-using-your-personal-avatar-with-Gemini-Omni-in-Vids.html
- Vertex remote MCP: https://cloud.google.com/blog/products/ai-machine-learning/gemini-enterprise-agent-platform-remote-mcp-server/
- mcp-genmedia: https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio/tree/main/experiments/mcp-genmedia

**OpenAI**
- Deprecations: https://developers.openai.com/api/docs/deprecations
- API changelog: https://developers.openai.com/api/docs/changelog
- Video generation guide: https://developers.openai.com/api/docs/guides/video-generation
- Your data: https://developers.openai.com/api/docs/guides/your-data
- sora-2-pro model page: https://developers.openai.com/api/docs/models/sora-2-pro
- Storyboards post: https://x.com/OpenAI/status/1978661828419822066
- Shutdown [S]: https://the-decoder.com/openai-sets-two-stage-sora-shutdown-with-app-closing-april-2026-and-api-following-in-september/
- Shutdown [S]: https://techcrunch.com/2026/03/24/openais-sora-was-the-creepiest-app-on-your-phone-now-its-shutting-down/
- Cameos and stitching [S]: https://www.macrumors.com/2025/10/30/openai-sora-app-character-cameos-video-stitching/
- Cameo permissions [S]: https://www.engadget.com/ai/openais-character-cameos-will-let-you-put-pets-and-original-personas-in-sora-videos-123043189.html

**Meta**
- Vibes: https://about.fb.com/news/2025/09/introducing-vibes-ai-videos/
- Muse Image and Muse Video: https://ai.meta.com/blog/introducing-muse-image-muse-video-msl/
- Muse Spark and Meta Model API: https://ai.meta.com/blog/introducing-muse-spark-meta-model-api/
- Meta One: https://about.fb.com/news/2026/09/introducing-meta-one-subscription-service-more-features-ai/
- Muse personal agent: https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/
- Meta AI app listing: https://apps.apple.com/us/app/meta-ai/id1558240027
- Edits app listing: https://apps.apple.com/us/app/edits-an-instagram-app/id6738967378
- Standalone Vibes test [S]: https://www.socialmediatoday.com/news/metas-testing-a-standalone-ai-video-app/811380/

**Adobe**
- Custom models and video creation: https://blog.adobe.com/en/publish/2026/03/19/adobe-firefly-expands-video-image-creation-with-new-ai-capabilities-custom-models
- Introducing Firefly AI Assistant: https://blog.adobe.com/en/publish/2026/04/15/introducing-firefly-ai-assistant-new-way-create-with-our-creative-agent
- Video and Premiere updates: https://blog.adobe.com/en/publish/2026/04/15/adobe-extends-leadership-video-unleashing-new-ai-powered-creation-firefly-reinventing-color-editors-in-premiere
- Public beta: https://blog.adobe.com/en/publish/2026/04/27/firefly-ai-assistant-public-beta
- Claude connector announcement: https://blog.adobe.com/en/publish/2026/04/28/adobe-for-creativity-connector
- June 2026 expansion: https://news.adobe.com/news/2026/06/adobe-unveils-major-expansion
- Music, speech and sound effects: https://blog.adobe.com/en/publish/2026/08/20/adobe-firefly-expands-its-creative-ai-studio-generate-music-speech-and-sound-effects-in-one-place
- Adobe for ChatGPT: https://blog.adobe.com/en/publish/2026/08/06/introducing-adobe-chatgpt-create-edit-get-work-done-all-in-chatgpt
- Claude connector listing: https://claude.com/connectors/adobe-creativity
- Firefly plans: https://www.adobe.com/products/firefly/plans.html
- Partner models: https://www.adobe.com/products/firefly/partner-models.html
- Generative AI approach: https://www.adobe.com/ai/overview/firefly/gen-ai-approach.html
- Firefly Services: https://developer.adobe.com/audio-video-firefly-services/

**xAI**
- Grok Imagine API: https://x.ai/news/grok-imagine-api
- Imagine Video 1.5 references: https://x.ai/news/grok-imagine-video-1-5-references
- Video generation docs: https://docs.x.ai/developers/model-capabilities/video/generation

**Runway**
- Introducing Runway Agent: https://runway.com/news/introducing-runway-agent
- Agent 2.0: https://runway.com/news/introducing-agent-2
- Agent product page: https://runway.com/product/agent
- Inside building Runway Agent: https://runway.com/news/engineering/inside-building-runway-agent
- Changelog: https://runway.com/changelog
- Aleph 2 and Edit Studio: https://runway.com/news/introducing-aleph-2-and-edit-studio
- Consumer MCP: https://runway.com/mcp
- Dev MCP: https://runway.com/news/company-news/runway-dev-mcp
- Open-source MCP server: https://github.com/runwayml/runway-api-mcp-server
- API AI context: https://docs.dev.runwayml.com/ai-context.md
- API reference: https://docs.dev.runwayml.com/api.md
- API changelog: https://docs.dev.runwayml.com/api-details/api_changelog/
- API pricing: https://docs.dev.runwayml.com/guides/pricing.md
- Plans: https://runway.com/pricing

**Luma**
- Luma App: https://lumalabs.ai/app
- LLM info: https://lumalabs.ai/llm-info
- Ray3.2: https://lumalabs.ai/news/introducing-ray-3-2
- Layers: https://lumalabs.ai/news/introducing-layers
- Agents API docs: https://docs.agents.lumalabs.ai/
- Agents API FAQ: https://docs.agents.lumalabs.ai/guides/faq/
- Pricing: https://lumalabs.ai/pricing
- API: https://lumalabs.ai/api
- Legacy MCP: https://github.com/lumalabs/luma-api-mcp
- Agents launch [S]: https://techcrunch.com/2026/03/05/exclusive-luma-launches-creative-ai-agents-powered-by-its-new-unified-intelligence-models/

**Kling**
- llms.txt: https://kling.ai/llms.txt
- Subject binding and character consistency: https://kling.ai/blog/kling-3-subject-binding-character-consistency
- Omni native lip-sync and audio: https://kling.ai/blog/kling-video-3-omni-native-lip-sync-audio-guide
- Claude Code MCP workflow: https://kling.ai/blog/claude-code-kling-mcp-food-promo-workflow
- Skill file: https://raw.githubusercontent.com/klingai-tech/skills/main/SKILL.md
- Kling 3.0 launch: https://www.prnewswire.com/news-releases/kling-ai-launches-3-0-model-ushering-in-an-era-where-everyone-can-be-a-director-302679944.html
- Kuaishou Q2 2026 results: https://www.prnewswire.com/news-releases/kuaishou-technology-announces-second-quarter-and-interim-2026-unaudited-financial-results-302855081.html

**MiniMax**
- H3: https://www.minimax.io/blog/minimax-h3
- Video Agent: https://www.minimax.io/news/video-agent
- Hailuo 2.3 and Media Agent: https://www.minimax.io/news/minimax-hailuo-23
- MiniMax Design (Hub): https://hub.minimax.io/
- MiniMax Agent changelog: https://agent.minimax.io/docs/changelog
- Video generation guide: https://platform.minimax.io/docs/guides/video-generation
- Pay-as-you-go pricing: https://platform.minimax.io/docs/guides/pricing-paygo
- MiniMax-MCP: https://github.com/MiniMax-AI/MiniMax-MCP
- CLI: https://github.com/MiniMax-AI/cli
- H3 Max by fal: https://blog.fal.ai/introducing-h3-max-by-fal/
- Hub launch [S]: https://tech.yahoo.com/ai/articles/minimax-launches-one-ai-video-193031165.html

**ByteDance**
- Seedance 2.0 launch: https://seed.bytedance.com/en/blog/official-launch-of-seedance-2-0
- Introducing Seedance 2.5: https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5
- Dreamina creative agent: https://dreamina.capcut.com/ai-video/ai-creative-agent
- Dreamina storyboards: https://dreamina.capcut.com/resource/ai-for-storyboards
- Dreamina Seedance 2.5 launch: https://dreamina.capcut.com/resource/seedance-2-5-launch
- CapCut Seedance 2.5 editor: https://www.capcut.com/features/seedance-2-5-for-video-editor
- CapCut Video Studio post: https://x.com/capcutapp/status/2036943209956344181
- ark-mcp: https://github.com/byteplus-sa/ark-mcp
- ark-director: https://github.com/byteplus-sa/ark-director

**Alibaba Wan**
- Newly released models: https://www.alibabacloud.com/help/en/model-studio/newly-released-models
- Video generation docs: https://www.alibabacloud.com/help/en/model-studio/use-video-generation
- Wan-Video GitHub: https://github.com/Wan-Video
- Wan-skills: https://github.com/Wan-Video/Wan-skills

**Pika**
- Pika Experiments: https://experiment.pika.art/blog/pika-experiments
- AI Self: https://experiment.pika.art/ai-self
- MCP: https://experiment.pika.art/mcp
- Developer API llms.txt: https://dev.pika.art/llms.txt
- Pricing: https://pika.art/pricing
- iOS app: https://apps.apple.com/us/app/pika-ai-agent/id6758411447

**Higgsfield**
- Supercomputer help: https://higgsfield.ai/creator-hub/help-center/tools/how-do-i-use-supercomputer
- Supercomputer guide: https://higgsfield.ai/blog/higgsfield-supercomputer-guide
- How Supercomputer was built: https://higgsfield.ai/blog/how-we-built-supercomputer
- Cinema Studio 4.0: https://higgsfield.ai/blog/cinema-studio-4-0
- Changelog: https://higgsfield.ai/creator-hub/changelog
- MCP: https://higgsfield.ai/mcp
- Connecting to an AI agent: https://higgsfield.ai/creator-hub/help-center/integrations/how-do-i-connect-higgsfield-to-ai-agent

**Krea**
- What is Krea Agent: https://www.krea.ai/blog/what-is-krea-agent
- Changelog: https://www.krea.ai/docs/changelog
- MCP docs: https://www.krea.ai/docs/developers/mcp.md
- Node workflow agent: https://www.krea.ai/blog/ai-workflow-agent

**LTX / Lightricks**
- LLM info: https://ltx.io/llm-info
- Storyboard generator update: https://ltx.io/blog/ltx-storyboard-generator-update
- Script to video: https://ltx.io/studio/platform/script-to-video
- Product updates: https://ltx.io/blog-category/product-updates
- Flows: https://ltx.io/blog/ltx-studio-flows
- Docs llms.txt: https://docs.ltx.io/llms.txt
- API pricing: https://docs.ltx.io/pricing.md
- Extend endpoint: https://docs.ltx.io/api-documentation/api-reference/async-video-generation/submit-extend.md
- Studio pricing: https://ltx.io/studio/pricing

**Magnific**
- Rebrand press release: https://www.prnewswire.com/news-releases/freepik-becomes-magnific-hits-230m-arr-and-introduces-the-no-collar-creative-economy-302755376.html
- MCP docs: https://docs.magnific.com/modelcontextprotocol
- API llms.txt: https://docs.magnific.com/llms.txt
- Agents: https://www.magnific.com/agents

**OpenArt**
- Director: https://openart.ai/features/director/
- How to use Director: https://openart.ai/blog/how-to-use-openart-director/
- What's new: https://openart.ai/whats-new
- MCP: https://openart.ai/mcp/
- Pricing: https://openart.ai/pricing

**Moonvalley and Midjourney**
- Reka and Moonvalley: https://reka.ai/news/reka-and-moonvalley-join-forces-to-advance-models-and-infrastructure-for-physical-ai
- Marey: https://www.moonvalley.com/marey
- Midjourney updates feed: https://updates.midjourney.com/rss/
- Midjourney V1 video: https://updates.midjourney.com/introducing-our-v1-video-model/

**HeyGen**
- Getting started with Video Agent: https://help.heygen.com/en/articles/12402907-how-to-get-started-with-video-agent
- Video Agent FAQ: https://help.heygen.com/en/articles/16007192-video-agent-faq
- July 2026 release: https://www.heygen.com/blog/heygen-july-2026-release
- MCP: https://developers.heygen.com/mcp/overview
- llms.txt: https://developers.heygen.com/llms.txt
- API pricing: https://help.heygen.com/en/articles/10060327-heygen-api-pricing-explained
- Plans: https://www.heygen.com/pricing
- Security: https://www.heygen.com/security
- HyperFrames: https://github.com/heygen-com/hyperframes

**Synthesia, InVideo, Captions / Mirage, Genspark, Manus**
- Synthesia Assistant: https://docs.synthesia.io/docs/assistant
- Synthesia video agents: https://www.synthesia.io/features/video-agents
- Synthesia pricing: https://www.synthesia.io/pricing
- InVideo Agent Two: https://invideo.io/agent-two/
- InVideo Agent Two announcement: https://invideo.io/news/introducing-agent-intelligence-invideo-agent-two/
- InVideo pricing: https://invideo.io/pricing
- Mirage: https://mirage.app/
- Captions overview: https://captions.ai/overview
- Captions pricing: https://captions.ai/pricing
- Genspark video agent: https://www.genspark.ai/agents?type=video_generation_agent
- Manus video generation help: https://help.manus.im/en/articles/11711172-what-can-manus-video-generation-feature-do

**Descript, VEED, OpusClip, Canva, ElevenLabs, Hedra**
- Descript on MCP: https://www.descript.com/blog/article/dont-ship-your-api-as-an-mcp
- Underlord help: https://help.descript.com/hc/en-us/articles/36803785502221-Underlord-beta-Your-AI-co-editor-in-Descript
- VEED OpenEdit: https://www.veed.io/learn/openedit-by-veed
- OpusClip MCP: https://www.opus.pro/mcp
- Agent Opus FAQ: https://help.opus.pro/agent-opus/article/ao-faq
- Canva MCP: https://www.canva.dev/docs/mcp/
- ElevenLabs image and video: https://elevenlabs.io/docs/overview/capabilities/image-video.md
- Hedra llms.txt: https://www.hedra.com/llms.txt
- Hedra model catalogue: https://api.hedra.com/v3/models

**fal and Replicate**
- fal Agent docs: https://fal.ai/docs/documentation/agent/index.md
- fal Agent FAQ: https://fal.ai/docs/documentation/agent/faq.md
- fal Agent launch: https://www.prnewswire.com/news-releases/fal-launches-fal-agent-a-creative-partner-for-frontier-generative-media-302850038.html
- fal MCP: https://fal.ai/docs/documentation/setting-up/mcp.md
- fal price estimate API: https://fal.ai/docs/platform-apis/v1/models/pricing/estimate.md
- fal webhooks: https://fal.ai/docs/documentation/model-apis/inference/webhooks.md
- Replicate remote MCP: https://replicate.com/blog/remote-mcp-server
- Replicate MCP docs: https://replicate.com/docs/reference/mcp
- Replicate skills: https://replicate.com/docs/reference/skills

**Cross-vendor, protocols and building blocks**
- Stripe Projects: https://docs.stripe.com/projects
- OpenRouter video webhooks: https://openrouter.ai/docs/cookbook/video-generation/video-generation-webhooks.md
- MCP Tasks: https://modelcontextprotocol.io/extensions/tasks/overview
- MCP Apps: https://blog.modelcontextprotocol.io/posts/2026-01-26-mcp-apps/
- State of WebMCP [S]: https://www.spronta.com/blog/state-of-webmcp-july-2026/
- C2PA explainer: https://spec.c2pa.org/specifications/specifications/2.2/explainer/Explainer.html
- Qwen3.5-27B: https://huggingface.co/Qwen/Qwen3.5-27B
- Whisper large-v3-turbo: https://huggingface.co/openai/whisper-large-v3-turbo
- ACE-Step 1.5: https://github.com/ace-step/ACE-Step-1.5
- Chatterbox: https://github.com/resemble-ai/chatterbox
- LatentSync: https://github.com/bytedance/LatentSync
- ViMax: https://github.com/HKUDS/ViMax
- VideoClaw: https://github.com/HITsz-TMG/VideoClaw
- Microsoft Copilot video: https://support.microsoft.com/en-us/microsoft-365-copilot/create-a-video-with-the-microsoft-365-copilot-app
- Amazon Nova Reel 1.1: https://aws.amazon.com/blogs/aws/amazon-nova-reel-1-1-featuring-up-to-2-minutes-multi-shot-videos
- Tavus CVI: https://www.tavus.io/cvi
