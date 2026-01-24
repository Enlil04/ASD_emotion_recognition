# import cv2
# import mediapipe as mp
# import torch
# import torch.nn as nn
# from torchvision import models, transforms
# from PIL import Image
# from collections import deque
# import numpy as np

# # ==============================
# # CONFIGURATION
# # ==============================
# MODEL_FILE = "mobilenet_v3_large_affectnet7_.pth"
# SMOOTHING_WINDOW = 6

# LABELS = ['Anger', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

# CLASS_MULTIPLIERS = {
#     "Anger": 1.0, 
#     "Disgust": 1.0, 
#     "Fear": 1.0,
#     "Happy": 2.0,       # ⬇️ Lowered slightly (Geometry does the heavy lifting now)
#     "Neutral": 5.0,     # ⬇️ Lowered slightly to let emotions shine
#     "Sad": 0.5,         # ⬆️ Restored to decent level (Geometry will block it if smiling)
#     "Surprise": 0.5 
# }

# BASE_THRESHOLDS = {
#     "Anger": 0.15, "Disgust": 0.40, "Fear": 0.15,
#     "Happy": 0.15, "Neutral": 0.20, "Sad": 0.20, "Surprise": 0.50
# }

# # =========================================================
# # EMOTION DETECTOR CLASS
# # =========================================================
# class EmotionDetector:
#     def __init__(self, model_path):
#         self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#         self.use_fp16 = self.device.type == "cuda"

#         # ------------------------------
#         # MODEL
#         # ------------------------------
#         self.model = models.mobilenet_v3_large(weights=None)
#         in_features = self.model.classifier[0].in_features

#         self.model.classifier = nn.Sequential(
#             nn.Linear(in_features, 1024),
#             nn.Hardswish(),
#             nn.Dropout(0.5),
#             nn.Linear(1024, len(LABELS))
#         )

#         try:
#             state = torch.load(model_path, map_location=self.device)
#             self.model.load_state_dict(state)
#         except Exception as e:
#             print(f"❌ Error loading model: {e}")
#             exit()

#         self.model.to(self.device).eval()
#         if self.use_fp16:
#             self.model.half()

#         print(f"✅ Model loaded on {self.device}")

#         # ------------------------------
#         # FACE MESH
#         # ------------------------------
#         self.mp_face_mesh = mp.solutions.face_mesh
#         self.face_mesh = self.mp_face_mesh.FaceMesh(
#             max_num_faces=1,
#             refine_landmarks=False,
#             min_detection_confidence=0.5,
#             min_tracking_confidence=0.5
#         )

#         self.transform = transforms.Compose([
#             transforms.Resize((224, 224)),
#             transforms.ToTensor(),
#             transforms.Normalize(
#                 mean=[0.485, 0.456, 0.406],
#                 std=[0.229, 0.224, 0.225]
#             )
#         ])

#         self.prob_buffer = deque(maxlen=SMOOTHING_WINDOW)
#         self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

#     def get_geometry_data(self, landmarks, w, h):
#         """
#         Calculates geometric features to correct the AI.
#         """
#         # --- INDICES ---
#         # Top Lip: 13, Bottom Lip: 14
#         # Left Corner: 61, Right Corner: 291
        
#         # 1. Openness Ratio (Vertical / Horizontal)
#         top = np.array([landmarks[13].x * w, landmarks[13].y * h])
#         bottom = np.array([landmarks[14].x * w, landmarks[14].y * h])
#         left = np.array([landmarks[61].x * w, landmarks[61].y * h])
#         right = np.array([landmarks[291].x * w, landmarks[291].y * h])

#         vertical_dist = np.linalg.norm(top - bottom)
#         horizontal_dist = np.linalg.norm(left - right)
        
#         ratio = vertical_dist / horizontal_dist if horizontal_dist > 0 else 0

#         # 2. Smile Curve (Corner Height vs Center Height)
#         # In images, Y increases downwards.
#         # Smile: Corners are HIGHER (smaller Y) than Center (larger Y)
#         # Sad: Corners are LOWER (larger Y) than Center
        
#         corner_avg_y = (left[1] + right[1]) / 2
#         center_avg_y = (top[1] + bottom[1]) / 2

#         # Negative = Smile (Corners above center)
#         # Positive = Frown (Corners below center)
#         curve_val = corner_avg_y - center_avg_y

#         # Normalize curve value by face width to be scale-invariant
#         normalized_curve = curve_val / horizontal_dist if horizontal_dist > 0 else 0

#         return ratio, normalized_curve

#     def predict(self, frame):
#         h, w, _ = frame.shape
#         rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#         result = self.face_mesh.process(rgb)

#         if not result.multi_face_landmarks:
#             self.prob_buffer.clear()
#             return None, 0.0, None, None

#         # --- BOUNDING BOX ---
#         landmarks = result.multi_face_landmarks[0].landmark
#         x_coords = [lm.x for lm in landmarks]
#         y_coords = [lm.y for lm in landmarks]
#         x1 = int(min(x_coords) * w)
#         y1 = int(min(y_coords) * h)
#         x2 = int(max(x_coords) * w)
#         y2 = int(max(y_coords) * h)
        
#         pad = 20
#         x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
#         x2, y2 = min(w, x2 + pad), min(h, y2 + pad)

#         face_roi = frame[y1:y2, x1:x2]
#         if face_roi.size == 0: return None, 0.0, None, None

#         # --- GET GEOMETRY ---
#         mouth_openness, smile_curve = self.get_geometry_data(landmarks, w, h)

#         # --- INFERENCE ---
#         gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
#         gray = self.clahe.apply(gray)
#         face_color = cv2.merge([gray, gray, gray])
        
#         img = Image.fromarray(face_color)
#         img_t = self.transform(img).unsqueeze(0).to(self.device)
#         if self.use_fp16: img_t = img_t.half()

#         with torch.no_grad():
#             logits = self.model(img_t)
#             probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

#         self.prob_buffer.append(probs)
#         avg_probs = np.mean(self.prob_buffer, axis=0)

#         # --- WEIGHTS ---
#         weighted = avg_probs.copy()
#         for i, label in enumerate(LABELS):
#             weighted[i] *= CLASS_MULTIPLIERS[label]

#         # =========================================================
#         # 🧠 GEOMETRY VETO SYSTEM (The Fix)
#         # =========================================================
#         temp_idx = np.argmax(weighted)
#         temp_emotion = LABELS[temp_idx]

#         # 1. THE SMILE CHECK (Sad vs Happy)
#         # If smile_curve is Negative, corners are UP. This is a smile.
#         # Threshold: -0.02 (Slight upward curve)
#         if smile_curve < -0.01: 
#             # We are smiling. Sadness is BANNED.
#             weighted[LABELS.index("Sad")] *= 0.0
            
#             # If the model thought it was Sad or Disgust, Force Happy
#             if temp_emotion in ["Sad", "Disgust", "Neutral"]:
#                 weighted[LABELS.index("Happy")] *= 10.0
#                 weighted[LABELS.index("Neutral")] *= 0.2

