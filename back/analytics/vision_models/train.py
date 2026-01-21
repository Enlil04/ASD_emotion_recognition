import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader, WeightedRandomSampler
from pathlib import Path
from PIL import Image
import numpy as np
import pandas as pd
from tqdm import tqdm
import os

# =========================================================
# 1. ADVANCED LOSS: FOCAL LOSS (To solve the Neutral/Sad mixup)
# =========================================================
class FocalLoss(nn.Module):
    def __init__(self, weight=None, gamma=2.0):
        super(FocalLoss, self).__init__()
        self.weight = weight
        self.gamma = gamma

    def forward(self, inputs, targets):
        ce_loss = nn.functional.cross_entropy(inputs, targets, weight=self.weight, reduction='none')
        pt = torch.exp(-ce_loss)
        focal_loss = ((1 - pt) ** self.gamma * ce_loss).mean()
        return focal_loss

# =========================================================
# 2. CONFIG & PATHS
# =========================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "dataset" / "archive_clean"
MODEL_SAVE_PATH = "mobilenet_v3_large_affectnet7_.pth"

BATCH_SIZE = 48 # Lowered slightly for more frequent weight updates
EPOCHS = 60
LEARNING_RATE = 2e-4 # Slightly slower learning for better convergence
NUM_CLASSES = 7 

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
USE_AMP = torch.cuda.is_available()

# =========================================================
# 3. TRANSFORMS (Targeting the "Happy-Blindness")
# =========================================================
train_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.RandomGrayscale(p=0.2), # Forces model to look at mouth shape, not skin tone
    transforms.ColorJitter(brightness=0.3, contrast=0.3),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def safe_loader(path):
    try:
        with open(path, "rb") as f:
            img = Image.open(f)
            return img.convert("RGB")
    except Exception:
        return Image.new("RGB", (224, 224), (0, 0, 0))

# =========================================================
# 4. TRAINING FUNCTION
# =========================================================
def train():
    print(f"\n🚀 Training Started on: {DEVICE}")
    
    train_ds = datasets.ImageFolder(DATASET_DIR / "train", transform=train_transform, loader=safe_loader)
    val_ds = datasets.ImageFolder(DATASET_DIR / "test", transform=val_transform, loader=safe_loader)

    # --- CALCULATE WEIGHTS ---
    # Index Check: Anger=0, Disgust=1, Fear=2, Happy=3, Neutral=4, Sad=5, Surprise=6
    counts = np.bincount(train_ds.targets)
    
    # Standard inverse weighting
    weights = 1.0 / torch.tensor(counts, dtype=torch.float)
    
    # !!! EMERGENCY OVERRIDES !!!
# Anger=0, Disgust=1, Fear=2, Happy=3, Neutral=4, Sad=5, Surprise=6

    weights[0] = weights[0] * 2.5  # BUFF ANGER (Eyebrow tension)
    weights[1] = weights[1] * 3.0  # BUFF DISGUST (Nose wrinkle - very rare!)
    weights[2] = weights[2] * 2.5  # BUFF FEAR (Widened eyes)
    weights[3] = weights[3] * 2.0  # KEEP HAPPY (Keep the 2x, but not 4x or it blinds others)
    weights[4] = weights[4] * 1.0  # NEUTRAL (Base)
    weights[5] = weights[5] * 1.5  # BUFF SAD (Bring it back slightly)
    weights[6] = weights[6] * 1.0  # SURPRISE (Already doing well)

    loss_weights = (weights / weights.sum() * len(counts)).to(DEVICE)

    # Sampler: Balances the batches so model sees Happy faces as often as Sad
    sample_weights = (weights.cpu().numpy())[train_ds.targets]
    sampler = WeightedRandomSampler(
        weights=torch.from_numpy(sample_weights).float(),
        num_samples=len(sample_weights),
        replacement=True
    )

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler, num_workers=4, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=4, pin_memory=True)

    # --- BUILD MODEL ---
    model = models.mobilenet_v3_large(weights="IMAGENET1K_V2")
    in_features = model.classifier[0].in_features
    model.classifier = nn.Sequential(
        nn.Linear(in_features, 1024),
        nn.Hardswish(),
        nn.Dropout(0.4), # Slightly lower dropout
        nn.Linear(1024, NUM_CLASSES)
    )
    model.to(DEVICE)

    # --- OPTIMIZATION ---
    # Using Focal Loss instead of CrossEntropy
    criterion = FocalLoss(weight=loss_weights, gamma=2.0)
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-2)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    scaler = torch.cuda.amp.GradScaler(enabled=USE_AMP)

    # --- LOOP ---
    best_acc = 0.0
    for epoch in range(EPOCHS):
        model.train()
        correct, total = 0, 0
        
        loop = tqdm(train_loader, desc=f"Epoch {epoch+1}/{EPOCHS}")
        for images, targets in loop:
            images, targets = images.to(DEVICE), targets.to(DEVICE)
            optimizer.zero_grad(set_to_none=True)

            with torch.cuda.amp.autocast(enabled=USE_AMP):
                outputs = model(images)
                loss = criterion(outputs, targets)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            _, preds = outputs.max(1)
            correct += (preds == targets).sum().item()
            total += targets.size(0)
            loop.set_postfix(acc=f"{100*correct/total:.2f}%")

        # --- VALIDATION ---
        model.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for images, targets in val_loader:
                images, targets = images.to(DEVICE), targets.to(DEVICE)
                outputs = model(images)
                _, preds = outputs.max(1)
                val_correct += (preds == targets).sum().item()
                val_total += targets.size(0)

        val_acc = val_correct / val_total
        print(f"📈 Summary | Train Acc: {100*correct/total:.2f}% | Val Acc: {100*val_acc:.2f}%")
        
        scheduler.step()
        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), MODEL_SAVE_PATH)
            print(f"⭐ Saved Best Model!")

    print(f"\n✅ Training Complete. Best Val Accuracy: {100*best_acc:.2f}%")

if __name__ == "__main__":
    train()

# the 1st one 
# import torch
# import torch.nn as nn
# import torch.optim as optim
# from torchvision import datasets, transforms, models
# from torch.utils.data import DataLoader, WeightedRandomSampler
# from pathlib import Path
# from PIL import Image
# import numpy as np
# import pandas as pd
# from tqdm import tqdm
# import os

# # =========================================================
# # 1. PATHS & CONFIG
# # =========================================================
# BASE_DIR = Path(__file__).resolve().parent.parent
# DATASET_DIR = BASE_DIR / "dataset" / "archive_clean"
# MODEL_SAVE_PATH = "mobilenet_v3_large_affectnet7.pth"

