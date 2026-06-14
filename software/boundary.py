"""boundary.py — characterize WHERE the IR technique works. Sweeps a grid of
(IR intensity x ir_cut) and plots the mean recognition rate as a heatmap. Low ir_cut
(night / no IR-cut filter) is where disruption works; high ir_cut (daylight / IR-cut
camera) is where it fails. This boundary is itself a headline finding."""
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from face_eval import FaceEvaluator
from dataset import load_lfw_subjects
from ir_simulator import apply_ir_disruption


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subjects", type=int, default=10)
    ap.add_argument("--per-subject", type=int, default=4)
    ap.add_argument("--steps", type=int, default=6)
    args = ap.parse_args()

    ev = FaceEvaluator(backend="auto")
    subs = load_lfw_subjects(ev, n_subjects=args.subjects, per_subject=args.per_subject)
    refs = [(ev.enroll(s["enroll"]), s["test"]) for s in subs]

    intensities = np.linspace(0, 1, args.steps)
    ircuts = np.linspace(0, 1, args.steps)
    grid = np.zeros((len(ircuts), len(intensities)))

    for yi, ic in enumerate(ircuts):
        for xi, inten in enumerate(intensities):
            hits = total = 0
            for ref, tests in refs:
                for ti, img in enumerate(tests):
                    frame = apply_ir_disruption(img, intensity=inten, ir_cut=ic, seed=ti)
                    hits += int(ev.evaluate(frame, ref)["recognized"])
                    total += 1
            grid[yi, xi] = hits / max(total, 1)

    plt.figure(figsize=(6.8, 5.2))
    im = plt.imshow(grid * 100, origin="lower", aspect="auto", cmap="magma",
                    extent=[0, 1, 0, 1], vmin=0, vmax=100)
    plt.colorbar(im, label="Identity recognition rate (%)")
    plt.xlabel("IR disruption intensity")
    plt.ylabel("Camera IR-cut strength (0=night, 1=daylight)")
    plt.title(f"Where IR disruption works ({ev.backend} backend)")
    plt.tight_layout()
    plt.savefig("boundary_heatmap.png", dpi=140)
    plt.close()
    print("wrote boundary_heatmap.png")
    print("corner check  inten=1,ircut=0 -> %.0f%%   inten=1,ircut=1 -> %.0f%%"
          % (grid[0, -1] * 100, grid[-1, -1] * 100))


if __name__ == "__main__":
    main()
