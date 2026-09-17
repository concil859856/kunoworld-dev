# Long videos from chained LTX-2.5 shots: first GPU run, 2026-09-16

**Question.** Can LTX-2.5 make videos longer than one clip (20 s at most) by chaining ordinary shots so the joins can't
be seen or heard? The technique is ComfyUI-JoyLTX25's AV-extend (MIT), rebuilt on our diffusers pipeline, not on
ComfyUI:
- **`continue`** pins the previous shot's last 3 video latent frames and the matching audio latents at the head of the
  next shot.
- **`cut`** pins the audio only.
- **`fresh`** starts a new shot with nothing pinned.

Code and instructions: `scripts/gpu-test/long_video/` (`README.md` explains the mechanism).

**Setup.** One Shadeform MassedCompute RTX PRO 6000 Blackwell (96 GB), Kansas City, $2.19/h, active about 18 min
(about $0.70).
- **Image and weights:** `vocence/kunoworld-worker:ltx-0.1.0-0ad70874cd6b`; `Lightricks/LTX-2.5-Diffusers@426936f8`.
- **Profile:** `ltx-2.5-fast` (distilled, two passes: half size, then upsample and refine), 720p (1280x704), 24 fps,
  offload `none`.
- **Not tested:** confidential computing, and `ltx-2.5-pro`.

## Result: the picture joins are seamless; the voice is not proven past a few shots

| Run | Shots x length | Joins | Stitched | Wall (incl. 20 s load) |
|---|---|---|---|---|
| `mixed-joins` | 4 x 3 s | fresh, continue, cut, fresh | 10.75 s | 58 s |
| `harbor-continue` | 4 x 5 s | 3 continue | 18.0 s | 81 s |
| `narrator` (anchor `first`, then `previous`) | 4 x 5 s | cut, continue, cut | 18.0 s | 79-80 s |
| `harbor-long` | 8 x 5 s | 7 continue | **35.4 s** | 140 s |
| `narrator-long` (`first`, then `previous`) | 8 x 5 s | 2 continue, 5 cut | 35.4 s | 139 s |

**The mechanism works on the real weights, every shot, both passes.**
- **Pins held:** `pins_exact` was true (pinned tokens bit-identical after denoising).
- **The model saw them as context:** `pinned_head_seen_at_t0` was true (the transformer received timestep 0 on the
  pinned head).
- **Video** uses the pipeline's native conditioning mask. **Audio** uses a per-token audio timestep plus a scheduler that
  writes the pinned tokens back after every step.

**Picture: `continue` joins can't be seen.**
- **How big the seams are:** the frame-to-frame change across a join is 0.99-2.04x the ordinary change inside a shot,
  against 16-227x at a cut.
- **Across 35 s:** in `harbor-long`, the same blue boat, dock and horizon carry through 35 s while the prompts move from
  golden hour to dusk to night. The lighting follows the prompts and nothing jumps at a join.
- **Cuts:** a `cut` or `fresh` shot can change style freely. One cafe shot came out as illustration, because the prompt
  didn't ask for a photo.

**Audio: mostly continuous, a few joins to listen to.**
- **Smooth joins:** audio sample jumps at `continue` joins were 0.57-1.76x the ordinary sample-to-sample change.
- **Three large jumps:** harbor shot 1→2 (5.4x), and narrator `previous` shots 3 and 5 (7.1x, 5.7x). These may be
  audible clicks. Nobody has listened to them yet.
- **Sync:** audio and picture stayed within ±13 ms of each other at every join.

**Voice over cuts: not established.** There is no transcription or speaker model here; `voice_stats.py` gives median
pitch and spectral centroid per shot as a rough proxy.
- **4 shots:** pitch stayed in a low male range (104-130 Hz). With anchor `first` it held at 110-113 Hz for shots 2-4;
  with `previous` it drifted from 113 to 104 Hz.
- **8 shots:** in both modes, pitch wandered between 96 and 152 Hz, and the spectral centroid rose from about 650 Hz to
  1,100-1,450 Hz in shots 4-7. Background sounds in those scenes (a brush, a kiln) could explain part of that.
- **Anchors:** `first` stayed closer than `previous` on both measures.
- **Needs a listener:** is shot 8 the same narrator as shot 1?

## Cost