# BATCH_SIZE = 64
# EPOCHS = 50
# LEARNING_RATE = 3e-4
# NUM_CLASSES = 7  # (Anger, Disgust, Fear, Happy, Neutral, Sad, Surprise)
# LABEL_SMOOTHING = 0.05

# DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# USE_AMP = torch.cuda.is_available()

# # =========================================================
# # 2. DATA UTILITIES
# # =========================================================
# def safe_loader(path):
#     try:
#         with open(path, "rb") as f:
#             img = Image.open(f)
#             return img.convert("RGB")
#     except Exception:
#         return Image.new("RGB", (224, 224), (0, 0, 0))

# train_transform = transforms.Compose([
#     transforms.Resize((224, 224)),
#     transforms.RandomHorizontalFlip(),
#     transforms.RandomRotation(20),
#     transforms.ColorJitter(0.3, 0.3),
#     transforms.RandomAffine(0, translate=(0.1, 0.1)),
#     transforms.ToTensor(),
#     transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
#     transforms.RandomErasing(p=0.2, scale=(0.02, 0.1))
# ])

# val_transform = transforms.Compose([
#     transforms.Resize((224, 224)),
#     transforms.ToTensor(),
#     transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
# ])

# # =========================================================
# # 3. TRAINING FUNCTION
# # =========================================================
# def train():
#     print(f"\n🚀 Training Started on: {DEVICE}")
    
#     # --- Load Data ---
#     train_ds = datasets.ImageFolder(DATASET_DIR / "train", transform=train_transform, loader=safe_loader)
#     val_ds = datasets.ImageFolder(DATASET_DIR / "test", transform=val_transform, loader=safe_loader)

#     # --- Handle Class Imbalance using labels.csv ---
#     csv_path = DATASET_DIR / "labels.csv"
#     if csv_path.exists():
#         print("📊 Calculating weights from labels.csv...")
#         df = pd.read_csv(csv_path)
#         # Ensure we only count classes that exist in our 7-class setup
#         counts = df['label'].value_counts().sort_index().values
#     else:
#         print("⚠️ labels.csv not found, using folder counts.")
#         counts = np.bincount(train_ds.targets)

#     # Calculate Weights for Loss Function (Penalizes missing rare emotions)
#     total_samples = sum(counts)
#     weights = total_samples / (len(counts) * counts)
#     loss_weights = torch.tensor(weights, dtype=torch.float).to(DEVICE)

#     # Calculate Weights for Sampler (Shows model more rare images)
#     sample_weights = (1.0 / counts)[train_ds.targets]
#     sampler = WeightedRandomSampler(
#         weights=torch.from_numpy(sample_weights).float(),
#         num_samples=len(sample_weights),
#         replacement=True
#     )

#     # --- Data Loaders ---
#     train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler, num_workers=4, pin_memory=True)
#     val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=4, pin_memory=True)

#     # --- Build Model ---
#     model = models.mobilenet_v3_large(weights="IMAGENET1K_V2")
#     in_features = model.classifier[0].in_features
    
#     # Custom head to match your EmotionDetector script
#     model.classifier = nn.Sequential(
#         nn.Linear(in_features, 1024),
#         nn.Hardswish(),
#         nn.Dropout(0.5),
#         nn.Linear(1024, NUM_CLASSES)
#     )
#     model.to(DEVICE)

#     # --- Optimization ---
#     criterion = nn.CrossEntropyLoss(weight=loss_weights, label_smoothing=LABEL_SMOOTHING)
#     optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-2)
#     scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
#     scaler = torch.cuda.amp.GradScaler(enabled=USE_AMP)

#     # --- Loop ---
#     best_acc = 0.0
#     for epoch in range(EPOCHS):
#         model.train()
#         train_loss, correct, total = 0, 0, 0
        
#         loop = tqdm(train_loader, desc=f"Epoch {epoch+1}/{EPOCHS}")
#         for images, targets in loop:
#             images, targets = images.to(DEVICE), targets.to(DEVICE)
            
#             optimizer.zero_grad(set_to_none=True)

#             with torch.cuda.amp.autocast(enabled=USE_AMP):
#                 outputs = model(images)
#                 loss = criterion(outputs, targets)

#             scaler.scale(loss).backward()
#             scaler.step(optimizer)
#             scaler.update()

#             _, preds = outputs.max(1)
#             correct += (preds == targets).sum().item()
#             total += targets.size(0)
#             train_loss += loss.item()

#             loop.set_postfix(acc=f"{100*correct/total:.2f}%", loss=f"{loss.item():.4f}")

#         # --- Validation ---
#         model.eval()
#         val_correct, val_total = 0, 0
#         with torch.no_grad():
#             for images, targets in val_loader:
#                 images, targets = images.to(DEVICE), targets.to(DEVICE)
#                 outputs = model(images)
#                 _, preds = outputs.max(1)
#                 val_correct += (preds == targets).sum().item()
#                 val_total += targets.size(0)

#         val_acc = val_correct / val_total
#         print(f"📈 Summary | Train Acc: {100*correct/total:.2f}% | Val Acc: {100*val_acc:.2f}%")
        
#         scheduler.step()

#         if val_acc > best_acc:
#             best_acc = val_acc
#             torch.save(model.state_dict(), MODEL_SAVE_PATH)
#             print(f"⭐ Saved Best Model: {100*best_acc:.2f}%")

#     print(f"\n✅ Training Complete. Best Val Accuracy: {100*best_acc:.2f}%")

# if __name__ == "__main__":
#     train()




# import torch
# import torch.nn as nn
# import torch.optim as optim
# from torchvision import datasets, transforms, models
# from torch.utils.data import DataLoader, WeightedRandomSampler
# from sklearn.utils.class_weight import compute_class_weight
# from tqdm import tqdm
# from pathlib import Path
# from PIL import Image
# import numpy as np
# import json
# import os

# # ==========================================
# # 1. ROBUST PATHING (Fixes FileNotFoundError)
# # ==========================================
# # This finds the absolute path regardless of where you run the script from
# BASE_DIR = Path(__file__).resolve().parent.parent # Points to 'analytics' folder
# DATASET_DIR = BASE_DIR / "dataset" / "archive_clean"

# # CONFIGURATION
# BATCH_SIZE = 64          # If GPU allows
# EPOCHS = 50              # 60 is OK but diminishing returns
# LEARNING_RATE = 3e-4     # Slightly safer
# NUM_CLASSES = 8         # AffectNet has 8 classes
# label_smoothing = 0.05   # 0.1 is a bit high for emotion

# DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# # ==========================================
# # 2. SAFE LOADER (Fixes UnidentifiedImageError)
# # ==========================================
# def safe_loader(path):
#     try:
#         with open(path, 'rb') as f:
#             img = Image.open(f)
#             return img.convert('RGB')
#     except Exception as e:
#         print(f"\n⚠️ Skipping corrupt image: {path}")
#         return Image.new('RGB', (224, 224), (0, 0, 0)) # Return black image as fallback

# # ==========================================
# # 3. AUGMENTATION (Fixes 30% Overfitting Gap)
# # ==========================================
# train_transform = transforms.Compose([
#     transforms.Resize((224, 224)),
#     transforms.RandomHorizontalFlip(),
#     transforms.RandomRotation(20),
#     transforms.ColorJitter(brightness=0.3, contrast=0.3),
#     transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
#     transforms.ToTensor(),
#     transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
#     transforms.RandomErasing(p=0.2, scale=(0.02, 0.1)) # Forces model to look at features, not noise
# ])

# val_transform = transforms.Compose([
#     transforms.Resize((224, 224)),
#     transforms.ToTensor(),
#     transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
# ])

# def train_model():
#     print(f"🚀 Training on: {DEVICE}")
#     print(f"📂 Dataset Path: {DATASET_DIR}")

#     if not DATASET_DIR.exists():
#         print(f"❌ Error: Cannot find dataset at {DATASET_DIR}")
#         return

#     # --- 4. Load Datasets ---
#     train_ds = datasets.ImageFolder(root=str(DATASET_DIR / "train"), transform=train_transform, loader=safe_loader)
#     val_ds = datasets.ImageFolder(root=str(DATASET_DIR / "test"), transform=val_transform, loader=safe_loader)

#     # Balanced Sampling (Crucial for AffectNet imbalance)
#     labels = np.array(train_ds.targets)
#     class_count = np.bincount(labels)
#     class_count[class_count == 0] = 1  # avoid division by zero
#     class_weights_sample = 1.0 / torch.tensor(class_count, dtype=torch.float)

#     sampler = WeightedRandomSampler(weights=class_weights_sample[labels], num_samples=len(labels), replacement=True)
    
#     train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler, num_workers=4, pin_memory=True)
#     val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=4, pin_memory=True)

#     # --- 5. Model (MobileNetV3-Large for higher accuracy) ---
#     model = models.mobilenet_v3_large(weights="IMAGENET1K_V2")
#     num_ftrs = model.classifier[0].in_features
    
#     model.classifier = nn.Sequential(
#         nn.Linear(num_ftrs, 1024),
#         nn.Hardswish(),
#         nn.Dropout(p=0.5), # High dropout to stop the 86% vs 55% gap
#         nn.Linear(1024, NUM_CLASSES)
#     )
#     model = model.to(DEVICE)

#     # --- 6. Optimization ---
#     criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
#     optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-2) # Stronger weight decay
#     scaler = torch.cuda.amp.GradScaler()
#     scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

#     # --- 7. Training Loop ---
#     best_acc = 0.0
#     for epoch in range(EPOCHS):
#         model.train()
#         train_correct, train_total = 0, 0
        
#         loop = tqdm(train_loader, desc=f"Epoch {epoch+1}/{EPOCHS}")
#         for images, labels_batch in loop:
#             images, labels_batch = images.to(DEVICE), labels_batch.to(DEVICE)
            
#             optimizer.zero_grad()
            
#             with torch.cuda.amp.autocast():  # <-- automatic mixed precision
#                 outputs = model(images)
#                 loss = criterion(outputs, labels_batch)
            
#             scaler.scale(loss).backward()
#             scaler.step(optimizer)
#             scaler.update()
            
#             _, preds = torch.max(outputs, 1)
#             train_correct += (preds == labels_batch).sum().item()
#             train_total += labels_batch.size(0)
#             loop.set_postfix(acc=f"{100*train_correct/train_total:.2f}%")


#         # for images, labels_batch in loop:
#         #     images, labels_batch = images.to(DEVICE), labels_batch.to(DEVICE)
            
#         #     optimizer.zero_grad()
#         #     outputs = model(images)
#         #     loss = criterion(outputs, labels_batch)
#         #     loss.backward()
#         #     optimizer.step()

#         #     _, preds = torch.max(outputs, 1)
#         #     train_correct += (preds == labels_batch).sum().item()
#         #     train_total += labels_batch.size(0)
#         #     loop.set_postfix(acc=f"{100*train_correct/train_total:.2f}%")

#         # Validation
#         model.eval()
#         val_correct, val_total = 0, 0
#         with torch.no_grad():
#             for images, labels_batch in val_loader:
#                 images, labels_batch = images.to(DEVICE), labels_batch.to(DEVICE)
#                 outputs = model(images)
#                 _, preds = torch.max(outputs, 1)
#                 val_correct += (preds == labels_batch).sum().item()
#                 val_total += labels_batch.size(0)

#         val_acc = val_correct / val_total
#         print(f"📊 Epoch {epoch+1} Summary: Train Acc: {100*train_correct/train_total:.2f}% | Val Acc: {100*val_acc:.2f}%")

#         scheduler.step()

#         if val_acc > best_acc:
#             best_acc = val_acc
#             torch.save(model.state_dict(), "mobilenet_v3_large_best.pth")
#             print(f"⭐ Saved New Best: {100*val_acc:.2f}%")

# if __name__ == "__main__":
#     train_model()
# import torch
# import torch.nn as nn
# import torch.optim as optim
# from torch.utils.data import DataLoader, WeightedRandomSampler
# from torchvision import datasets, transforms, models
# from sklearn.utils.class_weight import compute_class_weight
# from sklearn.metrics import classification_report, confusion_matrix
# import numpy as np
# import os
# import json

# # ==========================================
# # CONFIGURATION
# # ==========================================
# CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# ANALYTICS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
# DATASET_DIR = os.path.join(ANALYTICS_DIR, "dataset", "archive_clean")

# IMG_SIZE = 224
# BATCH_SIZE = 32   # Keep 32 for stability
# EPOCHS = 60       # AffectNet is huge; 60 epochs is usually plenty
# LEARNING_RATE = 1e-3

# # CHANGE 1: AffectNet has 8 classes (includes 'Contempt')
# # Check your folder: archive_clean/train/ should have 8 subfolders
# NUM_CLASSES = 8 

# DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# print(f"Using device: {DEVICE}")
# if DEVICE == "cuda":
#     print(f"CUDA device: {torch.cuda.get_device_name(0)}")

# # ==========================================
# # TRANSFORMS (Data Augmentation)
# # ==========================================
# train_transform = transforms.Compose([
#     transforms.Resize((IMG_SIZE, IMG_SIZE)),
    
