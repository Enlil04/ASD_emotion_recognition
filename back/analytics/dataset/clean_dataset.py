import os
import shutil
from pathlib import Path
from tqdm import tqdm

# ================================
# CONFIGURATION
# ================================
BASE_DIR = Path(__file__).resolve().parent
SRC_ROOT = BASE_DIR / "archive"       # Where folders 1, 2, 3... are
DST_ROOT = BASE_DIR / "archive_clean" # Where happy, sad... will go

# RAF-DB Standard Emotion Mapping
# 1: Surprise, 2: Fear, 3: Disgust, 4: Happy, 5: Sad, 6: Angry, 7: Neutral
EMOTION_MAP = {
    "1": "surprise",
    "2": "fear",
    "3": "disgust",
    "4": "happy",
    "5": "sad",
    "6": "angry",
    "7": "neutral"
}

def reorganize_folders():
    print(f"🚀 Starting Reorganization...")
    print(f"📂 Reading from: {SRC_ROOT}")

    if not SRC_ROOT.exists():
        print(f"❌ Error: Source folder not found at {SRC_ROOT}")
        return

    # Process both 'train' and 'test' folders
    for split in ["train", "test"]:
        src_split = SRC_ROOT / split
        dst_split = DST_ROOT / split
        
        if not src_split.exists():
            print(f"⚠️ Skipping '{split}' (folder not found)")
            continue

        print(f"\n🔄 Processing {split} data...")
        
        # Look for folders "1", "2", "3"... inside "train"
        for folder_name, emotion_name in EMOTION_MAP.items():
            src_emotion_folder = src_split / folder_name
            
            if not src_emotion_folder.exists():
                # Try finding it without quotes? (unlikely for Path, but safe to check)
                continue
            
            # Create destination: archive_clean/train/surprise
            dst_emotion_folder = dst_split / emotion_name
            dst_emotion_folder.mkdir(parents=True, exist_ok=True)
            
            # Get all images
            images = list(src_emotion_folder.glob("*"))
            print(f"   Moving {len(images)} images from '{folder_name}' to '{emotion_name}'...")
            
            for img_path in tqdm(images, leave=False):
                # We COPY instead of MOVE to keep your original data safe
                shutil.copy(img_path, dst_emotion_folder / img_path.name)

    print(f"\n🎉 Success! Data is ready in: {DST_ROOT}")
    print("   You can now run 'check_data.py' and then 'train.py'.")

if __name__ == "__main__":
    reorganize_folders()
# import os
# import cv2
# import numpy as np
# from pathlib import Path
# from tqdm import tqdm

# # ================================
# # CONFIG
# # ================================
# BASE_DIR = Path(__file__).resolve().parent  # folder where this .py file lives


# SRC_ROOT = BASE_DIR / "archive"          # FER-2013 root
# DST_ROOT = BASE_DIR / "archive_clean"    # Output folder

# IMG_SIZE = 224  # MobileNet input size

# VALID_EXTS = {".jpg", ".jpeg", ".png"}


# print("📍 Script location:", Path(__file__).resolve())
# print("📂 Working directory:", Path.cwd())
# print("📁 Looking for:", SRC_ROOT)


# def process_split(split):
#     """Process train/test folders and resize images to 224x224."""
#     src_dir = SRC_ROOT / split
#     dst_dir = DST_ROOT / split

#     if not src_dir.exists():
#         print(f"⚠️ Skipping missing folder: {src_dir}")
#         return

#     dst_dir.mkdir(parents=True, exist_ok=True)

#     class_dirs = [d for d in src_dir.iterdir() if d.is_dir()]
#     if not class_dirs:
#         print(f"⚠️ No class folders found in {src_dir}")
#         return

#     for cls in class_dirs:
#         out_cls = dst_dir / cls.name
#         out_cls.mkdir(parents=True, exist_ok=True)

#         images = [p for p in cls.iterdir() if p.suffix.lower() in VALID_EXTS]
#         print(f"\n📂 {split}/{cls.name} — {len(images)} images")

#         for img_path in tqdm(images, desc=f"{cls.name}", leave=False):
#             try:
#                 # Read image
#                 img = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
#                 if img is None:
#                     continue

#                 # Handle grayscale images
#                 if img.ndim == 2:
#                     img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
#                 elif img.shape[2] == 4:  # RGBA → RGB
#                     img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

#                 # Resize
#                 img = cv2.resize(
#                     img,
#                     (IMG_SIZE, IMG_SIZE),
#                     interpolation=cv2.INTER_CUBIC
#                 )

#                 # Save as JPG
#                 save_path = out_cls / f"{img_path.stem}.jpg"
#                 cv2.imwrite(str(save_path), img)

#             except Exception as e:
#                 print(f"❌ Error processing {img_path}: {e}")


