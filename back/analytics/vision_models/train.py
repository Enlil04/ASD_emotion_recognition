import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from sklearn.utils.class_weight import compute_class_weight
import numpy as np
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# One level up → .../back/analytics
ANALYTICS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

# Full dataset path
DATASET_DIR = os.path.join(
    ANALYTICS_DIR,
    "dataset",
    "archive_clean"
)



# CONFIG
IMG_SIZE = 224
BATCH_SIZE = 64
EPOCHS = 30
NUM_CLASSES = 8   # <-- AffectNet uses 8 classes
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("Using device:", DEVICE)

# -----------------------------------
# 1. Transforms (AffectNet correct)
# -----------------------------------
train_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.RandomRotation(15),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

val_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# -----------------------------------
# 2. Datasets
# -----------------------------------
train_ds = datasets.ImageFolder(
    os.path.join(DATASET_DIR, "train"),
    transform=train_transform
)

val_ds = datasets.ImageFolder(
    os.path.join(DATASET_DIR, "test"),
    transform=val_transform
)


print("Train classes:", train_ds.classes)
print("Val classes:", val_ds.classes)

train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)

# -----------------------------------
# 3. Class Weights
# -----------------------------------
labels = train_ds.targets
class_weights = compute_class_weight(
    "balanced", 
    classes=np.unique(labels), 
    y=labels
)
class_weights = torch.tensor(class_weights, dtype=torch.float).to(DEVICE)
print("Class weights:", class_weights)

# -----------------------------------
# 4. Model (MobileNetV3 Small)
# -----------------------------------
model = models.mobilenet_v3_small(weights="IMAGENET1K_V1")
model.classifier[3] = nn.Linear(model.classifier[3].in_features, NUM_CLASSES)
model = model.to(DEVICE)

criterion = nn.CrossEntropyLoss(weight=class_weights)
optimizer = optim.Adam(model.parameters(), lr=1e-4)

# -----------------------------------
# 5. Training Loop
# -----------------------------------
best_acc = 0.0

for epoch in range(EPOCHS):
    model.train()
    total, correct, epoch_loss = 0, 0, 0

    for images, labels in train_loader:
        images, labels = images.to(DEVICE), labels.to(DEVICE)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        epoch_loss += loss.item()
        _, preds = torch.max(outputs, 1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

    train_acc = correct / total
    print(f"Epoch {epoch+1}/{EPOCHS} | Train Acc: {train_acc:.3f}")

    # Validation
    model.eval()
    val_correct, val_total = 0, 0
    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            outputs = model(images)
            _, preds = torch.max(outputs, 1)
            val_correct += (preds == labels).sum().item()
            val_total += labels.size(0)

    val_acc = val_correct / val_total
    print(f"Validation Acc: {val_acc:.3f}")

    # Save best model
    if val_acc > best_acc:
        best_acc = val_acc
        torch.save(model.state_dict(), "mobilenet_affectNet.pth")
        print("💾 Saved best model!")

print("Training Done!")
