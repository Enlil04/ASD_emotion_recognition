import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from sklearn.utils.class_weight import compute_class_weight
import numpy as np
import os

# Paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ANALYTICS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
DATASET_DIR = os.path.join(ANALYTICS_DIR, "dataset", "archive_clean")

# Config
IMG_SIZE = 224
BATCH_SIZE = 32
EPOCHS = 30
NUM_CLASSES = 8
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("Using device:", DEVICE)

# ----------------------------------------------------
# 1. Transforms — cleaner for emotion classification
# ----------------------------------------------------
train_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.RandomHorizontalFlip(p=0.4),
    transforms.RandomRotation(10),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

val_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

# ----------------------------------------------------
# 2. Training Function
# ----------------------------------------------------
def train_model():

    # Load datasets
    train_ds = datasets.ImageFolder(os.path.join(DATASET_DIR, "train"), transform=train_transform)
    val_ds = datasets.ImageFolder(os.path.join(DATASET_DIR, "test"), transform=val_transform)

    print("Classes:", train_ds.classes)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    # Class weights
    labels = train_ds.targets
    class_weights = compute_class_weight("balanced", classes=np.unique(labels), y=labels)
    class_weights = torch.tensor(class_weights, dtype=torch.float).to(DEVICE)

    # ----------------------------------------------------
    # 3. Load MobileNetV3 Small correctly
    # ----------------------------------------------------
    model = models.mobilenet_v3_small(weights="IMAGENET1K_V1")

    # ALWAYS replace the last linear layer (safe across PyTorch versions)
    in_features = model.classifier[-1].in_features
    model.classifier[-1] = nn.Linear(in_features, NUM_CLASSES)

    model = model.to(DEVICE)

    # Loss, optimizer, scheduler
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.Adam(model.parameters(), lr=1e-4)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

    best_acc = 0.0

    # ----------------------------------------------------
    # 4. Training Loop
    # ----------------------------------------------------
    for epoch in range(EPOCHS):
        print(f"\n----- Epoch {epoch+1}/{EPOCHS} -----")
        model.train()
        running_loss = 0
        running_correct = 0
        total = 0

        for images, labels in train_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            _, preds = torch.max(outputs, 1)
            running_correct += (preds == labels).sum().item()
            total += labels.size(0)

        train_acc = running_correct / total
        train_loss = running_loss / len(train_loader)

        # ---------------- Validation ----------------
        model.eval()
        val_correct = 0
        val_total = 0
        val_loss = 0

        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(DEVICE), labels.to(DEVICE)
                outputs = model(images)
                loss = criterion(outputs, labels)

                val_loss += loss.item()
                _, preds = torch.max(outputs, 1)
                val_correct += (preds == labels).sum().item()
                val_total += labels.size(0)

        val_acc = val_correct / val_total
        val_loss = val_loss / len(val_loader)

        print(f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.3f}")
        print(f"Val   Loss: {val_loss:.4f} | Val   Acc: {val_acc:.3f}")

        scheduler.step()

        # Save best model
        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), "mobilenet_best_AffectNet.pth")
            print("💾 Saved new best model!")

    print("\nTraining Complete.")


if __name__ == "__main__":
    train_model()
# train.py - Rewritten with GPU and Safety Fixes

# import torch
# import torch.nn as nn
# import torch.optim as optim
# from torch.utils.data import DataLoader
# from torchvision import datasets, transforms, models
# from sklearn.utils.class_weight import compute_class_weight
# import numpy as np
# import os

# # --- Configuration for Paths ---
# CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# ANALYTICS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
# DATASET_DIR = os.path.join(
#     ANALYTICS_DIR,
#     "dataset",
#     "archive_clean"
# )

# # --- CONFIG ---
# IMG_SIZE = 224
# BATCH_SIZE = 32  # Safer starting size for VRAM (was 64)
# EPOCHS = 30
# NUM_CLASSES = 8  # AffectNet uses 8 classes
# DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# print("Using device:", DEVICE)
# if DEVICE == "cuda":
#     print(f"CUDA device: {torch.cuda.get_device_name(0)}")

# # -----------------------------------
# # 1. Transforms (AffectNet correct)
# # -----------------------------------
# train_transform = transforms.Compose([
#     transforms.Resize((IMG_SIZE, IMG_SIZE)),
#     transforms.RandomRotation(15),
#     transforms.RandomHorizontalFlip(),
#     transforms.ColorJitter(brightness=0.2, contrast=0.2),
#     transforms.ToTensor(),
#     transforms.Normalize(
#         mean=[0.485, 0.456, 0.406],
#         std=[0.229, 0.224, 0.225]
#     )
# ])

