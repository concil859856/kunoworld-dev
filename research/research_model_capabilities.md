# Kino: Model Capability Research — MiniMax H3 and LTX-2.5

Research date: 2026-09-11. Scope: every generation capability of the two open-weight models Kino miners will run. Also covers exact parameter constraints, the official inference entry points (with code), hardware needs, licensing obligations that affect the UI, a unified capability matrix, and a proposed unified request schema.

**How I checked sources.** I pulled raw files from GitHub and Hugging Face with `curl` wherever possible: READMEs, configs, request scripts, argparse source and `constants.py`. Statements are tagged:

- **[CONFIRMED]**: quoted or read directly from official source code, configs or official docs.
- **[SECONDARY]**: from third-party or partner pages (fal, Runpod, vLLM/SGLang recipe summaries, community guides).
- **[UNVERIFIED]**: inferred, contradicted between sources, or read from a gated page that couldn't be fetched.

Gated Hugging Face repos could not be fetched without auth. That covers `Lightricks/LTX-2.5` raw files, `LTX-2.5-Diffusers` raw files, and several IC-LoRA cards. For those I relied on the rendered HF pages (via WebFetch), the HF API file listings, and the LTX-2 GitHub repo, which is public.

---

## 0. TL;DR for the Kino team

1. **MiniMax H3 is really two checkpoints (transformer partitions).** They share the Qwen3-VL-32B encoder, the VAEs and the schedulers.
   - `transformer/` serves **t2va / fl2va** (0, 1 or 2 keyframe images).
   - `transformer_ref/` serves **ref2va**: ≤9 images, ≤3 videos, ≤3 audio clips, ≤12 total. Ref2VA also covers **video editing, video continuation (extension), voice-timbre reference and audio reuse**, all driven by prompt semantics.
   - Output is fixed at **24 fps**, a **768 px short edge** (canvas ≤1,032,192 px, i.e. 1344×768), **4–15 s** and **32 kHz stereo audio**.
   - The weights are **CFG-distilled**: no negative prompt, no guidance scale.
   - The open release does **not** include 2K (H3-Regenerate-2K) or the prompt pre-processor (H3-Context-IR). Both are MiniMax-hosted APIs only. Calling them would break Kino's privacy/TEE guarantee.
2. **H3 Turbo (LightX2V) is a set of LoRAs on top of H3.**
   - Step counts: 4 and 8 NFE. Training resolutions: 544p (mixed aspect ratios) or 768p (1344×768).
   - Video/audio shift: 12/3 for the 544p LoRAs, 6/3 for the 768p LoRAs.
   - Coverage: FL2VA/T2VA LoRAs plus a Ref2VA 4-step v0.1 LoRA. A Ref2VA 8-step v1.0 768p LoRA file is also published but not in the README table.
   - License: Apache-2.0 on the LoRA files, but they remain H3 Model Derivatives.
3. **LTX-2.5 is a much broader toolbox.** It is a 22B DiT with a Gemma-4-12B encoder, and `ltx-pipelines` ships 12 pipelines:
   - **Generation:** Distilled (8+3 steps), DFR (production quality, up to 4K, 2×/4× fps), TI2Vid two-stage (full model with CFG/STG), keyframe interpolation, A2Vid (audio→video), text→audio.
   - **Editing:** Retake (regenerate a time window), IC-LoRA video-to-video (control/restyle), Dub-It (lip-synced re-dubbing), HDR/EXR.
   - **Built in:** automatic duration prediction (duration head) and a prompt enhancer (Gemma-4 E2B-it).
   - **Constraints:** `num_frames = 8k+1`; dimensions must be divisible by 32 (one-stage), 64 (two-stage) or 128 (DFR `--spatial-upscalings 2`). 4K is 3840×2176.
4. **UI must-haves from the licenses.**
   - **H3:** "prominently display 'MiniMax H3'" on the UI. The territory exclusion (US/EU/UK/KR) means users there must be geo-blocked from H3 unless MiniMax grants authorization. Users must be bound to the Section V / Exhibit A use restrictions, and there must be an abuse-report mechanism.
   - **LTX:** free only for entities under $10M revenue. Built-in AI-disclosure, watermark and provenance features must not be stripped (EU AI Act, California AI Transparency Act clause).

---

## 1. MiniMax H3

Primary sources:
- GitHub README: https://github.com/MiniMax-AI/MiniMax-H3 (raw: https://raw.githubusercontent.com/MiniMax-AI/MiniMax-H3/main/README.md)
- HF model card: https://huggingface.co/MiniMaxAI/MiniMax-H3
- diffusers docs: https://huggingface.co/docs/diffusers/main/en/api/pipelines/minimax_h3
- SGLang cookbook: https://docs.sglang.io/cookbook/diffusion/MiniMax/MiniMax-H3
- vLLM recipe: https://recipes.vllm.ai/MiniMaxAI/MiniMax-H3
- Official request scripts: `scripts/readme/*.sh` in the GitHub repo
- LICENSE: https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE

### 1.1 Architecture facts that drive constraints [CONFIRMED]

- **H3-Omni-Transformer:** 33B dense, single-stream, about 13B of which is in AdaLN branches ("can be precomputed and cached"). Transformer config: `num_layers: 50`, `hidden_size: 5376`, `num_attention_heads: 56`, `attention_head_dim: 128`, `in_channels: 24`, `audio_in_channels: 32`, `patch_size: [1,2,2]`, `text_dim: 5120` (`transformer/config.json`).
- **H3-Encoder:** the full Qwen3-VL-32B, reading the hidden state from **layer 50**. H3 adds special tokens (e.g. `<d>`), so the H3 tokenizer and configs are required.
- **H3-VisualVAE:** f16t4d24 (16× spatial, 4× temporal, 24 channels). After the 1×2×2 patchify, the transformer sees 32× spatial and 4× temporal downsampling.
- **H3-AudioVAE:** 32 kHz, each stereo channel encoded independently at a 40 Hz latent rate.
- **Schedulers:** two `MiniMaxH3Scheduler` instances — `scheduler/scheduler_config.json` has `"shift": 12.0` (video) and `audio_scheduler/...` has `"shift": 3.0` (audio).
- **Guidance:** "The released checkpoints are CFG-distilled Omni Transformer model weights" (README). The diffusers docs add: "there is no guider, no `negative_prompt` and no `guidance_scale`, and every step runs exactly one forward pass."
- **Attention:** sparse attention is "not included in the initial open-source release" — the open release runs full attention only.

### 1.2 Capability list

| Capability | Supported? | How / notes | Source |
|---|---|---|---|
| Text-to-video (+audio) | Yes (FL2VA checkpoint) | `task: "t2va"`, no conditions | README, SGLang script [CONFIRMED] |
| Image-to-video (first frame) | Yes (FL2VA) | image condition `role: "keyframe"`, `frame_index: 0` (SGLang); `image=` (diffusers) | [CONFIRMED] |
| Last frame only ("L2VA") | Yes (FL2VA) | `frame_index: -1` (SGLang); `last_image=` alone (diffusers: "Can be passed on its own to generate *up to* a frame") | [CONFIRMED] |
| First + last frame interpolation | Yes (FL2VA) | two keyframe conditions, frame_index 0 and -1; diffusers `image=` + `last_image=` (last image is cover-cropped onto the canvas) | [CONFIRMED] |
| Multi-keyframe (>2 images at arbitrary times) | **No** in FL2VA (0–2 images only) | Ref2VA can use `<Picture N>` as a "keyframe completion" / "storyboard reference" through prompt semantics (ref-en guide). This is not hard pixel anchoring | ref-en.txt [CONFIRMED for prompt semantics; pixel-exactness UNVERIFIED] |
| Reference-to-video (omni-reference) | Yes (Ref2VA checkpoint) | ≤9 images, ≤3 videos (each 2–15 s, total ≤15 s), ≤3 audio clips (each 2–15 s, total ≤15 s), ≤12 files total. **Order is semantic**: it sets the `<Picture N>/<Video N>/<Audio N>` labels and advances the shared RoPE clock | README, diffusers [CONFIRMED] |
| What refs mean | Image = "subject, style or scene reference"; Video = "motion and camera reference", conditioned with its own soundtrack (or as an editing/continuation source); Audio = "voice or music reference" | Roles are declared in the **prompt** (`subject_definitions`, `retention_analysis` markers `fully_preserved / partially_preserved / attribute_transfer / weak_reference`; audio markers `fully_copy / partially_copy / reference`) | diffusers docstrings, ref-en.txt [CONFIRMED] |
| Audio-only reference | **Conflicting** | diffusers: "audio references cannot be the only ones". SGLang cookbook lists an `audio_only` Ref2VA mode | [UNVERIFIED — require ≥1 image/video ref in Kino to be safe] |
| Video extension / continuation | Yes (Ref2VA) | ref-en task type `video continuation`: "New content continues, extends, resumes, or transitions from an existing source video". Pass the source as a `video` or `video_audio` reference. Output length is still capped at 15 s | ref-en.txt [CONFIRMED semantics] |
| Video-to-video edit / restyle | Yes (Ref2VA) | ref-en task type `video editing` ("The target video is an edited version of <Video 1>"). The official Ref2VA example edits a video to make the subject speak new dialogue | request script [CONFIRMED] |
| Native audio (joint A/V) | Yes, always | 32 kHz stereo, one denoising loop (no separate vocoder pass) | [CONFIRMED] |
| Speech / lip-sync from text | Yes | `<d>[English] line</d>` dialogue tags, speaker IDs `(S1)`, `(S1,S2)`, voiceover syntax, `<scenetrans>`, `<cutoff>`. 11 "stable" languages: ar, zh, en, fr, de, it, ja, ko, pt, ru, es | base-en.txt, README [CONFIRMED] |
| Voice timbre cloning from audio | Yes (Ref2VA audio ref, marker `reference`) | e.g. "`<Audio 1>` is the voice-timbre reference for `<Subject 1>` (S1)" | ref-en.txt [CONFIRMED] |
| Audio-driven video (use supplied audio as the soundtrack) | Yes (Ref2VA, marker `fully_copy` / `partially_copy`) | diffusers: to match a reference soundtrack's length pass `num_frames=round(samples/sample_rate*24)` | [CONFIRMED] |
| Music | Yes | `non_diegetic_music:` prompt section (1–3 sentences, or `N/A`) | base-en.txt [CONFIRMED] |
| Silent output | Not native | Audio is always generated; strip it in post | [CONFIRMED by design] |
| Multi-shot / storyboard | Yes | `[Shot 1] ...` (no timestamp), `[Shot 2] At 00:03.500, the camera cuts to ...`; cut times strictly increasing within the duration. FL2VA "generally favors a single shot" | base-en.txt [CONFIRMED] |
| Camera control | Prompt only | Vocabulary: Zoom In/Out, Arc Shot, Tracking Shot, Static Shot, push-in, truck, etc. (base-en §4). A Ref2VA video can serve as a motion/camera reference. Community ComfyUI "embeddings" exist (e.g. `embedding:minimaxh3_bullet_time`) | [CONFIRMED prompt; embeddings SECONDARY] |
| Control signals (depth/pose/canny) | No official support | The ComfyUI H3 page lists a "ControlNet Union" workflow card; not verified as an H3-native feature | [UNVERIFIED] |
| Upscaling / 2K | **Not open** | H3-Regenerate-2K: "this module is not yet open-sourced". API: `POST /v2/video_regeneration` with `"resolution": "2K"` | README [CONFIRMED] |
| Looping | Not native | Possible trick: FL2VA with the same image as first and last frame | [UNVERIFIED] |
| Negative prompt / CFG | **No** | CFG-distilled | diffusers [CONFIRMED] |
| Prompt enhancer | **Hosted only** (H3-Context-IR, `POST /v2/h3_context_ir`) | MiniMax "strongly recommend incorporating it". Open alternative: the `h3-prompt-writing` skill (Markdown + reference guides `base-en.txt`, `ref-en.txt`) run with our own LLM | README [CONFIRMED] |
| Seeds / determinism | Yes | SGLang `seed`. diffusers: "One generator, three draws" — conditioning noise, then video noise, then audio noise, so the same generator state gives the same video and soundtrack. Note: the MiniMax hosted API does **not** accept a seed | diffusers, API docs [CONFIRMED] |
| Multiple outputs per request | Yes (SGLang) | `num_outputs_per_prompt: 1–10` | SGLang cookbook [SECONDARY summary] |

