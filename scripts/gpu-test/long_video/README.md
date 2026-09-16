# Long videos from chained LTX-2.5 shots (AV-extend)

This experiment asks one question before we build anything into the product: **can LTX-2.5 make a long video by
chaining ordinary shots, so that the joins cannot be seen or heard?** It runs on one rented GPU (the RTX PRO 6000 the
smoke test used), with the worker image and weights `ltx-smoke.sh` already put there.

Every shot is one normal LTX-2.5 generation, built by the worker's own `build_call`. A shot attaches to the one before it
in one of three ways, the technique of [ComfyUI-JoyLTX25](https://github.com/jlucasmcrell/ComfyUI-JoyLTX25) (MIT):

| Join | What is pinned at the head of the new shot | Meant to give |
|---|---|---|
| `continue` | the previous shot's last `--overlap` video latent frames, and the matching audio latents | one seamless take: same room, same motion, same sound |
| `cut` | the audio latents only | a new picture, but the voice and room tone carry across |
| `fresh` | nothing | an independent shot |

"Pinned" means the tokens are written at the head of the new shot's latents and never change while it is denoised. The
head is trimmed from the new shot's frames and samples before the shots are concatenated.

Everything is in this folder; nothing under `subnet/` or `platform/` changed.

| File | What it is |
|---|---|
| `ltx_extend.py` | The runner. Runs inside the worker image: `real` backend on the GPU, `tiny` and `fake` on the CPU. |
| `run.sh` | Runs `ltx_extend.py` in the worker image on the GPU box: prerequisites, GPU memory sampling, tarball. |
| `storyboards/` | `mixed-joins` (quick, every join once), `harbor-continue` (a seamless take), `narrator` (one voice over cuts). |
| `test_ltx_extend.py` | The index math, the pins, and whole fake and tiny runs. |

## How the pin is held

This is from diffusers 0.40's own source in the image (`pipelines/ltx2/pipeline_ltx2_condition.py`,
`models/transformers/transformer_ltx2.py`, `schedulers/scheduling_flow_match_euler_discrete.py`).

**Video uses the model's native mechanism.** `LTX2ConditionPipeline.prepare_latents` returns a per-token
`conditioning_mask`. Its loop does two things with the mask:

- It passes the transformer `timestep * (1 - mask)` per token, so masked tokens are seen as clean context at t = 0.
- It blends `x0 = denoised * (1 - mask) + clean * mask` before the Euler step, so a masked token's velocity is exactly
  zero.

This is how the pipeline holds an image-to-video first frame. The only thing `LTX2ExtendPipeline` changes is what sits
at the head: the pipeline puts VAE-encoded pixels there, and we put the previous shot's own latent tokens, with mask 1.

**Audio has no native mask in diffusers.** Every LTX2 pipeline passes one audio timestep per batch row. However, the
transformer documents and accepts `audio_timestep` of shape `(batch, audio_tokens)`, and its blocks read the per-token
shape generically. So a forward pre-hook turns the audio timestep into `t * (1 - audio_mask)`, and
`prepare_audio_latents` writes the tail. Nothing blends the audio x0, so the pipeline's `audio_scheduler` component is a
`PinnedScheduler`, which writes the pinned tokens back after every step.

The instruction to prefer a native mechanism was right. Re-imposing after the step alone would leave the model looking
at a noised copy of the context. The fake backend's stand-in model only continues context it receives at timestep 0, so
the tests fail if either half of this is missing.

**Both passes are pinned.** The distilled `ltx-2.5-fast` recipe renders at half size, upsamples the latents x2, then
refines at full size (`runtimes.LtxAdapter._two_stage`). Each pass is pinned from the previous shot's tokens of the
*same* pass, so the refine cannot redraw the join. The tails are each pass's final scheduler tokens: the pipeline's own
normalized, packed space. Nothing is decoded, re-encoded or re-normalized between shots.

**Every run proves the mechanism in `results.json`.** Two fields per shot and pass:

- `pins_exact`: the pinned tokens came out of denoising bit-identical.
- `pinned_head_seen_at_t0`: the transformer's first call actually received timestep 0 on the head and noise levels
  above 0 everywhere else.

If either is false, the run fails.

## Geometry, and how much is trimmed

