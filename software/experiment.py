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
from stats import wilson_interval, baseline_correct


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
            rows.append({"subject": "bundled", "intensity": lv, "seed": s,
                         "detected": int(r["detected"]),
                         "recognized": int(r["recognized"]),
                         "score": r["score"] if r["score"] is not None else np.nan})
    return rows


def run_dataset(ev, subjects, levels):
    """Multi-subject simulated sweep. Enroll each subject's clean image, then apply IR
    disruption to each held-out test image across intensities. This is the statistically
    defensible counterpart to run_simulated (n subjects, not n=1)."""
    rows = []
    for s in subjects:
        ref = ev.enroll(s["enroll"])
        for ti, img in enumerate(s["test"]):
            dets = ev.detect(img)
            box = dets[0]["box"] if dets else None
            for lv in levels:
                frame = apply_ir_disruption(img, face_box=box, intensity=lv, seed=ti)
                r = ev.evaluate(frame, ref)
                rows.append({"subject": s["name"], "intensity": lv, "seed": ti,
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
            rows.append({"subject": sub, "intensity": lv, "seed": i,
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
        n = len(sub)
        det_lo, det_hi = wilson_interval(int(np.sum([r["detected"] for r in sub])), n)
        rec_lo, rec_hi = wilson_interval(int(np.sum([r["recognized"] for r in sub])), n)
        agg[lv] = {"det_rate": det, "rec_rate": rec,
                   "score_mean": np.mean(scores) if scores else np.nan,
                   "score_std": np.std(scores) if scores else np.nan,
                   "n": n, "det_lo": det_lo, "det_hi": det_hi,
                   "rec_lo": rec_lo, "rec_hi": rec_hi}
    return levels, agg


def plot_rates(levels, agg, backend, out="results_rates.png"):
    det = [agg[l]["det_rate"] * 100 for l in levels]
    rec = [agg[l]["rec_rate"] * 100 for l in levels]
    plt.figure(figsize=(7, 4.5))
    rec_bc = [v * 100 for v in baseline_correct([agg[l]["rec_rate"] for l in levels])]
    plt.plot(levels, det, "o-", label="Face detected", linewidth=2)
    plt.plot(levels, rec, "s-", label="Identity recognised", linewidth=2)
    plt.plot(levels, rec_bc, "--", color="gray", alpha=0.8,
             label="Recognition (baseline-corrected)")
    if all("det_lo" in agg[l] for l in levels):
        plt.fill_between(levels, [agg[l]["det_lo"] * 100 for l in levels],
                         [agg[l]["det_hi"] * 100 for l in levels], alpha=0.15)
        plt.fill_between(levels, [agg[l]["rec_lo"] * 100 for l in levels],
                         [agg[l]["rec_hi"] * 100 for l in levels], alpha=0.15)
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
    ap.add_argument("--dataset", default=None, help="'lfw' for the multi-subject benchmark")
    ap.add_argument("--subjects", type=int, default=15, help="LFW subjects (dataset mode)")
    ap.add_argument("--per-subject", type=int, default=6, help="test images per subject")
    ap.add_argument("--backend", default="auto")
    ap.add_argument("--seeds", type=int, default=12, help="repeats per intensity (simulated)")
    args = ap.parse_args()

    ev = FaceEvaluator(backend=args.backend)

    if args.dataset == "lfw":
        from dataset import load_lfw_subjects
        levels = [round(0.1 * i, 1) for i in range(0, 11)]
        subjects = load_lfw_subjects(ev, n_subjects=args.subjects,
                                     per_subject=args.per_subject)
        print(f"loaded {len(subjects)} LFW subjects")
        rows = run_dataset(ev, subjects, levels)
    elif args.real_dir:
        ref_emb = ev.enroll(load_reference(args.image))
        print("enrolled reference, dim =", len(ref_emb))
        rows = run_real(ev, ref_emb, args.real_dir)
    else:
        ref_img = load_reference(args.image)
        ref_emb = ev.enroll(ref_img)
        print("enrolled reference, dim =", len(ref_emb))
        levels = [round(0.1 * i, 1) for i in range(0, 11)]
        seeds = list(range(args.seeds))
        rows = run_simulated(ev, ref_img, ref_emb, levels, seeds)

    with open("results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["subject", "intensity", "seed", "detected",
                                          "recognized", "score"])
        w.writeheader()
        w.writerows(rows)

    levels, agg = aggregate(rows)
    rec_bc = baseline_correct([agg[l]["rec_rate"] for l in levels])
    print("\nintensity | detect% | recog% | recog%(base-corr) | mean score")
    for l, bc in zip(levels, rec_bc):
        a = agg[l]
        print(f"   {l:>4}   |  {a['det_rate']*100:5.0f}  | {a['rec_rate']*100:5.0f}  | "
              f"     {bc*100:5.0f}        | {a['score_mean']:.3f}")

    f1 = plot_rates(levels, agg, ev.backend)
    f2 = plot_scores(levels, agg, ev.recog_threshold, ev.backend)
    print(f"\nwrote results.csv, {f1}, {f2}")


if __name__ == "__main__":
    main()
