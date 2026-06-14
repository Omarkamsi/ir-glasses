# IR Counter-Surveillance Glasses — Software Suite

The complete software half of the project: a deep-learning face-recognition test harness, an
IR-disruption simulator, a camera detector, an experiment runner that produces your report
figures, and a presentation demo. Everything runs today on a sample face; you swap in your own
face and real captured frames as the hardware comes online.

## What's inside

| File | Purpose |
|------|---------|
| `face_eval.py`     | The DL "adversary": detects a face, embeds it, and decides if the enrolled identity is matched. Pluggable backend. |
| `ir_simulator.py`  | Synthesises the glasses' IR effect (glare, wash-out, rolling-shutter banding) so you can test before the hardware exists. |
| `camera_detect.py` | Detects cameras aimed at the wearer via IR retroreflection (lens glint) — the "smart trigger" feature. |
| `experiment.py`    | Sweeps IR intensity, runs the pipeline, writes `results.csv` and two figures. Your core results. |
| `demo.py`          | Presentation demo: camera-detection + glasses-OFF vs glasses-ON, in one image or live on a webcam. |

## Install

```bash
pip install -r requirements.txt
```

That alone runs the whole suite using a built-in fallback detector (the Haar backend), which is
enough to validate everything. For real, publication-quality numbers, enable one DL backend:

### Backend A — OpenCV YuNet + SFace (recommended)

Download the two CNN models into `models/`:

```bash
mkdir -p models && cd models
curl -L -o face_detection_yunet_2023mar.onnx \
  https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
curl -L -o face_recognition_sface_2021dec.onnx \
  https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx
```

The pipeline auto-detects them and switches to the `opencv` backend.

### Backend B — dlib / face_recognition

```bash
pip install face_recognition
```

Auto-detected as the `dlib` backend (128-D ResNet embeddings, 0.6 match threshold).

> The code picks the best available backend automatically; force one with `--backend opencv|dlib|haar`.

## Usage

```bash
# 1) See the IR effect on a face
python ir_simulator.py            # -> ir_sim_demo.png

# 2) Sanity-check the recognition pipeline
python face_eval.py

# 3) Test the camera detector
python camera_detect.py           # -> camera_detect_demo.png

# 4) Run the full experiment -> CSV + report figures
python experiment.py --seeds 12              # simulated, bundled face
python experiment.py --image you.jpg         # simulated, your own face
python experiment.py --real-dir captures/    # REAL captured frames

# 5) Presentation demo
python demo.py                    # -> demo_panel.png (headless, works anywhere)
python demo.py --webcam           # live, needs a camera + display
```

## Multi-subject / multi-model study (defensible results)

The single-face run above is a quick sanity check. For report-grade results, evaluate
across many subjects and models. The faces come from **LFW** (Labeled Faces in the Wild),
auto-downloaded by scikit-learn — a standard, citable FR benchmark, no personal data
needed. Each subject is enrolled on one clean image and tested on disjoint held-out images.

```bash
# multi-subject curves with 95% confidence bands (recognition collapses before detection)
python experiment.py --dataset lfw --subjects 15 --per-subject 6   # -> results_rates.png

# same sweep across two FR models (YuNet+SFace vs dlib ResNet-128) with a
# "disruption threshold" (intensity where recognition drops below 50%) per model
python compare_models.py                                           # -> model_comparison.png

# WHERE it works: recognition rate over (IR intensity x camera IR-cut strength).
# Low IR-cut (night) = technique works; high IR-cut (daylight) = technique fails.
python boundary.py                                                 # -> boundary_heatmap.png

# assemble the above into one poster/report figure
python report_panel.py                                             # -> report_panel.png
```

The dlib backend is used **directly** (not via the `face_recognition` wrapper). Drop its
two model files into `models/` (see `requirements.txt`): `sp5.dat` (5-point shape
predictor) and `dlib_resnet.dat` (ResNet-128), both from <http://dlib.net/files/>. Model
files are gitignored.

## From simulation to real hardware

Before the glasses work, `experiment.py` and `demo.py` use `ir_simulator` to model the effect.
Once they work, capture frames of yourself wearing the glasses at several power levels and lay
them out as:

```
captures/
  0.0/  img1.jpg img2.jpg ...     # glasses off (control)
  0.3/  ...
  0.6/  ...
  1.0/  ...
```

then run `python experiment.py --real-dir captures/`. The metrics and figures are identical —
only the data source changes. That side-by-side (simulated vs measured) is strong report content.

## Notes for the report

- **Recognition fails before detection.** Watch the two curves in `results_rates.png`: identity
  matching collapses at a lower IR intensity than face detection does. Worth discussing.
- **Backend matters.** The Haar fallback is coarse; YuNet+SFace or dlib give smoother, stronger
  curves and are what you should cite. Run the experiment on at least one real DL backend.
- **The honest limitation.** Many cameras enable an IR-cut filter in daylight, so the real-world
  effect is strongest at night / against IR-illuminated or no-IR-cut cameras. Measure where that
  boundary falls with your hardware — that boundary *is* a headline result.
- **Camera detection** here uses IR retroreflection (lens glint), which pairs naturally with your
  IR emitter. A trained-CNN detector is sketched as an optional route in `camera_detect.py`.
```