# val_transform = transforms.Compose([
#     transforms.Resize((IMG_SIZE, IMG_SIZE)),
#     transforms.ToTensor(),
#     transforms.Normalize(
#         mean=[0.485, 0.456, 0.406],
#         std=[0.229, 0.224, 0.225]
#     )
# ])

# # -----------------------------------
# # 2. Main Logic Function
# # -----------------------------------
# def train_model():
#     # --- 2. Datasets ---
#     try:
#         train_ds = datasets.ImageFolder(
#             os.path.join(DATASET_DIR, "train"),
#             transform=train_transform
#         )
#         val_ds = datasets.ImageFolder(
#             os.path.join(DATASET_DIR, "test"),
#             transform=val_transform
#         )
#     except Exception as e:
#         print(f"❌ Error loading datasets. Check DATASET_DIR: {DATASET_DIR}")
#         print(f"Details: {e}")
#         return

#     print(f"Train samples: {len(train_ds)}, Val samples: {len(val_ds)}")
#     print("Train classes:", train_ds.classes)

#     # **CHANGE: num_workers added for faster data loading (set to 0 if freezing persists)**
#     train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0, pin_memory=True) #from 4 to 0 if issues
#     val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0, pin_memory=True) #from 4 to 0 if issues

#     # --- 3. Class Weights ---
#     labels = train_ds.targets
#     class_weights = compute_class_weight(
#         "balanced", 
#         classes=np.unique(labels), 
#         y=labels
#     )
#     # Weights moved to DEVICE (GPU)
#     class_weights = torch.tensor(class_weights, dtype=torch.float).to(DEVICE)
#     print("Class weights device:", class_weights.device)

#     # --- 4. Model (MobileNetV3 Small) ---
#     model = models.mobilenet_v3_small(weights="IMAGENET1K_V1")
#     model.classifier[3] = nn.Linear(model.classifier[3].in_features, NUM_CLASSES)
#     model = model.to(DEVICE)
#     print(f"Model moved to: {next(model.parameters()).device}")

#     criterion = nn.CrossEntropyLoss(weight=class_weights)
#     optimizer = optim.Adam(model.parameters(), lr=1e-4)

#     # --- 5. Training Loop ---
#     best_acc = 0.0

#     for epoch in range(EPOCHS):
#         print(f"--- Starting Epoch {epoch+1}/{EPOCHS} ---")
#         model.train()
#         total, correct, epoch_loss = 0, 0, 0

#         for batch_idx, (images, labels) in enumerate(train_loader):
#             # **FIX: Move data to GPU**
#             images, labels = images.to(DEVICE), labels.to(DEVICE)

#             # Optional: Print to ensure batch loading is working
#             # if batch_idx == 0 and epoch == 0:
#             #     print("Batch loaded and moved to GPU. Training step starting...")

#             optimizer.zero_grad()
#             outputs = model(images)
#             loss = criterion(outputs, labels)
#             loss.backward()
#             optimizer.step()

#             epoch_loss += loss.item()
#             _, preds = torch.max(outputs, 1)
#             correct += (preds == labels).sum().item()
#             total += labels.size(0)

#         train_acc = correct / total
#         print(f"Epoch {epoch+1}/{EPOCHS} | Train Loss: {epoch_loss/len(train_loader):.4f} | Train Acc: {train_acc:.3f}")

#         # Validation
#         model.eval()
#         val_correct, val_total = 0, 0
#         with torch.no_grad():
#             for images, labels in val_loader:
#                 # **FIX: Move validation data to GPU**
#                 images, labels = images.to(DEVICE), labels.to(DEVICE)
                
#                 outputs = model(images)
#                 _, preds = torch.max(outputs, 1)
#                 val_correct += (preds == labels).sum().item()
#                 val_total += labels.size(0)

#         val_acc = val_correct / val_total
#         print(f"Validation Acc: {val_acc:.3f}")

#         # Save best model
#         if val_acc > best_acc:
#             best_acc = val_acc
#             torch.save(model.state_dict(), "mobilenet_affectNet.pth")
#             print("💾 Saved best model!")

#     print("Training Done!")

# # -----------------------------------
# # 6. Safety Entry Point
# # -----------------------------------
# if __name__ == "__main__":
#     train_model()