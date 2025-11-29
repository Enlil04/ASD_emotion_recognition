import tensorflow as tf
from tensorflow.keras import layers, models, callbacks
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.utils import class_weight
import numpy as np
import os

# Config
IMG_SIZE = (224, 224)
BATCH_SIZE = 64
EPOCHS = 30  
NUM_CLASSES = 7

# 1. Setup Data Generators
train_datagen = ImageDataGenerator(
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

print("⏳ Loading Data...")
train_gen = train_datagen.flow_from_directory(
    'archive/train', 
    target_size=IMG_SIZE, 
    batch_size=BATCH_SIZE, 
    color_mode='rgb', 
    class_mode='categorical',
    shuffle=True
)

val_gen = val_datagen.flow_from_directory(
    'archive/test', 
    target_size=IMG_SIZE, 
    batch_size=BATCH_SIZE, 
    color_mode='rgb', 
    class_mode='categorical',
    shuffle=False
)

# 2. Compute Class Weights => This calculates which emotions are rare and tells the model to focus on them more.
class_weights = class_weight.compute_class_weight(
    class_weight='balanced',
    classes=np.unique(train_gen.classes),
    y=train_gen.classes
)
class_weights_dict = dict(enumerate(class_weights))
print(f"⚖️ Class Weights: {class_weights_dict}")

# 3. Build Model (MobileNetV3)
base_model = tf.keras.applications.MobileNetV3Small(
    input_shape=IMG_SIZE + (3,),
    include_top=False,
    weights='imagenet',
    minimalistic=True
)
base_model.trainable = True # Unfreeze specifically for better accuracy

# Fine-tune: Keep bottom layers frozen, train top layers
for layer in base_model.layers[:-20]:
    layer.trainable = False  # keep the lower 20 layers and
    



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

print(" Starting Training...")
history = model.fit(
    train_gen,
    epochs=EPOCHS,
    validation_data=val_gen,
    class_weight=class_weights_dict, # <--- CRITICAL LINE
    callbacks=[checkpoint, reduce_lr, early_stop]
)

print(" Model Saved as 'mobilenet_best.h5'")