Each 5 s shot took 13.7 s to generate (4.3 s half-size pass, 9.3 s refine) and 14.7 s including encoding. It peaked at
86.9 GB allocated and 92.7 GB reserved, out of 96 GB.
- **Per stitched second:** a 35.4 s take is 8 shots x 14.7 s = 118 GPU-seconds, or **3.3 GPU-s per output second**.
- **Why that's cheaper than a single short clip:** a 2 s clip measured 4.76 on 2026-09-15. The fixed per-shot work is
  spread over 5 s shots, and the overlap trim costs only 0.7 s per join.
- **At confidential prices:** on an RTX PRO 6000 at $1.879/h and 60% utilization, that is about **$0.003 per output
  second**. `ltx-2.5-fast`'s current price is $0.04-0.05/s.
- **Memory:** 5 s shots leave about 3 GB of headroom on a 96 GB card. Longer shots per join, or `ltx-2.5-pro`, need a
  memory check first (VAE tiling, or offload).

## Findings for the product

1. **Long LTX-2.5 videos are practical on one GPU.** A 35 s single take renders in about 2 minutes on the hardware class
   we already serve (C1), with no seam you can see.
2. **Joins must happen inside one job, in one enclave.** Each join needs the previous shot's final latents: normalized,
   packed tokens from both passes. They must never leave the enclave, so a storyboard is one job with one receipt, not a
   client stitching separate jobs.
3. **Audio anchoring needs a listening test before it's a feature.** Ship `continue` (seamless takes) first, and treat
   `cut` with a carried voice as experimental.
4. **JoyLTX25's proportional audio tail is off by about 173 ms** for 2 s shots, because both VAEs are causal. Our
   planner keeps each shot's sound within ±20 ms of its picture, and that held on the GPU.

## Next

1. **Listen** to the `narrator` and `narrator-long` stitched clips, and the three flagged joins
   (`data/gpu-tests/ltx-2.5/repro-20260916T15*_extend-*`).
2. **Product design:** a storyboard job type for the LTX-2.5 profiles.
   - **Protocol:** a list of shots, each with a prompt, duration and join.
   - **Worker:** the pinning pipeline built from `ltx_extend.py`.
   - **Receipts and pricing:** per-shot progress, and a price as the sum of the shots minus overlaps.
   - **Safety:** the gate runs on every shot's prompt and on the stitched output.
   - **Verified mode:** the transcripts need the pinned tokens committed per shot.
3. **Measure `ltx-2.5-pro`** and 10 s shots.

## Addendum: the product worker path on a GPU, and a memory bug it found (same day, 16:40–17:07 UTC)

Rental: a MassedCompute RTX PRO 6000 (94.97 GiB usable), about $1.03. The run used `scripts/gpu-test/long_video/run_storyboard_worker.py`
through the worker's own `LtxResidentBackend` (subnet `91b0581`, source mounted into
`vocence/kunoworld-worker:ltx-0.1.0-0ad70874cd6b`).

**Storyboards through the worker: pass.**

| Run | Output | Wall (incl. 20 s load) | Per shot | Peak allocated |
|---|---|---|---|---|
| `mixed-joins` (4 x 3 s) | 258 frames, 10.75 s, audio | 35 s | 8.5 s | 82.7 GiB |
| `harbor-long` (8 x 5 s) | 849 frames, 35.375 s, audio | 113 s | 13.9 s | 86.9 GiB |

- **Correctness:** frame counts equal `storyboard_frames`, the `shot i/N` progress stages appeared, and no step
  commitment was produced.
- **Timing:** it matches the experiment's.

**Clip length is limited by memory, for single clips too.** The worker assumed a 96 GB card holds any `ltx-2.5-fast`
request, but a single 20 s 720p clip ran out of memory. Peaks, bf16, no offload, from the torch allocator:

| 720p shot length | Latent tokens (full size) | Result |
|---|---|---|
| 3 s | 8,800 | 82.69 GiB |
| 5 s | 14,080 | 86.89 GiB |
| 12 s | 32,560 | fits only with `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`: 93.68 GiB; without it, out of memory with 3.8 GiB reserved but unused |
| 14, 15, 16, 20 s | 37,840+ | out of memory (with and without expandable segments) |
| 1080p 50 fps 10 s | 128,520 | out of memory |

- **With `KUNO_LTX_OFFLOAD=model`:** 20 s of 720p fit (66.7 GiB peak, 108-116 s per 20 s shot). But a 5 s shot took
  41-44 s against 13.9 s without offload, three times slower.

**What changed:**
- **Recipe:** `ltx-2.5-distilled/bf16/1` activations are now measured: 9.55 GiB fixed plus 3.674 GiB per 10k
  tokens, the line through the 5 s and 12 s peaks. The fp8-cast and int8 recipes take the same activation terms.
