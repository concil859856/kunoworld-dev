# Attention is the video bottleneck: Nunchux's VC-Attention, and what it means for us (2026-09-17)

**Sources.**
- Blog: [Nunchux AI, "Attention is the video bottleneck"](https://www.nunchux.ai/blog/attention-is-the-video-bottleneck),
  2026-09-16. The page's own title is "VC-Attention: Faster Low-Bit Attention Without Retraining".
- Paper: [arXiv:2609.15810](https://arxiv.org/abs/2609.15810), "VC-Attention: Value Smoothing and Softmax Casting for
  Low-bit Attention", submitted 2026-09-14, CC BY 4.0.
  - Authors: Xingyang Li, Dongyun Zou, Shining Zhang, Jiacheng Chen, Haocheng Xi, Lvmin Zhang, Jun-Yan Zhu, Song Han,
    Zhekai Zhang, Yujun Lin, Muyang Li. Several are from MIT HAN Lab and the Nunchaku/SVDQuant work.
- **Caveat:** the figures below were read from the blog and the arXiv HTML through a summarizing fetch, not from the
  PDF. Check a number against the PDF before quoting it outside this note. The blog gives B300 as 1.51x; the paper
  extraction gave 1.47x.

## What they claim

**The problem.** Diffusion transformers attend over every video token.
- "On one B200 with BF16 FlashAttention-4, about two thirds of every denoising step is attention."
- The cost grows with the square of the token count, so longer clips make it worse.
- On Wan2.2 at 75.6K tokens on an RTX 5090, attention is more than 64% of generation time.

**The method: training-free, and a kernel swap rather than a new model.**
- **V-Smooth.**
  - Earlier low-bit attention (SageAttention2) smooths queries and keys, but value outliers follow no fixed channel
    or spatiotemporal structure.
  - V-Smooth groups value tokens with a lightweight k-means (warm-started, run on the first 25% of steps), subtracts
    each block's mean, and quantizes only the residual.
  - Grouping costs about 3-4% of total attention time, amortized.
- **ExpCast-FP8.**
  - Low-bit tensor cores speed up only the two matrix multiplications. The FP32 softmax exponential between them
    becomes the slowest stage on datacenter GPUs.
  - ExpCast replaces "evaluate 2^z in FP32, then cast to E4M3" with one linear map straight to the FP8 byte:
    `code(u) = clip[0,120](round(8(u+8) + 56 + β))`, β = −0.35.
  - **Error bound:** total variation under 3.64% plus an underflow tail; 1.6% measured on average.
- **Number formats.**
  - Datacenter (8-bit): Q INT8 after a Hadamard rotation, K INT8 after channel-mean smoothing, V FP8 E4M3 residuals,
    probabilities FP8 E4M3 through ExpCast.
  - Workstation (4-bit): V in NVFP4, probabilities not quantized (no ExpCast).
  - It needs INT8×INT8 tensor cores and E4M3 support. B200, H200, RTX PRO 6000 and RTX 5090 are named.
- **Composition:** it leaves the attention pattern and the step schedule alone, so it should combine with sparse
  attention (Sparse VideoGen, Radial Attention, SpargeAttn). No combined measurement is given.
- **Code:** described as a fused CuTe/CUDA kernel. No repository or kernel release was found. A proprietary "Nunchux
  Attention" is also quoted as faster still.

**Models tested (tokens per clip):**

| Model | Clip | Tokens |
|---|---|---|
| Wan2.2-T2V-A14B | 720p, 81 frames | 75.6K |
| LongCat-Video | 480x832, 93 frames | 37.4K |
| HunyuanVideo-1.5 | 720p, 121 frames | 111.7K |
| **MiniMax-H3** | 1344x768, 243 frames | 73.5K |

**Quality.** PSNR, SSIM and LPIPS are measured against the same model's BF16 output, on B200, 8-bit:

| Model | SageAttention2 | V-Smooth only | V-Smooth + ExpCast (the fast kernel) |
|---|---|---|---|
| Wan2.2 | 20.3 dB / 0.730 / 0.206 | 22.6 / 0.792 / 0.152 | 20.5 / 0.744 / 0.191 |
| LongCat-Video | 23.1 / 0.793 / 0.122 | 24.5 / 0.822 / 0.102 | 23.8 / 0.807 / 0.109 |
| HunyuanVideo-1.5 | 15.6 / 0.581 / 0.382 | 18.4 / 0.675 / 0.271 | 17.5 / 0.648 / 0.301 |
| MiniMax-H3 | 19.9 / 0.723 / 0.252 | 21.0 / 0.751 / 0.218 | 20.2 / 0.726 / 0.248 |

- VBench subject consistency and imaging quality stay within 0.01 of BF16 for every method.
- **Reading:** PSNR of 15-24 dB against BF16 means a *different video* of similar quality, not the same video. Low-bit
  attention changes the sampling trajectory.

**Speed.** Attention kernel is vs BF16 FlashAttention-4; end-to-end is Wan2.2, whole clip:

| GPU | Attention kernel | End to end (Wan2.2) |
|---|---|---|
| B200 (8-bit) | 1.59x | 1.19x |
| B300 (8-bit) | 1.51x (blog) / 1.47x (paper extraction) | – |
| H200 (8-bit) | 1.46x | 1.13x |
| RTX PRO 6000 (4-bit) | 2.27x | 1.36x |
| RTX 5090 (4-bit) | 3.58x | 1.70x |

The blog's headline, 1.59x on B200, is the kernel. **End to end, datacenter GPUs gain 13-19%.** The large gains are on
workstation Blackwell cards with 4-bit values.

**Product note.** Nunchux says free access to MiniMax-H3 is coming "very soon" (waitlist on their Modelverse).

## What it means for KunoWorld

1. **H3's price gap barely moves.** On 4x H200 our full-H3 floor is $0.274/s at 5 s, against fal's H3 Max list of
   $0.08 (`research/pricing/measured_2026-09-16_h3-turbo.md`).
   - A 1.13x end-to-end gain would bring that to about $0.24.
   - The gain grows with length (attention's share rises with tokens), so 14 s ($0.505) gains more. It is still several
     times fal's price.
   - Turbo's step count matters far more than the attention kernel. Low-bit attention on Turbo would compound, and is
     worth measuring.
2. **H3 is about to be free somewhere.** fal's promotion is $0.04/s, and now Nunchux promises free access. H3 can't
   compete on price; what we sell with it is privacy (Private mode on confidential GPUs) and receipts. This supports the
   owner's decision: Standard at fal's list price, Private allowed to cost more.
3. **The largest measured gain is on our LTX card class.** On the RTX PRO 6000, the 4-bit kernel gave Wan2.2 1.36x end
   to end at 75.6K tokens.
   - Our LTX-2.5 clips are shorter in tokens: a 5 s 720p shot is 14K at full size, and an 18 s shot about 50K. The
     gain is smaller for short clips and grows for the long single clips the new memory limits allow.
   - VC-Attention isn't released. SageAttention3 (FP4 on Blackwell, open) is the comparable thing we could try today.
   - LTX-2.5 runs through diffusers' attention processors, not SGLang, so it would need a custom attention processor.
4. **Low-bit attention is a new precision recipe, not a free flag.**
   - Outputs differ from BF16 (PSNR about 20 dB), so a recipe must name the attention kernel and its settings. Its
     `model_digests` and verified-mode determinism are then specific to that kernel.
   - The step-replay audit can only replay on the same kernel and hardware class.
   - Customers should be able to see which recipe served them.
5. **Our pinned SGLang already has attention backends to try on H3** (0.5.19 in the H3 image, checked 2026-09-17):
   - `sage_attn` (with H3-style trailing-padding handling), `sage_attn3`, `sliding_tile_attn`, `video_sparse_attn`,
     `sparse_video_gen_2_attn`, `sparge_attn` and others.
   - The `sageattention` package itself is **not installed** in the image.
   - SGLang main (tree fetched earlier in this project) adds H3-specific backends: `hybrid_window_attn_h3.py`,
     `video_sparse_attn_h3.py`, `vsa_h3_kernels.py`. These aren't in 0.5.19.

## Suggested next steps

- **Done on 2026-09-17** for Turbo 8-step on one H200 (see the section below): 6.5% faster, 30.2 dB. Still open: the
  same A/B for full H3 at 50 passes and at 14 s, where the paper predicts a larger gain and a bigger quality change.
- **Track SGLang main's H3 sparse backends** (`video_sparse_attn_h3`, `hybrid_window_attn_h3`) for the next SGLang
  bump. Sparse attention changes quality more than low-bit attention does, so it needs the same side-by-side check.
- **LTX-2.5:** try SageAttention3 as a diffusers attention processor on the RTX PRO 6000 at 5 s and 18 s 720p. Keep it
  behind a separate precision recipe (point 4). Worth doing only if the 18 s single clip gains 20% or more.
- **Watch for a VC-Attention code release.** The paper is CC BY 4.0; no kernel is published.

## Measured on our own stack (2026-09-17, same day)

SageAttention was tried on the H3 image during the 8× H200 check (`h3-image-check_2026-09-17.md` §3). It is the open
stand-in for VC-Attention, which has no code release.

| H3 Turbo, 1 H200, 8 passes, 5 s | Backend | Wall | GPU-s per output second |
|---|---|---|---|
| A | FlashAttention (`fa`) | 51.26 s | 9.92 |
| B | SageAttention (`sage_attn`) | 47.95 s | 9.28 |

- **6.5% faster end to end**, close to the paper's 13% for 8-bit attention on an H200 at a larger token count.
- **Quality:** 30.2 dB PSNR and 0.925 SSIM against the FlashAttention clip, much closer than the paper's 19.9 dB for
  SageAttention2 against BF16, because Turbo runs 8 passes instead of 50.
- **Cost:** the package is not in the image and took 234 s to build on the box (nvcc 13.4 against CUDA 13.0 headers
  needs `-DCCCL_DISABLE_CTK_COMPATIBILITY_CHECK`; libcuda must be on the link path). It also costs about 2 GB of GPU
  memory.
- **It is really used:** SGLang's log names the backend, so a silent fallback would show.

**What this changes in the conclusions above:** point 1 stands (a few per cent off H3's cost doesn't close the gap to
fal), but a 6.5% saving on Turbo is worth having if the picture holds up to a viewer, because Turbo is the H3 profile
we can actually sell. Point 4 gains evidence: low-bit attention keeps far more of the original picture on a
few-step model than on a 50-step one.
