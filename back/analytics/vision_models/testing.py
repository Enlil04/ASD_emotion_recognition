# back/analytics/vision_models/testing.py
import cv2
from emotion_detector import EmotionDetector # Assuming you have this class

def test_vision_stream():
    print("--- Starting Vision Test (Press 'q' to quit) ---")
    
    # 1. Initialize the model
    detector = EmotionDetector() 
    cap = cv2.VideoCapture(0) # 0 is usually the default webcam

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 2. Run detection (Simulated or Real)
        # In a real scenario, this returns "happy", "sad", etc.
        emotion_result = detector.detect_latest_frame(frame) 
        
        # 3. Visual Feedback
        cv2.putText(frame, f"Emotion: {emotion_result}", (50, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.imshow('Vision Test', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_vision_stream()