# Measured render cost, 2026-09-16: H3 Turbo, and full H3 at 10 and 14 s

The question: can KunoWorld sell MiniMax H3 at fal's prices? On 2026-09-15 fal cut H3 Max 768p to $0.04/s and H3 Max
Turbo 768p to $0.02/s until September 30; after that, list prices are $0.08 and $0.04. At the 2026-09-15 measurement,
full H3 costs us $0.14/s. `h3-turbo` had never run. This run measures it, and fills in the duration factor that
[PRICING.md](../../subnet/PRICING.md) §6 asked for.

**Setup.** Shadeform excesssupply 8x H200 141 GB, `tokyo-japan-5`, $32/h. The region check passed: JP, and not in the
licence's Excluded Territories. Active 34 min, about $18.

- **Image:** `vocence/kunoworld-worker:h3-0.1.0-0ad70874cd6b`, running SGLang 0.5.19 from `/opt/sglang`.
- **Weights:** `MiniMaxAI/MiniMax-H3@42ed227e` (FL2VA). Turbo LoRAs `lightx2v/Minimax-h3-Turbo@3ec17a32`: `..._8step_v1.0_768p_bf16` and `..._4step_v1.0_768p_bf16`.
- **Client:** straight against `sglang serve` over HTTP. No gateway, worker, safety check or sealing.
  - Those add about 2-5 s per job: on 2026-09-15 the `h3` 5 s job took 82 s through the worker, and today the same request took 76.5 s straight to SGLang.
  - The runner scripts are in `scripts/gpu-test/h3_sglang/`.
- **Requests:** 1344x768, `t2va`, seed 1234. Turbo with `flow_shift` 6 and `audio_flow_shift` 3, the LoRAs' training shifts.
- **What it isn't:** single runs, no confidential-computing mode. CC costs an estimated 15-25% more; that has not been measured.

## Step counts: SGLang runs one model pass fewer than the number it is given

SGLang's H3 schedule is `linspace(1, 0, num_inference_steps)`, and the last point (0) is not a model pass. So
`num_inference_steps: 8` runs **7** passes, and `4` runs **3**. The full-H3 server log confirms this: "0/49" for 50.

