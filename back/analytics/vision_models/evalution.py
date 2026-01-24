import torch
import torch.nn as nn
from torchvision import datasets, transforms, models
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# --- PATH CONFIGURATION (Fixed) ---
# 1. Get the folder where this script lives (.../analytics/vision_models)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Go up one level to get to 'analytics'
ANALYTICS_DIR = os.path.dirname(CURRENT_DIR)

# 3. Build the correct path to the dataset
DATASET_DIR = os.path.join(ANALYTICS_DIR, "dataset", "archive_clean")

# 4. Path to the model file (assumed to be in the same folder as this script)
MODEL_PATH = os.path.join(CURRENT_DIR, "mobilenet_best_AffectNet.pth")

# --- OTHER CONFIG ---
IMG_SIZE = 224
BATCH_SIZE = 32
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# --- TRANSFORMS ---
test_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def evaluate():
    print(f"🔍 Looking for dataset at: {DATASET_DIR}")
    print(f"🧠 Looking for model at: {MODEL_PATH}")

    # 1. Load Dataset
    test_dir = os.path.join(DATASET_DIR, "test")
    if not os.path.exists(test_dir):
        print(f"❌ ERROR: Could not find test folder at: {test_dir}")
        print("   Please check that your 'dataset' folder is inside 'analytics'.")
        return

    try:
        test_ds = datasets.ImageFolder(test_dir, transform=test_transform)
        test_loader = torch.utils.data.DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)
        class_names = test_ds.classes
        print(f"✅ Dataset loaded! Classes: {class_names}")
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return

    # 2. Load Model
    model = models.mobilenet_v3_small(weights=None)
    # Recreate the architecture exactly as it was trained
    model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, len(class_names))
    
    try:
        state_dict = torch.load(MODEL_PATH, map_location=DEVICE)
        model.load_state_dict(state_dict)
        model.to(DEVICE)
        model.eval()
        print("✅ Model loaded successfully.")
    except FileNotFoundError:
        print(f"❌ Model file not found at {MODEL_PATH}")
        print("   Did you run train.py? Is the .pth file in this folder?")
        return

    # 3. Run Inference
    all_preds = []
    all_labels = []

    print("⚡ Running evaluation (this might take a moment)...")
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(DEVICE)
            outputs = model(images)
            _, preds = torch.max(outputs, 1)
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())

    # 4. Generate Report
    print("\n" + "="*40)
    print("       CLASSIFICATION REPORT       ")
    print("="*40)
    print(classification_report(all_labels, all_preds, target_names=class_names))

    # 5. Generate Confusion Matrix Plot
    try:
        cm = confusion_matrix(all_labels, all_preds)
        plt.figure(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=class_names, yticklabels=class_names)
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.title('Confusion Matrix - Emotion Recognition')
        plt.show()
        print("✅ Confusion Matrix displayed.")
    except Exception as plot_error:
        print(f"⚠️ Report generated, but could not show plot: {plot_error}")

if __name__ == "__main__":
    evaluate()