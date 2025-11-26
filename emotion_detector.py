import cv2
import mediapipe as mp
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications import MobileNetV3Large
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from tensorflow.keras.models import Model

# --- 1. SETUP MODEL (Ideally, load your trained weights here) ---
def build_mobilenet_emotion_model():
    # We use MobileNetV3Large as the base
    # input_shape=(224, 224, 3) is standard for MobileNet
    base_model = MobileNetV3Large(input_shape=(224, 224, 3), include_top=False, weights='mobilenet_emotion.h5')
    
    # Add custom layers for Emotion Classification
    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(1024, activation='relu')(x)
    # 7 Output classes: Angry, Disgust, Fear, Happy, Sad, Surprise, Neutral
    predictions = Dense(7, activation='softmax')(x)
    
    model = Model(inputs=base_model.input, outputs=predictions)
    return model

# Initialize model
model = build_mobilenet_emotion_model()
# model.load_weights('your_trained_emotion_weights.h5') # <--- UNCOMMENT THIS AFTER TRAINING
print("MobileNetV3 Loaded!")

# Emotion Labels
EMOTIONS = ["Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"]

# --- 2. SETUP MEDIAPIPE ---
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # Flip and convert
    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width, _ = frame.shape

    # Process with MediaPipe
    results = face_mesh.process(rgb_frame)

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            
            # --- 3. DYNAMIC CROPPING ---
            # We need to find the bounding box of the face from the mesh
            x_min, y_min = width, height
            x_max, y_max = 0, 0
            
            for lm in face_landmarks.landmark:
                x, y = int(lm.x * width), int(lm.y * height)
                if x < x_min: x_min = x
                if x > x_max: x_max = x
                if y < y_min: y_min = y
                if y > y_max: y_max = y

            # Add some padding to the crop so we don't cut the chin/forehead
            padding = 20
            x_min = max(0, x_min - padding)
            y_min = max(0, y_min - padding)
            x_max = min(width, x_max + padding)
            y_max = min(height, y_max + padding)

            # Draw the bounding box for visualization
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)

            # --- 4. PREPARE INPUT FOR MOBILENET ---
            try:
                # Crop the face
                face_crop = frame[y_min:y_max, x_min:x_max]
                
                if face_crop.size != 0:
                    # Resize to 224x224 (MobileNet standard)
                    roi = cv2.resize(face_crop, (224, 224))
                    roi = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
                    roi = tf.keras.applications.mobilenet_v3.preprocess_input(roi)
                    roi = np.expand_dims(roi, axis=0) # Add batch dimension

                    # --- 5. PREDICT EMOTION ---
                    # Note: Without training, this prediction will be random/nonsense
                    prediction = model.predict(roi, verbose=0)
                    max_index = int(np.argmax(prediction))
                    emotion_label = EMOTIONS[max_index]
                    confidence = prediction[0][max_index]

                    # Display the emotion
                    text = f"{emotion_label} ({confidence*100:.1f}%)"
                    cv2.putText(frame, text, (x_min, y_min - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            except Exception as e:
                print(f"Error in processing: {e}")

    cv2.imshow('MobileNetV3 + MediaPipe', frame)

    if cv2.waitKey(5) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()