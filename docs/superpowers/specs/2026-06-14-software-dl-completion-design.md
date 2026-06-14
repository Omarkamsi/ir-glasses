# Software / DL Completion — Design Spec

**Date:** 2026-06-14
**Project:** IR Counter-Surveillance Glasses (senior design)
**Scope:** Complete the software / deep-learning evaluation half of the project so the
central claim is *defensible*, not anecdotal. Hardware is the next phase and is out of
scope here.

## Context

The repo (`github.com/Omarkamsi/ir-glasses`) already has a clean, working evaluation
pipeline: a pluggable face-recognition "adversary" (`face_eval.py`), an IR-disruption
simulator (`ir_simulator.py`), an experiment runner (`experiment.py`), a camera detector,
and a demo. Today (this session) we enabled the real **YuNet + SFace CNN backend** and
regenerated the result figures, confirming the headline finding with a real model:
identity **recognition** collapses (75% @ I=0.6, 17% @ I=0.7) a full intensity step before
face **detection** does (100% until I=0.8).

The remaining gap to a committee-defensible study is four-fold: the result rests on a
**single face** (the bundled astronaut sample), uses **one model**, does not characterize
the **real-world boundary** (the IR-cut-filter / daylight limitation the README flags as a
headline finding), and lacks a consolidated **report figure set**. This spec closes those
gaps.

## Decisions (locked)

- **Dataset:** Labeled Faces in the Wild (LFW) via `sklearn.datasets.fetch_lfw_people`.
  Verified working: 62 subjects with ≥20 color images each at 125×94. Standard, citable
  FR benchmark — no personal data required.
- **Second model:** dlib / `face_recognition` (ResNet-128) for a genuinely different
  architecture. Building now; if the build fails, fall back to a second ONNX recognizer.
- **Environment:** isolated `software/.venv` (gitignored). Models gitignored (`*.onnx`),
  documented in README.

## The four pieces

Each piece is independent, testable on its own, and produces a graph.

### 1. Multi-subject statistical evaluation (foundation)

**New module `dataset.py`** — loads LFW, selects N subjects (default 15) whose clean image
the active backend can enroll, and returns per subject: one **clean enrollment image** plus
a held-out list of **test images** (enroll and test images are disjoint — no testing on the
enrolled frame).

**Extend `experiment.py`** with a `--dataset lfw [--subjects N] [--per-subject K]` mode.
For each (subject, test image, intensity) it detects the face, applies
`apply_ir_disruption` targeted on the detected box, and evaluates against that subject's
enrolled embedding. Rows accumulate to `results.csv` with a `subject` column.

**Confidence intervals.** Add a small `stats.py` with a **Wilson score interval** for
binomial proportions. `plot_rates` gains shaded 95% CI bands around the detection and
recognition curves. This is the anecdote→evidence step.

- Output: `results.csv` (per-trial), `results_rates.png` (curves + CI bands),
  `results_scores.png` (mean similarity ± std vs threshold).

### 2. Multi-model comparison (breadth)

**New script `compare_models.py`** — runs the piece-1 multi-subject sweep once per
available backend (`opencv`, and `dlib` if importable), overlays the **recognition** curves,
and computes a **disruption threshold** per model: the IR intensity where the recognition
rate crosses 50% (linear interpolation between the bracketing sweep points).

- Output: `model_comparison.png` (overlaid recognition curves, one per model, with each
  model's 50% threshold marked) and a printed/CSV summary table of thresholds.
- Fallback: if only one backend is available, the script still runs and notes that breadth
  is single-model; the spec's headline claims do not depend on dlib succeeding.

### 3. Real-world boundary heatmap (the headline limitation)

**Extend `ir_simulator.apply_ir_disruption`** with an `ir_cut` parameter in `[0, 1]` that
attenuates the glare/wash/banding terms — modeling a camera's IR-cut filter or bright
daylight. `ir_cut=0` → night / IR-illuminated / no-cut camera (full effect); `ir_cut=1` →
daylight with a strong IR-cut filter (effect largely removed). Default `0.0` keeps existing
behavior and all current results unchanged.

**New script `boundary.py`** — sweeps a grid of (IR intensity × ir_cut), computes the
recognition rate at each cell averaged over the LFW subjects, and renders a 2-D heatmap.
This *characterizes where the technique works vs fails*.

- Output: `boundary_heatmap.png` (recognition rate over intensity × IR-cut), with the
  "works" region (low IR-cut) visually distinct from the "fails" region (high IR-cut).

### 4. Demo + report figure set (showcase)

Assemble a single multi-panel **`report_panel.png`** for the poster/report: the rates curve
with CI bands, the model comparison, the boundary heatmap, and a strip of sample
disrupted faces at increasing intensity. Confirm `demo.py` still runs headless and (where a
camera exists) live. No behavior change to `demo.py` beyond ensuring it reads the new
outputs cleanly.

## Module map (what changes)

| File | Change |
|------|--------|
| `software/dataset.py` | **new** — LFW loader, per-subject enroll/test split |
| `software/stats.py` | **new** — Wilson CI helper |
| `software/experiment.py` | add `--dataset lfw` path; CI bands; `subject` column |
| `software/ir_simulator.py` | add `ir_cut` parameter (default 0.0, backward-compatible) |
| `software/compare_models.py` | **new** — multi-backend overlay + disruption threshold |
| `software/boundary.py` | **new** — intensity × IR-cut heatmap |
| `software/requirements.txt` | add `scikit-learn`; note dlib as optional 2nd model |
| `software/README.md` | document the new dataset / comparison / boundary commands |
| `software/example_outputs/` | add the new figures |

All new code follows the existing style: module docstring explaining *why*, the same
`FaceEvaluator` API (untouched), `matplotlib.use("Agg")` headless plotting, argparse CLIs.

## Verification (end to end)

1. `python experiment.py --dataset lfw --subjects 15` → `results.csv` has a `subject`
   column with ≥15 distinct subjects; `results_rates.png` shows two curves with visible CI
   bands; recognition curve sits below detection curve in the mid-intensity range
   (reproduces the headline finding across subjects, not just one face).
2. `python compare_models.py` → `model_comparison.png` renders; prints a threshold table;
   if dlib is present, two curves appear.
3. `python boundary.py` → `boundary_heatmap.png` renders; recognition rate is high
   (technique fails) at high `ir_cut` and low (technique works) at low `ir_cut`.
4. `python demo.py` → `demo_panel.png` still produced headless.
5. Existing default run `python experiment.py` (single bundled face) still works unchanged —
   `ir_cut` defaults to 0.0, so prior behavior and committed results are preserved.

## Out of scope (later phases)

- Hardware build, firmware tuning, and capturing **real** frames through the glasses
  (`experiment.py --real-dir` already supports that data path for when hardware is ready).
- CNN-based camera detector (the retroreflection detector stays as-is).
