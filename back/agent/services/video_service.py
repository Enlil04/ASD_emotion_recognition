import sys
import os
from collections import Counter
# --- PATH FIXER START ---
# 1. Get the folder where this file is (/back/agent/services)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Get the parent folder (/back/agent)
agent_dir = os.path.dirname(current_dir)

# 3. Get the GRANDPARENT folder (/back) -> THIS IS WHAT WE NEED
back_dir = os.path.dirname(agent_dir)

# 4. Add the grandparent (/back) to Python's search path
if back_dir not in sys.path:
    sys.path.append(back_dir)

# Optional: Keep agent_dir too if you import things from 'agent'
if agent_dir not in sys.path:
    sys.path.append(agent_dir)

print(f"🔧 Path Fixer: Added {back_dir} to sys.path")
# --- PATH FIXER END ---

# NOW your imports will work:
import cv2
import numpy as np
# This will now find 'back/analytics' because we added 'back' to the path
from analytics.vision_models.emotion_detector import EmotionDetector, MODEL_FILE, LABELS


class VideoProcessor:
    def __init__(self, detector):
        self.detector = detector
        # Hook for PyTorch models that need to know they are processing video
        if hasattr(self.detector, "is_video"):
            self.detector.is_video = True

    def process_session(self, video_path: str):
        """
        Analyzes a video file frame-by-frame and returns the dominant emotion.
        """
        # 1. Verify Video
        if not os.path.exists(video_path):
            print(f"❌ Error: Video file not found at {video_path}")
            return self._empty_result()

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"❌ Error: Could not open video source.")
            return self._empty_result()

        detected_history = []
        confidences = []
        total_frames = 0

        # 2. Process Loop
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            total_frames += 1
            
            # Optimization: Skip every 2nd frame if video is high FPS (optional)
            # if total_frames % 2 != 0: continue

            # Predict
            # smooth=True helps stabilize the jittery predictions in video
            emotion, conf, _, _ = self.detector.predict(frame, smooth=True)

            if emotion:
                detected_history.append(emotion)
                confidences.append(conf)

        cap.release()

        # 3. Aggregate Results
        if not detected_history:
            return self._empty_result()

        # Majority Vote
        counts = Counter(detected_history)
        dominant_emotion, _ = counts.most_common(1)[0]

        # Average Confidence (of the dominant emotion only)
        winning_confs = [c for i, c in enumerate(confidences) if detected_history[i] == dominant_emotion]
        avg_conf = float(np.mean(winning_confs)) if winning_confs else 0.0

        # Percentages
        total_hits = len(detected_history)
        percentages = {
            label: round((counts.get(label, 0) / total_hits) * 100, 1)
            for label in LABELS
        }

        return {
            "dominant_emotion": dominant_emotion,
            "confidence": round(avg_conf * 100, 1),
            "total_frames_analyzed": total_hits,
            "emotion_counts": dict(counts),
            "percentages": percentages
        }

    def _empty_result(self):
        return {
            "dominant_emotion": "Neutral",
            "confidence": 0.0,
            "total_frames_analyzed": 0,
            "emotion_counts": {},
            "percentages": {l: 0.0 for l in LABELS}
        }

# --- 2. INITIALIZE SERVICE ---
print(f"🔌 Loading AI Model from: {MODEL_FILE}")

# Ensure the file actually exists before passing it to PyTorch
if not os.path.exists(MODEL_FILE):
    # Fallback to check relative path if running from root
    if os.path.exists(f"back/agent/{MODEL_FILE}"):
        MODEL_FILE = f"back/agent/{MODEL_FILE}"
    else:
        print(f"❌ CRITICAL ERROR: Model file not found at: {MODEL_FILE}")
        print("Please check MODEL_FILE path in emotion_detector.py")

# Initialize
detector_instance = EmotionDetector(MODEL_FILE)
video_service = VideoProcessor(detector_instance)

print("✅ Video Service Online")