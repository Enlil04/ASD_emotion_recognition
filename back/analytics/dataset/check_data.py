import os
import random
from pathlib import Path
from PIL import Image

# ==========================================
# PATH SETUP (The Fix)
# ==========================================
# Get the folder where this script lives
SCRIPT_DIR = Path(__file__).resolve().parent

# Check potential locations for the data
# 1. Look for 'archive_clean' right next to this script
POSSIBLE_PATH_1 = SCRIPT_DIR / "archive_clean" / "train"

# 2. Look for 'dataset/archive_clean' (in case you moved it)
POSSIBLE_PATH_2 = SCRIPT_DIR / "dataset" / "archive_clean" / "train"

if POSSIBLE_PATH_1.exists():
    DATASET_PATH = POSSIBLE_PATH_1
elif POSSIBLE_PATH_2.exists():
    DATASET_PATH = POSSIBLE_PATH_2
else:
    print("\n❌ CRITICAL ERROR: Could not find the dataset folder.")
    print(f"   I looked in:\n   1. {POSSIBLE_PATH_1}\n   2. {POSSIBLE_PATH_2}")
    print("\n   Check your folder structure. You should see 'archive_clean' folder nearby.")
    exit()

print(f"✅ Found dataset at: {DATASET_PATH}")

# ==========================================
# MAIN CHECKER
# ==========================================
def check_data_quality():
    print("--- DATA QUALITY CHECK ---")
    print("Press ENTER to see the next image.")
    print("Type 'q' and ENTER to quit.")
    print("-" * 30)

    # Get all emotion folders
    emotions = [d for d in DATASET_PATH.iterdir() if d.is_dir()]
    
    if not emotions:
        print("❌ No emotion folders found! The folder exists but is empty.")
        return

    while True:
        try:
            # 1. Pick a random emotion folder
            emotion_folder = random.choice(emotions)
            
            # 2. Get all images in that folder
            images = list(emotion_folder.glob("*.jpg"))
            
            if not images:
                print(f"⚠️ Warning: {emotion_folder.name} is empty.")
                continue
                
            # 3. Pick a random image
            img_path = random.choice(images)
            
            # 4. Open and Show
            img = Image.open(img_path)
            print(f"Showing: {emotion_folder.name} | Size: {img.size}")
            img.show() 
            
            # 5. Wait for user input
            user_input = input(">> Next? ")
            if user_input.lower() == 'q':
                break
                
        except Exception as e:
            print(f"❌ Error: {e}")
            break

if __name__ == "__main__":
    check_data_quality()