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

