# Data-Capture Protocol — from real glasses to real results

This is the bridge between the hardware and the evaluation pipeline. Once the glasses work,
follow this to capture frames that drop **directly** into the existing analysis:

```bash
python software/experiment.py --real-dir captures/
```

The metrics, figures, and the recognition-before-detection finding are computed identically
to the simulated study — only the data source changes. A side-by-side of **simulated vs
measured** curves is strong report content.

---

## 1. The folder layout the pipeline expects

`experiment.py --real-dir DIR` reads sub-folders **named by intensity**, each holding frames
captured at that setting:

```
captures/
  0.0/   img01.jpg img02.jpg ...     # glasses OFF — the control / enrollment condition
  0.3/   ...                          # firmware intensity 30%
  0.6/   ...                          # firmware intensity 60%
  1.0/   ...                          # firmware intensity 100%
```

You may use as many intensity levels as you like (e.g. 0.0, 0.2, 0.4, 0.6, 0.8, 1.0) — more
points = smoother curves. Aim for **≥15 frames per level** so the per-level rates have
tight confidence intervals (the pipeline already computes Wilson 95% bands).

## 2. Firmware intensity → folder mapping

Drive the glasses over USB serial (115200 baud). The firmware command `I<n>` sets the PWM
duty to `n` %, which is your intensity axis:

| Folder | Firmware command | Meaning |
|--------|------------------|---------|
| `0.0/` | `M0` (or `I0`)   | LEDs off — control |
| `0.3/` | `I30`            | 30% intensity |
| `0.6/` | `I60`            | 60% intensity |
| `1.0/` | `I100`           | full intensity |

Set the pulse frequency once with `F120` (≈120 Hz gives clear rolling-shutter banding); use
`S` to confirm the state before each batch. Any serial terminal works:

```bash
#  screen /dev/ttyACM0 115200      (Linux/macOS)   — or the Arduino IDE Serial Monitor
#  then type:  F120  <enter>   I60  <enter>   S  <enter>
```

## 3. Camera setup (the "adversary")

- **Camera:** a phone **front/selfie camera** is ideal — those often lack an IR-cut filter,
  so they see the IR strongly (this is the favourable case). A laptop webcam also works.
- **Framing:** subject's face centred and filling a reasonable part of the frame, looking at
  the camera. Keep the **distance and framing constant** across all intensity levels — only
  the LED intensity should change between folders.
- **Distance:** pick one (e.g. ~1 m) and keep it fixed for the main sweep. Optionally repeat
  the sweep at a second distance as an extra variable.
- **Resolution/format:** any normal photo resolution; save as `.jpg` or `.png`.

## 4. Capture procedure (per subject)

1. **Enroll / control:** glasses **OFF** (`M0`). Capture ≥15 frames into `captures/0.0/`.
   These are also the clean reference the recogniser enrolls against.
2. For each intensity level: send the command (e.g. `I60`), confirm with `S`, then capture
   ≥15 frames into the matching folder (`captures/0.6/`). Vary your head pose slightly
   between frames (small yaw/pitch) so the set isn't identical — this mirrors how the LFW
   test images differ from the enrollment image.
3. Watch the status LED and serial log for the **low-battery warning**; recharge before the
   cell hits the cutoff so a dimming array doesn't contaminate a capture.

## 5. The day-vs-night condition (validates the boundary heatmap)

The simulator's `ir_cut` axis (`software/boundary.py`) predicts the technique works at night
and fails in daylight behind an IR-cut filter. **Measure this for real:**

- Capture **one full sweep in a dark room / at night** (IR-illuminated or no-IR-cut camera) →
  `captures_night/`. Expect recognition to collapse as intensity rises.
- Capture **one full sweep in bright daylight** → `captures_day/`. Expect the IR effect to be
  much weaker (the camera's IR-cut filter rejects it).

Run the pipeline on each (`--real-dir captures_night/` and `--real-dir captures_day/`) and
compare. The gap between the two **is** the real-world boundary — a headline result, and the
direct empirical test of the simulated heatmap.

## 6. Optional: wavelength comparison (850 vs 940 nm)

If you built both LED types, repeat one sweep per wavelength (`captures_850/`,
`captures_940/`). 850 nm should disrupt more strongly on typical sensors; quantifying that
difference is original content.

## 7. Sanity checks before you trust a dataset

- Open a `1.0/` frame: the face should be visibly washed out / banded. If it looks normal,
  the camera has an IR-cut filter — switch to the selfie camera or a darker setting.
- Confirm folder names are exactly the intensity values (`0.0`, not `0`), and that `0.0/`
  contains clean faces (the enrollment depends on it).
- Run `python software/experiment.py --real-dir captures/` and check the printed table:
  recognition should fall before detection, as in the simulation.

---

*Related: firmware serial interface in [`../firmware/ir_glasses_firmware.ino`](../firmware/ir_glasses_firmware.ino);
simulated counterparts in `software/experiment.py` and `software/boundary.py`.*