#     # Aggressive augmentation helps AffectNet generalization
#     transforms.RandomRotation(15),
#     transforms.RandomHorizontalFlip(p=0.5),
#     transforms.RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.9, 1.1)),
#     transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1),
    
#     transforms.ToTensor(),       
#     transforms.Normalize(        
#         mean=[0.485, 0.456, 0.406],
#         std=[0.229, 0.224, 0.225]
#     ), 
#     transforms.RandomErasing(p=0.1, scale=(0.02, 0.15)), 
# ])

# val_transform = transforms.Compose([
#     transforms.Resize((IMG_SIZE, IMG_SIZE)),
#     transforms.ToTensor(),
#     transforms.Normalize(
#         mean=[0.485, 0.456, 0.406],
#         std=[0.229, 0.224, 0.225]
#     )
# ])

# # ==========================================
# # MAIN TRAINING LOGIC
# # ==========================================
# def train_model():
#     # --- 1. Load Datasets ---
#     try:
#         train_ds = datasets.ImageFolder(
#             os.path.join(DATASET_DIR, "train"),
#             transform=train_transform
#         )
#         # Note: AffectNet often calls the test set 'val'
#         val_path = os.path.join(DATASET_DIR, "val")
#         if not os.path.exists(val_path):
#             val_path = os.path.join(DATASET_DIR, "test")
            
#         val_ds = datasets.ImageFolder(val_path, transform=val_transform)
        
#     except Exception as e:
#         print(f"❌ Error loading datasets. Check DATASET_DIR: {DATASET_DIR}")
#         print(f"Details: {e}")
#         return

#     print(f"Train samples: {len(train_ds)}, Val samples: {len(val_ds)}")
#     print("Train classes:", train_ds.classes)

#     # Save Class Names for the App
#     with open("class_names.json", "w") as f:
#         json.dump(train_ds.classes, f)
#     print("✓ Saved class_names.json")

#     # --- 2. Weighted Sampler (Crucial for AffectNet) ---
#     labels = np.array(train_ds.targets)
#     class_counts = np.bincount(labels)
    
#     # Check for empty classes
#     if 0 in class_counts:
#         print("⚠️ Warning: Some classes have 0 samples!")
        
#     class_weights_sample = 1.0 / torch.tensor(class_counts, dtype=torch.float)
#     sample_weights = class_weights_sample[labels]
    
#     sampler = WeightedRandomSampler(
#         weights=sample_weights,
#         num_samples=len(sample_weights),
#         replacement=True
#     )
    
#     # --- 3. DataLoaders ---
#     train_loader = DataLoader(
#         train_ds, 
#         batch_size=BATCH_SIZE, 
#         sampler=sampler, 
#         num_workers=2, 
#         pin_memory=True,
#         persistent_workers=True
#     )
    
#     val_loader = DataLoader(
#         val_ds, 
#         batch_size=BATCH_SIZE, 
#         shuffle=False, 
#         num_workers=2, 
#         pin_memory=True,
#         persistent_workers=True
#     )

#     # --- 4. Class Weights for Loss ---
#     weights = compute_class_weight(
#         class_weight='balanced',
#         classes=np.unique(labels),
#         y=labels
#     )
#     class_weights = torch.tensor(weights, dtype=torch.float).to(DEVICE)
#     print("Class weights for Loss:", class_weights.cpu().numpy().round(2))

#     # --- 5. Model Architecture ---
#     model = models.mobilenet_v3_small(weights="IMAGENET1K_V1")
    
#     # Custom Head
#     model.classifier = nn.Sequential(
#         nn.Linear(576, 1024),
#         nn.Hardswish(),
#         nn.Dropout(p=0.3),
#         nn.Linear(1024, NUM_CLASSES)
#     )
    
#     model = model.to(DEVICE)

#     # --- 6. Optimization ---
#     criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.1)
    
#     optimizer = optim.AdamW(
#         model.parameters(), 
#         lr=LEARNING_RATE, 
#         weight_decay=1e-4
#     )
    
#     scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
#         optimizer, 
#         T_0=10, 
#         T_mult=2
#     )

#     # --- 7. Training Loop ---
#     best_acc = 0.0
#     patience = 12
#     patience_counter = 0

#     for epoch in range(EPOCHS):
#         print(f"\n{'='*70}")
#         print(f"EPOCH {epoch+1}/{EPOCHS} | LR: {optimizer.param_groups[0]['lr']:.6f}")
#         print('='*70)
        
#         # Training
#         model.train()
#         total, correct, epoch_loss = 0, 0, 0

#         for batch_idx, (images, labels_batch) in enumerate(train_loader):
#             images, labels_batch = images.to(DEVICE), labels_batch.to(DEVICE)
            
#             optimizer.zero_grad()
#             outputs = model(images)
#             loss = criterion(outputs, labels_batch)
#             loss.backward()
            
#             torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
#             optimizer.step()

#             epoch_loss += loss.item()
#             _, preds = torch.max(outputs, 1)
#             correct += (preds == labels_batch).sum().item()
#             total += labels_batch.size(0)

#         train_acc = correct / total
#         avg_train_loss = epoch_loss / len(train_loader)
#         print(f"✓ Train Loss: {avg_train_loss:.4f} | Train Acc: {train_acc:.4f}")

#         # Validation
#         model.eval()
#         all_preds = []
#         all_labels = []
#         val_correct, val_total = 0, 0
#         val_loss = 0.0

#         with torch.no_grad():
#             for images, labels_batch in val_loader:
#                 images, labels_batch = images.to(DEVICE), labels_batch.to(DEVICE)
#                 outputs = model(images)
#                 loss = criterion(outputs, labels_batch)
#                 val_loss += loss.item()

#                 _, preds = torch.max(outputs, 1)
#                 val_correct += (preds == labels_batch).sum().item()
#                 val_total += labels_batch.size(0)

#                 all_preds.extend(preds.cpu().numpy())
#                 all_labels.extend(labels_batch.cpu().numpy())
                
#         val_acc = val_correct / val_total
#         avg_val_loss = val_loss / len(val_loader)
#         print(f"✓ Val Loss:   {avg_val_loss:.4f} | Val Acc:   {val_acc:.4f}")

#         # Metrics
#         if (epoch + 1) % 5 == 0:
#             print("\n" + "="*70)
#             print("CLASSIFICATION REPORT:")
#             print(classification_report(all_labels, all_preds, target_names=train_ds.classes, zero_division=0))
#             print("="*70)

#         scheduler.step()

