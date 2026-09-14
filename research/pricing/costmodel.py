"""Cost model for KunoWorld pricing notes. Every input is (low, base, high)."""
import json, math

# ---------- GPU prices, $/GPU-hour ----------
CONF_PRICE = {  # confidential tier: low = owned TCO (base case), base = rented CC-capable reserved, high = on-demand
    "RTX PRO 6000 BSE": (0.95, 1.80, 2.50),
    "H200": (2.05, 3.20, 4.80),
    "B200": (2.57, 4.50, 6.80),
    "B300": (2.91, 5.60, 7.90),
}
OPEN_PRICE = {
    "RTX 4090": (0.25, 0.34, 0.74),
    "RTX 5090": (0.40, 0.65, 0.99),
    "RTX PRO 6000": (1.06, 1.69, 2.20),
    "H100": (1.50, 2.59, 3.29),
}
CC = (0.02, 0.05, 0.15)

# ---------- LTX speed relative to H100 (higher = faster); wall = H100 wall / speed ----------
SPEED = {  # (slow, base, fast) -> we map low-cost case to fast, high-cost case to slow
    "H100": (1.0, 1.0, 1.0),
    "H200": (1.0, 1.10, 1.2),
    "RTX PRO 6000 BSE": (0.70, 0.85, 1.0),
    "RTX PRO 6000": (0.70, 0.85, 1.0),
    "B200": (2.0, 2.5, 3.0),
    "B300": (2.2, 2.7, 3.2),
    "RTX 5090": (0.25, 0.45, 0.70),
    "RTX 4090": (0.12, 0.25, 0.40),
}

# LTX wall seconds on H100, warm (low, base, high)
LTX_H100 = {
    ("ltx-2.5-fast", "720p", 5): (12, 20, 32),
    ("ltx-2.5-fast", "720p", 10): (25, 40, 65),
    ("ltx-2.5-fast", "1080p", 5): (22, 35, 55),
    ("ltx-2.5-fast", "1080p", 10): (50, 80, 130),
    ("ltx-2.5-pro", "720p", 5): (40, 65, 100),
    ("ltx-2.5-pro", "720p", 10): (90, 140, 210),
    ("ltx-2.5-pro", "1080p", 5): (100, 150, 220),
    ("ltx-2.5-pro", "1080p", 10): (210, 320, 480),
}
# 4K wall seconds on H200 (reference), then scaled by speed ratio vs H200
LTX4K_H200 = {
    ("ltx-2.5-4k", "1440p", 5): (85, 150, 240),
    ("ltx-2.5-4k", "2160p", 5): (160, 400, 850),
    ("ltx-2.5-4k", "2160p", 10): (340, 850, 1800),
}
# H3 wall seconds per clip on 4 GPUs
H3 = {
    "H200": {
        ("h3-turbo", "768p", 5): (16, 22, 30), ("h3-turbo", "768p", 10): (38, 50, 65), ("h3-turbo", "768p", 14): (63, 85, 111),
        ("h3", "768p", 5): (70, 75, 85), ("h3", "768p", 10): (185, 200, 230), ("h3", "768p", 14): (300, 335, 380),
        ("h3-reference", "768p", 5): (70, 112, 135), ("h3-reference", "768p", 10): (185, 300, 370), ("h3-reference", "768p", 14): (300, 500, 610),
    },
    "B300": {
        ("h3-turbo", "768p", 5): (9, 12, 16), ("h3-turbo", "768p", 10): (23, 30, 41), ("h3-turbo", "768p", 14): (38, 50, 71),
        ("h3", "768p", 5): (33, 42, 50), ("h3", "768p", 10): (88, 107, 130), ("h3", "768p", 14): (150, 187, 225),
        ("h3-reference", "768p", 5): (33, 63, 80), ("h3-reference", "768p", 10): (88, 160, 208), ("h3-reference", "768p", 14): (150, 280, 360),
    },
}
H3["B200"] = {k: tuple(round(x * 1.1) for x in v) for k, v in H3["B300"].items()}

