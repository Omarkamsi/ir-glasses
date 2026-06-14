# Software / DL Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the single-face IR-disruption demo into a defensible multi-subject, multi-model study with confidence intervals, a real-world-boundary heatmap, and a consolidated report figure.

**Architecture:** Keep the existing `FaceEvaluator` API untouched as the measurement instrument. Add focused modules around it: a stats helper (Wilson CI), an LFW dataset loader, an `ir_cut` knob on the simulator, and three driver scripts (`experiment.py` dataset mode, `compare_models.py`, `boundary.py`) that each emit a figure. All plotting stays headless (`matplotlib.use("Agg")`).

**Tech Stack:** Python 3.12, OpenCV (YuNet+SFace), dlib (ResNet-128), scikit-learn (LFW), numpy, matplotlib, pytest.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `software/stats.py` | **new** — Wilson score confidence interval for binomial proportions |
| `software/dataset.py` | **new** — load LFW, per-subject clean-enroll + disjoint test split |
| `software/face_eval.py` | **modify** — dlib backend uses dlib directly (models from `models/`) instead of the `face_recognition` wrapper |
| `software/ir_simulator.py` | **modify** — add `ir_cut` parameter (default 0.0, backward-compatible) |
| `software/experiment.py` | **modify** — add `--dataset lfw` mode; CI bands on rates plot; `subject` CSV column |
| `software/compare_models.py` | **new** — multi-backend overlay + disruption-threshold table |
| `software/boundary.py` | **new** — intensity × IR-cut recognition-rate heatmap |
| `software/report_panel.py` | **new** — assemble the multi-panel report figure |
| `software/tests/` | **new** — pytest unit tests for stats, dataset, ir_cut, threshold |
| `software/requirements.txt` | **modify** — add scikit-learn, pytest; note dlib models |
| `software/README.md` | **modify** — document new commands |
| `software/example_outputs/` | **modify** — add new figures |

Environment is already prepared (venv at `software/.venv`, all models downloaded). Activate with `. software/.venv/bin/activate` before any run.

---

## Task 0: Test harness + requirements

**Files:**
- Modify: `software/requirements.txt`
- Create: `software/tests/__init__.py` (empty)

- [ ] **Step 1: Install pytest into the venv**

Run: `. software/.venv/bin/activate && pip install pytest`
Expected: pytest installs cleanly.

- [ ] **Step 2: Update requirements.txt** — under the Core section add:

```
scikit-learn            # LFW benchmark dataset (sklearn.datasets.fetch_lfw_people)
pytest                  # unit tests (dev)
```

And under the dlib backend note, replace the `pip install face_recognition` line with:

```
# Option B — dlib ResNet-128 (used directly; not the face_recognition wrapper)
#   pip install dlib   (needs cmake + a C++ compiler)
#   Model files into ./models/: shape_predictor_5_face_landmarks.dat (-> sp5.dat)
#   and dlib_face_recognition_resnet_model_v1.dat (-> dlib_resnet.dat), from http://dlib.net/files/
```

- [ ] **Step 3: Create empty `software/tests/__init__.py`**

- [ ] **Step 4: Commit**

```bash
git add software/requirements.txt software/tests/__init__.py
git commit -m "test: add pytest harness and update requirements for LFW + dlib"
```

---

## Task 1: dlib backend uses dlib directly

**Why:** `face_recognition`'s model package is only on a blocked GitHub repo. Plain `dlib` works and its model `.dat` files are already in `software/models/`. Switch the dlib backend to call dlib directly.

**Files:**
- Modify: `software/face_eval.py` (constants near top; `_select_backend`, `_init_backend`, `detect`, `embed`)
- Test: `software/tests/test_dlib_backend.py`

- [ ] **Step 1: Write the failing test**

```python
# software/tests/test_dlib_backend.py
import os, cv2, numpy as np
from skimage import data
from face_eval import FaceEvaluator
from ir_simulator import apply_ir_disruption

def test_dlib_backend_enrolls_and_matches_clean_face():
    ev = FaceEvaluator(backend="dlib")
    assert ev.backend == "dlib"
    bgr = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)
    ref = ev.enroll(bgr)
    assert ref is not None and len(ref) == 128
    clean = ev.evaluate(apply_ir_disruption(bgr, intensity=0.0), ref)
    assert clean["detected"] and clean["recognized"]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd software && . .venv/bin/activate && python -m pytest tests/test_dlib_backend.py -q`
