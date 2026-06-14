# Parts List — IR Counter-Surveillance Glasses

A ready-to-buy shopping checklist. Quantities include sensible **spares** (you *will* kill an
LED or MOSFET). Prices are rough 2026 USD for ordering from AliExpress + a local Amman
electronics shop; treat the total as an estimate, not a quote.

> **Order the AliExpress items on day one.** Shipping to Jordan is typically 2–4 weeks —
> a big chunk of a 6-week project. Everything marked **[local]** you can usually get
> same-week.

## A. Order first (long lead time — AliExpress)

| ✅ | Item | What to search / spec | Qty | ~Unit | ~Line |
|----|------|-----------------------|-----|-------|-------|
| ☐ | ESP32-C3 SuperMini | "ESP32-C3 SuperMini" dev board, USB-C | **2** (1 spare) | $4 | $8 |
| ☐ | IR LEDs 850 nm, high-power | "850nm high power IR LED", 1–3 W emitter or 5 mm ≥100 mA, Vf 1.4–1.6 V | **10** | $0.6 | $6 |
| ☐ | IR LEDs 940 nm (optional) | for the wavelength-comparison experiment | **5** | $0.6 | $3 |
| ☐ | AO3400 N-MOSFET (SMD) | "AO3400 SOT-23", logic-level — final wearable | **5** | $0.1 | $0.5 |
| ☐ | IRLZ44N N-MOSFET (TO-220) | logic-level, easy on a breadboard — prototyping | **3** | $0.5 | $1.5 |
| ☐ | LiPo battery 1S | 3.7 V, 150–500 mAh, **with built-in protection** (drone-size) | **2** | $4 | $8 |
| ☐ | TP4056 charger module | "TP4056 with protection, USB-C" | **2** | $0.8 | $1.6 |

**Subtotal A ≈ $28**

## B. Local / same-week (Amman electronics or hobby shop)

| ✅ | Item | Spec | Qty | ~Unit | ~Line |
|----|------|------|-----|-------|-------|
| ☐ | Current-limit resistors | ~22 Ω, 1/2 W (one per LED branch) | **10** | $0.05 | $0.5 |
| ☐ | Gate pull-down resistor | 10 kΩ | **5** | $0.02 | $0.1 |
| ☐ | Battery-sense divider | 2 × 100 kΩ (for `GPIO3` VBAT monitor) | **4** | $0.02 | $0.1 |
| ☐ | Bulk capacitor | 220–470 µF, ≥6.3 V electrolytic | **3** | $0.1 | $0.3 |
| ☐ | Tactile push button | momentary (mode toggle) | **3** | $0.1 | $0.3 |
| ☐ | Slide switch | main power on/off | **2** | $0.2 | $0.4 |
| ☐ | Glasses frame | thick plastic frame (cheap / an old pair) | **1** | $5 | $5 |
| ☐ | Breadboard + jumpers | half-size breadboard, M-M jumpers | **1** | $4 | $4 |
| ☐ | Protoboard | small perfboard for the soldered build | **2** | $0.5 | $1 |
| ☐ | Thin enamelled (magnet) wire | for routing inside the frame arms | 1 roll | $2 | $2 |
| ☐ | Build supplies | solder, heat-shrink, hot glue, Kapton tape | — | — | $5 |

**Subtotal B ≈ $19**

## C. Tools you must already have / borrow

| ✅ | Tool | Why |
|----|------|-----|
| ☐ | **Multimeter** | measure LED branch current — **not optional** |
| ☐ | Soldering iron + tip | assembly |
| ☐ | Wire cutters / strippers | assembly |
| ☐ | **Smartphone** | its camera is your IR detector + capture device |
| ☐ | USB-C cable | flashing the ESP32, charging |

## Estimated total: **≈ $47** (+ shipping)

## Notes & substitutions

- **LED choice drives everything.** High-power 1–3 W 850 nm emitters give the strongest
  camera disruption but run hot — keep duty low (the firmware's PULSE modes). 5 mm ≥100 mA
  LEDs are gentler and easier to start with. Buy a few of each if unsure.
- **850 vs 940 nm.** 850 nm shows a faint red glow and is *more* visible to most camera
  sensors (stronger effect); 940 nm is fully invisible but weaker. The optional 940 nm LEDs
  let you make that trade-off a measured result in your report.
- **MOSFET must be logic-level** (fully on at 3.3 V gate). AO3400 and IRLZ44N both qualify;
  a standard IRF540 does **not** — don't substitute it.
- **Battery sizing:** run `python hardware/power_budget.py --leds <N> --peak-ma <I>` to pick
  capacity for your target runtime. 300 mAh ≈ 1.5–2 h in the pulsed modes.
- **Safety:** before finalizing LED count/power, run `python hardware/safety_iec62471.py`
  to confirm the eye-irradiance margin (see also Build Guide §7).

*Cross-reference: the original BOM with circuit context is in
[`IR_Glasses_Build_Guide.md`](IR_Glasses_Build_Guide.md) §1.*
