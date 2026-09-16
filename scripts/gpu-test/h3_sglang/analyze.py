"""Summarizes turbo-run results: GPU-seconds per output second, cost at confidential rental prices, price floors."""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

d = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
GPU_H = {"cc": 4.80, "plain": 4.00}  # USD per H200 GPU-hour (PRICING.md §1)
UTIL = 0.60
FLOOR = 1.25 / 0.60  # miner pay = cost x 1.25, at most 60% of the customer price

rows = [json.loads(line) for line in (d / "results.jsonl").read_text().splitlines() if line.strip()]
print(f"{'run':38} {'ok':3} {'wall s':>7} {'GPU-s/s':>8} {'cost cc@60%':>11} {'price floor':>11}  notes")
for r in rows:
    if "gpu_s_per_output_s" not in r:
        print(f"{r['name']:38} {str(r.get('ok'))[:3]:3} {r.get('wall_s', ''):>7}  {r.get('error') or ''}")
        continue
    g = r["gpu_s_per_output_s"]
    cost = g * GPU_H["cc"] / 3600 / UTIL
    streams = r.get("probe", {}).get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    a = next((s for s in streams if s.get("codec_type") == "audio"), {})
    note = f"{v.get('width')}x{v.get('height')} {v.get('nb_frames')}f audio {a.get('sample_rate')}" + (" WARMUP" if r.get("warmup") else "")
    print(f"{r['name']:38} {'ok':3} {r['wall_s']:>7} {g:>8} {cost:>11.4f} {cost * FLOOR:>11.4f}  {note}")

mem = d / "gpu-mem.csv"
if mem.exists():
    peak = defaultdict(int)
    for line in csv.reader(mem.open()):
        if len(line) >= 3:
            peak[line[1].strip()] = max(peak[line[1].strip()], int(line[2].strip().split()[0]))
    print("peak MiB per GPU:", dict(sorted(peak.items())))
