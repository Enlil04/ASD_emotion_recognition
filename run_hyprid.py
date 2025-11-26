import cv2
import numpy as np
import mediapipe as mp
import tensorflow as tf

# 1. Load your trained MobileNetV3
model = tf.keras.models.load_model('mobilenet_emotion.h5')
emotions = ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']

# 2. Setup MediaPipe with IRIS enabled
mp_face_mesh = mp.solutions.face_mesh
# refine_landmarks=True is what activates the IRIS tracking model
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True, 
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Iris Indices (Left and Right Centers)
LEFT_IRIS_CENTER = 468
RIGHT_IRIS_CENTER = 473

cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    h, w, c = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # --- MODEL 1: MediaPipe Face Mesh (Geometry & Iris) ---
    results = face_mesh.process(rgb_frame)

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            
            # A. Get Iris (Gaze) Data
            mesh_points = np.array([np.multiply([p.x, p.y], [w, h]).astype(int) for p in face_landmarks.landmark])
            
            # Visualize the Iris Centers (The "Gaze" Tracker)
            (l_cx, l_cy) = mesh_points[LEFT_IRIS_CENTER]
            (r_cx, r_cy) = mesh_points[RIGHT_IRIS_CENTER]
            
            cv2.circle(frame, (l_cx, l_cy), 3, (0, 255, 255), -1, cv2.LINE_AA) # Yellow Dot on Left Eye
            cv2.circle(frame, (r_cx, r_cy), 3, (0, 255, 255), -1, cv2.LINE_AA) # Yellow Dot on Right Eye

            # B. Get Face Bounding Box for MobileNet
            # (Simple approximation using face mesh extents)
            x_min, x_max = min(mesh_points[:,0]), max(mesh_points[:,0])
            y_min, y_max = min(mesh_points[:,1]), max(mesh_points[:,1])
            
            # --- MODEL 2: MobileNetV3 (Emotion) ---
            try:
                # Crop the face
                face_roi = frame[y_min:y_max, x_min:x_max]
                if face_roi.size > 0:
                    # Preprocess for MobileNet (48x48, RGB)
                    roi_resized = cv2.resize(face_roi, (48, 48))
                    roi_rgb = cv2.cvtColor(roi_resized, cv2.COLOR_BGR2RGB) # Ensure 3 channels
                    roi_normalized = np.expand_dims(roi_rgb, axis=0) / 255.0

                    # Predict
                    prediction = model.predict(roi_normalized, verbose=0)
                    emotion_idx = np.argmax(prediction)
                    emotion_label = emotions[emotion_idx]
                    confidence = prediction[0][emotion_idx]

                    # Display Emotion Label
                    cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
                    cv2.putText(frame, f"{emotion_label} ({int(confidence*100)}%)", 
                                (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            except Exception as e:
                print(f"Crop Error: {e}")

    cv2.imshow('Hybrid: MobileNet Emotion + MediaPipe Iris', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()