LightX2V trains Turbo for N passes on the grid `q_i = (N - i)/N` ([Turbo README, "Note on shift"](https://github.com/ModelTC/Minimax-H3-Turbo)).
That grid is `linspace(1, 0, N + 1)`, so **Turbo 8-step needs `num_inference_steps: 9`** (and 4-step needs 5).

This run sent 8 and 4, as the worker's `h3_resident.build_call` does with `profile.steps`, and diffusers counts the same
way. The runs below therefore used one pass fewer than the LoRA expects, on a slightly different grid.
- **Timings:** corrected by adding one measured pass, from each request's own `MiniMaxH3DenoisingStage` time.
- **Quality:** the 4-step clip's problems below may come partly from this.

Full H3 ran 49 passes: MiniMax's own SGLang example sends 50. The worker now sends passes + 1 for every H3 profile
(`kuno_protocol.profiles.h3_schedule_points`), so its `steps: 50` and verified mode's `stage_steps: [50]` mean the same
50 passes. That is one more than MiniMax's example, and about 2% more time than the full-H3 numbers below.

## Results

Wall time is from submit to completion. GPU-s/s is GPU-seconds per second of output (frames / 24); 4 GPUs count 4x.
Cost uses a confidential H200 at $4.80/GPU-h and 60% utilization. The floor is cost × 1.25 / 0.60, the smallest
customer price that pays a miner the PRICING.md rate while leaving 40% for everything else.

### As run

| Profile, GPUs | Passes | 5 s | 10 s | 14 s |
|---|---|---|---|---|
| Turbo 8-step, x4 | 7 | 13.6-14.0 s wall, **10.5-10.8** | 35.0 s, **13.8** | 61.1-62.2 s, **17.0-17.3** |
| Turbo 8-step, x1 | 7 | 45.7 s, **8.8** | – | 227 s, **15.8** |
| Turbo 4-step, x4 | 3 | 7.4 s, **5.7** | – | 29.7 s, **8.3** |
| Turbo 4-step, x1 | 3 | 22.9 s, **4.4** | – | 106 s, **7.4** |
| Full H3, x4 | 49 (reference) | 76.5 s, **59.2** | 218 s, **86.0** | 392 s, **109.0** |

### Corrected to the LoRAs' pass counts, with cost

| Profile, GPUs | 5 s: GPU-s/s, cost, floor | 10 s | 14 s |
|---|---|---|---|
| **Turbo 8-step, x4** | 11.5, $0.026, **$0.053** | 15.3, $0.034, **$0.071** | 19.0, $0.042, **$0.088** |
| Turbo 8-step, x1 | 9.7, $0.022, $0.045 | – | 17.6, $0.039, $0.082 |
| Turbo 4-step, x4 | 6.4, $0.014, $0.030 | – | 9.8, $0.022, $0.045 |
| Turbo 4-step, x1 | 5.1, $0.011, $0.024 | – | 8.8, $0.020, $0.041 |
| Full H3, x4 | 59.2, $0.132, **$0.274** | 86.0, $0.191, **$0.398** | 109.0, $0.242, **$0.505** |

Per pass, 4 GPUs: 1.06-1.30 s at 5 s, 3.8 s at 10 s, 5.6-6.9 s at 14 s. The 8-step LoRA loaded at server start was
about 20% slower per pass than the 4-step LoRA switched in later through `/v1/set_lora`. The cause (merged or dynamic
LoRA) is unconfirmed.

Outside the denoising loop, each request took about 3 s at 5 s and about 9 s at 14 s (decode 1.3 s and 3.7 s, text
encoding 0.1 s).

**Load and switching.** A 4-GPU server became ready in 148-203 s, a 1-GPU server in 183-184 s. `POST /v1/set_lora`
changed the LoRA on a running server in 15 s.

**Memory.**
- **One server:** a 4-GPU server holds 87-97 GB per GPU once loaded and peaks at about 103 GB per GPU.
- **1 GPU:** peaks at 137.6 GB at 14 s (8-step) and 138.9 GB (4-step), leaving 2-3 GB of an H200's 141 GB.
- **Two servers on the same GPUs:** 87-97 GB each would not fit. That is what `kuno-h3-worker` starts for a worker with both `h3` and `h3-reference` (fl2va and ref2va on the same 4 GPUs).
  - It has never run together: the 2026-09-15 smoke test ran one profile per worker. On H200 and B200 it will almost certainly run out of memory; B300 (288 GB) should fit.

## Quality, from the videos

Frames and spectrograms were checked. There is no transcription; the clips are in `data/gpu-tests/ltx-2.5/`, prefix `repro-20260916`.

- **Picture.**
  - **Same seed:** the lighthouse prompt with 2026-09-15's seed gives the same composition under full H3, Turbo 8-step (x4 and x1) and Turbo 4-step. None of the four looks visibly worse.
  - **Dialogue:** Turbo 8-step's chef clip matches the prompt, one chef talking to camera. Turbo 4-step's version added a second chef the prompt never asked for.
- **Audio.**
  - **Ambience:** under Turbo, the lighthouse ambience is about 20 dB quieter than full H3's (mean -43 vs -23 dB). The community's "audio degrades under Turbo" note matches.
  - **Speech:** Turbo 8-step's chef spectrogram shows clean voiced speech with pauses, at a normal level (mean -26 dB). Turbo 4-step's is denser and noisier.
- **Caveat:** all Turbo clips ran one pass short (above), so this is a lower bound on Turbo quality.

## What this means for pricing

Against fal (768p, per second, flat at any duration):

| | fal list | fal until 09-30 | Our floor at 5 s | Our floor at 14 s | Today's price, Standard / Private |
|---|---|---|---|---|---|
| Turbo | H3 Max Turbo $0.04 | $0.02 | 8-step $0.053; 4-step $0.030 | 8-step $0.088; 4-step $0.045 | $0.05 / $0.065 |
| Full | H3 Max $0.08 (plain H3 $0.06) | $0.04 | $0.274 | $0.505 | – / $0.20 |

1. **Full H3 cannot be sold near fal's price.** Its floor is 3.4x fal's H3 Max list at 5 s and 6.3x at 14 s. The
   current $0.20 Private price is below its own floor at every length. At 14 s a clip costs miners more than we charge.
2. **Turbo 8-step can sell at about $0.05-0.06/s if clips stay short.** At 5 s the floor is $0.053. Per-second cost
   rises 1.3x at 10 s and 1.65x at 14 s, so one flat price either overcharges short clips or loses money on long ones.
   Price per duration band, or cap Turbo at 10 s.
3. **Only 4-step Turbo comes near fal's $0.04 list.** Its floor is $0.030 at 5 s and $0.045 at 14 s (10 s was not
   measured). Its quality has to be checked with the correct pass count before anyone sells it.
4. **fal's $0.02 promotion is below our 4-step floor.** It is not a price to match.
5. **One GPU is 15-20% cheaper per GPU-second but has no headroom on an H200.**
   - It is 3.3-3.7x slower per clip: 50 s for a 5 s clip, 253 s for 14 s.
   - It peaks at 138-139 GB of 141 GB.
   - A 1-GPU Turbo class would suit B200 or B300. It is also the only way H3 escapes the whole-8-GPU-server rule for
     confidential multi-GPU VMs, since single-GPU confidential VMs are far easier to rent.

### VCU weights (cost-normalized, `ltx-2.5-fast` 720p = 3 at $0.0041/s)

| Profile | In `profiles.json` | Measured, 5 s | Duration slope in `profiles.json` | Measured slope |
|---|---|---|---|---|
| `h3-turbo` (8 passes, x4) | 17 (estimate) | **19** | 0.05 | **0.072** (1.33x at 10 s, 1.65x at 14 s) |
| `h3` | 100 | **96** (today) / 101 (09-15) | 0.06 | **0.093** (1.45x at 10 s, 1.84x at 14 s) |

The slope column fits `1 + slope × (d − 5)` to the measured per-second cost at 10 and 14 s.

## Next

1. **Fix the step count** in the worker (`num_inference_steps` = passes + 1 for Turbo) and re-render the Turbo clips.
   This matters most for the 4-step quality verdict. It needs another H3-capable rental.
2. **Serve Turbo through SGLang** (`--lora-path`, fl2va) rather than the in-process diffusers pipeline. Today the
   worker's image lacks `peft`, which diffusers' `load_lora_weights` needs, so `h3-turbo` would fail on its first job.
   SGLang also runs faster (LMSYS measured diffusers at 1.9x slower).
3. **Stop running fl2va and ref2va on the same GPUs.** On H200 and B200, give each C4 worker one variant.
4. **Update `profiles.json`:** `h3-turbo` weight 19 and slope 0.072; `h3` slope 0.093.

## Update, 2026-09-17

- **Done:** item 1 (passes + 1, confirmed through the worker at 8 and 50 passes), item 2 (Turbo on its own SGLang
  server), item 3 (one H3 load per worker, refused otherwise) and item 4 (`profiles.json` weights).
- **One GPU:** `h3-turbo` now serves on one GPU, with VCU 18 and slope 0.08 for one-GPU serving through the worker. The
  VCU table above describes four-GPU serving against SGLang directly.
- **Private-only:** full `h3` and `h3-reference` are Private-only.
- **Details:** `research/h3-image-check_2026-09-17.md`.
