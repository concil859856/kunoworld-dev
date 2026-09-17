# The H3 worker image on 8x H200, and SageAttention (2026-09-17)

**What this settles.** The H3 image had three changes that had never run on a GPU: Turbo on its own SGLang server with
the LightX2V LoRA, the refusal to load H3 twice on one worker's GPUs, and per-GPU-group profiles. It also measures
SageAttention, which `attention-bottleneck_nunchux_2026-09-17.md` recommended trying, and 4K on an H200.

**Setup.** Shadeform excesssupply 8x H200 141 GB, `tokyo-japan-5` (the API reports JP, Kagawa), $32/h. The region check
passed before any H3 download. Active 19:06-19:41 UTC, **$20.60**.
- **Images:** worker `h3-0.1.0-69e34d62492b` (`sha256:35150d43cedc…`) and `ltx-0.1.0-69e34d62492b`
  (`sha256:8289612b104a…`), gateway `cc8e9fb2553d`, mock-worker `69e34d62492b`.
- **Weights:** `MiniMaxAI/MiniMax-H3@42ed227e` (FL2VA) and `lightx2v/Minimax-h3-Turbo@3ec17a32`
  (`..._8step_v1.0_768p_bf16`, 1.38 GB).
- **Driver:** `scripts/gpu-test/ltx-smoke.sh` with the new `KUNO_SMOKE_GPUS` and `KUNO_SMOKE_GROUPS`, Private, JP.
- **Capacity:** four earlier creates of the same offer never provisioned and were deleted at $0 each. A listing marked
  "available" does not mean the provider will deliver.

## 1. H3 through the worker and a real gateway: both profiles pass

Private jobs, 5 s at 1344x768, 24 fps, sealed by the SDK and opened against the receipt.

| Profile | Worker start to registered | Job | Render (receipt) | GPU-seconds | GPU-s per output second | Peak per GPU |
|---|---|---|---|---|---|---|
| `h3-turbo` (8 passes, 4 GPUs) | 219 s | 22.2 s | 20.2 s | 80.6 | **15.6** | 96.7 GB |
| `h3` (50 passes, 4 GPUs) | 170 s | 84.4 s | 82.5 s | 329.8 | **63.8** | 95.2 GB |

- **Every check passed:** the MP4 is 124 frames of H.264 with AAC, and its SHA-256 is the receipt's `content_digest`.
- **Pass counts are right.** The worker's log shows progress bars totalling 8 for Turbo and 50 for full H3, so the
  `passes + 1` fix (`h3_schedule_points`) reaches SGLang correctly.
- **Turbo is 4.1x faster than full H3** for the same clip.

## 2. One H3 load per worker, and two GPU groups

- **The refusal works.** `kuno-h3-worker` with `KUNO_PROFILES=h3-turbo,h3` exits 1 and explains that two H3 loads
  don't fit on 141 GB H200s, pointing at GPU groups or `KUNO_H3_SHARED_SERVERS=1`.
- **`KUNO_H3_SHARED_SERVERS=1` plans both servers** (fl2va on 30010, turbo with `--lora-path` on 30012), as designed
  for 288 GB B300s. It was not run.
- **Two groups on one machine pass:** one worker per group against one gateway, `h3-turbo` on GPUs 0-3 (job 20.2 s) and
  `h3` on GPUs 4-7 (job 84.4 s), each registering its own enclave with its group's GPUs. Group timings match the
  single-group runs, so sharing a host costs nothing measurable.

## 3. SageAttention on H3 Turbo: 6.5% faster, close to the same picture

The `sageattention` package is not in the image. Building it on the box took 234 s (nvcc 13.4 against CUDA 13.0 headers
needs `-DCCCL_DISABLE_CTK_COMPATIBILITY_CHECK`, and libcuda must be on the link path). SGLang's log names the backend it
runs, so this is not a silent fallback.

| Run (1 GPU, Turbo 8 passes, 5 s, seed 1234) | Backend in the log | Wall | GPU-s per output second |
|---|---|---|---|
| A | `fa` (FlashAttention) | 51.26 s | 9.92 |
| B | `sage_attn` | 47.95 s | **9.28** |

- **Speed:** 6.5% faster end to end, in line with the paper's 13% for 8-bit attention on an H200 (which measured a
  larger model with more tokens).
