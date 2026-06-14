import cv2
from skimage import data
from ir_simulator import apply_ir_disruption, INTENSITY_GAMMA


def _mean_bright(img):
    return float(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).mean())


def test_intensity_response_is_gamma_not_linear():
    """The calibrated intensity knob has a >1 gamma response: the mid-intensity effect
    is well below half the full-intensity effect, which spreads the disruption transition
    across the intensity axis instead of collapsing it early."""
    assert INTENSITY_GAMMA > 1.0
    bgr = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)
    base = _mean_bright(bgr)
    half = _mean_bright(apply_ir_disruption(bgr, intensity=0.5, seed=1)) - base
    full = _mean_bright(apply_ir_disruption(bgr, intensity=1.0, seed=1)) - base
    assert full > 0
    assert half / full < 0.4          # quadratic-ish, clearly below the linear 0.5
