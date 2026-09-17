# MiniMax H3 cost runs straight against SGLang

These scripts time H3 renders on a rented multi-GPU box with no gateway and no worker. They measured H3 Turbo and full
H3 at 5, 10 and 14 s on 2026-09-16; the results are in `research/pricing/measured_2026-09-16_h3-turbo.md`.

| File | Runs on | What it does |
|---|---|---|
| `prep.sh` | GPU host | Makes `docker run --gpus` work (installs the NVIDIA container toolkit if missing) and installs ffprobe |
| `turbo-run.sh` | GPU host | Pulls the H3 worker image, downloads FL2VA and two Turbo LoRAs, starts `sglang serve` servers from the image's `/opt/sglang` venv, and runs the benchmark plan in its header |
| `h3_bench.py` | GPU host (stdlib only) | One render per `[warmup:]prompt:seconds`: submit, poll, fetch the MP4, ffprobe it, and append a JSON line to `results.jsonl` |
| `analyze.py` | anywhere | Prints GPU-s per output second, the cost on confidential H200s at 60% utilization, and the price floor, plus peak memory per GPU |
| `fetch_h3.py` | GPU host (only `huggingface_hub`) | H3's `FL2VA` (or `Ref2VA`) into a Hugging Face cache at `refs/main`, and the Turbo 8-step LoRA beside it, before any image is pulled: `uv run --no-project --with 'huggingface_hub[hf_xet]==1.31.0' python fetch_h3.py --cache … --lora-dir … --summary …` |
| `sage-ab.sh` | GPU host | SageAttention A/B on Turbo 8 passes, one GPU per side: `build` (time-boxed install into a derived image), `run` (default attention vs `--attention-backend sage_attn`, same seed), `report` (`sage-ab.json`: load and render times, the backend each server's log says it used, speed-up, PSNR and SSIM) |

MiniMax H3's licence excludes the US, EU, UK and South Korea, testing included. Run the scratchpad region check (or an
equivalent) before any H3 download.

```bash
scp prep.sh turbo-run.sh h3_bench.py user@box:
ssh user@box 'bash prep.sh && setsid nohup bash turbo-run.sh > turbo-run.log 2>&1 < /dev/null &'
# when ~/turbo/DONE exists:
scp -r user@box:turbo . && python3 analyze.py turbo
```

**Step counts.** SGLang's H3 schedule is `linspace(1, 0, num_inference_steps)`, and its last point is not a model pass.
An N-pass Turbo LoRA therefore needs `--steps N+1`. `turbo-run.sh` now passes N+1 (and 51 for full H3's 50 passes).
The 2026-09-16 run passed N (8, 4 and 50), so those renders were one pass short; the research note corrects the
timings.

## SageAttention A/B (`sage-ab.sh`)

`research/attention-bottleneck_nunchux_2026-09-17.md` asks whether low-bit attention narrows H3's cost. SGLang 0.5.19
in the H3 image has a `sage_attn` backend, but the `sageattention` package isn't installed.

**Install.** `sage-ab.sh build` installs SageAttention into `/opt/sglang` of a container and commits it as a derived
image. It uses commit `d9704247…`, the one SGLang's own log message names. On a Hopper GPU, SGLang also requires that
build's `sageattention.sm90_compile` binding. **Without it, SGLang falls back to FlashAttention with only an INFO or
WARNING line.** So `sage-ab.json` reports B as SageAttention only if B's server log names that backend: see
`sage_in_use` and `backend_log`.

A CPU dry run on 2026-09-17 (`BUILD_GPU=none`, 6 compile jobs) built and installed `sageattention-2.2.0` in 189 s,
with the SM90 binding present. It needed two fixes, both now in the script:
- **CUDA versions.** The venv's pip toolkit pairs nvcc 13.4 with CUDA runtime headers 13.0, which CCCL refuses:
  "CUDA compiler and CUDA toolkit headers are incompatible". The build passes `-DCCCL_DISABLE_CTK_COMPATIBILITY_CHECK`
  through `NVCC_APPEND_FLAGS`.
- **libcuda.** `setup.py` links `-lcuda`, which the pip toolkit doesn't ship. The build links against the driver's
  `libcuda.so.1`. Without a GPU, it uses an empty stub with that soname, which the linker then drops.

**Not yet shown:** that the kernels load and run on an H200, or what they do to H3's output.

```bash
export H3_CACHE=~/kuno-smoke/models/h3 LORA=~/kuno-smoke/models/h3/turbo/minimax_h3_fl2v_turbo_8step_v1.0_768p_bf16.safetensors
bash sage-ab.sh build &   # <= SETUP_TIMEOUT_S (300); needs only the image
bash sage-ab.sh run       # A on GPU_A at once; B on GPU_B when build.json says ok; then sage-ab.json
```

**The comparison.** Both sides render the same request: the lighthouse prompt, seed 1234, 5 s at 768p, and
`num_inference_steps` 9, which is 8 passes. Each side renders it twice, a warm-up and then the measured clip.

`sage-ab.json` records:
- **Speed:** `speedup_wall` and `speedup_inference`, A's time over B's for the measured clips.
- **Quality:** `quality.sage_vs_default`, the PSNR and SSIM of B's clip against A's (ffmpeg, frame by frame, on the
  encoded MP4s). The Nunchux paper measured 20-21 dB for low-bit attention against BF16 on H3.
- **Repeatability:** `quality.default_repeat` and `quality.sage_repeat`, each side's measured clip against its own
  warm-up. `inf: identical` means that side repeats exactly.

A and B run at the same time on different GPUs of one host, alongside whatever else the host runs.