CUSTOMER = {
    ("ltx-2.5-fast", "720p"): 0.024, ("ltx-2.5-fast", "1080p"): 0.04,
    ("ltx-2.5-pro", "720p"): 0.04, ("ltx-2.5-pro", "1080p"): 0.07,
    ("ltx-2.5-4k", "1440p"): 0.12, ("ltx-2.5-4k", "2160p"): 0.20,
    ("h3-turbo", "768p"): 0.06, ("h3", "768p"): 0.12, ("h3-reference", "768p"): 0.10,
}
VCU = {"ltx-2.5-fast": 5, "ltx-2.5-pro": 15, "ltx-2.5-4k": 40, "h3-turbo": 16, "h3": 60, "h3-reference": 64}
GPUS = {"ltx-2.5-fast": 1, "ltx-2.5-pro": 1, "ltx-2.5-4k": 1, "h3-turbo": 4, "h3": 4, "h3-reference": 4}
CONF_HW = {
    "ltx-2.5-fast": ["RTX PRO 6000 BSE", "H200", "B200", "B300"],
    "ltx-2.5-pro": ["H200", "B200", "B300"],
    "ltx-2.5-4k": ["H200", "B200", "B300"],
    "h3-turbo": ["H200", "B200", "B300"], "h3": ["H200", "B200", "B300"], "h3-reference": ["H200", "B200", "B300"],
}
OPEN_HW = {"ltx-2.5-fast": ["RTX 4090", "RTX 5090", "RTX PRO 6000", "H100"], "ltx-2.5-pro": ["RTX PRO 6000", "H100"]}


def wall(profile, res, dur, hw):
    """(low, base, high) wall seconds."""
    if profile.startswith("h3"):
        return H3[hw][(profile, res, dur)]
    if profile == "ltx-2.5-4k":
        ref = LTX4K_H200[(profile, res, dur)]
        s = SPEED[hw]; h = SPEED["H200"]
        return (ref[0] * h[1] / s[2], ref[1] * h[1] / s[1], ref[2] * h[1] / s[0])
    ref = LTX_H100[(profile, res, dur)]
    s = SPEED[hw]
    return (ref[0] / s[2], ref[1] / s[1], ref[2] / s[0])


def usd_per_s(price, gpus, wall_s, dur, util, cc):
    return price * gpus * wall_s * (1 + cc) / 3600 / dur / util


def rows():
    out = []
    keys = list(LTX_H100) + list(LTX4K_H200) + list(H3["H200"])
    for (profile, res, dur) in keys:
        for tier, hws, prices in (("conf", CONF_HW[profile], CONF_PRICE), ("open", OPEN_HW.get(profile, []), OPEN_PRICE)):
            for hw in hws:
                if hw in ("RTX 4090", "RTX 5090") and (res == "1080p" and dur == 10 and hw == "RTX 4090"):
                    pass
                w = wall(profile, res, dur, hw)
                p = prices[hw]
                cc = CC if tier == "conf" else (0, 0, 0)
                g = GPUS[profile]
                out.append(dict(
                    profile=profile, res=res, dur=dur, tier=tier, hw=hw, gpus=g,
                    wall=w, gpu_s_per_s=g * w[1] / dur,
                    low60=usd_per_s(p[0], g, w[0], dur, 0.60, cc[0]),
                    base30=usd_per_s(p[1], g, w[1], dur, 0.30, cc[1]),
                    base60=usd_per_s(p[1], g, w[1], dur, 0.60, cc[1]),
                    base85=usd_per_s(p[1], g, w[1], dur, 0.85, cc[1]),
                    high60=usd_per_s(p[2], g, w[2], dur, 0.60, cc[2]),
                    floor85_low=usd_per_s(p[0], g, w[0], dur, 0.85, cc[0]),
                    customer=CUSTOMER[(profile, res)],
                ))
    return out


def fmt(x):
    return f"{x:.4f}" if x < 0.1 else f"{x:.3f}"


