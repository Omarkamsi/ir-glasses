"""
face_eval.py
------------
The DL "adversary" you measure against. Given an image, it answers:
  - Was a face DETECTED?               (detection stage of any FR system)
  - Was the enrolled identity MATCHED? (recognition stage)
  - How far is the face embedding from the enrolled reference?

This is the instrument for your experiment: run clean vs IR-disrupted frames through it
and record how detection / recognition degrade.

Backends (auto-selected, best first):
  * "opencv" : YuNet detector + SFace recogniser (ONNX). Put the two .onnx files in ./models/
               (download links in README). Small, fast, modern CNNs.
  * "dlib"   : the `face_recognition` library (dlib ResNet, 128-D). `pip install face_recognition`.
  * "haar"   : OpenCV Haar cascade for detection + a coarse grayscale embedding. Fallback only,
               so the pipeline still runs with zero downloads; not for final results.

All backends expose the same API, so the rest of your code never changes.
"""

import os
import numpy as np
import cv2

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
YUNET = os.path.join(MODELS_DIR, "face_detection_yunet_2023mar.onnx")
SFACE = os.path.join(MODELS_DIR, "face_recognition_sface_2021dec.onnx")


class FaceEvaluator:
    def __init__(self, backend="auto", recog_threshold=None):
        self.backend = self._select_backend(backend)
        self._init_backend()
        # sensible per-backend match thresholds
        if recog_threshold is not None:
            self.recog_threshold = recog_threshold
        elif self.backend == "opencv":
            self.recog_threshold = 0.363      # SFace cosine match threshold (OpenCV default)
        elif self.backend == "dlib":
            self.recog_threshold = 0.6        # face_recognition default L2 threshold
        else:
            self.recog_threshold = 0.55       # haar fallback (cosine on coarse vector)
        print(f"[FaceEvaluator] backend = {self.backend}, threshold = {self.recog_threshold}")

    # ---------- backend selection ----------
    def _select_backend(self, backend):
        if backend != "auto":
            return backend
        if os.path.exists(YUNET) and os.path.exists(SFACE) and hasattr(cv2, "FaceDetectorYN"):
            return "opencv"
        try:
            import face_recognition  # noqa
            return "dlib"
        except Exception:
            return "haar"

    def _init_backend(self):
        if self.backend == "opencv":
            self.detector = cv2.FaceDetectorYN.create(YUNET, "", (320, 320),
                                                      score_threshold=0.6)
            self.recognizer = cv2.FaceRecognizerSF.create(SFACE, "")
        elif self.backend == "dlib":
            import face_recognition
            self._fr = face_recognition
        else:  # haar
            cascade = os.path.join(cv2.data.haarcascades,
                                   "haarcascade_frontalface_default.xml")
            self.detector = cv2.CascadeClassifier(cascade)

    # ---------- detection ----------
    def detect(self, img):
        """Return list of dicts: {box:(x,y,w,h), conf:float, raw:<backend-specific>}."""
        h, w = img.shape[:2]
        results = []
        if self.backend == "opencv":
            self.detector.setInputSize((w, h))
            _, faces = self.detector.detect(img)
            if faces is not None:
                for f in faces:
                    x, y, bw, bh = f[:4].astype(int)
                    results.append({"box": (x, y, bw, bh), "conf": float(f[-1]), "raw": f})
        elif self.backend == "dlib":
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            locs = self._fr.face_locations(rgb)  # (top, right, bottom, left)
            for (t, r, b, l) in locs:
                results.append({"box": (l, t, r - l, b - t), "conf": 1.0,
                                "raw": (t, r, b, l), "_rgb": rgb})
        else:  # haar
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            boxes = self.detector.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
            for (x, y, bw, bh) in boxes:
                results.append({"box": (int(x), int(y), int(bw), int(bh)),
                                "conf": 1.0, "raw": None})
        # largest face first
        results.sort(key=lambda d: d["box"][2] * d["box"][3], reverse=True)
        return results

    # ---------- embedding ----------
    def embed(self, img, det):
        """Return an embedding vector for the detected face, or None."""
        if self.backend == "opencv":
            aligned = self.recognizer.alignCrop(img, det["raw"])
            feat = self.recognizer.feature(aligned)
            return np.asarray(feat).flatten()
        elif self.backend == "dlib":
            rgb = det.get("_rgb", cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            encs = self._fr.face_encodings(rgb, known_face_locations=[det["raw"]])
            return encs[0] if encs else None
        else:  # haar: coarse normalised grayscale vector
            x, y, w, h = det["box"]
            crop = img[max(0, y):y + h, max(0, x):x + w]
            if crop.size == 0:
                return None
            g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            g = cv2.resize(g, (32, 32)).astype(np.float32).flatten()
            g = (g - g.mean()) / (g.std() + 1e-6)
            return g

    # ---------- similarity / matching ----------
    def _is_match(self, ref, emb):
        """Return (matched: bool, score: float) where score is a backend-native distance."""
        if self.backend == "opencv":
            cos = float(np.dot(ref, emb) / (np.linalg.norm(ref) * np.linalg.norm(emb)))
            return cos >= self.recog_threshold, cos       # higher = more similar
        elif self.backend == "dlib":
            dist = float(np.linalg.norm(ref - emb))
            return dist <= self.recog_threshold, dist      # lower = more similar
        else:
            cos = float(np.dot(ref, emb) / (np.linalg.norm(ref) * np.linalg.norm(emb)))
            return cos >= self.recog_threshold, cos

    # ---------- high-level helpers ----------
    def enroll(self, img):
        """Compute the reference embedding for the identity to protect (clean image)."""
        dets = self.detect(img)
        if not dets:
            raise RuntimeError("enroll: no face found in reference image")
        emb = self.embed(img, dets[0])
        if emb is None:
            raise RuntimeError("enroll: could not embed reference face")
        return emb

    def evaluate(self, img, reference_emb):
        """
        Run the full pipeline on one frame.
        Returns dict with detection + recognition outcome and the raw score.
        """
        dets = self.detect(img)
        out = {"detected": len(dets) > 0,
               "n_faces": len(dets),
               "det_conf": dets[0]["conf"] if dets else 0.0,
               "recognized": False,
               "score": None}
        if not dets:
            return out
        emb = self.embed(img, dets[0])
        if emb is None:
            return out
        matched, score = self._is_match(reference_emb, emb)
        out["recognized"] = bool(matched)
        out["score"] = float(score)
        return out


if __name__ == "__main__":
    from skimage import data
    from ir_simulator import apply_ir_disruption

    bgr = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)
    ev = FaceEvaluator()
    ref = ev.enroll(bgr)
    print("enrolled reference embedding, dim =", len(ref))

    for lv in [0.0, 0.3, 0.6, 0.9]:
        d = apply_ir_disruption(bgr, intensity=lv, seed=1)
        r = ev.evaluate(d, ref)
        print(f"intensity {lv:>3}: detected={r['detected']}  "
              f"recognized={r['recognized']}  score={r['score']}")