#         # Save Best Model
#         if val_acc > best_acc:
#             best_acc = val_acc
#             # CHANGE 2: Updated filename for AffectNet
#             torch.save(model.state_dict(), "mobilenet_best_AffectNet.pth")
#             print(f"\n🎉 NEW BEST MODEL SAVED! Val Acc: {val_acc:.4f}")
#             patience_counter = 0
#         else:
#             patience_counter += 1
            
#         if patience_counter >= patience:
#             print(f"\n⚠️ Early stopping triggered.")
#             break

#     print(f"\n{'='*70}")
#     print(f"🏁 TRAINING COMPLETE!")
#     print(f"🏆 Best Validation Accuracy: {best_acc:.4f}")
#     print('='*70)

# if __name__ == "__main__":
#     train_model()
# raf-db train script
# import torch
# import torch.nn as nn
# import torch.optim as optim
# from torch.utils.data import DataLoader, WeightedRandomSampler  # <--- Added Sampler
# from torchvision import datasets, transforms, models
# from sklearn.utils.class_weight import compute_class_weight
# from sklearn.metrics import classification_report, confusion_matrix # <--- Added Matrix
# import numpy as np
# import os
# import json

# # --- Configuration for Paths ---
# CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# ANALYTICS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
# DATASET_DIR = os.path.join(ANALYTICS_DIR, "dataset", "archive_clean")

# # --- CONFIG ---
# IMG_SIZE = 224
# BATCH_SIZE = 32   # Reduced slightly for stability
# EPOCHS = 75       # RAF-DB converges faster than FER
# LEARNING_RATE = 1e-3 # <--- Defined this
# NUM_CLASSES = 7 

# DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# print(f"Using device: {DEVICE}")
# if DEVICE == "cuda":
#     print(f"CUDA device: {torch.cuda.get_device_name(0)}")

# # -----------------------------------
# # 1. Transforms (Tailored for RAF-DB)
# # -----------------------------------
# # RAF-DB is high quality, so we use "Medium-High" augmentation
# train_transform = transforms.Compose([
#     transforms.Resize((IMG_SIZE, IMG_SIZE)),
#     transforms.RandomRotation(15),
#     transforms.RandomHorizontalFlip(p=0.5),
#     transforms.RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.9, 1.1)),
#     transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1),
    
#     transforms.ToTensor(),       # 1. Convert Image to Tensor
#     transforms.Normalize(        # 2. Normalize
#         mean=[0.485, 0.456, 0.406],
#         std=[0.229, 0.224, 0.225]
#     ), 
#     transforms.RandomErasing(p=0.1, scale=(0.02, 0.15)), # 3. Random Erasing
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
#     # --- Datasets ---
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

#     # Analyze class distribution
#     labels = np.array(train_ds.targets)
#     unique, counts = np.unique(labels, return_counts=True)
#     print("\nClass distribution in training set:")
#     for cls_idx, count in zip(unique, counts):
#         print(f"   {train_ds.classes[cls_idx]:12s}: {count:5d} samples ({count/len(labels)*100:.1f}%)")

#     # SAVE CLASS NAMES (Crucial for App)
#     with open("class_names.json", "w") as f:
#         json.dump(train_ds.classes, f)
#     print("✓ Saved class_names.json")

#     # -----------------------------------
#     # WEIGHTED SAMPLING (The "Secret Sauce" for Imbalance)
#     # -----------------------------------
#     # This forces the dataloader to pick "Fear" as often as "Happy"
#     class_counts = np.bincount(labels)
#     class_weights_sample = 1.0 / torch.tensor(class_counts, dtype=torch.float)
#     sample_weights = class_weights_sample[labels]
    
#     sampler = WeightedRandomSampler(
#         weights=sample_weights,
#         num_samples=len(sample_weights),
#         replacement=True
#     )
    
#     # DATALOADERS
#     train_loader = DataLoader(
#         train_ds, 
#         batch_size=BATCH_SIZE, 
#         sampler=sampler,  # <--- Using Sampler (Auto-Shuffles)
#         num_workers=2, 
#         pin_memory=True,
#         persistent_workers=True
#     )
    
#     val_loader = DataLoader(
#         val_ds, 
#         batch_size=BATCH_SIZE, 
#         shuffle=False, 
#         num_workers=2, 
#         pin_memory=True,
#         persistent_workers=True
#     )

#     # -----------------------------------
#     # CLASS WEIGHTS FOR LOSS (Double Safety)
#     # -----------------------------------
#     weights = compute_class_weight(
#         class_weight='balanced',
#         classes=np.unique(labels),
#         y=labels
#     )
#     class_weights = torch.tensor(weights, dtype=torch.float).to(DEVICE)
#     print("Class weights for Loss:", class_weights.cpu().numpy().round(2))

#     # -----------------------------------
#     # MODEL: MobileNetV3 Small
#     # -----------------------------------
#     model = models.mobilenet_v3_small(weights="IMAGENET1K_V1")
    
#     # Custom Classifier Head
#     model.classifier = nn.Sequential(
#         nn.Linear(576, 1024),
#         nn.Hardswish(),
#         nn.Dropout(p=0.3), # Helps prevent overfitting
#         nn.Linear(1024, NUM_CLASSES)
#     )
    
#     model = model.to(DEVICE)

#     # -----------------------------------
#     # LOSS, OPTIMIZER, SCHEDULER
#     # -----------------------------------
#     criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.1)
    
#     optimizer = optim.AdamW(
#         model.parameters(), 
#         lr=LEARNING_RATE, 
#         weight_decay=1e-4
#     )
    
#     # Cosine Annealing (Starts fast, slows down smoothly)
#     scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
#         optimizer, 
#         T_0=10, 
#         T_mult=2
#     )

#     # -----------------------------------
#     # TRAINING LOOP
#     # -----------------------------------
#     best_acc = 0.0
#     patience = 12
#     patience_counter = 0

#     for epoch in range(EPOCHS):
#         print(f"\n{'='*70}")
#         print(f"EPOCH {epoch+1}/{EPOCHS} | LR: {optimizer.param_groups[0]['lr']:.6f}")
#         print('='*70)
        
#         # ========== TRAINING ==========
#         model.train()
#         total, correct, epoch_loss = 0, 0, 0

#         for batch_idx, (images, labels_batch) in enumerate(train_loader):
#             images, labels_batch = images.to(DEVICE), labels_batch.to(DEVICE)
            
#             optimizer.zero_grad()
#             outputs = model(images)
#             loss = criterion(outputs, labels_batch)
#             loss.backward()
            
#             # Gradient clipping (prevents "exploding" gradients)
#             torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            
#             optimizer.step()

#             epoch_loss += loss.item()
#             _, preds = torch.max(outputs, 1)
#             correct += (preds == labels_batch).sum().item()
#             total += labels_batch.size(0)

