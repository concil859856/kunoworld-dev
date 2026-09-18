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

## 3. SageAttention on H3 Turbo: 6.5% faster, the same scene framed differently

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
  - **Correction, 2026-09-18:** looking at the frames, it is not the same picture. The scene, light and colour
    match, but the cliff and the lighthouse sit in different places. The PSNR is high because most of the frame
    is dark silhouette and smooth sky. The decision rests on whether B looks as good, not on the metric.
- **Deterministic:** each backend repeated its own clip bit-identically.
- **Memory:** 128.9 GB peak against 126.6 GB, so it costs about 2 GB.

## 4. What this means for H3 pricing

Cost is GPU-seconds per output second at $4.80 per confidential H200-hour and 60% utilization; the floor is
cost x 1.25 / 0.60, the smallest price that pays a miner the PRICING.md rate and leaves 40% for everything else.

| Serving | GPU-s/s | Cost per output second | Floor | Our price (Standard / Private) |
|---|---|---|---|---|
| `h3-turbo`, 4 GPUs, through the worker | 15.6 | $0.035 | **$0.072** | $0.04 / $0.065 |
| `h3-turbo`, 1 GPU, FlashAttention | 9.92 | $0.022 | **$0.046** | $0.04 / $0.065 |
| `h3-turbo`, 1 GPU, SageAttention | 9.28 | $0.021 | **$0.043** | $0.04 / $0.065 |
| `h3` (full), 4 GPUs, through the worker | 63.8 | $0.142 | **$0.295** | $0.06 / $0.30 |

The prices are today's catalog (`profiles.json`), where Standard matches fal's list and Private covers cost: `h3-turbo`
$0.04 / $0.065 with `long_clip` 1.4x over 8 s, `h3` $0.06 / $0.30 with 1.7x over 6 s. An earlier draft of this note
quoted a stale $0.20 for Private full H3.

1. **Serve Turbo on one GPU, not four** (owner approved 2026-09-17). On four GPUs its floor ($0.072) is above both
   prices; on one GPU it is $0.046, under the $0.065 Private price, though still 13% above the $0.04 Standard price,
   which matches fal's list. SageAttention narrows that to $0.043. One GPU was already 15-20% cheaper per GPU-second on 2026-09-16; the worker's overhead makes the gap
   decisive. It also needs no multi-GPU confidential VM.
   - **Caveat:** a 1-GPU H200 peaks at 126-129 GB of 141 GB for a 5 s clip, and the 2026-09-16 run peaked at 138-139 GB
     at 14 s. Cap 1-GPU Turbo's length, or give it a B200/B300.
2. **SageAttention is worth adopting for Turbo** once its quality is judged by eye: 6.5% cheaper for 2 GB of memory,
   with the same scene, though not the same framing (30 dB PSNR overstates the match). It needs a package built into the image, not a flag, and its own precision recipe.
3. **Full H3's Private price already covers its floor:** $0.30 against $0.295 at 5 s, and at 14 s the `long_clip`
   multiplier gives $0.51 against a $0.505 floor (2026-09-16 numbers). The margin is thin but positive, and Private
   full H3 is a premium, privacy-only profile; fal sells the non-private version at $0.08.
   - **Standard full H3 at $0.06** (fal's list) is a fifth of its cost. It should be withdrawn from Standard, or served
     only where GPUs are much cheaper.
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

## Decided and done (2026-09-17, subnet `ea6d1c1`)

- **`h3-turbo` serves on one GPU.** `gpus_per_worker` is 1, `min_vram_gb` 141, and the verified classes are the `C2.*.x1`
  ones.
  - **Envelope, by GPU memory:** 10 s on a 141 GB H200 (interpolated, about 134 GB at 10 s) and the profile's 14 s on
    160 GB or more (unmeasured on those cards).
  - **VCU:** 18 at 768p, slope 0.08, from 10.9 GPU-s per output second at 5 s through the worker. Both roundings favour
    miners.
  - **CVM shapes:** Turbo moved from the `c8.*` whole-server shapes to the single-GPU `c2.*.x1` ones.
- **SageAttention is built into the H3 image, off by default.**
  - `KUNO_H3_ATTENTION=sage` adds `--attention-backend sage_attn`; the default runs FlashAttention as every measurement
    did.
  - The worker's start-up log names the backend it used. Receipts don't carry it yet.
  - **Update 2026-09-18: on by default for Turbo on H200s** (subnet `1511c92`, image `h3-0.1.0-1511c921bb89`). The owner
    watched the two clips side by side and could not tell which was better. `KUNO_H3_ATTENTION=auto`, the new default,
    gives the Turbo server SageAttention when the image has it and NVML reports only SM90 GPUs; full H3 and other cards
    keep FlashAttention, and `sage` by name is refused on cards the kernels aren't built for.
- **Full `h3` and `h3-reference` are Private-only.** Their Standard prices ($0.06, a fifth of cost or less) were removed,
  so the gateway refuses Standard jobs for them with its existing `privacy_mode_unavailable`, before any charge.

## Next

1. **Done 2026-09-18 for SageAttention:** the owner watched the pair and could not tell them apart.
2. **Run one-GPU Turbo through the worker on an H200:** `--num-gpus 1`, a 10 s render watched for peak memory (the
   envelope's interpolated rung), and the ×1 `gpu_seconds` in the receipt.
3. **Switched 2026-09-18** (subnet `1511c92`). Still to confirm on a GPU, from the rebuilt image, that SGLang's log says
   `sage_attn` and that a 10 s clip fits one H200 with SageAttention's extra ~2 GB (step 2 covers both).
4. **Done:** full H3 and H3 Director are Private-only.
