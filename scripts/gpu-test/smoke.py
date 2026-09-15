"""Helpers for ltx-smoke.sh. Every subcommand runs inside one of the KunoWorld images, never on the host:

  fetch-weights  worker image   the LTX-2.5-Diffusers files the chosen profiles load, resumable
  resident-call  worker image   the diffusers call the resident backend will make, checked against the pipeline signature
  run-job        gateway image  one Standard-mode text-to-video job with the dev API key: submit, poll, download
  check-video    gateway image  ffprobe's view of the MP4 against the request and the enclave's receipt
  results        gateway image  results.json from the run's state, samples, jobs and checks

Standard library only, plus what the image already carries (huggingface_hub, diffusers, kuno_worker, httpx,
kuno_protocol). Secrets (HF_TOKEN, the dev API key) come from the environment or the data dir and are never printed.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROMPT = "A lighthouse on a cliff at dawn, waves rolling in"


def read_env(path: Path) -> dict[str, str]:
    pairs = (line.split("=", 1) for line in path.read_text().splitlines() if "=" in line and not line.startswith("#"))
    return {key.strip(): value.strip() for key, value in pairs}


def write_json(path: Path, data) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)


def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def gb(n: float) -> str:
    return f"{n / 1e9:.2f} GB"


# ------------------------------------------------------------------ fetch-weights (worker image)


def _hub_failure(exc: Exception, repo: str) -> int:
    if isinstance(exc, OSError) and not hasattr(exc, "response"):
        print(f"fetch-weights: cannot write the weights locally: {exc} (the models dir must be writable by this user)", file=sys.stderr)
        return 24
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if status in (401, 403) or type(exc).__name__ == "GatedRepoError":
        print(
            f"fetch-weights: HTTP {status} from Hugging Face: {repo} is gated.\n"
            f"  401: HF_TOKEN is missing, mistyped or revoked.\n"
            f"  403: the token works but its account has no access yet. Open https://huggingface.co/{repo} signed in as the\n"
            "       account that accepted the licence and check access is granted; a fine-grained token also needs\n"
            "       'Read access to contents of all public gated repos you can access'.",
            file=sys.stderr,
        )
        return 20
    print(f"fetch-weights: Hugging Face request failed: {type(exc).__name__}: {str(exc)[:400]}", file=sys.stderr)
    return 21


def _complete(path: Path, size: int) -> bool:
    try:
        return path.is_file() and path.stat().st_size == size
    except OSError:
        return False


def cmd_fetch_weights(args) -> int:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from huggingface_hub import HfApi, hf_hub_download
    from kuno_protocol.profiles import load_profiles
    from kuno_worker.backends.quantized import resolve_recipe

    if not os.environ.get("HF_TOKEN"):
        print("fetch-weights: HF_TOKEN is not set", file=sys.stderr)
        return 20
    dest = Path(args.dest)
    started = time.time()

    # What the worker reads: the recipe's include list (all of it is hashed before loading, so all of it must exist)
    # plus every component model_index.json names (LTX2Pipeline.from_pretrained loads each one), with the profile's
    # own transformer subfolder instead of model_index's "transformer" (the loader passes that module in).
    profiles = load_profiles()
    include: set[str] = set()
    transformers: set[str] = set()
    recipes = {}
    for pid in args.profiles.split(","):
        recipe, _ = resolve_recipe(profiles[pid], None)
        recipes[pid] = {"recipe": recipe.id, "transformer_subfolder": recipe.transformer_subfolder, "include": list(recipe.include)}
        include.update(recipe.include)
        transformers.add(recipe.transformer_subfolder)

    api = HfApi()
    try:
        info = api.model_info(args.repo, revision=args.revision, files_metadata=True)
        index_path = hf_hub_download(args.repo, "model_index.json", revision=info.sha, local_dir=dest)
    except Exception as exc:  # classified: gated (401/403) or anything else
        return _hub_failure(exc, args.repo)
    sizes = {s.rfilename: int(s.size or 0) for s in info.siblings}
    model_index = json.loads(Path(index_path).read_text())
    components = sorted(
        k for k, v in model_index.items() if not k.startswith("_") and isinstance(v, list) and len(v) == 2 and v[0] is not None
    )
    wanted = (include | set(components) | transformers) - ({"transformer"} - transformers)

    keep: dict[str, int] = {}
    unused: dict[str, int] = {}
    for entry in sorted(wanted):
        if entry in sizes:  # a file at the repo root, such as model_index.json
            keep[entry] = sizes[entry]
            continue
        files = sorted(f for f in sizes if f.startswith(entry + "/"))
        if not files:
            print(f"fetch-weights: {args.repo}@{info.sha[:12]} has no {entry}/, which the worker loads", file=sys.stderr)
            return 22
        # A folder with a *.safetensors.index.json loads only the shards its weight_map names (diffusers and transformers
        # both prefer the index); LTX-2.5-Diffusers also ships unreferenced copies (a second shard set in transformer/,
        # a single-file connectors/), which are skipped.
        indexes = [f for f in files if f.endswith(".safetensors.index.json")]
        shards: set[str] = set()
        for index in indexes:
            try:
                local = hf_hub_download(args.repo, index, revision=info.sha, local_dir=dest)
            except Exception as exc:
                return _hub_failure(exc, args.repo)
            parent = Path(index).parent
            shards.update((parent / name).as_posix() for name in json.loads(Path(local).read_text()).get("weight_map", {}).values())
        missing = sorted(s for s in shards if s not in sizes)
        if missing:
            print(f"fetch-weights: {entry}'s index names shards the repo lacks: {', '.join(missing[:3])}", file=sys.stderr)
            return 22
        for f in files:
            if indexes and f.endswith(".safetensors") and f not in shards:
                unused[f] = sizes[f]
            else:
                keep[f] = sizes[f]
    for f, size in sizes.items():
        if f not in keep and f not in unused:
            unused[f] = size

    total = sum(keep.values())
    todo = sorted((f for f in keep if not _complete(dest / f, keep[f])), key=keep.get)
    present = total - sum(keep[f] for f in todo)
    folders: dict[str, int] = {}
    for f, size in keep.items():
        folders[f.split("/")[0]] = folders.get(f.split("/")[0], 0) + size
    print(f"{args.repo}@{info.sha[:12]} for {args.profiles}: {len(keep)} files, {gb(total)}; {gb(present)} already in {dest}")
    for folder, size in sorted(folders.items()):
        print(f"  {folder:28s} {gb(size):>10s}")
    print(f"  not downloaded: {len(unused)} files, {gb(sum(unused.values()))} (unused by these profiles, or unreferenced shard copies)")

    done = present
    failure = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(hf_hub_download, args.repo, f, revision=info.sha, local_dir=dest): f for f in todo}
        for n, future in enumerate(as_completed(futures), 1):
            name = futures[future]
            try:
                future.result()
            except Exception as exc:
                failure = failure or _hub_failure(exc, args.repo)
                for other in futures:
                    other.cancel()
                continue
            done += keep[name]
            print(f"  [{n}/{len(todo)}] {name} ({gb(keep[name])}); {gb(done)} of {gb(total)} on disk after {time.time() - started:.0f}s", flush=True)
    if failure:
        return failure
    bad = [f for f in keep if not _complete(dest / f, keep[f])]
    if bad:
        print(f"fetch-weights: {len(bad)} file(s) have the wrong size after download, e.g. {bad[0]}: run again to resume", file=sys.stderr)
        return 23
    seconds = round(time.time() - started, 1)
    write_json(
        Path(args.summary),
        {
            "repo": args.repo, "revision_requested": args.revision, "revision": info.sha, "profiles": recipes,
            "model_index_components": components, "folders_bytes": folders, "files": len(keep), "bytes": total,
            "downloaded_bytes": total - present, "already_present_bytes": present, "seconds": seconds,
            "not_downloaded_bytes": sum(unused.values()),
            "not_downloaded": {f: s for f, s in sorted(unused.items()) if s >= 1_000_000},
        },
    )
    print(f"weights ready: {gb(total)} in {seconds:.0f}s ({gb(total - present)} downloaded)")
    return 0


# ------------------------------------------------------------------ resident-call (worker image)


def cmd_resident_call(args) -> int:
    import inspect
    import tempfile

    import diffusers
    from kuno_protocol.profiles import Mode, load_profiles
    from kuno_worker.backends.ltx_resident import build_call
    from kuno_worker.plan import build_task, example_task

    profile = load_profiles()[args.profile]
    params = example_task(
        profile, Mode.TEXT_TO_VIDEO, duration_s=args.duration, resolution=args.resolution, aspect_ratio=args.aspect,
        fps=args.fps, audio=bool(args.audio),
    )
    with tempfile.TemporaryDirectory(prefix="kuno-smoke-") as tmp:
        call = build_call(build_task(profile, params, Path(tmp), seed=42, prompt=PROMPT, negative_prompt=None))
    kind = call.pop("pipeline")
    # LtxAdapter (backends/runtimes.py) consumes these before it calls the pipeline, and adds `generator`.
    # `second_stage_sigmas` becomes its second call (latents, audio_latents, noise_scale, sigmas).
    for key in ("seed", "generate_audio", "kuno_trajectory_tap", "second_stage_sigmas"):
        call.pop(key, None)
    from diffusers import LTX2ConditionPipeline, LTX2Pipeline

    cls = LTX2ConditionPipeline if kind == "condition" else LTX2Pipeline
    parameters = inspect.signature(cls.__call__).parameters
    open_ended = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values())
    unexpected = [] if open_ended else sorted(set(call) - set(parameters))
    write_json(
        Path(args.out),
        {
            "profile": profile.id, "pipeline_kind": kind, "pipeline_class": cls.__name__, "diffusers": diffusers.__version__,
            "call": {k: v for k, v in call.items() if k != "prompt"}, "unexpected_kwargs": unexpected,
        },
    )
    if unexpected:
        print(
            f"  WARN  {profile.id}: the resident backend calls {cls.__name__} with {', '.join(unexpected)}, which diffusers "
            f"{diffusers.__version__} does not accept; with KUNO_BACKEND=real expect this job to fail with a TypeError"
        )
        return 10
    print(f"  ok    {profile.id}: the resident call's keywords all exist on {cls.__name__} (diffusers {diffusers.__version__})")
    return 0


# ------------------------------------------------------------------ run-job (gateway image)


def _error_text(response) -> tuple[str | None, str]:
    try:
        body = response.json()
    except ValueError:
        return None, response.text[:300]
    detail = body.get("detail", body) if isinstance(body, dict) else body
    if isinstance(detail, dict):
        inner = detail.get("error") if isinstance(detail.get("error"), dict) else detail
        return inner.get("code"), str(inner.get("message") or json.dumps(detail))[:300]
    return None, json.dumps(detail)[:300]


def cmd_run_job(args) -> int:
    import uuid

    import httpx
    from kuno_protocol.canonical import sha256_hex
    from kuno_protocol.profiles import Mode, load_profiles, validate_params
    from kuno_protocol.schemas import GenerationParams

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    from kuno_protocol.profiles import InputRole

    profile = load_profiles()[args.profile]
    limits = profile.limits
    prompt = args.prompt or PROMPT
    params = GenerationParams(
        profile_id=profile.id, mode=Mode(args.mode), duration_s=float(args.duration), resolution=args.resolution,
        aspect_ratio=args.aspect, fps=args.fps, audio=bool(args.audio) and limits.audio,
        input_roles=[InputRole.REFERENCE_IMAGE] * len(args.reference_image),
    )
    validate_params(profile, params)
    width, height = limits.sizes[args.resolution][args.aspect]
    job_id = str(uuid.uuid4())
    record: dict = {
        "profile": profile.id, "job_id": job_id, "privacy": args.privacy, "prompt": prompt, "seed": args.seed,
        "params": params.model_dump(mode="json"),
        "expected": {"width": width, "height": height, "frames": profile.num_frames(params.duration_s, params.fps), "audio": params.audio},
        "result": "fail", "error": None, "timeline": [],
    }

    def finish(code: int, error: str | None = None) -> int:
        record["result"], record["error"] = ("pass" if code == 0 else "fail"), error
        write_json(out / f"{profile.id}.job.json", record)
        if error:
            print(f"FAIL  {profile.id}: {error}", flush=True)
        return code

    headers = {"authorization": f"Bearer {read_env(Path(args.data) / 'dev.env')['KUNO_DEV_API_KEY']}"}
    if args.country:
        headers["x-kuno-country"] = args.country
    body = {"job_id": job_id, "params": params.model_dump(mode="json"), "prompt": prompt, "seed": args.seed, "options": {}, "inputs": []}
    private = args.privacy == "private"
    if args.reference_image and not private:
        return finish(1, "reference images are only wired for Private mode (--privacy private)")
    if private:
        # Private mode, as a customer's program does it: the SDK routes to an attested enclave (checked against the dev
        # golden manifest), seals the request to it, and later checks the enclave's receipt and opens the sealed video.
        from kuno_protocol.attestation import GoldenManifest
        from kunoworld import Input, KunoClient, KunoError

        manifest = GoldenManifest.model_validate_json((Path(args.data) / "manifest.json").read_text())
        sdk = KunoClient(headers["authorization"].removeprefix("Bearer "), args.gateway, manifest=manifest, country=args.country or None)
    with httpx.Client(base_url=args.gateway, timeout=60.0) as client:
        started = time.time()
        while True:  # a freshly registered worker can briefly be missing from job routing: retry capacity errors
            if private:
                try:
                    inputs = [Input.load(InputRole.REFERENCE_IMAGE, Path(path)) for path in args.reference_image]
                    prepared = sdk.prepare(
                        prompt, inputs=inputs, model=profile.id, mode=Mode(args.mode), duration_s=params.duration_s, resolution=args.resolution,
                        aspect_ratio=args.aspect, fps=args.fps, audio=params.audio, seed=args.seed,
                    )
                    sdk_job = sdk.submit(prepared)
                    job_id = record["job_id"] = sdk_job.job_id
                    break
                except KunoError as exc:
                    status_code, code, message = (list(exc.args) + [0, "error", ""])[:3]
                    problem = f"the gateway refused the job: HTTP {status_code} {code}: {message}"
                    if status_code not in (409, 429, 503):
                        return finish(1, problem)
                except httpx.HTTPError as exc:
                    problem = f"could not reach the gateway: {type(exc).__name__}"
            else:
                try:
                    response = client.post("/v1/standard/videos", json=body, headers=headers)
                except httpx.HTTPError as exc:
                    response, problem = None, f"could not reach the gateway: {type(exc).__name__}"
                else:
                    code, message = _error_text(response) if response.status_code != 201 else (None, "")
                    if response.status_code == 201 or code == "duplicate_job":
                        break
                    problem = f"the gateway refused the job: HTTP {response.status_code} {code}: {message}"
                    if response.status_code not in (409, 429, 503):
                        return finish(1, problem)
            if time.time() - started > args.submit_retry_s:
                return finish(1, problem)
            print(f"  {problem}; retrying", flush=True)
            time.sleep(3)
        submitted = time.time()
        record["submit_s"] = round(submitted - started, 2)
        print(
            f"{profile.id}: submitted {args.privacy.capitalize()} job {job_id}: {width}x{height}, {params.duration_s:g}s at {params.fps} fps, "
            f"audio {'on' if params.audio else 'off'}", flush=True,
        )
        last = None
        status: dict = {}
        while True:
            try:
                response = client.get(f"/v1/videos/{job_id}", headers=headers)
                response.raise_for_status()
                status = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                if time.time() - submitted > args.timeout:
                    return finish(1, f"polling the job failed: {type(exc).__name__}")
                time.sleep(args.poll)
                continue
            now = time.time()
            if (status["status"], status.get("stage")) != last:
                last = (status["status"], status.get("stage"))
                record["timeline"].append(
                    {"t_s": round(now - submitted, 2), "status": status["status"], "stage": status.get("stage"), "progress": status.get("progress")}
                )
                stage = f" / {status['stage']}" if status.get("stage") else ""
                print(f"  +{now - submitted:7.1f}s  {status['status']}{stage}  {100 * float(status.get('progress') or 0):.0f}%", flush=True)
            if status["status"] in ("succeeded", "failed", "canceled"):
                break
            if now - submitted > args.timeout:
                try:
                    client.post(f"/v1/videos/{job_id}/cancel", headers=headers)
                except httpx.HTTPError:
                    pass
                return finish(1, f"the job was still {status['status']} after {args.timeout:.0f}s; canceled it")
            time.sleep(args.poll)
        record["wall_s"] = round(time.time() - submitted, 2)
        first = {}
        for event in record["timeline"]:
            first.setdefault(event["status"], event["t_s"])
        record["queued_s"] = first.get("running")
        record["status"] = {k: status.get(k) for k in ("status", "stage", "error_code", "error", "enclave_id", "price_usd")}
        if status["status"] != "succeeded":
            return finish(1, f"the job {status['status']}: {status.get('error_code')}: {status.get('error')}")
        receipt = (status.get("receipt") or {}).get("body") or {}
        record["receipt"] = {
            k: receipt.get(k)
            for k in ("image_digest", "enclave_id", "miner_hotkey", "gpu_seconds", "started_at", "finished_at", "output_bytes", "content_digest", "video")
        }
        if receipt.get("started_at") and receipt.get("finished_at"):
            record["render_s"] = round(float(receipt["finished_at"]) - float(receipt["started_at"]), 2)
        began = time.time()
        if private:
            try:
                data = sdk_job.result().video  # the sealed blob, checked against the enclave's signed receipt, then opened
            except KunoError as exc:
                return finish(1, f"opening the private video failed: {exc.args}")
        else:
            response = client.get(f"/v1/standard/videos/{job_id}/video", headers=headers, timeout=600.0)
            if response.status_code != 200:
                code, message = _error_text(response)
                return finish(1, f"downloading the video failed: HTTP {response.status_code} {code}: {message}")
            data = response.content
        record["download_s"] = round(time.time() - began, 2)
        digest = sha256_hex(data)
        record["video"] = {"file": f"{profile.id}.mp4", "bytes": len(data), "sha256": digest, "matches_receipt": digest == receipt.get("content_digest")}
        (out / f"{profile.id}.mp4").write_bytes(data)
        if not record["video"]["matches_receipt"]:
            return finish(1, "the downloaded video's SHA-256 is not the receipt's content digest")
        print(f"{profile.id}: succeeded after {record['wall_s']:.1f}s; {len(data)} bytes, SHA-256 matches the receipt", flush=True)
        return finish(0)


# ------------------------------------------------------------------ check-video (gateway image)


def _rate(text: str | None) -> float | None:
    try:
        num, _, den = (text or "").partition("/")
        return float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return None


def cmd_check_video(args) -> int:
    job = json.loads(Path(args.job).read_text())
    probe = json.loads(Path(args.ffprobe).read_text())
    streams, fmt = probe.get("streams", []), probe.get("format", {})
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    expected, params = job["expected"], job["params"]
    claimed = (job.get("receipt") or {}).get("video") or {}
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str, severity: str = "fail") -> None:
        checks.append({"name": name, "ok": bool(ok), "severity": severity, "detail": detail})

    check("MP4 container", "mp4" in fmt.get("format_name", ""), fmt.get("format_name", "?"))
    check("SHA-256 matches the receipt", (job.get("video") or {}).get("matches_receipt") is True, (job.get("video") or {}).get("sha256", "?"))
    check("video stream", video is not None, video.get("codec_name", "?") if video else "none")
    summary = {"format": fmt.get("format_name"), "bytes": int(fmt.get("size") or 0), "duration_s": float(fmt.get("duration") or 0)}
    if video is not None:
        width, height = int(video.get("width") or 0), int(video.get("height") or 0)
        duration = float(video.get("duration") or fmt.get("duration") or 0)
        fps = _rate(video.get("avg_frame_rate"))
        frames = int(video["nb_frames"]) if str(video.get("nb_frames", "")).isdigit() else None
        summary |= {"video_codec": video.get("codec_name"), "width": width, "height": height, "video_duration_s": duration, "fps": fps, "frames": frames}
        check("codec is H.264", video.get("codec_name") == "h264", video.get("codec_name", "?"), severity="warn")
        check("size matches the request", (width, height) == (expected["width"], expected["height"]), f"{width}x{height}, asked {expected['width']}x{expected['height']}")
        asked = float(params["duration_s"])
        check("duration matches the request", abs(duration - asked) <= max(0.5, 0.25 * asked), f"{duration:.3f}s, asked {asked:g}s")
        if claimed:
            check("duration matches the receipt", abs(duration - float(claimed["duration_s"])) <= 0.15, f"{duration:.3f}s, receipt {claimed['duration_s']}s")
        if fps is not None:
            check("frame rate matches the request", abs(fps - float(params["fps"])) < 0.01, f"{fps:g} fps, asked {params['fps']}", severity="warn")
        if frames is not None:
            check("frame count matches the profile", frames == expected["frames"], f"{frames}, profile renders {expected['frames']}", severity="warn")
    if expected["audio"]:
        check("audio stream", audio is not None, audio.get("codec_name", "?") if audio else "none")
        if audio is not None and video is not None:
            audio_duration = float(audio.get("duration") or 0)
            summary |= {"audio_codec": audio.get("codec_name"), "audio_duration_s": audio_duration, "sample_rate": audio.get("sample_rate")}
            check(
                "audio length matches the video", abs(audio_duration - summary["video_duration_s"]) <= 0.25,
                f"audio {audio_duration:.3f}s at {audio.get('sample_rate')} Hz, video {summary['video_duration_s']:.3f}s",
            )
    else:
        check("no audio stream (audio off)", audio is None, "none" if audio is None else audio.get("codec_name", "?"))

    passed = all(c["ok"] or c["severity"] == "warn" for c in checks)
    write_json(Path(args.out), {"profile": job["profile"], "result": "pass" if passed else "fail", "ffprobe": summary, "checks": checks})
    for c in checks:
        mark = "ok  " if c["ok"] else ("warn" if c["severity"] == "warn" else "FAIL")
        print(f"  {mark}  {c['name']}: {c['detail']}")
    return 0 if passed else 1


# ------------------------------------------------------------------ results (gateway image)


def _number(value: str | None):
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return value


def _iso(epoch: str | None) -> str | None:
    value = _number(epoch)
    return datetime.fromtimestamp(value, timezone.utc).isoformat(timespec="seconds") if isinstance(value, float) else None


def cmd_results(args) -> int:
    root = Path(args.dir)
    state: dict[str, str] = {}
    failures: list[str] = []
    for line in (root / "state.tsv").read_text().splitlines():
        key, _, value = line.partition("\t")
        if key == "failure":
            failures.append(value)
        else:
            state[key] = value

    samples = []
    if (root / "samples.csv").exists():
        with (root / "samples.csv").open() as handle:
            for row in csv.DictReader(handle):
                try:
                    samples.append({k: (float(v) if v not in ("", None) else None) for k, v in row.items()})
                except ValueError:
                    continue

    def peaks(start: float | None = None, end: float | None = None) -> dict:
        rows = [r for r in samples if (start is None or r["epoch_s"] >= start) and (end is None or r["epoch_s"] <= end)]
        gpu = [r["gpu_mem_used_mib"] for r in rows if r.get("gpu_mem_used_mib") is not None]
        util = [r["gpu_util_pct"] for r in rows if r.get("gpu_util_pct") is not None]
        ram = [r["mem_used_kib"] for r in rows if r.get("mem_used_kib") is not None]
        return {
            "samples": len(rows),
            "gpu_mem_used_mib_peak": max(gpu) if gpu else None,
            "gpu_mem_total_mib": next((r["gpu_mem_total_mib"] for r in rows if r.get("gpu_mem_total_mib")), None),
            "gpu_util_pct_peak": max(util) if util else None,
            "host_ram_used_gib_peak": round(max(ram) / 2**20, 2) if ram else None,
            "host_ram_used_gib_at_start": round(ram[0] / 2**20, 2) if ram else None,
        }

    profiles = [p for p in state.get("profiles", "").split(",") if p]
    detail = {}
    for pid in profiles:
        pre = f"profile.{pid}."
        job = load_json(root / "jobs" / f"{pid}.job.json") or {}
        checked = load_json(root / "jobs" / f"{pid}.check.json") or {}
        resident = load_json(root / f"resident-call-{pid}.json") or {}
        error = state.get(pre + "error") or job.get("error")
        passed = job.get("result") == "pass" and checked.get("result") == "pass" and not state.get(pre + "error")
        if pre + "worker_start_epoch" not in state:
            error = error or "not run (the run stopped before this profile)"
        detail[pid] = {
            "result": "pass" if passed else "fail",
            "error": error,
            "worker_cold_start_to_registered_s": _number(state.get(pre + "cold_start_to_registered_s")),
            "job_id": job.get("job_id"),
            "job_wall_s": job.get("wall_s"),
            "job_queued_s": job.get("queued_s"),
            "render_s_from_receipt": job.get("render_s"),
            "gpu_seconds_from_receipt": (job.get("receipt") or {}).get("gpu_seconds"),
            "download_s": job.get("download_s"),
            "timeline": job.get("timeline"),
            "params": job.get("params"),
            "video": (job.get("video") or {}) | {"ffprobe": checked.get("ffprobe")},
            "checks": checked.get("checks"),
            "image_digest_in_receipt": (job.get("receipt") or {}).get("image_digest"),
            "plan_exit": _number(state.get(pre + "plan_exit")),
            "resident_call": {"pipeline_class": resident.get("pipeline_class"), "unexpected_kwargs": resident.get("unexpected_kwargs")},
            "worker_exit": state.get(pre + "worker_exit"),
            "peaks": peaks(_number(state.get(pre + "worker_start_epoch")), _number(state.get(pre + "worker_stop_epoch"))),
        }

    passed = bool(profiles) and all(d["result"] == "pass" for d in detail.values()) and not failures
    started, finished = _number(state.get("started_epoch")), _number(state.get("finished_epoch"))
    preflight = load_json(root / "preflight.json") or {}
    results = {
        "result": "pass" if passed else "fail",
        "mode": state.get("mode"),
        "backend": state.get("backend"),
        "model_exercised": state.get("backend") in ("real", "cold"),
        "started_at": _iso(state.get("started_epoch")),
        "finished_at": _iso(state.get("finished_epoch")),
        "total_s": round(finished - started, 1) if isinstance(started, float) and isinstance(finished, float) else None,
        "profiles_tested": profiles,
        "failures": failures,
        "timings_s": {k[len("timing."):]: _number(v) for k, v in state.items() if k.startswith("timing.")},
        "profiles": detail,
        "peaks_whole_run": peaks(),
        "host": {k[len("host."):]: v for k, v in state.items() if k.startswith("host.")},
        "images": {k[len("image."):]: v for k, v in state.items() if k.startswith("image.")},
        "settings": {k[len("setting."):]: v for k, v in state.items() if k.startswith("setting.")},
        "prerequisites": {k[len("check."):]: v for k, v in state.items() if k.startswith("check.")},
        "preflight": {"exit": _number(state.get("preflight_exit")), "blocked": preflight.get("blocked"), "servable": preflight.get("servable")},
        "weights": load_json(root / "weights.json"),
    }
    write_json(root / "results.json", results)

    for pid, d in detail.items():
        video = (d["video"] or {}).get("ffprobe") or {}
        size = f"{video.get('width')}x{video.get('height')} {video.get('video_duration_s') or 0:.2f}s {video.get('video_codec')}" if video else "no video"
        audio = f"+{video['audio_codec']}" if video.get("audio_codec") else ""
        gpu = d["peaks"]["gpu_mem_used_mib_peak"]
        line = (
            f"{'PASS' if d['result'] == 'pass' else 'FAIL'}  {pid}: registered after {d['worker_cold_start_to_registered_s']}s, "
            f"job {d['job_wall_s']}s, {size}{audio}, peak GPU {'n/a' if gpu is None else f'{gpu:.0f} MiB'}, "
            f"peak host RAM {d['peaks']['host_ram_used_gib_peak']} GiB"
        )
        print(line + (f"\n      error: {d['error']}" if d["error"] and d["result"] != "pass" else ""))
    for failure in failures:
        print(f"FAIL  {failure}")
    note = "" if results["model_exercised"] else f" (KUNO_BACKEND={results['backend']}: the model itself was not exercised)"
    print(f"RESULT: {'PASS' if passed else 'FAIL'}{note}")
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch-weights")
    fetch.add_argument("--repo", required=True)
    fetch.add_argument("--revision", required=True)
    fetch.add_argument("--profiles", required=True)
    fetch.add_argument("--dest", required=True)
    fetch.add_argument("--summary", required=True)
    fetch.add_argument("--workers", type=int, default=4)

    def job_shape(p):
        p.add_argument("--profile", required=True)
        p.add_argument("--duration", type=float, required=True)
        p.add_argument("--resolution", required=True)
        p.add_argument("--aspect", required=True)
        p.add_argument("--fps", type=int, required=True)
        p.add_argument("--audio", type=int, choices=[0, 1], required=True)

    resident = sub.add_parser("resident-call")
    job_shape(resident)
    resident.add_argument("--out", required=True)

    run = sub.add_parser("run-job")
    job_shape(run)
    run.add_argument("--gateway", required=True)
    run.add_argument("--data", required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--seed", type=int, default=1234)
    run.add_argument("--timeout", type=float, default=1800.0)
    run.add_argument("--poll", type=float, default=2.0)
    run.add_argument("--submit-retry-s", type=float, default=120.0)
    run.add_argument("--country", default="", help="sent as x-kuno-country; the dev gateway honours it")
    run.add_argument("--mode", default="text_to_video", help="reference_to_video needs --reference-image")
    run.add_argument("--reference-image", action="append", default=[], help="a reference image file (Private mode)")
    run.add_argument("--prompt", default="", help="instead of the built-in prompt")
    run.add_argument("--privacy", choices=["standard", "private"], default="standard",
                     help="private goes through the kunoworld SDK (on PYTHONPATH): sealed to the attested enclave")

    check = sub.add_parser("check-video")
    check.add_argument("--job", required=True)
    check.add_argument("--ffprobe", required=True)
    check.add_argument("--out", required=True)

    results = sub.add_parser("results")
    results.add_argument("--dir", required=True)

    args = parser.parse_args()
    handler = {
        "fetch-weights": cmd_fetch_weights, "resident-call": cmd_resident_call, "run-job": cmd_run_job,
        "check-video": cmd_check_video, "results": cmd_results,
    }[args.command]
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
