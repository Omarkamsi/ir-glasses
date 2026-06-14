"""
ir_simulator.py
---------------
Synthesises the effect of the active IR-emitter glasses on a captured image so you can
validate the whole evaluation pipeline BEFORE the hardware is built, and so you have a
controllable "intensity" knob for plotting accuracy-vs-disruption curves.

Once the real glasses exist, you stop using this and feed real captured frames into
face_eval.py instead. The metrics code is identical either way.

Model of the physical effect (what the glasses do to a camera):
  1. Bright IR hotspots where the LEDs sit (brow / bridge), seen by the sensor as glare.
  2. Local over-exposure / wash-out of the face region (sensor saturation).
  3. Rolling-shutter banding from the pulsed LEDs (horizontal bright stripes).

All three scale with `intensity` in [0, 1].
"""

import numpy as np
import cv2


def _radial_hotspot(h, w, center, radius, strength):
    """A soft circular glare blob centred at `center`."""
    yy, xx = np.ogrid[:h, :w]
    d2 = (xx - center[0]) ** 2 + (yy - center[1]) ** 2
    blob = np.exp(-d2 / (2.0 * radius ** 2))
    return (blob * strength).astype(np.float32)


def apply_ir_disruption(img, face_box=None, intensity=0.6,
                        banding=True, seed=None):
    """
    Apply synthetic IR disruption to a BGR image.

    img       : HxWx3 uint8 BGR image
    face_box  : (x, y, w, h) of the face to target; if None, targets image centre
    intensity : 0..1 strength of the effect
    banding   : add rolling-shutter style horizontal bands
    returns   : disrupted uint8 BGR image
    """
    if seed is not None:
        np.random.seed(seed)

    h, w = img.shape[:2]
    out = img.astype(np.float32)

    # Where to put the LED hotspots
    if face_box is not None:
        x, y, fw, fh = face_box
        cx, cy = x + fw // 2, y + fh // 2
        span = max(fw, fh)
    else:
        cx, cy = w // 2, h // 2
        span = min(h, w) // 2

    # 1) Two LED hotspots around the brow + one at the bridge
    glare = np.zeros((h, w), np.float32)
    led_strength = 255.0 * intensity
    led_radius = 0.18 * span * (0.7 + intensity)
    offsets = [(-0.22, -0.15), (0.22, -0.15), (0.0, 0.0)]
    for dx, dy in offsets:
        glare += _radial_hotspot(h, w, (cx + dx * span, cy + dy * span),
                                 led_radius, led_strength)

    # 2) Broad wash-out over the whole face ROI (sensor saturation)
    wash = _radial_hotspot(h, w, (cx, cy), 0.55 * span, 120.0 * intensity)
    glare += wash

    out += glare[..., None]

    # 3) Rolling-shutter banding: horizontal sinusoidal brightness ripple
    if banding and intensity > 0:
        rows = np.arange(h)
        band = (np.sin(rows / 6.0 + np.random.uniform(0, 6.28)) * 0.5 + 0.5)
        band = band * (90.0 * intensity)
        out += band[:, None, None]

    return np.clip(out, 0, 255).astype(np.uint8)


def sweep_intensities(img, face_box=None, levels=None, seed=0):
    """Return a dict {intensity: disrupted_image} for a sweep, for experiments."""
    if levels is None:
        levels = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    return {lv: apply_ir_disruption(img, face_box, intensity=lv, seed=seed)
            for lv in levels}


if __name__ == "__main__":
    # Self-test on the bundled astronaut face (a real human face).
    from skimage import data
    rgb = data.astronaut()
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    strip = []
    for lv in [0.0, 0.3, 0.6, 1.0]:
        d = apply_ir_disruption(bgr, intensity=lv, seed=1)
        cv2.putText(d, f"I={lv}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.9, (0, 255, 0), 2)
        strip.append(d)
    cv2.imwrite("ir_sim_demo.png", np.hstack(strip))
    print("wrote ir_sim_demo.png", np.hstack(strip).shape)