Expected: FAIL (current dlib backend imports `face_recognition`, which errors on missing models).

- [ ] **Step 3: Implement dlib-direct backend** in `software/face_eval.py`.

Add model paths near the existing `YUNET`/`SFACE` constants:

```python
DLIB_SP   = os.path.join(MODELS_DIR, "sp5.dat")
DLIB_REC  = os.path.join(MODELS_DIR, "dlib_resnet.dat")
```

In `_select_backend`, replace the `import face_recognition` probe with a dlib-models probe:

```python
        if os.path.exists(DLIB_SP) and os.path.exists(DLIB_REC):
            try:
                import dlib  # noqa
                return "dlib"
            except Exception:
                pass
        return "haar"
```

In `_init_backend`, replace the dlib branch body:

```python
        elif self.backend == "dlib":
            import dlib
            self._dlib = dlib
            self._dlib_det = dlib.get_frontal_face_detector()
            self._dlib_sp  = dlib.shape_predictor(DLIB_SP)
            self._dlib_rec = dlib.face_recognition_model_v1(DLIB_REC)
```

In `detect`, replace the dlib branch:

```python
        elif self.backend == "dlib":
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            for d in self._dlib_det(rgb, 1):
                results.append({"box": (d.left(), d.top(),
                                        d.right() - d.left(), d.bottom() - d.top()),
                                "conf": 1.0, "raw": d, "_rgb": rgb})
```

In `embed`, replace the dlib branch:

```python
        elif self.backend == "dlib":
            rgb = det.get("_rgb", cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            shape = self._dlib_sp(rgb, det["raw"])
            return np.array(self._dlib_rec.compute_face_descriptor(rgb, shape))
```

