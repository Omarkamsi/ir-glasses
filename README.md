# IR Counter-Surveillance Glasses

A wearable device that emits modulated infrared light to disrupt non-consensual facial
recognition, together with a deep-learning evaluation framework that measures **when and how
well** the disruption actually defeats a face-recognition system.

Senior design project (Computer Engineering). The novelty is not the gadget — IR-LED attacks on
face recognition are known (see reference below) — but the **quantified, hypothesis-driven
evaluation** of where the technique works and where it fails.

## Repository layout

```
.
├── docs/        Project proposal + hardware build guide
├── firmware/    ESP32-C3 firmware that drives the pulsed IR-LED array
└── software/    DL evaluation pipeline, IR simulator, camera detector, experiments, demo
```

- **docs/** — the one-page proposal and the Phase-1 hardware build guide (bill of materials,
  wiring, power budget, assembly, safety).
- **firmware/** — `ir_glasses_firmware.ino`: hardware-PWM pulsing of the IR LEDs via a
  logic-level MOSFET, with mode button and battery monitoring.
- **software/** — the full Python suite. See [`software/README.md`](software/README.md) for
  install and usage. It runs today on a sample face and a built-in fallback detector; enable a
  CNN backend (YuNet+SFace or dlib) for final results, and swap the simulator for real captured
  frames as the hardware comes online.

## Quick start (software)

```bash
cd software
pip install -r requirements.txt
python experiment.py        # produces results.csv + report figures
python demo.py              # produces the presentation panel
```

## Key result

Identity **recognition** breaks down at a lower IR intensity than face **detection** does —
recognition is the more fragile stage. See `software/example_outputs/results_rates.png`.

## Honest limitation

Many cameras enable an IR-cut filter in daylight, so the effect is strongest at night, against
IR-illuminated cameras, or cameras without an IR-cut filter. Characterising that boundary with
the real hardware is itself a headline finding.

## Reference

Z. Zhou et al., "Invisible Mask: Practical Attacks on Face Recognition with Infrared,"
arXiv:1803.04683, 2018 — PWM-driven IR-LED adversarial attack on FaceNet; basis for the method.

## Safety & ethics

The device operates within infrared photobiological-safety limits (IEC 62471). It saturates
camera sensors and does **not** affect human vision. Intended use is consensual self-protection
against non-consensual recognition.

## License

MIT — see [LICENSE](LICENSE).
