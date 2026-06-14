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


def _match(truth, hits, tol):
    """Greedily match detections to ground-truth lens centres within `tol` pixels.
    Returns (true_positives, false_positives, false_negatives)."""
    used = set()
    tp = 0
    for h in hits:
        cx, cy = h["center"]
        best, best_d = None, tol
        for i, (tx, ty) in enumerate(truth):
            if i in used:
                continue
            d = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5
            if d <= best_d:
                best, best_d = i, d
        if best is not None:
            used.add(best)
            tp += 1
    fp = len(hits) - tp
    fn = len(truth) - tp
    return tp, fp, fn


def evaluate_glint_detector(n_scenes=60, tol=12, bright_thresh=210, seed0=0):
    """Quantify the lens-glint detector over many synthetic scenes with known ground
    truth. Returns precision / recall / F1 and false-positives-per-scene — the same kind
    of metrics the face-recognition pipeline reports, for the 'smart trigger' feature."""
    det = LensGlintDetector(bright_thresh=bright_thresh)
    TP = FP = FN = 0
    for k in range(n_scenes):
        n_lenses = 1 + (k % 3)                     # 1..3 lenses per scene
        scene, truth = _make_synthetic_scene(n_lenses=n_lenses, seed=seed0 + k)
        tp, fp, fn = _match(truth, det.detect(scene), tol)
        TP += tp; FP += fp; FN += fn
    prec = TP / (TP + FP) if (TP + FP) else 0.0
    rec = TP / (TP + FN) if (TP + FN) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"precision": prec, "recall": rec, "f1": f1,
            "fp_per_scene": FP / n_scenes, "n_scenes": n_scenes,
            "tp": TP, "fp": FP, "fn": FN}


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

    # ---- quantitative evaluation: precision/recall over many synthetic scenes ----
    m = evaluate_glint_detector(n_scenes=120)
    print(f"\nlens-glint detector over {m['n_scenes']} scenes: "
          f"precision={m['precision']:.2f} recall={m['recall']:.2f} "
          f"F1={m['f1']:.2f} FP/scene={m['fp_per_scene']:.2f}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    thresholds = list(range(170, 246, 5))
    precs = [evaluate_glint_detector(n_scenes=120, bright_thresh=t)["precision"]
             for t in thresholds]
    recs = [evaluate_glint_detector(n_scenes=120, bright_thresh=t)["recall"]
            for t in thresholds]
    plt.figure(figsize=(7, 4.5))
    plt.plot(thresholds, precs, "o-", label="Precision", linewidth=2)
    plt.plot(thresholds, recs, "s-", label="Recall", linewidth=2)
    plt.axvline(det.bright_thresh, color="gray", linestyle=":",
                label=f"operating point ({det.bright_thresh})")
    plt.xlabel("Brightness threshold")
    plt.ylabel("Score")
    plt.title("Lens-glint camera detector — precision/recall vs threshold")
    plt.ylim(-0.05, 1.05)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig("camera_eval.png", dpi=140)
    plt.close()
    print("wrote camera_eval.png")
