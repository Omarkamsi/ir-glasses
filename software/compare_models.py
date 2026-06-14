"""compare_models.py — run the multi-subject sweep on each available FR backend,
overlay the recognition curves, and report each model's disruption threshold (the IR
intensity at which recognition first drops below 50%). Shows the effect is not specific
to one face-recognition model."""
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from face_eval import FaceEvaluator
from dataset import load_lfw_subjects
from experiment import run_dataset, aggregate


def disruption_threshold(levels, rec_rates, target=0.5):
    """First intensity where rec_rate crosses below `target`, linearly interpolated.
    Returns None if it never crosses."""
    for i in range(1, len(levels)):
        y0, y1 = rec_rates[i - 1], rec_rates[i]
        if y0 >= target > y1:
            x0, x1 = levels[i - 1], levels[i]
            frac = (y0 - target) / (y0 - y1) if y0 != y1 else 0.0
            return x0 + frac * (x1 - x0)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subjects", type=int, default=12)
    ap.add_argument("--per-subject", type=int, default=5)
    ap.add_argument("--backends", default="opencv,dlib")
    args = ap.parse_args()

    levels = [round(0.1 * i, 1) for i in range(0, 11)]
    plt.figure(figsize=(7.5, 4.8))
    table = []
    for backend in args.backends.split(","):
        try:
            ev = FaceEvaluator(backend=backend)
        except Exception as e:
            print(f"skip {backend}: {e}")
            continue
        subs = load_lfw_subjects(ev, n_subjects=args.subjects, per_subject=args.per_subject)
        rows = run_dataset(ev, subs, levels)
        lv, agg = aggregate(rows)
        rec = [agg[l]["rec_rate"] for l in lv]
        thr = disruption_threshold(lv, rec)
        table.append((backend, thr, len(subs)))
        plt.plot(lv, [r * 100 for r in rec], "o-", linewidth=2,
                 label=f"{backend} (thr={thr:.2f})" if thr else f"{backend} (no cross)")
        if thr is not None:
            plt.axvline(thr, color="gray", linestyle=":", alpha=0.5)

    plt.axhline(50, color="red", linestyle="--", alpha=0.6, label="50% recognition")
    plt.xlabel("IR disruption intensity")
    plt.ylabel("Identity recognition rate (%)")
    plt.title("Recognition vs IR intensity across FR models")
    plt.ylim(-5, 105)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig("model_comparison.png", dpi=140)
    plt.close()

    print("\nbackend | disruption threshold | subjects")
    for b, t, n in table:
        print(f"  {b:7} | {('%.2f' % t) if t else 'n/a':>20} | {n}")
    print("wrote model_comparison.png")


if __name__ == "__main__":
    main()
