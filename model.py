import tensorflow as tf
from tensorflow.keras import layers, models

def build_mobilenet_emotion_model(input_shape=(48, 48, 3), num_classes=7):
    # 1. Load the Base Model (MobileNetV3Small)
    # We use include_top=False to remove the "ImageNet" classifier
    # We use 'minimalistic' for extra speed on Android
    base_model = tf.keras.applications.MobileNetV3Small(
        input_shape=input_shape,
        include_top=False,
        weights='imagenet', # Start with knowledge of shapes/textures
        minimalistic=True
    )

    # 2. Freeze the base model (Optional: unfreeze later for fine-tuning)
    base_model.trainable = False 

    # 3. Add the Emotion Classification Head
    model = models.Sequential([
        base_model,
        layers.GlobalAveragePooling2D(),
        layers.Dense(128, activation='relu'),
        layers.Dropout(0.2), # Prevents overfitting
        layers.Dense(num_classes, activation='softmax') # 7 Emotions
    ])
    
    return model

if __name__ == "__main__":
    model = build_mobilenet_emotion_model()
    model.summary()
    print("✅ MobileNetV3 Emotion Model Built!")