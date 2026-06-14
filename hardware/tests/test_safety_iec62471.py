import math
from safety_iec62471 import (beam_solid_angle_sr, irradiance_w_m2,
                             ir_eye_limit_w_m2, assess)


def test_hemisphere_solid_angle_is_two_pi():
    assert abs(beam_solid_angle_sr(90) - 2 * math.pi) < 1e-9


def test_irradiance_inverse_square():
    e1 = irradiance_w_m2(1, 0.25, 22, 0.2)
    e2 = irradiance_w_m2(1, 0.25, 22, 0.4)   # double distance -> quarter irradiance
    assert abs(e1 / e2 - 4.0) < 1e-9


def test_long_exposure_limit_is_100():
    assert ir_eye_limit_w_m2(1000) == 100.0
    assert ir_eye_limit_w_m2(5000) == 100.0
    assert ir_eye_limit_w_m2(10) > 100.0     # shorter exposure -> higher allowed


def test_assess_passes_at_low_average_power():
    # 15% duty average of a 0.25 W LED -> comfortably under the limit at 0.2 m
    r = assess(6, 0.25 * 0.15, 22, 0.2)
    assert r["pass"] and r["margin"] > 1.0
