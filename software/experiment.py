"""
experiment.py
-------------
Produces the core results of the project: how face DETECTION and RECOGNITION degrade as
the IR disruption increases. Outputs a CSV plus two publication-style figures.

Two data sources:
  * Simulated (default): uses ir_simulator on a reference face. Great before the hardware
    exists and for clean, repeatable curves.
  * Real captures (--real-dir DIR): DIR contains sub-folders named by intensity
    (e.g. 0.0/, 0.3/, 0.6/ ...), each holding frames captured through the real glasses.
    Same metrics, real data. This is your final-report dataset.

Usage:
  python experiment.py                          # simulated sweep on the bundled face
  python experiment.py --image me.jpg           # simulated sweep on your own enrolled face
  python experiment.py --real-dir captures/     # real captured frames
"""

import os
import csv
import argparse
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from face_eval import FaceEvaluator
from ir_simulator import apply_ir_disruption


def load_reference(image_path):
    if image_path and os.path.exists(image_path):
        img = cv2.imread(image_path)
        if img is None:
            raise RuntimeError(f"could not read {image_path}")
        return img
    from skimage import data
    return cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)


def run_simulated(ev, ref_img, ref_emb, levels, seeds):
    rows = []
    for lv in levels:
        for s in seeds:
            frame = apply_ir_disruption(ref_img, intensity=lv, seed=s)
            r = ev.evaluate(frame, ref_emb)
            rows.append({"intensity": lv, "seed": s,
                         "detected": int(r["detected"]),
                         "recognized": int(r["recognized"]),
                         "score": r["score"] if r["score"] is not None else np.nan})
    return rows


def run_real(ev, ref_emb, real_dir):
    rows = []
    for sub in sorted(os.listdir(real_dir)):
        path = os.path.join(real_dir, sub)
        if not os.path.isdir(path):
            continue
        try:
            lv = float(sub)
        except ValueError:
            continue
        for i, fn in enumerate(sorted(os.listdir(path))):
            img = cv2.imread(os.path.join(path, fn))
            if img is None:
                continue
            r = ev.evaluate(img, ref_emb)
            rows.append({"intensity": lv, "seed": i,
                         "detected": int(r["detected"]),
                         "recognized": int(r["recognized"]),
                         "score": r["score"] if r["score"] is not None else np.nan})
    return rows


def aggregate(rows):
    levels = sorted(set(r["intensity"] for r in rows))
    agg = {}
    for lv in levels:
        sub = [r for r in rows if r["intensity"] == lv]
        det = np.mean([r["detected"] for r in sub])
        rec = np.mean([r["recognized"] for r in sub])
        scores = [r["score"] for r in sub if not np.isnan(r["score"])]
        agg[lv] = {"det_rate": det, "rec_rate": rec,
                   "score_mean": np.mean(scores) if scores else np.nan,
                   "score_std": np.std(scores) if scores else np.nan}
    return levels, agg


def plot_rates(levels, agg, backend, out="results_rates.png"):
    det = [agg[l]["det_rate"] * 100 for l in levels]
    rec = [agg[l]["rec_rate"] * 100 for l in levels]
    plt.figure(figsize=(7, 4.5))
    plt.plot(levels, det, "o-", label="Face detected", linewidth=2)
    plt.plot(levels, rec, "s-", label="Identity recognised", linewidth=2)
    plt.xlabel("IR disruption intensity")
    plt.ylabel("Success rate (%)")
    plt.title(f"Face detection & recognition vs IR intensity  ({backend} backend)")
    plt.ylim(-5, 105)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out, dpi=140)
    plt.close()
    return out


def plot_scores(levels, agg, threshold, backend, out="results_scores.png"):
    means = [agg[l]["score_mean"] for l in levels]
    stds = [agg[l]["score_std"] for l in levels]
    plt.figure(figsize=(7, 4.5))
    plt.errorbar(levels, means, yerr=stds, fmt="o-", capsize=4, linewidth=2,
                 label="Mean similarity score")
    plt.axhline(threshold, color="red", linestyle="--",
                label=f"Match threshold ({threshold})")
    plt.xlabel("IR disruption intensity")
    plt.ylabel("Embedding similarity to enrolled face")
    plt.title(f"Recognition confidence vs IR intensity  ({backend} backend)")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out, dpi=140)
    plt.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=None, help="reference face image (else bundled face)")
    ap.add_argument("--real-dir", default=None, help="dir of real captures by intensity")
    ap.add_argument("--backend", default="auto")
    ap.add_argument("--seeds", type=int, default=12, help="repeats per intensity (simulated)")
    args = ap.parse_args()

    ev = FaceEvaluator(backend=args.backend)
    ref_img = load_reference(args.image)
    ref_emb = ev.enroll(ref_img)
    print("enrolled reference, dim =", len(ref_emb))

    if args.real_dir:
        rows = run_real(ev, ref_emb, args.real_dir)
    else:
        levels = [round(0.1 * i, 1) for i in range(0, 11)]
        seeds = list(range(args.seeds))
        rows = run_simulated(ev, ref_img, ref_emb, levels, seeds)

    with open("results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["intensity", "seed", "detected",
                                          "recognized", "score"])
        w.writeheader()
        w.writerows(rows)

    levels, agg = aggregate(rows)
    print("\nintensity | detect% | recog% | mean score")
    for l in levels:
        a = agg[l]
        print(f"   {l:>4}   |  {a['det_rate']*100:5.0f}  | {a['rec_rate']*100:5.0f}  | "
              f"{a['score_mean']:.3f}")

    f1 = plot_rates(levels, agg, ev.backend)
    f2 = plot_scores(levels, agg, ev.recog_threshold, ev.backend)
    print(f"\nwrote results.csv, {f1}, {f2}")


if __name__ == "__main__":
    main()
