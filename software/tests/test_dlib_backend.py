import os, importlib.util
import cv2, numpy as np
import pytest
from skimage import data
from face_eval import FaceEvaluator, DLIB_SP, DLIB_REC
from ir_simulator import apply_ir_disruption

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("dlib") is None
    or not (os.path.exists(DLIB_SP) and os.path.exists(DLIB_REC)),
    reason="dlib and/or its model files are not available")


def test_dlib_backend_enrolls_and_matches_clean_face():
    ev = FaceEvaluator(backend="dlib")
    assert ev.backend == "dlib"
    bgr = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)
    ref = ev.enroll(bgr)
    assert ref is not None and len(ref) == 128
    clean = ev.evaluate(apply_ir_disruption(bgr, intensity=0.0), ref)
    assert clean["detected"] and clean["recognized"]
