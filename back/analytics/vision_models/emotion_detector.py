import cv2
import mediapipe as mp
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
from collections import deque
import numpy as np
import os

# --- PATH SETUP ---
base_path = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(base_path, "mobilenet_v3_large_affectnet7_.pth")

# --- CONFIGURATION ---
SMOOTHING_WINDOW = 5 # Increased for stability
LABELS = ['Anger', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

CLASS_MULTIPLIERS = {
    "Anger": 0.8,    # 📉 Reduced to stop Neutral-to-Anger jitter
    "Disgust": 0.45, 
    "Fear": 9.0,
    "Happy": 3.8,    # 📈 Boosted to beat Surprise
    "Neutral": 4.0,  # 📈 Boosted to be the "Default" state
    "Sad": 0.3,     # 📉 Heavily reduced to stop Neutral-to-Sad jitter
    "Surprise": 0.9  # 📉 Reduced to stop Smile-to-Surprise jitter
}

BASE_THRESHOLDS = {
    "Anger": 0.35,   # 📈 Higher bar to trigger
    "Disgust": 0.68, 
    "Fear": 0.25,
    "Happy": 0.10, 
    "Neutral": 0.15, 
    "Sad": 0.60,     # 📈 Needs high confidence to break Neutral
    "Surprise": 0.3  # 📈 Needs high confidence to break Happy
}

class EmotionDetector:
    def __init__(self, model_path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.use_fp16 = self.device.type == "cuda"
        self.prev_emotion = "Neutral"
        self.emotion_hold = 0
        self.prob_buffer = deque(maxlen=SMOOTHING_WINDOW)
        self.micro_buffer = deque(maxlen=4)
        self.micro_threshold = 0.22

        # --- MODEL ---
        self.model = models.mobilenet_v3_large(weights=None)
        in_features = self.model.classifier[0].in_features
        self.model.classifier = nn.Sequential(
            nn.Linear(in_features, 1024),
            nn.Hardswish(),
            nn.Dropout(0.5),
            nn.Linear(1024, len(LABELS))
        )
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device).eval()
        if self.use_fp16: self.model.half()

        self.face_mesh = mp.solutions.face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def get_geometry(self, lm, w, h):
        # Mouth Height vs Width
        m_top, m_bot = np.array([lm[13].x*w, lm[13].y*h]), np.array([lm[14].x*w, lm[14].y*h])
        m_l, m_r = np.array([lm[61].x*w, lm[61].y*h]), np.array([lm[291].x*w, lm[291].y*h])
        
        m_height = np.linalg.norm(m_top - m_bot)
        m_width = np.linalg.norm(m_l - m_r)
        
        # Brow Distance (Inner Brow to Eye)
        # Left: 52 to 159 | Right: 282 to 386
        brow_dist = (abs(lm[52].y - lm[159].y) + abs(lm[282].y - lm[386].y)) / 2
        
        return m_height, m_width, brow_dist



    def predict(self, frame, smooth=True):
                h, w, _ = frame.shape
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res = self.face_mesh.process(rgb)

                if not res.multi_face_landmarks:
                    return "Neutral", 0.0, None, None, None

                lm = res.multi_face_landmarks[0].landmark
                
                # --- 1. FACE CROP ---
                xs, ys = [p.x for p in lm], [p.y for p in lm]
                x1, y1, x2, y2 = int(min(xs)*w), int(min(ys)*h), int(max(xs)*w), int(max(ys)*h)
                face = frame[max(0,y1-20):min(h,y2+20), max(0,x1-20):min(w,x2+20)]
                if face.size == 0: return "Neutral", 0.0, None, None, None

                # --- 2. CNN INFERENCE ---
                lab = cv2.cvtColor(face, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(l)
                face_rgb = cv2.cvtColor(cv2.merge((clahe, a, b)), cv2.COLOR_LAB2RGB)
                img_t = self.transform(Image.fromarray(face_rgb)).unsqueeze(0).to(self.device)
                if self.use_fp16: img_t = img_t.half()
                
                with torch.no_grad():
                    probs = torch.softmax(self.model(img_t), dim=1)[0].cpu().numpy()

                self.prob_buffer.append(probs)
                avg_probs = np.mean(self.prob_buffer, axis=0)

                # --- 3. GEOMETRY CALCULATIONS ---
                m_h, m_w, b_dist = self.get_geometry(lm, w, h)
                m_ratio = m_h / m_w if m_w > 0 else 0
                
                # EAR (Eye Aspect Ratio) - detecting wide eyes
                e_open = (abs(lm[159].y - lm[145].y) + abs(lm[386].y - lm[374].y)) / 2

                # --- 4. SMART OVERRIDES ---
                weighted = avg_probs.copy()
                
                # Order: ['Anger', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']
                # Rebalanced: Sad boosted to 0.8, Neutral slightly relaxed to 3.5
                multipliers = [0.8, 0.45, 1.2, 4.0, 3.5, 0.8, 2.5] 
                for i in range(len(LABELS)):
                    weighted[i] *= multipliers[i]
                
                # --- RULE 1: THE HAPPY GUARD (Smiles kill Sadness & Fear) ---
                if m_ratio < 0.38: 
                    weighted[LABELS.index("Happy")] *= 12.0
                    weighted[LABELS.index("Sad")] *= 0.01      
                    weighted[LABELS.index("Fear")] *= 0.01     
                    weighted[LABELS.index("Surprise")] *= 0.01

                # --- RULE 2: WIDE EYES (Fear vs Surprise) ---
                # Lowered eye threshold slightly to make Surprise easier
                elif e_open > 0.022:
                    # Lowered from 0.60 to 0.48 so you don't have to open as wide
                    if m_ratio > 0.48: 
                        weighted[LABELS.index("Surprise")] *= 15.0
                        weighted[LABELS.index("Fear")] *= 0.1
                        weighted[LABELS.index("Sad")] *= 0.1
                    elif 0.38 <= m_ratio <= 0.48: # Tense Horizontal Stretch
                        weighted[LABELS.index("Fear")] *= 10.0
                        weighted[LABELS.index("Surprise")] *= 0.1
                        weighted[LABELS.index("Sad")] *= 0.1

                # --- RULE 3: THE NEUTRAL / RESTING FACE GUARD ---
                else:
                    weighted[LABELS.index("Fear")] *= 0.05
                    weighted[LABELS.index("Surprise")] *= 0.05
                    
                    # Only crush Sadness if the CNN is highly confident it's Neutral
                    if avg_probs[LABELS.index("Neutral")] > 0.50:
                        weighted[LABELS.index("Neutral")] *= 5.0
                        weighted[LABELS.index("Sad")] *= 0.2

                # --- FINAL CHOICE ---
                idx = np.argmax(weighted)
                new_emotion = LABELS[idx]
                total_w = weighted.sum()
                conf = weighted[idx] / total_w if total_w > 0 else 0.0

                # Dropped Sadness requirement from 0.60 down to 0.40
                if new_emotion == "Sad" and conf < 0.40:
                    new_emotion = "Neutral"
                elif conf < 0.15: 
                    new_emotion = "Neutral"

                # --- TEMPORAL SMOOTHING ---
                if new_emotion != self.prev_emotion and self.emotion_hold < 3:
                    self.emotion_hold += 1
                    final_emotion = self.prev_emotion
                else:
                    self.emotion_hold = 0
                    self.prev_emotion = new_emotion
                    final_emotion = new_emotion

                return final_emotion, conf, (x1, y1, x2, y2), avg_probs, None



    def draw_hud(self, frame, probs):
        if probs is None: return
        for i, label in enumerate(LABELS):
            cv2.putText(frame, f"{label}: {int(probs[i]*100)}%", (10, 25 + i * 22), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

# --- MAIN LOOP ---
if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    detector = EmotionDetector(MODEL_FILE)

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        emo, conf, box, probs, micro = detector.predict(frame)
        detector.draw_hud(frame, probs)

        if box:
            x1, y1, x2, y2 = box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{emo} {int(conf*100)}%", (x1, y1-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        if micro:
            cv2.putText(frame, f"MICRO spikes: {micro}", (10, 200), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow("Emotion AI", frame)
        if cv2.waitKey(1) & 0xFF == 27: break

    cap.release()
    cv2.destroyAllWindows()



# import cv2
# import mediapipe as mp
# import torch
# import torch.nn as nn
# from torchvision import models, transforms
# from PIL import Image
# from collections import deque
# import numpy as np
 

# import os

# # 1. Start from this script's location
# base_path = os.path.dirname(os.path.abspath(__file__))

# # 2. Try to find the file
# MODEL_FILE = os.path.join(base_path, "mobilenet_v3_large_affectnet7_.pth")

# # 3. If it fails, check if we accidentally went too deep
# if not os.path.exists(MODEL_FILE):
#     # This checks one level up just in case
#     alternative_path = os.path.join(os.path.dirname(base_path), "mobilenet_v3_large_affectnet7_.pth")
#     if os.path.exists(alternative_path):
#         MODEL_FILE = alternative_path

# print(f"Final Model Path Target: {MODEL_FILE}")

# # ==============================
# # CONFIGURATION
# # ==============================
# #MODEL_FILE = "mobilenet_v3_large_affectnet7_.pth"
# SMOOTHING_WINDOW = 6

# LABELS = ['Anger', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

# # --- CLASS WEIGHTS ---
# CLASS_MULTIPLIERS = {
#     "Anger": 0.25,
#     "Disgust": 0.098,
#     "Fear": 1.0,
#     "Happy": 12.0,      # boosted
#     "Neutral": 10.9,    # reduced from 15
#     "Sad": 0.097,
#     "Surprise": 0.55
# }

# BASE_THRESHOLDS = {
#     "Anger": 0.05, "Disgust": 0.40, "Fear": 0.15,
#     "Happy": 0.05, "Neutral": 0.15, "Sad": 0.25, "Surprise": 0.55
# }

# # =========================================================
# # EMOTION DETECTOR
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

#         state = torch.load(model_path, map_location=self.device)
#         self.model.load_state_dict(state)
#         self.model.to(self.device).eval()
#         if self.use_fp16:
#             self.model.half()

#         print(f"✅ Model loaded on {self.device}")

#         # ------------------------------
#         # MEDIAPIPE FACE MESH
#         # ------------------------------
#         self.face_mesh = mp.solutions.face_mesh.FaceMesh(
#             max_num_faces=1,
#             refine_landmarks=False,
#             min_detection_confidence=0.5,
#             min_tracking_confidence=0.5
#         )

#         # ------------------------------
#         # TRANSFORM
#         # ------------------------------
#         self.transform = transforms.Compose([
#             transforms.Resize((224, 224)),
#             transforms.ToTensor(),
#             transforms.Normalize(
#                 mean=[0.485, 0.456, 0.406],
#                 std=[0.229, 0.224, 0.225]
#             )
#         ])

#         self.prob_buffer = deque(maxlen=SMOOTHING_WINDOW)
#         self.clahe = cv2.createCLAHE(2.0, (8, 8))

#     # =========================================================
#     # GEOMETRY HELPERS
#     # =========================================================
#     def mouth_open_ratio(self, lm, w, h):
#         top = np.array([lm[13].x * w, lm[13].y * h])
#         bot = np.array([lm[14].x * w, lm[14].y * h])
#         left = np.array([lm[61].x * w, lm[61].y * h])
#         right = np.array([lm[291].x * w, lm[291].y * h])

#         vert = np.linalg.norm(top - bot)
#         horiz = np.linalg.norm(left - right)
#         return vert / horiz if horiz > 0 else 0

#     def smile_width_ratio(self, lm, w, h):
#         mouth_l = np.array([lm[61].x * w, lm[61].y * h])
#         mouth_r = np.array([lm[291].x * w, lm[291].y * h])
#         jaw_l = np.array([lm[234].x * w, lm[234].y * h])
#         jaw_r = np.array([lm[454].x * w, lm[454].y * h])

#         mouth_w = np.linalg.norm(mouth_l - mouth_r)
#         face_w = np.linalg.norm(jaw_l - jaw_r)
#         return mouth_w / face_w if face_w > 0 else 0

#     # =========================================================
#     # PREDICTION
#     # =========================================================
#     def predict(self, frame, smooth=True):
#         h, w, _ = frame.shape
#         rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#         res = self.face_mesh.process(rgb)

#         if not res.multi_face_landmarks:
#             self.prob_buffer.clear()
#             return None, 0.0, None, None

#         lm = res.multi_face_landmarks[0].landmark

#         # --- FACE BOUNDING BOX ---
#         xs = [p.x for p in lm]
#         ys = [p.y for p in lm]
#         x1, y1 = int(min(xs) * w), int(min(ys) * h)
#         x2, y2 = int(max(xs) * w), int(max(ys) * h)

#         pad = 20
#         x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
#         x2, y2 = min(w, x2 + pad), min(h, y2 + pad)

#         face = frame[y1:y2, x1:x2]
#         if face.size == 0:
#             return None, 0.0, None, None
        

#         # --- lighting analysis ---
#         gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
#         average_brightness = np.mean(gray)

#         dynamic_clahe_clip = cv2.createCLAHE(clipLimit=1.2 if average_brightness > 160 else 2.0, tileGridSize=(8,8))
#         gray_enhanced = dynamic_clahe_clip.apply(gray)
#         face_3c = cv2.merge([gray_enhanced, gray_enhanced, gray_enhanced])

#         img = Image.fromarray(face_3c)
#         img_t = self.transform(img).unsqueeze(0).to(self.device)
#         if self.use_fp16:
#             img_t = img_t.half()


#         # --- GEOMETRY ---
#         mouth_open = self.mouth_open_ratio(lm, w, h)
#         smile_width = self.smile_width_ratio(lm, w, h)


#         # --- INFERENCE ---
#         with torch.no_grad():
#             logits = self.model(img_t)
#             probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

#         # --- 
#         if smooth:
#             self.prob_buffer.append(probs)
#             avg = np.mean(self.prob_buffer, axis=0) 
#         else:
#             avg = probs

#         weighted = avg.copy()
#         for i, label in enumerate(LABELS):
#             weighted[i] *= CLASS_MULTIPLIERS[label]

#         temp_idx = np.argmax(weighted)
#         temp_emotion = LABELS[temp_idx]


#         if average_brightness > 150:

#             weighted[LABELS.index("Anger")] *= 0.07
#             weighted[LABELS.index("Neutral")] *= 2.5

#         # =========================================================
#         # SMART OVERRIDES 
#         # =========================================================

#         # Sad vs Neutral
#         if temp_emotion == "Sad" and avg[LABELS.index("Neutral")] > 0.15:
#             weighted[LABELS.index("Sad")] *= 0.2
#             weighted[LABELS.index("Neutral")] *= 2.0

#         # Sad vs Happy (CNN confusion)
#         if temp_emotion == "Sad" and avg[LABELS.index("Happy")] > 0.02:
#             weighted[LABELS.index("Sad")] *= 0.1
#             weighted[LABELS.index("Happy")] *= 8.0

#         # Surprise with closed mouth
#         if temp_emotion == "Surprise" and mouth_open < 0.25:
#             weighted[LABELS.index("Surprise")] *= 0.0
#             weighted[LABELS.index("Happy")] *= 3.0

#         # Disgust as smile
#         if temp_emotion == "Disgust" and avg[LABELS.index("Happy")] > 0.1:
#             weighted[LABELS.index("Disgust")] *= 0.1
#             weighted[LABELS.index("Happy")] *= 3.0

#         # 🔥 CLOSED-MOUTH SMILE FIX
#         if temp_emotion == "Sad" and smile_width > 0.42:
#             weighted[LABELS.index("Sad")] *= 0.05
#             weighted[LABELS.index("Happy")] *= 12.0


#         print(f"Raw CNN - Fear: {avg[LABELS.index('Fear')]:.4f} | Sad: {avg[LABELS.index('Sad')]:.4f} | Disgust: {avg[LABELS.index('Disgust')]:.4f}")

#         # =========================================================

#         total = weighted.sum()
#         final_probs = weighted / total if total > 0 else weighted
#         idx = np.argmax(final_probs)
#         emotion = LABELS[idx]
#         conf = final_probs[idx]

#         if conf < BASE_THRESHOLDS.get(emotion, 0.2):
#             emotion = "Neutral"

#         return emotion, conf, (x1, y1, x2, y2), final_probs

#     # =========================================================
#     # HUD
#     # =========================================================
#     def draw_hud(self, frame, probs):
#         if probs is None:
#             return
#         for i, label in enumerate(LABELS):
#             y = 25 + i * 22
#             cv2.putText(
#                 frame,
#                 f"{label}: {int(probs[i]*100)}%",
#                 (10, y),
#                 cv2.FONT_HERSHEY_SIMPLEX,
#                 0.5,
#                 (255,255,255),
#                 1
#             )


# # =========================================================
# # MAIN LOOP
# # =========================================================
# if __name__ == "__main__":
#     cap = cv2.VideoCapture(0)
#     detector = EmotionDetector(MODEL_FILE)

#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break

#         emotion, conf, box, probs = detector.predict(frame)
#         detector.draw_hud(frame, probs)

#         if box:
#             x1, y1, x2, y2 = box
#             color = (0,255,0)
#             if emotion == "Happy": color = (0,255,255)
#             elif emotion == "Sad": color = (255,0,0)
#             elif emotion == "Surprise": color = (255,0,255)

#             cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
#             cv2.putText(
#                 frame,
#                 f"{emotion} {int(conf*100)}%",
#                 (x1, y1-10),
#                 cv2.FONT_HERSHEY_SIMPLEX,
#                 0.8,
#                 color,
#                 2
#             )

#         cv2.imshow("Emotion AI", frame)
#         if cv2.waitKey(1) & 0xFF == 27:
#             break

#     cap.release()
#     cv2.destroyAllWindows()