#         # 2. THE SURPRISE CHECK (Open Mouth)
#         if temp_emotion == "Surprise":
#             # If mouth is closed, it cannot be Surprise.
#             if mouth_openness < 0.25:
#                 weighted[LABELS.index("Surprise")] *= 0.0
#                 weighted[LABELS.index("Neutral")] *= 5.0

#         # 3. DISGUST/ANGER CLEANUP
#         # If smiling, clear these negatives
#         if smile_curve < -0.02:
#              weighted[LABELS.index("Disgust")] *= 0.0
#              weighted[LABELS.index("Anger")] *= 0.0

#         # =========================================================

#         total = weighted.sum()
#         final_probs = weighted / total if total > 0 else weighted
#         idx = np.argmax(final_probs)
#         emotion = LABELS[idx]
#         conf = final_probs[idx]

#         if conf < BASE_THRESHOLDS.get(emotion, 0.2):
#             emotion = "Neutral"

#         return emotion, conf, (x1, y1, x2, y2), final_probs

#     def draw_hud(self, frame, display_probs):
#         if display_probs is None: return
#         start_x, start_y, gap = 10, 20, 25
#         overlay = frame.copy()
#         cv2.rectangle(overlay, (0, 0), (280, 200), (0, 0, 0), -1)
#         cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

#         for i, label in enumerate(LABELS):
#             prob = display_probs[i]
#             y = start_y + i * gap
#             color = (255, 255, 255)
#             if label == "Happy": color = (0, 255, 255)
#             elif label == "Surprise": color = (255, 100, 0)
#             elif label == "Sad": color = (255, 0, 0)
            
#             cv2.putText(frame, f"{label}: {int(prob*100)}%", (start_x, y), 
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
#             cv2.rectangle(frame, (start_x + 100, y - 10), 
#                          (start_x + 100 + int(150 * prob), y), color, -1)

# # =========================================================
# # MAIN
# # =========================================================
# if __name__ == "__main__":
#     cap = cv2.VideoCapture(0)
#     detector = EmotionDetector(MODEL_FILE)

#     while True:
#         ret, frame = cap.read()
#         if not ret: break

#         emotion, conf, box, probs = detector.predict(frame)
#         detector.draw_hud(frame, probs)

#         if box:
#             x1, y1, x2, y2 = box
#             color = (0, 255, 0)
#             if emotion == "Happy": color = (0, 255, 255)
#             elif emotion == "Sad": color = (255, 0, 0)
#             elif emotion == "Surprise": color = (255, 0, 255)
            
#             cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
#             cv2.putText(frame, f"{emotion} {int(conf*100)}%", (x1, y1-10), 
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

#         cv2.imshow("Emotion AI", frame)
#         if cv2.waitKey(1) & 0xFF == 27: break

#     cap.release()
#     cv2.destroyAllWindows()












# # very close
# import cv2
# import mediapipe as mp
# import torch
# import torch.nn as nn
# from torchvision import models, transforms
# from PIL import Image
# from collections import deque
# import numpy as np

# # ==============================
# # CONFIGURATION
# # ==============================
# MODEL_FILE = "mobilenet_v3_large_affectnet7_.pth"
# SMOOTHING_WINDOW = 6

# LABELS = ['Anger', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

# # --- TUNING SECTION ---
# CLASS_MULTIPLIERS = {
#     "Anger": 1.0, 
#     "Disgust": 0.7, 
#     "Fear": 1.0,
#     "Happy": 9.0,       # ⬆️ High to catch smiles
#     "Neutral": 15.0,    # ⬆️ High to prevent jitter
#     "Sad": 0.1,         # ⬇️ LOWERED: Was 0.27, now 0.1 (Stops it from overpowering)
#     "Surprise": 0.5 
# }

# BASE_THRESHOLDS = {
#     "Anger": 0.15, "Disgust": 0.40, "Fear": 0.15,
#     "Happy": 0.05, "Neutral": 0.15, "Sad": 0.25, "Surprise": 0.55
# }

# # =========================================================
# # EMOTION DETECTOR CLASS
# # =========================================================
# class EmotionDetector:
#     def __init__(self, model_path):
#         self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#         self.use_fp16 = self.device.type == "cuda"

#         # ------------------------------
#         # MODEL
#         # ------------------------------
#         self.model = models.mobilenet_v3_large(weights=None)
#         in_features = self.model.classifier[0].in_features

#         self.model.classifier = nn.Sequential(
#             nn.Linear(in_features, 1024),
#             nn.Hardswish(),
#             nn.Dropout(0.5),
#             nn.Linear(1024, len(LABELS))
#         )

#         try:
#             state = torch.load(model_path, map_location=self.device)
#             self.model.load_state_dict(state)
#         except Exception as e:
#             print(f"❌ Error loading model: {e}")
#             exit()

#         self.model.to(self.device).eval()
#         if self.use_fp16:
#             self.model.half()

#         print(f"✅ Model loaded on {self.device}")

#         # ------------------------------
#         # FACE MESH
#         # ------------------------------
#         self.mp_face_mesh = mp.solutions.face_mesh
#         self.face_mesh = self.mp_face_mesh.FaceMesh(
#             max_num_faces=1,
#             refine_landmarks=False,
#             min_detection_confidence=0.5,
#             min_tracking_confidence=0.5
#         )

#         self.transform = transforms.Compose([
#             transforms.Resize((224, 224)),
#             transforms.ToTensor(),
#             transforms.Normalize(
#                 mean=[0.485, 0.456, 0.406],
#                 std=[0.229, 0.224, 0.225]
#             )
#         ])

#         self.prob_buffer = deque(maxlen=SMOOTHING_WINDOW)
#         self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

#     def get_mouth_ratio(self, landmarks, w, h):
#         # Top: 13, Bottom: 14, Left: 61, Right: 291
#         top = np.array([landmarks[13].x * w, landmarks[13].y * h])
#         bottom = np.array([landmarks[14].x * w, landmarks[14].y * h])
#         left = np.array([landmarks[61].x * w, landmarks[61].y * h])
#         right = np.array([landmarks[291].x * w, landmarks[291].y * h])

#         vertical_dist = np.linalg.norm(top - bottom)
#         horizontal_dist = np.linalg.norm(left - right)

#         if horizontal_dist == 0: return 0
#         return vertical_dist / horizontal_dist

#     def predict(self, frame):
#         h, w, _ = frame.shape
#         rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#         result = self.face_mesh.process(rgb)

#         if not result.multi_face_landmarks:
#             self.prob_buffer.clear()
#             return None, 0.0, None, None

#         # --- EXTRACT BOUNDING BOX ---
#         landmarks = result.multi_face_landmarks[0].landmark
#         x_coords = [lm.x for lm in landmarks]
#         y_coords = [lm.y for lm in landmarks]
#         x1 = int(min(x_coords) * w)
#         y1 = int(min(y_coords) * h)
#         x2 = int(max(x_coords) * w)
#         y2 = int(max(y_coords) * h)

#         pad = 20
#         x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
#         x2, y2 = min(w, x2 + pad), min(h, y2 + pad)

#         face_roi = frame[y1:y2, x1:x2]
#         if face_roi.size == 0: return None, 0.0, None, None

#         mouth_ratio = self.get_mouth_ratio(landmarks, w, h)

#         # --- PREPROCESSING ---
#         gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
#         gray = self.clahe.apply(gray)
#         face_color = cv2.merge([gray, gray, gray])
        
