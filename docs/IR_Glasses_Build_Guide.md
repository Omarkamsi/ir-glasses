# IR Counter-Surveillance Glasses — Build Guide (Phase 1: Hardware + Firmware)

This covers everything needed for **Weeks 1–3** of the plan: source parts, breadboard a single-LED
proof-of-concept, scale to the full array, and integrate into the frame. The evaluation pipeline
(Weeks 4–6) is a separate document.

---

## 1. Bill of Materials

Order the AliExpress items **on day one** — shipping to Jordan is typically 2–4 weeks, which is a big
chunk of your 6-week window. Common passives, the frame, wire, and tools you can usually get same-week
from a local electronics/hobby shop in Amman.

| # | Item | Spec / what to search | Qty | ~Unit (USD) | Source |
|---|------|-----------------------|-----|-------------|--------|
| 1 | **ESP32-C3 SuperMini** | dev board, 3.3 V, built-in USB | 1 (buy 2) | 3–5 | AliExpress |
| 2 | **High-power IR LEDs, 850 nm** | "850nm high power IR LED" (1–3 W emitter, or 5 mm ≥100 mA). Vf ≈ 1.4–1.6 V | 6 | 0.3–1.0 | AliExpress / local |
| 3 | IR LEDs, 940 nm (optional) | for your wavelength comparison experiment | 3 | 0.3–1.0 | AliExpress |
| 4 | **Logic-level N-MOSFET** | **AO3400** (SOT-23, for the final wearable) **and** **IRLZ44N** (TO-220, easy on a breadboard) | 2–3 each | 0.2–0.6 | AliExpress / local |
| 5 | **LiPo battery** | 3.7 V 1S, 150–500 mAh, *with built-in protection* (drone-size) | 1 | 3–6 | local / AliExpress |
| 6 | **TP4056 charger module** | search "TP4056 with protection, USB-C" | 1 | 0.5–1.0 | AliExpress / local |
| 7 | Current-limit resistors | ~22 Ω, 1/2 W (one per LED branch) | 6 | cents | local |
| 8 | Gate pull-down resistor | 10 kΩ | 1 | cents | local |
| 9 | Battery-sense divider | 2 × 100 kΩ (optional, for voltage monitoring) | 2 | cents | local |
| 10 | **Bulk capacitor** | 220–470 µF, ≥6.3 V electrolytic | 2 | cents | local |
| 11 | Push button | tactile momentary (mode toggle) | 2 | cents | local |
| 12 | Slide switch | main power on/off | 1 | cents | local |
| 13 | Glasses frame | thick plastic frame (cheap, or an old pair) | 1 | 2–10 | optician / local |
| 14 | Wire + build supplies | thin enameled/magnet wire, small protoboard, heat-shrink, solder, hot glue | — | — | local |

