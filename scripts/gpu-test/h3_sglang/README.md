# MiniMax H3 cost runs straight against SGLang

These scripts time H3 renders on a rented multi-GPU box with no gateway and no worker. They measured H3 Turbo and full
H3 at 5, 10 and 14 s on 2026-09-16; the results are in `research/pricing/measured_2026-09-16_h3-turbo.md`.

| File | Runs on | What it does |
|---|---|---|
| `prep.sh` | GPU host | Makes `docker run --gpus` work (installs the NVIDIA container toolkit if missing) and installs ffprobe |
| `turbo-run.sh` | GPU host | Pulls the H3 worker image, downloads FL2VA and two Turbo LoRAs, starts `sglang serve` servers from the image's `/opt/sglang` venv, and runs the benchmark plan in its header |
| `h3_bench.py` | GPU host (stdlib only) | One render per `[warmup:]prompt:seconds`: submit, poll, fetch the MP4, ffprobe it, and append a JSON line to `results.jsonl` |
| `analyze.py` | anywhere | Prints GPU-s per output second, the cost on confidential H200s at 60% utilization, and the price floor, plus peak memory per GPU |

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
