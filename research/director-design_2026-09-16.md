# Director: plan a storyboard from a brief, inside the enclave

Research and design date: 2026-09-16.

**Question.** A customer writes a brief ("a 30-second ad for a small coffee roastery, warm and handmade"). The system
proposes an editable storyboard: a scene and 2-12 shots, each with a prompt, a duration and a join, plus an exact price.
Nothing renders before the customer approves. The approved plan renders as the storyboard job that already exists
(PROTOCOL.md "Storyboards"). In Private mode, nobody outside the attested enclave or the customer's device may read the
brief or the plan. So the planner can't be a third-party LLM API.

Related notes:
- `video-agents_2026-09-16.md` §4 recommendation 3: why every big platform plans first.
- `long-video_ltx-av-extend_2026-09-16.md`: storyboards on a GPU, and the 96 GB memory limits.
- `research_model_capabilities.md`: LTX-2.5 components and prompt rules.

**Method.**
1. **Code.** I read the worker, protocol, gateway, SDK and studio code.
2. **Image.** I inspected `kuno-worker:ltx` (diffusers 0.40.0, transformers 5.17.0, torch 2.11.0+cu128).
3. **Model files.** I compared the Hugging Face file listings of `Lightricks/LTX-2.5-Diffusers@426936f8` (the gated
   repo's tree, saved in an earlier session) with Google's public Gemma 4 repositories.
4. **CPU experiment.** On this dev server (AMD EPYC 4244P, 6 cores, no GPU), I ran three candidate planner models on five
   briefs with llama.cpp. Section 6 has the details.
5. **No GPU was rented.** Anything about GPU latency is an estimate, and I say so.

**Legend**
- **[V]** verified in our code, the worker image, or the file listings.
- **[M]** measured for this note on the CPU.
- **[C]** a primary source.
- **[S]** a secondary source.
- **[A]** an assumption or estimate that still needs checking.
- **[U]** unverified.

---

## 1. Summary

**Recommendation: run the planner inside the enclave, on the LTX-2.5 worker, using the model that is already on the
GPU.**
- **The model.** `LTX-2.5-Diffusers` ships a `prompt_enhancer` component that is (or is derived from)
  `google/gemma-4-E2B-it`. That is a 5.1B-parameter (2.3B effective) instruction-tuned chat LLM whose base is
  Apache-2.0.
- **It is already loaded.** Our loader puts it on the GPU with every other component [V].
- **Cost of using it.** No new weights, no second model on the 96 GB card, and a KV cache under 0.1 GiB.
- **How it runs.** Planning is a new job mode, `plan`. It uses the normal sealed-job path, and its output is a sealed
  JSON plan instead of a video.
- **Standard mode** uses the same enclave planner. The gateway can also read the brief and the plan, so it checks both.

**Division of labour: the model writes the words, and shared code does everything else.** The code, in a new module
`kuno_protocol.plans`:
- fixes the JSON;
- clamps shot count and durations to the profile and the worker envelope;
- fits the stitched length to the target;
- sanity-checks joins;
- truncates prompts to `max_prompt_chars`;
- runs the content policy on every generated shot prompt.

The SDKs run the same code when a customer edits a plan, so the price shown is exact: it is the same
`profile.price_usd` the gateway charges [V].

**What the CPU test showed (5 briefs per model, Q8_0, llama.cpp)** [M]
- **Gemma-4-E2B (the bundled enhancer's base model) works as a first-draft planner.**
  - Every output was usable JSON once one deterministic repair was applied. 3 of 5 free-form outputs closed the object
    early; with a JSON-schema grammar, 5 of 5 were valid.
  - It kept quoted speech in the brief's language ("Guten Morgen.").
  - Its weaknesses need code and UX around them:
    - it overused `continue`: the shot size changed at 23 of its 24 `continue` joins;
    - it wrote short prompts of 1-3 sentences, and 33 of 34 shots copied "the camera stays still" from the instructions;
    - it undershot long targets: 49 s for a 90 s brief;
    - it dropped a required slogan.
- **Stock Gemma 4 12B-it was clearly better on the same prompt.**
  - Valid JSON 5 of 5, with no repair.
  - Mostly `cut` joins, varied camera moves, 3-5 sentences per shot.
  - The dialogue belonged to the right character.
  - It kept the slogan exactly.
  - It was 5× slower on CPU.
- **Qwen3.5-4B was no better than E2B here.**
  - Valid JSON 5 of 5.
  - But it planned 23 s for a 45 s brief, and it dropped the required slogan.
  - It was also half as fast.

**Upgrade path, in order**
1. **Try the LTX 12B text encoder as the planner.**
   - `text_encoder` is a Gemma 4 12B with exactly the tensor sizes of stock `google/gemma-4-12B-it`, including tied
     embeddings, so an LM head exists [V].
   - It is also already on the GPU (22.3 GiB).
   - But Lightricks trained it jointly with the video model and routes enhancement to the separate E2B instead [C].
   - One GPU hour decides whether it still writes coherent text. If it does, it gives 12B-class plans at zero extra
     memory.
2. **Otherwise, load stock Gemma 4 12B-it (24 GB, Apache-2.0) as a planner on the H200/B200 classes**, which have the
   memory for it.
3. **Add a per-shot expansion pass.** It uses Lightricks' own LTX-2.5 enhancer system prompt, the one E2B is paired with
   (§6.4).

**Not for v1**
- **A browser planner** (WebGPU, about a 3 GB download): useful later as "plan on this device", but not needed to meet
  the Private guarantee.
- **A CPU LLM inside the CVM:** it adds llama.cpp to the attested image. It becomes interesting if we evict the enhancer
  from the GPU (next point).

**The finding with the largest product impact: the idle enhancer costs about 9 s of shot length on the RTX PRO 6000.**
- The `prompt_enhancer` occupies 9.5 GiB of VRAM on every LTX worker today. Nothing uses it: the SDKs never send
  `enhance_prompt` [V].
- By the measured activation slope, freeing that memory would raise the longest 720p shot on the card from 11 s to
  about 20 s [A, arithmetic in §2.4].
- So the planner's location is a trade-off:
  - **v1** keeps the enhancer on the GPU and uses it;
  - **a GPU measurement** of the eviction gain decides whether v2 moves planning off the card.

---

## 2. Can the planner run on the model already in the worker? (question 1)

### 2.1 What the prompt enhancer is [V]

In the worker image's diffusers 0.40.0 (`diffusers/pipelines/ltx2/`):

- **Class.** `LTX2Pipeline` declares `prompt_enhancer: Gemma4ForConditionalGeneration | None` and
  `processor: ProcessorMixin | None`, both optional components. The text encoder is typed
  `Gemma3ForConditionalGeneration | Gemma4UnifiedForConditionalGeneration`.
- **Which model.** `utils.py` says:
  - "LTX-2.5: a dedicated `google/gemma-4-E2B-it` `prompt_enhancer` component (the fine-tuned text encoder isn't trained
    for enhancement)";
  - the enhancer's system prompt is "Paired with `google/gemma-4-E2B-it`".
- **The Gemma 4 decoding config.**
  - `GEMMA4_PROMPT_ENHANCEMENT_CONFIG`: `max_new_tokens=600`, `do_sample=False`, `no_repeat_ngram_size=5`, seed 10.
  - The LTX-2.0/2.3 fallback (Gemma 3 text encoder): 512 tokens, `do_sample=True, temperature=0.7`.
- **How diffusers calls it** (`LTX2Pipeline.enhance_prompt`):
  - It builds `[{"role": "system", ...}, {"role": "user", "content": "user prompt: <prompt>"}]`.
  - It applies `self.processor.tokenizer.apply_chat_template(..., add_generation_prompt=True)`.
  - It left-pads to a multiple of 8, runs `enhancer.generate(**inputs, max_new_tokens, **kwargs)`, decodes the new
    tokens, then calls `clean_response`.
- **The default system prompt** is `LTX2_5_T2V_DEFAULT_SYSTEM_PROMPT` ("capstyle_plus", 3,769 characters). It asks for one
  150-220-word caption paragraph in the training captions' style. §6.4 tests it.
- **Our code.** `ltx_resident.build_call` sets `enable_prompt_enhancement=True` only when the sealed
  `options.enhance_prompt` is true and the profile's `limits.prompt_enhancer` is true (all three LTX profiles). Neither
  SDK nor the studio sends that option [V: grep].

**Is the bundled copy stock E2B?** Not proven. Two indicators:

| | LTX `prompt_enhancer/` | `google/gemma-4-E2B-it` |
|---|---|---|
| Weights | 3 shards, 10,208,851,838 bytes | 1 file, 10,246,621,918 bytes |
| `chat_template.jinja` | 18,569 bytes (`processor/`) | 18,569 bytes |
| `tokenizer.json` | 32,169,626 bytes | 32,169,626 bytes |

- The chat template and tokenizer sizes match exactly.
- The weights are 37.8 MB smaller. Resharding alone doesn't explain that, so Lightricks may have dropped or changed some
  tensors.
- The blob hashes are hidden without the gate. A GPU box with the token can settle it with `sha256sum`.
- A release guide calls it "a custom prompt enhancer" [S] ([ltx23.org](https://ltx23.org/blog/ltx-2-5-release-guide)).

**Gemma-4-E2B-it facts** [C] ([HF card](https://huggingface.co/google/gemma-4-E2B-it),
[Google Open Source Blog](https://opensource.googleblog.com/2026/03/gemma-4-expanding-the-gemmaverse-with-apache-20.html))
- **Size:** 2.3B effective parameters, 5.1B with embeddings; `Gemma4ForConditionalGeneration`.
- **Context:** 128K tokens.
- **Licence:** Apache-2.0. This corrects `video-agents_2026-09-16.md` §4.4, which said "Gemma terms". Gemma 4 is the
  first Gemma under Apache-2.0.
- **Features:** native `system` role and tool use; thinking only when the `<|think|>` token is present.
- **Recommended sampling:** `temperature=1.0, top_p=0.95, top_k=64`.
- **Text config** [V, `config.json`]: 35 layers, 20 of them sharing KV; 1 KV head; `head_dim` 256 (512 on global
  layers); sliding window 512; `tie_word_embeddings: true`.

**Conclusion.** It is a generative, instruction-tuned chat LM with a chat template. It can take a system prompt that
asks for a JSON shot list. §6 shows that it does.

**The pipeline's own `enhance_prompt` can't be reused for JSON** [V]
- `clean_response` returns the text from its first letter onward, so it strips a leading `{`. Tested in the image:
  `clean_response('{"title": "x"}')` → `'title": "x"}'`.
- `no_repeat_ngram_size=5` bans the repeated key sequences that every JSON shot list needs (`", "duration_s": `).
- 600 tokens is too short for 8+ shots.

So the planner calls `pipe.prompt_enhancer.generate` directly, with `pipe.processor.tokenizer` and its own decoding
settings.

### 2.2 Could the 12B text encoder generate instead? [V, C]

**For:**
- `text_encoder/` is 5 shards totalling 23,919,548,424 bytes. Stock `google/gemma-4-12B-it` is one 23,919,549,408-byte
  file. The 984-byte difference is consistent with safetensors headers, so the tensor set and dtypes appear identical.
- The class `Gemma4UnifiedForConditionalGeneration` has an `lm_head` tied to the language model's `embed_tokens`
  (transformers 5.17 in the image). Stock config: 48 layers, sliding window 1,024, `tie_word_embeddings: true`.
- So the checkpoint *can* run `generate()` with no extra weights, and it is on the GPU already.

**Against:**
- Lightricks staff: "Since the model and the encoder were trained together, using the model with any other encoder
  produces sub optimal results" ([HF discussion #34](https://huggingface.co/Lightricks/LTX-2.5/discussions/34)) [C].
- diffusers: "LTX-2.5's text encoder is not trained for enhancement, unlike LTX-2.0/2.3's" [V].
- Joint training moves the hidden states that the LM head reads. Nobody has published whether the result still writes
  well.

**Why it is worth testing.** Stock 12B scores far above E2B [C, HF card]:

| Benchmark | E2B | E4B | 12B |
|---|---|---|---|
| MMLU-Pro | 60.0 | 69.4 | 77.2 |
| GPQA Diamond | 43.4 | 58.6 | 78.8 |
| Tau2 | 24.5 | 42.2 | 69.0 |
| BigBench Extra Hard | 21.9 | 33.1 | 53.0 |

- Stock 12B also planned clearly better in §6.
- **The test.** Run the five §6 briefs through `pipe.text_encoder.generate` with `pipe.tokenizer`'s chat template.
  `tokenizer/chat_template.jinja` is 18,683 bytes, the same as stock 12B's. Compare the outputs with the stock-12B CPU
  outputs.
- **Cost:** under an hour on the GPU box already used for storyboard tests.
- **Extra memory:** the KV cache at 4K tokens is at most about 1.3 GiB [A, computed from the config]. That fits between
  renders.

### 2.3 Is the enhancer really on the GPU today? [V code; inferred for the measurement]

1. `quantized.build_ltx_pipelines` calls `LTX2Pipeline.from_pretrained(models_dir, transformer=..., torch_dtype=bf16)`.
   That loads every component `model_index.json` names whose folder exists: `prompt_enhancer`, `processor` and
   `duration_head` included.
2. `_apply_offload(base, "none", device)` then calls `pipeline.to(device)`.
3. The GPU test script's `fetch-weights` (`scripts/gpu-test/smoke.py`) downloads every component `model_index.json`
   names.

So the 2026-09-16 measurements (86.89 GiB peak for 720p 5 s; 93.68 GiB for 12 s) were almost certainly taken with the
9.5 GiB enhancer on the card.

The folder sizes of the weights that load:

| Component | GiB |
|---|---|
| transformer | 35.38 |
| text encoder | 22.28 |
| prompt enhancer | 9.51 |
| connectors | 5.91 |
| VAE, audio VAE, vocoder, upsampler | 2.62 |
| **Total weights** | **75.7** |

That leaves about 11 GiB for activations and allocator overhead at the 5 s peak.

**Planning needs almost no extra memory.**
- An E2B KV cache for a 4K-token plan is under 0.1 GiB (15 layers with their own KV; one KV head).
- Generation activations are small next to a render's.
- The worker runs one job at a time (`Worker.run` handles each pulled item in turn) [V]. So planning never overlaps a
  render on the same card.

**Two gaps to fix**
1. **Safety** [V].
   - `worker.process` runs the content policy on the customer's prompt *before* `backend.generate`.
   - Enhancement happens inside the pipeline call.
   - So today an enhanced prompt is never checked. Only the output frame check stands behind it.
   - The planner design below checks generated text explicitly. The existing `enhance_prompt` option should get the
     same fix, or be removed.
2. **The weights digest doesn't cover the planner's chat template** [V].
   - `precision_recipes.json`'s `include` lists `prompt_enhancer` but not `processor`, which holds
     `chat_template.jinja` and the tokenizer the enhancer uses.
   - So those files aren't hashed into the pinned weights digest.
   - A models directory built only from `include` would load no `processor`. `enhance_prompt` would then fail on
     `self.processor.tokenizer`.
   - Add `processor` to the LTX recipes' `include`. That changes the digests, so the manifest's `model_digests` must be
     republished.

### 2.4 The trade-off: 9.5 GiB of VRAM for a planner [A]

The memory plan uses the recipe's measured line. Available room is 94.97 − 0.5 reserve − 1.5 overhead = 92.97 GiB.

| | Base (weights + fixed activations) | Max full-size tokens | 720p 16:9 at 24 fps (880 tokens per latent frame) | 1080p 16:9 (2,040 per latent frame) |
|---|---|---|---|---|
| Today: enhancer on GPU (recipe counts 8.0 GiB) | 81.72 GiB | about 30,600 | **11 s** (29,920) | 4 s |
| Enhancer evicted (9.51 GiB actually freed) | 72.2 GiB | about 56,500 | **about 20 s** (53,680) | about 8 s |

**Why it matters.**
- The gain is large: fewer, longer shots mean fewer joins, and one card could serve the profile's full 20 s.
- **It is not measured.** Allocator fragmentation already cost 3.8 GiB at 12 s without expandable segments.

**Options to keep a planner and get the memory back**
- **(a)** Keep the enhancer in CVM host RAM and move it to the GPU only for a plan job. This costs about 10 GB of
  host-to-device transfer per plan, through confidential-computing bounce buffers. The speed is unmeasured.
- **(b)** Plan on the CPU inside the CVM (§3).
- **(c)** Use the 12B text encoder as planner (§2.2), which is on the GPU anyway.

Option (c) makes (a) and (b) unnecessary, which is why the 12B test comes first.

### 2.5 Answer to question 1

**Yes: the loaded E2B enhancer can plan.**
- **Memory:** it adds nothing that matters.
- **Latency on the GPU: not measured.**
  - On a 6-core CPU in llama.cpp Q8_0, a free-form plan took 33-48 s [M].
  - A Blackwell GPU through HF `generate` should be well under that. Expect roughly 10-40 s for 400-1,000 tokens [A]:
    HF's per-token Python loop, not the GPU, limits a 5B model.
- **Quality:** a first draft that code must repair and people will edit (§6).
- **The 12B text encoder** is technically able to generate and is a much stronger model class. Whether its jointly
  trained weights still write well is the one question that needs a GPU.

---

## 3. Alternatives (question 2)

| Option | Where it runs | Model and size | Licence | Speed | Privacy | Quality | Verdict |
|---|---|---|---|---|---|---|---|
| **A. Bundled E2B enhancer** | Enclave, GPU, between renders | Gemma-4-E2B-it, 10.2 GB bf16, already loaded | Apache-2.0 base; shipped inside LTX-2.5-Diffusers (LTX-2 Community License) | GPU [A] 10-40 s; CPU Q8 [M] 33-48 s free-form, 74-102 s with a JSON grammar | Brief and plan only in the enclave | Draft: needs repairs (§6) | **v1** |
| **B. LTX 12B text encoder** | Enclave, GPU | Gemma 4 12B jointly trained by Lightricks, already loaded | LTX-2 Community License | GPU [A] 30-90 s; stock 12B on CPU [M] 139-216 s | Same as A | Stock 12B: best of the three tested; this copy unknown | **Test first on a GPU** |
| **C. Stock 12B-class planner as a new component** | Enclave, GPU; H200 141 GB and B200 180 GB classes only | Gemma 4 12B-it, 23.9 GB bf16 ([HF](https://huggingface.co/google/gemma-4-12B-it)); or Qwen3.5-9B, 9.7B params ([HF](https://huggingface.co/Qwen/Qwen3.5-9B)) | Apache-2.0 [C] | GPU [A] 30-90 s | Same as A | 12B: good (§6) | **If B fails.** New weights to pin and a routing constraint |
| **D. CPU LLM inside the CVM** | Enclave, CPU (TDX), can run beside a render | E2B GGUF Q8_0, 4.97 GB ([ggml-org](https://huggingface.co/ggml-org/gemma-4-E2B-it-GGUF)) | Apache-2.0 (model), MIT (llama.cpp) | [M] 6-core Zen 4: prefill 143 tok/s, generate 18.7 tok/s. A server CVM with more memory channels should be faster [A] | Same as A | Same as A at Q8 | **Only if the enhancer is evicted** (§2.4). Adds llama.cpp and a GGUF to the attested image; shares CPUs with ffmpeg and the CPU safety classifiers |
| **E. In the customer's browser** | WebGPU, transformers.js | `onnx-community/gemma-4-E2B-it-ONNX` q4f16, about 3.1 GB text-only download (decoder 1.52 GB + embeddings 1.59 GB) [V, HF tree]; `Qwen3.5-2B-ONNX` q4f16, about 1.4 GB | Apache-2.0 | 20-25 tok/s on an M3 MacBook, about 30 tok/s on an RTX 3060 laptop [S, search snippet] ([gemma4-ai.com](https://gemma4-ai.com/blog/webgpu-browser-guide)) | Strongest: nothing leaves the device | 4-bit, same model class as A; no JSON grammar in transformers.js [U] | **Later**, as "Plan on this device". Excludes the Python SDK, most phones and old browsers |
| **F. The customer's own agent** | Claude, ChatGPT and others through the MCP server | The host's model | n/a | n/a | The host sees the brief (outside our guarantee) | Usually strong | **Supported from day one** through the deterministic `fit_storyboard` and `quote_price` tools (§4.9) |

**Notes on the alternatives**
- **Qwen3.5 small models** are Apache-2.0 with 262K context and thinking on by default ([HF](https://huggingface.co/Qwen/Qwen3.5-4B)) [C].
  - Model-card scores for the 4B: IFEval 89.8, IFBench 59.2, BFCL-V4 50.3.
  - In our test the 4B was slower than E2B on CPU (8.9 against 18.7 tok/s generation) and planned worse (§6), so it
    offers no reason to add weights.
- **WebLLM** has JSON-schema generation ([GitHub](https://github.com/mlc-ai/web-llm)) [C]. Its prebuilt list, as fetched,
  showed no Gemma 4 or Qwen3.5 builds [U].
- **Hosted open-weight APIs for Standard mode** (fal, Together and others) would add a third party that sees prompts.
  PRIVACY_MODES.md allows only KunoWorld and the GPU provider to see Standard content, so they are excluded.

---

## 4. Protocol and product design (question 3)

### 4.1 A plan is a job

**The flow**
1. The client seals a brief to an attested enclave, exactly like a video request.
2. The worker plans and seals a JSON plan to the job's output key.
3. The gateway stores the ciphertext, charges, refunds on failure, and relays progress and the receipt, as for videos.

Reusing the job path keeps attestation checks, HPKE, padding, cancel, refunds and receipts unchanged.

**Public params** (`GenerationParams`, the AAD):

```
{"profile_id": "ltx-2.5-fast", "mode": "plan", "duration_s": 30, "resolution": "720p", "aspect_ratio": "16:9",
 "fps": 24, "audio": true, "input_roles": []}
```

- `profile_id` is the profile the storyboard will render on.
- `duration_s` is the target stitched length. It is public because the eventual storyboard publishes its exact length
  anyway, and the gateway must validate the range.
- No `shots`. No inputs in v1; reference images belong to the Elements work.

**Sealed payload** (`SealedPayload`):

```
{"v": 1, "prompt": "<the brief>", "seed": 123456,
 "options": {"plan": {"v": 1, "style": "35mm film, warm", "max_shot_s": 11, "min_shots": 2, "max_shots": 12,
                      "revise": null}}}
```

- **`max_shot_s`.** The SDK takes the longest duration that some routable confidential enclave's `envelope` serves at
  this resolution, aspect ratio and fps (`GET /v1/route`), capped by the profile. That is the same rule the storyboard
  will route by. On an RTX PRO 6000 at 720p it is 11 today.
- **`revise`** (optional) is `{"plan": <Plan v1>, "instruction": "make shot 3 a close-up, darker", "shots": [3]}`.
  - Only the listed shots are rewritten.
  - Every other shot comes back byte-identical, and the duration fit only moves the rewritten shots.
  - Without `shots`, the whole plan is rewritten under the instruction.

**Profile additions** (`profiles.json`, `ltx-2.5-fast` first):

```
"modes": [..., "storyboard", "plan"],
"limits": {..., "plan": {"min_target_s": 4, "max_brief_chars": 4000, "max_style_chars": 500, "max_new_tokens": 2048,
                         "planner": "prompt_enhancer", "prompt_version": "plan/1"}},
"pricing": {..., "plan_usd": 0.10, "standard_plan_usd": 0.08},
"vcu_weights": {..., "plan": 27}
```

**`validate_params` for mode `plan`**
- `shots` must be absent and `input_roles` empty.
- `min_target_s ≤ duration_s ≤ limits.storyboard.max_total_s`.
- The resolution, aspect ratio and fps must be valid for the profile.

**`render_duration_s` is 0 for a plan.** So an envelope lookup (`fits`, `admission_refusal`) admits a plan on any enclave
that serves that size and frame rate.

**Output**
- A blob with label `<job_id>/output/plan`.
- The plaintext is the plan JSON with the request padding framing, `0x02 | length:u32be | JSON | 0x00…` to
  `bucket(5 + length)` (PROTOCOL.md "Sealed request padding"), then `encrypt_blob` as usual.
- A plan is 2-5 KB of JSON [M]. Blob PADMÉ alone would reveal its length to within a few percent, and so roughly how
  many shots it has. Power-of-two buckets from 4 KiB hide that.

### 4.2 Receipts

`ReceiptBody` gains an optional `plan` and makes `video` optional. Both keys are left out of the signed bytes when
unset, as `step_commitment` already is, so every existing receipt signs and verifies byte-for-byte as before:

```
"plan": {"shots": 6, "duration_s": 29.708, "planner": "ltx-2.5-distilled/bf16/1:prompt_enhancer", "prompt_version": "plan/1",
         "output_tokens": 612}
```

- `content_digest` is the SHA-256 of the unpadded plan JSON.
- `output_digest` and `output_bytes` describe the sealed blob, as for videos.
- `gpu_seconds` as usual.
- No C2PA: the plan isn't media.
- **Receipt readers that predate plans** fail to parse a plan receipt. Only new clients request plans, and validators
  are upgraded first (§7).
- **Link to the render.** The storyboard rendered from a plan carries `options.plan_digest` (sealed). The render's C2PA
  manifest can then list the plan as an input ingredient by hash later (`video-agents_2026-09-16.md` §4.4).
  The gateway learns nothing new from this.

### 4.3 Worker flow (mode `plan`)

1. **Reject what doesn't fit.** As for every job: validate params, check the envelope, open the payload. Refuse a
   `plan` job if the backend has no planner (`internal_error` before decryption, as storyboards do today).
2. **Check the brief and style.**
   - Length: `max_brief_chars`, `max_style_chars` → `prompt_too_long`.
   - Content: `check_request(brief)` and `check_request(style)`. That is the content policy plus the configured prompt
     classifier (Qwen3Guard on CPU). A block is reported as `safety_blocked` with the fixed message. Nothing is
     generated.
3. **Generate, on whichever LTX pipeline is loaded.** `ModelStore` keeps one profile resident, and every LTX recipe
   includes the same enhancer, so planning never forces a 60 GB reload.
   - Messages: system prompt `plan/1` (§5.1) and user `Brief: …`.
   - Decoding: `do_sample=True, temperature=0.7, top_p=0.95, top_k=64, max_new_tokens=2048`, seeded from `seed`.
   - Progress stage: `planning`.
4. **Parse and repair** with `kuno_protocol.plans.repair` (§5.3). If parsing still fails, or there are fewer than 2
   shots, or the model's own stitched length is more than 25% short of the target:
   - retry once, adding the problem as a user turn ("Your plan runs 49 s; the target is 90 s. Add shots.");
   - if it still fails, fail as `plan_failed`: refunded, and not counted against the miner.
5. **Check the brief's quoted text.** Every phrase the brief puts in quotes (a slogan, a line) must appear in some shot
   prompt. If one is missing, run the same single retry. E2B's free-form run dropped "Sip. Stay fresh." [M].
6. **Check the output's safety.**
   - Run `check_request(shot_prompt(scene, prompt))` for every shot, and the content policy on `title`, `notes` and each
     `beat`.
   - A blocked shot is regenerated once. A second block fails the job as `safety_blocked`.
   - The storyboard render checks every shot again later.
7. **Deliver.**
   - Validate the result as storyboard params (`validate_params`) and check `len(shot_prompt) ≤ max_prompt_chars`.
     Failing that is a bug and becomes `internal_error`.
   - Pad and seal the plan, sign the receipt, upload.
   - There is no output frame check.

### 4.4 Gateway

- **Routes.**
  - `POST /v1/videos` accepts `mode: "plan"` through the same admission code. `POST /v1/plans` is a documented alias.
  - `GET /v1/videos/{id}` returns `JobStatus` as usual.
- **Routing.**
  - Only confidential enclaves: plans can't be step-audited, the same rule as storyboards.
  - Only enclaves that advertise the feature. `MinerRegistration` gets an optional `features: ["plan/1"]`, published in
    the enclave feeds.
  - The gating is needed because a worker from before plans can't parse `mode: "plan"`. It would log "malformed job"
    and leave the job to time out.
- **Price.**
  - `price_usd` for a plan is `pricing.plan_usd` (Private) or `standard_plan_usd`, flat. It is not subject to
    `min_job_usd`.
  - The usual ledger charge, refund on failure, and `billable_usd`.
- **Rate limits.** Plans count toward `max_active_jobs`, with a separate `plans_per_minute`.
- **Standard mode.**
  - `POST /v1/standard/plans` takes `{job_id?, params, brief, style?, options?}`.
  - The gateway runs `check_prompt` on the brief (strike on violation, as for Standard prompts), seals to a confidential
    plan-capable enclave, and charges.
  - When the job succeeds, it decrypts the plan, runs `check_prompt` on the scene and every shot prompt, and stores the
    plan like a Standard prompt: readable, deletable, no expiry.
  - `GET /v1/standard/plans/{job_id}` returns the plan JSON.
  - A Standard storyboard then goes through the existing `POST /v1/standard/videos` with `shots`.

### 4.5 Price

**What a plan costs (all estimates until measured)** [A]
- GPU time: E2B needs 400-1,700 output tokens. That is about 10-40 s of GPU on C1 [A].
- Rental cost: at the measured $1.879/h, 30 GPU-s is $0.016.
- Miner pay: VCU pays 3 VCU per 720p output second, which takes 3.3 GPU-s (measured), at $0.0019 per VCU. That is
  $0.0017 per GPU-s, so a 30 GPU-s plan pays the miner about $0.05.
- Customer price: PRICING.md keeps miner pay at or below 60% of the price. So a plan should cost at least about $0.09.

**Recommendation (placeholders, like every price)**
- $0.10 per plan in Private and $0.08 in Standard.
- A revision of 3 or fewer shots costs half.
- Refunds on failure as usual.
- Replace the values once `kuno-bench` measures plan GPU-seconds.

**Not free with a rate limit.** A plan occupies a confidential GPU worker that VCU pays for, and free jobs invite abuse
of the scarcest capacity we have.

**Optional product decision: credit the plan fee against its storyboard.**
- It needs a public `plan_job_id` on the storyboard's `JobCreate`, which tells the gateway which plan became which render.
- The gateway can mostly infer that from timing anyway.

**The render quote is exact.**
- `KunoClient.estimate_price` (Python) and `priceQuote` (JS) apply the gateway's own `profile.price_usd` to the fitted
  shots [V].
- Example: E2B's roastery plan fitted to 29.708 s costs $3.565 Private ($0.12/s) or $2.674 Standard ($0.09/s).

### 4.6 Validators

Plans carry no step commitment, and sampled text can't be replayed exactly across machines. They are **attested and
receipted, but unverified**, like storyboards today.

**Ledger**
- A plan row pays the flat `vcu_weights.plan`.
- The ±0.5 s video-duration check is skipped for plan rows, which have no `receipt.video`.
- `gpu_seconds` must be positive and under a cap (e.g. 300 s).

**Plan canaries (main validator)**
- Canaries go through the ordinary sealed path, from a private brief set. Each brief carries 2-3 *must-mention* terms
  (e.g. "lighthouse", "keeper").
- A delivered canary fails when any of these hold:
  - the receipt signature or attestation fails;
  - the plan doesn't decrypt, doesn't parse, or fails `kuno_protocol.plans.validate`;
  - the stitched length is off target by more than 0.5 s without a matching entry in `repairs`;
  - a shot prompt fails the content policy;
  - fewer than half of the must-mention terms appear;
  - `planner` isn't a planner the manifest's recipe for that image allows.
- These checks catch a miner returning canned or empty plans, which is the only cheap cheat. The enclave image is
  attested, so a confidential miner can't swap the model.
- Canaries that never return a receipt stay unattributable, as today.
- **Standard canaries** use `POST /v1/standard/plans`.

**Not in v1:** judging plan quality. It is subjective, and scoring it would push miners toward gaming a judge.

### 4.7 Studio UX

```
Storyboard ─────────────────────────────────────────────────────────────
 Plan from a brief                                   🔒 planned inside a confidential worker
 ┌──────────────────────────────────────────────────────────────────┐
 │ A 30-second ad for a small coffee roastery, warm and handmade.   │
 └──────────────────────────────────────────────────────────────────┘
 Length  [15] [30●] [45] [60] [90]    16:9 · 720p · Sound on (composer chips)
 Style (optional) [ warm, handheld, 35mm film look          ]
 [ Plan · $0.10 ]                                     about 30 s

 Scene, shared by every shot  [editable: people, place, light, look, background sound]
 ① Beans hit the cooler        6 s  New shot        [Rewrite] [×]
 ② Hands check the roast       5 s  New angle ▾     [Rewrite] [×]
 ③ …
 ⓘ Adjusted: shot 3 shortened to 11 s (the longest this worker class renders at 720p).
 ⓘ Planner note: titles and the logo should be added in editing.
 Running length 29.7 s · Private $3.57
 [ Render storyboard · $3.57 ]
```

**Where it lives.** The panel sits at the top of the existing Storyboard tab (`components/studio/StoryboardTray.tsx`).
It loads a finished plan through the composer's existing snapshot action (`composerState`: `prompt` becomes the scene,
and `shots` replace the cards) [V].

**Shot cards**
- The cards already show running length and price (`lib/shot.ts` `storyboardLength`, `estimatePrice`).
- Planning adds the `beat` as the card title, and a **Rewrite** button (a revision job for that shot, with an optional
  instruction).
- Join chips are labelled "Same take" for `continue`, "New angle, same sound" for `cut`, and "New shot" for `fresh`.

**States**
- **Planning:** progress `planning` / `checking`.
- **Refunds:** `plan_failed` ("Couldn't plan this brief. You weren't charged. Try rephrasing.") and `safety_blocked`
  (fixed message).
- **Adjustments:** every entry in `repairs` shows as a dismissible notice. Nothing is changed silently.

**Storage.** A Private plan lives only in the browser (the local draft), optionally synced through the key vault, which
the gateway can't read. A Standard plan also appears in history.

**Honesty in copy**
- "A first draft to edit". The v1 planner is a small model.
- The lock line links to the attestation panel.

**WebMCP.** Add `stage_storyboard` (fill the cards for review, no spend) next to the existing `stage_video_prompt`.

### 4.8 SDKs

**Python**

```python
board = client.plan(
    "A 30-second ad for a small coffee roastery, warm and handmade.",
    duration_s=30, model="ltx-2.5-fast", resolution="720p", aspect_ratio="16:9", style="35mm film",
    privacy="private",                     # sealed on this machine to an attested enclave
)                                          # -> Storyboard (waits; wait=False returns a PlanJob)
board.shots[2].prompt += " The camera slowly pushes in."
board.shots[3].duration_s = 6
board.fit()                                # kuno_protocol.plans.fit_storyboard, locally, no network
print(board.duration_s, board.repairs, client.estimate_price(board.profile_id, shots=board.shots, resolution=board.resolution))
board = client.revise_plan(board, "make shot 3 a close-up, darker", shots=[3])
video = client.generate(board.scene, shots=board.shots, model=board.profile_id, resolution=board.resolution,
                        aspect_ratio=board.aspect_ratio, fps=board.fps, audio=board.audio)
# or client.generate_storyboard(board)
```

- `Storyboard` is a dataclass: `title, scene, shots: list[PlannedShot], notes, profile_id, resolution, aspect_ratio, fps,
  audio, duration_s, repairs, planner, job_id, receipt`.
- `PlannedShot` extends the existing `Shot` (`prompt, duration_s, join`) with `beat`, so `shots=board.shots` passes
  straight to `generate` [V: `Shot` fields].

**JS**

```ts
client.plan({ brief, durationS, model, resolution, aspectRatio, style, privacy }): Promise<Storyboard>
client.revisePlan(board, instruction, { shots }): Promise<Storyboard>
fitStoryboard(profile, board, { maxShotS }): Storyboard      // pure, mirrors kuno_protocol.plans
```

The fitted board feeds `generate({ prompt: board.scene, shots: board.shots, ... })`, using the existing
`GenerateShot` [V].

**Shared vectors.** A new `plans` group in `sdk/js/test/vectors.json` pins repair and fit cases, including the E2B
outputs from §6, so both languages produce identical boards.

### 4.9 MCP tools

The server is being built in parallel. It runs locally and wraps the SDK, so Private mode seals on the user's machine.

| Tool | Maps to | Cost | Notes |
|---|---|---|---|
| `plan_video(brief, duration_s, aspect_ratio?, resolution?, style?, privacy)` | `client.plan` | plan price | Returns the storyboard JSON, `repairs`, and a `quote` for rendering it. An MCP Task if it runs over a few seconds |
| `revise_plan(storyboard, instruction, shots?)` | `client.revise_plan` | revision price | |
| `fit_storyboard(storyboard, model, resolution, fps)` | `plans.fit_storyboard` | free, local | For host agents that write shots themselves: fixes durations, joins and lengths, and reports errors |
| `quote_price(model, shots or duration_s, resolution, fps, privacy)` | `estimate_price` | free, local | Exact against published prices |
| `generate_video(prompt, shots?, storyboard?, ...)` | `client.generate` | render price | Accepts a `storyboard` object directly |
| `get_job(job_id)` | `status` / `wait` | free | |

**Tool descriptions must say two things**
- The agent host sees the brief the user types. The privacy guarantee covers KunoWorld, miners and GPU operators
  (`video-agents_2026-09-16.md` §4.2 rec. 2).
- `plan_video` is optional: a capable host model can write shots itself. So `fit_storyboard`'s description carries the
  same LTX rules as §5.1.

### 4.10 Private and Standard compared

| | Private | Standard |
|---|---|---|
| Brief visible to | the enclave only | KunoWorld and the GPU provider |
| Gateway checks | none (can't read it); the enclave checks brief and output | `check_prompt` on the brief before sealing; on scene and shots after |
| Plan stored | ciphertext only; the customer's device holds the key | plaintext, owner-deletable, in history |
| Route | `POST /v1/videos` (`mode: plan`) | `POST /v1/standard/plans` |
| Enclaves | confidential, `plan/1` | confidential, `plan/1` (v1; open tier can't be audited) |
| Price (placeholder) | $0.10 | $0.08 |

---

## 5. The planning prompt (question 4)

### 5.1 System prompt `plan/1`

`plan/1` merges the two versions tested in §6, so as a whole it is **untested**:
- **v1's three-way join enum.** With v2's booleans, E2B chose "fresh" for almost everything.
- **v2's shot-count hint** ("about N shots of about S s"). It cut E2B's miss on the 90 s brief from 41 s to 10 s.
- **v2's camera menu.** It ended the "the camera stays still" parroting.
- **Firmer speech rules.** Both versions dropped required speech at least once.

Placeholders are filled by the worker. `suggested_shots = clamp(round(target / 6), 2, 12)`;
`suggested_shot_s = round((target + 0.7 × (suggested_shots − 1)) / suggested_shots)`.

```
You plan storyboards for LTX-2.5, a video model that renders each shot as a separate clip with sound and then joins
the clips into one video. Turn the customer's brief into a shot plan.

Output only one JSON object, with no Markdown, no code fences and no text before or after it:
{"title": "...", "scene": "...", "shots": [{"beat": "...", "prompt": "...", "duration_s": 6, "join": "fresh"}], "notes": "..."}

LENGTH
- The video should run about {target_s} seconds. Use about {suggested_shots} shots of about {suggested_shot_s} seconds each.
- Each duration_s is a whole number from {min_shot_s} to {max_shot_s}. Use between {min_shots} and {max_shots} shots.
- Frame: {aspect_ratio} at {resolution}. Sound: {sound}.{style_line}

WHAT THE VIDEO MODEL SEES
The model renders each shot from "scene" followed by that shot's "prompt", and nothing else: not the brief, not the
other shots.
- "scene" holds what stays the same in every shot: each person who appears (apparent age, hair, clothing, one
  distinguishing detail, worded the same way every time), the place, the time of day and the light, the visual style,
  and the steady background sound. At most 600 characters. No actions and no camera moves.
- Each "prompt" is one paragraph of 4 to 6 sentences in the present tense, in this order: the shot size and angle; what
  happens, with concrete verbs, step by step; how the camera moves (for example a slow push-in, a pan, a tracking shot
  that follows the subject, a gentle handheld drift, or a locked-off camera), chosen to suit the action; and what is
  heard (ambient sound, effects, music, speech).
- One prompt is one continuous clip: never write a cut or a second camera set-up inside it.

JOINS
- "fresh": a new moment, place or sound. Always for the first shot.
- "continue": the same take carries on from the last frames of the shot before: same place, same shot size, same
  camera position at the start, same sound. Use it rarely, only for an unbroken take.
- "cut": a new shot size or angle on the same moment; the sound and any voice carry on from the shot before.

SPEECH
- Only when the brief asks for talking, a voice-over, a line of dialogue or a slogan.
- Words the brief puts in quotes must appear exactly, in double quotes, in one of the prompts.
- Say who speaks and how, for example: a warm female voice-over says, "Fresh every morning." Keep each line short
  enough to say inside its shot.
- Keep quoted words in the language the brief asks for; write everything else in English.

PICTURES THAT WORK
- Never ask for readable text, logos, captions, phone or computer screens with words, labels or brand names in the
  picture: the model misspells them. Put a name or slogan in speech, and say in "notes" that titles should be added in
  editing.
- One light logic per shot, few people per shot, no chaotic physics (crowds, splashes, fights).
- Show feelings through visible cues (a small smile, shoulders relax), not emotion words.

OTHER FIELDS
- "beat": at most 8 words, a label for the storyboard card. "title": at most 8 words. "notes": at most 2 sentences
  about assumptions you made.
- If the brief asks for sexual content, nudity, or a real named person, output {"refusal": "cannot plan this brief"}.
```

**Where the rules come from**
- The LTX prompting guide ([docs.ltx.io](https://docs.ltx.io/api-documentation/implementation-guides/prompting-guide))
  [C]:
  - shot → scene → action → character → camera → audio;
  - 4-8 sentences, present tense;
  - emotion through physical cues;
  - one light logic per shot;
  - dialogue in quotes with language and accent;
  - avoid on-screen text and chaotic physics.
- LTX-2.5's own enhancer prompt [V]: "Begin immediately with the action", shot type plus camera motion plus viewpoint,
  quote dialogue exactly.
- `research_model_capabilities.md` §2.3: prompts are capped at 1,024 tokens, and the README says "Keep within 200 words".
- The storyboard rules in PROTOCOL.md [V]:
  - the model sees `scene + "\n\n" + shot`;
  - `max_prompt_chars` 4,000;
  - `continue` pins frames and audio, `cut` pins audio only.

**Why the rules differ from LTX's native multishot guidance.** LTX's guide writes cuts as prose inside one generation
("A hard cut transitions to…", 2-4 shots). Our shots are separate generations joined by latents, so the prompt forbids
cuts inside a shot.

### 5.2 Schemas

**What the model writes.** The JSON Schema used for grammar-constrained decoding in §6:

```json
{"type": "object", "additionalProperties": false, "required": ["title", "scene", "shots", "notes"],
 "properties": {
   "title": {"type": "string"}, "scene": {"type": "string"}, "notes": {"type": "string"},
   "shots": {"type": "array", "minItems": 2, "maxItems": 12, "items": {
     "type": "object", "additionalProperties": false, "required": ["beat", "prompt", "duration_s", "join"],
     "properties": {"beat": {"type": "string"}, "prompt": {"type": "string"},
                    "duration_s": {"type": "integer", "minimum": 2, "maximum": 11},
                    "join": {"enum": ["fresh", "continue", "cut"]}}}}}}
```

The alternative output `{"refusal": string}` is allowed in free-form decoding only.

**What the enclave returns, Plan v1** (`kuno_protocol.plans.Plan`, `extra="forbid"`):

```json
{"v": 1, "profile_id": "ltx-2.5-fast", "resolution": "720p", "aspect_ratio": "16:9", "fps": 24, "audio": true,
 "target_s": 30, "duration_s": 29.708,
 "title": "Handmade Coffee Roastery Warmth",
 "scene": "A rustic, warmly lit coffee roastery interior. ...",
 "shots": [{"beat": "Opening the beans", "prompt": "Close-up shot ...", "duration_s": 6, "join": "fresh"}, ...],
 "notes": "...",
 "repairs": ["the plan ran 23.4 s; shots 1, 3 and 5 lengthened to reach 29.7 s"],
 "planner": {"model": "ltx-2.5-distilled/bf16/1:prompt_enhancer", "prompt_version": "plan/1"}}
```

**Rules the code checks.** They are the same in the worker, the gateway (Standard) and both SDKs:
- `2 ≤ len(shots) ≤ limits.storyboard.max_shots`.
- Each `duration_s` is on the profile's grid, and `min_duration_s ≤ d ≤ min(profile max at fps, max_shot_s)`.
- The first join is `fresh`.
- `duration_s = storyboard_duration_s(shots) ≤ max_total_s`.
- `len(shot_prompt(scene, prompt)) ≤ max_prompt_chars`.
- Length caps: `title ≤ 80`, `beat ≤ 60`, `notes ≤ 400`, `scene ≤ 1,000` characters.
- `validate_params` accepts the equivalent storyboard `GenerationParams`.

### 5.3 Validation and repair (`kuno_protocol.plans.repair`, deterministic)

1. **Find the object.** Drop `<think>…</think>`, code fences, and any text outside the outermost braces.
2. **Parse, repairing the observed defects**, up to 3 attempts.
   - *Early close:* on `Extra data` where the parsed prefix ends in `}` and the rest starts with `,` or `"`, reopen the
     object and insert a comma if needed. E2B did this in 3 of 5 v1 free-form outputs (`…]} , "notes": …`) and 1 of 5
     v2 outputs (`…]} "notes": …`) [M].
   - *Trailing commas:* remove them.
   - If parsing still fails, the worker's single retry applies (§4.3 step 4).
3. **Refusal.** A `refusal` object fails the job as `safety_blocked`.
4. **Shots.**
   - Drop non-objects and blank prompts, and keep at most `max_shots`.
   - A missing `beat` becomes the prompt's first 6 words.
   - Strip leading labels (`Shot 3:`, `Prompt:`) and Markdown.
   - Map curly quotes to ASCII, as diffusers' `_UNICODE_REPLACEMENTS` does.
   - Collapse whitespace.
5. **Joins.**
   - The first becomes `fresh`, and an unknown value becomes `cut`.
   - **Shot-size guard:** a `continue` whose prompt names a different shot size than the shot before (wide, medium,
     close-up, overhead…) becomes `cut`, recorded in `repairs`. On the saved v1 outputs this changed 23 of E2B's 24
     `continue` joins, 19 of Qwen3.5-4B's 20, and 4 of stock 12B's 6 [M].
6. **Durations.**
   - Round to the grid and clamp to `[min, cap]`.
   - Then fit the target. While stitched < target − 0.5 s and a shot is below the cap, add 1 s to the shortest (lowest
     index on ties). While stitched > target + 0.5 s or > `max_total_s`, take 1 s from the longest.
   - On revisions, only rewritten shots move.
   - At 24 fps each step changes the stitched length by exactly 1 s (`ltx_num_frames` adds 24 frames).
7. **Lengths.** Truncate `scene` to 1,000 characters and each prompt to fit `max_prompt_chars` with the scene, both at
   the last sentence end within budget.
8. **Brief quotes.** Every quoted phrase in the brief must occur in some prompt, or the worker retries (§4.3 step 5).
9. **Final check.** `validate_params` must pass on the storyboard. Record every change in `repairs`.

**Grammar-constrained decoding.**
- **What it fixed.** llama.cpp's JSON-schema mode gave 5 of 5 valid outputs.
- **What it cost.**
  - E2B then pretty-printed, generating 2.3-2.8× the tokens and taking twice the wall time [M].
  - Its lighthouse plan dropped the requested line of dialogue.
- **What adoption in the worker needs.**
  - xgrammar (Apache-2.0) as a transformers logits processor, with whitespace disabled.
  - That is a new dependency in the attested image: `xgrammar`, `outlines` and `lmformatenforcer` are all absent from
    `kuno-worker:ltx` [V].
- **Recommendation.** v1 ships parse, repair and retry. Measure the retry rate on the GPU, and add the grammar only if
  that rate matters.

---

## 6. Experiment: three planners on five briefs (CPU, 2026-09-16)

**Setup** [M]
- **Machine:** AMD EPYC 4244P (6 cores, Zen 4), 62 GB RAM, no GPU.
- **Runtime:** llama.cpp `ghcr.io/ggml-org/llama.cpp:server` (build 10991, commit 930e2fa59), 6 threads, context 8,192,
  `--jinja`.
- **Models:** Q8_0 GGUFs:
  - `ggml-org/gemma-4-E2B-it-GGUF`
  - `unsloth/Qwen3.5-4B-GGUF` (thinking off)
  - `ggml-org/gemma-4-12B-it-GGUF`
- **Sampling:** temperature 0.7, top-p 0.95, top-k 64 (Qwen: 0.8 / 20), seed 7, `max_tokens` 3000.
- **Prompt (v1):** plan/1 without the shot-count hint, the camera menu and the brief-quote rule. `max_shot_s` 11.
- **Checker:** repair and checks against `kuno_protocol` from the subnet working tree.
- **Scripts and raw outputs:** session scratchpad only, not committed.
- **A first try in transformers bf16 on the same CPU** ran E2B at 1.3 tok/s, partly contended by a download. That is
  unusable, and is why llama.cpp was used.

**Briefs**
1. roastery, 30 s: "A 30-second ad for a small coffee roastery, warm and handmade."
2. lighthouse, 45 s: an old keeper's last night before automation; quiet; one line of dialogue at the end.
3. water, 20 s, 9:16: an app explainer; female voice-over; "end on the slogan 'Sip. Stay fresh.'"
4. bakery_de, 25 s: a German brief; one short line by the baker, in German.
5. ebike, 90 s: a folding e-bike from sunrise street to office locker; music; no dialogue.

### 6.1 Speed

| Model | llama-bench prefill 1,024 | Generation | Plan wall time (5 briefs) | Output tokens |
|---|---|---|---|---|
| Gemma-4-E2B Q8_0 (4.61 GiB) | 143 tok/s | 18.7 tok/s | 33-48 s | 421-604 |
| E2B with JSON schema | | | 74-102 s | 1,201-1,669 |
| E2B, v2 prompt | | | 24-64 s | 350-995 |
| Qwen3.5-4B Q8_0 (4.16 GiB) | 51 tok/s | 8.9 tok/s | 39-87 s | 312-713 |
| Gemma-4-12B Q8_0 (11.78 GiB) | 23 tok/s | 3.7 tok/s | 139-216 s | 394-644 |

Every prompt was 803-908 tokens.

### 6.2 Structure and length

The last column gives the model's own stitched length against the target, before the fit.

| Model | Valid JSON as written | After repair | Stitched vs target (roastery 30 · lighthouse 45 · water 20 · bakery 25 · ebike 90) |
|---|---|---|---|
| E2B, free | 2/5 (3 early closes) | 5/5 | 23.4 · 32.0 · 23.0 · 23.7 · **49.1** |
| E2B, schema | 5/5 | 5/5 | 28.7 · 36.0 · 17.4 · 22.4 · **53.1** |
| E2B, v2 prompt (shot-count hint, booleans, camera menu) | 4/5 | 5/5 with the generalised early-close rule | 41.5 · n/a · 20.1 · 27.8 · 80.4 |
| Qwen3.5-4B | 5/5 | 5/5 | 22.7 · **23.0** · 14.7 · 22.4 · **38.4** |
| Gemma-4-12B | 5/5 | 5/5 | 26.7 · 37.7 · 18.0 · 23.0 · 52.0 |

Every plan passed the content policy, and every combined prompt was under 1,000 characters.

### 6.3 Content (v1 prompt, free-form)

| | E2B | Qwen3.5-4B | Gemma-4-12B |
|---|---|---|---|
| Sentences per shot prompt | 1-3 | 1-4 | 3-5 |
| "The camera stays still" | 33 of 34 shots | 15 of 26 | 11 of 27; also pans, tracks, push-ins, pull-backs |
| Joins as written | mostly `continue` (FCCCCX…) | mostly `continue` | mostly `cut` (FXXX…) |
| `continue` joins with a shot-size change | 23/24 | 19/20 | 4/6 |
| Lighthouse dialogue | "It is time now." as a voice-over | "Goodbye, old friend." by a *female* voice-over | the keeper, "in a raspy, tired voice": "She's in good hands now." |
| Water slogan "Sip. Stay fresh." | missing (wrote "Time to hydrate.") | missing (notes claimed it was there) | exact |
| German line | "Guten Morgen." | "Frisch jeden Morgen.", "Danke schön." | "Frisch gebacken für Ihren Morgen." |
| On-screen text despite the rule | a phone screen "displays" a reminder | a phone screen | none; notes: "Titles should be added in editing" |
| Unrequested speech | none (free); two lines with the schema | none | one line in the roastery ad |

**E2B's structure is fine and its words are thin.** The rules in §4.3 and §5.3 target exactly its failures:
- the duration fit;
- the join guard;
- the brief-quote check;
- the camera menu.

The v2 prompt shows how sensitive a small model is:
- **The camera menu worked:** push-ins, pans, tracking, handheld, locked-off.
- **The shot-count hint fixed the 90 s undershoot** (80 s).
- **The booleans overcorrected the joins** to nearly all `fresh`.
- **It dropped the water voice-over entirely.**

So every prompt change needs a regression run on a fixed brief set (§7 step 9).

### 6.4 Second pass: expanding shots with Lightricks' enhancer prompt

**What I ran** [M]. I fed each shot of E2B's roastery and lighthouse plans back to E2B with LTX-2.5's own
`LTX2_5_T2V_DEFAULT_SYSTEM_PROMPT` (`user prompt: <scene>\n\n<shot>`), at temperature 0.

**What came back**
- **Length:** 88-151 words per shot (112-183 tokens), 7-15 s per shot on the CPU.
- **Style:** the training-caption style: shot type, camera and viewpoint as prose ("A close-up frames the elderly man,
  captured from a front-facing angle as the camera remains static"), a full soundscape, and the exact quoted line.
- **Identity:** each output restates the scene's people and place in the same words, which helps identity hold across
  shots.
- **Limits:**
  - It can't add a camera move the first pass didn't choose.
  - It adds adjectives ("film-grade color", "crisp high-resolution detail").

**Design option (v1.1).**
- Keep stage 1 as the plan the customer edits. Run the expansion inside the storyboard render as a per-shot
  `enhance_prompt`, with the policy check *after* expansion (§2.3's safety gap).
- Or offer it as a "Detail this shot" button that edits the card.
- On a GPU the expansions batch into one `generate` call [A].

---

## 7. Implementation plan (question 5)

Estimates are for one engineer who knows the codebase. "GPU" marks steps that need hardware.

0. **GPU spike (GPU; ~0.5 day, about $3 on a Shadeform RTX PRO 6000).** Use the current `kuno-worker:ltx` and the §6
   briefs, driven by a new `scripts/gpu-test/plan_spike.py`:
   1. Time E2B planning via `prompt_enhancer.generate` on the resident pipeline, and measure the peak-memory delta.
   2. Run the same briefs through `text_encoder.generate` (the LTX 12B) and compare with the stock-12B CPU outputs. This
      decides option B.
   3. Build the pipeline without the enhancer and find the longest 720p and 1080p shots (confirms or corrects §2.4's
      11 → about 20 s).
   4. `sha256sum` the enhancer weights against `google/gemma-4-E2B-it`.
   5. Time moving the enhancer between host and device (for §2.4 option a; confidential-computing overhead is not
      covered on a non-CC box).
   - Write it up as `research/director-gpu-spike_<date>.md`.
1. **Protocol (`subnet/protocol`; 2-3 days).**
   - `profiles.py`:
     - `Mode.PLAN` and a `PlanLimits` class on `Limits`;
     - the `validate_params` plan branch;
     - `pricing.plan_usd` and `standard_plan_usd` in `price_usd`;
     - `vcu_for` for plans;
     - `render_duration_s` = 0 for plans.
   - `schemas.py`: `MinerRegistration.features`.
   - `receipts.py`: optional `video`, plus `PlanInfo`, both omitted when absent.
   - New `plans.py`: the `Plan` model, `extract_json`, `repair`, `fit_storyboard`, `validate_plan`, the brief-quote
     check, `plan_output_label`, and padding reused from `sealed_payload`.
   - The versioned prompt file `plan_prompts/plan-1.txt`.
   - Data files:
     - `profiles.json`: `ltx-2.5-fast` gets `plan`;
     - `precision_recipes.json`: add `processor` to the three LTX recipes' `include`.
   - PROTOCOL.md: a "Plans" section.
   - Tests:
     - `protocol/tests/test_plans.py`, covering every §6 defect verbatim, the join guard, the fit cases, revision
       fixity, truncation and the policy;
     - receipt byte-identity for old receipts;
     - `test_worker_image_pins` for the digest change;
     - a new `plans` vector group.
2. **Worker (`subnet/worker`; 2-3 days).**
   - New `backends/ltx_planner.py`: message building, `generate` on the loaded pipeline, the retry policy, and the
     per-shot policy check with regeneration.
   - `LtxResidentBackend.plans = True` and `plan(task, progress)`.
   - `worker.process`: the plan branch (no output frame check; seal the padded JSON; receipt with `plan`), and
     `features` at registration.
   - `backends/mock.py`: a deterministic valid plan for integration tests.
   - Fix the `enhance_prompt` safety gap.
   - Tests: `test_ltx_planner.py` with a scripted fake generator (broken JSON, a refusal, a blocked shot, short plans)
     and `test_worker_plan.py`.
3. **Gateway (`platform/gateway`; 2-3 days).**
   - `api_public.py`: accept `mode: plan`, plus the `/v1/plans` alias.
   - Routing and admission: `standard_jobs`, `envelopes` (`features` plus confidential tier).
   - `api_miner.py`: store `features`; accept plan output blobs and receipts without `video`.
   - `api_standard.py`: `POST/GET /v1/standard/plans`, with output decryption and the policy check.
   - Ledger and validator feeds: plan rows.
   - Limits: `plans_per_minute`.
   - Docs: STANDARD_MODE.md, PAYMENTS.md.
   - Tests: pricing, refund, routing to feature-less enclaves, Standard policy on output, receipt without video.
   - Remember that `/video/platform` is its own repo.
4. **Validator (`subnet/validator`; 1-2 days).**
   - `ledger.py`: plan rows skip duration checks and pay flat VCU.
   - `canaries.py`: plan canaries with must-mention terms (`--plan-canary`, `--standard-plan-canary`).
   - VALIDATING.md.
   - Tests.
5. **SDKs (`sdk/python`, `sdk/js`; 2 days).**
   - `plan`, `revise_plan` and `generate_storyboard`.
   - `Storyboard` and `PlannedShot`.
   - `fit_storyboard` in JS (a port of `plans.py`), checked against the vectors.
   - Error codes `plan_failed`.
   - READMEs.
6. **Studio (`platform/web`; 3-4 days).**
   - The plan panel in `StoryboardTray.tsx`.
   - `lib/plan.ts` (request, decrypt, load into the composer).
   - Beats and the Rewrite button on cards; repairs notices.
   - The `stage_storyboard` WebMCP tool.
   - `llms.txt`.
   - A Playwright spec against the mock worker (both projects, `--workers=1`).
7. **MCP server (parallel team; about 1 day on top).**
   - `plan_video`, `revise_plan`, `fit_storyboard` and `quote_price` as in §4.9.
   - Descriptions carry §5.1's rules and the privacy caveat.
8. **Integration (`/video/tests`; 1-2 days).**
   - Plan end to end in Private and Standard: SDK → gateway → mock worker → decrypt → fit → storyboard render → receipt.
   - Run `pytest` from `/video`: the full suites, not just `pytest subnet`.
9. **GPU validation (GPU; 1 day, about $5).**
   - Build the worker image at HEAD.
   - Run 20 briefs through the real worker on an RTX PRO 6000 (a new `KUNO_SMOKE_TASK=plan`). Record latency, output
     tokens, retry and repair rates, and policy blocks.
   - Render 3 plans as storyboards into `data/gpu-tests/` for the user to review.
   - Set `plan_usd` and `vcu_weights.plan` from the measured GPU-seconds.
   - Keep the 20-brief set as the regression set for every prompt change.

**Rollout order, as for storyboards:** protocol → validators → workers → gateway → SDKs → studio and MCP.
- Workers must advertise `plan/1` before the gateway routes plans to them.
- Rebuild and republish both images, because the digest changes when `processor` joins `include`.

**Total:** about 15-21 engineer-days plus about 1.5 GPU-days. The step 0 spike should come first, because its answer to
option B changes steps 2 and 9.

---

## 8. Open risks

1. **Planner quality.**
   - E2B is the smallest Gemma 4. The v1 product must present plans as drafts, and depends on the repairs.
   - The 12B test (step 0) is the main upgrade lever.
   - The sample is small: 5 briefs per model, one seed.
2. **LTX 12B generation is unknown.** If joint training broke its LM behaviour, option C needs new pinned weights and
   limits richer planning to H200/B200 workers.
3. **GPU latency and queueing.**
   - Unmeasured.
   - A plan takes a GPU worker's only job slot, so busy hours delay plans behind renders, and renders behind plans.
   - Watch queue time, and consider a CPU planner (option D) if plans pile up.
4. **Memory opportunity cost.** The idle enhancer may be costing C1 about 9 s of maximum shot length (§2.4). That
   decision is worth taking even if the Director waited.
5. **Unverifiable output.** Canaries catch canned or empty plans only. A plan is cheap and low-stakes, so this is
   accepted, as for storyboards.
6. **Prompt injection through the brief.** A brief can instruct the planner. Mitigations:
   - the per-shot content policy and classifier;
   - the refusal path;
   - the storyboard render re-checks every shot.

   A brief can't reach anything but its own plan: there are no tools and no other customers' data.
7. **Metadata.** Plan params reveal target length, frame and time. A plan followed by a storyboard from the same
   account is linkable by timing. Neither shows content.
8. **Licences.**
   - The bundled enhancer comes inside LTX-2.5-Diffusers under the LTX-2 Community License. Its base, Gemma 4, is
     Apache-2.0.
   - Our LTX usage already needs a commercial licence above $10M revenue. Planning adds no new licence.
   - Stock 12B and Qwen3.5 are Apache-2.0.
9. **Joins versus unfinished audio work.** `cut` with a carried voice is still marked experimental
   (`long-video_ltx-av-extend_2026-09-16.md` finding 3), yet the join guard converts most `continue` joins to `cut`.
   Until the listening test passes, the studio should default converted joins to `fresh` when the shot has no speech
   and no music bed.
10. **Languages.** One German brief worked. Other languages are untested, and the content policy is English-centric
    (`content_policy.py` trade-offs).

---

## 9. Sources

**Verified in code, image and file listings (2026-09-16)**
- `kuno-worker:ltx` image:
  - `diffusers/pipelines/ltx2/{pipeline_ltx2.py, prompt_enhancement.py, utils.py, duration_head.py}`
  - `transformers/models/gemma4_unified/modeling_gemma4_unified.py`
- `subnet/worker/src/kuno_worker/{worker.py, safety.py, backends/ltx_resident.py, backends/runtimes.py, backends/quantized.py, backends/resident.py}`
- `subnet/protocol/src/kuno_protocol/{schemas.py, profiles.py, profiles.json, precision_recipes.json, receipts.py, content_policy.py}`
- `subnet/PROTOCOL.md` ("Storyboards", "Sealed request padding"), `subnet/PRICING.md`
- `platform/gateway/src/kuno_gateway/api_public.py`, `platform/gateway/STANDARD_MODE.md`
- `sdk/python/src/kunoworld/client.py`, `sdk/js/src/client.ts`
- `platform/web/components/studio/StoryboardTray.tsx`, `platform/web/lib/{shot.ts, composerState.ts}`, `platform/web/components/studio.tsx`
- `scripts/gpu-test/smoke.py` (`fetch-weights`)
- Hugging Face file listing of `Lightricks/LTX-2.5-Diffusers@426936f8` (saved earlier), and the Hub API for
  `google/gemma-4-E2B-it`, `google/gemma-4-12B-it`, `Qwen/Qwen3.5-{2B,4B,9B,27B}`, `onnx-community/*-ONNX`, and the GGUF
  repositories

**Primary**
- Gemma 4 E2B model card: https://huggingface.co/google/gemma-4-E2B-it
- Gemma 4 12B model card: https://huggingface.co/google/gemma-4-12B-it
- Gemma 4 under Apache-2.0: https://opensource.googleblog.com/2026/03/gemma-4-expanding-the-gemmaverse-with-apache-20.html
- LTX-2.5 model card: https://huggingface.co/Lightricks/LTX-2.5
- LTX-2.5 text-encoder discussion (Lightricks staff): https://huggingface.co/Lightricks/LTX-2.5/discussions/34
- LTX prompting guide: https://docs.ltx.io/api-documentation/implementation-guides/prompting-guide
- Qwen3.5-4B model card: https://huggingface.co/Qwen/Qwen3.5-4B
- WebLLM: https://github.com/mlc-ai/web-llm
- llama.cpp server image: https://github.com/ggml-org/llama.cpp (build 10991, commit 930e2fa59)
- GGUFs:
  - https://huggingface.co/ggml-org/gemma-4-E2B-it-GGUF
  - https://huggingface.co/ggml-org/gemma-4-12B-it-GGUF
  - https://huggingface.co/unsloth/Qwen3.5-4B-GGUF
- Browser builds: https://huggingface.co/onnx-community/gemma-4-E2B-it-ONNX

**Secondary**
- LTX-2.5 release guide (fine-tuned Gemma 4 12B encoder, custom prompt enhancer): https://ltx23.org/blog/ltx-2-5-release-guide
- Runpod on LTX-2.5: https://www.runpod.io/blog/ltx-2-5-the-open-weights-world-model-built-for-speed-and-how-to-run-it-on-runpod
- Gemma 4 WebGPU speeds (search snippet): https://gemma4-ai.com/blog/webgpu-browser-guide
- Transformers.js Gemma 4 tutorial: https://pyimagesearch.com/2026/07/27/running-gemma-4-in-the-browser-with-transformers-js-and-webgpu/
- Community ComfyUI repack of the 12B encoder: https://huggingface.co/DeepNeuralNerd/Gemma-4-12B-it-uncensored-heretic-DeepNeuralNerd-LTX_2.5_ComfyUI