**Tools you must have:** soldering iron, **multimeter** (you'll measure LED current — not optional),
wire cutters/strippers, and a smartphone (its camera is your IR detector).

---

## 2. How the circuit works (one paragraph for your report)

The ESP32 generates a hardware PWM signal on one GPIO that drives the **gate** of a logic-level
N-channel MOSFET. The MOSFET sits on the **low side**: it switches the common cathode of the LED array
to ground. Each LED's anode connects through its own current-limiting resistor to the battery's positive
rail, so the LEDs sit in parallel branches. A **bulk capacitor** across the battery rail near the LEDs
supplies the fast current spikes during each pulse (the battery alone can't respond quickly enough). A
**10 kΩ pull-down** on the gate guarantees the LEDs stay off while the ESP32 boots. Driving the LEDs with
a **low duty cycle at high frequency** lets you push high *peak* current for very short bursts — high peak
IR brightness to the camera, low *average* current so nothing overheats. This pulsed overdrive is also
what produces the rolling-shutter banding that corrupts the captured frame.

---

## 3. Wiring

### Connection table

| From | To | Notes |
|------|----|-------|
| LiPo + (via slide switch) | LED rail (+) and ESP32 `5V`/`VIN` pin | raw 3.7 V powers LEDs and the board |
| LiPo − | common ground | tie everything to one ground |
| LED rail (+) | each LED anode → 22 Ω resistor | one resistor per LED |
| each LED cathode | MOSFET **drain** | all cathodes join at the drain node |
| MOSFET **source** | ground | low-side switch |
| MOSFET **gate** | ESP32 `GPIO4` (PWM) | the control signal |
| MOSFET gate | ground via **10 kΩ** | pull-down (keep-off at boot) |
| 220–470 µF cap | across LED rail (+) and ground | observe polarity; place near LEDs |
| Push button | ESP32 `GPIO9` ↔ ground | uses internal pull-up |
| Battery divider mid-point | ESP32 `GPIO3` (ADC) | optional 100k/100k from LiPo+ to GND |
| TP4056 B+ / B− | LiPo + / − | charge the cell through this module |

### Simplified schematic

```
   LiPo+ ──[SW]──┬───────────────┬──────────────┐
                 │               │              │
              [ESP32 5V]     [+ 470µF]      [22Ω]×N
                 │               │              │
              GPIO4 ───┐        GND         (N × IR LED)
                       │                        │ (cathodes)
                    [GATE]                       │
              ┌────────┴───────┐                 │
              │   N-MOSFET     │  DRAIN ─────────┘
   GPIO4 ──┬──┤ (AO3400 /      │
           │  │  IRLZ44N)      │  SOURCE ── GND
        [10kΩ]└────────────────┘
           │
          GND
```

(N = number of LEDs, start with 1 for the proof-of-concept, then scale to 4.)

---

## 4. Power budget (justify your battery + runtime in the report)

Worked example with 4 LEDs at 150 mA peak, 15 % duty:

- Average current per LED ≈ 150 mA × 0.15 ≈ **22.5 mA**
- Four LEDs ≈ **90 mA**
- ESP32-C3 with Wi-Fi off ≈ **40–80 mA**
- **Total average ≈ 130–170 mA**

A 300 mAh LiPo → roughly **1.5–2 hours** of runtime. Measure your real numbers with the multimeter and
put the comparison (theoretical vs measured) in your report — that's easy, credible engineering content.

---

## 5. Assembly — do it in this order

1. **One LED on a breadboard.** ESP32 + IRLZ44N + one IR LED + resistor + 10 kΩ + cap. Flash the
   firmware, confirm it pulses (see §6). Do **not** move on until this works — it's the hardest 10 %.
2. **Measure current.** Put the multimeter in series with the LED branch; confirm it matches your
   resistor math. Adjust the resistor if needed.
3. **Scale to 4 LEDs** in parallel branches. Re-check total current and that the MOSFET stays cool.
4. **Move to protoboard** and solder the stable circuit; swap the TO-220 MOSFET for the SMD AO3400 if
   you're tight on space.
5. **Integrate into the frame.** Drill small holes along the brow/bridge, push the LEDs through facing
   outward, glue them, and route the thin enameled wire inside the frame arms. Mount the ESP32, MOSFET
   board, TP4056, and LiPo on/behind the arms.

---

## 6. Test & verification

- **IR is invisible to you but not to a camera.** Point a phone camera (front "selfie" cameras usually
  lack an IR-cut filter and work best) at the LEDs while the firmware runs — you should see them flashing
  bright white/purple on screen. That's your proof they're emitting.
- **Banding test.** Record a short video of the running LEDs; at the PULSE modes you should see horizontal
  bands sweep across the frame. Capture these — they're figures for your report.
- **Thermal check.** After a minute, the LEDs and MOSFET should be warm at most, not hot. If hot, lower
  the duty cycle or raise the resistor value.

---

## 7. Safety (keep this section in your report too)

- Infrared is **invisible**, so your eyes' blink/aversion reflex won't protect against a bright source.
  Keep average current modest, never stare into the array at close range, and always aim the LEDs
  **outward**, away from the wearer and bystanders' eyes.
- Reference **IEC 62471** (photobiological safety of lamps) in your report and do a back-of-envelope
  irradiance check for your final LED count — examiners value that you considered it.
- Be clear in your writeup: the device **saturates a camera sensor**; it does **not** harm human vision.
- Thermal: verify the LEDs/MOSFET don't overheat during extended runs.

---

*Next document (Weeks 4–6): the Python face-detection/recognition evaluation pipeline — captures frames,
runs them through the DL models, and produces your recognition-accuracy-vs-IR-parameter graphs.*