- **Planner:** it plans against the GPU's reported memory when a class declares none. A card that holds every weight
  but not the largest requests keeps everything on the GPU and gets a token cap instead of no plan.
- **The RTX PRO 6000 now advertises:** 720p up to 11 s (5 s at 50 fps) and 1080p 16:9 up to 4 s.
- **Image:** the LTX image sets expandable segments.
- **Storyboards** chain shots within those lengths. Longer single clips route to H200-class workers.

## Addendum 2: storyboards through a real gateway on a GPU (19:29–19:42 UTC)

Rental: a MassedCompute RTX PRO 6000, about $0.65. Published images: worker `ltx-0.1.0-1ca142565a29`
(sha256:ae99f6b8…), gateway `8ee717432b9d`, mock-worker `1ca142565a29`. Driven by `ltx-smoke.sh` with
`KUNO_SMOKE_STORYBOARD` (dev commit `7c46a65`).

| Run | Mode | Result |
|---|---|---|
| `mixed-joins` (4 shots) | Standard | **PASS**: job 42 s, 1280x704, 10.75 s, H.264 + AAC, peak GPU 86.7 GiB |
| `harbor-long` (8 shots) | Private, sealed by the Python SDK | **PASS**: job 130 s, 35.38 s video, SHA-256 matches the receipt, peak GPU 91.2 GiB |
| a plain 11 s 720p clip | Standard | rendered 265 frames with no out-of-memory error (the new cap's longest), **but FAIL**: 11.605 s of audio over 11.042 s of video |

**The audio overrun** was an encoder bug in single clips. The vocoder returns more audio than frames for long clips, and
`apad` plus `-shortest` let ffmpeg cut it half a second late. Fixed in subnet `9b873ef`: the samples are cut or padded
to frames / fps and the file is capped with `-t`. Storyboards stitch their own audio and were exact. The fix has not
been re-run on a GPU; a local test with the measured lengths gives 11.041 s of audio over 11.042 s of video.

## Addendum 3: retake and audio-to-video on the pinning mechanism (2026-09-17 01:16–01:24 UTC)

**Why.** Before subnet `89568ae`, both modes crashed on the GPU: the worker sent `audio_path` and `video_path`
keywords that no diffusers 0.40 LTX-2 pipeline accepts. Both now render on the storyboard pinning mechanism
(`backends/ltx_pinning.py`, `ltx_edit.py`; spec in `subnet/PROTOCOL.md` "Edits: retake and audio-to-video").

**Setup.** Same rental as `director-design_2026-09-16.md` §12. Worker image `ltx-0.1.0-89568ae64d7e`; driver
`scripts/gpu-test/long_video/run_edit_modes_worker.py`; 720p, 24 fps. Nothing was downloaded: the sound was synthesized
with ffmpeg, and the clip to retake was rendered first.

| Job | Wall | Peak allocated | Result |
|---|---|---|---|
| Source clip, `ltx-2.5-fast`, 5 s | 31.6 s | 77.22 GiB | 121 frames, audio 5.056 s |
| Retake of 1.5-3.5 s, picture and sound | 22.8 s | 78.26 GiB | **PASS** |
| The same window, `regenerate_video: false` | 22.8 s | 78.26 GiB | **PASS** |
| Audio-to-video, `ltx-2.5-pro`, 4 s, with a first frame | 232.3 s | 75.90 GiB | **PASS** |

**Retake.**
- **Regenerated span:** latent frames 5-12 (pixel frames 33-89) for the 1.5-3.5 s window. 9 of 16 latent frames and 75
  of 126 audio latents were held.
- **Pins:** held tokens stayed bit-exact in every pass, and the model saw them at t = 0.
- **Picture:** held frames came back at 35.8-39.7 dB PSNR against the source (mean 38.3). The window's mean was 28.0 dB,
  so it really changed.
- **Sound:** samples outside the span are identical to the source. Splice jumps were 2.5-3.2x the typical step (limit 8).
- **Sound-only retake:** every frame stayed at or above 35.9 dB, and only the sound in the window was regenerated.
- **Encoding the source took 1.2 s.**

**Audio-to-video.**
- **Samples:** the returned samples are exactly the source's. The MP4's AAC track lines up with the source at 0 ms lag
  (correlation 0.9999).
- **Pins:** held audio tokens stayed exact in every pass.
- **Audio VAE settings:** a round trip through the audio VAE (encode, decode, vocoder) gives a log-mel correlation of
  0.87 with the source. This confirms the n_fft of 1024 the encoder assumes.
- **Speed:** 4 s of `ltx-2.5-pro` took 232 s, about 58 s per output second.

**Problems found.**
1. **Encoding the source needs about 8x the memory admission assumes.**
   - Measured: 12.07 GiB extra for 121 frames at 1280x704, against `source_encode_gib`'s 1.47 GiB.
   - A 5 s retake still fit (78.26 GiB).
   - If encode memory grows with length, retakes near the RTX PRO 6000's 15 s cap would run out of memory. Fixed the
     same day with a chunked encode (addendum 4).
2. **The driver kept the evicted `ltx-2.5-fast` pipeline alive,** so its single-process run ran out of memory loading
   `ltx-2.5-pro`.
   - The worker is fine: `LtxResidentBackend.warm(fast)` then `warm(pro)` reloaded to 66.18 GiB in 12.0 s.
   - Audio-to-video was run in a fresh process. The driver was fixed and re-run in one process (addendum 4).

Clips: `data/gpu-tests/ltx-2.5/repro-20260917T0118_edit-*.mp4` and `repro-20260917T0124_edit-a2v.mp4`.

## Addendum 4: the chunked source encode, and an 18 s retake at the cap (2026-09-17 12:18–12:47 UTC)

**What changed** (subnet `6c43b02`, `backends/ltx_chunked_encode.py`):
- **Encode:** a retake's source is encoded as frame 0, then 8 frames at a time. The causal convolutions' last input
  frames carry between chunks, so encode memory no longer grows with length.
- **Admission:** it counts the encode's peak beside the weights, not on top of the render (the encode frees before
  denoising). The retake cap on the RTX PRO 6000 rose from 15 s to 18 s at 720p.