### 1.3 Parameter constraints

| Parameter | Value | Source |
|---|---|---|
| FPS | **24 fixed** | README, diffusers [CONFIRMED] |
| Duration | README/model card: **4–15 s**. diffusers: "**5 to 15 seconds**", with `num_frames` snapped **up** to the next `17*n + 5` | [CONFLICT — see below] |
| Frame rule | `num_frames = 17*n + 5`. ComfyUI Turbo doc: "a 5-second request is snapped to 124 frames (about 5.17 seconds)". Turbo script: `frames = max(5, round(duration*24))`, then rounded up to `17n+5` | diffusers, Turbo repo [CONFIRMED] |
| Valid frame counts (safe set) | 124, 141, 158, 175, 192, 209, 226, 243, 260, 277, 294, 311, 328, **345** (5.17 s – 14.375 s). 362 frames = 15.08 s, which may be rejected by diffusers' 15 s limit. Shorter counts (107 = 4.46 s, 90 = 3.75 s) are accepted by SGLang `seconds: 4` per the cookbook, but the diffusers check rejects <5 s | [Kino recommendation; UNVERIFIED edges] |
| Resolution | Short edge 768 by default. Width and height must be **multiples of 32**. diffusers config `canvas_short_edge: 768`, `canvas_max_pixels: 1032192` (= 1344×768). Native 16:9 canvas is 1344×768. Smaller canvases are allowed ("960x544 runs about 2.3x faster per step") | diffusers [CONFIRMED] |
| Aspect ratios | 21:9, 16:9, 4:3, 1:1, 3:4, 9:16 ("including but not limited to"). The Turbo `resolution_util.py` adds 9:21. SGLang `target.aspect_ratio: "auto"` follows the keyframe. With diffusers FL2VA, the canvas defaults to the first keyframe's aspect ratio (image is *stretched*) | README, Turbo, SGLang [CONFIRMED] |
| Turbo/megapixel ladder (16:9) | 0.2→608×352, 0.3→736×416, 0.4→864×480, 0.5→960×544, 0.6→1056×608, 0.7→1152×640, 0.8→1216×672, 0.9→1280×736, 0.98→1344×768, 1.0→1376×768, 1.2→1504×832, 1.5→1664×928, 1.8→1824×1024, 2.0→1920×1088; 21:9 @0.5 = 1088×480 | `resolution_util.py` [CONFIRMED] (above 0.98 MP exceeds `canvas_max_pixels` of the base model; do not expose) |
| Steps | Base: **50** default (SGLang request example, vLLM recipe, Turbo script "Ref2VA base model, 50 NFE"). The community quality floor is ~20–25 steps. diffusers: "`num_inference_steps` counts sigma grid points, the terminal 0 included, so it drives one model evaluation less" | [CONFIRMED / SECONDARY for floor] |
| Flow shift | video 12.0, audio 3.0 (SGLang fields `flow_shift`, `audio_flow_shift`) | configs [CONFIRMED] |
| Guidance | none (CFG-distilled) | [CONFIRMED] |
| Audio | 32 kHz stereo out. Audio refs are resampled to the audio VAE rate | [CONFIRMED] |
| Prompt length | **7,000 characters** max (vLLM recipe; MiniMax API "max 7000 characters per item") | [SECONDARY] |
| Input images (hosted API limits; use as Kino limits) | JPG/JPEG/PNG/WEBP/HEIC/HEIF, ≤30 MB, 256–5760 px per side, aspect 0.4–2.5 | MiniMax API docs [SECONDARY summary] |
| Input videos | MP4/MOV, ≤50 MB, 256–5760 px, aspect 0.4–2.5, 2–15 s each, total ≤15 s, ≤3 clips | API docs + README [CONFIRMED counts/durations] |
| Input audio | WAV/MP3, ≤15 MB, 2–15 s each, total ≤15 s, ≤3 clips | API docs + README |
| Reference image sizing | diffusers default: short edge forced to 2048 (`reference_image_short_edge: 2048`). The Turbo repo adds `--reference-resize-mode {match,max,diffusers}`; `match` is recommended for Turbo | [CONFIRMED] |
| Video reference fps | Resampled onto 24 fps by dropping/duplicating frames. Must pass the true fps (`MiniMaxH3VideoReference.from_file` preserves it; `load_video` does not) | diffusers [CONFIRMED] |

### 1.4 Official inference entry points

#### 1.4.1 SGLang (official deployment example in the README) [CONFIRMED]

```bash
# FL2VA server (t2va / i2va / l2va / fl2va)
sglang serve --model-path MiniMaxAI/MiniMax-H3 --num-gpus 4 --ulysses-degree 4 \
  --performance-mode speed --host 0.0.0.0 --port 30010 --model-variant fl2va
# Ref2VA server
sglang serve --model-path MiniMaxAI/MiniMax-H3 --num-gpus 4 --ulysses-degree 4 \
  --performance-mode speed --host 0.0.0.0 --port 30011 --model-variant ref2va
```

Additional flags from the SGLang cookbook [SECONDARY summary]:
- Parallelism: `--tp-size {1,2,4,8}`, `--ring-degree`, `--sp-degree`, `--nnodes/--node-rank/--dist-init-addr`
- Memory mode: `--performance-mode memory|speed`
- Offload: `--layerwise-offload-components dit,text_encoder,vae`, `--dit-layerwise-resident-layers N`, `--use-fsdp-inference true`
- Graphs and warm-up: `--enable-breakable-cuda-graph true`, `--warmup-resolutions 1344x768`
- Attention: `--attention-backend fa|sage_attn|aiter`
- Quantization: `--quantization fp8`
- Encoder: `--encoder-parallel auto|dp|fold|replicate`

HTTP API. Submit with `POST /v1/videos`, poll `GET /v1/videos/{id}` (status), then download `GET /v1/videos/{id}/content` (official scripts):

```jsonc
// T2VA (verbatim structure from scripts/readme/reproducible-768p-t2va-request.sh)
{ "task": "t2va",
  "prompt": "integrated_multimodal_description: [Shot 1] ... [Shot 2] At 00:04.500, the camera cuts to ...\noverall_soundscape: ...\nnon_diegetic_music: ...",
  "conditions": [],
  "target": { "short_edge": 768, "aspect_ratio": "16:9", "duration_seconds": 10 },
  "seed": 0 }

// FL2VA / I2VA (first frame). For last frame use frame_index -1; for both, two entries.
{ "task": "fl2va",
  "prompt": "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\nintegrated_multimodal_description: ...",
  "conditions": [ { "type": "image", "uri": "https://.../first.png", "role": "keyframe", "frame_index": 0 } ],
  "target": { "short_edge": 768, "aspect_ratio": "auto", "duration_seconds": 8 },
  "seed": 0 }

// Ref2VA (video + audio refs; verbatim structure from reproducible-768p-ref2va-request.sh)
{ "task": "ref2va",
  "prompt": "subject_definitions:\n<Subject 1> is ... in <Video 1>.\n<Video 1> is the source video for the editing task.\n<Audio 1> ...\n<Audio 2> is the voice timbre reference ...\n\nsummary:\n[video editing + audio reference + audio reuse] ...\n\nretention_analysis:\n...\n\ndetailed_description:\n...\n\noverall_soundscape:\n...\n\nnon_diegetic_music:\n...",
  "conditions": [
    { "type": "video", "uri": "https://.../src.mp4", "role": "reference" },
    { "type": "audio", "uri": "https://.../voice.mp3", "role": "reference" } ],
  "target": { "short_edge": 768, "aspect_ratio": "auto", "duration_seconds": 5 },
  "seed": 0 }
```

Other request fields (SGLang cookbook) [SECONDARY]:
- `"quality": "lossless"|"extra-high"|"high"`. `high` is audited Cache-DiT: 1.40× faster at SSIM 0.931.
- Sampling: `"num_inference_steps": 50`, `"flow_shift": 12.0`, `"audio_flow_shift": 3.0`.
- `"num_outputs_per_prompt": 1..10`.
- Conditions: `type` ∈ `image|audio|video|video_audio`, `role` ∈ `reference|keyframe`, `start_time_seconds` (trim point for video refs).
- The `uri` may be `http(s)://` or `file://`. A `file://` path is resolved by the **server** process, so it is fine for TEE-local files.

#### 1.4.2 diffusers (Modular only) [CONFIRMED]

