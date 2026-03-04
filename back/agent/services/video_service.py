# import cv2
# import numpy as np
# from collections import Counter
# from analytics.vision_models.emotion_detector import EmotionDetector, LABELS

import cv2
import numpy as np
from collections import Counter
from analytics.vision_models.emotion_detector import LABELS

class VideoProcessor:
    def __init__(self, detector):
        self.detector = detector

    def process_session(self, video_path: str) -> dict:
        cap = cv2.VideoCapture(video_path)
        
        # 1. Detect Rotation (Critical for Mobile)
        # Some OpenCV builds support CAP_PROP_ORIENTATION_META
        rotation = cap.get(cv2.CAP_PROP_ORIENTATION_META)
        
        detected_history = []
        confidences = []

        if hasattr(self.detector, "prob_buffer"):
            self.detector.prob_buffer.clear()

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            # 2. MANUALLY ROTATE IF NEEDED
            # If the video is sideways, MediaPipe WILL fail.
            if rotation == 90:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            elif rotation == 180:
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            elif rotation == 270:
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

            # 3. Predict
            emotion, conf, box, _, _ = self.detector.predict(frame, smooth=True)
            
            if emotion and box: # Only count if a face was actually seen
                detected_history.append(emotion)
                confidences.append(float(conf))

        cap.release()

        if not detected_history:
            return {"dominant_emotion": "Neutral", "face_detected": False}

        # 4. Aggregate
        counts = Counter(detected_history)
        dom_emotion = counts.most_common(1)[0][0]
        avg_conf = np.mean(confidences) if confidences else 0.0

        return {
            "dominant_emotion": dom_emotion,
            "confidence": round(avg_conf * 100, 2),
            "face_detected": True,
            "percentages": {l: round((counts.get(l,0)/len(detected_history))*100, 2) for l in LABELS}
        }
# import cv2
# import numpy as np
# from collections import Counter

# # Import your source of truth
# from analytics.vision_models.emotion_detector import (
#     EmotionDetector,
#     MODEL_FILE,
#     LABELS
# )

# class VideoProcessor:
#     def __init__(self, detector: EmotionDetector):
#         self.detector = detector

#         # Tell the detector we're in VIDEO mode (optional hook)
#         if hasattr(self.detector, "is_video"):
#             self.detector.is_video = True

#     def process_session(self, video_path: str):
#         cap = cv2.VideoCapture(video_path)

#         detected_history = []
#         confidences = []
#         total_frames = 0

#         while cap.isOpened():
#             ret, frame = cap.read()
#             if not ret:
#                 break

#             total_frames += 1

#             # 🔥 CRITICAL FIX: disable smoothing for video
#             emotion, conf, _, _ = self.detector.predict(
#                 frame,
#                 smooth=False
#             )

#             if emotion is not None:
#                 detected_history.append(emotion)
#                 confidences.append(conf)

#         cap.release()

#         # -------------------------------
#         # NO FACE / NO DATA
#         # -------------------------------
#         if not detected_history:
#             return {
#                 "dominant_emotion": "Neutral",
#                 "confidence": 0.0,
#                 "total_frames_analyzed": 0,
#                 "emotion_counts": {},
#                 "percentages": {label: 0.0 for label in LABELS}
#             }

#         # -------------------------------
#         # MAJORITY VOTE (HUMAN PERCEPTION)
#         # -------------------------------
#         counts = Counter(detected_history)
#         dominant_emotion, dominant_count = counts.most_common(1)[0]

#         # -------------------------------
#         # CONFIDENCE FOR WINNER ONLY
#         # -------------------------------
#         winning_confidences = [
#             confidences[i]
#             for i, emo in enumerate(detected_history)
#             if emo == dominant_emotion
#         ]

#         avg_conf = float(np.mean(winning_confidences)) if winning_confidences else 0.0

#         # -------------------------------
#         # PERCENTAGE BREAKDOWN
#         # -------------------------------
#         total_hits = len(detected_history)
#         percentages = {
#             label: round((counts.get(label, 0) / total_hits) * 100, 2)
#             for label in LABELS
#         }

#         return {
#             "dominant_emotion": dominant_emotion,
#             "confidence": round(avg_conf * 100, 2),
#             "total_frames_analyzed": total_hits,
#             "emotion_counts": dict(counts),
#             "percentages": percentages
#         }


# # ------------------------------------
# # SINGLETON INITIALIZATION (SAFE)
# # ------------------------------------
# detector_instance = EmotionDetector(MODEL_FILE)
# video_service = VideoProcessor(detector_instance)
