from power_budget import average_current_ma, runtime_hours, mode_table


def test_average_current_matches_build_guide_example():
    # Build guide §4: 4 LEDs @ 150 mA, 15% duty -> 90 mA LEDs + 60 mA ESP = 150 mA
    assert average_current_ma(4, 150, 15, 60) == 150.0


def test_runtime_derates_capacity():
    # 300 mAh at 80% usable, 150 mA draw -> 1.6 h
    assert abs(runtime_hours(300, 150, 0.8) - 1.6) < 1e-9


def test_runtime_infinite_when_off():
    assert runtime_hours(300, 0) == float("inf")


def test_mode_table_off_row_has_only_esp_draw():
    rows = mode_table(4, 150, 60, 300)
    off = next(r for r in rows if r["mode"] == "OFF")
    assert off["avg_ma"] == 60.0
    assert off["runtime_h"] == float("inf") if off["avg_ma"] == 0 else off["runtime_h"] > 0
