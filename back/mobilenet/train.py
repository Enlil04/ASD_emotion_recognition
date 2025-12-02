import tensorflow as tf # The core deep learning framework.
# from tensorflow.keras import layers, models, callbacks
from keras import layers, models, callbacks # Modules for building the network structure, training utilities, and controlling the training process.
# from tensorflow.keras.preprocessing.image import ImageDataGenerator 
from keras.preprocessing.image import ImageDataGenerator # A utility for augmenting images and feeding them efficiently to the model.
from sklearn.utils import class_weight # Used for calculating class weights to handle imbalanced datasets.
import numpy as np
import os

# Config
IMG_SIZE = (224, 224)
BATCH_SIZE = 64 # The number of samples processed before the model's parameters are updated.
EPOCHS = 30  
NUM_CLASSES = 7 # e.g., Angry, Disgust, Fear, Happy, Sad, Surprise, Neutral

# 1. Setup Data Generators with stronger augmentation
train_datagen = ImageDataGenerator(   # Defines the pre-processing and augmentation pipeline for the training data.
    rescale=1./255,
    rotation_range=15,
    width_shift_range=0.1,
    height_shift_range=0.1,
    shear_range=0.1,
    zoom_range=0.1,
    horizontal_flip=True,
    fill_mode='nearest'
)

val_datagen = ImageDataGenerator(rescale=1./255) 
# Defines the pre-processing for the validation/test data. Critically, it only includes rescale=1./255 
# because validation data must be evaluated on its original, unaltered form to get an accurate performance measure.

print("⏳ Loading Data...")
train_gen = train_datagen.flow_from_directory(
    'archive/train', 
    target_size=IMG_SIZE, 
    batch_size=BATCH_SIZE, 
    color_mode='rgb', 
    class_mode='categorical',
    shuffle=True  # shuffle=True (Used for Training Data)
)

val_gen = val_datagen.flow_from_directory(
    'archive/test', 
    target_size=IMG_SIZE, 
    batch_size=BATCH_SIZE, 
    color_mode='rgb', 
    class_mode='categorical',
    shuffle=False # shuffle=False (Used for Validation/Test Data) The images are loaded and evaluated in the same, sequential order
) 

# 2. Compute Class Weights (The Fix for "Only Happy")
# This calculates which emotions are rare and tells the model to focus on them more.
class_weights = class_weight.compute_class_weight(
    class_weight='balanced', 
    classes=np.unique(train_gen.classes), 
    y=train_gen.classes
)
class_weights_dict = dict(enumerate(class_weights))
print(f"⚖️ Class Weights: {class_weights_dict}")

# 3. Build Model (MobileNetV3)
base_model = tf.keras.applications.MobileNetV3Small( #Imports a pre-trained, efficient Convolutional Neural Network (CNN) architecture.
    input_shape=IMG_SIZE + (3,), 
    include_top=False, # Excludes the final classification layer to allow customization.
    weights='imagenet',
    minimalistic=True
)
base_model.trainable = True # Unfreeze specifically for better accuracy

# Fine-tune: Keep bottom layers frozen, train top layers
for layer in base_model.layers[:-20]:
    layer.trainable = False
    

model = models.Sequential([
    base_model, #extracts deep features from images (edges, shapes, textures).
    layers.GlobalAveragePooling2D(), #Converts the 2D feature maps from the base model into a single vector
    layers.Dense(256, activation='relu'), # relu helps the model learn complex non-linear patterns.
    layers.Dropout(0.4), # Higher dropout to prevent overfitting, Forces the network to generalize.
    layers.Dense(NUM_CLASSES, activation='softmax') #Final classification layer., Softmax outputs a probability distribution over all classes.
])

# 4. Compile with a lower learning rate
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001), # Slower, more careful learning, adam Very important when fine-tuning pre-trained models.
    loss='categorical_crossentropy', #Used for multi-class classification when labels are one-hot encoded.
    metrics=['accuracy'] #Tracks training accuracy and validation accuracy.
)

# 5. Callbacks (The Safety Nets)
checkpoint = callbacks.ModelCheckpoint(
    'mobilenet_best.h5', 
    monitor='val_accuracy', 
    save_best_only=True, 
    mode='max', 
    verbose=1
) 
#Saves the model only when validation accuracy improves
# Prevents losing the best version during training
# ✔ Ensures you always keep the highest-performing model
# ✔ Stored in the file: mobilenet_best.h5


