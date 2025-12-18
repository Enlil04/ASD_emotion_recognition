import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight

import numpy as np
import os

# --- Configuration for Paths ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ANALYTICS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
DATASET_DIR = os.path.join(ANALYTICS_DIR,"dataset","archive_clean")

# --- CONFIG ---
IMG_SIZE = 224
BATCH_SIZE = 32
EPOCHS = 75
NUM_CLASSES = 8
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("Using device:", DEVICE)
if DEVICE == "cuda":
    print(f"CUDA device: {torch.cuda.get_device_name(0)}")

# -----------------------------------
# 1. Transforms (AffectNet correct)
# -----------------------------------

# train_transform is for data augmentation
train_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.RandomRotation(10), #might be to aggressive was 15 now 10
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.05),

    transforms.ToTensor(), # 1 convert to tensor
    # CRITICAL: Randomly erasing small parts forces the model to look at 
    # the whole face, not just one feature (like the mouth).
    # Great for when a hand covers part of the face.
    transforms.Normalize(mean=[0.485, 0.456, 0.406],std=[0.229, 0.224, 0.225]), # 2 normalize
    transforms.RandomErasing(p=0.1, scale=(0.02, 0.1)), # 3 randomly erase small parts
])

# cleans the images to make it like they came from camera
val_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# -----------------------------------
# 2. Main Logic Function
# -----------------------------------
def train_model():
    # --- 2. Datasets ---
    try:
        #loads the training dataset
        train_ds = datasets.ImageFolder(
            os.path.join(DATASET_DIR, "train"),
            transform=train_transform
        )
        #loads the testing dataset
        val_ds = datasets.ImageFolder(
            os.path.join(DATASET_DIR, "test"),
            transform=val_transform
        )
    except Exception as e:
        print(f"Error loading datasets. Check DATASET_DIR: {DATASET_DIR}")
        print(f"Details: {e}")
        return

    print(f"Train samples: {len(train_ds)}, Val samples: {len(val_ds)}")
    print("Train classes:", train_ds.classes)

    # Note: num_workers=0 (single process) is often safer on Windows to avoid freezing.
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0, pin_memory=True)

    # --- 3. Class Weights ---
    # pay attention to the rare emotions (still does not work)
    labels = train_ds.targets
    class_counts = np.bincount(labels)
    total_samples = len(labels)


    # weights = np.sqrt(total_samples / (len(class_counts) * class_counts)) // tried this but made it worse

#------------------------
    weights = compute_class_weight(
        class_weight='balanced',
        classes=np.unique(labels),
        y=labels
    )

# ------------------------
    class_weights = torch.tensor(weights, dtype=torch.float).to(DEVICE)
    print("Class weights device:", class_weights.device)

    # --- 4. Model (MobileNetV3 Small) ---
    model = models.mobilenet_v3_small(weights="IMAGENET1K_V1")
    # Correctly replace the final linear layer for 8 classes
    model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, NUM_CLASSES)
    model = model.to(DEVICE)
    print(f"Model moved to: {next(model.parameters()).device}")

    # Loss, Optimizer, and Scheduler
    #criterion measures how wrong the model is, by using class weights
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    #optimizer used to reduce the error
    #  [CHANGED THIS ] optimizer = optim.Adam(model.parameters(), lr=1e-4)
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    #start fast but slow down when getting closer to more accurate results
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

    # --- 5. Training Loop ---
    best_acc = 0.0

    for epoch in range(EPOCHS):
        print(f"--- Starting Epoch {epoch+1}/{EPOCHS} ---")
        model.train()
        total, correct, epoch_loss = 0, 0, 0

        for batch_idx, (images, labels) in enumerate(train_loader):
            # move images and labels to GPU so it can process them
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            #reset the previously learned info
            optimizer.zero_grad()
            #the model outputs its guess
            outputs = model(images)
            #check if the guess is correct by comparing it to the label
            loss = criterion(outputs, labels)
            #go backward to see what neuron made this mistake
            loss.backward()
            #try to correct the that mistake
            optimizer.step()

            epoch_loss += loss.item()
            _, preds = torch.max(outputs, 1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)

        train_acc = correct / total
        print(f"Epoch {epoch+1}/{EPOCHS} | Train Loss: {epoch_loss/len(train_loader):.4f} | Train Acc: {train_acc:.3f}")




        # Validation with detailed metrics
        model.eval()
        all_preds = []
        all_labels = []
        val_correct, val_total = 0, 0
        val_loss = 0.0

        with torch.no_grad():
            for images, labels_batch in val_loader:
                images, labels_batch = images.to(DEVICE), labels_batch.to(DEVICE)
                outputs = model(images)

                loss = criterion(outputs, labels_batch)
                val_loss += loss.item()

                
                _, preds = torch.max(outputs, 1)
                
                val_correct += (preds == labels_batch).sum().item()
                val_total += labels_batch.size(0)

                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels_batch.cpu().numpy())
                
        val_acc = val_correct / val_total
        avg_val_loss = val_loss / len(val_loader)
        print(f"Validation Loss: {avg_val_loss:.4f} | Validation Acc: {val_acc:.3f}")

       # val_acc = val_correct / val_total
        #print(f"Validation Acc: {val_acc:.3f}")

        # Detailed metrics every 5 epochs
        if (epoch + 1) % 5 == 0:
            print("\n" + "="*60)
            print("PER-CLASS PERFORMANCE:")
            print(classification_report(all_labels, all_preds, target_names=train_ds.classes, zero_division=0))
            print("="*60)

        scheduler.step()

        # Save best model
        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), "mobilenet_best_AffectNet.pth")
            print(f"✓ Saved new best model! Val Acc: {val_acc:.3f}")

    print("\nTraining Done! Best Validation Accuracy:", best_acc)

if __name__ == "__main__":
    train_model()
#         #Here we move to testing 
#         model.eval()
#         val_correct, val_total = 0, 0
#         with torch.no_grad():
#             for images, labels in val_loader:
#                 images, labels = images.to(DEVICE), labels.to(DEVICE)
                
#                 outputs = model(images)
#                 _, preds = torch.max(outputs, 1)
#                 val_correct += (preds == labels).sum().item()
#                 val_total += labels.size(0)

#         val_acc = val_correct / val_total
#         print(f"Validation Acc: {val_acc:.3f}")

        
#         scheduler.step()

#         # Save best model
#         if val_acc > best_acc:
#             best_acc = val_acc
#             torch.save(model.state_dict(), "mobilenet_best_AffectNet.pth") 
#             print(" Saved new best model: mobilenet_best_AffectNet.pth!")

#     print("Training Done!")



# if __name__ == "__main__":
#     train_model()