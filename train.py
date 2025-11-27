import tensorflow as tf # The core deep learning framework.
from tensorflow.keras import layers, models, callbacks # Modules for building the network structure, training utilities, and controlling the training process.
from tensorflow.keras.preprocessing.image import ImageDataGenerator # A utility for augmenting images and feeding them efficiently to the model.
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
    base_model,
    layers.GlobalAveragePooling2D(),
    layers.Dense(256, activation='relu'), # Increased density
    layers.Dropout(0.4), # Higher dropout to prevent overfitting
    layers.Dense(NUM_CLASSES, activation='softmax')
])

# 4. Compile with a lower learning rate
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001), # Slower, more careful learning
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# 5. Callbacks (The Safety Nets)
checkpoint = callbacks.ModelCheckpoint(
    'mobilenet_best.h5', 
    monitor='val_accuracy', 
    save_best_only=True, 
    mode='max', 
    verbose=1
)

reduce_lr = callbacks.ReduceLROnPlateau(
    monitor='val_loss', 
    factor=0.5, 
    patience=3, 
    min_lr=1e-6, 
    verbose=1
)

early_stop = callbacks.EarlyStopping(
    monitor='val_loss', 
    patience=8, 
    restore_best_weights=True
)

print("🚀 Starting Robust Training...")
history = model.fit(
    train_gen,
    epochs=EPOCHS,
    validation_data=val_gen,
    class_weight=class_weights_dict, # <--- CRITICAL LINE
    callbacks=[checkpoint, reduce_lr, early_stop]
)

print("✅ Best Model Saved as 'mobilenet_best.h5'")