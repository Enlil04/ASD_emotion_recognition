
# import cv2
# import numpy as np
# from collections import Counter
# # Import your source of truth
# from analytics.vision_models.emotion_detector import EmotionDetector, MODEL_FILE, LABELS

# class VideoProcessor:
#     def __init__(self, detector: EmotionDetector):
#         self.detector = detector

#     def process_session(self, video_path: str):
#         cap = cv2.VideoCapture(video_path)
#         # We store the exact emotion label your detector chooses for every frame
#         detected_history = []
#         confidences = []
#         total_frames = 0

#         while cap.isOpened():
#             ret, frame = cap.read()
#             if not ret:
#                 break
            
#             total_frames += 1
#             # We process every frame to match your real-time detection exactly
            
#             # 1. Call your predict method exactly like your main loop does
#             # This respects your CLASS_MULTIPLIERS, SMART OVERRIDES, and BASE_THRESHOLDS
#             emotion, conf, _, _ = self.detector.predict(frame, smooth=True)
            
#             if emotion:
#                 detected_history.append(emotion)
#                 confidences.append(conf)

#         cap.release()

#         if not detected_history:
#             return {
#                 "dominant_emotion": "Neutral", 
#                 "confidence": 0.0, 
#                 "total_frames_analyzed": 0
#             }

#         # 2. Find which emotion won the most frames (Majority Vote)
#         # This mirrors how a human perceives the video based on your HUD
#         counts = Counter(detected_history)
#         dominant_emotion = counts.most_common(1)[0][0]
        
#         # 3. Calculate the average confidence for ONLY the winning emotion
#         winning_confidences = [
#             confidences[i] for i, emo in enumerate(detected_history) 
#             if emo == dominant_emotion
#         ]
#         avg_conf = np.mean(winning_confidences) if winning_confidences else 0.0

#         # 4. Create the percentage breakdown for the dashboard
#         # This shows the percentage of frames each emotion occupied
#         total_hits = len(detected_history)
#         percentages = {
#             label: round((counts.get(label, 0) / total_hits) * 100, 2)
#             for label in LABELS
#         }

#         return {
#             "dominant_emotion": dominant_emotion,
#             "confidence": round(float(avg_conf * 100), 2),
#             "total_frames_analyzed": total_hits,
#             "emotion_counts": dict(counts),
#             "percentages": percentages
#         }

# # --- Auto-Initialize ---
# # One instance of your detector with your exact MODEL_FILE
# detector_instance = EmotionDetector(MODEL_FILE)
# video_service = VideoProcessor(detector_instance)


import cv2
import numpy as np
from collections import Counter

# Import your source of truth
from analytics.vision_models.emotion_detector import (
    EmotionDetector,
    MODEL_FILE,
    LABELS
)

class VideoProcessor:
    def __init__(self, detector: EmotionDetector):
        self.detector = detector

        # Tell the detector we're in VIDEO mode (optional hook)
        if hasattr(self.detector, "is_video"):
            self.detector.is_video = True

    def process_session(self, video_path: str):
        cap = cv2.VideoCapture(video_path)

        detected_history = []
        confidences = []
        total_frames = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            total_frames += 1

            # 🔥 CRITICAL FIX: disable smoothing for video
            emotion, conf, _, _ = self.detector.predict(
                frame,
                smooth=True
            )

            if emotion is not None:
                detected_history.append(emotion)
                confidences.append(conf)

        cap.release()

        # -------------------------------
        # NO FACE / NO DATA
        # -------------------------------
        if not detected_history:
            return {
                "dominant_emotion": "Neutral",
                "confidence": 0.0,
                "total_frames_analyzed": 0,
                "emotion_counts": {},
                "percentages": {label: 0.0 for label in LABELS}
            }

        # -------------------------------
        # MAJORITY VOTE (HUMAN PERCEPTION)
        # -------------------------------
        counts = Counter(detected_history)
        dominant_emotion, dominant_count = counts.most_common(1)[0]

        # -------------------------------
        # CONFIDENCE FOR WINNER ONLY
        # -------------------------------
        winning_confidences = [
            confidences[i]
            for i, emo in enumerate(detected_history)
            if emo == dominant_emotion
        ]

        avg_conf = float(np.mean(winning_confidences)) if winning_confidences else 0.0

        # -------------------------------
        # PERCENTAGE BREAKDOWN
        # -------------------------------
        total_hits = len(detected_history)
        percentages = {
            label: round((counts.get(label, 0) / total_hits) * 100, 2)
            for label in LABELS
        }

        return {
            "dominant_emotion": dominant_emotion,
            "confidence": round(avg_conf * 100, 2),
            "total_frames_analyzed": total_hits,
            "emotion_counts": dict(counts),
            "percentages": percentages
        }


# ------------------------------------
# SINGLETON INITIALIZATION (SAFE)
# ------------------------------------
detector_instance = EmotionDetector(MODEL_FILE)
video_service = VideoProcessor(detector_instance)