- **Driver:** it now releases evicted pipelines.

**Setup.** MassedCompute RTX PRO 6000, about 29 min, about $1.05. About 10 of those minutes went to a stale SSH host
key on a reused IP. Image `ltx-0.1.0-6c43b0258502` (ghcr); driver `run_edit_modes_worker.py`, every job in one process.

| Job | Wall | Peak allocated | Admission's estimate | Result |
|---|---|---|---|---|
| Source clip, 5 s | 30.7 s | 77.22 GiB | 77.48 GiB | pass |
| Retake 1.5-3.5 s | 22.9 s | 77.24 GiB (78.26 before, with the whole-clip encode) | 77.73 GiB | pass |
| Retake, sound only | 22.8 s | 77.25 GiB | 77.73 GiB | pass |
| **Retake of an 18 s clip** (433 frames, 48,400 tokens) | 115.9 s | **92.94 GiB** | 93.51 GiB | pass |
| Audio-to-video, `ltx-2.5-pro`, 4 s, after evicting fast | 230.0 s | 75.90 GiB | 77.44 GiB | pass |

**The encode, measured on its own:**
- **Chunked encode, 121 frames at 1280x704:** 1.63 GiB above the weights in 1.09 s. 433 frames took 1.64 GiB, so it
  doesn't grow with length.
- **Against the estimate:** `source_encode_gib` says 2.43 GiB. 16-frame chunks took 2.42 GiB; the whole clip at once
  took 12.06 GiB.
- **The encoder's real layout:** `block_out_channels` [256, 512, 1024, 1024], `layers_per_block` [4, 6, 4, 2, 2], causal.
  It caches 448 values per pixel, not the 522 of diffusers' default layout, so the estimate is conservative.

**Token agreement.** Chunked tokens against the whole-clip encode, in bf16:
- mean absolute difference 0.001;
- largest 0.059, against a spread of 0.977.

The driver's 5% maximum failed the run on this alone, so `RESULT: FAIL` is this check. But the retake's held frames
came back exactly as with the whole-clip encode: 35.83 dB minimum and 38.25 dB mean in both runs. The differences
are kernel choice (convolutions over 8 frames against 121), not a misalignment, which would differ by the whole
spread. The check now takes the mean (1% of spread) and a 25% maximum.

**Other results.**
- **Evictions:** both loads started clean. No module of the evicted profile was alive, and 0.01 GiB was allocated
  before pro loaded, which took 13.9 s.
- **Long retake quality:** held frames on the test-pattern source were 25.0-26.6 dB. A test pattern's fine lines are the
  VAE's worst case, so this is recorded, not checked. Its splice jumps were 1.2-1.6x.
- **Weight digests:** the golden manifest's `model_digests` for the three LTX-2.5 recipes were computed on this box.
  They are in `research/weights-digests/`.