#         train_acc = correct / total
#         avg_train_loss = epoch_loss / len(train_loader)
#         print(f"✓ Train Loss: {avg_train_loss:.4f} | Train Acc: {train_acc:.4f}")

#         # ========== VALIDATION ==========
#         model.eval()
#         all_preds = []
#         all_labels = []
#         val_correct, val_total = 0, 0
#         val_loss = 0.0

#         with torch.no_grad():
#             for images, labels_batch in val_loader:
#                 images, labels_batch = images.to(DEVICE), labels_batch.to(DEVICE)
#                 outputs = model(images)
#                 loss = criterion(outputs, labels_batch)
#                 val_loss += loss.item()

#                 _, preds = torch.max(outputs, 1)
#                 val_correct += (preds == labels_batch).sum().item()
#                 val_total += labels_batch.size(0)

#                 all_preds.extend(preds.cpu().numpy())
#                 all_labels.extend(labels_batch.cpu().numpy())
                
#         val_acc = val_correct / val_total
#         avg_val_loss = val_loss / len(val_loader)
#         print(f"✓ Val Loss:   {avg_val_loss:.4f} | Val Acc:   {val_acc:.4f}")

#         # ========== DETAILED METRICS ==========
#         if (epoch + 1) % 5 == 0:
#             print("\n" + "="*70)
#             print("CLASSIFICATION REPORT:")
#             print(classification_report(all_labels, all_preds, target_names=train_ds.classes, zero_division=0))
#             print("="*70)

#         scheduler.step()

#         # ========== SAVE BEST MODEL ==========
#         if val_acc > best_acc:
#             best_acc = val_acc
#             # Updated filename for RAF-DB
#             torch.save(model.state_dict(), "mobilenet_best_RAFDB.pth")
#             print(f"\n🎉 NEW BEST MODEL SAVED! Val Acc: {val_acc:.4f}")
#             patience_counter = 0
#         else:
#             patience_counter += 1
            
#         # Early stopping
#         if patience_counter >= patience:
#             print(f"\n⚠️ Early stopping triggered (no improvement for {patience} epochs)")
#             break

#     print(f"\n{'='*70}")
#     print(f"🏁 TRAINING COMPLETE!")
#     print(f"🏆 Best Validation Accuracy: {best_acc:.4f}")
#     print('='*70)

# if __name__ == "__main__":
#     train_model()
# import torch
# import torch.nn as nn
# import torch.optim as optim
# from torch.utils.data import DataLoader
# from torchvision import datasets, transforms, models
# from sklearn.utils.class_weight import compute_class_weight
# from sklearn.metrics import classification_report
# import numpy as np
# import os
# import json  # <--- REQUIRED for saving class names

# # --- Configuration for Paths ---
# CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# ANALYTICS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
# DATASET_DIR = os.path.join(ANALYTICS_DIR, "dataset", "archive_clean")

# # --- CONFIG ---
# IMG_SIZE = 224
# BATCH_SIZE = 64
# EPOCHS = 100

# # CHANGE 1: FER-2013 usually has 7 classes. 
# # (Check your archive_clean/train folder to be sure!)
# NUM_CLASSES = 7 

# DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# print("Using device:", DEVICE)
# if DEVICE == "cuda":
#     print(f"CUDA device: {torch.cuda.get_device_name(0)}")

# # -----------------------------------
# # 1. Transforms 
# # -----------------------------------

# train_transform = transforms.Compose([
#     # More aggressive augmentation
#     transforms.RandomRotation(15),
#     transforms.RandomHorizontalFlip(p=0.5),
#     transforms.RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.9, 1.1)),
#     transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.3, hue=0.1),
#     transforms.RandomGrayscale(p=0.1),  # Sometimes grayscale helps

#     # ORDER MATTERS HERE:
#     transforms.ToTensor(),       # 1. Convert Image to Tensor
#     transforms.Normalize(        # 2. Normalize (Math stuff)
#         mean=[0.485, 0.456, 0.406],
#         std=[0.229, 0.224, 0.225]
#     ), 
#     transforms.RandomErasing(p=0.2, scale=(0.02, 0.15)), # 3. Erase (Must occur on Tensor)
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
#     # --- Datasets ---
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
#         print(f"Error loading datasets. Check DATASET_DIR: {DATASET_DIR}")
#         print(f"Details: {e}")
#         return

#     print(f"Train samples: {len(train_ds)}, Val samples: {len(val_ds)}")
#     print("Train classes:", train_ds.classes)

#     # analyze class distribution
#     labels = np.array(train_ds.targets)
#     unique, counts = np.unique(labels, return_counts=True)
#     print("\nClass distribution in training set:")
#     for cls_idx, count in zip(unique, counts):
#         print(f"   {train_ds.classes[cls_idx]:12s}: {count:5d} samples ({count/len(labels)*100:.1f}%)")


#     # CHANGE 2: Save class names so the App knows '0' = 'Angry'
#     with open("class_names.json", "w") as f:
#         json.dump(train_ds.classes, f)
#     print("✓ Saved class_names.json")

#     # num_workers=0 is safer on Windows
#     train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=2, pin_memory=True, persistent_workers=True)
#     val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=2, pin_memory=True, persistent_workers=True)

#     # -----------------------------------
#     # WEIGHTED SAMPLING (addresses imbalance)
#     # -----------------------------------
#     class_counts = np.bincount(labels)
#     class_weights_sample = 1.0 / torch.tensor(class_counts, dtype=torch.float)
#     sample_weights = class_weights_sample[labels]
    
#     sampler = WeightedRandomSampler(
#         weights=sample_weights,
#         num_samples=len(sample_weights),
#         replacement=True
#     )
    
#     train_loader = DataLoader(
#         train_ds, 
#         batch_size=BATCH_SIZE, 
#         sampler=sampler,  # Use sampler instead of shuffle
#         num_workers=4, 
#         pin_memory=True,
#         persistent_workers=True
#     )
    
#     val_loader = DataLoader(
#         val_ds, 
#         batch_size=BATCH_SIZE, 
#         shuffle=False, 
#         num_workers=4, 
#         pin_memory=True,
#         persistent_workers=True
#     )

#     # -----------------------------------
#     # CLASS WEIGHTS FOR LOSS
#     # -----------------------------------
#     weights = compute_class_weight(
#         class_weight='balanced',
#         classes=np.unique(labels),
#         y=labels
#     )
#     class_weights = torch.tensor(weights, dtype=torch.float).to(DEVICE)
#     print("Class weights:", class_weights.cpu().numpy().round(2))

#     # -----------------------------------
#     # MODEL: MobileNetV3 Small
#     # -----------------------------------
#     model = models.mobilenet_v3_small(weights="IMAGENET1K_V1")
    
