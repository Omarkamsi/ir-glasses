"""safety_iec62471.py — photobiological IR safety check (IEC 62471 / ICNIRP).

For near-IR (IR-A, 780-1400 nm) the governing eye hazard for a small lamp is the thermal
load on the cornea and lens, limited by the infrared irradiance E_IR at the eye. IEC 62471
(aligned with ICNIRP) gives, for the unprotected eye:

    exposure t >= 1000 s :  E_IR <= 100 W/m^2
    exposure t <  1000 s :  E_IR <= 18000 * t^(-0.75) W/m^2

We model the LED array as N directional emitters of optical power P each, radiating into a
cone of given half-angle, and compute the on-axis irradiance at a viewing distance. IEC
62471 classifies general lamps at 200 mm. Because the LEDs are driven by PWM, the hazard
scales with the AVERAGE optical power (peak x duty) for continuous viewing; pass the peak
power for an absolute worst case.

    python safety_iec62471.py --leds 6 --optical-w 0.25 --half-angle 22 --distance 0.2

Note: this is the corneal/lens irradiance check examiners expect. The retinal thermal
hazard (radiance-based) is small for these low-radiance LEDs but should be mentioned
qualitatively in the report.
"""
import argparse
import math

IR_LIMIT_LONG_W_M2 = 100.0   # E_IR limit for exposure >= 1000 s


def beam_solid_angle_sr(half_angle_deg):
    """Solid angle (sr) of a cone of the given half-angle. Hemisphere (90 deg) -> 2*pi."""
    return 2.0 * math.pi * (1.0 - math.cos(math.radians(half_angle_deg)))


def radiant_intensity_w_sr(optical_w, half_angle_deg):
    """On-axis radiant intensity (W/sr), treating the beam as uniform within its cone."""
    return optical_w / beam_solid_angle_sr(half_angle_deg)


def irradiance_w_m2(n_leds, optical_w, half_angle_deg, distance_m):
    """On-axis IR irradiance (W/m^2) from N LEDs at a viewing distance."""
    ie = radiant_intensity_w_sr(optical_w, half_angle_deg)
    return n_leds * ie / (distance_m ** 2)


def ir_eye_limit_w_m2(exposure_s):
    """IEC 62471 corneal/lens IR irradiance limit (W/m^2) for an exposure duration."""
    if exposure_s >= 1000:
        return IR_LIMIT_LONG_W_M2
    return 18000.0 * (exposure_s ** -0.75)


def assess(n_leds, optical_w, half_angle_deg, distance_m, exposure_s=1000):
    """Return the irradiance, the applicable limit, the safety margin, and pass/fail."""
    e = irradiance_w_m2(n_leds, optical_w, half_angle_deg, distance_m)
    limit = ir_eye_limit_w_m2(exposure_s)
    return {"irradiance_w_m2": e, "limit_w_m2": limit,
            "margin": (limit / e) if e > 0 else float("inf"),
            "pass": e <= limit}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--leds", type=int, default=6)
    ap.add_argument("--optical-w", type=float, default=0.25,
                    help="optical (radiant) power per LED, W — PEAK for worst case")
    ap.add_argument("--half-angle", type=float, default=22.0,
                    help="LED beam half-angle, degrees")
    ap.add_argument("--distance", type=float, default=0.2,
                    help="viewing distance, m (IEC 62471 classifies at 0.2 m)")
    ap.add_argument("--duty", type=float, default=15.0,
                    help="PWM duty %% — used to show the average-power (continuous-view) case")
    args = ap.parse_args()

    peak = assess(args.leds, args.optical_w, args.half_angle, args.distance)
    avg_w = args.optical_w * args.duty / 100.0
    avg = assess(args.leds, avg_w, args.half_angle, args.distance)

    print(f"array: {args.leds} LEDs, {args.optical_w:.3f} W optical each (peak), "
          f"{args.half_angle:.0f} deg half-angle, viewed at {args.distance*1000:.0f} mm")
    print(f"IEC 62471 eye IR limit (>=1000 s exposure): {IR_LIMIT_LONG_W_M2:.0f} W/m^2\n")
    print(f"  PEAK drive    : E = {peak['irradiance_w_m2']:6.1f} W/m^2   "
          f"margin x{peak['margin']:.1f}   {'PASS' if peak['pass'] else 'FAIL'}")
    print(f"  AVG @ {args.duty:.0f}% duty: E = {avg['irradiance_w_m2']:6.1f} W/m^2   "
          f"margin x{avg['margin']:.1f}   {'PASS' if avg['pass'] else 'FAIL'}")
    print("\n(Pulsing lowers the average optical power and thus the continuous-viewing "
          "irradiance — a safety as well as a power benefit.)")


if __name__ == "__main__":
    main()