Read from the loaded pipeline. These are LTX-2.5's, confirmed by the 2026-09-15 GPU run (49 frames and 96,480 samples
for 2 s):

- **Video:** the VAE is causal, 8x in time and 32x in space. n latent frames decode to `1 + 8(n - 1)` frames.
- **Audio:** 16 kHz mel at hop 160, 4x in time, so 25 latents per second. The audio VAE is causal too: n latents decode
  to `4n - 3` mel frames. The vocoder with bandwidth extension gives 480 samples per mel frame at 48 kHz.
- **The default overlap of 3** pins 3 latent frames and trims **17 frames** (0.71 s at 24 fps). The audio pin is
  **18 latents**, trimmed as **33,120 samples**.
- **Stitched length** = the sum of the shots' frames − 17 per `continue` or `cut` join. A `cut` trims the same span: those
  frames were drawn under the previous shot's replayed sound.

The audio pin count is chosen, not proportional. JoyLTX25 takes `round(audio_latents × overlap / latent_frames)`, which
is 22 for 2 s shots. That ignores that both VAEs are causal: the pinned sound would sit 173 ms off the pinned picture,
and about 140 ms of the previous shot's sound would be heard twice.

Here the planner (`Timeline`) takes the count whose decoded span best lines the new shot's audio clock up with its video
clock in the stitched output, given every earlier join:

- **Sound that runs straight through** (the pin is the previous shot's own tail) continues it sample for sample, and
  stays within ±20 ms of the picture. The error never accumulates; the tests check 29-shot chains at 24, 25, 48 and 50 fps.
- **Sound that cannot run through** (a `fresh` shot, or a pin anchored to an earlier shot) starts exactly in sync. The
  previous shot's audio is padded to fit: the vocoder returns about 32 ms less audio than a shot's picture. A 5 ms fade
  on either side prevents a click.

Two more cases:

- **Overlap too short for the sound.** If the overlap trims less picture than the previous shot's audio falls short (only
  `--overlap 1` at 50 fps), that join pads instead of drifting and says so in `notes`.
- **Decoder mismatch.** If the real decoder ever returns a different sample count than the causal rule predicts, the trim
  is rescaled, and `notes` and `warnings` say so.

**`--audio-anchor`** sets where a join's audio pin comes from:

- `first` (the default, as in JoyLTX25 1.2.1): the first shot of the current run of joined shots. This is against voice
  drift: "by shot six the speaker was somebody else".
- `previous`: the shot just before, so the sound runs straight through every seam.

With `first`, only the first join's sound can run through. Later seams are sound-discontinuous by design.

## Run it on the GPU box

**Before you start:**

- `ltx-smoke.sh` has run on this machine at least once, so the worker image is pulled and the weights are in
  `$KUNO_SMOKE_DIR/models/ltx-2.5`. The default downloads both profiles; `ltx-2.5-pro` needs `transformer_full/`.
- Copy this folder over: `scp -r scripts/gpu-test user@gpu-box:~/gpu-test`.
- Run inside `tmux`. No tokens are needed: nothing is downloaded.

```bash
cd ~/gpu-test/long_video
export KUNO_SMOKE_DIR=/data/kuno-smoke            # wherever the smoke test put its weights
export KUNO_EXTEND_COPY_TO=~/repro                # optional: data/gpu-tests/tools/sync.sh copies ~/repro/*.mp4 home

./run.sh storyboards/mixed-joins.json --plan-only                          # 1. the join table, no model loaded (seconds)
./run.sh storyboards/mixed-joins.json                                      # 2. quick check: every join mode once
./run.sh storyboards/harbor-continue.json --audio-anchor previous          # 3. a seamless 18 s take
./run.sh storyboards/narrator.json --audio-anchor first                    # 4. one voice across cuts, anchored...
./run.sh storyboards/narrator.json --audio-anchor previous                 #    ...and walking, to compare
./run.sh storyboards/mixed-joins.json --profile ltx-2.5-pro                # 5. optional: the 30-step model, one pass
./run.sh storyboards/harbor-continue.json --audio-anchor previous --overlap 6   # 6. optional: a longer overlap
```

Any `ltx_extend.py` flag goes after the storyboard. The main ones:

| Flag | Default |
|---|---|
| `--profile` | `ltx-2.5-fast` |
| `--resolution`, `--aspect`, `--fps` | `720p`, `16:9`, the profile's 24 |
| `--seed` | `1234`; shot N renders with seed + N − 1 |
| `--overlap` | `3` |
| `--audio-anchor` | `first` |
| `--offload` | `auto`: none, on a 96 GB card with no hardware class |
| `--vae-tiling` | off |
| `--no-shot-videos` | off |

`run.sh` settings:

| Variable | Default |
|---|---|
| `KUNO_SMOKE_DIR`, `KUNO_SMOKE_MODELS_DIR` | as in `ltx-smoke.sh` |
| `KUNO_EXTEND_IMAGE` | `KUNO_SMOKE_WORKER_IMAGE`, else the smoke default `ghcr.io/concil859856/kunoworld-worker:ltx-0.1.0-0ad70874cd6b` |
| `KUNO_EXTEND_BACKEND` | `real` (`tiny` or `fake` need no GPU) |
| `KUNO_EXTEND_OUT` | `$KUNO_SMOKE_DIR/extend/<UTC stamp>-<storyboard>` |
| `KUNO_EXTEND_COPY_TO` | unset |

It exits with 0 if every shot rendered with exact, t = 0 pins and the stitched frame count matched the plan. It exits
with 1 otherwise, and with 2 if a prerequisite is missing.

### Expected time and memory

These are **estimates**, scaled from the one measured point: `ltx-2.5-fast` at 2 s 720p took 6.4 s of generation and
peaked at 87–88 GB. Only the run itself will measure them.

| Step | Estimate |
|---|---|
| Load: size check, no hashing; weights in page cache | 1–2 min per run |
| `ltx-2.5-fast`, one 3 s shot | about 10–15 s to generate, plus 5–10 s to encode that shot and add it to the stitch |
| `ltx-2.5-fast`, one 5 s shot | about 20–40 s, plus about 10–15 s |
| `mixed-joins` (4 × 3 s) | about 3 min |
| `harbor-continue`, and each `narrator` run (4 × 5 s) | about 4–5 min |
| `mixed-joins` on `ltx-2.5-pro` (4 × 3 s, 30 steps with guidance) | about 10–20 min |
| Steps 1–4 above | about 20 min |

**Memory.** Weights are about 72 GiB in bf16; the precision recipe estimates 1.6 GiB per 10k latent tokens on top. A 5 s
720p shot is 14,080 tokens against 6,160 for 2 s, so expect a few GB more than the smoke test's 88 GB.

On `CUDA out of memory`:

1. Add `--vae-tiling`.
2. Use `--offload model`, which is slower.
3. Use shorter shots.

A failure mid-run still stitches the shots rendered before it (`stitched.partial` in `results.json`).

## What to look at

The output lives in `$KUNO_SMOKE_DIR/extend/<stamp>-<storyboard>/`, with a `.tar.gz` of it beside:

| File | What it is |
|---|---|
| `stitched.mp4` | The long video: H.264 CRF 18, AAC 48 kHz. |
| `stitched.wav` | Its sound, lossless. Look here for clicks. |
| `seams.png` | One row per join: the last kept frame before it, the first kept frame after it, with the two measures below. |
| `shots/NN-<join>.mp4` | Each shot as rendered, untrimmed. For `continue`, its first 0.71 s replays the end of the shot before. |
| `results.json` | Settings, geometry, the plan and the actual join table, per-shot timings, peak GPU memory, seams. |
| `run.log`, `samples.csv` | The run's output, and host RAM and GPU memory once a second. |

**First, the mechanism.** `RESULT: PASS` means all of these held:

- every pinned pass had `pins_exact: true` and `pinned_head_seen_at_t0: true`;
- the stitched video has `expected_frames`;
- `decoded_audio_samples == predicted_audio_samples` for every shot.

Otherwise there is a line under `warnings`.

**Then the pictures.** Watch `stitched.mp4` around each `seams[].time_s`.

- **`continue` seams:** the `seams.png` pair should look like two adjacent frames. `video_step_ratio` compares the change
  across the seam with an ordinary frame step: about 1–3 is seamless, and tens is a pop. A cut or fresh seam is expected
  to be large.
