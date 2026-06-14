import numpy as np, cv2
from skimage import data
from ir_simulator import apply_ir_disruption


def _mean_bright(img):
    return float(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).mean())


def test_ir_cut_attenuates_effect():
    bgr = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)
    base = _mean_bright(bgr)
    full = _mean_bright(apply_ir_disruption(bgr, intensity=0.8, ir_cut=0.0, seed=1))
    cut = _mean_bright(apply_ir_disruption(bgr, intensity=0.8, ir_cut=1.0, seed=1))
    assert full > cut                 # IR-cut removes brightness gain
    assert abs(cut - base) < abs(full - base)


def test_ir_cut_default_unchanged():
    bgr = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)
    a = apply_ir_disruption(bgr, intensity=0.6, seed=3)
    b = apply_ir_disruption(bgr, intensity=0.6, ir_cut=0.0, seed=3)
    assert np.array_equal(a, b)       # default ir_cut=0.0 is backward-compatible