reduce_lr = callbacks.ReduceLROnPlateau(
    monitor='val_loss', 
    factor=0.5, 
    patience=3, 
    min_lr=1e-6, 
    verbose=1
)
# ✔ If the model stops improving for 3 epochs → reduce learning rate by 50%
# ✔ Prevents training from getting stuck
# ✔ Gradually makes learning more precise

early_stop = callbacks.EarlyStopping(
    monitor='val_loss', 
    patience=8, 
    restore_best_weights=True
)
# ✔ Stops training automatically when the model stops improving
# ✔ Prevents overfitting
# ✔ Saves time by avoiding unnecessary epochs
# ✔ Restores the best weights (not the last ones)

print("🚀 Starting Robust Training...")
history = model.fit(
    train_gen,
    epochs=EPOCHS,
    validation_data=val_gen,
    class_weight=class_weights_dict, # <--- CRITICAL LINE
    callbacks=[checkpoint, reduce_lr, early_stop]
)

print("✅ Best Model Saved as 'mobilenet_best.h5'")

# import torch
# import torch.nn as nn
# import torch.optim as optim
# from torch.utils.data import DataLoader
# from torchvision import datasets, transforms, models
# from sklearn.utils.class_weight import compute_class_weight
# import numpy as np

# # CONFIG
# IMG_SIZE = 224
# BATCH_SIZE = 64
# EPOCHS = 30
# NUM_CLASSES = 7
# DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# # 1. Transforms (augmentation)
# train_transform = transforms.Compose([
#     transforms.Resize((IMG_SIZE, IMG_SIZE)),
#     transforms.RandomRotation(15),
#     transforms.RandomHorizontalFlip(),
#     transforms.ColorJitter(brightness=0.2, contrast=0.2),
#     transforms.ToTensor(),
# ])

# val_transform = transforms.Compose([
#     transforms.Resize((IMG_SIZE, IMG_SIZE)),
#     transforms.ToTensor(),
# ])

# # 2. Datasets
# train_ds = datasets.ImageFolder("archive/train", transform=train_transform)
# val_ds = datasets.ImageFolder("archive/test", transform=val_transform)

# train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
# val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)

# # 3. Class Weights
# labels = train_ds.targets
# class_weights = compute_class_weight("balanced", classes=np.unique(labels), y=labels)
# class_weights = torch.tensor(class_weights, dtype=torch.float).to(DEVICE)

# # 4. Model (MobileNetV3)
# model = models.mobilenet_v3_small(weights="IMAGENET1K_V1")
# model.classifier[3] = nn.Linear(model.classifier[3].in_features, NUM_CLASSES)
# model = model.to(DEVICE)

# criterion = nn.CrossEntropyLoss(weight=class_weights)
# optimizer = optim.Adam(model.parameters(), lr=1e-4)

# # 5. Training Loop
# best_acc = 0.0

# for epoch in range(EPOCHS):
#     model.train()
#     total, correct, epoch_loss = 0, 0, 0

#     for images, labels in train_loader:
#         images, labels = images.to(DEVICE), labels.to(DEVICE)

#         optimizer.zero_grad()
#         outputs = model(images)
#         loss = criterion(outputs, labels)
#         loss.backward()
#         optimizer.step()

#         epoch_loss += loss.item()
#         _, preds = torch.max(outputs, 1)
#         correct += (preds == labels).sum().item()
#         total += labels.size(0)

#     train_acc = correct / total
#     print(f"Epoch {epoch+1}/{EPOCHS} | Train Acc: {train_acc:.3f}")

#     # Validation
#     model.eval()
#     val_correct, val_total = 0, 0
#     with torch.no_grad():
#         for images, labels in val_loader:
#             images, labels = images.to(DEVICE), labels.to(DEVICE)
#             outputs = model(images)
#             _, preds = torch.max(outputs, 1)
#             val_correct += (preds == labels).sum().item()
#             val_total += labels.size(0)

#     val_acc = val_correct / val_total
#     print(f"Validation Acc: {val_acc:.3f}")

#     # Save best model
#     if val_acc > best_acc:
#         best_acc = val_acc
#         torch.save(model, "mobilenet_best.pt")
#         print("💾 Saved best model!")

# print("Training Done!")
