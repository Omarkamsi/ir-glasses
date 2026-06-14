"""
demo.py
-------
Ties the whole system together for your presentation.

It tells the story in one frame:
  TOP   : the glasses' own view -> lens-glint camera detection -> "IR ACTIVATED"
  LEFT  : what a surveillance camera sees with the glasses OFF  -> identity matched
  RIGHT : what the same camera sees with the glasses ON (IR)    -> match defeated

Modes:
  python demo.py                      # headless: writes demo_panel.png (works anywhere)
  python demo.py --image me.jpg       # use your own enrolled face
  python demo.py --webcam             # live: needs a camera + a display

In --webcam mode the IR "on" view is synthesised with ir_simulator so you can present the
defence convincingly before / without the physical glasses. Once the hardware works, point a
real camera at yourself with the glasses on and the RIGHT panel becomes a real capture.
"""

import argparse
import numpy as np
import cv2

from face_eval import FaceEvaluator
from ir_simulator import apply_ir_disruption
from camera_detect import LensGlintDetector, _make_synthetic_scene


def label(img, text, color=(255, 255, 255), y=28):
    cv2.rectangle(img, (0, 0), (img.shape[1], y + 10), (0, 0, 0), -1)
    cv2.putText(img, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return img


def surveillance_view(ev, ref_emb, frame, title):
    """Annotate a frame as a surveillance camera + FR system would see it."""
    view = frame.copy()
    r = ev.evaluate(view, ref_emb)
    dets = ev.detect(view)
    for d in dets:
        x, y, w, h = d["box"]
        cv2.rectangle(view, (x, y), (x + w, y + h), (0, 200, 0), 2)
    if not r["detected"]:
        status, col = "NO FACE DETECTED", (0, 0, 255)
    elif r["recognized"]:
        status, col = f"IDENTIFIED  (score {r['score']:.2f})", (0, 200, 0)
    else:
        status, col = f"UNRECOGNISED  (score {r['score']:.2f})", (0, 165, 255)
    h = view.shape[0]
    cv2.rectangle(view, (0, h - 34), (view.shape[1], h), (0, 0, 0), -1)
    cv2.putText(view, status, (8, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)
    return label(view, title)


def build_panel(ev, ref_emb, face_frame, glint_det, glint_scene=None,
                ir_intensity=0.9):
    """Compose the full 3-part demo image."""
    H = face_frame.shape[0]

    # bottom-left: glasses OFF
    off = surveillance_view(ev, ref_emb, face_frame, "Surveillance cam - glasses OFF")
    # bottom-right: glasses ON (IR)
    on_frame = apply_ir_disruption(face_frame, intensity=ir_intensity, seed=2)
    on = surveillance_view(ev, ref_emb, on_frame, "Surveillance cam - glasses ON (IR)")
    bottom = np.hstack([off, on])

    # top: camera-detection view
    if glint_scene is None:
        glint_scene, _ = _make_synthetic_scene(h=H // 2, w=bottom.shape[1], seed=3)
    hits = glint_det.detect(glint_scene)
    top = glint_det.annotate(glint_scene, hits)
    trig = f"Cameras detected: {len(hits)}  ->  " + ("IR ACTIVATED" if hits else "idle")
    top = label(top, trig, color=(0, 0, 255) if hits else (200, 200, 200))
    top = cv2.resize(top, (bottom.shape[1], H // 2))

    return np.vstack([top, bottom])


def run_headless(args):
    ev = FaceEvaluator(backend=args.backend)
    if args.image:
        ref_img = cv2.imread(args.image)
    else:
        from skimage import data
        ref_img = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)
    ref_emb = ev.enroll(ref_img)
    panel = build_panel(ev, ref_emb, ref_img, LensGlintDetector())
    cv2.imwrite("demo_panel.png", panel)
    print("wrote demo_panel.png", panel.shape)


def run_webcam(args):
    ev = FaceEvaluator(backend=args.backend)
    glint = LensGlintDetector()
    cap = cv2.VideoCapture(0)
    print("Webcam demo. Enroll: look at the camera and press 'e'. Quit: 'q'.")
    ref_emb = None
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if ref_emb is not None:
            panel = build_panel(ev, ref_emb, frame, glint, glint_scene=frame.copy())
            cv2.imshow("IR Glasses Demo", panel)
        else:
            cv2.imshow("IR Glasses Demo", label(frame.copy(),
                       "Press 'e' to enroll your face"))
        k = cv2.waitKey(1) & 0xFF
        if k == ord("e"):
            try:
                ref_emb = ev.enroll(frame)
                print("enrolled.")
            except Exception as ex:
                print("enroll failed:", ex)
        elif k == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=None)
    ap.add_argument("--webcam", action="store_true")
    ap.add_argument("--backend", default="auto")
    args = ap.parse_args()
    run_webcam(args) if args.webcam else run_headless(args)