Class names from `model_index.json`:
- Pipeline and blocks: `MiniMaxH3ModularPipeline` (blocks `MiniMaxH3Blocks`).
- Models: `MiniMaxH3Transformer3DModel` (both `transformer` and `transformer_ref`), `AutoencoderKLMiniMaxH3`, `AutoencoderKLMiniMaxH3Audio`.
- Scheduler: `MiniMaxH3Scheduler`.
- Encoder stack: `Qwen3VLForConditionalGeneration`, `Qwen2TokenizerFast`, `Qwen3VLProcessor`.
- Install: `pip install "git+https://github.com/huggingface/diffusers.git@minimax-h3"` (requirements.txt).

```python
import torch
from diffusers import ComponentsManager, ModularPipeline
from diffusers.utils import load_image
from diffusers.utils.export_utils import encode_video

manager = ComponentsManager()
manager.enable_auto_cpu_offload(device="cuda")
pipe = ModularPipeline.from_pretrained("MiniMaxAI/MiniMax-H3", components_manager=manager)
pipe.load_components(workflow="fl2va", dtype=torch.bfloat16)   # fetches transformer/ only
out = ["videos", "audio", "sampling_rate"]

# T2VA
r = pipe(prompt=prompt, num_frames=124, generator=torch.Generator().manual_seed(42), output=out)
# I2VA (first frame); add last_image=... for FL2VA; pass only last_image=... for L2VA
r = pipe(prompt=prompt, image=load_image("first.png"), num_frames=124,
         generator=torch.Generator().manual_seed(42), output=out)
encode_video(r["videos"][0], fps=24, output_path="out.mp4",
             audio=r["audio"][0], audio_sample_rate=r["sampling_rate"])
```

Other `__call__` inputs:
- Canvas and length: `height`, `width` (multiples of 32), `num_frames`.
- Keyframes: `image`, `last_image`.
- `references`.
- Noise and schedule: `generator`, `latents` with shape `(1, 24, T_lat, H_lat, W_lat)`, `audio_latents` with shape `(2, 32, N)`, `num_inference_steps`.
- `attention_kwargs`.
- `output_type` ∈ `pil|np|pt`.

Ref2VA:

```python
from diffusers.modular_pipelines.minimax_h3 import (
    MiniMaxH3AudioReference, MiniMaxH3ImageReference, MiniMaxH3VideoReference)
pipe = ModularPipeline.from_pretrained("MiniMaxAI/MiniMax-H3", workflow="ref2va", components_manager=manager)
pipe.load_components(dtype=torch.bfloat16)                      # fetches transformer_ref/ only
r = pipe(prompt="...",
         references=[MiniMaxH3ImageReference.from_file("subject.jpg"),
                     MiniMaxH3VideoReference.from_file("motion.mp4"),     # keeps fps + soundtrack
                     MiniMaxH3AudioReference.from_file("voice.wav")],
         num_frames=124,                                              # REQUIRED for ref2va
         output=["videos", "audio", "sampling_rate"])
# Reference constructors (in-memory): MiniMaxH3ImageReference(image), MiniMaxH3VideoReference(frames, fps=None, audio=None, sample_rate=None),
# MiniMaxH3AudioReference(audio, sample_rate=None)
```

Chaining is supported: a `t2va` output can be fed back as a `MiniMaxH3VideoReference(frames=..., audio=..., sample_rate=...)`. This is the documented path for **extend/continue** and "same character, new scene".

#### 1.4.3 vLLM-Omni [SECONDARY summary of https://recipes.vllm.ai/MiniMaxAI/MiniMax-H3]

```bash
vllm serve /path/to/MiniMax-H3 --omni --host 0.0.0.0 --port 8000 --trust-remote-code \
  --num-gpus 4 --usp 4 --ring 1 --vae-patch-parallel-size 4 --vae-parallel-mode tile --vae-use-tiling
curl -X POST http://127.0.0.1:8000/v1/videos/sync -F 'prompt=...' -F "width=1344" -F "height=768" \
  -F 'fps=24' -F 'num_inference_steps=50' -F 'flow_shift=12' -F 'seed=1101' \
  -F 'extra_params={"task":"t2va","duration":5.0,"audio_flow_shift":3.0}' -o out.mp4
```

For 2 RTX GPUs, the recipe uses `--task-type fl2va --tensor-parallel-size 2 --enable-distributed-layerwise-offload --dlo-resident-layers N`.

#### 1.4.4 ComfyUI [CONFIRMED node names from the Turbo repo; others SECONDARY]

- Core nodes are `MiniMaxH3ImageToVideo` (subgraph with `first_frame`, `last_frame`) and `MiniMaxH3ReferenceToVideo`. ComfyUI ≥0.31.0 is required.
- Weights: `Comfy-Org/MiniMax-H3`.
- Templates: `video_minimax_h3_t2v.json` and `video_minimax_h3_r2v.json` in Comfy-Org/workflow_templates.

#### 1.4.5 H3 Turbo (LightX2V / ModelTC) [CONFIRMED from https://github.com/ModelTC/Minimax-H3-Turbo]

| LoRA file (lightx2v/Minimax-h3-Turbo) | Tasks | Train res | Shift v/a | NFE (recommended) |
|---|---|---|---|---|
| `minimax_h3_fl2v_turbo_4step_v0.1.safetensors` | FL2VA/T2VA | 544p mixed AR | 12/3 | 4 |
| `minimax_h3_fl2v_turbo_8step_v1.0_bf16.safetensors` | FL2VA/T2VA | 544p mixed AR | 12/3 | 8 (or 4) |
| `minimax_h3_fl2v_turbo_4step_v1.0_768p_bf16.safetensors` | FL2VA/T2VA | 1344×768 | 6/3 | 4 |
| `minimax_h3_fl2v_turbo_8step_v1.0_768p_bf16.safetensors` | FL2VA/T2VA | 1344×768 | 6/3 | 8 (used by LightX2V Studio) |
| `minimax_h3_ref2v_turbo_4step_v0.1_bf16.safetensors` | Ref2VA | 544p mixed AR | 12/3 | 4 |

Additional files appear in the HF listing but not in the README table [UNVERIFIED usage]:
- `..._4step_v1.1_768p_{bf16,fp8}`, `..._4step_v1.2_768p_bf16`
- `minimax_h3_ref2v_turbo_8step_v1.0_768p_bf16`
- `lightx2v/Minimax-h3-Turbo-SLA`: a 4-step 768p FL2V LoRA with 85%-sparse SLA attention, "approximately 2.5× inference acceleration on an NVIDIA RTX 5090". Its LightX2V config uses `video_flow_shift 6.0`, `audio_flow_shift 3.0`, `h3_step_update: training_euler`.

```bash
# Single-GPU (diffusers + CPU offload), 8 NFE
python inference_minimax_h3.py --jobs-json examples/prompts_t2va_test.json \
  --lora-path minimax_h3_fl2v_turbo_8step_v1.0_bf16.safetensors --inference-steps 8 --output-dir out
# 768p 4-step
python inference_minimax_h3.py --jobs-json examples/prompts_t2va_test.json \
  --lora-path minimax_h3_fl2v_turbo_4step_v1.0_768p_bf16.safetensors --inference-steps 4 \
  --video-shift 6 --lora-alpha 128 --megapixels 1.0 --aspect-ratio 16:9 --output-dir out
# Ref2VA 4-step (script auto-selects transformer_ref)
python inference_minimax_h3.py --jobs-json examples/prompts_ref2va_test.json \
  --lora-path minimax_h3_ref2v_turbo_4step_v0.1_bf16.safetensors --inference-steps 4 --output-dir out
# 8-GPU FSDP2
torchrun --standalone --nproc-per-node=8 inference_minimax_h3.py --fsdp2 --jobs-json ... --lora-path ... --inference-steps 8
```

Full flag list of `inference_minimax_h3.py`: `--jobs-json`, `--model-id` (default `MiniMaxAI/MiniMax-H3`), `--lora-path`, `--lora-alpha` (default 8), `--lora-scale` (1.0), `--fuse-lora`, `--output-dir`, `--seed` (42), `--megapixels`, `--aspect-ratio`, `--num-frames/--frames`, `--inference-steps` (default 4), `--video-shift` (12.0), `--audio-shift` (3.0), `--reference-resize-mode {match,max,diffusers}` (default match), `--device`, `--memory-reserve-margin` (12GB), `--no-cpu-offload`, `--fsdp2`, `--attention-backend` (e.g. `_flash_3_hub`), `--dry-run`.

Jobs JSON fields: `duration`, `megapixels`, `aspect_ratio`, plus images or references.

