# GPU smoke test: LTX-2.5 and MiniMax H3 on a rented server

`ltx-smoke.sh` runs KunoWorld's real worker images on one rented GPU server and proves one video per profile comes
out end to end. LTX-2.5 by default; MiniMax H3 with `KUNO_SMOKE_FAMILY=h3` ([below](#minimax-h3)):

1. It checks the machine.
2. It pulls the images and downloads only the weights the profiles load.
3. It starts a dev gateway and a worker with the simulated TEE (`KUNO_TEE=mock`), all on 127.0.0.1.
4. For each profile, it submits a job with the dev API key — Standard mode, or Private through the SDK for H3 —
   downloads the MP4 and checks it with ffprobe.
5. It writes timings, peak GPU memory and host RAM, a results JSON and every log into one tarball.

Nothing touches a chain, and nothing listens beyond 127.0.0.1.

Two other tasks reuse the same machine check, images and weights, but call the worker's own tools instead of the job
loop — no gateway, no enclave, no job ([Other tasks](#other-tasks)):

- `KUNO_SMOKE_TASK=bench`: `kuno-bench` measures what each profile costs to render, cell by cell. Its JSON is what
  `kuno-devkit derive-rates` turns into a rate-card proposal, so this is the run that replaces guessed prices.
- `KUNO_SMOKE_TASK=determinism`: `kuno-verified-check` renders the golden cases twice, in two processes, and compares
  every committed latent. This is step 1 of `subnet/VERIFIED_MODE.md`'s Phase 0, which a GPU class must pass before
  verified-mode penalties can apply to it.

`smoke.py` beside the script holds the helpers. They run inside the images, so the host needs only `bash`, `docker`,
`curl`, `ffprobe` and `tar`.

## What to rent

| | Needed | Checked by the script |
|---|---|---|
| GPU | one NVIDIA GPU with ≥ 80 GB, e.g. RTX PRO 6000 Blackwell 96 GB, H100/H200 | `nvidia-smi` memory ≥ 80000 MiB |
| Driver | R570 or newer (the image runs CUDA 12.8 PyTorch 2.11) | `driver_version` major ≥ 570 |
| Docker | with the NVIDIA container toolkit | `docker run --gpus all ubuntu:24.04 nvidia-smi -L` |
| RAM | ≥ 64 GB (95 GB is comfortable) | `MemTotal` |
| Disk | ≥ 200 GB free where the weights go | `df` on `KUNO_SMOKE_DIR` (weights already there count) |
| Packages | `curl`, `ffprobe` (`apt-get install -y ffmpeg`) | `command -v` |

**For H3** (`KUNO_SMOKE_FAMILY=h3`): 4 GPUs of at least 141 GB in one machine for `h3` and `h3-reference` (an 8-GPU
H200 box is what we used) — `h3-turbo` needs only one of them, since 2026-09-17 it is a single-GPU profile —
driver R580 or newer, about 150 GB of disk for the `FL2VA` weights (`Ref2VA` adds about 61 GB), and a country the
MiniMax H3 licence allows — not the US, EU, UK or South Korea, testing included.

No TDX or confidential-computing mode is needed.

## Run it

Set two environment variables:
- `HF_TOKEN`: a Hugging Face read token for the account that accepted the LTX-2.5 licence (the repo is gated).
  H3's weights are not gated, so an H3 run needs no token.
- `GITHUB_TOKEN`: a GitHub token with `read:packages` for the private `ghcr.io/concil859856` images.

```bash
scp -r scripts/gpu-test user@gpu-box:~/gpu-test        # or git clone and cd into scripts/gpu-test
ssh user@gpu-box
export HF_TOKEN=hf_...  GITHUB_TOKEN=ghp_...            # read -rs is safer than typing them into history
KUNO_SMOKE_DIR=/data/kuno-smoke ~/gpu-test/ltx-smoke.sh # KUNO_SMOKE_DIR defaults to ./kuno-smoke
```

Run it inside `tmux` so a dropped SSH session doesn't stop it. It exits with:
- 0 if every profile produced a checked video;
- 1 if anything failed;
- 2 if a prerequisite failed, in which case nothing was started.

The tokens are never echoed or written to disk:
- The GitHub token logs Docker in through `--password-stdin`, into a temporary Docker config that is deleted after the pull.
- `HF_TOKEN` reaches the download container by name (`-e HF_TOKEN`).
- Any secret value that shows up in a log is replaced with `[redacted]` before the tarball is made.

### Expected time and disk

| Step | Time | Disk |
|---|---|---|
| Prerequisites | < 1 min | |
| Image pull: worker 6.6 GB compressed, gateway and mock-worker < 0.5 GB | 2–10 min | about 25 GB under Docker's root |
| Weights, both profiles (resumable) | 6 min at about 330 MB/s on the test host; 10–40 min at 1–10 Gbit/s | 120 GB; `ltx-2.5-fast` alone 82 GB |
| Per profile: worker start → registered (hash the weights, load to GPU) | about 70 s with the weights in page cache; longer from a cold disk | |
| Per profile: one 2 s 720p job | fast: 6.4 s of generation; pro: 103 s (30 steps, then 3 at full size) | < 2 MB |
| **First run** | **about 20–60 min**, mostly the download | **about 150 GB** |
| Re-run (images and weights present) | about 8 min | |

Measured on 2026-09-15 on a MassedCompute RTX PRO 6000 Blackwell Server Edition (96 GB, driver 580, 141 GB RAM): peak GPU
memory 87–88 GB with `KUNO_LTX_OFFLOAD=auto` (no offload), peak host RAM 7.4 GB. `results.json` records each run's numbers.

## Why `KUNO_BACKEND=real`

The worker has two GPU backends (`subnet/MINING.md`, 3b):
- `cold` runs `python -m ltx_pipelines.<pipeline>` with the split `Lightricks/LTX-2.5` files.
- `real` keeps the diffusers `LTX2Pipeline` / `LTX2ConditionPipeline` resident, using the `Lightricks/LTX-2.5-Diffusers` layout.

The LTX image is built from `subnet/image/pyproject.toml`, which installs `kuno-worker[nvidia,gpu,safety,provenance]`. The
`gpu` extra is torch, torchaudio, torchao, diffusers 0.40, transformers 5.x, accelerate and PyAV. Neither `ltx_pipelines`
nor `ltx_core` is in it. Checked in `kuno-worker:ltx`:
- `import ltx_pipelines` fails;
- `from diffusers import LTX2Pipeline, LTX2ConditionPipeline` works.

`cold` would fail on its first job, so the script uses `real`, the image's own default.

## Which weights, and how

The download runs `smoke.py fetch-weights` inside the worker image. It uses the image's `huggingface_hub` 1.31 with `hf_xet`;
the host needs no Python and no `hf` CLI.

The script pins the repo revision to `426936f8b22d…`, `main` on 2026-09-15; `KUNO_SMOKE_HF_REVISION` overrides it.

**What it downloads:**
- `model_index.json`.
- Every folder the profiles' precision recipes list. The worker hashes all of them before it loads, so they must all exist:
  `scheduler`, `tokenizer`, `text_encoder`, `connectors`, `vae`, `audio_vae`, `vocoder`, `latent_upsampler`, `prompt_enhancer`.
- Every other component `model_index.json` names. `LTX2Pipeline.from_pretrained` loads those too, e.g. `processor`, `duration_head`.
- The profile's transformer: `transformer/` for `ltx-2.5-fast`, `transformer_full/` for `ltx-2.5-pro`.

In a folder with a `*.safetensors.index.json`, only the shards the index names are fetched. The repo also carries copies
nothing loads:
- a second 38 GB shard set in `transformer/`;
- a single-file `connectors` (6.3 GB).

**Skipped:** those copies, the 9.7 GB distilled LoRA at the repo root, and the `ltx-2.5-4k`-only folders. `weights.json`
lists what was fetched and what was not.

Files land in `KUNO_SMOKE_DIR/models/ltx-2.5`, which is mounted read-only into the worker at `/models/ltx-2.5`. Re-running
resumes partial files and skips complete ones.

## MiniMax H3

Run `region-check.sh` on the machine first (`bash region-check.sh JP ap-northeast-1,ap-northeast-3`, last line `PASS`):
the MiniMax H3 licence excludes the US, EU, UK and South Korea, testing included, and nothing H3 may be downloaded
before the check passes.

```bash
KUNO_SMOKE_FAMILY=h3 KUNO_SMOKE_COUNTRY=JP GITHUB_TOKEN=ghp_... ~/gpu-test/ltx-smoke.sh
# Turbo, then full H3, one worker each:
KUNO_SMOKE_FAMILY=h3 KUNO_SMOKE_COUNTRY=JP KUNO_SMOKE_PROFILES=h3-turbo,h3 ~/gpu-test/ltx-smoke.sh
# reference-to-video as well:
KUNO_SMOKE_FAMILY=h3 KUNO_SMOKE_COUNTRY=JP KUNO_SMOKE_PROFILES=h3-reference \
  KUNO_SMOKE_REFERENCE_IMAGE=~/ref/fox.png KUNO_SMOKE_PROMPT='The fox from the reference image in an autumn forest' \
  ~/gpu-test/ltx-smoke.sh
```

What differs from LTX:

- **One worker on 4 GPUs.** The container gets `--gpus "device=0,1,2,3"` and `--ipc host` (NCCL shared memory), and
  SGLang serves the model at `KUNO_H3_NUM_GPUS=4`. Its log is kept (`KUNO_SGLANG_LOG=inherit`). Loading takes about
  160 s before the worker registers.
- **Private-mode jobs.** H3 has no Standard price, so the job is submitted with the `kunoworld` SDK, which seals it to
  the attested enclave and opens the video after checking the receipt. The SDK is mounted from `KUNO_SMOKE_SDK_DIR`,
  `./sdk/kunoworld` beside this script, or the repository's `sdk/python/src`.
- **A country is required.** `KUNO_SMOKE_COUNTRY` is sent as `x-kuno-country` on the job (the dev gateway runs with
  `KUNO_ALLOW_COUNTRY_OVERRIDE=1`) and as `KUNO_MINER_COUNTRY` to the worker: the gateway serves H3 only to customers
  outside the licence's excluded territories, and refuses to register a worker running inside them.
- **Weights** are a Hugging Face cache at `/models/h3` (`HF_HUB_CACHE`), not a diffusers directory: `FL2VA/` for `h3`
  and `h3-turbo`, `Ref2VA/` for `h3-reference`, plus the repo's root JSON. It is not gated, so `HF_TOKEN` is optional.
- **`h3-turbo`** also needs LightX2V's 8-step 768p LoRA (`lightx2v/Minimax-h3-Turbo@3ec17a32`,
  `minimax_h3_fl2v_turbo_8step_v1.0_768p_bf16.safetensors`). The script downloads it to `<models>/turbo/` whenever the
  profiles include `h3-turbo`, mounts it with the cache and sets `KUNO_H3_TURBO_LORA`, which `kuno-h3-worker` passes
  to the Turbo server as `--lora-path`. `weights.json` records it under `turbo_lora`.
- **Prefetching.** `h3_sglang/fetch_h3.py` writes the same cache and LoRA with nothing but `huggingface_hub`, so the
  download can start on the host while the images are still pulling; the script's own download then takes seconds.
- **No resident-call check.** That check inspects diffusers' `LTX2Pipeline`; H3 runs in SGLang.

Measured on 2026-09-15, 4 of 8 H200 141 GB (Tokyo), image `h3-0.1.0-0ad70874cd6b` plus ffmpeg and CUDA `lib64` fixes:

| | `h3` | `h3-reference` |
|---|---|---|
| Worker start to registered | 163 s | 163 s |
| Submit to finished video | 82 s | 133 s |
| Output | 1344x768, 124 frames, 5.17 s, H.264 + 32 kHz AAC | same |
| Peak GPU memory (per GPU) | 95 GB | 97 GB |
| Weights download | 144 GB in 198 s | +61 GB in 90 s |

### Sharing the machine: GPU lists and GPU groups

**`KUNO_SMOKE_GPUS`** gives the worker only the listed GPUs (nvidia-smi indices), so other work can run on the rest of
an 8-GPU box at the same time:
- the worker, preflight, `bench` and `determinism` get `--gpus "device=<list>"`;
- `KUNO_H3_NUM_GPUS` is the list's length for `h3` and `h3-reference`; a Turbo-only worker is left at the profile's
  own default of one GPU, whatever the list holds;
- `samples.csv` samples only those GPUs.

Unset, LTX gets every GPU and H3 the first `KUNO_SMOKE_MIN_GPUS`, as before. The script's own containers are named
`kuno-smoke-<stamp>-*` and labelled `kuno-smoke=<stamp>`, and cleanup removes only those. Anything else running beside
it needs other names, labels and ports: the gateway uses `KUNO_SMOKE_PORT` (18180), and an H3 worker's SGLang servers
listen on 30010-30012, 31010-31012 and 32010-32012.

**`KUNO_SMOKE_GROUPS`** runs the layout `kuno-app` gives a whole-server TD (`subnet/image/CVM.md` §6): one worker
container per GPU group, all started at once against one gateway, each with its own profiles.

```bash
KUNO_SMOKE_FAMILY=h3 KUNO_SMOKE_COUNTRY=JP KUNO_SMOKE_GROUPS="0:h3-turbo 1,2,3,4:h3" KUNO_SMOKE_PORT=18190 ~/gpu-test/ltx-smoke.sh
```

- **Syntax.** Each entry is `<GPU indices>:<profiles>`, and entries are separated by spaces. No GPU or profile may
  appear twice. It replaces `KUNO_SMOKE_PROFILES` and `KUNO_SMOKE_GPUS`, and works with the `smoke` task only.
- **Ports.** Worker *i* gets `KUNO_H3_FL2VA_URL=http://127.0.0.1:30010+10i`, `_REF2VA_URL` on 30011+10i and
  `_TURBO_URL` on 30012+10i, as `kuno-app` assigns them. Its SGLang master and scheduler ports are 1000 and 2000 higher.
- **Sequence.** Every worker must register before any job is submitted. Then each profile gets one job, in group order,
  while all workers stay up. They stop together.
- **Output.** Logs are `logs/worker-g<i>.log`. `results.json` gives each profile its `gpus` and `gpu_group`.
- **Group sizes.** A `h3` or `h3-reference` group is four GPUs, a `h3-turbo` group one (a real TD's groups are all the
  same size; this driver does not enforce that).

**`KUNO_SMOKE_H3_ATTENTION=sage`** passes `KUNO_H3_ATTENTION=sage` to every H3 worker, which starts its SGLang servers
with `--attention-backend sage_attn`. It needs an image with SageAttention built in, which the worker refuses to run
without. `h3-0.1.0-fda88a73e660` is the first published image that has it; its kernels have not yet been imported on a
GPU. The A/B of 2026-09-17 ran in a container committed by `h3_sglang/sage-ab.sh`. Leave it unset for FlashAttention,
which every measurement so far used.
- **One H3 load per group.** A group given two H3 variants (say `h3-turbo,h3`) exits at start, which is
  `kuno-h3-worker`'s rule on 141 GB H200s and 180 GB B200s. That group's profiles are reported as failed.
- **Tested.** Only with `KUNO_SMOKE_MOCK=1` so far (2026-09-17).

## Other tasks

Both need the same rented machine as a smoke run, and reuse weights already downloaded there.

**The cost grid** (about 1–3 h on one GPU, `--time-budget` caps it):

```bash
KUNO_SMOKE_TASK=bench KUNO_SMOKE_BENCH_ARGS="--time-budget 2h --check-determinism" ./ltx-smoke.sh
```

It writes `results/bench.json`: per profile, cold and warm load times, seconds per denoising step, and wall time,
GPU-seconds per output second and peak memory for every resolution × fps × duration cell that fits the budget.
Feed it to `kuno-devkit derive-rates` to get VCU weights and rates with the margin check applied.

**Determinism** (minutes, once the weights are there):

```bash
KUNO_SMOKE_TASK=determinism KUNO_SMOKE_HARDWARE_CLASS=C1.rtx-pro-6000-bw-se.x1 \
  KUNO_SMOKE_PROFILES=ltx-2.5-fast ./ltx-smoke.sh
```

`kuno-verified-check` exists only in images built at subnet `528d31d` or later, so this task needs a newer worker
image than the tags below default to: pass `KUNO_SMOKE_WORKER_TAG`, or build one on the box and use
`KUNO_SMOKE_WORKER_IMAGE` with `KUNO_SMOKE_PULL=missing`.

The hardware class is what turns verified mode on, so it is required and must be one the profile lists (see
`profiles.json`; `C1.rtx-pro-6000-bw-se.x1` is the RTX PRO 6000 Server Edition). It runs `kuno-verified-check run`
twice — the second process takes its cases from the first run's file — then `compare`, and writes
`results/verified-<profile>-a.json`, `-b.json` and the compare log. A pass means every leaf matched; the run file
is then what `python -m kuno_validator.golden adopt` publishes as that class's golden set.

A divergence is reported by the step it happened at: leaf 0 is the seed's noise, a differing conditioning digest is
the text encoder, a later leaf is the denoiser.

## Output

Everything for one run is under `KUNO_SMOKE_DIR/runs/<UTC timestamp>/`:

| Path | What it is |
|---|---|
| `ltx-smoke-<stamp>.tar.gz` | `results/` below, packed. Send this one file back. |
| `results/results.json` | Pass/fail per profile and overall, with timings and peak memory; details below. |
| `results/state.tsv` | The raw facts the script recorded, one `key<TAB>value` per line; `results.json` is built from it. |
| `results/samples.csv` | Once a second: host RAM total/used (KiB), and the busiest GPU's memory used/total (MiB) and utilization. With `KUNO_SMOKE_GPUS` or `_GROUPS`, only the run's GPUs count. |
| `results/weights.json` | Repo, resolved revision, folders and bytes downloaded, seconds, and what was skipped. |
| `results/preflight.txt`, `preflight.json` | `kuno-preflight --no-tee --gateway …` inside the worker image. |
| `results/plan-<profile>.txt` | `kuno-plan <profile> text_to_video …`. It prints the `cold` backend's `ltx_pipelines` command, which is informational under `real`. |
| `results/resident-call-<profile>.json` | The keyword arguments the resident backend will pass to diffusers, checked against the pipeline's signature before the worker starts. |
| `results/bench.json` | `bench` task: the measured cost grid, rewritten after every profile. |
| `results/verified-<profile>-a.json`, `-b.json` | `determinism` task: each process's committed leaves, with the cases both ran. |
| `results/jobs/<profile>.mp4` | The generated video. |
| `results/jobs/<profile>.job.json` | Job id, params, status timeline, receipt summary, wall/queue/render/download seconds, SHA-256 against the receipt. |
| `results/jobs/<profile>.ffprobe.json`, `.check.json` | ffprobe's output and the checks run on it. |
| `results/logs/` | `gateway.log`, `worker-<profile>.log` (`worker-g<i>.log` with groups), `job-<profile>.log`, `weights.log`, `pull.log`, `devkit.log`, and the stderr of preflight, plan and ffprobe. |
| `data/` | The gateway's data dir: dev keys, SQLite, blobs. Owned by uid 10001 and **not** in the tarball. |

**`results.json`:**
- `timings_s`: `image_pull_s`, `weights_download_s`, `devkit_init_s`, `gateway_start_s`.
- Per profile under `profiles.<id>`:
  - `worker_cold_start_to_registered_s`;
  - `job_wall_s`, `job_queued_s`, `render_s_from_receipt`;
  - `video`, with its ffprobe summary;
  - `checks`;
  - `peaks`: GPU MiB and host RAM GiB while that profile's worker ran;
  - `gpus` and `gpu_group`: the worker's GPU list, and its group with `KUNO_SMOKE_GROUPS`.
- `peaks_whole_run`, `host`, `images` (tags and image IDs), `settings`, `prerequisites`.

**What the ffprobe check requires:**
- an MP4 whose SHA-256 is the receipt's content digest;
- a video stream of the requested size (1280x704 for 720p 16:9);
- a duration within 0.5 s of the request and 0.15 s of the receipt;
- with audio on, an audio stream whose length matches the video within 0.25 s.

A wrong frame rate, frame count or a non-H.264 codec is reported as a warning.

Containers are removed on exit, including Ctrl-C. The weights, `results/` and `data/` stay. To delete a run's `data/` as a
non-root user:

```bash
docker run --rm -v "$PWD/kuno-smoke/runs/<stamp>:/r" ubuntu:24.04 rm -rf /r/data
```

## Settings

All optional.

| Variable | Default | Meaning |
|---|---|---|
| `KUNO_SMOKE_DIR` | `./kuno-smoke` | Weights, runs and tarballs |
| `KUNO_SMOKE_MODELS_DIR` | `$KUNO_SMOKE_DIR/models/ltx-2.5` | Where the weights are kept |
| `KUNO_SMOKE_FAMILY` | `ltx` | `ltx` or `h3`; picks the defaults marked "H3:" below |
| `KUNO_SMOKE_TASK` | `smoke` | `smoke`, `bench` or `determinism` ([above](#other-tasks)) |
| `KUNO_SMOKE_HARDWARE_CLASS` | unset | The verified hardware class this machine declares; required by `determinism`, optional for `bench` |
| `KUNO_SMOKE_BENCH_ARGS` | `--time-budget 2h --check-determinism` | Extra `kuno-bench` flags |
| `KUNO_SMOKE_CASES` | `3` | Golden cases per profile in the `determinism` task |
| `KUNO_SMOKE_PROFILES` | `ltx-2.5-fast,ltx-2.5-pro` (H3: `h3`) | Profiles to test, in order; one worker container each |
| `KUNO_SMOKE_GPUS` | unset: every GPU (H3: `0,1,2,3`) | The worker's GPUs as nvidia-smi indices ([above](#sharing-the-machine-gpu-lists-and-gpu-groups)) |
| `KUNO_SMOKE_GROUPS` | unset | `"<gpus>:<profiles> ..."`: one worker per GPU group, all up at once, against one gateway |
| `KUNO_SMOKE_TURBO_LORA_REPO`, `_TURBO_LORA_REVISION` | `lightx2v/Minimax-h3-Turbo`, `3ec17a32…` | Where `h3-turbo`'s 8-step LoRA comes from |
| `KUNO_SMOKE_COUNTRY` | unset (H3: required) | The test customer's country, sent as `x-kuno-country`, and the worker's `KUNO_MINER_COUNTRY` |
| `KUNO_SMOKE_PRIVACY` | `standard` (H3: `private`) | Private jobs go through the SDK, sealed to the enclave |
| `KUNO_SMOKE_STORYBOARD` | unset | A storyboard JSON (`long_video/storyboards/`): `ltx-2.5-fast` renders it as one storyboard job |
| `KUNO_SMOKE_PLAN` | unset | A brief JSON (`long_video/briefs/`): `ltx-2.5-fast` plans it through the gateway with the SDK, then renders the plan as a storyboard |
| `KUNO_SMOKE_SDK_DIR` | `./sdk` or the repo's `sdk/python/src` | The `kunoworld` SDK mounted into the job helper |
| `KUNO_SMOKE_REFERENCE_IMAGE`, `KUNO_SMOKE_PROMPT` | unset | A reference image (needed by `h3-reference`) and a prompt to replace the built-in one |
| `KUNO_SMOKE_DURATION`, `_RESOLUTION`, `_ASPECT`, `_FPS`, `_AUDIO` | `2`, `720p`, `16:9`, `24`, `1` (H3: `5`, `768p`) | The test job |
| `KUNO_SMOKE_LTX_OFFLOAD` | `auto` | `KUNO_LTX_OFFLOAD` for the worker: `auto`, `none`, `model` or `group` |
| `KUNO_SMOKE_WEIGHTS_VERIFY` | `full` | `KUNO_WEIGHTS_VERIFY` (`size` needs `KUNO_MODEL_DIGEST`) |
| `KUNO_MODEL_DIGEST` | unset | Passed to the worker when set |
| `KUNO_SMOKE_REGISTRY` | `ghcr.io/concil859856` | Image registry and namespace |
| `KUNO_SMOKE_WORKER_TAG`, `_GATEWAY_TAG`, `_DEVKIT_TAG` | `ltx-0.1.0-fda88a73e660` (or `h3-0.1.0-fda88a73e660`), `65e4bc789542`, `fda88a73e660` | Image tags |
| `KUNO_SMOKE_WORKER_IMAGE`, `_GATEWAY_IMAGE`, `_DEVKIT_IMAGE` | built from the two rows above | Whole image references, e.g. `…@sha256:…` |
| `KUNO_SMOKE_SKIP_LOGIN`, `KUNO_SMOKE_REGISTRY_USER` | `0`, `concil859856` | Skip `docker login` (public images); the login user name |
| `KUNO_SMOKE_PULL` | `always` | `missing`: use an image already on this machine (e.g. one built there) and pull the rest |
| `KUNO_SMOKE_HF_REPO`, `KUNO_SMOKE_HF_REVISION` | `Lightricks/LTX-2.5-Diffusers`, `426936f8b22d…` (H3: `MiniMaxAI/MiniMax-H3`, `main`) | Weights source |
| `KUNO_SMOKE_DOWNLOAD_WORKERS` | `4` | Files downloaded in parallel |
| `KUNO_SMOKE_PORT` | `18180` | Gateway port on 127.0.0.1 |
| `KUNO_SMOKE_REGISTER_TIMEOUT`, `KUNO_SMOKE_JOB_TIMEOUT` | `2700`, `1800` | Seconds |
| `KUNO_SMOKE_MIN_DRIVER`, `_MIN_GPU_MIB`, `_MIN_DISK_GB`, `_MIN_RAM_GB`, `_MIN_GPUS` | `570`, `80000`, `200`, `64`, `1` (H3: `580`, `140000`, `4` GPUs) | Prerequisite thresholds |
| `KUNO_SMOKE_MOCK` | `0` | `1`: the dry run below |

## Dry run without a GPU

```bash
KUNO_SMOKE_MOCK=1 KUNO_SMOKE_DIR=/tmp/gpu-smoke scripts/gpu-test/ltx-smoke.sh
```

**What changes:**
- It skips the GPU, driver, RAM, disk and token checks and the weights download.
- It uses the local images `kuno-worker:ltx`, `kunoworld/gateway:local` and `kunoworld/mock-worker:local`.
- It runs the same LTX worker image with `KUNO_BACKEND=mock` (placeholder video from ffmpeg).

**What still runs:** devkit init, the gateway, preflight and plan, the resident-call check, worker registration, the
Standard job, polling, download, ffprobe, `results.json`, the tarball and cleanup. Only the model itself is left out.

The H3 image dry-runs the same way. The job is Private and goes through the SDK. The mock gateway image is the
published one, since no local `kunoworld/gateway:local` build is needed:

```bash
KUNO_SMOKE_MOCK=1 KUNO_SMOKE_FAMILY=h3 KUNO_SMOKE_COUNTRY=JP KUNO_SMOKE_GROUPS="0,1,2,3:h3-turbo 4,5,6,7:h3" \
  KUNO_SMOKE_WORKER_IMAGE=ghcr.io/concil859856/kunoworld-worker:h3-0.1.0-fda88a73e660 \
  KUNO_SMOKE_GATEWAY_IMAGE=ghcr.io/concil859856/kunoworld-gateway:65e4bc789542 \
  KUNO_SMOKE_DEVKIT_IMAGE=ghcr.io/concil859856/kunoworld-mock-worker:fda88a73e660 KUNO_SMOKE_DIR=/tmp/gpu-smoke-h3 scripts/gpu-test/ltx-smoke.sh
```

On 2026-09-17 three dry runs passed:
- `KUNO_SMOKE_PROFILES=h3-turbo,h3` with `KUNO_SMOKE_GPUS=0,1,2,3`;
- the two groups above;
- the default LTX run.

It takes about a minute. Each worker registers in about 9 s, most of it loading the safety classifiers on the CPU, and
each job takes about 6 s. `preflight` exits 1 ("no NVIDIA GPU"); that is recorded, not judged. `ltx-2.5-fast` shows the
`second_stage_sigmas` warning described under Troubleshooting.

## Troubleshooting

**The weights download stops with HTTP 401 or 403.** `Lightricks/LTX-2.5-Diffusers` is gated.
- 401: `HF_TOKEN` is missing, mistyped or revoked.
- 403: the token's account has no access. Open the repo page signed in as the account that accepted the licence. A
  fine-grained token also needs "Read access to contents of all public gated repos you can access".

Nothing else starts. Re-run once fixed; completed files are kept.

**`driver: NVIDIA 550.x is older than R570`.** The image's CUDA 12.8 PyTorch needs R570 or newer. Pick a host image with a newer
driver; a driver can't be upgraded from inside a container.

**`docker-gpu` fails.** Install `nvidia-container-toolkit`, run `sudo nvidia-ctk runtime configure --runtime=docker`, then
`sudo systemctl restart docker`.

**`docker login` or pull is denied.** `GITHUB_TOKEN` needs `read:packages` and access to the private `concil859856`
packages. To use another registry, set `KUNO_SMOKE_REGISTRY` and the tags.

**Out of memory.**
- **GPU:** `torch.OutOfMemoryError` / `CUDA out of memory` in `logs/worker-<profile>.log`. It shows either before
  registering (loading) or as a failed job. With `KUNO_LTX_OFFLOAD=auto` and no hardware class, the whole bf16 pipeline goes
  onto the GPU:
  - the transformer, about 39 GiB;
  - the Gemma text encoder, about 22 GiB;
  - the prompt enhancer, about 9.5 GiB;
  - the connectors, VAEs and vocoder, about 8 GiB;
  - the safety classifiers, and activations.

  That is tight on 96 GB. Re-run with `KUNO_SMOKE_LTX_OFFLOAD=model` (slower), or `group`.
- **Host:** `OOMKilled true` in `state.tsv` / `results.json`. It needs more RAM, or `KUNO_SMOKE_PROFILES=ltx-2.5-fast` on
  its own.

**The worker never registers.** The script prints the last worker log lines and records the reason. In
`logs/worker-<profile>.log`:
- **still `loading ltx-2.5-…`:** hashing 81 GB (`KUNO_WEIGHTS_VERIFY=full`) then loading can pass 10 minutes on slow disks.
  Raise `KUNO_SMOKE_REGISTER_TIMEOUT`.
- **`… needs <folder> under /models/ltx-2.5, which is missing`:** the weights for that profile were not downloaded. Run
  again with the same `KUNO_SMOKE_PROFILES`.
- **`no CUDA device is visible to PyTorch`:** the container has no GPU; see `docker-gpu` above.
- **`the gateway rejected this enclave's attestation`:** the worker's `kuno_protocol` and the gateway's disagree. Use the
  default tags together.
- **`worker loop exited unexpectedly (a backend failed to warm up?)`:** loading failed; the traceback is above that line.

**The job fails with `TypeError: … unexpected keyword argument 'second_stage_sigmas'`.** The worker image predates
`ltx-0.1.0-0ad70874cd6b`. Older images passed `second_stage_sigmas` straight to diffusers 0.40's `LTX2Pipeline`, which has no
such parameter; from that tag on, the worker runs the two stages itself through the latent upsampler. Use the default tag.

**`127.0.0.1:18180 is in use`.** Set `KUNO_SMOKE_PORT`.