# # ================================
# # MAIN
# # ================================
# print("🚀 Starting FER-2013 preprocessing → 224x224")

# DST_ROOT.mkdir(exist_ok=True)

# if (SRC_ROOT / "train").exists():
#     process_split("train")
#     process_split("test")

# elif (SRC_ROOT / "Training").exists():
#     print("📁 Detected Kaggle-style folders")
#     process_split("Training")

#     if (SRC_ROOT / "PrivateTest").exists():
#         process_split("PrivateTest")
#     elif (SRC_ROOT / "PublicTest").exists():
#         process_split("PublicTest")

# else:
#     raise FileNotFoundError(
#         f"❌ Could not find FER-2013 folders in {SRC_ROOT}"
#     )

# print("\n🎉 Preprocessing complete! Dataset ready for MobileNet.")



# # Clean and crop AffectNet dataset using MediaPipe Face Mesh
# # import os
# # import cv2
# # import mediapipe as mp
# # import numpy as np
# # from pathlib import Path
# # from tqdm import tqdm

# # # ================================
# # # CONFIG
# # # ================================
# # SRC_ROOT = Path("archive")           # your raw dataset
# # DST_ROOT = Path("archive_clean")     # cleaned/cropped dataset

# # IMG_SIZE = 224

# # MIN_FACE_SIZE = 60

# # mp_face_mesh = mp.solutions.face_mesh
# # face_mesh = mp_face_mesh.FaceMesh(
# #     max_num_faces=1,
# #     refine_landmarks=True,
# #     min_detection_confidence=0.5,
# #     min_tracking_confidence=0.5,
# # )

# # # ================================
# # # Functions
# # # ================================
# # def safe_crop(img, box):
# #     x1, y1, x2, y2 = box
# #     h, w = img.shape[:2]

# #     x1 = max(0, min(w, x1))
# #     x2 = max(0, min(w, x2))
# #     y1 = max(0, min(h, y1))
# #     y2 = max(0, min(h, y2))

# #     if x2 <= x1 or y2 <= y1:
# #         return None
# #     return img[y1:y2, x1:x2]


# # def crop_face_mediapipe(image):
# #     """Returns cropped face or None if no face detected or face is too small."""
# #     h, w = image.shape[:2]
# #     rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
# #     results = face_mesh.process(rgb)

# #     if not results.multi_face_landmarks:
# #         return None

# #     pts = np.array([[int(l.x * w), int(l.y * h)]
# #                     for l in results.multi_face_landmarks[0].landmark])

# #     x_min, y_min = np.min(pts, axis=0)
# #     x_max, y_max = np.max(pts, axis=0)

# #     box_w = x_max - x_min
# #     box_h = y_max - y_min

# #     # --- NEW: Check if face is too small ---
# #     if box_w < MIN_FACE_SIZE or box_h < MIN_FACE_SIZE:
# #         return None  # Skip this image, it's too blurry/small

# #     cx = x_min + box_w // 2
# #     cy = y_min + box_h // 2

# #     max_dim = max(box_w, box_h)
# #     pad = int(max_dim * 0.2)  # 20% padding is a good choice
# #     size = max_dim + pad

# #     x1 = cx - size // 2
# #     y1 = cy - size // 2
# #     x2 = cx + size // 2
# #     y2 = cy + size // 2

# #     cropped = safe_crop(image, (x1, y1, x2, y2))
# #     return cropped

# # def process_split(split):
# #     """Process train/test folders."""
# #     src_dir = SRC_ROOT / split
# #     dst_dir = DST_ROOT / split
# #     dst_dir.mkdir(parents=True, exist_ok=True)

# #     class_dirs = [d for d in src_dir.iterdir() if d.is_dir()]

# #     for cls in class_dirs:
# #         out_cls = dst_dir / cls.name
# #         out_cls.mkdir(parents=True, exist_ok=True)

# #         images = list(cls.glob("*"))

# #         print(f"\n📂 Class: {cls.name} ({split}) — {len(images)} images")

# #         for img_path in tqdm(images, desc=f"Processing {cls.name}"):
# #             try:
# #                 img = cv2.imread(str(img_path))
# #                 if img is None:
# #                     continue

# #                 cropped = crop_face_mediapipe(img)
# #                 if cropped is None:
# #                     continue   # skip images with no face

# #                 cropped = cv2.resize(cropped, (IMG_SIZE, IMG_SIZE))
# #                 save_name = img_path.stem + ".jpg"
# #                 cv2.imwrite(str(out_cls / save_name), cropped)

# #             except Exception as e:
# #                 print("Error:", e)
# #                 continue


# # # ================================
# # # MAIN
# # # ================================
# # print("🚀 Starting AffectNet cleaning + face cropping...")

# # process_split("train")
# # process_split("test")

# # print("\n🎉 Cleaning complete!")
# # print("➡ New clean dataset saved to: cleaned_dataset/")
