import os, importlib.util
import numpy as np
import pytest
from face_eval import FaceEvaluator, YUNET, SFACE

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("sklearn") is None
    or not (os.path.exists(YUNET) and os.path.exists(SFACE)),
    reason="scikit-learn or the OpenCV model files are not available")

from dataset import load_lfw_subjects


def test_lfw_subjects_shape_and_disjoint():
    ev = FaceEvaluator(backend="opencv")
    subs = load_lfw_subjects(ev, n_subjects=3, per_subject=4)
    assert 1 <= len(subs) <= 3
    for s in subs:
        assert s["enroll"].dtype == np.uint8 and s["enroll"].shape[2] == 3
        assert 1 <= len(s["test"]) <= 4
        # enroll image is not byte-identical to any test image
        for t in s["test"]:
            assert not (t.shape == s["enroll"].shape and np.array_equal(t, s["enroll"]))
