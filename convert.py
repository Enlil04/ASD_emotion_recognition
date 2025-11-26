import tensorflow as tf

# Load your trained model
model = tf.keras.models.load_model('mobilenet_emotion.h5')

# Convert
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT] # Optimize for mobile size
tflite_model = converter.convert()

# Save
with open('emotion_model.tflite', 'wb') as f:
    f.write(tflite_model)

print("✅ Converted to emotion_model.tflite (Ready for Android!)")