#         img = Image.fromarray(face_color)
#         img_t = self.transform(img).unsqueeze(0).to(self.device)
#         if self.use_fp16: img_t = img_t.half()

#         # --- INFERENCE ---
#         with torch.no_grad():
#             logits = self.model(img_t)
#             probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

#         self.prob_buffer.append(probs)
#         avg_probs = np.mean(self.prob_buffer, axis=0)

#         # --- APPLY WEIGHTS ---
#         weighted = avg_probs.copy()
#         for i, label in enumerate(LABELS):
#             weighted[i] *= CLASS_MULTIPLIERS[label]

#         # =========================================================
#         # 🧠 SMART OVERRIDE LOGIC
#         # =========================================================
#         temp_idx = np.argmax(weighted)
#         temp_emotion = LABELS[temp_idx]
        
#         # 1. FIX: SAD OVERPOWERING NEUTRAL
#         # If model thinks "Sad", but Neutral is reasonably high, default to Neutral
#         # Sadness usually has a very distinct look; if the model is "unsure", it's usually Neutral.
#         if temp_emotion == "Sad" and avg_probs[LABELS.index("Neutral")] > 0.15:
#             weighted[LABELS.index("Sad")] *= 0.2
#             weighted[LABELS.index("Neutral")] *= 2.0

#         # 2. FIX: SMILE READING AS SAD
#         # Smiling creates nasolabial folds (lines) that AI confuses with sadness.
#         # If Predicted="Sad" but there is even a 2% trace of "Happy", it is a Smile.
#         if temp_emotion == "Sad" and avg_probs[LABELS.index("Happy")] > 0.02:
#             weighted[LABELS.index("Sad")] *= 0.1  # Kill Sad
#             weighted[LABELS.index("Happy")] *= 10.0 # Force Happy

#         # 3. FIX: SURPRISE WITH CLOSED MOUTH
#         if temp_emotion == "Surprise" and mouth_ratio < 0.25:
#             if avg_probs[LABELS.index("Happy")] > 0.02:
#                 weighted[LABELS.index("Surprise")] *= 0.0
#                 weighted[LABELS.index("Happy")] *= 5.0
#             else:
#                 weighted[LABELS.index("Surprise")] *= 0.0
#                 weighted[LABELS.index("Neutral")] *= 5.0

#         # 4. FIX: DISGUST AS SMILE
#         if temp_emotion == "Disgust" and avg_probs[LABELS.index("Happy")] > 0.1:
#             weighted[LABELS.index("Happy")] *= 3.0
#             weighted[LABELS.index("Disgust")] *= 0.1
#         # =========================================================

#         total = weighted.sum()
#         final_probs = weighted / total if total > 0 else weighted
#         idx = np.argmax(final_probs)
#         emotion = LABELS[idx]
#         conf = final_probs[idx]

#         if conf < BASE_THRESHOLDS.get(emotion, 0.2):
#             emotion = "Neutral"

#         return emotion, conf, (x1, y1, x2, y2), final_probs

#     def draw_hud(self, frame, display_probs):
#         if display_probs is None: return
#         start_x, start_y, gap = 10, 20, 25
#         overlay = frame.copy()
#         cv2.rectangle(overlay, (0, 0), (280, 200), (0, 0, 0), -1)
#         cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

#         for i, label in enumerate(LABELS):
#             prob = display_probs[i]
#             y = start_y + i * gap
#             color = (255, 255, 255)
#             if label == "Happy": color = (0, 255, 255)
#             elif label == "Surprise": color = (255, 100, 0)
#             elif label == "Sad": color = (255, 0, 0)
            
#             cv2.putText(frame, f"{label}: {int(prob*100)}%", (start_x, y), 
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
#             cv2.rectangle(frame, (start_x + 100, y - 10), 
#                          (start_x + 100 + int(150 * prob), y), color, -1)

# # =========================================================
# # MAIN
# # =========================================================
# if __name__ == "__main__":
#     cap = cv2.VideoCapture(0)
#     detector = EmotionDetector(MODEL_FILE)

#     while True:
#         ret, frame = cap.read()
#         if not ret: break

#         emotion, conf, box, probs = detector.predict(frame)
#         detector.draw_hud(frame, probs)

#         if box:
#             x1, y1, x2, y2 = box
#             color = (0, 255, 0)
#             if emotion == "Happy": color = (0, 255, 255)
#             elif emotion == "Sad": color = (255, 0, 0)
#             elif emotion == "Surprise": color = (255, 0, 255)
            
#             cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
#             cv2.putText(frame, f"{emotion} {int(conf*100)}%", (x1, y1-10), 
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

#         cv2.imshow("Emotion AI", frame)
#         if cv2.waitKey(1) & 0xFF == 27: break

#     cap.release()
#     cv2.destroyAllWindows()


#OPTION 2

import cv2
import mediapipe as mp
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
from collections import deque
import numpy as np

# ==============================
# CONFIGURATION
# ==============================
MODEL_FILE = "mobilenet_v3_large_affectnet7_.pth"
SMOOTHING_WINDOW = 6

