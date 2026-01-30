import cv2
import numpy as np
from collections import Counter

class VideoProcessor:
    def __init__(self, detector):
        self.detector = detector

    def process_session(self, file_path):
        cap = cv2.VideoCapture(file_path)
        
        if not cap.isOpened():
            return {"dominant_emotion": "Neutral", "confidence": 0}

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0: total_frames = 100
        
        # We want to analyze exactly 20 frames spread evenly
        num_samples = 20
        # Calculate the jump size (stride)
        stride = max(1, total_frames // num_samples)
        
        emotion_tally = []
        
        # --- OPTIMIZATION: JUMP instead of walking ---
        for i in range(0, total_frames, stride):
            # 1. Jump directly to the frame (Fast I/O)
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            
            if not ret:
                break
            
            try:
                # 2. CRITICAL FIX: Pass smooth=False
                # This treats every frame as a unique event, preventing "muddy" averaging
                emotion, conf, box, _ = self.detector.predict(frame, smooth=False)
                
                if box is not None:
                    # 3. FIX: Trust the detector's logic. 
                    # The detector ALREADY returns 'Neutral' if confidence is low.
                    # We don't need a second conflicting threshold check here.
                    emotion_tally.append(emotion)
            
            except Exception as e:
                print(f"⚠️ Frame processing error at {i}: {e}")

        cap.release()

        if not emotion_tally:
            return {"dominant_emotion": "Neutral", "confidence": 0}

        # Calculate final results
        counts = Counter(emotion_tally)
        most_common, count = counts.most_common(1)[0]
        
        confidence_score = round((count / len(emotion_tally)) * 100, 1)

        return {
            "dominant_emotion": str(most_common), 
            "confidence": float(confidence_score),
            "total_frames_analyzed": len(emotion_tally)
        }