import cv2
import os
from collections import Counter

class VideoProcessor:
    def __init__(self, detector):
        self.detector = detector

    # FIX: Remove 'async'. This is a blocking CPU task.
    def process_session(self, file_path):
        cap = cv2.VideoCapture(file_path)
        
        # Safety Check: If video is corrupt or path is wrong
        if not cap.isOpened():
            print(f"❌ Error: Could not open video at {file_path}")
            return {"dominant_emotion": "Neutral", "confidence": 0}

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Safety: Handle cases where header info is missing (returns 0)
        if total_frames <= 0:
            total_frames = 100 # Fallback assumption
            
        # Process ~20 frames total to speed it up
        frame_step = max(1, total_frames // 20) 
        
        emotion_tally = []
        current_frame = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: 
                break
            
            # Analyze specific frames
            if current_frame % frame_step == 0:
                try:
                    # Depending on your model, this might return different values. 
                    # Ensure your detector.predict returns exactly 4 values.
                    emotion, conf, box, _ = self.detector.predict(frame)
                    
                    if box is not None:
                        emotion_tally.append(emotion)
                except Exception as e:
                    print(f"⚠️ Frame processing error: {e}")

            current_frame += 1

        cap.release()

        # Logic to find dominant emotion
        if not emotion_tally:
            return {"dominant_emotion": "Neutral", "confidence": 0}

        counts = Counter(emotion_tally)
        most_common, count = counts.most_common(1)[0]
        confidence = round((count / len(emotion_tally)) * 100, 1)

        return {"dominant_emotion": most_common, "confidence": confidence}