LABELS = ['Anger', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

# --- CLASS WEIGHTS ---
CLASS_MULTIPLIERS = {
    "Anger": 1.0,
    "Disgust": 0.1,
    "Fear": 1.0,
    "Happy": 12.0,      # boosted
    "Neutral": 11.0,    # reduced from 15
    "Sad": 0.094,
    "Surprise": 0.55
}

BASE_THRESHOLDS = {
    "Anger": 0.15, "Disgust": 0.40, "Fear": 0.15,
    "Happy": 0.05, "Neutral": 0.15, "Sad": 0.25, "Surprise": 0.55
}

# =========================================================
# EMOTION DETECTOR
# =========================================================
class EmotionDetector:
    def __init__(self, model_path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.use_fp16 = self.device.type == "cuda"

        # ------------------------------
        # MODEL
        # ------------------------------
        self.model = models.mobilenet_v3_large(weights=None)
        in_features = self.model.classifier[0].in_features

        self.model.classifier = nn.Sequential(
            nn.Linear(in_features, 1024),
            nn.Hardswish(),
            nn.Dropout(0.5),
            nn.Linear(1024, len(LABELS))
        )

        state = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(state)
        self.model.to(self.device).eval()
        if self.use_fp16:
            self.model.half()

        print(f"✅ Model loaded on {self.device}")

        # ------------------------------
        # MEDIAPIPE FACE MESH
        # ------------------------------
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # ------------------------------
        # TRANSFORM
        # ------------------------------
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

        self.prob_buffer = deque(maxlen=SMOOTHING_WINDOW)
        self.clahe = cv2.createCLAHE(2.0, (8, 8))

    # =========================================================
    # GEOMETRY HELPERS
    # =========================================================
    def mouth_open_ratio(self, lm, w, h):
        top = np.array([lm[13].x * w, lm[13].y * h])
        bot = np.array([lm[14].x * w, lm[14].y * h])
        left = np.array([lm[61].x * w, lm[61].y * h])
        right = np.array([lm[291].x * w, lm[291].y * h])

        vert = np.linalg.norm(top - bot)
        horiz = np.linalg.norm(left - right)
        return vert / horiz if horiz > 0 else 0

    def smile_width_ratio(self, lm, w, h):
        mouth_l = np.array([lm[61].x * w, lm[61].y * h])
        mouth_r = np.array([lm[291].x * w, lm[291].y * h])
        jaw_l = np.array([lm[234].x * w, lm[234].y * h])
        jaw_r = np.array([lm[454].x * w, lm[454].y * h])

        mouth_w = np.linalg.norm(mouth_l - mouth_r)
        face_w = np.linalg.norm(jaw_l - jaw_r)
        return mouth_w / face_w if face_w > 0 else 0

    # =========================================================
    # PREDICTION
    # =========================================================
    def predict(self, frame):
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self.face_mesh.process(rgb)

        if not res.multi_face_landmarks:
            self.prob_buffer.clear()
            return None, 0.0, None, None

        lm = res.multi_face_landmarks[0].landmark

        # --- FACE BOUNDING BOX ---
        xs = [p.x for p in lm]
        ys = [p.y for p in lm]
        x1, y1 = int(min(xs) * w), int(min(ys) * h)
        x2, y2 = int(max(xs) * w), int(max(ys) * h)

        pad = 20
        x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
        x2, y2 = min(w, x2 + pad), min(h, y2 + pad)

        face = frame[y1:y2, x1:x2]
        if face.size == 0:
            return None, 0.0, None, None

        # --- GEOMETRY ---
        mouth_open = self.mouth_open_ratio(lm, w, h)
        smile_width = self.smile_width_ratio(lm, w, h)

        # --- PREPROCESS ---
        gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
        gray = self.clahe.apply(gray)
        face_3c = cv2.merge([gray, gray, gray])

        img = Image.fromarray(face_3c)
        img_t = self.transform(img).unsqueeze(0).to(self.device)
        if self.use_fp16:
            img_t = img_t.half()

        # --- INFERENCE ---
        with torch.no_grad():
            logits = self.model(img_t)
            probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

        self.prob_buffer.append(probs)
        avg = np.mean(self.prob_buffer, axis=0)

        weighted = avg.copy()
        for i, label in enumerate(LABELS):
            weighted[i] *= CLASS_MULTIPLIERS[label]

        temp_idx = np.argmax(weighted)
        temp_emotion = LABELS[temp_idx]

        # =========================================================
        # SMART OVERRIDES
        # =========================================================

        # Sad vs Neutral
        if temp_emotion == "Sad" and avg[LABELS.index("Neutral")] > 0.15:
            weighted[LABELS.index("Sad")] *= 0.2
            weighted[LABELS.index("Neutral")] *= 2.0

        # Sad vs Happy (CNN confusion)
        if temp_emotion == "Sad" and avg[LABELS.index("Happy")] > 0.02:
            weighted[LABELS.index("Sad")] *= 0.1
            weighted[LABELS.index("Happy")] *= 8.0

        # Surprise with closed mouth
        if temp_emotion == "Surprise" and mouth_open < 0.25:
            weighted[LABELS.index("Surprise")] *= 0.0
            weighted[LABELS.index("Happy")] *= 3.0

        # Disgust as smile
        if temp_emotion == "Disgust" and avg[LABELS.index("Happy")] > 0.1:
            weighted[LABELS.index("Disgust")] *= 0.1
            weighted[LABELS.index("Happy")] *= 3.0

        # 🔥 CLOSED-MOUTH SMILE FIX
        if temp_emotion == "Sad" and smile_width > 0.42:
            weighted[LABELS.index("Sad")] *= 0.05
            weighted[LABELS.index("Happy")] *= 12.0

        # =========================================================

        total = weighted.sum()
        final_probs = weighted / total if total > 0 else weighted
        idx = np.argmax(final_probs)
        emotion = LABELS[idx]
        conf = final_probs[idx]

        if conf < BASE_THRESHOLDS.get(emotion, 0.2):
            emotion = "Neutral"

        return emotion, conf, (x1, y1, x2, y2), final_probs

    # =========================================================
    # HUD
    # =========================================================
    def draw_hud(self, frame, probs):
        if probs is None:
            return
        for i, label in enumerate(LABELS):
            y = 25 + i * 22
            cv2.putText(
                frame,
                f"{label}: {int(probs[i]*100)}%",
                (10, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255,255,255),
                1
            )


# =========================================================
# MAIN LOOP
# =========================================================
if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    detector = EmotionDetector(MODEL_FILE)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        emotion, conf, box, probs = detector.predict(frame)
        detector.draw_hud(frame, probs)

        if box:
            x1, y1, x2, y2 = box
            color = (0,255,0)
            if emotion == "Happy": color = (0,255,255)
            elif emotion == "Sad": color = (255,0,0)
            elif emotion == "Surprise": color = (255,0,255)

            cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
            cv2.putText(
                frame,
                f"{emotion} {int(conf*100)}%",
                (x1, y1-10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                color,
                2
            )

        cv2.imshow("Emotion AI", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()






# OPTION 1 worse

# import cv2
# import mediapipe as mp
# import torch
# import torch.nn as nn
# from torchvision import models, transforms
# from PIL import Image
# from collections import deque
# import numpy as np

# # ==============================
# # CONFIGURATION
# # ==============================
# MODEL_FILE = "mobilenet_v3_large_affectnet7_.pth"
# SMOOTHING_WINDOW = 6

# LABELS = ['Anger', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

# # --- TUNING SECTION ---
# CLASS_MULTIPLIERS = {
#     "Anger": 1.0, 
#     "Disgust": 1.0, 
#     "Fear": 1.0,
#     "Happy": 2.0,       # Reduced from 9.0 (Let geometry do the heavy lifting)
#     "Neutral": 8.0,     # Reduced from 15.0 to allow real emotions to pop
#     "Sad": 1.0,         # Reset to 1.0 (We will filter it via logic instead of suppressing)
#     "Surprise": 1.0 
# }

# BASE_THRESHOLDS = {
#     "Anger": 0.15, "Disgust": 0.40, "Fear": 0.15,
#     "Happy": 0.15, "Neutral": 0.25, "Sad": 0.25, "Surprise": 0.40
# }

# # =========================================================
# # EMOTION DETECTOR CLASS
# # =========================================================
# class EmotionDetector:
#     def __init__(self, model_path):
#         self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#         self.use_fp16 = self.device.type == "cuda"

#         # ------------------------------
#         # MODEL
#         # ------------------------------
#         self.model = models.mobilenet_v3_large(weights=None)
#         in_features = self.model.classifier[0].in_features

#         self.model.classifier = nn.Sequential(
#             nn.Linear(in_features, 1024),
#             nn.Hardswish(),
#             nn.Dropout(0.5),
#             nn.Linear(1024, len(LABELS))
#         )

#         try:
#             state = torch.load(model_path, map_location=self.device)
#             self.model.load_state_dict(state)
#         except Exception as e:
#             print(f"❌ Error loading model: {e}")
#             # For testing without model file, comment out exit
#             # exit() 
#             pass

#         self.model.to(self.device).eval()
#         if self.use_fp16:
#             self.model.half()

#         print(f"✅ Model loaded on {self.device}")

#         # ------------------------------
#         # FACE MESH
#         # ------------------------------
#         self.mp_face_mesh = mp.solutions.face_mesh
#         self.face_mesh = self.mp_face_mesh.FaceMesh(
#             max_num_faces=1,
#             refine_landmarks=False,
#             min_detection_confidence=0.5,
#             min_tracking_confidence=0.5
#         )

#         self.transform = transforms.Compose([
#             transforms.Resize((224, 224)),
#             transforms.ToTensor(),
#             transforms.Normalize(
#                 mean=[0.485, 0.456, 0.406],
#                 std=[0.229, 0.224, 0.225]
#             )
#         ])

#         self.prob_buffer = deque(maxlen=SMOOTHING_WINDOW)
#         self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

#     def get_mouth_dims(self, landmarks, w, h):
#         """
#         Returns aspect ratio (openness) and curvature (smile degree).
#         """
#         # Top Lip Bottom: 13, Bottom Lip Top: 14
#         # Left Corner: 61, Right Corner: 291
        
#         top = np.array([landmarks[13].x * w, landmarks[13].y * h])
#         bottom = np.array([landmarks[14].x * w, landmarks[14].y * h])
#         left = np.array([landmarks[61].x * w, landmarks[61].y * h])
#         right = np.array([landmarks[291].x * w, landmarks[291].y * h])

#         # 1. Openness Ratio
#         vertical_dist = np.linalg.norm(top - bottom)
#         horizontal_dist = np.linalg.norm(left - right)
#         ratio = vertical_dist / horizontal_dist if horizontal_dist > 0 else 0

#         # 2. Curvature (Smile Check)
#         # Calculate average height (y) of the corners
#         corners_y_avg = (left[1] + right[1]) / 2
#         # Calculate center height (y) of the mouth (landmark 13/14 avg)
#         center_y_avg = (top[1] + bottom[1]) / 2
        
#         # In image coords, Y increases downwards. 
#         # If corners are HIGHER than center, corners_y will be SMALLER than center_y.
#         # Positive curvature = Smile (Corners higher than center)
#         # Negative curvature = Frown (Corners lower than center)
#         curvature = center_y_avg - corners_y_avg
        
#         # Normalize curvature by face width to be scale-invariant
#         curvature_norm = curvature / horizontal_dist if horizontal_dist > 0 else 0

#         return ratio, curvature_norm

#     def predict(self, frame):
#         h, w, _ = frame.shape
#         rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#         result = self.face_mesh.process(rgb)

#         if not result.multi_face_landmarks:
#             self.prob_buffer.clear()
#             return None, 0.0, None, None

#         # --- EXTRACT BOUNDING BOX ---
#         landmarks = result.multi_face_landmarks[0].landmark
#         x_coords = [lm.x for lm in landmarks]
#         y_coords = [lm.y for lm in landmarks]
#         x1 = int(min(x_coords) * w)
#         y1 = int(min(y_coords) * h)
#         x2 = int(max(x_coords) * w)
#         y2 = int(max(y_coords) * h)

#         pad = 20
#         x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
#         x2, y2 = min(w, x2 + pad), min(h, y2 + pad)

#         face_roi = frame[y1:y2, x1:x2]
#         if face_roi.size == 0: return None, 0.0, None, None

#         # --- GEOMETRIC FEATURES ---
#         mouth_ratio, mouth_curve = self.get_mouth_dims(landmarks, w, h)

#         # --- PREPROCESSING ---
#         gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
#         gray = self.clahe.apply(gray)
#         face_color = cv2.merge([gray, gray, gray])
        
#         img = Image.fromarray(face_color)
#         img_t = self.transform(img).unsqueeze(0).to(self.device)
#         if self.use_fp16: img_t = img_t.half()

#         # --- INFERENCE ---
#         with torch.no_grad():
#             logits = self.model(img_t)
#             probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

#         self.prob_buffer.append(probs)
#         avg_probs = np.mean(self.prob_buffer, axis=0)

#         # --- APPLY WEIGHTS ---
#         weighted = avg_probs.copy()
#         for i, label in enumerate(LABELS):
#             weighted[i] *= CLASS_MULTIPLIERS[label]

#         # =========================================================
#         # 🧠 SMART OVERRIDE LOGIC (GEOMETRY + CNN)
#         # =========================================================
        
#         # 1. GEOMETRIC SMILE OVERRIDE (Crucial Fix)
#         # If mouth corners are significantly higher than the center (curve > 0.05),
#         # it is physically impossible to be Sad. Force Happy.
#         if mouth_curve > 0.04: # Threshold: 0.04 allows slight smiles, 0.1 is big smile
#             weighted[LABELS.index("Sad")] *= 0.0  # Kill Sad completely
#             weighted[LABELS.index("Happy")] *= 5.0 # Boost Happy
#             if mouth_ratio > 0.4: # Wide open mouth smile (laughing)
#                  weighted[LABELS.index("Surprise")] *= 0.5 # Reduce false surprise

#         # 2. GEOMETRIC FROWN CONFIRMATION
#         # If corners are WAY below center (curve < -0.05), boost Sad
#         elif mouth_curve < -0.03:
#             weighted[LABELS.index("Happy")] *= 0.0

#         # 3. SURPRISE FILTER (Open mouth check)
#         # Surprise requires an open mouth. If mouth is closed, kill Surprise.
#         if mouth_ratio < 0.15:
#             weighted[LABELS.index("Surprise")] *= 0.1
        
#         # 4. NEUTRAL vs SAD
#         # If no strong geometric sad/happy cue, and CNN is unsure, lean Neutral
#         temp_idx = np.argmax(weighted)
#         temp_emotion = LABELS[temp_idx]
        
#         if temp_emotion == "Sad" and mouth_curve > -0.01:
#             # If Model says Sad, but mouth is flat or slightly up -> likely Neutral
#             weighted[LABELS.index("Sad")] *= 0.3
#             weighted[LABELS.index("Neutral")] *= 2.0

#         # =========================================================

#         total = weighted.sum()
#         final_probs = weighted / total if total > 0 else weighted
#         idx = np.argmax(final_probs)
#         emotion = LABELS[idx]
#         conf = final_probs[idx]

#         if conf < BASE_THRESHOLDS.get(emotion, 0.2):
#             emotion = "Neutral"

#         return emotion, conf, (x1, y1, x2, y2), final_probs

#     def draw_hud(self, frame, display_probs):
#         if display_probs is None: return
#         start_x, start_y, gap = 10, 20, 25
#         overlay = frame.copy()
#         cv2.rectangle(overlay, (0, 0), (280, 200), (0, 0, 0), -1)
#         cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

#         for i, label in enumerate(LABELS):
#             prob = display_probs[i]
#             y = start_y + i * gap
#             color = (255, 255, 255)
#             if label == "Happy": color = (0, 255, 255)
#             elif label == "Surprise": color = (255, 100, 0)
#             elif label == "Sad": color = (255, 0, 0)
            
#             cv2.putText(frame, f"{label}: {int(prob*100)}%", (start_x, y), 
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
#             cv2.rectangle(frame, (start_x + 100, y - 10), 
#                          (start_x + 100 + int(150 * prob), y), color, -1)

# # =========================================================
# # MAIN
# # =========================================================
# if __name__ == "__main__":
#     cap = cv2.VideoCapture(0)
#     detector = EmotionDetector(MODEL_FILE)

#     while True:
#         ret, frame = cap.read()
#         if not ret: break

#         emotion, conf, box, probs = detector.predict(frame)
#         detector.draw_hud(frame, probs)

#         if box:
#             x1, y1, x2, y2 = box
#             color = (0, 255, 0)
#             if emotion == "Happy": color = (0, 255, 255)
#             elif emotion == "Sad": color = (255, 0, 0)
#             elif emotion == "Surprise": color = (255, 0, 255)
            
#             cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
#             cv2.putText(frame, f"{emotion} {int(conf*100)}%", (x1, y1-10), 
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

#         cv2.imshow("Emotion AI", frame)
#         if cv2.waitKey(1) & 0xFF == 27: break

#     cap.release()
#     cv2.destroyAllWindows()


















# import cv2
# import mediapipe as mp
# import torch
# import torch.nn as nn
# from torchvision import models, transforms
# from PIL import Image
# from collections import deque
# import numpy as np

# # ==============================
# # 1. CONFIGURATION
# # ==============================
# MODEL_FILE = "mobilenet_v3_large_affectnet7_.pth"
# FRAME_SKIP = 2
# USE_FP16 = torch.cuda.is_available()
# SMOOTHING_WINDOW = 4

# # --- NEW SETTING: NIGHT VISION ---
# # Set this to True if you are in a dark room.
# # It artificially boosts contrast to find hidden frown lines.
# LOW_LIGHT_MODE = True  
# GAMMA_INTENSITY = 1.5  # 1.0 = Normal, 2.0 = Night Vision

# LABELS = ['Anger', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

# # LOGIC TUNING
# CLASS_MULTIPLIERS = {
#     "Anger": 1.0, "Disgust": 0.5, "Fear": 1.0,     
#     "Happy": 2.5, "Neutral": 2.0, "Sad": 0.3, "Surprise": 1.0  
# }

# BASE_THRESHOLDS = {
#     "Anger": 0.15, "Disgust": 0.40, "Fear": 0.15,    
#     "Happy": 0.05, "Neutral": 0.10, "Sad": 0.50, "Surprise": 0.20
# }

# class EmotionDetector:
#     def __init__(self, model_path):
#         self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#         self.model = models.mobilenet_v3_large(weights=None)
#         num_ftrs = self.model.classifier[0].in_features
#         self.model.classifier = nn.Sequential(
#             nn.Linear(num_ftrs, 1024),
#             nn.Hardswish(),
#             nn.Dropout(0.5),
#             nn.Linear(1024, len(LABELS)) 
#         )
#         try:
#             state = torch.load(model_path, map_location=self.device, weights_only=True)
#             self.model.load_state_dict(state)
#             print(f"✅ Night-Vision AI Loaded")
#         except Exception as e:
#             print(f"❌ Load Error: {e}")
#             exit()

#         self.model.to(self.device).eval()
#         if USE_FP16: self.model.half()
#         self.prob_buffer = deque(maxlen=SMOOTHING_WINDOW)
#         self.face_detector = mp.solutions.face_detection.FaceDetection(
#             model_selection=0, min_detection_confidence=0.6
#         )
#         self.transform = transforms.Compose([
#             transforms.Resize((224, 224)),
#             transforms.ToTensor(),
#             transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
#         ])

#     def adjust_gamma(self, image, gamma=1.5):
#         # Build a lookup table mapping the pixel values [0, 255] to their adjusted gamma values
#         invGamma = 1.0 / gamma
#         table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
#         return cv2.LUT(image, table)

#     def predict(self, frame):
#         # --- NIGHT MODE PRE-PROCESSING ---
#         if LOW_LIGHT_MODE:
#             # We only brighten the frame for the AI, not for the display (optional)
#             # This helps it see the "hidden" shadows of a frown
#             ai_frame = self.adjust_gamma(frame, GAMMA_INTENSITY)
#         else:
#             ai_frame = frame

#         rgb = cv2.cvtColor(ai_frame, cv2.COLOR_BGR2RGB)
#         result = self.face_detector.process(rgb)

#         if not result.detections:
#             self.prob_buffer.clear()
#             return None, 0, None, None

#         h, w, _ = frame.shape
#         box = result.detections[0].location_data.relative_bounding_box
#         x1, y1 = max(0, int(box.xmin * w)), max(0, int(box.ymin * h))
#         x2, y2 = min(w, int((box.xmin + box.width) * w)), min(h, int((box.ymin + box.height) * h))
        
#         # Crop from the ENHANCED frame
#         face = ai_frame[y1:y2, x1:x2]
#         if face.size == 0: return None, 0, None, None

#         img = Image.fromarray(cv2.cvtColor(face, cv2.COLOR_BGR2RGB))
#         img = self.transform(img).unsqueeze(0).to(self.device)
#         if USE_FP16: img = img.half()

#         with torch.no_grad():
#             logits = self.model(img)
#             probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

#         self.prob_buffer.append(probs)
#         avg_probs = np.mean(self.prob_buffer, axis=0)
        
#         # --- LOGIC ENGINE ---
#         weighted_probs = np.zeros_like(avg_probs)
#         for i, label in enumerate(LABELS):
#             weighted_probs[i] = avg_probs[i] * CLASS_MULTIPLIERS.get(label, 1.0)
            
#         top_idx = np.argmax(weighted_probs)
#         hap_idx, dis_idx = LABELS.index("Happy"), LABELS.index("Disgust")
#         sad_idx, neu_idx = LABELS.index("Sad"), LABELS.index("Neutral")

#         # Logic Overrides
#         if top_idx == dis_idx:
#             if avg_probs[hap_idx] > 0.03: top_idx = hap_idx
#             elif avg_probs[neu_idx] > 0.10: top_idx = neu_idx

#         if top_idx == sad_idx:
#             if avg_probs[neu_idx] > 0.05: top_idx = neu_idx
#             if (weighted_probs[sad_idx] - weighted_probs[neu_idx]) < 0.1: top_idx = neu_idx

#         emotion = LABELS[top_idx]
        
#         # --- VISUAL SYNC ---
#         total_weight = np.sum(weighted_probs)
#         display_probs = weighted_probs / total_weight if total_weight > 0 else weighted_probs
#         conf = display_probs[top_idx]

#         thresh = BASE_THRESHOLDS.get(emotion, 0.20)
#         if emotion == "Happy" and LABELS[np.argmax(weighted_probs)] == "Disgust":
#             display_emotion = "Happy"
#         elif conf < thresh:
#             display_emotion = "Uncertain"
#         else:
#             display_emotion = emotion

#         return display_emotion, conf, (x1, y1, x2, y2), display_probs

# # ==============================
# # UI DISPLAY (Standard)
# # ==============================
# def draw_ui(frame, emotion, conf, box, probs):
#     x1, y1, x2, y2 = box
#     color = (0, 255, 0) if emotion != "Uncertain" else (0, 165, 255)
#     cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
#     cv2.putText(frame, f"{emotion} {conf*100:.0f}%", (x1, y1 - 10), 
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

#     overlay = frame.copy()
#     cv2.rectangle(overlay, (10, 10), (220, 240), (0, 0, 0), -1)
#     cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

#     for i, label in enumerate(LABELS):
#         p = probs[i]
#         bar_w = int(p * 120)
#         y = 40 + (i * 28)
#         is_winner = (label == emotion) and (emotion != "Uncertain")
#         bar_color = (0, 255, 255) if is_winner else ((0, 255, 0) if p > 0.3 else (100, 100, 100))
#         cv2.putText(frame, f"{label[:3]}:", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)
#         cv2.rectangle(frame, (60, y-10), (180, y), (50, 50, 50), -1)
#         cv2.rectangle(frame, (60, y-10), (60 + bar_w, y), bar_color, -1)
#         cv2.putText(frame, f"{int(p*100)}%", (190, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

# if __name__ == "__main__":
#     cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
#     detector = EmotionDetector(MODEL_FILE)
#     cap.set(cv2.CAP_PROP_BRIGHTNESS, 150) 
#     print("🎥 Night-Vision AI Started...")
    
#     last_data = (None, 0, None, None)
#     count = 0

#     while True:
#         ret, frame = cap.read()
#         if not ret: break

#         count += 1
#         if count % FRAME_SKIP == 0:
#             last_data = detector.predict(frame)

#         emotion, conf, box, probs = last_data

#         if emotion:
#             draw_ui(frame, emotion, conf, box, probs)
#             # Optional: Show the "AI Vision" (Gamma Corrected) in a small window
#             # if LOW_LIGHT_MODE:
#             #     cv2.imshow("What AI Sees", detector.adjust_gamma(frame, GAMMA_INTENSITY))

#         cv2.imshow("Emotion AI", frame)
#         if cv2.waitKey(1) & 0xFF == ord('q'): break

#     cap.release()
#     cv2.destroyAllWindows()





# import cv2
# import mediapipe as mp
# import torch
# import torch.nn as nn
# from torchvision import models, transforms
# from PIL import Image
# from collections import deque
# import numpy as np

# # ==============================
# # CONFIG
# # ==============================
# MODEL_FILE = "mobilenet_v3_large_affectnet7_.pth"

# # Keep the same resolution across devices for stability.
# CAPTURE_W, CAPTURE_H = 640, 480

# # Speed vs stability
# FRAME_SKIP = 2
# SMOOTHING_WINDOW = 6      # probs smoothing
# BOX_SMOOTHING = 0.6       # 0..1 (higher = smoother box)

# # Precision: FP16 is faster on GPU but can slightly change outputs.
# # For max similarity across devices, set FORCE_FP32 = True
# FORCE_FP32 = True

# # Low light handling (AUTO, not always-on)
# AUTO_LOW_LIGHT = True
# LOW_LIGHT_LUMA_THRESH = 70    # avg grayscale brightness threshold (0-255)
# GAMMA_INTENSITY = 1.5         # apply only in low light

# LABELS = ['Anger', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

# # Your tuning (keep if you want same behavior)
# CLASS_MULTIPLIERS = {
#     "Anger": 1.0, "Disgust": 1, "Fear": 1.0,
#     "Happy": 2.5, "Neutral": 2.0, "Sad": 0.5, "Surprise": 1.0
# }

# BASE_THRESHOLDS = {
#     "Anger": 0.15, "Disgust": 0.40, "Fear": 0.15,
#     "Happy": 0.05, "Neutral": 0.10, "Sad": 0.50, "Surprise": 0.20
# }

# # Face crop behavior
# FACE_PAD_RATIO = 0.25  # padding around face box (25% of box size)
# PICK_BIGGEST_FACE = True


# # ==============================
# # HELPERS
# # ==============================
# def clamp(v, lo, hi):
#     return max(lo, min(hi, v))

# def box_area(box):
#     x1, y1, x2, y2 = box
#     return max(0, x2 - x1) * max(0, y2 - y1)

# def smooth_box(prev, curr, alpha=0.6):
#     """Exponential moving average for bounding boxes."""
#     if prev is None:
#         return curr
#     px1, py1, px2, py2 = prev
#     cx1, cy1, cx2, cy2 = curr
#     sx1 = int(alpha * px1 + (1 - alpha) * cx1)
#     sy1 = int(alpha * py1 + (1 - alpha) * cy1)
#     sx2 = int(alpha * px2 + (1 - alpha) * cx2)
#     sy2 = int(alpha * py2 + (1 - alpha) * cy2)
#     return (sx1, sy1, sx2, sy2)

# def adjust_gamma_bgr(image_bgr, gamma=1.5):
#     invGamma = 1.0 / gamma
#     table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
#     return cv2.LUT(image_bgr, table)

# def make_square_crop(frame_bgr, box, pad_ratio=0.25):
#     """
#     Convert a face box to a padded square crop, then crop from frame.
#     """
#     h, w, _ = frame_bgr.shape
#     x1, y1, x2, y2 = box

#     bw = x2 - x1
#     bh = y2 - y1
#     if bw <= 0 or bh <= 0:
#         return None, None

#     # center
#     cx = x1 + bw / 2
#     cy = y1 + bh / 2

#     # square side with padding
#     side = max(bw, bh)
#     side = side * (1 + pad_ratio * 2)

#     nx1 = int(cx - side / 2)
#     ny1 = int(cy - side / 2)
#     nx2 = int(cx + side / 2)
#     ny2 = int(cy + side / 2)

#     nx1 = clamp(nx1, 0, w)
#     ny1 = clamp(ny1, 0, h)
#     nx2 = clamp(nx2, 0, w)
#     ny2 = clamp(ny2, 0, h)

#     if nx2 <= nx1 or ny2 <= ny1:
#         return None, None

#     crop = frame_bgr[ny1:ny2, nx1:nx2]
#     return crop, (nx1, ny1, nx2, ny2)


# # ==============================
# # EMOTION DETECTOR
# # ==============================
# class EmotionDetector:
#     def __init__(self, model_path):
#         self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

#         # Decide FP16 usage
#         self.use_fp16 = (self.device.type == "cuda") and (not FORCE_FP32)

#         self.model = models.mobilenet_v3_large(weights=None)
#         num_ftrs = self.model.classifier[0].in_features
#         self.model.classifier = nn.Sequential(
#             nn.Linear(num_ftrs, 1024),
#             nn.Hardswish(),
#             nn.Dropout(0.5),
#             nn.Linear(1024, len(LABELS))
#         )

#         # Load weights
#         try:
#             state = torch.load(model_path, map_location=self.device, weights_only=True)
#             self.model.load_state_dict(state)
#             print("✅ Model loaded")
#         except Exception as e:
#             print(f"❌ Load Error: {e}")
#             raise

#         self.model.to(self.device).eval()
#         if self.use_fp16:
#             self.model.half()
#             print("⚡ Using FP16 on CUDA")
#         else:
#             print("🧠 Using FP32")

#         # Mediapipe face detection
#         self.face_detector = mp.solutions.face_detection.FaceDetection(
#             model_selection=0, min_detection_confidence=0.6
#         )

#         self.transform = transforms.Compose([
#             transforms.Resize((224, 224)),
#             transforms.ToTensor(),
#             transforms.Normalize(mean=[0.485, 0.456, 0.406],
#                                  std=[0.229, 0.224, 0.225])
#         ])

#         self.prob_buffer = deque(maxlen=SMOOTHING_WINDOW)
#         self.prev_box = None

#     def choose_face_box(self, detections, w, h):
#         """Pick the biggest face box (or first) for stability."""
#         boxes = []
#         for det in detections:
#             bb = det.location_data.relative_bounding_box
#             x1 = int(bb.xmin * w)
#             y1 = int(bb.ymin * h)
#             x2 = int((bb.xmin + bb.width) * w)
#             y2 = int((bb.ymin + bb.height) * h)
#             x1 = clamp(x1, 0, w - 1)
#             y1 = clamp(y1, 0, h - 1)
#             x2 = clamp(x2, 0, w)
#             y2 = clamp(y2, 0, h)
#             boxes.append((x1, y1, x2, y2))

#         if not boxes:
#             return None

#         if PICK_BIGGEST_FACE:
#             boxes.sort(key=box_area, reverse=True)
#         return boxes[0]

#     def predict(self, frame_bgr):
#         """
#         Returns:
#           display_emotion, conf, draw_box, display_probs
#         """
#         h, w, _ = frame_bgr.shape

#         # AUTO low light decision based on the actual frame
#         ai_frame = frame_bgr
#         if AUTO_LOW_LIGHT:
#             gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
#             mean_luma = float(np.mean(gray))
#             low_light = mean_luma < LOW_LIGHT_LUMA_THRESH
#             if low_light:
#                 ai_frame = adjust_gamma_bgr(frame_bgr, GAMMA_INTENSITY)
#         else:
#             # keep as-is
#             mean_luma = None
#             low_light = False

#         # Face detection expects RGB
#         rgb = cv2.cvtColor(ai_frame, cv2.COLOR_BGR2RGB)
#         result = self.face_detector.process(rgb)

#         if not result.detections:
#             self.prob_buffer.clear()
#             self.prev_box = None
#             return None, 0.0, None, None

#         # Choose face box
#         raw_box = self.choose_face_box(result.detections, w, h)
#         if raw_box is None:
#             self.prob_buffer.clear()
#             self.prev_box = None
#             return None, 0.0, None, None

#         # Smooth box to reduce jitter
#         smoothed = smooth_box(self.prev_box, raw_box, alpha=BOX_SMOOTHING)
#         self.prev_box = smoothed

#         # Crop a padded SQUARE for more consistent model input
#         face_crop, draw_box = make_square_crop(ai_frame, smoothed, pad_ratio=FACE_PAD_RATIO)
#         if face_crop is None or face_crop.size == 0:
#             self.prob_buffer.clear()
#             return None, 0.0, None, None

#         img = Image.fromarray(cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB))
#         tens = self.transform(img).unsqueeze(0).to(self.device)
#         if self.use_fp16:
#             tens = tens.half()

#         with torch.no_grad():
#             logits = self.model(tens)
#             probs = torch.softmax(logits, dim=1)[0].float().cpu().numpy()  # force float for stability

#         # Probability smoothing
#         self.prob_buffer.append(probs)
#         avg_probs = np.mean(self.prob_buffer, axis=0)

#         # Logic engine (same as your idea)
#         weighted_probs = np.zeros_like(avg_probs)
#         for i, label in enumerate(LABELS):
#             weighted_probs[i] = avg_probs[i] * CLASS_MULTIPLIERS.get(label, 1.0)

#         top_idx = int(np.argmax(weighted_probs))

#         hap_idx = LABELS.index("Happy")
#         dis_idx = LABELS.index("Disgust")
#         sad_idx = LABELS.index("Sad")
#         neu_idx = LABELS.index("Neutral")

#         # Overrides (kept, but be aware these can behave differently across setups)
#         if top_idx == dis_idx:
#             if avg_probs[hap_idx] > 0.03:
#                 top_idx = hap_idx
#             elif avg_probs[neu_idx] > 0.10:
#                 top_idx = neu_idx

#         if top_idx == sad_idx:
#             if (weighted_probs[sad_idx] - weighted_probs[neu_idx]) < 0.1:
#                 top_idx = neu_idx

#         emotion = LABELS[top_idx]

#         # “Display probs” normalized for UI
        
#         total_weight = float(np.sum(weighted_probs))
#         display_probs = (weighted_probs / total_weight) if total_weight > 0 else weighted_probs
#         conf = float(display_probs[top_idx])

#         thresh = float(BASE_THRESHOLDS.get(emotion, 0.20))
#         if conf < thresh:
#             display_emotion = "Uncertain"
#         else:
#             display_emotion = emotion

#         return display_emotion, conf, draw_box, display_probs


# # ==============================
# # UI
# # ==============================
# def draw_ui(frame, emotion, conf, box, probs):
#     x1, y1, x2, y2 = box
#     color = (0, 255, 0) if emotion != "Uncertain" else (0, 165, 255)
#     cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
#     cv2.putText(frame, f"{emotion} {conf*100:.0f}%", (x1, max(20, y1 - 10)),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

#     # Prob bars
#     overlay = frame.copy()
#     cv2.rectangle(overlay, (10, 10), (240, 260), (0, 0, 0), -1)
#     cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

#     for i, label in enumerate(LABELS):
#         p = float(probs[i])
#         bar_w = int(p * 130)
#         y = 40 + (i * 30)
#         is_winner = (label == emotion) and (emotion != "Uncertain")

#         # keep your style; just stable
#         bar_color = (0, 255, 255) if is_winner else ((0, 255, 0) if p > 0.3 else (100, 100, 100))

#         cv2.putText(frame, f"{label[:3]}:", (20, y),
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
#         cv2.rectangle(frame, (70, y - 12), (210, y), (50, 50, 50), -1)
#         cv2.rectangle(frame, (70, y - 12), (70 + bar_w, y), bar_color, -1)
#         cv2.putText(frame, f"{int(p * 100)}%", (215, y),
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)


# # ==============================
# # MAIN
# # ==============================
# if __name__ == "__main__":
#     # Use CAP_ANY first for portability. If you *must* use DSHOW on Windows, you can switch.
#     cap = cv2.VideoCapture(0, cv2.CAP_ANY)

#     # Force same resolution on both devices
#     cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_W)
#     cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_H)

#     # Optional: try to reduce camera auto changes (may not work on all webcams)
#     # cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # some cams accept 0.25/0.75 style values
#     # cap.set(cv2.CAP_PROP_EXPOSURE, -6)         # cam-specific

#     if not cap.isOpened():
#         print("❌ Could not open webcam")
#         raise SystemExit

#     detector = EmotionDetector(MODEL_FILE)
#     print("🎥 Emotion AI Started... Press 'q' to quit")

#     last_data = (None, 0.0, None, None)
#     count = 0

#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break

#         count += 1
#         if count % FRAME_SKIP == 0:
#             last_data = detector.predict(frame)

#         emotion, conf, box, probs = last_data

#         if emotion and box and probs is not None:
#             draw_ui(frame, emotion, conf, box, probs)

#         cv2.imshow("Emotion AI (Consistent)", frame)
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break

#     cap.release()
#     cv2.destroyAllWindows()
