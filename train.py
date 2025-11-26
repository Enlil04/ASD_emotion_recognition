import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV3Large
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.optimizers import Adam

# --- CONFIGURATION ---
TRAIN_DIR = 'archive/train'  # <--- UPDATE THIS PATH
TEST_DIR = 'archive/test'    # <--- UPDATE THIS PATH
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 30
NUM_CLASSES = 7  # Angry, Disgust, Fear, Happy, Sad, Surprise, Neutral

# --- 1. DATA GENERATORS (Augmentation) ---
# We use the native MobileNet preprocessing function
train_datagen = ImageDataGenerator(
    preprocessing_function=tf.keras.applications.mobilenet_v3.preprocess_input,
    rotation_range=20,       # Rotate head slightly
    width_shift_range=0.2,   # Shift left/right
    height_shift_range=0.2,  # Shift up/down
    shear_range=0.2,
    zoom_range=0.2,          # Zoom in/out
    horizontal_flip=True,    # Mirror face
    fill_mode='nearest'
)

test_datagen = ImageDataGenerator(
    preprocessing_function=tf.keras.applications.mobilenet_v3.preprocess_input
)

print("Loading Training Data...")
train_generator = train_datagen.flow_from_directory(
    TRAIN_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    shuffle=True
)

print("Loading Validation Data...")
validation_generator = test_datagen.flow_from_directory(
    TEST_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    shuffle=False
)

# --- 2. BUILD MODEL ---
# Load MobileNetV3 without the top layer (include_top=False)
base_model = MobileNetV3Large(
    weights='imagenet', 
    include_top=False, 
    input_shape=(224, 224, 3)
)

# Freeze the base model layers (so we don't destroy ImageNet weights)
base_model.trainable = False 

# Add our custom Emotion Classification head
x = base_model.output
x = GlobalAveragePooling2D()(x)
x = Dense(1024, activation='relu')(x)
x = Dropout(0.5)(x) # Dropout helps prevent overfitting
predictions = Dense(NUM_CLASSES, activation='softmax')(x)

model = Model(inputs=base_model.input, outputs=predictions)

# Compile
model.compile(
    optimizer=Adam(learning_rate=0.001),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# --- 3. TRAIN ---
# Callbacks help stop training if the model stops improving
callbacks = [
    EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True),
    ModelCheckpoint('best_emotion_model.h5', monitor='val_accuracy', save_best_only=True)
]

print("Starting Training...")
history = model.fit(
    train_generator,
    epochs=EPOCHS,
    validation_data=validation_generator,
    callbacks=callbacks
)

# --- 4. OPTIONAL: FINE TUNING ---
# Unfreeze the last few layers of MobileNet for better accuracy
print("Fine-tuning...")
base_model.trainable = True
# Freeze all layers except the last 20
for layer in base_model.layers[:-20]:
    layer.trainable = False

model.compile(
    optimizer=Adam(learning_rate=1e-5), # Lower learning rate for fine-tuning
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

history_fine = model.fit(
    train_generator,
    epochs=10, # Train for a few more epochs
    validation_data=validation_generator
)

# --- 5. SAVE FINAL MODEL ---
model.save('final_emotion_model.h5')
print("Model saved as final_emotion_model.h5")