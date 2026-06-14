"""download_models.py — fetch every model file the suite can use into ./models/.

One command sets up the OpenCV (YuNet + SFace) and dlib (ResNet-128 + shape predictor)
backends so the experiments are fully reproducible. Idempotent: existing files are kept.
Uses only the standard library (urllib + bz2), so it runs before any pip install.

    python download_models.py
"""
import os
import bz2
import urllib.request

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

# (destination filename, url, is_bz2_compressed)
FILES = [
    ("face_detection_yunet_2023mar.onnx",
     "https://github.com/opencv/opencv_zoo/raw/main/models/"
     "face_detection_yunet/face_detection_yunet_2023mar.onnx", False),
    ("face_recognition_sface_2021dec.onnx",
     "https://github.com/opencv/opencv_zoo/raw/main/models/"
     "face_recognition_sface/face_recognition_sface_2021dec.onnx", False),
    ("sp5.dat",
     "http://dlib.net/files/shape_predictor_5_face_landmarks.dat.bz2", True),
    ("dlib_resnet.dat",
     "http://dlib.net/files/dlib_face_recognition_resnet_model_v1.dat.bz2", True),
]


def fetch(dest, url, is_bz2):
    path = os.path.join(MODELS_DIR, dest)
    if os.path.exists(path):
        print(f"  [skip] {dest} already present")
        return
    print(f"  [get ] {dest} <- {url}")
    raw = urllib.request.urlopen(url).read()
    if is_bz2:
        raw = bz2.decompress(raw)
    with open(path, "wb") as f:
        f.write(raw)
    print(f"  [ok  ] {dest} ({len(raw)} bytes)")


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    print(f"downloading models into {MODELS_DIR}")
    for dest, url, is_bz2 in FILES:
        fetch(dest, url, is_bz2)
    print("done.")


if __name__ == "__main__":
    main()
