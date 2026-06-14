# Project Summary — IR Counter-Surveillance Glasses

A senior design project (Computer Engineering): a wearable that emits modulated infrared
light to disrupt non-consensual facial recognition, paired with a deep-learning evaluation
framework that **quantifies when and how well** the disruption actually defeats a
face-recognition (FR) system. The novelty is not the gadget — IR-LED attacks are known —
but the hypothesis-driven, statistically defensible **measurement** of where the technique
works and where it fails.

**Repo:** https://github.com/Omarkamsi/ir-glasses · CI: tests run on every push.

---

## Headline findings

1. **Recognition fails before detection.** Identity recognition collapses at a *lower* IR
   intensity than face detection does — recognition is the more fragile stage. Demonstrated
   across **15 LFW subjects** with two FR models, with 95% confidence bands.
2. **Model-independent.** YuNet+SFace (CNN) and dlib (ResNet-128) reach the disruption
   threshold within 0.01 of each other (~0.50 intensity), so the effect isn't model-specific.
3. **The real-world boundary.** A 2-D sweep of (IR intensity × camera IR-cut strength) shows
   the technique fully defeats recognition at night / against no-IR-cut cameras (0%), but a
   daylight IR-cut filter rescues recognition (~85%). This boundary *is* a headline result.
4. **The smart trigger works.** The lens-glint camera detector hits precision 1.00 / recall
   0.97 over 120 synthetic scenes.

Key figure: `software/example_outputs/report_panel.png` (assembles all of the above).

---

## Repository structure

```
.
├── README.md                  Project overview + CI badge
├── PROJECT_SUMMARY.md         This file
├── .github/workflows/tests.yml  CI: runs the test suite on push/PR
├── docs/
│   ├── Senior_Project_Proposal.docx
│   ├── IR_Glasses_Build_Guide.md      Hardware build walkthrough
│   ├── Parts_List.md                  Ready-to-buy shopping checklist (~$47)
│   ├── Data_Capture_Protocol.md       Bridge: real glasses → --real-dir pipeline
│   └── superpowers/                   Design spec + implementation plan
├── firmware/
│   └── ir_glasses_firmware.ino   ESP32-C3: PWM IR driver, serial control, batt monitor
├── hardware/
│   ├── power_budget.py            Battery/runtime calculator (tested)
│   ├── safety_iec62471.py         IR eye-safety worked example (tested)
│   ├── schematic.py → schematic.png  Circuit + frame-layout figure
│   └── tests/                     8 unit tests
└── software/
    ├── face_eval.py              FR "adversary": detect + embed + match (opencv/dlib/haar)
    ├── ir_simulator.py           Synthetic IR effect, gamma-calibrated, with ir_cut axis
    ├── dataset.py                LFW loader: per-subject clean-enroll + disjoint test split
    ├── stats.py                  Wilson CI + baseline correction
    ├── experiment.py             Multi-subject sweep → results.csv + rate/score figures
    ├── compare_models.py         Multi-model overlay + disruption threshold
    ├── boundary.py               intensity × IR-cut recognition heatmap
    ├── camera_detect.py          Lens-glint detector + precision/recall evaluation
    ├── demo.py / report_panel.py Presentation outputs
    ├── download_models.py        One-command model fetch (stdlib, idempotent)
    ├── tests/                    14 unit tests
    └── example_outputs/          Committed result figures + results.csv
```

---

## Software / DL — complete

The measurement instrument and the study around it.

- **Pluggable FR backend** (`face_eval.py`): OpenCV YuNet+SFace, dlib ResNet-128 (used
  directly), or a Haar fallback — one API throughout.
- **IR simulator** (`ir_simulator.py`): models glare, wash-out and rolling-shutter banding;
  a **gamma=2.0** intensity calibration spreads the disruption transition across the full
  axis, and an **`ir_cut`** parameter models the daylight / IR-cut-filter condition.
- **Statistical rigor**: evaluates across LFW subjects, enrolling on a clean image and
  testing on disjoint images, with Wilson 95% confidence bands and a baseline-corrected
  recognition curve (isolates disruption from the recogniser's own error).
- **Reproducible**: `pip install -r software/requirements.txt && python download_models.py`;
  14 unit tests; CI runs the logic/simulator/calibration/camera tests on every push.

Run it:
```bash
cd software && pip install -r requirements.txt && python download_models.py
python experiment.py --dataset lfw --subjects 15    # curves + CI bands
python compare_models.py                            # two FR models + thresholds
python boundary.py                                  # intensity × IR-cut heatmap
python report_panel.py                              # one-figure report panel
```

---

## Hardware — fully specified, build-ready (parts not yet ordered)

- **Firmware** (`ir_glasses_firmware.ino`): drives the IR array via hardware PWM through a
  low-side logic-level MOSFET. Compiles on ESP32 Arduino core **2.x and 3.x**. A **serial
  command interface** (`I`/`F`/`M`/`S`/`H`) sets a numeric intensity that maps 1:1 onto the
  capture pipeline (`I60` → `captures/0.6/`). Battery low-voltage warning + force-OFF cutoff.
- **Calculators**: `power_budget.py` (runtime vs configuration) and `safety_iec62471.py`
  (corneal/lens IR irradiance vs the 100 W/m² limit — ~8× margin in pulsed operation).
- **Docs**: build guide, ~$47 parts checklist, and a capture protocol that feeds real frames
  straight into `experiment.py --real-dir captures/` — identical metrics, real data.

---

## Status & what remains

| Phase | Status |
|-------|--------|
| Software / DL evaluation | ✅ Complete, tested, CI-protected |
| Firmware | ✅ Complete (compiles on core 2.x/3.x; not yet flashed to hardware) |
| Hardware design / docs / calcs | ✅ Complete |
| Physical build | ⏳ Pending — order parts (`docs/Parts_List.md`) |
| Real-data capture | ⏳ Pending hardware — protocol ready (`docs/Data_Capture_Protocol.md`) |

**Next step once parts arrive:** breadboard → flash → build → capture frames per the
protocol → `python software/experiment.py --real-dir captures/`. The simulated-vs-measured
comparison that follows is the strongest possible report content.

---

## Safety & ethics

Operates within IR photobiological-safety limits (IEC 62471 check included). It saturates
camera sensors and does **not** affect human vision. Intended use is consensual
self-protection against non-consensual recognition.

*Reference: Z. Zhou et al., "Invisible Mask: Practical Attacks on Face Recognition with
Infrared," arXiv:1803.04683, 2018. License: MIT.*