#     # Add dropout for regularization
#     model.classifier = nn.Sequential(
#         nn.Linear(576, 1024),
#         nn.Hardswish(),
#         nn.Dropout(p=0.3),
#         nn.Linear(1024, NUM_CLASSES)
#     )
    
#     model = model.to(DEVICE)

#     # -----------------------------------
#     # LOSS, OPTIMIZER, SCHEDULER
#     # -----------------------------------
#     criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.1)
    
#     optimizer = optim.AdamW(
#         model.parameters(), 
#         lr=LEARNING_RATE, 
#         weight_decay=1e-4
#     )
    
#     # Cosine annealing with warm restarts
#     scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
#         optimizer, 
#         T_0=10, 
#         T_mult=2
#     )

#     # -----------------------------------
#     # TRAINING LOOP
#     # -----------------------------------
#     best_acc = 0.0
#     patience = 15
#     patience_counter = 0

#     for epoch in range(EPOCHS):
#         print(f"\n{'='*70}")
#         print(f"EPOCH {epoch+1}/{EPOCHS} | LR: {optimizer.param_groups[0]['lr']:.6f}")
#         print('='*70)
        
#         # ========== TRAINING ==========
#         model.train()
#         total, correct, epoch_loss = 0, 0, 0

#         for batch_idx, (images, labels_batch) in enumerate(train_loader):
#             images, labels_batch = images.to(DEVICE), labels_batch.to(DEVICE)
            
#             optimizer.zero_grad()
#             outputs = model(images)
#             loss = criterion(outputs, labels_batch)
#             loss.backward()
            
#             # Gradient clipping
#             torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            
#             optimizer.step()

#             epoch_loss += loss.item()
#             _, preds = torch.max(outputs, 1)
#             correct += (preds == labels_batch).sum().item()
#             total += labels_batch.size(0)

#             if (batch_idx + 1) % 50 == 0:
#                 print(f"   Batch {batch_idx+1}/{len(train_loader)} | Loss: {loss.item():.4f}")

#         train_acc = correct / total
#         avg_train_loss = epoch_loss / len(train_loader)
#         print(f"\n✓ Train Loss: {avg_train_loss:.4f} | Train Acc: {train_acc:.4f}")

#         # ========== VALIDATION ==========
#         model.eval()
#         all_preds = []
#         all_labels = []
#         val_correct, val_total = 0, 0
#         val_loss = 0.0

#         with torch.no_grad():
#             for images, labels_batch in val_loader:
#                 images, labels_batch = images.to(DEVICE), labels_batch.to(DEVICE)
#                 outputs = model(images)
#                 loss = criterion(outputs, labels_batch)
#                 val_loss += loss.item()

#                 _, preds = torch.max(outputs, 1)
#                 val_correct += (preds == labels_batch).sum().item()
#                 val_total += labels_batch.size(0)

#                 all_preds.extend(preds.cpu().numpy())
#                 all_labels.extend(labels_batch.cpu().numpy())
                
#         val_acc = val_correct / val_total
#         avg_val_loss = val_loss / len(val_loader)
#         print(f"✓ Val Loss: {avg_val_loss:.4f} | Val Acc: {val_acc:.4f}")

#         # ========== DETAILED METRICS ==========
#         if (epoch + 1) % 5 == 0:
#             print("\n" + "="*70)
#             print("CLASSIFICATION REPORT:")
#             print("="*70)
#             print(classification_report(
#                 all_labels, 
#                 all_preds, 
#                 target_names=train_ds.classes, 
#                 zero_division=0,
#                 digits=3
#             ))
            
#             # Confusion Matrix
#             cm = confusion_matrix(all_labels, all_preds)
#             print("\nConfusion Matrix:")
#             print("Rows = True, Cols = Predicted")
#             print(cm)
#             print("="*70)

#         scheduler.step()

#         # ========== SAVE BEST MODEL ==========
#         if val_acc > best_acc:
#             best_acc = val_acc
#             torch.save(model.state_dict(), "mobilenet_best_FER2013.pth")
#             print(f"\n🎉 NEW BEST MODEL! Val Acc: {val_acc:.4f}")
#             patience_counter = 0
#         else:
#             patience_counter += 1
            
#         # Early stopping
#         if patience_counter >= patience:
#             print(f"\n⚠️ Early stopping triggered (no improvement for {patience} epochs)")
#             break

#     print(f"\n{'='*70}")
#     print(f"🏁 TRAINING COMPLETE!")
#     print(f"🏆 Best Validation Accuracy: {best_acc:.4f}")
#     print('='*70)

# if __name__ == "__main__":
#     train_model()

    
# # import torch
# # import torch.nn as nn
# # import torch.optim as optim
# # from torch.utils.data import DataLoader
# # from torchvision import datasets, transforms, models
# # from sklearn.utils.class_weight import compute_class_weight
# # from sklearn.metrics import classification_report, confusion_matrix
# # from sklearn.utils.class_weight import compute_class_weight

# # import numpy as np
# # import os

# # # --- Configuration for Paths ---
# # CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# # ANALYTICS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
# # DATASET_DIR = os.path.join(ANALYTICS_DIR,"dataset","archive_clean")

# # # --- CONFIG ---
# # IMG_SIZE = 224
# # BATCH_SIZE = 32
# # EPOCHS = 75
# # NUM_CLASSES = 8
# # DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# # print("Using device:", DEVICE)
# # if DEVICE == "cuda":
# #     print(f"CUDA device: {torch.cuda.get_device_name(0)}")

# # # -----------------------------------
# # # 1. Transforms (AffectNet correct)
# # # -----------------------------------

# # # train_transform is for data augmentation
# # train_transform = transforms.Compose([
# #     transforms.Resize((IMG_SIZE, IMG_SIZE)),
# #     transforms.RandomRotation(10), #might be to aggressive was 15 now 10
# #     transforms.RandomHorizontalFlip(),
# #     transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.05),

# #     transforms.ToTensor(), # 1 convert to tensor
# #     # CRITICAL: Randomly erasing small parts forces the model to look at 
# #     # the whole face, not just one feature (like the mouth).
# #     # Great for when a hand covers part of the face.
# #     transforms.Normalize(mean=[0.485, 0.456, 0.406],std=[0.229, 0.224, 0.225]), # 2 normalize
# #     transforms.RandomErasing(p=0.1, scale=(0.02, 0.1)), # 3 randomly erase small parts
# # ])

# # # cleans the images to make it like they came from camera
# # val_transform = transforms.Compose([
# #     transforms.Resize((IMG_SIZE, IMG_SIZE)),
# #     transforms.ToTensor(),
# #     transforms.Normalize(
# #         mean=[0.485, 0.456, 0.406],
# #         std=[0.229, 0.224, 0.225]
# #     )
# # ])

