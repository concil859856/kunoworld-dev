"""Downloads MiniMax H3's weights into a Hugging Face cache, and the Turbo LoRA beside it, before any image is pulled.

The layout is the one the worker and `sglang serve` resolve offline: HF_HUB_CACHE=<cache>, `MiniMaxAI/MiniMax-H3` at
refs/<revision> (keep `main`: SGLang looks the model up by name, which reads refs/main). ltx-smoke.sh's own download then
finds every file present and takes seconds. Needs only huggingface_hub (with hf_xet), so it runs on the host:

    uv run --no-project --with 'huggingface_hub[hf_xet]==1.31.0' python fetch_h3.py \\
        --cache ~/kuno-smoke/models/h3 --lora-dir ~/kuno-smoke/models/h3/turbo --summary weights-h3.json

or in the H3 worker image (`/opt/kuno/bin/python fetch_h3.py ...`). Run the MiniMax licence region check first: the
licence excludes the US, EU, UK and South Korea, testing included. H3's repo is not gated, so no token is needed.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

H3_REPO = "MiniMaxAI/MiniMax-H3"
LORA_REPO = "lightx2v/Minimax-h3-Turbo"
LORA_REVISION = "3ec17a324ced54151364f24f8b5fb6bf7e26414f"  # measured on 2026-09-16
LORA_8STEP = "minimax_h3_fl2v_turbo_8step_v1.0_768p_bf16.safetensors"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", required=True, help="HF_HUB_CACHE the servers will use")
    parser.add_argument("--revision", default="main")
    parser.add_argument("--variants", default="FL2VA", help="comma-separated checkpoint folders: FL2VA (h3, h3-turbo), Ref2VA (h3-reference)")
    parser.add_argument("--lora-dir", default="", help="where the Turbo 8-step LoRA goes; empty skips it")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    os.environ.setdefault("HF_XET_HIGH_PERFORMANCE", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    from huggingface_hub import HfApi, hf_hub_download, snapshot_download

    summary: dict = {"repo": H3_REPO, "revision_requested": args.revision}
    started = time.time()
    patterns = ["*.json", "LICENSE", "README.md", *(f"{v.strip()}/*" for v in args.variants.split(",") if v.strip())]
    path = snapshot_download(H3_REPO, revision=args.revision, cache_dir=args.cache, allow_patterns=patterns, max_workers=args.workers)
    snapshot = Path(path)
    size = sum(f.stat().st_size for f in snapshot.rglob("*") if f.is_file())
    summary.update(revision=snapshot.name, allow_patterns=patterns, snapshot=str(snapshot), bytes=size, seconds=round(time.time() - started, 1))
    try:
        summary["revision_sha_now"] = HfApi().model_info(H3_REPO, revision=args.revision).sha
    except Exception as exc:  # noqa: BLE001 - informational
        summary["revision_sha_now"] = f"unavailable: {exc!r}"[:200]
    print(json.dumps({k: summary[k] for k in ("revision", "bytes", "seconds")}), flush=True)
    if args.lora_dir:
        lora_started = time.time()
        lora = hf_hub_download(LORA_REPO, LORA_8STEP, revision=LORA_REVISION, local_dir=args.lora_dir)
        summary["turbo_lora"] = {"repo": LORA_REPO, "revision": LORA_REVISION, "path": lora, "bytes": os.path.getsize(lora),
                                 "seconds": round(time.time() - lora_started, 1)}
        print(json.dumps(summary["turbo_lora"]), flush=True)
    summary["total_seconds"] = round(time.time() - started, 1)
    Path(args.summary).write_text(json.dumps(summary, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
