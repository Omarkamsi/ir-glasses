"""schematic.py — generate a readable wiring schematic and frame-layout figure.

Block-style schematic (clear nets + labels rather than full EDA symbols) plus a front-view
of the glasses frame showing LED placement and where each board mounts. Run to produce
schematic.png for the build guide / report.

    python schematic.py            # -> schematic.png
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch


def _box(ax, x, y, w, h, label, fc="#eef3fb", ec="#34508c"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                linewidth=1.6, edgecolor=ec, facecolor=fc))
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=9)


def _wire(ax, p0, p1, label=None, color="#333", lw=1.6):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-", linewidth=lw, color=color))
    if label:
        ax.text((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + 0.12, label,
                ha="center", va="bottom", fontsize=7.5, color="#1a3a6b")


def draw_schematic(ax):
    ax.set_title("Circuit (low-side MOSFET LED driver)", fontsize=11, weight="bold")
    # Blocks
    _box(ax, 0.3, 5.2, 1.8, 0.9, "LiPo 3.7 V\n1S + protection", fc="#fdeee6", ec="#b5651d")
    _box(ax, 0.3, 3.9, 1.8, 0.8, "TP4056\nUSB-C charger", fc="#fdeee6", ec="#b5651d")
    _box(ax, 0.3, 6.5, 1.2, 0.6, "SLIDE SW", fc="#f3f3f3", ec="#555")
    _box(ax, 3.0, 5.2, 2.2, 1.4, "ESP32-C3\nGPIO4=PWM  GPIO9=BTN\nGPIO3=VBAT  5V/GND")
    _box(ax, 3.4, 3.2, 1.4, 0.9, "N-MOSFET\nG  D  S", fc="#e7f6ec", ec="#2e7d4f")
    _box(ax, 6.3, 5.0, 2.4, 1.7, "IR LED ARRAY\nN x (22 Ohm + LED)\nanodes -> rail\ncathodes -> drain",
         fc="#fdeaea", ec="#b03a3a")
    _box(ax, 6.3, 3.4, 1.5, 0.7, "470 uF\nbulk cap", fc="#f0f0fb", ec="#5a4b9c")
    _box(ax, 3.4, 2.0, 1.2, 0.6, "10k\ngate pull-down", fc="#f3f3f3", ec="#555")
    _box(ax, 0.3, 2.0, 1.6, 0.7, "button\nGPIO9-GND", fc="#f3f3f3", ec="#555")

    # Wires (nets)
    _wire(ax, (1.2, 6.5), (1.2, 6.1))                       # switch -> battery +
    _wire(ax, (2.1, 5.65), (3.0, 5.7), "3.7V")              # batt -> ESP 5V
    _wire(ax, (2.1, 5.9), (6.3, 6.2), "LED rail +")         # batt -> LED rail
    _wire(ax, (5.2, 5.6), (6.0, 5.6))                       # (spacer to array region)
    _wire(ax, (4.1, 5.2), (4.1, 4.1), "GPIO4 -> GATE")      # ESP GPIO4 -> MOSFET gate
    _wire(ax, (4.1, 3.2), (4.1, 2.6), "gate")               # gate -> pulldown
    _wire(ax, (4.8, 3.65), (6.3, 4.2), "drain<-cathodes")   # MOSFET drain <- LED cathodes
    _wire(ax, (4.1, 3.2), (4.1, 2.9))                       # source side hint
    _wire(ax, (3.4, 3.4), (2.4, 2.7), "source->GND")        # MOSFET source -> GND
    _wire(ax, (1.1, 3.9), (1.1, 3.0))                       # TP4056 -> batt (charge)
    _wire(ax, (6.3, 5.4), (7.0, 4.1), "cap across rail")    # cap to rail/gnd
    _wire(ax, (1.9, 2.3), (3.0, 5.5), "GPIO9")              # button -> ESP

    ax.text(4.4, 1.4, "All grounds common.  LEDs aimed OUTWARD, away from eyes.",
            ha="center", fontsize=8, style="italic", color="#444")
    ax.set_xlim(0, 9); ax.set_ylim(1.0, 7.4); ax.axis("off")


def draw_frame(ax):
    ax.set_title("Frame layout (front view) — LEDs face outward", fontsize=11, weight="bold")
    # lenses
    for cx in (3.3, 6.7):
        ax.add_patch(Circle((cx, 4.2), 1.25, fill=False, lw=2.2, edgecolor="#333"))
    # bridge + temples
    ax.plot([4.55, 5.45], [4.5, 4.5], color="#333", lw=2.2)
    ax.plot([2.05, 0.6], [4.6, 5.1], color="#333", lw=2.2)
    ax.plot([7.95, 9.4], [4.6, 5.1], color="#333", lw=2.2)
    # LED positions: 2 per brow + 1 bridge (scale to N as needed)
    leds = [(2.6, 5.25), (3.9, 5.3), (5.0, 5.05), (6.1, 5.3), (7.4, 5.25)]
    for x, y in leds:
        ax.add_patch(Circle((x, y), 0.16, facecolor="#d33", edgecolor="#7a1010", lw=1.2))
    ax.text(5.0, 6.0, "IR LEDs along brow + bridge", ha="center", fontsize=8.5, color="#b03a3a")
    # mounted boards on temples
    ax.text(0.9, 5.45, "ESP32-C3\n+ MOSFET\nboard", ha="center", va="center", fontsize=7.5,
            bbox=dict(boxstyle="round", fc="#eef3fb", ec="#34508c"))
    ax.text(9.1, 5.45, "LiPo +\nTP4056", ha="center", va="center", fontsize=7.5,
            bbox=dict(boxstyle="round", fc="#fdeee6", ec="#b5651d"))
    ax.text(5.0, 2.4, "Thin enamelled wire routed inside the frame arms.",
            ha="center", fontsize=8, style="italic", color="#444")
    ax.set_xlim(0, 10); ax.set_ylim(2.0, 6.4); ax.set_aspect("equal"); ax.axis("off")


def main():
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    draw_schematic(axes[0])
    draw_frame(axes[1])
    fig.suptitle("IR Counter-Surveillance Glasses — Hardware", fontsize=14, weight="bold")
    fig.tight_layout()
    fig.savefig("schematic.png", dpi=140)
    print("wrote schematic.png")


if __name__ == "__main__":
    main()
