import cv2
import numpy as np
import tensorflow as tf
import mediapipe as mp

# Load Model
interpreter = tf.lite.Interpreter(model_path="emotion_model.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Emotions Label Map (Standard FER-2013 order)
emotions = ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']

# Setup MediaPipe Face Detection (Fastest way to get the crop)
mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(min_detection_confidence=0.5)

cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    # 1. Detect Faces
    results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    if results.detections:
        for detection in results.detections:
            # Get Bounding Box
            bboxC = detection.location_data.relative_bounding_box
            ih, iw, _ = frame.shape
            x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), \
                         int(bboxC.width * iw), int(bboxC.height * ih)

            # 2. Crop & Preprocess for MobileNet
            if w > 0 and h > 0:
                face_roi = frame[y:y+h, x:x+w]
                try:
                    face_roi = cv2.resize(face_roi, (48, 48))
                    face_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2RGB) # Ensure RGB
                    face_input = np.expand_dims(face_roi, axis=0).astype(np.float32) / 255.0

                    # 3. Predict with TFLite
                    interpreter.set_tensor(input_details[0]['index'], face_input)
                    interpreter.invoke()
                    output_data = interpreter.get_tensor(output_details[0]['index'])
                    
                    emotion_idx = np.argmax(output_data)
                    emotion_label = emotions[emotion_idx]
                    confidence = output_data[0][emotion_idx]

                    # 4. Draw
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, f"{emotion_label} ({int(confidence*100)}%)", 
                                (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                except Exception as e:
                    pass

    cv2.imshow('MobileNetV3 Emotion Test', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()