import os
from pathlib import Path
from PIL import Image
from tqdm import tqdm

# Point this to your CLEAN dataset
DATASET_DIR = Path(__file__).parent / "archive_clean"

def remove_corrupt_images():
    print(f"🕵️ Scanning for bad images in: {DATASET_DIR}")
    
    if not DATASET_DIR.exists():
        print("❌ Error: Dataset folder not found.")
        return

    bad_files = []
    # Recursively find all images
    all_images = list(DATASET_DIR.rglob("*.*")) 
    # Filter for image extensions only
    all_images = [p for p in all_images if p.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']]

    print(f"   Found {len(all_images)} total images. Checking validity...")

    for img_path in tqdm(all_images):
        try:
            # Try to open and fully load the image
            with Image.open(img_path) as img:
                img.verify() # Fast check
        except (IOError, SyntaxError) as e:
            print(f"   ❌ CORRUPT: {img_path.name} -> Deleting...")
            bad_files.append(img_path)

    # Delete them
    if bad_files:
        print(f"\n🗑️ Deleting {len(bad_files)} corrupt files...")
        for p in bad_files:
            try:
                os.remove(p)
            except Exception as e:
                print(f"   Error deleting {p.name}: {e}")
        print("✅ Cleanup complete.")
    else:
        print("\n✅ No corrupt images found! Your dataset is clean.")

if __name__ == "__main__":
    remove_corrupt_images()