# LTX-2.5 weight digests (for the golden manifest's `model_digests`)

Computed 2026-09-17 on a rented RTX PRO 6000 with `python -m kuno_protocol.devkit weights-digest`, run inside
`ghcr.io/concil859856/kunoworld-worker:ltx-0.1.0-6c43b0258502`. The weights are `Lightricks/LTX-2.5-Diffusers` at
revision `426936f8b22dc28e4def61e515478b0b7e4a53cc`, downloaded by `scripts/gpu-test/smoke.py fetch-weights`. Each file
here lists every weight file's path, size and SHA-256 behind the digest: 41 files, including `processor/` since the
recipes started pinning it.

| Manifest key | Recipe | Digest |
|---|---|---|
| `ltx-2.5-fast` | `ltx-2.5-distilled/bf16/1` | `04998b4216458d10a993607017244f8ce1f9b4746ec10e65c60bd756e2dec1c7` |
| `ltx-2.5-pro` | `ltx-2.5-dev/bf16/1` | `6aeaf45d6bc3aa50d13c80e42e954efad083bde0bb2d8ebacc7f401c3be92fc0` |
| `ltx-2.5-fast@O1.rtx-5090-32gb.x1.fp8-cast` | `ltx-2.5-distilled/fp8-cast/1` | `97aa95b16ccd51c0fc328b76acbb0d5e9f1e1665a3dac23d9e5f4ce48530f6c4` |

**`ltx-2.5-4k` has no digest yet, and its recipe changed on 2026-09-17.**
- **What changed.** The resident backend now decodes 4K with LTX-2.5's diffusion decoder. So `ltx-2.5-dfr/bf16/1`'s
  `include` is now `ltx-2.5-fast`'s plus `diffusion_decoder/` (0.83 GB). It no longer lists `temporal_latent_upsampler/`,
  which nothing reads.
- **Compute it before a manifest lists `ltx-2.5-4k`.** Use a box whose download includes `diffusion_decoder/` at the
  revision above:
  `python -m kuno_protocol.devkit weights-digest --profile ltx-2.5-4k --models-dir <dir>`.
- **What it covers.** `ltx-2.5-fast`'s 41 files plus `diffusion_decoder/config.json` and its safetensors file.

**When these go stale:**
- **What they depend on:** the recipe identity (`precision_recipes.json`: precision, transformer subfolder,
  components) and every file's bytes.
- **Recompute when:**
  - a recipe's `include` or components change;
  - the pinned revision changes.
- **Classes:** a bf16 class key (`ltx-2.5-fast@C1.…`) resolves to the same recipe, so the bare profile key covers it
  unless a class selects another recipe. The owner adds these to a release manifest with
  `subnet/image/cvm/publish.py entry --model-digest <key>=<digest>` and signs it (`subnet/image/CVM.md`).