Community note: "Audio degrades under Turbo; re-run final pass without" ([awesome-minimax-H3 perf guide](https://github.com/wildminder/awesome-minimax-H3/blob/main/guides/minimax-h3-performance.md)) [SECONDARY].

### 1.5 Hardware

- **Weight sizes** [CONFIRMED, diffusers docs]: the transformer is **61.7 GB** BF16 per partition, and the Qwen3-VL conditioner is **62.1 GB**. Loading both partitions pulls 2×61.7 GB.
- **Deployment recipes** [CONFIRMED, diffusers docs]:
  - 1×80 GB: `ComponentsManager` with `enable_auto_cpu_offload(..., memory_reserve_margin="12GB")` and `_flash_3_hub` on Hopper ("roughly 3x faster").
  - 2×80 GB: full BF16, with the conditioner on `cuda:1` and the rest on `cuda:0`.
  - 2×48 GB: the same split with int8.
  - 24–32 GB: torchao `Int8WeightOnlyConfig(version=2)` plus block-level group offload, which needs about 75 GB of host RAM.
  - 12–16 GB: additionally offload the VAE, use a small canvas.
- **Official SGLang:** 4 GPUs, Ulysses degree 4. The cookbook lists these profiles [SECONDARY]:
  - B200/B300: 8 GPUs resident, or FSDP on 4.
  - GB200/GB300: 4 GPUs resident.
  - H200: 4 GPUs resident, 4-GPU FSDP, or 16 GPUs cross-node.
  - H100: TP2 resident, or FSDP.
  - RTX 4090: offload, ~8.5 s/step plus 9.6 s decode.
  - MI300X/MI355X: 1–8 GPUs.
- **Measured speeds:**
  - vLLM 4×B300 FL2VA: **86.96 s client end-to-end** at 1248×768 for 8.7 s of video; the DiT is 79.1 s (88%) [SECONDARY].
  - 4×H200, 5 s, 50 steps, 1344×768: about 74 s ([Spheron](https://www.spheron.network/blog/deploy-minimax-h3-gpu-cloud/)) [SECONDARY].
  - RTX 4070 at 576×832, 124 frames: 20 steps = 272.97 s; LightX2V 4-step = 79.36 s (3.44×) with the same 10.66 GB peak VRAM [SECONDARY, perf guide].
- **Quantization:**
  - SGLang `--quantization fp8`, vLLM online FP8.
  - Community INT8 / NVFP4 / GGUF builds. FP8 plus Cache-DiT drifts from BF16: SSIM 0.881 / PSNR 26.6 dB [SECONDARY].
  - Community tip: keep the audio VAE in fp32 or A/V desyncs [SECONDARY].

### 1.6 Licensing notes that affect the UI (MiniMax H3 Community License, Aug 2 2026) [CONFIRMED verbatim]

- **Territory:** "Applicable Territory" means worldwide, excluding the **EU, UK, Republic of Korea and USA**. Section V.4: "You may not use, reproduce, modify, distribute, or display the MiniMax H3 Works or any of their Outputs or results outside the Applicable Territory." An application form for those regions is at https://platform.minimax.io/h3-license.
- **Attribution (mandatory):** Section IV.2: "You shall prominently display "MiniMax H3" on the user interface of commercial product or service that uses MiniMax H3 or MiniMax H3 Works."
- **Encouraged (III.3):** a "Powered by MiniMax H3" notice, an AI-generation identifier on output files, and a public blog post.
- **III.1:** "provide a copy of this Agreement to all such Third Parties who receive the MiniMax H3 Works or use your products or services related thereto". So link the LICENSE in the UI.
- **V.2:** bind every user to terms "at least as protective as" Section V and Exhibit A (AUP), and notify them.
- **V.5:** hosted services must run safeguards and keep a "reasonably accessible mechanism for reporting suspected violations", with takedown and repeat-violator suspension.
- **AUP item 12:** content disseminated publicly must be "clearly and prominently disclos[ed] ... machine-generated".
- **V.3:** no use of outputs to improve other AI models.
- **IV.1:** written authorization is required above **$20M** yearly revenue.
- **Turbo LoRAs:** Apache-2.0 on the files, but they are H3 derivatives, so the H3 license still governs use.

---

## 2. LTX-2.5 (Lightricks)

Primary sources:
- GitHub `Lightricks/LTX-2` README and `packages/ltx-pipelines/docs/*`: https://github.com/Lightricks/LTX-2
- `utils/args.py`, `utils/constants.py`, `utils/types.py`, and per-pipeline sources
- CHANGELOG 1.2.0 (2026-08-11, "Support for LTX 2.5") and 1.3.0 (2026-08-25)
- HF model card: https://huggingface.co/Lightricks/LTX-2.5 (gated; rendered page fetched)
- HF: https://huggingface.co/Lightricks/LTX-2.5-Diffusers
- diffusers LTX-2 docs: https://huggingface.co/docs/diffusers/main/en/api/pipelines/ltx2
- SGLang cookbook: https://lmsysorg.mintlify.app/cookbook/diffusion/LTX/LTX2.5
- vLLM recipe: https://recipes.vllm.ai/Lightricks/LTX-2.5-Diffusers
- LICENSE-2_x: https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x

### 2.1 Checkpoints [CONFIRMED from HF API listing + README]

`Lightricks/LTX-2.5` (split layout, "roughly 66 GiB" for the Quick Start set):

- **Transformers:**
  - `diffusion_models/ltx-2.5-22b-distilled-transformer-bf16.safetensors`, used by DistilledPipeline, DFRPipeline, ICLoraPipeline, DubItPipeline and Retake.
  - `…-distilled-transformer-nvfp4.safetensors`
  - `…-distilled-transformer-comfy-int8-convrot.safetensors`
  - `ltx-2.5-22b-dev-transformer-bf16.safetensors`: "the full model; used by the guided two-stage pipelines (TI2Vid, Keyframe, A2Vid)".
  - `…-dev-transformer-comfy-int8-convrot`
- **Text encoder:** `text_encoders/gemma4-12b-with-proj-ltx-2.5-bf16.safetensors` (version-checked as `gemma4-12b-ltx-v1`), plus a comfy-int8 variant.
- **Video VAE:** `vae/ltx-2.5-video-vae-bf16.safetensors` (diffusion decoder `NADiffusionDecoder`) or `vae/ltx-2.5-video-vae-conv-bf16.safetensors` (convolutional, lighter).
- **Audio VAE:** `vae/ltx-2.5-audio-vae-bf16.safetensors` (audio VAE plus vocoder).
- **Upscalers:** `latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors` and `…-temporal-upscaler-x2-bf16-1.0.safetensors`.
- **Distilled LoRA:** `loras/ltx-2.5-22b-distilled-lora-450-bf16.safetensors`, for stage 2 of the dev two-stage pipelines.
- **Duration head:** `model_patches/ltx-2.5-duration-head-bf16.safetensors`.
- **Separate repos:**
  - Detailing IC-LoRA for DFR: `Lightricks/LTX-2.5-22b-IC-LoRA-Pixel-Spatial-Upscaler` → `ltx-2.5-22b-ic-lora-pixel-spatial-upscaler-x2-1.0.safetensors`.
  - `Lightricks/LTX-2.5-Pre-Trained`.

`Lightricks/LTX-2.5-Diffusers` subfolders:
- `transformer/` (distilled, default) and `transformer_full/`
- `vae/` (conv) and `diffusion_decoder/`
- `latent_upsampler/` and `temporal_latent_upsampler/`
- `audio_vae/`, `vocoder/`, `connectors/`, `text_encoder/`, `tokenizer/`, `processor/`, `scheduler/`
- `duration_head/`
- **`prompt_enhancer/`** (a bundled 3-shard LLM)

2.5-native LoRAs on HF (all gated) [CONFIRMED to exist; purposes partly SECONDARY]:
- **IC-LoRAs:** Pixel-Spatial-Upscaler, Water-Simulation, Deblur, Decompression, Colorization, **Ingredients**, Day-To-Night, Clean-Plate
- **LoRA:** **Cinemagraph**
- **LTX-2.3 LoRAs** (Union-Control = Canny+Depth+Pose, Motion-Track-Control, In-Outpainting, Relight, HDR, DubIt, Foley-V2A, Instant-Shave, Cross-Eyed, …) and **LTX-2 19B camera LoRAs** (Dolly In/Out/Left/Right, Jib Up/Down, Static) also exist.

**Compatibility conflict [UNVERIFIED]:**
- The HF card says LoRAs "from LTX-2.3 generally run on 2.5 without modification, though validation is recommended".
- The GitHub README says "Files are not interchangeable between the two models, and a LoRA only works with the model it was trained on".
- An HF discussion is titled "IC-LoRA-Ingredients (2.3) doesnt work with ltx 2.5".
- The LTX-2 19B camera LoRAs are almost certainly incompatible with the 22B model.

**Kino policy:** only enable a 2.3 LoRA on 2.5 after our own golden tests.

### 2.2 Capability list

| Capability | Supported? | Entry point / notes | Source |
|---|---|---|---|
| Text-to-video (+audio) | Yes | DistilledPipeline, DFRPipeline, TI2VidTwoStages(HQ), TI2VidOneStage; diffusers `LTX2Pipeline` | [CONFIRMED] |
| Image-to-video (first frame) | Yes | `--image PATH 0 STRENGTH [CRF]`; diffusers `LTX2ImageToVideoPipeline(image=...)` | [CONFIRMED] |
| Image at any frame / last frame | Yes | `--image PATH FRAME_IDX STRENGTH`, repeatable; diffusers `LTX2ConditionPipeline` with `LTX2VideoCondition(frames=img, index=-1, strength=1.0)` | args.py, diffusers [CONFIRMED] |
| First+last frame (FLF2V) | Yes | Two `--image` conditions on Distilled (replacing latents) or **KeyframeInterpolationPipeline** ("guiding latents ... smoother transitions", dev model + distilled LoRA); diffusers LTX2ConditionPipeline (index 0 and -1) | [CONFIRMED] |
| Multi-keyframe | Yes | KeyframeInterpolationPipeline with N `--image` entries at chosen frame indices | [CONFIRMED] |
| Generated keyframe slots (extra internal keyframes for fast motion) | Yes (2.5+) | `--num-generated-keyframes N` on Distilled/TI2Vid (default 0); DFR derives its own | conditioning.md [CONFIRMED] |
| Reference-to-video (subject/character refs) | **Partial** | No native multi-reference. The **IC-LoRA "Ingredients"** (2.5 repo exists, gated) is the path; the HF discussion reports mixed results on 2.5 | [UNVERIFIED] |
| Video extension / continuation | **Partial** | No dedicated extend pipeline in `ltx-pipelines` (the `video_editing_arg_parser` docstring mentions "retake, extension, inpainting, sticker movement" but only Retake ships). diffusers `LTX2ConditionPipeline` accepts a video condition `LTX2VideoCondition(frames=video, index=0, strength=1.0)` plus a longer `num_frames`; this is the plausible extend path | [UNVERIFIED for 2.5 quality] |
| Retake (regenerate a time window, keep the rest) | Yes | `RetakePipeline` (`--video-path --start-time --end-time`); Python `regenerate_video` and `regenerate_audio` flags. Source must be 8k+1 frames and multiples of 32 px | [CONFIRMED] |
| Video-to-video / restyle / control | Yes | `ICLoraPipeline` (distilled only) `--video-conditioning PATH STRENGTH`, optional `--conditioning-attention-mask MASK STRENGTH`, `--skip-stage-2`, plus `--lora <ic-lora>` | [CONFIRMED] |
| Control signals | Via IC-LoRA | Union-Control (Canny+Depth+Pose, reference at 0.5× resolution, "ref0.5"), Motion-Track (colored spline trajectories). These are 2.3 LoRAs; 2.5 compatibility is unverified. 2.5-native effect IC-LoRAs: deblur, decompression, colorization, day-to-night, clean-plate, water-sim | HF cards [CONFIRMED 2.3; UNVERIFIED on 2.5] |
| Native audio | Yes | Joint A/V; audio VAE plus vocoder. **48 kHz stereo** per the vLLM/SGLang recipes. ltx-core's vocoder base default is 24 kHz with a bandwidth-extension stage | [SECONDARY for 48 kHz] |
| Speech / lip-sync from text | Yes | Put quoted dialogue in the prompt (README example); `modality_scale` (A2V/V2A guidance) "may increase lipsync quality" | [CONFIRMED] |
| Audio-to-video | Yes (dev model) | `A2VidPipelineTwoStage`: `--audio-path` (required), `--audio-start-time`, `--audio-max-duration` (mutually exclusive with `--num-frames`). "the original audio waveform is passed through and returned in the output" | pipelines.md [CONFIRMED] |
| Text-to-audio only | Yes | `T2AOneStagePipeline` (audio-only wav) | [CONFIRMED] |
| Dubbing (new words, same voice, matching lips) | Yes | `DubItPipeline` with `--reference-video`, `--reference-strength`; requires the DubIt IC-LoRA (2.3 repo) | [CONFIRMED pipeline; 2.5 LoRA compat UNVERIFIED] |
| Video-to-audio (Foley) | LoRA exists (2.3 `LoRA-Foley-V2A`, gated) | — | [UNVERIFIED] |
| Multi-shot | Yes, native in 2.5 | Written in **prose**, not a shot list. Name each cut ("A hard cut transitions to..."), re-establish framing, re-identify characters, state audio continuity. 2–4 shots recommended | HF card, fal guide [CONFIRMED feature; syntax SECONDARY] |
| Camera control | Prompt-based on 2.5 | Camera LoRAs exist only for LTX-2 19B. The hosted fal/LTX API has a camera enum (e.g. `dolly_in`, `jib_up`, `static`, `focus_shift`), but that is the hosted product, not open weights | [SECONDARY] |
| Upscaling / 2-stage | Yes | Latent spatial ×2 upscaler (Distilled, TI2Vid two-stage). **DFR**: generated keyframes plus a spatial detailing IC-LoRA pass up to 4K; `--spatial-upscalings {1,2}`; temporal `--temporal-upscalings {0,1,2}` gives 2×/4× fps | [CONFIRMED] |
| HDR / EXR | Yes | `--hdr {SRGB_LINEAR,ACESCG,ACESCCT}`; EXR stills/folders in; half EXR plus BT.2020/HLG master out; `HDRICLoraPipeline` | [CONFIRMED] |
| Looping | LoRA | `LTX-2.5-22b-LoRA-Cinemagraph`: "smooth, continuous-loop animations where only specific elements move" (2.3 card description) | [SECONDARY] |
| Negative prompt | Full (dev) model only | Default `DEFAULT_NEGATIVE_PROMPT` (long artifact list in constants.py). The distilled model runs unguided and vLLM "Distilled pipelines reject negative prompts" | [CONFIRMED] |
| Guidance | Full model | Video: `cfg 3.0, stg 1.0, rescale 0.7, modality 3.0, stg_blocks [28]`. Audio: `cfg 7.0, stg 1.0, rescale 0.7, modality 3.0` | constants.py (LTX_2_3/2_4 params) [CONFIRMED] |
| Prompt enhancer | **Yes, built-in** | CLI `--enhance-prompt` (+ `--prompt-enhancer-gemma-root`, `--enhance-static-cache`). diffusers `enable_prompt_enhancement=True`, `system_prompt=LTX2_5_T2V_DEFAULT_SYSTEM_PROMPT / LTX2_5_I2V_DEFAULT_SYSTEM_PROMPT`; enhancer model `google/gemma-4-E2B-it` (bundled as `prompt_enhancer/`) | [CONFIRMED] |
| Auto duration | Yes (2.5) | Duration head: omit `--num-frames`, or `--auto-duration MIN MAX` (default 1–20 s); diffusers `num_frames=None, min_seconds, max_seconds` | [CONFIRMED] |
| Seeds | Yes | `--seed` (default 10 in PipelineParams); diffusers `generator` | [CONFIRMED] |
| Custom LoRAs | Yes | `--lora PATH [STRENGTH]`, repeatable | [CONFIRMED] |

### 2.3 Parameter constraints

| Parameter | Value | Source |
|---|---|---|
| Frames | `num_frames = 8*k + 1` (1, 9, 17, …, 121, …). Default 121 (~5.04 s @24) | args.py [CONFIRMED] |
| Duration | Auto-duration default range **1–20 s**; diffusers `min_seconds=1.0, max_seconds=20.0`. Hosted fal product: Pro 6/8/10 s, Fast 6–20 s, A2V 2–20 s | types.py [CONFIRMED]; fal [SECONDARY] |
| Max frames (Kino) | 20 s @ 24 fps → 481 frames (8·60+1); @50 fps → 1001 frames (token budget and VRAM grow linearly and attention cost quadratically; SP `max_tokens` 32768 for distilled multi-GPU) | derived [UNVERIFIED long-clip quality] |
| Width/height | One-stage: divisible by **32**. Two-stage (Distilled, TI2Vid, DubIt): final size divisible by **64** (stage 1 runs at half). DFR: divisible by 64, or **128** with `--spatial-upscalings 2`. **4K = 3840×2176** (not 2160) | args.py, pipelines.md [CONFIRMED] |
| Defaults | PipelineParams stage-1 512×768, so two-stage output is 1024×1536. DFR default output 1024×1536 @ 24 fps. SGLang/vLLM defaults: one-stage 960×544, two-stage 1920×1088 | [CONFIRMED] |
| FPS | `--frame-rate` float, default 24.0. Hosted product exposes 24/25/48/50. DFR temporal rounds double playback fps (121 frames → 241 @48 → 481 @96); "The transformer independently snaps conditioning fps to 60 whenever playback fps is above 30". Dialogue advice: "stay at 24 or 25 fps" | pipelines.md [CONFIRMED]; fal [SECONDARY] |
| Steps | **Distilled:** fixed sigmas `DISTILLED_SIGMA_VALUES = [1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0]` (8 steps), stage 2 `[0.909375, 0.725, 0.421875, 0.0]` (3 steps). **Full/dev:** 30 (2.3/2.4+ default; README "Reduce inference steps from 40 to 20-30" with gradient estimation). **HQ (res_2s):** 15 | constants.py [CONFIRMED] |
| Guidance | Distilled: `guidance_scale=1.0`, `stg_scale=0.0`, `modality_scale=1.0` (diffusers card). Full: see §2.2 | [CONFIRMED] |
| Image conditioning | PNG/JPEG (SDR) or `.exr` (HDR). Re-compressed with H.264 CRF (default 18 for LTX-2.4+, 33 for older) to match training | constants.py [CONFIRMED] |
| Retake input | Source video frames 8k+1, dimensions multiples of 32, container fps used | retake.py [CONFIRMED] |
| A2V input | Any audio file readable by the pipeline; clipped to `num_frames/frame_rate`, or length derived from `--audio-max-duration` and snapped to 8k+1 | pipelines.md [CONFIRMED] |
| Prompt length | diffusers `encode_prompt(max_sequence_length=1024)` (tokens). README guidance: "Keep within 200 words" | [CONFIRMED] |
| Audio | 48 kHz stereo | [SECONDARY] |

### 2.4 Official inference entry points

#### 2.4.1 `ltx-pipelines` CLI (official reference implementation) [CONFIRMED]

Install: `git clone https://github.com/Lightricks/LTX-2 && cd LTX-2 && uv sync --extra natten`.

```bash
M=models/ltx-2.5
COMMON="--transformer-path $M/diffusion_models/ltx-2.5-22b-distilled-transformer-bf16.safetensors \
 --text-encoder-path $M/text_encoders/gemma4-12b-with-proj-ltx-2.5-bf16.safetensors \
 --video-vae-path $M/vae/ltx-2.5-video-vae-bf16.safetensors --audio-vae-path $M/vae/ltx-2.5-audio-vae-bf16.safetensors"

# T2V (distilled, fastest). Add --image first.png 0 1.0 for I2V; add --image last.png 120 1.0 for FLF.
uv run python -m ltx_pipelines.distilled $COMMON \
  --spatial-upsampler-path $M/latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors \
  --num-frames 121 --seed 42 --output-path out.mp4 --prompt "..."
#   optional: --height/--width (÷64) --frame-rate 24 --enhance-prompt --auto-duration 2 10
#             --duration-head-path $M/model_patches/ltx-2.5-duration-head-bf16.safetensors
#             --num-generated-keyframes N --lora path strength --quantization fp8-cast --offload cpu

# DFR (production quality; up to 4K and 2x/4x fps)
uv run python -m ltx_pipelines.dfr_pipeline $COMMON \
  --detailing-lora $M/loras/ltx-2.5-22b-ic-lora-pixel-spatial-upscaler-x2-1.0.safetensors \
  --spatial-upsampler-path $M/latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors \
  --temporal-upsampler-path $M/latent_upscale_models/ltx-2.5-latent-temporal-upscaler-x2-bf16-1.0.safetensors \
  --temporal-upscalings 1 --width 3840 --height 2176 --num-frames 121 --output-path out.mp4 --prompt "..."
#   (--spatial-upscalings 2 for the tiled 4K epilogue; multi-GPU: python -m ltx_pipelines.dfr_mgpu, same flags)

# Guided two-stage (full/dev model + distilled LoRA in stage 2) with negative prompt and CFG/STG
uv run python -m ltx_pipelines.ti2vid_two_stages \
  --transformer-path $M/diffusion_models/ltx-2.5-22b-dev-transformer-bf16.safetensors \
  --text-encoder-path ... --video-vae-path ... --audio-vae-path ... \
  --distilled-lora $M/loras/ltx-2.5-22b-distilled-lora-450-bf16.safetensors 1.0 \
  --spatial-upsampler-path ... --num-inference-steps 30 --negative-prompt "..." \
  --video-cfg-guidance-scale 3.0 --video-stg-guidance-scale 1.0 --video-rescale-scale 0.7 --a2v-guidance-scale 3.0 \
  --audio-cfg-guidance-scale 7.0 --audio-stg-guidance-scale 1.0 --v2a-guidance-scale 3.0 --output-path out.mp4 --prompt "..."
#   HQ variant: ltx_pipelines.ti2vid_two_stages_hq (+ --distilled-lora-strength-stage-1 0.25 --distilled-lora-strength-stage-2 0.5)

# Keyframe interpolation (dev model; same flags as two-stage + N images)
uv run python -m ltx_pipelines.keyframe_interpolation <two-stage flags> \
  --image k0.png 0 1.0 --image k1.png 48 1.0 --image k2.png 120 1.0

# Audio-to-video (dev model)
uv run python -m ltx_pipelines.a2vid_two_stage <two-stage flags> --audio-path speech.wav --audio-start-time 0 --audio-max-duration 8

# Retake a time region (distilled)
uv run python -m ltx_pipelines.retake $COMMON --video-path src.mp4 --start-time 2.0 --end-time 4.0 --output-path out.mp4 --prompt "..."

# IC-LoRA video-to-video / control (distilled only)
uv run python -m ltx_pipelines.ic_lora $COMMON --spatial-upsampler-path ... \
  --lora ltx-2.3-22b-ic-lora-union-control-ref0.5.safetensors 1.0 \
  --video-conditioning depth.mp4 1.0 [--conditioning-attention-mask mask.mp4 0.5] [--skip-stage-2] --prompt "..."

# Dub-It (distilled + one DubIt IC-LoRA; frame count/fps from the reference)
uv run python -m ltx_pipelines.dubit $COMMON --spatial-upsampler-path ... --lora dubit.safetensors \
  --reference-video speaker.mp4 --reference-strength 1.0 --prompt "..."

# Text-to-audio
uv run python -m ltx_pipelines.t2a_one_stage --transformer-path <dev> ... --num-frames 121 --frame-rate 24 --prompt "..."
```

Python API constructors and calls [CONFIRMED signatures]:
- `DistilledPipeline(model_paths, spatial_upsampler_path, loras, device=None, quantization=None, ..., offload_mode=OffloadMode.NONE, prompt_enhancer_gemma_root=None, diffvae_optimization=DiffVAEMode.CHUNKED_EAGER)`, called as `__call__(prompt, seed, height, width, frame_rate, images, num_frames=DEFAULT_AUTO_DURATION, ..., enhance_prompt=False, color_space=None, generated_keyframes=0)`.
- `images` is a list of `ImageConditioningInput(path, frame_idx, strength, crf)`. This is positional usage in `dfr_pipeline.py`; the field names are inferred.
- Since 1.3.0, pipelines return `PipelineOutput` (`.video`, `.audio`, `.keyframes`, `.video_latent`).
- `RetakePipeline.__call__(video_path, prompt, start_time, end_time, seed, fps=None, negative_prompt="", num_inference_steps=40, video_guider_params=None, audio_guider_params=None, regenerate_video=True, regenerate_audio=True, enhance_prompt=False, ..., sigmas=None)`.
- `A2VidPipelineTwoStage.__call__(prompt, negative_prompt, seed, height, width, num_frames, frame_rate, num_inference_steps, video_guider_params, images, audio_path, audio_start_time=0.0, audio_max_duration=None, ...)`.
- `ICLoraPipeline.__call__(prompt, seed, height, width, num_frames, frame_rate, images, ..., conditioning_attention_strength=1.0, conditioning_attention_mask=None)`.

#### 2.4.2 diffusers [CONFIRMED from the diffusers docs and the LTX-2.5-Diffusers card]

Classes:
- Pipelines: `LTX2Pipeline`, `LTX2ImageToVideoPipeline`, `LTX2ConditionPipeline` (+ `LTX2VideoCondition(frames, index, strength)`), `LTX2LatentUpsamplePipeline` (+ `LTX2LatentUpsamplerModel`), `LTX2VideoDiffusionDecodePipeline` (+ `LTX2VideoDiffusionDecoderModel`, `LTX2VideoVaeNeighborhoodNattenProcessor`), `LTX2DFRPipeline`, `LTX2DFRTemporalRefinePipeline`, and `ModularPipeline`.
- Transformer: `LTX2VideoTransformer3DModel`.
- Constants in `diffusers.pipelines.ltx2.utils`: `DISTILLED_SIGMA_VALUES`, `STAGE_2_DISTILLED_SIGMA_VALUES`, `DEFAULT_NEGATIVE_PROMPT`, `LTX2_5_T2V_DEFAULT_SYSTEM_PROMPT`, `LTX2_5_I2V_DEFAULT_SYSTEM_PROMPT`.

```python
import torch
from diffusers import LTX2Pipeline, LTX2LatentUpsamplePipeline
from diffusers.pipelines.ltx2.latent_upsampler import LTX2LatentUpsamplerModel
from diffusers.pipelines.ltx2.utils import DEFAULT_NEGATIVE_PROMPT, DISTILLED_SIGMA_VALUES, STAGE_2_DISTILLED_SIGMA_VALUES
from diffusers.utils import encode_video
MODEL_ID = "Lightricks/LTX-2.5-Diffusers"

pipe = LTX2Pipeline.from_pretrained(MODEL_ID, dtype=torch.bfloat16); pipe.enable_model_cpu_offload(); pipe.vae.enable_tiling()
ups = LTX2LatentUpsamplePipeline(vae=pipe.vae, latent_upsampler=LTX2LatentUpsamplerModel.from_pretrained(
        MODEL_ID, subfolder="latent_upsampler", dtype=torch.bfloat16).to("cuda"))
g = torch.Generator("cuda").manual_seed(42)
shared = dict(prompt="...", negative_prompt=DEFAULT_NEGATIVE_PROMPT, frame_rate=24.0, guidance_scale=1.0,
              audio_guidance_scale=1.0, stg_scale=0.0, audio_stg_scale=0.0, modality_scale=1.0,
              audio_modality_scale=1.0, generator=g, return_dict=False)
lat, alat = pipe(height=544, width=960, num_frames=121, sigmas=DISTILLED_SIGMA_VALUES, output_type="latent", **shared)
up = ups(latents=lat, output_type="latent", return_dict=False)[0]
video, audio = pipe(num_frames=121, sigmas=STAGE_2_DISTILLED_SIGMA_VALUES, latents=up, audio_latents=alat,
                    noise_scale=STAGE_2_DISTILLED_SIGMA_VALUES[0], output_type="np", **shared)
encode_video(video[0], fps=24, output_path="out.mp4", audio=audio[0].float().cpu(),
             audio_sample_rate=pipe.vocoder.config.output_sampling_rate)
```

The card warns: "Distilled inference is driven by an explicit sigma schedule, not a step count". Passing `num_inference_steps` instead silently degrades quality.

Usage notes:
- **Full model:** load `transformer_full` via `LTX2VideoTransformer3DModel.from_pretrained(MODEL_ID, subfolder="transformer_full")`, and set `pipe.scheduler = FlowMatchEulerDiscreteScheduler.from_config(pipe.scheduler.config, use_dynamic_shifting=True, shift_terminal=0.1)`. Then `num_inference_steps=30`, guidance per §2.2, `use_cross_timestep=True`.
- **FLF / keyframes / video conditions:**
  ```python
  pipe = LTX2ConditionPipeline.from_pretrained(...)
  pipe(conditions=[LTX2VideoCondition(frames=first, index=0, strength=1.0),
                   LTX2VideoCondition(frames=last, index=-1, strength=1.0)], ...)
  ```
  A video can also be a condition (`frames=load_video(...)`).
- **Prompt enhancement:** `enable_prompt_enhancement=True` (loads `pipe.prompt_enhancer`, Gemma-4-E2B-it).
- **Auto duration:** `num_frames=None, min_seconds=2.0, max_seconds=10.0`.
- **`__call__` defaults (LTX2Pipeline):** `height=512, width=768, num_frames=None, min_seconds=1.0, max_seconds=20.0, frame_rate=24.0, num_inference_steps=30, guidance_scale=3.0, stg_scale=1.0, modality_scale=3.0, guidance_rescale=0.7, audio_guidance_scale=7.0, ..., spatio_temporal_guidance_blocks=[28], noise_scale=0.0, enable_prompt_enhancement=False, system_prompt=None`. `LTX2ImageToVideoPipeline` adds `image` and `image_crf`.

#### 2.4.3 SGLang / vLLM-Omni / ComfyUI [SECONDARY summaries]

- **SGLang:** `sglang serve --model-path Lightricks/LTX-2.5-Diffusers --pipeline-class-name LTX2Pipeline`. Two-stage via `--pipeline-class-name LTX2TwoStagePipeline --height 1088 --width 1920`. FP8: "Reduces transformer load from 35.37 GB to 18.11 GB with unchanged denoising speed". CFG parallel only works with `--model-variant dev`. Duration head and diffusion decoder are "optional and disabled by default".
- **vLLM-Omni:** `vllm serve Lightricks/LTX-2.5-Diffusers --omni --model-class-name LTX2DistilledTwoStagePipeline`. Classes: `LTX2Pipeline` (30 steps, 960×544), `LTX2TwoStagePipeline` (30+3, 1920×1088), `LTX2DistilledOneStagePipeline` (8), `LTX2DistilledTwoStagePipeline` (8+3). T2V and first-frame I2V only. `--quantization fp8`.
- **ComfyUI:** native T2V / I2V / FLF2V templates using `ltx-2.5-22b-distilled-transformer-comfy-int8-convrot`, `gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot`, and an optional prompt enhancer `gemma4_e2b_it_int8_convrot` ([Comfy docs](https://docs.comfy.org/tutorials/video/ltx/ltx-2-5)). IC-LoRA nodes: `LTXICLoRALoaderModelOnly`, `LTXAddVideoICLoRAGuide`.

### 2.5 Hardware

- **Official:**
  - The Quick Start bundle is about 66 GiB.
  - Memory flags: `--quantization fp8-cast` (BF16 checkpoints, downcast on the fly), `fp8-scaled-mm` (FP8 checkpoints, Hopper+), `nvfp4-cast` / `nvfp4-prequant` (Blackwell, `ltx-kernels`), and `--offload {none,cpu,disk}`.
  - Attention: FlashAttention 3 (Hopper) or FA4 `flash-attn-4==4.0.0b9` (B200).
  - DiffVAE decode presets: `chunked_eager` (default, lowest VRAM), `chunked_compile`, `combined_compile` (fastest warm, about 2× VRAM), `blackwell_dsl` (B200).
  - DFR: "decode is usually the memory cliff".
- **Multi-GPU (official):**
  - `distilled_mgpu`, `ti2vid_two_stages_mgpu`, `ti2vid_two_stages_hq_mgpu`, `dfr_mgpu`.
  - Sequence parallelism is "numerically equivalent to single-GPU inference". It uses the all2all kernel from `ltx-kernels` and requires `num_heads` divisible by world size.
  - Token sizes: `sp_max_tokens=32768` for distilled 1024×1536×121 (about 24k tokens); DFR 4K about 514k (`524288`).
  - Also available: tiled data parallel, a distributed VAE decoder, and distributed Gemma.
- **Sizing [SECONDARY, Runpod]:** 16–24 GB with quantized variants only; 32–48 GB with int8; **80–96 GB for the full BF16 pipeline** (H100, RTX PRO 6000); 141 GB+ for 4K HDR.
- **Speed [SECONDARY, vendor]:** a 10 s 24 fps clip in **6.8 s on 2× GB200**; the LTX API at 1080p takes 23.7 s end-to-end.

### 2.6 Licensing notes that affect the UI (LTX-2.x Community License) [CONFIRMED from LICENSE-2_x]

- **Revenue threshold (2.1):** entities with "annual revenues of at least $10,000,000 (the "Commercial Entities") are required to obtain a paid license". Licensing contact: ltxv-licensing@lightricks.com. Revenue is measured "across the whole entity, including subsidiaries and affiliates" (HF card).
- **Non-commercial carve-out (2.2):** this exemption excludes use "in direct interactions with or that has impact on end users".
- **Outputs (5):** "Licensor claims no rights in the Output you generate".
- **AI regulations (6):** comply with the EU AI Act and the California AI Transparency Act. Operators "shall not remove, disable, alter, or circumvent any ... disclosures, metadata, watermarking, content provenance, latent disclosure" features. **Kino's output pipeline must preserve any embedded provenance/metadata and show AI-generated labeling.**
- **Modified files (3.3):** must "carry prominent notices". The Attachment A use restrictions apply to users, so pass them through in the Kino ToS.
- **No mandatory "LTX" branding** was found, unlike H3. Showing "LTX-2.5 by Lightricks" in the model picker is good practice [my recommendation].

---

## 3. Unified capability matrix

Legend: ✅ supported natively / officially · 🟡 partial, prompt-only, LoRA-dependent or unverified · ❌ not available with open weights.

"LTX-2.5 full/pro" here means the open-weights **dev transformer** pipelines (TI2Vid two-stage, Keyframe, A2Vid, T2A) **plus DFR** (production quality; DFR itself uses the distilled transformer). The hosted "LTX-2.5 Pro" API is a different product.

| Feature | H3 FL2VA | H3 Ref2VA | H3 Turbo (LoRA) | LTX-2.5 distilled | LTX-2.5 full / DFR |
|---|---|---|---|---|---|
| Text-to-video | ✅ | ❌ (needs ≥1 ref) | ✅ (FL2VA LoRAs) | ✅ | ✅ |
| Image-to-video (first frame) | ✅ | 🟡 (Picture as "keyframe completion" via prompt) | ✅ | ✅ | ✅ |
| Last frame only | ✅ (`frame_index -1`) | 🟡 | ✅ | ✅ (`--image p N-1 s`) | ✅ |
| First + last frame | ✅ | 🟡 | ✅ | ✅ (latent replace) | ✅ (KeyframeInterpolation, guiding latents) |
| >2 keyframes at arbitrary times | ❌ | 🟡 (storyboard via prompt) | ❌ | ✅ | ✅ |
| Multi-reference (subject/char/style/scene) | ❌ | ✅ ≤9 img | ✅ (Ref2VA 4-step v0.1) | 🟡 (Ingredients IC-LoRA, gated/unverified) | 🟡 |
| Video reference (motion/camera) | ❌ | ✅ ≤3 clips | ✅ | 🟡 (IC-LoRA control video) | 🟡 |
| Audio reference (voice timbre / music) | ❌ | ✅ ≤3 clips | 🟡 | ❌ (DubIt uses ref video audio) | ❌ |
| Video extension / continuation | ❌ | ✅ (task "video continuation") | 🟡 (untested) | 🟡 (diffusers video condition; unverified) | 🟡 |
| Video edit / restyle (V2V) | ❌ | ✅ (task "video editing") | 🟡 | ✅ (ICLoraPipeline) | ✅ |
| Retake time region | ❌ | 🟡 (edit via prompt) | ❌ | ✅ (RetakePipeline) | ✅ (Retake, full + CFG) |
| Depth / pose / canny control | ❌ | ❌ | ❌ | 🟡 (Union-Control 2.3 IC-LoRA) | 🟡 |
| Motion-trajectory control | ❌ | ❌ | ❌ | 🟡 (Motion-Track 2.3) | 🟡 |
| Native audio | ✅ 32 kHz st | ✅ | ✅ (quality lower) | ✅ 48 kHz st* | ✅ |
| Dialogue / lip-sync from text | ✅ (`<d>` tags, 11 langs) | ✅ | ✅ | ✅ | ✅ |
| Audio-to-video (given soundtrack) | ❌ | ✅ (`fully_copy`) | 🟡 | ❌ | ✅ (A2Vid) |
| Re-dub existing video | ❌ | ✅ (edit + audio ref) | 🟡 | ✅ (DubIt, 2.3 LoRA) | ✅ |
| Text-to-audio only | ❌ | ❌ | ❌ | ❌ | ✅ (T2A) |
| Multi-shot | ✅ `[Shot N] At mm:ss.sss` | ✅ | ✅ | ✅ (prose cuts, 2–4) | ✅ |
| Camera control | 🟡 prompt | 🟡 prompt + video ref | 🟡 | 🟡 prompt (no 2.5 camera LoRAs) | 🟡 |
| Upscale / 2-stage | ❌ (2K closed) | ❌ | ❌ | ✅ latent ×2 | ✅ DFR to 4K |
| Frame interpolation (fps ×2/×4) | ❌ | ❌ | ❌ | ❌ | ✅ (DFR `--temporal-upscalings`) |
| HDR / EXR | ❌ | ❌ | ❌ | ✅ | ✅ |
| Looping | 🟡 (same first/last) | ❌ | 🟡 | 🟡 (Cinemagraph LoRA) | 🟡 |
| Negative prompt | ❌ | ❌ | ❌ | ❌ | ✅ (dev pipelines) |
| Guidance scales | ❌ | ❌ | ❌ | ❌ | ✅ (CFG/STG/modality/rescale, video+audio) |
| Prompt enhancer | 🟡 (hosted Context-IR only; open skill + own LLM) | 🟡 | 🟡 | ✅ built-in | ✅ |
| Auto duration | ❌ | ❌ | ❌ | ✅ | ✅ |
| Seed | ✅ | ✅ | ✅ | ✅ | ✅ |
| Max res (open weights) | 1344×768 (≤1,032,192 px) | same | 544p or 768p | 1920×1088 typical; 4K possible | 3840×2176 (DFR) |
| Duration | 4/5–15 s | 5–15 s (`num_frames` required) | same | 1–20 s | 1–20 s |
| FPS | 24 | 24 | 24 | any float (24/25/48/50) | + 48/96 via DFR |
| Steps | 50 | 50 | 4 / 8 | 8 + 3 (fixed sigmas) | 30 (+3), HQ 15; DFR distilled schedule |
| Min GPUs (BF16, no offload) | 2×80 GB (split); 4× official | same | same (+LoRA) | 1×80–96 GB | 1×80–141 GB (4K DFR: 141 GB+ or SP) |

\* 48 kHz per SGLang/vLLM recipes [SECONDARY].

---

## 4. Proposed unified request schema (Kino `/v1/generations`)

Design principles:
1. One `mode` enum covers every capability.
2. Media is referenced by Kino asset IDs, which the TEE resolves to local `file://` paths. This is critical, because SGLang resolves `uri` on the server side.
3. Model-specific knobs live under `advanced` and are validated per `model`.
4. The server snaps durations to legal frame counts and returns the actual `num_frames`/`duration`.

```jsonc
{
  "model": "minimax-h3" | "minimax-h3-turbo" | "ltx-2.5-distilled" | "ltx-2.5-dfr" | "ltx-2.5-full",
  "mode": "t2v" | "i2v" | "l2v" | "flf2v" | "keyframes" | "ref2v" | "v2v_edit" | "extend" |
          "a2v" | "retake" | "control" | "dub" | "t2a",
  "prompt": "string",
  "negative_prompt": "string | null",               // ltx-2.5-full only
  "prompt_enhance": { "enabled": false, "engine": "native" | "kino_llm", "style_guide": "h3_base" | "h3_ref" | "ltx" },
  "output": {
    "aspect_ratio": "21:9" | "16:9" | "4:3" | "1:1" | "3:4" | "9:16" | "9:21" | "auto",
    "resolution": "480p" | "544p" | "720p" | "768p" | "1080p" | "1440p" | "2160p",  // or explicit:
    "width": 1344, "height": 768,
    "duration_seconds": 5.0,                         // snapped; mutually exclusive with num_frames / auto_duration
    "num_frames": null,
    "auto_duration": { "min_seconds": 1, "max_seconds": 20 },   // ltx only
    "fps": 24,
    "audio": true,                                   // false => strip audio in post (both models always generate)
    "num_outputs": 1
  },
  "inputs": {
    "keyframes": [ { "asset_id": "img_1", "position": "first" | "last" | { "frame_index": 48 } | { "time_seconds": 2.0 },
                     "strength": 1.0 } ],
    "references": [ { "asset_id": "img_2", "type": "image" | "video" | "video_audio" | "audio",
                      "start_time_seconds": 0, "role_hint": "subject" | "style" | "scene" | "motion" | "voice" | "music" | "source_edit" | "source_continue" } ],
    "source_video": { "asset_id": "vid_1", "start_time_seconds": 2.0, "end_time_seconds": 4.0,
                      "regenerate_video": true, "regenerate_audio": true },     // retake / extend / v2v / dub
    "source_audio": { "asset_id": "aud_1", "start_time_seconds": 0, "max_duration_seconds": 8 },   // a2v
    "control": { "type": "union" | "depth" | "pose" | "canny" | "motion_track" | "restyle",
                 "asset_id": "vid_ctrl", "strength": 1.0, "mask_asset_id": null, "mask_strength": 1.0 }
  },
  "loras": [ { "id": "ltx-2.5-cinemagraph", "strength": 1.0 } ],              // allow-listed IDs only
  "quality": { "tier": "draft" | "standard" | "production",                    // maps to steps/pipeline
               "upscale": "none" | "latent_x2" | "dfr", "spatial_upscalings": 1, "temporal_upscalings": 0,
               "hdr": null | "SRGB_LINEAR" | "ACESCG" | "ACESCCT" },
  "seed": 42,
  "advanced": {
    "num_inference_steps": 50,                       // h3 / ltx-full only
    "flow_shift": 12.0, "audio_flow_shift": 3.0,     // h3 only
    "turbo": { "steps": 4 | 8, "lora_version": "fl2v_8step_v1.0_768p" },     // h3-turbo only
    "reference_resize_mode": "match" | "max" | "diffusers",                  // h3 ref2v
    "guidance": { "video_cfg": 3.0, "video_stg": 1.0, "video_rescale": 0.7, "a2v": 3.0,
                  "audio_cfg": 7.0, "audio_stg": 1.0, "audio_rescale": 0.7, "v2a": 3.0, "stg_blocks": [28] },  // ltx-full only
    "num_generated_keyframes": 0                     // ltx distilled/full (not dfr)
  }
}
```

### 4.1 Per-model validation rules

**MiniMax H3 (`minimax-h3`, `minimax-h3-turbo`)**

- **Allowed modes:**
  - Base: `t2v`, `i2v`, `l2v`, `flf2v` (FL2VA partition).
  - Reference: `ref2v`, `v2v_edit`, `extend`, `a2v` (Ref2VA partition), and `dub` (Ref2VA edit + voice ref).
  - Turbo: `t2v`, `i2v`, `l2v`, `flf2v`, and `ref2v` (4-step only) until the others are tested.
  - Rejected: `keyframes` (>2), `retake`, `control`, `t2a`.
- **Keyframes:** 0–2; positions only `first` (frame_index 0) or `last` (−1); `strength` must be 1.0 or omitted.
- **References:**
  - ≤9 images, ≤3 video/video_audio, ≤3 audio, ≤12 total.
  - Each video/audio 2–15 s, with a total ≤15 s per modality.
  - Require ≥1 image or video when any audio is present (diffusers rule).
  - Order is semantic, so preserve the user's order and expose it in the UI as `<Picture n>/<Video n>/<Audio n>` chips.
- **Limits:**
  - Duration 5–15 s (accept 4 s only on the SGLang path after a golden test).
  - Snap `num_frames` up to `17n+5` and cap at 345 frames unless 362 is verified.
  - `fps` must be 24.
  - `width`/`height` multiples of 32; `width*height ≤ 1,032,192`; the default short edge is 768.
  - Turbo 544p LoRAs expect about 0.5 MP; 768p LoRAs expect 1344×768 with video shift 6.
- **Always reject:** `negative_prompt`, `advanced.guidance`, `auto_duration`, `upscale != none`, `hdr`, and `loras` other than allow-listed Turbo LoRAs.
- **Prompt:**
  - ≤7,000 characters.
  - If `prompt_enhance.enabled`, run a **Kino-internal LLM inside the TEE** with the `h3-prompt-writing` guides (base-en/ref-en). Never call H3-Context-IR, which is off-TEE.
  - Base modes must produce `integrated_multimodal_description` / `overall_soundscape` / `non_diegetic_music`.
  - Ref modes must produce the six sections, with the first-frame / last-frame instruction line when applicable.
- **Geo and legal gating:**
  - Reject requests where the user's jurisdiction is in {US, EU, UK, KR} unless MiniMax authorization is on file.
  - Show "MiniMax H3" branding in the response metadata (`attribution: "MiniMax H3"`) so the UI can render it.

**LTX-2.5 (`ltx-2.5-distilled`, `ltx-2.5-dfr`, `ltx-2.5-full`)**

- **Allowed modes:**
  - distilled: `t2v`, `i2v`, `l2v`, `flf2v`, `keyframes`, `retake`, `control`, `dub`, `extend` (experimental).
  - dfr: `t2v`, `i2v` (+keyframes via `--image`).
  - full: `t2v`, `i2v`, `flf2v`, `keyframes`, `a2v`, `retake`, `t2a`.
  - `ref2v`: only if the Ingredients IC-LoRA passes validation. `v2v_edit` maps to `control` with a restyle IC-LoRA.
- **Frames and fps:**
  - `num_frames = 8k+1`; snap to the nearest ≤ value; duration 1–20 s.
  - `fps` ∈ {24, 25, 48, 50} (UI default 24). Warn when dialogue is combined with fps > 25.
- **Dimensions:**
  - One-stage: multiples of 32.
  - distilled/full two-stage: final size multiples of 64.
  - dfr: multiples of 64, or 128 when `spatial_upscalings=2`; 4K must be 3840×2176.
  - Cap total tokens per GPU class, e.g. deny 4K on anything below 141 GB or without SP.
- **Keyframes:** `frame_index` must be in `[0, num_frames-1]`; `strength` ∈ (0, 1].
- **Retake:**
  - Source frames must be 8k+1 and dimensions multiples of 32. Pre-transcode or trim on ingest, and tell the user.
  - `0 ≤ start < end ≤ source_duration`.
- **A2V:** `num_frames` and `source_audio.max_duration_seconds` are mutually exclusive.
- **Guidance and prompts:**
  - `negative_prompt` and `advanced.guidance` only for `ltx-2.5-full`. The distilled model and DFR force guidance 1.0 and fixed sigmas, and reject `num_inference_steps`.
  - `prompt_enhance.engine="native"` maps to `--enhance-prompt` / `enable_prompt_enhancement=True`.
  - Prompt ≤1,024 tokens (the UI can soft-warn above 200 words).
- **LoRAs:** allow-list only, with IC-LoRA/mode pairing enforced (e.g. `dub` requires the DubIt LoRA). 2.3 LoRAs stay behind a feature flag.
- **Legal:** preserve output metadata and provenance; add "AI-generated" labeling; revenue-threshold check for enterprise tenants.

### 4.2 Adapter mapping (schema → official call)

| Kino mode | H3 adapter (SGLang `/v1/videos`) | LTX adapter (`ltx_pipelines`) |
|---|---|---|
| t2v | `task:"t2va"`, `conditions:[]` | `DistilledPipeline(... images=[])` / `DFRPipeline` / `TI2VidTwoStagesPipeline` |
| i2v | `task:"fl2va"`, image keyframe `frame_index:0` | `images=[ImageConditioningInput(path,0,strength,crf)]` |
| l2v | image keyframe `frame_index:-1` | `images=[(path, num_frames-1, s)]` |
| flf2v | two keyframes 0 / −1 | Distilled (2 images) or `KeyframeInterpolationPipeline` |
| keyframes | reject | `KeyframeInterpolationPipeline(images=[...])` |
| ref2v | `task:"ref2va"`, `conditions[] role:"reference"` in order | IC-LoRA Ingredients (flagged) |
| v2v_edit / extend | `ref2va` + `video`/`video_audio` ref + prompt task tag `[video editing]` / `[video continuation]` | `ICLoraPipeline(video_conditioning)` / diffusers `LTX2ConditionPipeline` video condition (extend) |
| a2v | `ref2va` + image ref + audio ref marked `fully_copy` in prompt | `A2VidPipelineTwoStage(audio_path, audio_start_time, audio_max_duration)` |
| retake | reject | `RetakePipeline(video_path, start_time, end_time, regenerate_video, regenerate_audio)` |
| control | reject | `ICLoraPipeline` + control IC-LoRA + `--video-conditioning` (+ mask) |
| dub | `ref2va` edit + voice audio ref | `DubItPipeline(reference_video, reference_strength)` |
| t2a | reject | `T2AOneStagePipeline` |

---

## 5. Open questions / things to verify before launch

1. **H3 duration edges:** does SGLang accept 4 s (107 frames)? Does diffusers reject 15 s (362 frames)? Settle it with golden tests.
2. **H3 audio-only Ref2VA:** the SGLang cookbook lists an `audio_only` mode; diffusers forbids it.
3. **H3 Turbo on SGLang:** the Turbo repo documents diffusers/ComfyUI/LightX2V only. I found no SGLang LoRA flag for Turbo [UNVERIFIED]. Kino may need a diffusers-based worker for Turbo.
4. **LTX-2.3 LoRAs on 2.5** (Union-Control, Motion-Track, DubIt, Ingredients): the card says "generally run", the README says "only works with the model it was trained on". Needs testing.
5. **LTX extend:** there is no official 2.5 extend recipe; prototype with `LTX2ConditionPipeline` video conditions.
6. **LTX audio sample rate:** 48 kHz according to the recipes; confirm from `vocoder/config.json`, which is gated.
7. **Gated repos:** Kino needs an HF token with gated-repo read access for `Lightricks/LTX-2.5*` and several IC-LoRAs.
8. **H3 privacy:** the official quality path (Context-IR, Regenerate-2K) sends prompts and media to MiniMax servers. It is incompatible with Kino's TEE promise, so treat it as a disabled, opt-in-only feature.

## 6. Source index

- MiniMax H3:
  - GitHub README: https://github.com/MiniMax-AI/MiniMax-H3
  - Request scripts: https://github.com/MiniMax-AI/MiniMax-H3/tree/main/scripts/readme
  - Prompt skill: https://github.com/MiniMax-AI/MiniMax-H3/tree/main/skills/h3-prompt-writing
  - HF model card: https://huggingface.co/MiniMaxAI/MiniMax-H3
  - LICENSE: https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE
  - diffusers docs: https://huggingface.co/docs/diffusers/main/en/api/pipelines/minimax_h3
  - SGLang cookbook: https://docs.sglang.io/cookbook/diffusion/MiniMax/MiniMax-H3
  - vLLM recipe: https://recipes.vllm.ai/MiniMaxAI/MiniMax-H3
  - ComfyUI tutorial: https://docs.comfy.org/tutorials/video/minimax/minimax-h3
  - MiniMax API: https://platform.minimax.io/docs/api-reference/video-generation-v2-create
- H3 Turbo:
  - GitHub: https://github.com/ModelTC/Minimax-H3-Turbo
  - HF weights: https://huggingface.co/lightx2v/Minimax-h3-Turbo
  - SLA variant: https://huggingface.co/lightx2v/Minimax-h3-Turbo-SLA
  - Community perf guide: https://github.com/wildminder/awesome-minimax-H3/blob/main/guides/minimax-h3-performance.md
- LTX-2.5:
  - GitHub: https://github.com/Lightricks/LTX-2
  - Pipelines doc: https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-pipelines/docs/pipelines.md
  - CHANGELOG: https://github.com/Lightricks/LTX-2/blob/main/CHANGELOG.md
  - HF weights: https://huggingface.co/Lightricks/LTX-2.5
  - HF Diffusers weights: https://huggingface.co/Lightricks/LTX-2.5-Diffusers
  - diffusers docs: https://huggingface.co/docs/diffusers/main/en/api/pipelines/ltx2
  - SGLang cookbook: https://lmsysorg.mintlify.app/cookbook/diffusion/LTX/LTX2.5
  - vLLM recipe: https://recipes.vllm.ai/Lightricks/LTX-2.5-Diffusers
  - ComfyUI tutorial: https://docs.comfy.org/tutorials/video/ltx/ltx-2-5
  - fal product page: https://fal.ai/ltx-2.5
  - fal how-to: https://fal.ai/learn/tools/how-to-use-ltx-2-5
  - Runpod post: https://www.runpod.io/blog/ltx-2-5-the-open-weights-world-model-built-for-speed-and-how-to-run-it-on-runpod
  - Union-Control IC-LoRA: https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-Union-Control
  - Motion-Track IC-LoRA: https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-Motion-Track-Control
  - License: https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x
