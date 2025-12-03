import os
import cv2
import mediapipe as mp
import numpy as np
from pathlib import Path
from tqdm import tqdm

# ================================
# CONFIG
# ================================
SRC_ROOT = Path("archive")           # your raw dataset
DST_ROOT = Path("archive_clean")     # cleaned/cropped dataset

IMG_SIZE = 224

MIN_FACE_SIZE = 60

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

# ================================
# Functions
# ================================
def safe_crop(img, box):
    x1, y1, x2, y2 = box
    h, w = img.shape[:2]

    x1 = max(0, min(w, x1))
    x2 = max(0, min(w, x2))
    y1 = max(0, min(h, y1))
    y2 = max(0, min(h, y2))

    if x2 <= x1 or y2 <= y1:
        return None
    return img[y1:y2, x1:x2]


def crop_face_mediapipe(image):
    """Returns cropped face or None if no face detected."""
    h, w = image.shape[:2]
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    if not results.multi_face_landmarks:
        return None

    pts = np.array([[int(l.x * w), int(l.y * h)]
                    for l in results.multi_face_landmarks[0].landmark])

    x_min, y_min = np.min(pts, axis=0)
    x_max, y_max = np.max(pts, axis=0)

    box_w = x_max - x_min
    box_h = y_max - y_min
    cx = x_min + box_w // 2
    cy = y_min + box_h // 2

    max_dim = max(box_w, box_h)
    pad = int(max_dim * 0.2)
    size = max_dim + pad

    x1 = cx - size // 2
    y1 = cy - size // 2
    x2 = cx + size // 2
    y2 = cy + size // 2

    cropped = safe_crop(image, (x1, y1, x2, y2))
    return cropped


def process_split(split):
    """Process train/test folders."""
    src_dir = SRC_ROOT / split
    dst_dir = DST_ROOT / split
    dst_dir.mkdir(parents=True, exist_ok=True)

    class_dirs = [d for d in src_dir.iterdir() if d.is_dir()]

    for cls in class_dirs:
        out_cls = dst_dir / cls.name
        out_cls.mkdir(parents=True, exist_ok=True)

        images = list(cls.glob("*"))

        print(f"\n📂 Class: {cls.name} ({split}) — {len(images)} images")

        for img_path in tqdm(images, desc=f"Processing {cls.name}"):
            try:
                img = cv2.imread(str(img_path))
                if img is None:
                    continue

                cropped = crop_face_mediapipe(img)
                if cropped is None:
                    continue   # skip images with no face

                cropped = cv2.resize(cropped, (IMG_SIZE, IMG_SIZE))
                cv2.imwrite(str(out_cls / img_path.name), cropped)

            except Exception as e:
                print("Error:", e)
                continue


# ================================
# MAIN
# ================================
print("🚀 Starting AffectNet cleaning + face cropping...")

process_split("train")
process_split("test")

print("\n🎉 Cleaning complete!")
print("➡ New clean dataset saved to: cleaned_dataset/")