- **Quality:** B against A is 30.2 dB PSNR and 0.925 SSIM. That is far closer than SageAttention2's 19.9 dB against
  BF16 in the VC-Attention paper, because Turbo runs 8 passes rather than 50, so trajectories diverge less.
- **Deterministic:** each backend repeated its own clip bit-identically.
- **Memory:** 128.9 GB peak against 126.6 GB, so it costs about 2 GB.

## 4. What this means for H3 pricing

Cost is GPU-seconds per output second at $4.80 per confidential H200-hour and 60% utilization; the floor is
cost x 1.25 / 0.60, the smallest price that pays a miner the PRICING.md rate and leaves 40% for everything else.

| Serving | GPU-s/s | Cost per output second | Floor | Our price (Standard / Private) |
|---|---|---|---|---|
| `h3-turbo`, 4 GPUs, through the worker | 15.6 | $0.035 | **$0.072** | $0.05 / $0.065 |
| `h3-turbo`, 1 GPU, FlashAttention | 9.92 | $0.022 | **$0.046** | $0.05 / $0.065 |
| `h3-turbo`, 1 GPU, SageAttention | 9.28 | $0.021 | **$0.043** | $0.05 / $0.065 |
| `h3` (full), 4 GPUs, through the worker | 63.8 | $0.142 | **$0.295** | - / $0.20 |

1. **Serve Turbo on one GPU, not four.** On four GPUs its floor ($0.072) is above both our prices; on one GPU it fits
   under them. One GPU was already 15-20% cheaper per GPU-second on 2026-09-16; the worker's overhead makes the gap
   decisive. It also needs no multi-GPU confidential VM.
   - **Caveat:** a 1-GPU H200 peaks at 126-129 GB of 141 GB for a 5 s clip, and the 2026-09-16 run peaked at 138-139 GB
     at 14 s. Cap 1-GPU Turbo's length, or give it a B200/B300.
2. **SageAttention is worth adopting for Turbo** once its quality is judged by eye: 6.5% cheaper for 2 GB of memory,
   with the same picture to 30 dB. It needs a package built into the image, not a flag, and its own precision recipe.
3. **Full H3 is still far below its floor** ($0.295 against $0.20 Private), as measured before. Either raise the price,
   cap its length, or serve it only where GPUs are cheaper.
4. **`h3-turbo`'s VCU weight** (19 at 768p, slope 0.072) matches 4-GPU serving. If Turbo moves to one GPU, re-measure
   it: 1-GPU serving is about 0.6x the cost.

## 5. 4K on an H200 (`ltx-2.5-4k`)

The 4K envelope for H200s was extrapolated from an RTX PRO 6000. Both cells at the profile's maximum length were
rendered on one H200 each, concurrently with the H3 runs.

| Clip | Frames | Tokens | Wall (render + decode) | Render peak | Decode peak | Admission (render / decode) |
|---|---|---|---|---|---|---|
| 1440p, 10 s | 241 | 109,120 | 326 s (102 + 217) | 82.59 GiB | 91.27 GiB | 84.46 / 93.39 |
| 2160p, 10 s | 241 | 252,960 | 811 s (429 + 368) | 102.64 GiB | **111.92 GiB** | 104.88 / 116.73 |

- **Both passed**, with frames, size and sound correct, and every peak inside admission's estimate by 1.9-4.8 GiB.
- **The refit model extrapolates well:** it was fitted on a 94.97 GiB card at up to 109,120 tokens, and it held at
  252,960 tokens on a 139.8 GiB card.
- **The H200 serves the whole profile** at 24/25 fps (10 s at both sizes) and 2160p 7 s at 48/50 fps.
- **Cost:** 2160p is 81 GPU-seconds per output second, 1440p 33. At $4.80 per H200-hour and 60% utilization that is
  $0.18 and $0.073 per output second, against prices of $0.39 and $0.25 Private. An RTX PRO 6000 is much cheaper for
  1440p (29 GPU-s/s at $1.879/h).

## Next

1. **Watch the Turbo clips** (`data/gpu-tests/ltx-2.5/smoke-20260917T191725Z_h3-turbo.mp4` and the SageAttention pair)
   against 2026-09-16's 7-pass clips, to confirm the quality of 8 real passes and of SageAttention.
2. **Decide 1-GPU Turbo serving** (a new hardware class and envelope), and re-measure its VCU weight.
3. **Decide on SageAttention** in the H3 image: it adds a build step and a second attention implementation to pin in
   the recipe.
4. **Full H3's price** needs an owner decision (§4).