(The dlib threshold of `0.6` L2 in `__init__` stays correct for the ResNet-128 embeddings.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd software && . .venv/bin/activate && python -m pytest tests/test_dlib_backend.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add software/face_eval.py software/tests/test_dlib_backend.py
git commit -m "feat: use dlib directly for the dlib FR backend"
```

---

## Task 2: Wilson confidence interval (`stats.py`)

**Files:**
- Create: `software/stats.py`
- Test: `software/tests/test_stats.py`

- [ ] **Step 1: Write the failing test**

```python
# software/tests/test_stats.py
from stats import wilson_interval

def test_wilson_midpoint_and_bounds():
    lo, hi = wilson_interval(5, 10)          # 50% of 10
    assert 0.0 <= lo < 0.5 < hi <= 1.0
    assert round((lo + hi) / 2, 2) == 0.5    # symmetric at p=0.5

def test_wilson_all_success_not_one():
    lo, hi = wilson_interval(10, 10)         # 100% -> upper near 1, lower < 1
    assert hi <= 1.0 and lo < 1.0

def test_wilson_zero_n():
    assert wilson_interval(0, 0) == (0.0, 1.0)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd software && . .venv/bin/activate && python -m pytest tests/test_stats.py -q`
Expected: FAIL (`No module named 'stats'`).

- [ ] **Step 3: Implement `software/stats.py`**

```python
"""stats.py — confidence intervals for binomial proportions (success rates)."""
import math

def wilson_interval(successes, n, z=1.96):
    """95% Wilson score interval for a proportion. Returns (lo, hi) in [0,1]."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd software && . .venv/bin/activate && python -m pytest tests/test_stats.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add software/stats.py software/tests/test_stats.py
git commit -m "feat: add Wilson confidence interval helper"
```

---

## Task 3: LFW dataset loader (`dataset.py`)

**Files:**
- Create: `software/dataset.py`
- Test: `software/tests/test_dataset.py`

- [ ] **Step 1: Write the failing test**

```python
# software/tests/test_dataset.py
import numpy as np
from dataset import load_lfw_subjects
from face_eval import FaceEvaluator

def test_lfw_subjects_shape_and_disjoint():
    ev = FaceEvaluator(backend="opencv")
    subs = load_lfw_subjects(ev, n_subjects=3, per_subject=4)
    assert 1 <= len(subs) <= 3
    for s in subs:
        assert s["enroll"].dtype == np.uint8 and s["enroll"].shape[2] == 3
        assert 1 <= len(s["test"]) <= 4
        # enroll image is not byte-identical to any test image
        for t in s["test"]:
            assert not (t.shape == s["enroll"].shape and np.array_equal(t, s["enroll"]))
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd software && . .venv/bin/activate && python -m pytest tests/test_dataset.py -q`
Expected: FAIL (`No module named 'dataset'`).

- [ ] **Step 3: Implement `software/dataset.py`**

```python
"""dataset.py — load LFW faces as per-subject (clean enroll image, disjoint test images).

LFW images are RGB float [0,1] from sklearn; we convert to uint8 BGR for OpenCV/our
pipeline. For each subject we pick the first image the active backend can enroll as the
reference, and return the remaining (up to per_subject) images as the test set.
"""
import numpy as np
import cv2
from sklearn.datasets import fetch_lfw_people


def _to_bgr_uint8(img_float_rgb):
    rgb = np.clip(img_float_rgb * 255.0, 0, 255).astype(np.uint8)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def load_lfw_subjects(evaluator, n_subjects=15, per_subject=6, min_faces=20, seed=0):
    """Return a list of dicts: {name, enroll(uint8 BGR), test:[uint8 BGR,...]}.

    Only subjects whose enrollment image yields a face embedding are kept.
    """
    people = fetch_lfw_people(min_faces_per_person=min_faces, color=True,
                              resize=1.0, funneled=True)
    names = people.target_names
    rng = np.random.RandomState(seed)
    order = rng.permutation(len(names))

    subjects = []
    for ci in order:
        if len(subjects) >= n_subjects:
            break
        idxs = np.where(people.target == ci)[0]
        imgs = [_to_bgr_uint8(people.images[i]) for i in idxs]
        enroll = None
        rest = []
        for im in imgs:
            if enroll is None:
                try:
                    if evaluator.enroll(im) is not None:
                        enroll = im
                        continue
                except Exception:
                    continue
            else:
                rest.append(im)
            if len(rest) >= per_subject:
                break
        if enroll is not None and rest:
            subjects.append({"name": str(names[ci]), "enroll": enroll, "test": rest})
    return subjects
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd software && . .venv/bin/activate && python -m pytest tests/test_dataset.py -q`
Expected: PASS (LFW is cached from setup, so no re-download).

- [ ] **Step 5: Commit**

```bash
git add software/dataset.py software/tests/test_dataset.py
git commit -m "feat: add LFW per-subject loader with enroll/test split"
```

---

## Task 4: `ir_cut` parameter on the simulator

**Files:**
- Modify: `software/ir_simulator.py` (`apply_ir_disruption` signature + the three effect terms)
- Test: `software/tests/test_ir_cut.py`

- [ ] **Step 1: Write the failing test**

```python
# software/tests/test_ir_cut.py
import numpy as np, cv2
from skimage import data
from ir_simulator import apply_ir_disruption

def _mean_bright(img):
    return float(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).mean())

def test_ir_cut_attenuates_effect():
    bgr = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)
    base = _mean_bright(bgr)
    full = _mean_bright(apply_ir_disruption(bgr, intensity=0.8, ir_cut=0.0, seed=1))
    cut  = _mean_bright(apply_ir_disruption(bgr, intensity=0.8, ir_cut=1.0, seed=1))
    assert full > cut                 # IR-cut removes brightness gain
    assert abs(cut - base) < abs(full - base)

def test_ir_cut_default_unchanged():
    bgr = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)
    a = apply_ir_disruption(bgr, intensity=0.6, seed=3)
    b = apply_ir_disruption(bgr, intensity=0.6, ir_cut=0.0, seed=3)
    assert np.array_equal(a, b)       # default ir_cut=0.0 is backward-compatible
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd software && . .venv/bin/activate && python -m pytest tests/test_ir_cut.py -q`
Expected: FAIL (`apply_ir_disruption() got an unexpected keyword argument 'ir_cut'`).

- [ ] **Step 3: Implement** — change the signature and scale the effect by `(1 - ir_cut)`:

Signature:

```python
def apply_ir_disruption(img, face_box=None, intensity=0.6,
                        banding=True, seed=None, ir_cut=0.0):
```

Right after `out = img.astype(np.float32)`, add:

```python
    eff = intensity * (1.0 - float(np.clip(ir_cut, 0.0, 1.0)))   # IR-cut attenuation
```

Then replace every use of `intensity` in the effect terms (led_strength, led_radius,
wash, banding `if eff > 0`, band magnitude) with `eff`. Specifically:

```python
    led_strength = 255.0 * eff
    led_radius = 0.18 * span * (0.7 + eff)
    ...
    wash = _radial_hotspot(h, w, (cx, cy), 0.55 * span, 120.0 * eff)
    ...
    if banding and eff > 0:
        rows = np.arange(h)
        band = (np.sin(rows / 6.0 + np.random.uniform(0, 6.28)) * 0.5 + 0.5)
        band = band * (90.0 * eff)
        out += band[:, None, None]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd software && . .venv/bin/activate && python -m pytest tests/test_ir_cut.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add software/ir_simulator.py software/tests/test_ir_cut.py
git commit -m "feat: add ir_cut (IR-cut-filter/daylight) attenuation to simulator"
```

---

## Task 5: `experiment.py` dataset mode + CI bands

**Files:**
- Modify: `software/experiment.py` (`run_simulated` sibling `run_dataset`; `aggregate`; `plot_rates`; `main` args + CSV `subject` column)

- [ ] **Step 1: Add `run_dataset`** below `run_real`:

```python
def run_dataset(ev, subjects, levels):
    """Multi-subject simulated sweep. Enroll each subject's clean image, then apply
    IR disruption to each held-out test image across intensities."""
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
                             "score": r["score"] if r["score"] is not None else float("nan")})
    return rows
```

- [ ] **Step 2: Add a `subject` column everywhere.** In `run_simulated`/`run_real` rows add `"subject": "bundled"` / `"subject": sub`. Update the `csv.DictWriter` fieldnames to `["subject", "intensity", "seed", "detected", "recognized", "score"]`.

- [ ] **Step 3: Add CI to `aggregate`** — import `from stats import wilson_interval` at top, and in the per-level loop add:

```python
        n = len(sub)
        det_lo, det_hi = wilson_interval(int(np.sum([r["detected"] for r in sub])), n)
        rec_lo, rec_hi = wilson_interval(int(np.sum([r["recognized"] for r in sub])), n)
        agg[lv].update({"n": n, "det_lo": det_lo, "det_hi": det_hi,
                        "rec_lo": rec_lo, "rec_hi": rec_hi})
```

- [ ] **Step 4: Shade CI bands in `plot_rates`** — after the two `plt.plot(...)` lines:

```python
    plt.fill_between(levels, [agg[l]["det_lo"]*100 for l in levels],
                     [agg[l]["det_hi"]*100 for l in levels], alpha=0.15)
    plt.fill_between(levels, [agg[l]["rec_lo"]*100 for l in levels],
                     [agg[l]["rec_hi"]*100 for l in levels], alpha=0.15)
```

- [ ] **Step 5: Wire up `main`** — add args and branch:

```python
    ap.add_argument("--dataset", default=None, help="'lfw' for multi-subject benchmark")
    ap.add_argument("--subjects", type=int, default=15)
    ap.add_argument("--per-subject", type=int, default=6)
```

and in the data-source selection:

```python
    if args.dataset == "lfw":
        from dataset import load_lfw_subjects
        levels = [round(0.1 * i, 1) for i in range(0, 11)]
        subjects = load_lfw_subjects(ev, n_subjects=args.subjects, per_subject=args.per_subject)
        print(f"loaded {len(subjects)} LFW subjects")
        rows = run_dataset(ev, subjects, levels)
    elif args.real_dir:
        ...
```

- [ ] **Step 6: Verify end-to-end**

Run: `cd software && . .venv/bin/activate && python experiment.py --dataset lfw --subjects 12 --per-subject 5`
Expected: prints "loaded N LFW subjects" and the intensity table; writes `results.csv` (with a `subject` column, ≥10 distinct subjects) and `results_rates.png` / `results_scores.png`. The recognition rate should fall below detection rate across mid intensities.

- [ ] **Step 7: Commit**

```bash
git add software/experiment.py
git commit -m "feat: multi-subject LFW experiment mode with Wilson CI bands"
```

---

## Task 6: `compare_models.py` (multi-model + disruption threshold)

**Files:**
- Create: `software/compare_models.py`
- Test: `software/tests/test_threshold.py`

- [ ] **Step 1: Write the failing test for the threshold helper**

```python
# software/tests/test_threshold.py
from compare_models import disruption_threshold

def test_threshold_linear_interpolation():
    levels = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    rates  = [1.0, 1.0, 1.0, 0.0, 0.0, 0.0]   # crosses 0.5 between 0.4 and 0.6
    assert abs(disruption_threshold(levels, rates) - 0.5) < 1e-6

def test_threshold_none_when_never_crosses():
    assert disruption_threshold([0.0, 1.0], [1.0, 1.0]) is None
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd software && . .venv/bin/activate && python -m pytest tests/test_threshold.py -q`
Expected: FAIL (`No module named 'compare_models'`).

- [ ] **Step 3: Implement `software/compare_models.py`**

```python
"""compare_models.py — run the multi-subject sweep on each available FR backend,
overlay the recognition curves, and report each model's disruption threshold
(the IR intensity at which recognition first drops below 50%)."""
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
    plt.ylim(-5, 105); plt.grid(alpha=0.3); plt.legend(); plt.tight_layout()
    plt.savefig("model_comparison.png", dpi=140); plt.close()

    print("\nbackend | disruption threshold | subjects")
    for b, t, n in table:
        print(f"  {b:7} | {('%.2f' % t) if t else 'n/a':>20} | {n}")
    print("wrote model_comparison.png")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the unit test to verify it passes**

Run: `cd software && . .venv/bin/activate && python -m pytest tests/test_threshold.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Verify end-to-end**

Run: `cd software && . .venv/bin/activate && python compare_models.py --subjects 10 --per-subject 4`
Expected: prints a per-backend threshold table for `opencv` and `dlib`; writes `model_comparison.png` with two overlaid curves.

- [ ] **Step 6: Commit**

```bash
git add software/compare_models.py software/tests/test_threshold.py
git commit -m "feat: multi-model comparison with disruption-threshold metric"
```

---

## Task 7: `boundary.py` (intensity × IR-cut heatmap)

**Files:**
- Create: `software/boundary.py`

- [ ] **Step 1: Implement `software/boundary.py`**

```python
"""boundary.py — characterize WHERE the IR technique works. Sweeps a grid of
(IR intensity x ir_cut) and plots the mean recognition rate as a heatmap. Low ir_cut
(night / no IR-cut filter) is where disruption works; high ir_cut (daylight / IR-cut
camera) is where it fails."""
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
                    hits += int(ev.evaluate(frame, ref)["recognized"]); total += 1
            grid[yi, xi] = hits / max(total, 1)

    plt.figure(figsize=(6.8, 5.2))
    im = plt.imshow(grid * 100, origin="lower", aspect="auto", cmap="magma",
                    extent=[0, 1, 0, 1], vmin=0, vmax=100)
    plt.colorbar(im, label="Identity recognition rate (%)")
    plt.xlabel("IR disruption intensity")
    plt.ylabel("Camera IR-cut strength (0=night, 1=daylight)")
    plt.title(f"Where IR disruption works ({ev.backend} backend)")
    plt.tight_layout(); plt.savefig("boundary_heatmap.png", dpi=140); plt.close()
    print("wrote boundary_heatmap.png")
    print("corner check  inten=1,ircut=0 -> %.0f%%   inten=1,ircut=1 -> %.0f%%"
          % (grid[0, -1] * 100, grid[-1, -1] * 100))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify end-to-end**

Run: `cd software && . .venv/bin/activate && python boundary.py --subjects 8 --per-subject 3 --steps 6`
Expected: writes `boundary_heatmap.png`; corner check shows low recognition at (intensity=1, ircut=0) and high recognition at (intensity=1, ircut=1) — i.e. IR-cut rescues recognition.

- [ ] **Step 3: Commit**

```bash
git add software/boundary.py
git commit -m "feat: intensity x IR-cut boundary heatmap"
```

---

## Task 8: Report panel + docs + example outputs

**Files:**
- Create: `software/report_panel.py`
- Modify: `software/README.md`, `software/example_outputs/`

- [ ] **Step 1: Implement `software/report_panel.py`** — assemble existing PNGs into one figure:

```python
"""report_panel.py — assemble the key figures into one poster/report panel.
Run experiment.py --dataset lfw, compare_models.py, and boundary.py first."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os

PANELS = [("results_rates.png", "Detection vs recognition (95% CI)"),
          ("model_comparison.png", "Across FR models"),
          ("boundary_heatmap.png", "Where it works (intensity x IR-cut)"),
          ("ir_sim_demo.png", "Simulated IR disruption")]

present = [(f, t) for f, t in PANELS if os.path.exists(f)]
n = len(present)
fig, axes = plt.subplots(2, 2, figsize=(13, 9))
for ax, (f, t) in zip(axes.flat, present):
    ax.imshow(mpimg.imread(f)); ax.set_title(t, fontsize=11); ax.axis("off")
for ax in axes.flat[n:]:
    ax.axis("off")
fig.suptitle("IR Counter-Surveillance Glasses — DL Evaluation", fontsize=15, weight="bold")
fig.tight_layout()
fig.savefig("report_panel.png", dpi=130); print("wrote report_panel.png")
```

- [ ] **Step 2: Generate the full result set**

Run:
```bash
cd software && . .venv/bin/activate
python experiment.py --dataset lfw --subjects 15 --per-subject 6
python compare_models.py --subjects 12 --per-subject 5
python boundary.py --subjects 10 --per-subject 4 --steps 6
python ir_simulator.py
python report_panel.py
```
Expected: all five figures + `report_panel.png` produced without error.

- [ ] **Step 3: Update `software/README.md`** — add a "Multi-subject / multi-model study" subsection documenting:

```
python experiment.py --dataset lfw --subjects 15   # multi-subject curves + CI bands
python compare_models.py                           # YuNet+SFace vs dlib, disruption thresholds
python boundary.py                                 # intensity x IR-cut heatmap
python report_panel.py                             # one-figure report panel
```

and note the LFW source and that dlib models live in `models/` (downloaded, gitignored).

- [ ] **Step 4: Copy figures into `example_outputs/` and commit**

```bash
cd software
cp results.csv results_rates.png results_scores.png model_comparison.png \
   boundary_heatmap.png report_panel.png example_outputs/
cd .. && git add software/report_panel.py software/README.md software/example_outputs/
git commit -m "feat: report panel, multi-subject/model/boundary docs and example outputs"
```

---

## Task 9: Full test sweep + push

- [ ] **Step 1: Run the whole test suite**

Run: `cd software && . .venv/bin/activate && python -m pytest tests/ -q`
Expected: all tests pass (dlib backend, stats, dataset, ir_cut, threshold).

- [ ] **Step 2: Confirm the default single-face path still works (regression)**

Run: `cd software && . .venv/bin/activate && python experiment.py --backend opencv`
Expected: still produces results from the bundled face — `ir_cut` defaults preserve old behavior.

- [ ] **Step 3: Push to GitHub** (use the provided PAT)

```bash
git -c credential.helper= push "https://Omarkamsi:<PAT>@github.com/Omarkamsi/ir-glasses.git" HEAD:main
```
Expected: all task commits land on `main`.

---

## Self-Review notes

- **Spec coverage:** rigor → Tasks 3,5; breadth → Tasks 1,6; boundary → Tasks 4,7; report → Task 8. All four spec pieces covered.
- **Type consistency:** `run_dataset`/`aggregate` row dict keys (`subject,intensity,seed,detected,recognized,score`) are consistent across experiment.py, compare_models.py, boundary.py. `load_lfw_subjects(evaluator, ...)` signature matches all callers. `disruption_threshold(levels, rates)` matches its test and caller.
- **Backward compatibility:** `ir_cut` defaults to 0.0 (Task 4 test asserts byte-identical output); CSV gains a leading `subject` column (consumers read by name, not index).
