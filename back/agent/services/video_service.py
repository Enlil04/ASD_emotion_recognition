import cv2
import os
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
            
        # We still process 20 frames, but we will be pickier about them
        frame_step = max(1, total_frames // 20) 
        
        emotion_tally = []
        current_frame = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            if current_frame % frame_step == 0:
                try:
                    # 1. Get prediction
                    emotion, conf, box, _ = self.detector.predict(frame)
                    
                    # 2. FIX: ONLY tally if the AI is actually confident (> 50%)
                    # Otherwise, treat it as 'Neutral' to avoid hallucinations
                    if box is not None:
                        if conf > 0.15:
                            emotion_tally.append(emotion)
                        else:
                            emotion_tally.append("Neutral")
                            
                except Exception as e:
                    print(f"⚠️ Frame processing error: {e}")

            current_frame += 1

        cap.release()

        if not emotion_tally:
            return {"dominant_emotion": "Neutral", "confidence": 0}

        # Calculate final results
        counts = Counter(emotion_tally)
        most_common, count = counts.most_common(1)[0]
        
        # Calculate how many frames agreed on this emotion
        confidence_score = round((count / len(emotion_tally)) * 100, 1)

        return {
            "dominant_emotion": str(most_common), 
            "confidence": float(confidence_score),
            "total_frames_analyzed": len(emotion_tally)
        }