- **Drift over a take:** in `harbor-continue`, compare shot 1 with shot 4. Look at the boat's colour and shape, the light,
  and the grain. A slow drift is the known risk of chaining; a jump at a seam is a failure of the pin.
- **Sound at seams where it runs through** (`audio_continuous: true`): `audio_jump_ratio` near 1 means no click. Listen
  anyway; the ratio is a heuristic.
- **The narrator:** is the voice in shot 4 the voice of shot 1? Compare the `--audio-anchor first` and `previous` runs.
  Also listen for words clipped at a seam. A `cut` join trims 0.71 s of the new shot's head, so a line spoken right at
  its start can lose its first syllable.
- **`sync_error_ms`:** within ±20 ms by construction. If lips or motion look off by more, that is the model, not the
  stitch.

**What would count as "yes, build it":** `continue` seams that cannot be spotted at normal speed, no clicks, and the
same voice across the narrator's four shots with at least one anchor setting. Drift over four shots should be no worse
than within a single 20 s generation.

## Checking it without a GPU

Everything except the real weights runs on the CPU in the worker image (the tests pass in `kuno-worker:ltx` and in
`ltx-0.1.0-0ad70874cd6b`):

```bash
cd scripts/gpu-test/long_video
# The CPU stand-in, full flow, in seconds (writes to /tmp/extend-fake):
mkdir -p /tmp/extend-fake && docker run --rm -v "$PWD:/w:ro" -v /tmp/extend-fake:/out --user "$(id -u):$(id -g)" \
  -e HOME=/tmp -e USER=kuno --entrypoint python kuno-worker:ltx -W ignore /w/ltx_extend.py /w/storyboards/mixed-joins.json \
  --fake --size 320x192 --out /out
# The same through diffusers' real classes with tiny random weights: --backend tiny instead of --fake.

# The tests: the math on the host (the torch tests skip there)...
cd /video && uv run pytest scripts/gpu-test/long_video -q
# ...and all of them inside the image, with the host venv's pure-Python pytest mounted in:
S=/video/.venv/lib/python3.12/site-packages; docker run --rm -v /video/scripts/gpu-test/long_video:/w:ro \
  $(for m in pytest _pytest pluggy iniconfig py.py; do printf -- '-v %s/%s:/pt/%s:ro ' "$S" "$m" "$m"; done) \
  -e PYTHONPATH=/pt -e PYTHONDONTWRITEBYTECODE=1 -w /tmp --entrypoint python kuno-worker:ltx -m pytest /w -q -p no:cacheprovider
```

**`fake`** is plain torch with LTX-2.5's geometry. Its stand-in model writes a clock into each token, counted on from
whatever clean context it is shown, and decodes it through the causal VAEs' frame layout. The tests check that stitched
clocks advance by exactly one frame, and one sample, across every seam that should be continuous.

**`tiny`** builds `LTX2ConditionPipeline`, its transformer, both VAEs, the vocoder with bandwidth extension, the
connectors and the latent upsampler, all with tiny random weights and LTX-2.5's geometry. It includes the LTX-2.3+
prompt-modulation branch. It runs this script's real extension path through both passes of `ltx-2.5-fast`, and through
the one CFG pass of `ltx-2.5-pro` with STG and modality guidance. The pictures are noise; the shapes, hooks, token counts
and decoded lengths are the real code's.

## Not verified without the GPU

- **Whether LTX-2.5's weights continue well from pinned context.** This is the experiment itself. For video, the mask
  is the one image-to-video uses, and multi-frame heads are what the pipeline's own video conditioning does. For audio,
  clean audio context through per-token timesteps is what ComfyUI's noise mask does (JoyLTX25's route), but diffusers
  never exercises it.
- **Timings and peak memory** for 3–5 s shots, and whether `--offload model` or `group` work with the extension
  pipeline sharing the loader's hooked modules. Only `none` is expected on the 96 GB card.
- **The loader call itself** (`ltx_loader(...)(profile)`) is the smoke test's; it ran on this GPU, but not from this
  script.
- **Quality at the trim points:** the VAE and vocoder decode the new shot's first kept frames and samples with different
  context than the previous shot had.
- **Fresh shots are not pixel-identical to a worker render with the same seed.** All shots go through
  `LTX2ConditionPipeline`, which draws noise in packed order, while the worker's text-to-video uses `LTX2Pipeline`.
