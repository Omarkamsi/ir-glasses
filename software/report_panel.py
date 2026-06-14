"""report_panel.py — assemble the key figures into one poster/report panel.
Run experiment.py --dataset lfw, compare_models.py, boundary.py, and ir_simulator.py
first so the source PNGs exist."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

PANELS = [("results_rates.png", "Detection vs recognition (95% CI)"),
          ("model_comparison.png", "Across FR models"),
          ("boundary_heatmap.png", "Where it works (intensity x IR-cut)"),
          ("ir_sim_demo.png", "Simulated IR disruption")]

present = [(f, t) for f, t in PANELS if os.path.exists(f)]
n = len(present)
fig, axes = plt.subplots(2, 2, figsize=(13, 9))
for ax, (f, t) in zip(axes.flat, present):
    ax.imshow(mpimg.imread(f))
    ax.set_title(t, fontsize=11)
    ax.axis("off")
for ax in axes.flat[n:]:
    ax.axis("off")
fig.suptitle("IR Counter-Surveillance Glasses — DL Evaluation", fontsize=15, weight="bold")
fig.tight_layout()
fig.savefig("report_panel.png", dpi=130)
print("wrote report_panel.png")
