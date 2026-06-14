from camera_detect import evaluate_glint_detector, _match


def test_match_counts_tp_fp_fn():
    truth = [(100, 100), (200, 200)]
    hits = [{"center": (102, 99)}, {"center": (500, 500)}]   # 1 near a lens, 1 spurious
    tp, fp, fn = _match(truth, hits, tol=12)
    assert (tp, fp, fn) == (1, 1, 1)


def test_glint_detector_metrics_reasonable():
    m = evaluate_glint_detector(n_scenes=40)
    assert m["recall"] > 0.8          # finds almost all real lens glints
    assert m["precision"] > 0.6       # the bright-window distractor is not flagged
    assert m["fp_per_scene"] < 1.0
