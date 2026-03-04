# # Use your preferred import style:
# # If you decided to use back.analytics...
# # from analytics.vision_models.emotion_detector import EmotionDetector, MODEL_FILE, LABELS

# import sys
# import os
# import cv2
# import numpy as np
# from typing import Optional, Tuple, Dict, Any

# # --- PATH FIXER START ---
# current_dir = os.path.dirname(os.path.abspath(__file__))
# agent_dir = os.path.dirname(current_dir)
# back_dir = os.path.dirname(agent_dir)

# if back_dir not in sys.path:
#     sys.path.append(back_dir)
# if agent_dir not in sys.path:
#     sys.path.append(agent_dir)
# # --- PATH FIXER END ---

# # NOW this will work perfectly:
# from analytics.vision_models.emotion_detector import (
#     EmotionDetector,
#     MODEL_FILE,
#     LABELS
# )

# # ... (rest of your ImageEmotionService code)

# class ImageEmotionService:
#     def __init__(self):
#         self.detector = EmotionDetector(MODEL_FILE)

#         # OpenCV Haar fallback (ships with opencv-python)
#         haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
#         self.haar = cv2.CascadeClassifier(haar_path)

#     # ---------- Public API ----------
#     def analyze_image_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
#         frame_bgr = self._decode_bgr(image_bytes)
#         if frame_bgr is None:
#             return self._no_face("Invalid image decode", debug={"stage": "decode"})

#         frame_bgr = self._normalize_size(frame_bgr)

#         # Try 1: normal RGB
#         result = self._predict_on_frame(frame_bgr, attempt="rgb")
#         if result["face_detected"]:
#             return result

#         # Try 2: enhanced RGB (helps dark/harsh lighting)
#         enhanced_bgr = self._enhance_bgr(frame_bgr)
#         result = self._predict_on_frame(enhanced_bgr, attempt="enhanced_rgb")
#         if result["face_detected"]:
#             return result

#         # Try 3: fallback bbox via Haar -> crop -> predict (normal)
#         bbox = self._haar_face_bbox(frame_bgr)
#         if bbox is not None:
#             crop_bgr = self._crop_expand(frame_bgr, bbox, expand=0.35)
#             result = self._predict_on_frame(crop_bgr, attempt="haar_crop_rgb", debug_extra={"bbox": bbox})
#             if result["face_detected"]:
#                 return result

#             # Try 4: fallback bbox + enhanced crop
#             crop_bgr2 = self._enhance_bgr(crop_bgr)
#             result = self._predict_on_frame(crop_bgr2, attempt="haar_crop_enhanced_rgb", debug_extra={"bbox": bbox})
#             if result["face_detected"]:
#                 return result

#         # Still no face
#         dbg = {"stage": "all_attempts_failed"}
#         if bbox is not None:
#             dbg["haar_bbox"] = bbox
#         return self._no_face("No face detected. Try better lighting and keep face centered.", debug=dbg)

#     # ---------- Core prediction ----------
#     def _predict_on_frame(self, frame_bgr: np.ndarray, attempt: str, debug_extra: Optional[dict] = None) -> Dict[str, Any]:
#         # EmotionDetector/MediaPipe usually expects RGB uint8
#         rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
#         rgb = np.ascontiguousarray(rgb, dtype=np.uint8)

#         # Avoid any leftover temporal smoothing state
#         if hasattr(self.detector, "prob_buffer"):
#             try:
#                 self.detector.prob_buffer.clear()
#             except Exception:
#                 pass

#         emotion, conf, _bbox, probs = self.detector.predict(rgb, smooth=False)

#         debug = {
#             "attempt": attempt,
#             "w": int(frame_bgr.shape[1]),
#             "h": int(frame_bgr.shape[0]),
#             "mean_brightness": float(frame_bgr.mean()),
#         }
#         if debug_extra:
#             debug.update(debug_extra)

#         if emotion is None or probs is None:
#             return self._no_face("Detector returned no face", debug=debug)

#         confidence_pct = round(float(conf) * 100.0, 2)

#         raw_breakdown = {
#             LABELS[i]: round(float(probs[i]) * 100.0, 2)
#             for i in range(len(LABELS))
#         }

#         # Optional UX-friendly rule: if it's not confident, say "Uncertain"
#         top1_label, top1_val = max(raw_breakdown.items(), key=lambda kv: kv[1])
#         top2_val = sorted(raw_breakdown.values(), reverse=True)[1] if len(raw_breakdown) > 1 else 0.0

#         dominant = top1_label
#         if top1_val < 60.0 or (top1_val - top2_val) < 15.0:
#             dominant = "Uncertain"

#         return {
#             "dominant_emotion": dominant,
#             "confidence": top1_val,          # top1 probability in %
#             "raw_breakdown": raw_breakdown,
#             "face_detected": True,
#             "debug": debug,
#         }