# # # -----------------------------------
# # # 2. Main Logic Function
# # # -----------------------------------
# # def train_model():
# #     # --- 2. Datasets ---
# #     try:
# #         #loads the training dataset
# #         train_ds = datasets.ImageFolder(
# #             os.path.join(DATASET_DIR, "train"),
# #             transform=train_transform
# #         )
# #         #loads the testing dataset
# #         val_ds = datasets.ImageFolder(
# #             os.path.join(DATASET_DIR, "test"),
# #             transform=val_transform
# #         )
# #     except Exception as e:
# #         print(f"Error loading datasets. Check DATASET_DIR: {DATASET_DIR}")
# #         print(f"Details: {e}")
# #         return

# #     print(f"Train samples: {len(train_ds)}, Val samples: {len(val_ds)}")
# #     print("Train classes:", train_ds.classes)

# #     # Note: num_workers=0 (single process) is often safer on Windows to avoid freezing.
# #     train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0, pin_memory=True)
# #     val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0, pin_memory=True)

# #     # --- 3. Class Weights ---
# #     # pay attention to the rare emotions (still does not work)
# #     labels = train_ds.targets
# #     class_counts = np.bincount(labels)
# #     total_samples = len(labels)


# #     # weights = np.sqrt(total_samples / (len(class_counts) * class_counts)) // tried this but made it worse

# # #------------------------
# #     weights = compute_class_weight(
# #         class_weight='balanced',
# #         classes=np.unique(labels),
# #         y=labels
# #     )

# # # ------------------------
# #     class_weights = torch.tensor(weights, dtype=torch.float).to(DEVICE)
# #     print("Class weights device:", class_weights.device)

# #     # --- 4. Model (MobileNetV3 Small) ---
# #     model = models.mobilenet_v3_small(weights="IMAGENET1K_V1")
# #     # Correctly replace the final linear layer for 8 classes
# #     model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, NUM_CLASSES)
# #     model = model.to(DEVICE)
# #     print(f"Model moved to: {next(model.parameters()).device}")

# #     # Loss, Optimizer, and Scheduler
# #     #criterion measures how wrong the model is, by using class weights
# #     criterion = nn.CrossEntropyLoss(weight=class_weights)
# #     #optimizer used to reduce the error
# #     #  [CHANGED THIS ] optimizer = optim.Adam(model.parameters(), lr=1e-4)
# #     optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
# #     #start fast but slow down when getting closer to more accurate results
# #     scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

# #     # --- 5. Training Loop ---
# #     best_acc = 0.0

# #     for epoch in range(EPOCHS):
# #         print(f"--- Starting Epoch {epoch+1}/{EPOCHS} ---")
# #         model.train()
# #         total, correct, epoch_loss = 0, 0, 0

# #         for batch_idx, (images, labels) in enumerate(train_loader):
# #             # move images and labels to GPU so it can process them
# #             images, labels = images.to(DEVICE), labels.to(DEVICE)
# #             #reset the previously learned info
# #             optimizer.zero_grad()
# #             #the model outputs its guess
# #             outputs = model(images)
# #             #check if the guess is correct by comparing it to the label
# #             loss = criterion(outputs, labels)
# #             #go backward to see what neuron made this mistake
# #             loss.backward()
# #             #try to correct the that mistake
# #             optimizer.step()

# #             epoch_loss += loss.item()
# #             _, preds = torch.max(outputs, 1)
# #             correct += (preds == labels).sum().item()
# #             total += labels.size(0)

# #         train_acc = correct / total
# #         print(f"Epoch {epoch+1}/{EPOCHS} | Train Loss: {epoch_loss/len(train_loader):.4f} | Train Acc: {train_acc:.3f}")




# #         # Validation with detailed metrics
# #         model.eval()
# #         all_preds = []
# #         all_labels = []
# #         val_correct, val_total = 0, 0
# #         val_loss = 0.0

# #         with torch.no_grad():
# #             for images, labels_batch in val_loader:
# #                 images, labels_batch = images.to(DEVICE), labels_batch.to(DEVICE)
# #                 outputs = model(images)

# #                 loss = criterion(outputs, labels_batch)
# #                 val_loss += loss.item()

                
# #                 _, preds = torch.max(outputs, 1)
                
# #                 val_correct += (preds == labels_batch).sum().item()
# #                 val_total += labels_batch.size(0)

# #                 all_preds.extend(preds.cpu().numpy())
# #                 all_labels.extend(labels_batch.cpu().numpy())
                
# #         val_acc = val_correct / val_total
# #         avg_val_loss = val_loss / len(val_loader)
# #         print(f"Validation Loss: {avg_val_loss:.4f} | Validation Acc: {val_acc:.3f}")

# #        # val_acc = val_correct / val_total
# #         #print(f"Validation Acc: {val_acc:.3f}")

# #         # Detailed metrics every 5 epochs
# #         if (epoch + 1) % 5 == 0:
# #             print("\n" + "="*60)
# #             print("PER-CLASS PERFORMANCE:")
# #             print(classification_report(all_labels, all_preds, target_names=train_ds.classes, zero_division=0))
# #             print("="*60)

# #         scheduler.step()

# #         # Save best model
# #         if val_acc > best_acc:
# #             best_acc = val_acc
# #             torch.save(model.state_dict(), "mobilenet_best_AffectNet.pth")
# #             print(f"✓ Saved new best model! Val Acc: {val_acc:.3f}")

# #     print("\nTraining Done! Best Validation Accuracy:", best_acc)

# # if __name__ == "__main__":
# #     train_model()
# # #         #Here we move to testing 
# # #         model.eval()
# # #         val_correct, val_total = 0, 0
# # #         with torch.no_grad():
# # #             for images, labels in val_loader:
# # #                 images, labels = images.to(DEVICE), labels.to(DEVICE)
                
# # #                 outputs = model(images)
# # #                 _, preds = torch.max(outputs, 1)
# # #                 val_correct += (preds == labels).sum().item()
# # #                 val_total += labels.size(0)

# # #         val_acc = val_correct / val_total
# # #         print(f"Validation Acc: {val_acc:.3f}")

        
# # #         scheduler.step()

# # #         # Save best model
# # #         if val_acc > best_acc:
# # #             best_acc = val_acc
# # #             torch.save(model.state_dict(), "mobilenet_best_AffectNet.pth") 
# # #             print(" Saved new best model: mobilenet_best_AffectNet.pth!")

# # #     print("Training Done!")



# # # if __name__ == "__main__":
# # #     train_model()