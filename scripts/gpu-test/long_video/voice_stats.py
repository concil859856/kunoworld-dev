"""Per-shot voice stats for a long_video run directory: median F0 of voiced frames (autocorrelation), spectral centroid,
voiced fraction and RMS. A crude same-speaker check: no transcription, no speaker embedding."""
import json, subprocess, sys
from pathlib import Path
import numpy as np

SR = 16000
def pcm(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768

def stats(x):
    frame, hop = 640, 320
    f0s, cents, voiced = [], [], 0
    n = 0
    for i in range(0, len(x) - frame, hop):
        w = x[i:i + frame] * np.hanning(frame)
        n += 1
        if np.sqrt(np.mean(w ** 2)) < 0.01:
            continue
        spec = np.abs(np.fft.rfft(w)); freqs = np.fft.rfftfreq(frame, 1 / SR)
        cents.append(float((spec * freqs).sum() / (spec.sum() + 1e-9)))
        ac = np.correlate(w, w, "full")[frame - 1:]
        lo, hi = SR // 400, SR // 60
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.45 * ac[0]:
            f0s.append(SR / k); voiced += 1
    return {"f0_median": round(float(np.median(f0s)), 1) if f0s else None, "f0_iqr": [round(float(np.percentile(f0s, 25)), 1), round(float(np.percentile(f0s, 75)), 1)] if f0s else None,
            "centroid_hz": round(float(np.median(cents)), 0) if cents else None, "voiced_frac": round(voiced / max(n, 1), 2), "rms": round(float(np.sqrt(np.mean(x ** 2))), 4)}

if __name__ == "__main__":
    run = Path(sys.argv[1])
    print(run.name)
    for shot in sorted((run / "shots").glob("*.mp4")):
        print("  ", shot.name, stats(pcm(shot)))
