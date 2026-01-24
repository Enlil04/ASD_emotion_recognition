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

        # Sise with closed mouthurpr
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