if __name__ == "__main__":
    R = rows()
    print("| Profile | Res | Dur s | Tier | Hardware | Wall s (L/B/H) | GPU-s per out-s | $/s low@60% | $/s base@30% | base@60% | base@85% | $/s high@60% | Customer $/s |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in R:
        w = r["wall"]
        print(f"| {r['profile']} | {r['res']} | {r['dur']} | {r['tier']} | {r['hw']}{' x4' if r['gpus']==4 else ''} | {w[0]:.0f}/{w[1]:.0f}/{w[2]:.0f} | {r['gpu_s_per_s']:.1f} | {fmt(r['low60'])} | {fmt(r['base30'])} | {fmt(r['base60'])} | {fmt(r['base85'])} | {fmt(r['high60'])} | {r['customer']} |")

    # Placeholder check: miner pay and implied $/GPU-hour
    print("\n## Placeholder implied pay")
    print("| Profile | Res | Dur | HW | Placeholder conf $/s | Customer $/s | Output-s per GPU-h (100% util) | Implied $/GPU-h @100% | @60% | @30% |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in R:
        if r["tier"] != "conf":
            continue
        pay = 0.01 * VCU[r["profile"]]
        outs_per_gpuh = 3600 / (r["gpu_s_per_s"])
        print(f"| {r['profile']} | {r['res']} | {r['dur']} | {r['hw']} | {pay:.2f} | {r['customer']} | {outs_per_gpuh:.0f} | {pay*outs_per_gpuh:.1f} | {pay*outs_per_gpuh*0.6:.1f} | {pay*outs_per_gpuh*0.3:.1f} |")
    print("\n## Open-tier placeholder implied pay (0.5 x)")
    for r in R:
        if r["tier"] != "open":
            continue
        pay = 0.005 * VCU[r["profile"]]
        outs = 3600 / r["gpu_s_per_s"]
        print(f"| {r['profile']} | {r['res']} | {r['dur']} | {r['hw']} | {pay:.3f} | out-s/GPU-h {outs:.0f} | $/GPU-h@100% {pay*outs:.1f} | @60% {pay*outs*0.6:.1f} |")

    # VCU proportionality: GPU-s per output s on H200 vs VCU; cost-based
    print("\n## VCU check (H200 reference; H3 on 4xH200)")
    for r in R:
        if r["hw"] == "H200" and r["tier"] == "conf":
            print(f"| {r['profile']} | {r['res']} | {r['dur']} | GPU-s/out-s {r['gpu_s_per_s']:.1f} | VCU {VCU[r['profile']]} | ratio {r['gpu_s_per_s']/VCU[r['profile']]:.2f} | base $/s@100% {r['base60']*0.6:.4f} |")

    # Best (cheapest) confidential hardware per row at base60 and median across eligible
    print("\n## Confidential cost floors per row (base price, base wall, CC 5%)")
    import statistics
    groups = {}
    for r in R:
        if r["tier"] == "conf":
            groups.setdefault((r["profile"], r["res"], r["dur"]), []).append(r)
    for k, g in groups.items():
        best = min(g, key=lambda r: r["base60"])
        med = statistics.median([r["base60"] for r in g])
        best_low85 = min(r["floor85_low"] for r in g)
        print(f"| {k[0]} | {k[1]} | {k[2]} | cheapest {best['hw']} base@60 {best['base60']:.4f} | median base@60 {med:.4f} | best base@85 {best['base85']:.4f} | owned floor@85 {best_low85:.4f} | cust {best['customer']} |")
    print("\n## Open cost floors")
    groups = {}
    for r in R:
        if r["tier"] == "open":
            groups.setdefault((r["profile"], r["res"], r["dur"]), []).append(r)
    for k, g in groups.items():
        for r in g:
            print(f"| {k[0]} | {k[1]} | {k[2]} | {r['hw']} base@60 {r['base60']:.4f} base@85 {r['base85']:.4f} low@60 {r['low60']:.4f} high@60 {r['high60']:.4f}")
