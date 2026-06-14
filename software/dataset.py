"""dataset.py — load LFW faces as per-subject (clean enroll image, disjoint test images).

LFW images are RGB float [0, 1] from scikit-learn; we convert to uint8 BGR for OpenCV and
the rest of the pipeline. For each subject we pick the first image the active backend can
enroll as the reference, and return the remaining (up to per_subject) images as the test
set. Enroll and test images are disjoint, so we never test on the enrolled frame.
"""
import numpy as np
import cv2
from sklearn.datasets import fetch_lfw_people


def _to_bgr_uint8(img_float_rgb):
    rgb = np.clip(img_float_rgb * 255.0, 0, 255).astype(np.uint8)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def load_lfw_subjects(evaluator, n_subjects=15, per_subject=6, min_faces=20, seed=0):
    """Return a list of dicts: {name, enroll(uint8 BGR), test:[uint8 BGR, ...]}.

    Only subjects whose enrollment image yields a face embedding under `evaluator` are
    kept, so the reference is always valid for the active backend.
    """
    people = fetch_lfw_people(min_faces_per_person=min_faces, color=True,
                              resize=1.0, funneled=True)
    names = people.target_names
    rng = np.random.RandomState(seed)
    order = rng.permutation(len(names))

    subjects = []
    for ci in order:
        if len(subjects) >= n_subjects:
            break
        idxs = np.where(people.target == ci)[0]
        imgs = [_to_bgr_uint8(people.images[i]) for i in idxs]
        enroll = None
        rest = []
        for im in imgs:
            if enroll is None:
                try:
                    if evaluator.enroll(im) is not None:
                        enroll = im
                        continue
                except Exception:
                    continue
            else:
                rest.append(im)
            if len(rest) >= per_subject:
                break
        if enroll is not None and rest:
            subjects.append({"name": str(names[ci]), "enroll": enroll, "test": rest})
    return subjects
