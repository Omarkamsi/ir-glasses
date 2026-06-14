"""power_budget.py — battery / runtime calculator for the IR glasses.

Pulsed LEDs draw current only during the ON part of each PWM period, so the *average*
current — what drains the battery — scales with duty cycle, not peak. This computes the
average draw and runtime for a given configuration and for each firmware preset mode, so
the report can justify the battery choice with theoretical numbers (then compare against
the multimeter measurement).

    python power_budget.py --leds 4 --peak-ma 150 --battery-mah 300
"""
import argparse

# Firmware preset modes (must match firmware/ir_glasses_firmware.ino).
# Frequency does not affect average current; duty does.
PRESET_MODES = [
    ("OFF", 0),
    ("STEADY", 70),
    ("PULSE_LOW", 15),
    ("PULSE_HIGH", 15),
]


def average_current_ma(n_leds, peak_ma, duty_pct, esp_ma):
    """Total average current (mA): n LEDs at (peak x duty) plus the ESP32 itself."""
    led_avg = n_leds * peak_ma * (duty_pct / 100.0)
    return led_avg + esp_ma


def runtime_hours(battery_mah, avg_ma, usable_fraction=0.8):
    """Runtime (h) for a battery, derating capacity by usable_fraction (protection cutoff,
    voltage sag, ageing). Returns infinity at zero average draw."""
    if avg_ma <= 0:
        return float("inf")
    return (battery_mah * usable_fraction) / avg_ma


def mode_table(n_leds, peak_ma, esp_ma, battery_mah, usable_fraction=0.8):
    """Per-preset-mode average current and runtime."""
    rows = []
    for name, duty in PRESET_MODES:
        avg = average_current_ma(n_leds, peak_ma, duty, esp_ma)
        rt = runtime_hours(battery_mah, avg, usable_fraction)
        rows.append({"mode": name, "duty_pct": duty, "avg_ma": avg, "runtime_h": rt})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--leds", type=int, default=4)
    ap.add_argument("--peak-ma", type=float, default=150.0, help="peak current per LED (mA)")
    ap.add_argument("--esp-ma", type=float, default=60.0, help="ESP32 draw, Wi-Fi off (mA)")
    ap.add_argument("--battery-mah", type=float, default=300.0)
    ap.add_argument("--usable", type=float, default=0.8, help="usable battery fraction")
    args = ap.parse_args()

    print(f"config: {args.leds} LEDs @ {args.peak_ma:.0f} mA peak, "
          f"ESP {args.esp_ma:.0f} mA, battery {args.battery_mah:.0f} mAh "
          f"(usable {args.usable*100:.0f}%)\n")
    print("mode        | duty | avg mA | runtime")
    print("------------+------+--------+---------")
    for r in mode_table(args.leds, args.peak_ma, args.esp_ma,
                        args.battery_mah, args.usable):
        rt = "  off " if r["runtime_h"] == float("inf") else f"{r['runtime_h']:.1f} h"
        print(f"{r['mode']:<11} | {r['duty_pct']:>3}% | {r['avg_ma']:>6.1f} | {rt:>6}")


if __name__ == "__main__":
    main()