#     # ---------- Utilities ----------
#     def _decode_bgr(self, image_bytes: bytes) -> Optional[np.ndarray]:
#         arr = np.frombuffer(image_bytes, dtype=np.uint8)
#         frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
#         return frame

#     def _normalize_size(self, bgr: np.ndarray) -> np.ndarray:
#         h, w = bgr.shape[:2]

#         # Up-scale tiny images (helps face detectors)
#         if w < 320:
#             scale = 320 / w
#             bgr = cv2.resize(bgr, (320, int(h * scale)))

#         # Down-scale huge images (stability + speed)
#         h, w = bgr.shape[:2]
#         if w > 900:
#             scale = 900 / w
#             bgr = cv2.resize(bgr, (900, int(h * scale)))

#         return bgr

#     def _enhance_bgr(self, bgr: np.ndarray) -> np.ndarray:
#         # Mild luminance equalization (fast + helps shadows)
#         ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
#         y, cr, cb = cv2.split(ycrcb)
#         y = cv2.equalizeHist(y)
#         ycrcb = cv2.merge([y, cr, cb])
#         return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

#     def _haar_face_bbox(self, bgr: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
#         gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
#         gray = cv2.equalizeHist(gray)

#         faces = self.haar.detectMultiScale(
#             gray,
#             scaleFactor=1.1,
#             minNeighbors=5,
#             minSize=(60, 60)
#         )
#         if len(faces) == 0:
#             return None

#         # Pick largest face
#         faces = sorted(faces, key=lambda r: r[2] * r[3], reverse=True)
#         x, y, w, h = faces[0]
#         return int(x), int(y), int(w), int(h)

#     def _crop_expand(self, bgr: np.ndarray, bbox: Tuple[int, int, int, int], expand: float = 0.3) -> np.ndarray:
#         x, y, w, h = bbox
#         H, W = bgr.shape[:2]

#         pad_w = int(w * expand)
#         pad_h = int(h * expand)

#         x1 = max(0, x - pad_w)
#         y1 = max(0, y - pad_h)
#         x2 = min(W, x + w + pad_w)
#         y2 = min(H, y + h + pad_h)

#         crop = bgr[y1:y2, x1:x2]
#         return crop if crop.size else bgr

#     def _no_face(self, msg: str, debug: Optional[dict] = None) -> Dict[str, Any]:
#         return {
#             "dominant_emotion": "not sure",
#             "confidence": 0.0,
#             "raw_breakdown": {},
#             "face_detected": False,
#             "message": msg,
#             "debug": debug or {},
#         }


# image_service = ImageEmotionService()

import cv2
import numpy as np
import sys
import os

# --- PATH FIXER START ---
current_dir = os.path.dirname(os.path.abspath(__file__))
agent_dir = os.path.dirname(current_dir)
back_dir = os.path.dirname(agent_dir)

if back_dir not in sys.path:
    sys.path.append(back_dir)
if agent_dir not in sys.path:
    sys.path.append(agent_dir)
# --- PATH FIXER END ---

# NOW this will work perfectly:
from analytics.vision_models.emotion_detector import (
    EmotionDetector,
    MODEL_FILE,
    LABELS
)


class ImageEmotionService:
    def __init__(self, detector):
        self.detector = detector

    def check_lighting(self, face_crop) -> tuple:
        """
        Calculates the average brightness of the face crop.
        Returns a tuple: (Status Message, Boolean Is_OK)
        """
        # Convert to grayscale to evaluate brightness
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        
        # Get the average pixel intensity (0 is black, 255 is pure white)
        brightness = np.mean(gray)
        
        # Adjust these thresholds if your emulator is naturally darker/brighter
        if brightness < 40:
            return "Image is too dark", False
        elif brightness > 220:
            return "Image is washed out (too bright)", False
            
        return "Lighting is okay", True

    def analyze_image_bytes(self, image_bytes: bytes) -> dict:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None: return {"face_detected": False}

        # 1. Clear buffer
        if hasattr(self.detector, "prob_buffer"):
            self.detector.prob_buffer.clear()

        # 2. Extract face landmarks first to get the face crop
        # (We use a lightweight check before full inference)
        emotion, conf, box, probs, _ = self.detector.predict(frame, smooth=False)

        if box is None:
            return {"dominant_emotion": "Neutral", "face_detected": False, "message": "No face found"}

        # 3. LIGHTING CHECK on the face crop
        x1, y1, x2, y2 = box
        face_crop = frame[y1:y2, x1:x2]
        
        if face_crop.size > 0:
            status, is_ok = self.check_lighting(face_crop)
            if not is_ok:
                return {
                    "dominant_emotion": "Neutral",
                    "face_detected": True,
                    "status": "bad_lighting",
                    "message": status
                }

        # 4. SUCCESS
        return {
            "dominant_emotion": emotion,
            "confidence": round(float(conf) * 100, 2),
            "face_detected": True,
            "status": "success"
        }