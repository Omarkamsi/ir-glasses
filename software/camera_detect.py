"""
camera_detect.py
----------------
Detects cameras pointed at the wearer so the glasses can fire the IR array only when
needed (saving battery + staying inconspicuous). This is the "smart trigger" stretch goal.

Primary method: IR RETROREFLECTION ("lens glint").
A camera lens retroreflects light straight back to the source. Since these glasses already
emit IR, a small companion camera sees any lens aimed at the wearer as a tiny, very bright,
round hotspot - exactly how commercial hidden-camera finders work. This pairs perfectly with
the project theme and needs no trained model, so it is robust and fully testable.

Optional method (hook only): a custom-trained CNN/YOLO "surveillance camera" detector. That
needs you to collect + label data and train a model; a stub is provided for where it plugs in.
"""

import numpy as np
import cv2


class LensGlintDetector:
    """Find candidate camera lenses as small, bright, round retroreflections."""

    def __init__(self, bright_thresh=210, min_area=3, max_area=600,
                 min_circularity=0.55):
        self.bright_thresh = bright_thresh
        self.min_area = min_area
        self.max_area = max_area
        self.min_circularity = min_circularity

    def detect(self, frame):
        """Return list of dicts {center:(x,y), radius, area, circularity, brightness}."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        # Isolate the brightest pinpoints (no opening: lens glints can be only a few px)
        _, mask = cv2.threshold(gray, self.bright_thresh, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        hits = []
        for c in contours:
            area = cv2.contourArea(c)
            if not (self.min_area <= area <= self.max_area):
                continue
            perim = cv2.arcLength(c, True)
            if perim == 0:
                continue
            circularity = 4 * np.pi * area / (perim * perim)   # 1.0 = perfect circle
            if circularity < self.min_circularity:
                continue
            (x, y), r = cv2.minEnclosingCircle(c)
            mcoords = np.zeros(gray.shape, np.uint8)
            cv2.drawContours(mcoords, [c], -1, 255, -1)
            brightness = float(cv2.mean(gray, mask=mcoords)[0])
            hits.append({"center": (int(x), int(y)), "radius": float(r),
                         "area": float(area), "circularity": float(circularity),
                         "brightness": brightness})
        hits.sort(key=lambda h: h["brightness"], reverse=True)
        return hits

    def annotate(self, frame, hits):
        out = frame.copy()
        for h in hits:
            cv2.circle(out, h["center"], max(8, int(h["radius"] * 3)),
                       (0, 0, 255), 2)
            cv2.putText(out, "lens?", (h["center"][0] + 8, h["center"][1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        return out


def cnn_camera_detector_stub(frame):
    """
    Placeholder for an optional trained 'surveillance camera' detector.
    Train a small YOLO/MobileNet on labelled camera images, load it here, and return
    boxes. Not required for the core project; the glint detector above is the deliverable.
    """
    raise NotImplementedError("Plug a trained model in here if you pursue the CNN route.")


def _make_synthetic_scene(h=360, w=640, n_lenses=2, seed=0):
    """A dark room with a couple of bright retroreflective lens glints + distractors."""
    rng = np.random.default_rng(seed)
    img = (rng.normal(35, 8, (h, w, 3))).clip(0, 80).astype(np.uint8)  # dim background
    truth = []
    for _ in range(n_lenses):
        cx, cy = int(rng.integers(60, w - 60)), int(rng.integers(60, h - 60))
        cv2.circle(img, (cx, cy), int(rng.integers(3, 6)), (255, 255, 255), -1)
        truth.append((cx, cy))
    img = cv2.GaussianBlur(img, (0, 0), 0.8)            # mild lens blur, applied once
    # a large bright distractor (e.g. a window) that should NOT be flagged as a lens
    cv2.rectangle(img, (w - 120, 20), (w - 30, 110), (240, 240, 240), -1)
    return img, truth


if __name__ == "__main__":
    det = LensGlintDetector()
    scene, truth = _make_synthetic_scene(seed=3)
    hits = det.detect(scene)
    print(f"ground-truth lenses: {truth}")
    print(f"detected {len(hits)} candidate(s):")
    for h in hits:
        print(f"   center={h['center']} area={h['area']:.0f} "
              f"circ={h['circularity']:.2f} bright={h['brightness']:.0f}")
    cv2.imwrite("camera_detect_demo.png", det.annotate(scene, hits))
    print("wrote camera_detect_demo.png")
