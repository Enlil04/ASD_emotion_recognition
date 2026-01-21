import cv2
import mediapipe as mp
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
from collections import deque
import numpy as np

# ==============================
# 1. CONFIGURATION
# ==============================
MODEL_FILE = "mobilenet_v3_large_affectnet7_.pth"
FRAME_SKIP = 2
USE_FP16 = torch.cuda.is_available()

# Short memory for snappy response
SMOOTHING_WINDOW = 4

LABELS = ['Anger', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

# --- TUNING ENGINE ---

# 1. CLASS MULTIPLIERS 
# Neutral is now the strongest class. Sad is the weakest.
CLASS_MULTIPLIERS = {
    "Anger": 1.0,    
    "Disgust": 0.5,  
    "Fear": 1.0,     
    "Happy": 2.5,    
    "Neutral": 2.0,  # SUPER BOOST: Neutral is now a "Magnet"
    "Sad": 0.3,      # CRUSHED: Sadness barely registers unless extreme
    "Surprise": 1.0  
}

# 2. THRESHOLDS 
BASE_THRESHOLDS = {
    "Anger": 0.15,
    "Disgust": 0.40, 
    "Fear": 0.15,    
    "Happy": 0.05,   
    "Neutral": 0.10, # Very low bar to enter Neutral
    "Sad": 0.60,     # EXTREME BAR: AI must be 60% certain to show Sad
    "Surprise": 0.20
}

# ==============================
# 2. EMOTION DETECTOR
# ==============================
class EmotionDetector:
    def __init__(self, model_path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = models.mobilenet_v3_large(weights=None)
        num_ftrs = self.model.classifier[0].in_features
        self.model.classifier = nn.Sequential(
            nn.Linear(num_ftrs, 1024),
            nn.Hardswish(),
            nn.Dropout(0.5),
            nn.Linear(1024, len(LABELS)) 
        )

        try:
            state = torch.load(model_path, map_location=self.device, weights_only=True)
            self.model.load_state_dict(state)
            print(f"✅ Final-Tuned Model Loaded: {model_path}")
        except Exception as e:
            print(f"❌ Load Error: {e}")
            exit()

        self.model.to(self.device).eval()
        if USE_FP16: self.model.half()

        self.prob_buffer = deque(maxlen=SMOOTHING_WINDOW)
        self.face_detector = mp.solutions.face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=0.6
        )
        
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def predict(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.face_detector.process(rgb)

        if not result.detections:
            self.prob_buffer.clear()
            return None, 0, None, None

        # Extract Face
        h, w, _ = frame.shape
        box = result.detections[0].location_data.relative_bounding_box
        x1, y1 = max(0, int(box.xmin * w)), max(0, int(box.ymin * h))
        x2, y2 = min(w, int((box.xmin + box.width) * w)), min(h, int((box.ymin + box.height) * h))
        face = frame[y1:y2, x1:x2]
        if face.size == 0: return None, 0, None, None

        # Inference
        img = Image.fromarray(cv2.cvtColor(face, cv2.COLOR_BGR2RGB))
        img = self.transform(img).unsqueeze(0).to(self.device)
        if USE_FP16: img = img.half()

        with torch.no_grad():
            logits = self.model(img)
            probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

        self.prob_buffer.append(probs)
        avg_probs = np.mean(self.prob_buffer, axis=0)
        
        # ==================================================
        # 3. BALANCING LOGIC
        # ==================================================
        
        # A. Apply Multipliers 
        scored_probs = np.zeros_like(avg_probs)
        for i, label in enumerate(LABELS):
            scored_probs[i] = avg_probs[i] * CLASS_MULTIPLIERS.get(label, 1.0)

        # B. Pick Preliminary Winner
        top_idx = np.argmax(scored_probs)
        
        # Indices
        hap_idx = LABELS.index("Happy")
        dis_idx = LABELS.index("Disgust")
        sad_idx = LABELS.index("Sad")
        neu_idx = LABELS.index("Neutral")

        # --- RULE 1: THE DISGUST FILTER ---
        if top_idx == dis_idx:
            if avg_probs[hap_idx] > 0.03: 
                top_idx = hap_idx
            elif avg_probs[neu_idx] > 0.10:
                top_idx = neu_idx

        # --- RULE 2: THE NEUTRAL MAGNET (Fixes Sadness) ---
        # If Sad wins, we check the gap with Neutral.
        if top_idx == sad_idx:
            # 1. If Neutral is present at all (>5%), switch to Neutral
            if avg_probs[neu_idx] > 0.05:
                top_idx = neu_idx
            
            # 2. GAP CHECK: Even if Sad wins, is it winning by a lot?
            # If the raw gap between Sad and Neutral is small (< 0.4), force Neutral.
            # This handles "Resting Sad Face" where the model is 50/50.
            raw_gap = avg_probs[sad_idx] - avg_probs[neu_idx]
            if raw_gap < 0.4: 
                top_idx = neu_idx

        # ==================================================

        emotion = LABELS[top_idx]
        conf = avg_probs[top_idx] 

        # Threshold Check
        thresh = BASE_THRESHOLDS.get(emotion, 0.20)
        
        if emotion == "Happy" and LABELS[np.argmax(scored_probs)] == "Disgust":
            display_emotion = "Happy"
        elif conf < thresh:
            display_emotion = "Uncertain"
        else:
            display_emotion = emotion

        return display_emotion, conf, (x1, y1, x2, y2), avg_probs

# ==============================
# 3. UI DISPLAY
# ==============================
def draw_ui(frame, emotion, conf, box, probs):
    x1, y1, x2, y2 = box
    color = (0, 255, 0) if emotion != "Uncertain" else (0, 165, 255)
    
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    cv2.putText(frame, f"{emotion} {conf*100:.0f}%", (x1, y1 - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (220, 240), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    for i, label in enumerate(LABELS):
        p = probs[i]
        bar_w = int(p * 120)
        y = 40 + (i * 28)
        
        multiplier = CLASS_MULTIPLIERS.get(label, 1.0)
        label_color = (200, 200, 200)
        if multiplier > 1.5: label_color = (0, 255, 0)   
        if multiplier < 0.6: label_color = (0, 0, 255)   

        cv2.putText(frame, f"{label[:3]}:", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, label_color, 1)
        cv2.rectangle(frame, (60, y-10), (180, y), (50, 50, 50), -1)
        
        is_winner = (label == emotion) and (emotion != "Uncertain")
        bar_color = (0, 255, 255) if is_winner else ((0, 255, 0) if p > 0.3 else (100, 100, 100))
        
        cv2.rectangle(frame, (60, y-10), (60 + bar_w, y), bar_color, -1)
        cv2.putText(frame, f"{int(p*100)}%", (190, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

# ==============================
# 4. START
# ==============================
if __name__ == "__main__":
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    detector = EmotionDetector(MODEL_FILE)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 150) 
    print("🎥 Final-Tuned AI Started...")
    
    last_data = (None, 0, None, None)
    count = 0

    while True:
        ret, frame = cap.read()
        if not ret: break

        count += 1
        if count % FRAME_SKIP == 0:
            last_data = detector.predict(frame)

        emotion, conf, box, probs = last_data

        if emotion:
            draw_ui(frame, emotion, conf, box, probs)

        cv2.imshow("Emotion AI - Final", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

# this is perfect but doesnt read happy, and sad neutral mix up
# import cv2
# import mediapipe as mp
# import torch
# import torch.nn as nn
# from torchvision import models, transforms
# from PIL import Image
# from collections import deque
# import numpy as np

# # ==============================
# # 1. CONFIGURATION - TUNED FOR SENSITIVITY
# # ==============================
# MODEL_FILE = "mobilenet_v3_large_affectnet7.pth"
# FRAME_SKIP = 2
# USE_FP16 = torch.cuda.is_available()

# # Lowered from 15 to 6. This makes the model respond faster to 
# # quick expressions like "Surprise".
# SMOOTHING_WINDOW = 6 

# LABELS = ['Anger', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

# # Lowered thresholds significantly. Focal Loss models are "quieter", 
# # so we need to listen more closely.
# BASE_THRESHOLDS = {
#     "Anger": 0.30,
#     "Disgust": 0.05,
#     "Fear": 0.35,
#     "Happy": 0.00,
#     "Neutral": 0.20,
#     "Sad": 0.80,
#     "Surprise": 0.40
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
#             print(f"✅ Recalibrated Model Loaded.")
#         except:
#             print("❌ Model file not found.")
#             exit()

#         self.model.to(self.device).eval()
#         if USE_FP16: self.model.half()

#         self.prob_buffer = deque(maxlen=SMOOTHING_WINDOW)
#         self.last_stable_emotion = "Neutral"

#         self.face_detector = mp.solutions.face_detection.FaceDetection(min_detection_confidence=0.6)
#         self.transform = transforms.Compose([
#             transforms.Resize((224, 224)),
#             transforms.ToTensor(),
#             transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
#         ])

#     def predict(self, frame):
#         rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#         result = self.face_detector.process(rgb)

#         if not result.detections:
#             self.prob_buffer.clear()
#             return None, None, None

#         h, w, _ = frame.shape
#         box = result.detections[0].location_data.relative_bounding_box
#         x1, y1 = max(0, int(box.xmin * w)), max(0, int(box.ymin * h))
#         x2, y2 = min(w, int((box.xmin + box.width) * w)), min(h, int((box.ymin + box.height) * h))
        
#         face = frame[y1:y2, x1:x2]
#         if face.size == 0: return None, None, None

#         img = Image.fromarray(cv2.cvtColor(face, cv2.COLOR_BGR2RGB))
#         img = self.transform(img).unsqueeze(0).to(self.device)
#         if USE_FP16: img = img.half()

#         with torch.no_grad():
#             logits = self.model(img)
#             probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

#         self.prob_buffer.append(probs)
#         avg_probs = np.mean(self.prob_buffer, axis=0)
        
#         top_idx = np.argmax(avg_probs)
#         conf = avg_probs[top_idx]
#         emotion = LABELS[top_idx]

#         # ---- DYNAMIC CALIBRATION FOR NEUTRAL/SAD ----
#         # If the model is bias towards Sad, we give Neutral a "boost"
#         # to help it overcome the Focal Loss penalty.
#         sad_idx = LABELS.index("Sad")
#         neu_idx = LABELS.index("Neutral")
        
#         if emotion == "Sad" and avg_probs[neu_idx] > (avg_probs[sad_idx] - 0.10):
#             # If they are within 10% of each other, favor Neutral
#             emotion = "Neutral"
#             conf = avg_probs[neu_idx]

#         # ---- HYSTERESIS (The "Stickiness" Factor) ----
#         thresh = BASE_THRESHOLDS.get(emotion, 0.35)
#         # We make it very easy to stay in Happy/Surprise once detected
#         grace = 0.12 if emotion in ["Happy", "Surprise"] else 0.08
        
#         if emotion == self.last_stable_emotion:
#             effective_thresh = thresh - grace
#         else:
#             effective_thresh = thresh

#         if conf < effective_thresh:
#             final_emotion = "Uncertain"
#         else:
#             final_emotion = emotion
#             self.last_stable_emotion = emotion

#         return final_emotion, conf, (x1, y1, x2, y2)

# # ... [Main loop remains the same as your previous script] ...

# # ==============================
# # 3. MAIN LOOP
# # ==============================
# if __name__ == "__main__":
#     cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
#     detector = EmotionDetector(MODEL_FILE)

#     print("🎥 Started. Press 'Q' to Exit.")
    
#     last_res = (None, None, None)
#     frame_cnt = 0

#     while True:
#         ret, frame = cap.read()
#         if not ret: break

#         frame_cnt += 1
#         if frame_cnt % FRAME_SKIP == 0:
#             last_res = detector.predict(frame)

#         emotion, conf, box = last_res

#         if emotion:
#             x1, y1, x2, y2 = box
#             color = (0, 255, 0) if emotion != "Uncertain" else (0, 165, 255)
#             cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
#             cv2.putText(frame, f"{emotion} ({conf*100:.1f}%)", (x1, y1 - 10),
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

#         cv2.imshow("Emotion AI Stability Pro", frame)
#         if cv2.waitKey(1) & 0xFF == ord('q'): break

#     cap.release()
#     cv2.destroyAllWindows()


# #------------------------------- BEST MODEL SO FAR -------------------------------#

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
# FRAME_SKIP = 2
# SMOOTHING_WINDOW = 9
# # Use FP16 only if your GPU supports it well; otherwise, stay with Float32 for stability
# USE_FP16 = torch.cuda.is_available() 

# LABELS = [
#     'Anger',
#     'Disgust',
#     'Fear',
#     'Happy',
#     'Neutral',
#     'Sad',
#     'Surprise'
# ]

# # Adjusted thresholds based on the weighted training
# EMOTION_THRESHOLDS = {
#     "Anger": 0.40,
#     "Disgust": 0.35,
#     "Fear": 0.35,
#     "Happy": 0.50,
#     "Neutral": 0.50,
#     "Sad": 0.40,
#     "Surprise": 0.40
# }

# # ==============================
# # EMOTION DETECTOR
# # ==============================
# class EmotionDetector:
#     def __init__(self, model_path):
#         self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

#         # ---- 1. Match Architecture Exactly ----
#         self.model = models.mobilenet_v3_large(weights=None)
#         num_ftrs = self.model.classifier[0].in_features
        
#         # This MUST match the Sequential block in your train.py
#         self.model.classifier = nn.Sequential(
#             nn.Linear(num_ftrs, 1024),
#             nn.Hardswish(),
#             nn.Dropout(0.5),
#             nn.Linear(1024, len(LABELS)) 
#         )

#         # ---- 2. Load State with Error Handling ----
#         try:
#             state = torch.load(model_path, map_location=self.device, weights_only=True)
#             self.model.load_state_dict(state)
#             print(f"✅ Successfully loaded model: {model_path}")
#         except RuntimeError as e:
#             print(f"❌ Load Error: {e}")
#             print("💡 TIP: Ensure you are loading the 7-class model, not an old 8-class one.")
#             exit()

#         self.model.to(self.device).eval()

#         if USE_FP16:
#             self.model.half()

#         # ---- Preprocessing (Matches Val Transform) ----
#         self.transform = transforms.Compose([
#             transforms.Resize((224, 224)),
#             transforms.ToTensor(),
#             transforms.Normalize(
#                 mean=[0.485, 0.456, 0.406],
#                 std=[0.229, 0.224, 0.225]
#             )
#         ])

#         self.face_detector = mp.solutions.face_detection.FaceDetection(
#             model_selection=0,
#             min_detection_confidence=0.6
#         )

#         self.idx_history = deque(maxlen=SMOOTHING_WINDOW)
#         self.conf_history = deque(maxlen=SMOOTHING_WINDOW)

#     def predict(self, frame):
#         rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#         result = self.face_detector.process(rgb)

#         if not result.detections:
#             self.idx_history.clear()
#             self.conf_history.clear()
#             return None, None, None

#         h, w, _ = frame.shape
#         det = result.detections[0]
#         box = det.location_data.relative_bounding_box

#         x1 = max(0, int(box.xmin * w))
#         y1 = max(0, int(box.ymin * h))
#         x2 = min(w, int((box.xmin + box.width) * w))
#         y2 = min(h, int((box.ymin + box.height) * h))

#         face = frame[y1:y2, x1:x2]
#         if face.size == 0:
#             return None, None, None

#         # Heuristics for difficult classes
#         fh, fw, _ = face.shape
#         upper_face = face[: int(0.45 * fh), :]
#         lower_face = face[int(0.55 * fh):, :]
#         upper_energy = upper_face.std()
#         lower_energy = lower_face.std()

#         # Model inference
#         img = Image.fromarray(cv2.cvtColor(face, cv2.COLOR_BGR2RGB))
#         img = self.transform(img).unsqueeze(0).to(self.device)

#         if USE_FP16:
#             img = img.half()

#         with torch.no_grad():
#             logits = self.model(img)
#             probs = torch.softmax(logits, dim=1)[0]

#         conf, idx = torch.max(probs, dim=0)
#         conf = conf.item()
#         idx = idx.item()
#         emotion = LABELS[idx]

#         # Apply Correction Heuristics
#         if emotion in ("Fear", "Disgust"):
#             if upper_energy > lower_energy * 1.15:
#                 emotion = "Fear"
#             elif lower_energy > upper_energy * 1.15:
#                 emotion = "Disgust"

#         # Neutral Suppression (Helps catch subtle emotions)
#         neutral_idx = LABELS.index("Neutral")
#         neutral_conf = probs[neutral_idx].item()
#         if emotion == "Neutral" and conf < 0.55: # Slightly lower threshold
#             return "Uncertain", conf, (x1, y1, x2, y2)

#         # Check Threshold
#         threshold = EMOTION_THRESHOLDS.get(emotion, 0.40)
#         if conf < threshold:
#             return "Uncertain", conf, (x1, y1, x2, y2)

#         # EMA Smoothing
#         self.idx_history.append(LABELS.index(emotion))
#         self.conf_history.append(conf)

#         weights = np.linspace(0.5, 1.0, len(self.idx_history))
#         weights /= weights.sum()

#         stable_idx = int(np.round(np.sum(np.array(self.idx_history) * weights)))
#         stable_idx = max(0, min(stable_idx, len(LABELS) - 1))
#         stable_conf = float(np.sum(np.array(self.conf_history) * weights))

#         return LABELS[stable_idx], stable_conf, (x1, y1, x2, y2)

# # ==============================
# # MAIN LOOP
# # ==============================
# if __name__ == "__main__":
#     # Ensure this matches the MODEL_SAVE_PATH in your train.py
#     MODEL_FILE = "mobilenet_v3_large_affectnet7.pth" 
    
#     cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
#     detector = EmotionDetector(MODEL_FILE)

#     print(f"🎥 Detection Started using {MODEL_FILE}")

#     while True:
#         ret, frame = cap.read()
#         if not ret: break

#         # Prediction logic
#         emotion, conf, box = detector.predict(frame)

#         if emotion:
#             x1, y1, x2, y2 = box
#             color = (0, 255, 0) if emotion != "Uncertain" else (0, 255, 255)
#             cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
#             cv2.putText(frame, f"{emotion} ({conf*100:.1f}%)", (x1, y1 - 10),
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

#         cv2.imshow("Emotion AI", frame)
#         if cv2.waitKey(1) & 0xFF == ord('q'): break

#     cap.release()
#     cv2.destroyAllWindows()


#------------------------------------------------------------------------------------------------------






















# best one so far

# import cv2
# import mediapipe as mp
# import torch
# import torch.nn as nn
# from torchvision import models, transforms
# from PIL import Image
# from collections import deque

# # ================================
# # CONFIG
# # ================================
# CONF_THRESHOLD = 0.65
# SMOOTHING_WINDOW = 9
# FRAME_SKIP = 2
# USE_FP16 = torch.cuda.is_available()

# # ================================
# # EMOTION DETECTOR
# # ================================
# class EmotionDetector:
#     def __init__(self, model_path):
#         self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

#         self.labels = [
#             'Anger', 'Contempt', 'Disgust', 'Fear',
#             'Happy', 'Neutral', 'Sad', 'Surprise'
#         ]

#         self.model = models.mobilenet_v3_large(weights=None)
#         num_ftrs = self.model.classifier[0].in_features

#         self.model.classifier = nn.Sequential(
#             nn.Linear(num_ftrs, 1024),
#             nn.Hardswish(),
#             nn.Dropout(0.5),
#             nn.Linear(1024, len(self.labels))
#         )

#         state = torch.load(
#             model_path,
#             map_location=self.device,
#             weights_only=True
#         )
#         self.model.load_state_dict(state)
#         self.model.to(self.device).eval()

#         if USE_FP16:
#             self.model = self.model.half()

#         self.transform = transforms.Compose([
#             transforms.Resize((224, 224)),
#             transforms.ToTensor(),
#             transforms.Normalize(
#                 mean=[0.485, 0.456, 0.406],
#                 std=[0.229, 0.224, 0.225]
#             )
#         ])

#         self.face_detector = mp.solutions.face_detection.FaceDetection(
#             model_selection=0,
#             min_detection_confidence=0.6
#         )

#         self.history = deque(maxlen=SMOOTHING_WINDOW)
#         self.conf_history = deque(maxlen=SMOOTHING_WINDOW)

#     def predict(self, frame):
#         rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#         results = self.face_detector.process(rgb)

#         if not results.detections:
#             self.history.clear()
#             self.conf_history.clear()
#             return None, None, None

#         h, w, _ = frame.shape
#         det = results.detections[0]
#         box = det.location_data.relative_bounding_box

#         x1 = int(box.xmin * w)
#         y1 = int(box.ymin * h)
#         x2 = int((box.xmin + box.width) * w)
#         y2 = int((box.ymin + box.height) * h)

#         face = frame[y1:y2, x1:x2]
#         if face.size == 0:
#             return None, None, None

#         img = Image.fromarray(cv2.cvtColor(face, cv2.COLOR_BGR2RGB))
#         img = self.transform(img).unsqueeze(0)

#         if USE_FP16:
#             img = img.half()

#         img = img.to(self.device)

#         with torch.no_grad():
#             probs = torch.softmax(self.model(img), dim=1)[0]
#             conf, idx = torch.max(probs, dim=0)

#         conf = conf.item()
#         idx = idx.item()

#         if conf < CONF_THRESHOLD:
#             return "Uncertain", conf, (x1, y1, x2, y2)

#         self.history.append(idx)
#         self.conf_history.append(conf)

#         stable_idx = max(set(self.history), key=self.history.count)
#         stable_conf = sum(self.conf_history) / len(self.conf_history)

#         return self.labels[stable_idx], stable_conf, (x1, y1, x2, y2)


# # ================================
# # CAMERA LOOP
# # ================================
# cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
# detector = EmotionDetector("mobilenet_v3_large_best.pth")

# frame_count = 0
# last_result = (None, None, None)

# print("🎥 Emotion Detection Running — Press Q to quit")

# while True:
#     ret, frame = cap.read()
#     if not ret:
#         break

#     frame_count += 1

#     if frame_count % FRAME_SKIP == 0:
#         last_result = detector.predict(frame)

#     emotion, conf, box = last_result

#     if emotion is None:
#         cv2.putText(frame, "No Face", (20, 40),
#                     cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
#     else:
#         x1, y1, x2, y2 = box
#         color = (0, 255, 0) if emotion != "Uncertain" else (0, 255, 255)
#         cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
#         cv2.putText(
#             frame,
#             f"{emotion} ({conf*100:.1f}%)",
#             (x1, y1 - 10),
#             cv2.FONT_HERSHEY_SIMPLEX,
#             0.9,
#             color,
#             2
#         )

#     cv2.imshow("Emotion Detection", frame)
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break

# cap.release()
# cv2.destroyAllWindows()













# import time
# import collections
# import cv2
# import numpy as np
# import mediapipe as mp
# import json
# import torch
# import torch.nn as nn
# from pathlib import Path
# from torchvision.models import mobilenet_v3_small

# # ==========================================
# # CONFIGURATION
# # ==========================================
# # CHANGE 1: Point to your new AffectNet model
# MODEL_PATH = "mobilenet_best_AffectNet.pth" 
# CLASS_NAMES_PATH = "class_names.json"

# # CHANGE 2: AffectNet standard emotions (8 classes usually)
# # This is a fallback if the JSON file is missing
# DEFAULT_EMOTIONS = ['anger', 'contempt', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']

# MAX_HISTORY = 7  # Smoother predictions
# MIN_FACE_SIZE = 60
# DISPLAY_FPS = True
# CONFIDENCE_THRESHOLD = 0.40  

# # Memory paths
# MEMORY_FILE = Path("analytics/local_memory/emotion_log.json")
# BASELINE_FILE = Path("analytics/local_memory/baseline.json")
# MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

# IN_H, IN_W = 224, 224

# # ==========================================
# # SETUP & LOADING
# # ==========================================

# # 1. Load Class Names
# try:
#     if Path(CLASS_NAMES_PATH).exists():
#         with open(CLASS_NAMES_PATH, 'r') as f:
#             EMOTIONS = json.load(f)
#         print(f"✓ Loaded classes from file: {EMOTIONS}")
#     else:
#         EMOTIONS = DEFAULT_EMOTIONS
#         print(f"⚠️ Warning: {CLASS_NAMES_PATH} not found. Using default AffectNet labels.")
# except Exception as e:
#     EMOTIONS = DEFAULT_EMOTIONS
#     print(f"Error loading class names: {e}")

# NUM_CLASSES = len(EMOTIONS)
# print(f"Expecting model with {NUM_CLASSES} classes.")

# # 2. Load PyTorch Model
# DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# print(f"Device: {DEVICE}")

# try:
#     model = mobilenet_v3_small(weights=None)
    
#     # CHANGE 3: Ensure this matches your training script architecture exactly
#     model.classifier = nn.Sequential(
#         nn.Linear(576, 1024),
#         nn.Hardswish(),
#         nn.Dropout(p=0.3),
#         nn.Linear(1024, NUM_CLASSES)
#     )
    
#     # Load Weights
#     state_dict = torch.load(MODEL_PATH, map_location=DEVICE)
#     model.load_state_dict(state_dict)
#     model.to(DEVICE)
#     model.eval()
#     print("✅ AffectNet Model loaded successfully!")
    
# except FileNotFoundError:
#     print(f"❌ CRITICAL: Model file '{MODEL_PATH}' not found.")
#     print("   Please run 'train.py' first.")
#     exit()
# except Exception as e:
#     print(f"❌ Error loading model architecture: {e}")
#     exit()

# # 3. Setup MediaPipe
# mp_face_mesh = mp.solutions.face_mesh
# face_mesh = mp_face_mesh.FaceMesh(
#     max_num_faces=1,
#     refine_landmarks=True,
#     min_detection_confidence=0.6,
#     min_tracking_confidence=0.6
# )

# # Buffers
# bbox_history = collections.deque(maxlen=MAX_HISTORY)
# emotion_history = collections.deque(maxlen=MAX_HISTORY)
# memory_buffer = []

# # ==========================================
# # HELPER FUNCTIONS
# # ==========================================
# def smooth_box(history_deque, new_box):
#     history_deque.append(new_box)
#     arr = np.array(history_deque)
#     return tuple(arr.mean(axis=0).astype(int))

# def safe_crop(img, box):
#     x1, y1, x2, y2 = box
#     h, w = img.shape[:2]
#     x1, x2 = max(0, x1), min(w, x2)
#     y1, y2 = max(0, y1), min(h, y2)
#     if x2 <= x1 or y2 <= y1: return None
#     return img[y1:y2, x1:x2]

# def smooth_emotion_prediction(history_deque, new_emotion, new_confidence):
#     """Temporal smoothing"""
#     history_deque.append((new_emotion, new_confidence))
    
#     if len(history_deque) < 3:
#         return new_emotion, new_confidence
    
#     emotion_votes = {}
#     total_confidence = {}
    
#     for emotion, conf in history_deque:
#         emotion_votes[emotion] = emotion_votes.get(emotion, 0) + 1
#         total_confidence[emotion] = total_confidence.get(emotion, 0) + conf
    
#     best_emotion = max(emotion_votes, key=emotion_votes.get)
#     avg_confidence = total_confidence[best_emotion] / emotion_votes[best_emotion]
    
#     return best_emotion, avg_confidence

# def save_emotion_batch(entries):
#     if not entries: return
#     try:
#         current_data = []
#         if MEMORY_FILE.exists():
#             try:
#                 content = MEMORY_FILE.read_text()
#                 if content.strip(): current_data = json.loads(content)
#             except: pass
            
#         current_data.extend(entries)
#         if len(current_data) > 1000: current_data = current_data[-1000:]
        
#         MEMORY_FILE.write_text(json.dumps(current_data, indent=2))
#         compute_baseline(current_data)
#     except Exception as e:
#         print(f"Memory error: {e}")

# def compute_baseline(data):
#     try:
#         counts = {}
#         for d in data:
#             e = d.get('emotion')
#             if e: counts[e] = counts.get(e, 0) + 1
#         total = sum(counts.values())
#         if total > 0:
#             baseline = {k: round(v/total, 3) for k, v in counts.items()}
#             BASELINE_FILE.write_text(json.dumps(baseline, indent=2))
#     except: pass

# # ==========================================
# # PREPROCESSING
# # ==========================================
# def preprocess_face(face_roi):
#     # Resize
#     roi = cv2.resize(face_roi, (IN_W, IN_H), interpolation=cv2.INTER_CUBIC)
#     roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
    
#     # Tensor
#     roi_tensor = torch.from_numpy(roi_rgb).permute(2, 0, 1).float() / 255.0
    
#     # Normalize (Standard ImageNet)
#     mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
#     std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
#     roi_tensor = (roi_tensor - mean) / std
    
#     # Batch Dim
#     roi_tensor = roi_tensor.unsqueeze(0).to(DEVICE)
#     return roi_tensor, roi_rgb

# # ==========================================
# # MAIN LOOP
# # ==========================================
# cap = cv2.VideoCapture(0)

# prev_time = time.time()
# fps = 0.0
# frame_count = 0

# print("\n🚀 Emotion Recognition System Active (AffectNet Mode)")
# print("   Press 'q' to quit\n")

# while cap.isOpened():
#     ret, frame = cap.read()
#     if not ret: break

#     frame_count += 1
#     h, w = frame.shape[:2]
#     rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
#     results = face_mesh.process(rgb)

#     if results.multi_face_landmarks:
#         face_landmarks = results.multi_face_landmarks[0]
#         pts = np.array([[int(p.x * w), int(p.y * h)] for p in face_landmarks.landmark])

#         # Bounding Box Logic
#         x_min, y_min = np.min(pts, axis=0)
#         x_max, y_max = np.max(pts, axis=0)
        
#         box_w, box_h = x_max - x_min, y_max - y_min
#         cx, cy = x_min + box_w // 2, y_min + box_h // 2
#         size = int(max(box_w, box_h) * 1.5) 
        
#         x1, y1 = cx - size // 2, cy - size // 2
#         x2, y2 = cx + size // 2, cy + size // 2

#         fx1, fy1, fx2, fy2 = smooth_box(bbox_history, (x1, y1, x2, y2))

#         if (fx2 - fx1) > MIN_FACE_SIZE:
#             face_roi = safe_crop(frame, (fx1, fy1, fx2, fy2))
            
#             if face_roi is not None and face_roi.size > 0:
#                 try:
#                     roi_tensor, roi_rgb = preprocess_face(face_roi)
                    
#                     # Show AI view
#                     cv2.imshow("AI Vision", cv2.resize(roi_rgb, (150, 150)))

#                     # Inference
#                     with torch.no_grad():
#                         outputs = model(roi_tensor)
#                         probs = torch.nn.functional.softmax(outputs, dim=1)
#                         conf, idx = torch.max(probs, 1)
                        
#                         raw_emotion = EMOTIONS[idx.item()]
#                         raw_confidence = conf.item()
                    
#                     # Temporal Smoothing
#                     emotion_label, confidence = smooth_emotion_prediction(
#                         emotion_history, raw_emotion, raw_confidence
#                     )

#                     # Visualization
#                     if confidence > CONFIDENCE_THRESHOLD:
#                         color = (0, 255, 0) if emotion_label == 'happy' else (0, 0, 255)
                        
#                         cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), color, 2)
                        
#                         label_text = f"{emotion_label.upper()} {int(confidence*100)}%"
#                         (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                        
#                         cv2.rectangle(frame, (fx1, fy1-35), (fx1 + tw + 20, fy1), color, -1)
#                         cv2.putText(frame, label_text, (fx1+10, fy1-8), 
#                                     cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
                        
#                         # Detailed Probability Bars
#                         y_off = fy2 + 20
#                         for i, emo in enumerate(EMOTIONS):
#                             p = probs[0][i].item()
#                             if p > 0.1: 
#                                 bar_w = int(p * 100)
#                                 cv2.rectangle(frame, (fx1, y_off), (fx1 + bar_w, y_off+10), (200,200,200), -1)
#                                 cv2.putText(frame, f"{emo}", (fx1 + bar_w + 5, y_off+8), 
#                                             cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)
#                                 y_off += 15

#                         # Logging
#                         if frame_count % 15 == 0:
#                             entry = {
#                                 "timestamp": time.time(),
#                                 "emotion": emotion_label,
#                                 "confidence": round(confidence, 4)
#                             }
#                             memory_buffer.append(entry)
#                             print(f"🧠 {emotion_label:10s} | {int(confidence*100)}%")

#                             if len(memory_buffer) >= 5:
#                                 save_emotion_batch(memory_buffer)
#                                 memory_buffer = []

#                 except Exception as e:
#                     print(f"Inference error: {e}")

#     # FPS
#     if DISPLAY_FPS:
#         now = time.time()
#         fps = 0.9 * fps + 0.1 * (1 / (now - prev_time)) if (now-prev_time) > 0 else 0
#         prev_time = now
#         cv2.putText(frame, f"FPS: {int(fps)}", (10, h - 10), 
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

#     cv2.imshow("Emotion Detector (AffectNet)", frame)
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break

# # Cleanup
# save_emotion_batch(memory_buffer)
# cap.release()
# cv2.destroyAllWindows()
# print("\n👋 System exited")
# rafdb
# import time
# import collections
# import cv2
# import numpy as np
# import mediapipe as mp
# import json
# import torch
# import torch.nn as nn
# from pathlib import Path
# from torchvision.models import mobilenet_v3_small

# # ==========================================
# # CONFIGURATION
# # ==========================================
# # CHANGE 1: Match the filename from train.py
# MODEL_PATH = "mobilenet_best_RAFDB.pth" 
# CLASS_NAMES_PATH = "class_names.json"

# # RAF-DB Defaults (Fallback)
# DEFAULT_EMOTIONS = ['surprise', 'fear', 'disgust', 'happy', 'sad', 'angry', 'neutral']

# MAX_HISTORY = 7  # Smoother predictions
# MIN_FACE_SIZE = 60
# DISPLAY_FPS = True
# CONFIDENCE_THRESHOLD = 0.40  # Slightly higher threshold for cleaner output

# # Memory paths
# MEMORY_FILE = Path("analytics/local_memory/emotion_log.json")
# BASELINE_FILE = Path("analytics/local_memory/baseline.json")
# MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

# IN_H, IN_W = 224, 224

# # ==========================================
# # SETUP & LOADING
# # ==========================================

# # 1. Load Class Names
# try:
#     if Path(CLASS_NAMES_PATH).exists():
#         with open(CLASS_NAMES_PATH, 'r') as f:
#             EMOTIONS = json.load(f)
#         print(f"✓ Loaded classes from file: {EMOTIONS}")
#     else:
#         EMOTIONS = DEFAULT_EMOTIONS
#         print(f"⚠️ Warning: {CLASS_NAMES_PATH} not found. Using default RAF-DB labels.")
# except Exception as e:
#     EMOTIONS = DEFAULT_EMOTIONS
#     print(f"Error loading class names: {e}")

# NUM_CLASSES = len(EMOTIONS)

# # 2. Load PyTorch Model
# DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# print(f"Device: {DEVICE}")

# try:
#     model = mobilenet_v3_small(weights=None)
    
#     # CHANGE 2: EXACTLY MATCH THE ARCHITECTURE FROM TRAIN.PY
#     # If this is different, the weights will fail to load!
#     model.classifier = nn.Sequential(
#         nn.Linear(576, 1024),
#         nn.Hardswish(),
#         nn.Dropout(p=0.3),
#         nn.Linear(1024, NUM_CLASSES)
#     )
    
#     # Load Weights
#     state_dict = torch.load(MODEL_PATH, map_location=DEVICE)
#     model.load_state_dict(state_dict)
#     model.to(DEVICE)
#     model.eval()
#     print("✅ RAF-DB Model loaded successfully!")
    
# except FileNotFoundError:
#     print(f"❌ CRITICAL: Model file '{MODEL_PATH}' not found.")
#     print("   Please run 'train.py' first to generate the model file.")
#     exit()
# except Exception as e:
#     print(f"❌ Error loading model architecture: {e}")
#     print("   Ensure the classifier definition matches train.py exactly.")
#     exit()

# # 3. Setup MediaPipe
# mp_face_mesh = mp.solutions.face_mesh
# face_mesh = mp_face_mesh.FaceMesh(
#     max_num_faces=1,
#     refine_landmarks=True,
#     min_detection_confidence=0.6,
#     min_tracking_confidence=0.6
# )

# # Buffers
# bbox_history = collections.deque(maxlen=MAX_HISTORY)
# emotion_history = collections.deque(maxlen=MAX_HISTORY)
# memory_buffer = []

# # ==========================================
# # HELPER FUNCTIONS
# # ==========================================
# def smooth_box(history_deque, new_box):
#     history_deque.append(new_box)
#     arr = np.array(history_deque)
#     return tuple(arr.mean(axis=0).astype(int))

# def safe_crop(img, box):
#     x1, y1, x2, y2 = box
#     h, w = img.shape[:2]
#     x1, x2 = max(0, x1), min(w, x2)
#     y1, y2 = max(0, y1), min(h, y2)
#     if x2 <= x1 or y2 <= y1: return None
#     return img[y1:y2, x1:x2]

# def smooth_emotion_prediction(history_deque, new_emotion, new_confidence):
#     """Temporal smoothing: Majority vote from last 7 frames"""
#     history_deque.append((new_emotion, new_confidence))
    
#     if len(history_deque) < 3:
#         return new_emotion, new_confidence
    
#     # Count votes
#     emotion_votes = {}
#     total_confidence = {}
    
#     for emotion, conf in history_deque:
#         emotion_votes[emotion] = emotion_votes.get(emotion, 0) + 1
#         total_confidence[emotion] = total_confidence.get(emotion, 0) + conf
    
#     # Winner
#     best_emotion = max(emotion_votes, key=emotion_votes.get)
#     avg_confidence = total_confidence[best_emotion] / emotion_votes[best_emotion]
    
#     return best_emotion, avg_confidence

# def save_emotion_batch(entries):
#     if not entries: return
#     try:
#         current_data = []
#         if MEMORY_FILE.exists():
#             try:
#                 content = MEMORY_FILE.read_text()
#                 if content.strip(): current_data = json.loads(content)
#             except: pass
            
#         current_data.extend(entries)
#         if len(current_data) > 1000: current_data = current_data[-1000:]
        
#         MEMORY_FILE.write_text(json.dumps(current_data, indent=2))
#         compute_baseline(current_data)
#     except Exception as e:
#         print(f"Memory error: {e}")

# def compute_baseline(data):
#     try:
#         counts = {}
#         for d in data:
#             e = d.get('emotion')
#             if e: counts[e] = counts.get(e, 0) + 1
#         total = sum(counts.values())
#         if total > 0:
#             baseline = {k: round(v/total, 3) for k, v in counts.items()}
#             BASELINE_FILE.write_text(json.dumps(baseline, indent=2))
#     except: pass

# # ==========================================
# # PREPROCESSING
# # ==========================================
# def preprocess_face(face_roi):
#     # Resize
#     roi = cv2.resize(face_roi, (IN_W, IN_H), interpolation=cv2.INTER_CUBIC)
#     roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
    
#     # Tensor
#     roi_tensor = torch.from_numpy(roi_rgb).permute(2, 0, 1).float() / 255.0
    
#     # Normalize (Standard ImageNet)
#     mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
#     std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
#     roi_tensor = (roi_tensor - mean) / std
    
#     # Batch Dim
#     roi_tensor = roi_tensor.unsqueeze(0).to(DEVICE)
#     return roi_tensor, roi_rgb

# # ==========================================
# # MAIN LOOP
# # ==========================================
# cap = cv2.VideoCapture(0)
# # Optional: Set Camera Resolution
# # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
# # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# prev_time = time.time()
# fps = 0.0
# frame_count = 0

# print("\n🚀 Emotion Recognition System Active")
# print("   Press 'q' to quit\n")

# while cap.isOpened():
#     ret, frame = cap.read()
#     if not ret: break

#     frame_count += 1
#     h, w = frame.shape[:2]
#     rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
#     results = face_mesh.process(rgb)

#     if results.multi_face_landmarks:
#         face_landmarks = results.multi_face_landmarks[0]
#         pts = np.array([[int(p.x * w), int(p.y * h)] for p in face_landmarks.landmark])

#         # Bounding Box Logic
#         x_min, y_min = np.min(pts, axis=0)
#         x_max, y_max = np.max(pts, axis=0)
        
#         box_w, box_h = x_max - x_min, y_max - y_min
#         cx, cy = x_min + box_w // 2, y_min + box_h // 2
#         size = int(max(box_w, box_h) * 1.5) # 50% Padding for context
        
#         x1, y1 = cx - size // 2, cy - size // 2
#         x2, y2 = cx + size // 2, cy + size // 2

#         fx1, fy1, fx2, fy2 = smooth_box(bbox_history, (x1, y1, x2, y2))

#         if (fx2 - fx1) > MIN_FACE_SIZE:
#             face_roi = safe_crop(frame, (fx1, fy1, fx2, fy2))
            
#             if face_roi is not None and face_roi.size > 0:
#                 try:
#                     roi_tensor, roi_rgb = preprocess_face(face_roi)
                    
#                     # Show AI view
#                     cv2.imshow("AI Vision", cv2.resize(roi_rgb, (150, 150)))

#                     # Inference
#                     with torch.no_grad():
#                         outputs = model(roi_tensor)
#                         probs = torch.nn.functional.softmax(outputs, dim=1)
#                         conf, idx = torch.max(probs, 1)
                        
#                         raw_emotion = EMOTIONS[idx.item()]
#                         raw_confidence = conf.item()
                    
#                     # Temporal Smoothing
#                     emotion_label, confidence = smooth_emotion_prediction(
#                         emotion_history, raw_emotion, raw_confidence
#                     )

#                     # Visualization
#                     if confidence > CONFIDENCE_THRESHOLD:
#                         color = (0, 255, 0) if emotion_label == 'happy' else (0, 0, 255)
                        
#                         # Box
#                         cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), color, 2)
                        
#                         # Label Background
#                         label_text = f"{emotion_label.upper()} {int(confidence*100)}%"
#                         (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                        
#                         cv2.rectangle(frame, (fx1, fy1-35), (fx1 + tw + 20, fy1), color, -1)
#                         cv2.putText(frame, label_text, (fx1+10, fy1-8), 
#                                     cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
                        
#                         # Detailed Probability Bars
#                         y_off = fy2 + 20
#                         for i, emo in enumerate(EMOTIONS):
#                             p = probs[0][i].item()
#                             if p > 0.1: # Only show significant ones
#                                 bar_w = int(p * 100)
#                                 cv2.rectangle(frame, (fx1, y_off), (fx1 + bar_w, y_off+10), (200,200,200), -1)
#                                 cv2.putText(frame, f"{emo}", (fx1 + bar_w + 5, y_off+8), 
#                                             cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)
#                                 y_off += 15

#                         # Logging (Every 15 frames)
#                         if frame_count % 15 == 0:
#                             entry = {
#                                 "timestamp": time.time(),
#                                 "emotion": emotion_label,
#                                 "confidence": round(confidence, 4)
#                             }
#                             memory_buffer.append(entry)
#                             print(f"🧠 {emotion_label:10s} | {int(confidence*100)}%")

#                             if len(memory_buffer) >= 5:
#                                 save_emotion_batch(memory_buffer)
#                                 memory_buffer = []

#                 except Exception as e:
#                     print(f"Inference error: {e}")

#     # FPS
#     if DISPLAY_FPS:
#         now = time.time()
#         fps = 0.9 * fps + 0.1 * (1 / (now - prev_time)) if (now-prev_time) > 0 else 0
#         prev_time = now
#         cv2.putText(frame, f"FPS: {int(fps)}", (10, h - 10), 
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

#     cv2.imshow("Emotion Detector (RAF-DB)", frame)
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break

# # Cleanup
# save_emotion_batch(memory_buffer)
# cap.release()
# cv2.destroyAllWindows()
# print("\n👋 System exited")


# import time
# import collections
# import cv2
# import numpy as np
# import mediapipe as mp
# import json
# import torch
# import torch.nn as nn
# from pathlib import Path
# from torchvision.models import mobilenet_v3_small

# # ==========================================
# # CONFIGURATION
# # ==========================================
# MODEL_PATH = "mobilenet_best_FER2013.pth" 
# CLASS_NAMES_PATH = "class_names.json"
# DEFAULT_EMOTIONS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']

# MAX_HISTORY = 7  # Increased for smoother predictions
# MIN_FACE_SIZE = 60
# DISPLAY_FPS = True
# CONFIDENCE_THRESHOLD = 0.25  # Only show predictions above this threshold

# # Memory paths
# MEMORY_FILE = Path("analytics/local_memory/emotion_log.json")
# BASELINE_FILE = Path("analytics/local_memory/baseline.json")
# MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

# IN_H, IN_W = 224, 224

# # ==========================================
# # SETUP & LOADING
# # ==========================================

# # Load class names
# try:
#     if Path(CLASS_NAMES_PATH).exists():
#         with open(CLASS_NAMES_PATH, 'r') as f:
#             EMOTIONS = json.load(f)
#         print(f"✓ Loaded classes: {EMOTIONS}")
#     else:
#         EMOTIONS = DEFAULT_EMOTIONS
#         print(f"⚠️ Using default FER-2013 labels")
# except Exception as e:
#     EMOTIONS = DEFAULT_EMOTIONS
#     print(f"Error loading class names: {e}")

# NUM_CLASSES = len(EMOTIONS)

# # Load PyTorch Model
# DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# print(f"Device: {DEVICE}")

# try:
#     model = mobilenet_v3_small(weights=None)
    
#     # Match the architecture from training
#     model.classifier = nn.Sequential(
#         nn.Linear(576, 1024),
#         nn.Hardswish(),
#         nn.Dropout(p=0.3),
#         nn.Linear(1024, NUM_CLASSES)
#     )
    
#     state_dict = torch.load(MODEL_PATH, map_location=DEVICE)
#     model.load_state_dict(state_dict)
#     model.to(DEVICE)
#     model.eval()
#     print("✅ Model loaded successfully!")
    
# except FileNotFoundError:
#     print(f"❌ Model file '{MODEL_PATH}' not found. Run train.py first!")
#     exit()
# except Exception as e:
#     print(f"❌ Error loading model: {e}")
#     exit()

# # Setup MediaPipe
# mp_face_mesh = mp.solutions.face_mesh
# face_mesh = mp_face_mesh.FaceMesh(
#     max_num_faces=1,
#     refine_landmarks=True,
#     min_detection_confidence=0.6,  # Increased threshold
#     min_tracking_confidence=0.6
# )

# # Buffers
# bbox_history = collections.deque(maxlen=MAX_HISTORY)
# emotion_history = collections.deque(maxlen=MAX_HISTORY)  # NEW: Temporal smoothing
# memory_buffer = []

# # ==========================================
# # HELPER FUNCTIONS
# # ==========================================
# def smooth_box(history_deque, new_box):
#     history_deque.append(new_box)
#     arr = np.array(history_deque)
#     return tuple(arr.mean(axis=0).astype(int))

# def safe_crop(img, box):
#     x1, y1, x2, y2 = box
#     h, w = img.shape[:2]
#     x1, x2 = max(0, x1), min(w, x2)
#     y1, y2 = max(0, y1), min(h, y2)
#     if x2 <= x1 or y2 <= y1: 
#         return None
#     return img[y1:y2, x1:x2]

# def smooth_emotion_prediction(history_deque, new_emotion, new_confidence):
#     """Temporal smoothing: Use majority vote from recent predictions"""
#     history_deque.append((new_emotion, new_confidence))
    
#     if len(history_deque) < 3:
#         return new_emotion, new_confidence
    
#     # Count emotions in history
#     emotion_votes = {}
#     total_confidence = {}
    
#     for emotion, conf in history_deque:
#         emotion_votes[emotion] = emotion_votes.get(emotion, 0) + 1
#         total_confidence[emotion] = total_confidence.get(emotion, 0) + conf
    
#     # Get most common emotion
#     best_emotion = max(emotion_votes, key=emotion_votes.get)
#     avg_confidence = total_confidence[best_emotion] / emotion_votes[best_emotion]
    
#     return best_emotion, avg_confidence

# def save_emotion_batch(entries):
#     if not entries: 
#         return
    
#     try:
#         current_data = []
#         if MEMORY_FILE.exists():
#             try:
#                 content = MEMORY_FILE.read_text()
#                 if content.strip(): 
#                     current_data = json.loads(content)
#             except: 
#                 pass
            
#         current_data.extend(entries)
#         if len(current_data) > 1000: 
#             current_data = current_data[-1000:]
        
#         MEMORY_FILE.write_text(json.dumps(current_data, indent=2))
#         compute_baseline(current_data)
#     except Exception as e:
#         print(f"Memory error: {e}")

# def compute_baseline(data):
#     try:
#         counts = {}
#         for d in data:
#             e = d.get('emotion')
#             if e: 
#                 counts[e] = counts.get(e, 0) + 1
        
#         total = sum(counts.values())
#         if total > 0:
#             baseline = {k: round(v/total, 3) for k, v in counts.items()}
#             BASELINE_FILE.write_text(json.dumps(baseline, indent=2))
#     except: 
#         pass

# # ==========================================
# # PREPROCESSING (EXACTLY MATCH TRAINING)
# # ==========================================
# def preprocess_face(face_roi):
#     """Preprocess face exactly as in training"""
#     # Resize
#     roi = cv2.resize(face_roi, (IN_W, IN_H), interpolation=cv2.INTER_CUBIC)
    
#     # Convert to RGB
#     roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
    
#     # To tensor [C, H, W]
#     roi_tensor = torch.from_numpy(roi_rgb).permute(2, 0, 1).float() / 255.0
    
#     # Normalize (ImageNet stats)
#     mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
#     std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
#     roi_tensor = (roi_tensor - mean) / std
    
#     # Add batch dimension [1, C, H, W]
#     roi_tensor = roi_tensor.unsqueeze(0).to(DEVICE)
    
#     return roi_tensor, roi_rgb

# # ==========================================
# # MAIN LOOP
# # ==========================================
# cap = cv2.VideoCapture(0)
# cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
# cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
# cap.set(cv2.CAP_PROP_FPS, 30)

# prev_time = time.time()
# fps = 0.0
# frame_count = 0

# print("\n🚀 Emotion Recognition System Active")
# print("   Press 'q' to quit\n")

# while cap.isOpened():
#     ret, frame = cap.read()
#     if not ret: 
#         break

#     frame_count += 1
#     h, w = frame.shape[:2]
#     rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
#     # Detect face
#     results = face_mesh.process(rgb)

#     if results.multi_face_landmarks:
#         face_landmarks = results.multi_face_landmarks[0]
#         pts = np.array([[int(p.x * w), int(p.y * h)] for p in face_landmarks.landmark])

#         # Calculate bounding box
#         x_min, y_min = np.min(pts, axis=0)
#         x_max, y_max = np.max(pts, axis=0)
        
#         box_w, box_h = x_max - x_min, y_max - y_min
#         cx, cy = x_min + box_w // 2, y_min + box_h // 2
#         size = int(max(box_w, box_h) * 1.4)
        
#         x1, y1 = cx - size // 2, cy - size // 2
#         x2, y2 = cx + size // 2, cy + size // 2

#         # Smooth box
#         fx1, fy1, fx2, fy2 = smooth_box(bbox_history, (x1, y1, x2, y2))

#         if (fx2 - fx1) > MIN_FACE_SIZE:
#             face_roi = safe_crop(frame, (fx1, fy1, fx2, fy2))
            
#             if face_roi is not None and face_roi.size > 0:
#                 try:
#                     # Preprocess
#                     roi_tensor, roi_rgb = preprocess_face(face_roi)
                    
#                     # Show what AI sees
#                     cv2.imshow("AI Vision", cv2.resize(roi_rgb, (200, 200)))

#                     # Inference
#                     with torch.no_grad():
#                         outputs = model(roi_tensor)
#                         probs = torch.nn.functional.softmax(outputs, dim=1)
#                         conf, idx = torch.max(probs, 1)
                        
#                         raw_emotion = EMOTIONS[idx.item()]
#                         raw_confidence = conf.item()
                    
#                     # Temporal smoothing
#                     emotion_label, confidence = smooth_emotion_prediction(
#                         emotion_history, 
#                         raw_emotion, 
#                         raw_confidence
#                     )

#                     # Only display if confidence is reasonable
#                     if confidence > CONFIDENCE_THRESHOLD:
#                         # Color coding
#                         if emotion_label == 'happy':
#                             color = (0, 255, 0)
#                         elif emotion_label in ['sad', 'fear', 'angry']:
#                             color = (0, 0, 255)
#                         else:
#                             color = (255, 165, 0)
                        
#                         # Draw box
#                         cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), color, 3)
                        
#                         # Label
#                         label_text = f"{emotion_label.upper()} {int(confidence*100)}%"
                        
#                         # Background for text
#                         (text_width, text_height), _ = cv2.getTextSize(
#                             label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2
#                         )
#                         cv2.rectangle(
#                             frame, 
#                             (fx1, fy1-35), 
#                             (fx1 + text_width + 10, fy1), 
#                             color, 
#                             -1
#                         )
#                         cv2.putText(
#                             frame, 
#                             label_text, 
#                             (fx1 + 5, fy1 - 8), 
#                             cv2.FONT_HERSHEY_SIMPLEX, 
#                             0.9, 
#                             (255, 255, 255), 
#                             2
#                         )
                        
#                         # Show all class probabilities (debug)
#                         y_offset = fy2 + 25
#                         for i, emotion in enumerate(EMOTIONS):
#                             prob = probs[0][i].item()
#                             bar_width = int(prob * 150)
#                             cv2.rectangle(
#                                 frame,
#                                 (fx1, y_offset),
#                                 (fx1 + bar_width, y_offset + 15),
#                                 (100, 100, 100),
#                                 -1
#                             )
#                             cv2.putText(
#                                 frame,
#                                 f"{emotion}: {int(prob*100)}%",
#                                 (fx1 + 160, y_offset + 12),
#                                 cv2.FONT_HERSHEY_SIMPLEX,
#                                 0.4,
#                                 (255, 255, 255),
#                                 1
#                             )
#                             y_offset += 20

#                         # Log every 15 frames (~0.5 sec)
#                         if frame_count % 15 == 0:
#                             entry = {
#                                 "timestamp": time.time(),
#                                 "emotion": emotion_label,
#                                 "confidence": round(confidence, 4)
#                             }
#                             memory_buffer.append(entry)
#                             print(f"🧠 {emotion_label:10s} | Confidence: {int(confidence*100):3d}%")

#                             if len(memory_buffer) >= 5:
#                                 save_emotion_batch(memory_buffer)
#                                 memory_buffer = []

#                 except Exception as e:
#                     print(f"Prediction error: {e}")

#     # FPS Counter
#     if DISPLAY_FPS:
#         now = time.time()
#         fps = 0.9 * fps + 0.1 * (1 / (now - prev_time)) if (now-prev_time) > 0 else 0
#         prev_time = now
#         cv2.putText(
#             frame, 
#             f"FPS: {int(fps)}", 
#             (10, h - 10), 
#             cv2.FONT_HERSHEY_SIMPLEX, 
#             0.7, 
#             (0, 255, 0), 
#             2
#         )

#     cv2.imshow("Emotion Detector", frame)
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break

# # Cleanup
# save_emotion_batch(memory_buffer)
# cap.release()
# cv2.destroyAllWindows()
# print("\n👋 System exited")


# #  # emotion_detector.py
# # import time
# # import collections
# # import cv2
# # import numpy as np
# # import mediapipe as mp
# # import json
# # from pathlib import Path

# # # --- PYTORCH IMPORTS ---
# # import torch
# # import torch.nn as nn
# # from torchvision.models import mobilenet_v3_small
# # # -------------------------

# # # -------------------------
# # # CONFIG
# # # -------------------------
# # MODEL_PATH = "mobilenet_best_AffectNet.pth" 
# # EMOTIONS = ['anger', 'contempt', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']

# # MAX_HISTORY = 5 
# # MIN_FACE_SIZE = 60
# # DISPLAY_FPS = True

# # MEMORY_FILE = Path("local_memory/emotion_log.json")
# # BASELINE_FILE = Path("local_memory/baseline.json")
# # MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

# # IN_H, IN_W = 224, 224  # input size

# # # -------------------------
# # # HELPERS
# # # -------------------------
# # def smooth_point(history_deque, new_point):
# #     history_deque.append(new_point)
# #     pts = np.array(history_deque)
# #     return tuple(np.mean(pts, axis=0).astype(int))

# # def smooth_box(history_deque, new_box):
# #     history_deque.append(new_box)
# #     arr = np.array(history_deque)
# #     mean = arr.mean(axis=0).astype(int)
# #     return tuple(mean.tolist())

# # def safe_crop(img, box):
# #     x1, y1, x2, y2 = box
# #     h, w = img.shape[:2]
# #     x1 = max(0, min(w, x1))
# #     x2 = max(0, min(w, x2))
# #     y1 = max(0, min(h, y1))
# #     y2 = max(0, min(h, y2))
# #     if x2 <= x1 or y2 <= y1:
# #         return None
# #     return img[y1:y2, x1:x2]

# # # -------------- MEMORY FUNCTIONS -------------------
# # #This file writes to the emotion_log.json
# # def save_emotion_batch(entries):
# #     if not entries:
# #         return
# #     current_data = []
# #     if MEMORY_FILE.exists():
# #         try:
# #             current_data = json.loads(MEMORY_FILE.read_text())
# #         except:
# #             current_data = []
# #     current_data.extend(entries)
# #     MEMORY_FILE.write_text(json.dumps(current_data, indent=2))

# # def compute_baseline():
# #     if not MEMORY_FILE.exists(): 
# #         return
# #     try:
# #         data = json.loads(MEMORY_FILE.read_text())
# #         counts = {}
# #         for d in data:
# #             e = d['emotion']
# #             counts[e] = counts.get(e, 0) + 1
# #         total = sum(counts.values())
# #         if total > 0:
# #             baseline = {k: round(v/total, 3) for k,v in counts.items()}
# #             BASELINE_FILE.write_text(json.dumps(baseline, indent=2))
# #             print(f"Baseline Updated: {baseline}")
# #     except Exception as e:
# #         print(f"Baseline error: {e}")

# # # -------------------------
# # # LOAD PYTORCH MODEL (MobileNetV3 Small)
# # # -------------------------
# # print(f"Loading PyTorch model: {MODEL_PATH}...")
# # DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# # print("Device:", DEVICE)

# # NUM_CLASSES = len(EMOTIONS)

# # try:
# #     # instantiate model architecture
# #     model = mobilenet_v3_small(weights=None)
# #     # Replace final classifier layer robustly
# #     # many torchvision versions use classifier[-1] as the final linear
# #     if hasattr(model, "classifier") and isinstance(model.classifier, nn.Sequential):
# #         last = model.classifier[-1]
# #         if isinstance(last, nn.Linear):
# #             in_features = last.in_features
# #             model.classifier[-1] = nn.Linear(in_features, NUM_CLASSES)
# #         else:
# #             # fallback: replace whole classifier
# #             model.classifier = nn.Sequential(nn.Linear(model.classifier[0].in_features, NUM_CLASSES))
# #     else:
# #         # fallback generic
# #         model.classifier = nn.Sequential(nn.Linear(576, NUM_CLASSES))

# #     # load weights
# #     state = torch.load(MODEL_PATH, map_location=DEVICE)
# #     model.load_state_dict(state)
# #     model = model.to(DEVICE)
# #     model.eval()
# #     print(f" PyTorch MobileNetV3 model loaded. Input: {IN_H}x{IN_W}")
# # except Exception as e:
# #     print(f" Error loading PyTorch model: {e}")
# #     raise SystemExit(1)

# # # -------------------------
# # # INITIALIZE MEDIAPIPE
# # # -------------------------
# # mp_face_mesh = mp.solutions.face_mesh
# # face_mesh = mp_face_mesh.FaceMesh(
# #     max_num_faces=1,
# #     refine_landmarks=True, 
# #     min_detection_confidence=0.5,
# #     min_tracking_confidence=0.5
# # )

# # LEFT_IRIS_CENTER = 468
# # RIGHT_IRIS_CENTER = 473
# # bbox_history = collections.deque(maxlen=MAX_HISTORY)
# # l_iris_hist = collections.deque(maxlen=MAX_HISTORY)
# # r_iris_hist = collections.deque(maxlen=MAX_HISTORY)

# # memory_buffer = []

# # # -------------------------
# # # VIDEO LOOP
# # # -------------------------
# # cap = cv2.VideoCapture(0)
# # prev_time = time.time()
# # frame_count = 0
# # fps = 0.0

# # print("AffectNet Hybrid System Running with PyTorch MobileNetV3...")

# # while cap.isOpened():
# #     ret, frame = cap.read()
# #     if not ret: break

# #     frame_count += 1
# #     h, w = frame.shape[:2]
# #     rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
# #     results = face_mesh.process(rgb)

# #     if results.multi_face_landmarks:
# #         face_landmarks = results.multi_face_landmarks[0]
# #         pts = np.array([[int(p.x * w), int(p.y * h)] for p in face_landmarks.landmark])

# #         # SQUARE CROP LOGIC
# #         x_min, y_min = np.min(pts[:,0]), np.min(pts[:,1])
# #         x_max, y_max = np.max(pts[:,0]), np.max(pts[:,1])
# #         box_w = x_max - x_min
# #         box_h = y_max - y_min
# #         cx = x_min + box_w // 2
# #         cy = y_min + box_h // 2
# #         max_dim = max(box_w, box_h)
# #         pad = int(max_dim * 0.40) 
# #         size = max_dim + pad
# #         sx1 = cx - size // 2
# #         sy1 = cy - size // 2
# #         sx2 = cx + size // 2
# #         sy2 = cy + size // 2

# #         smooth_bbox = smooth_box(bbox_history, (sx1, sy1, sx2, sy2))
# #         fx1, fy1, fx2, fy2 = smooth_bbox

# #         if (fx2 - fx1) > MIN_FACE_SIZE:
# #             face_roi = safe_crop(frame, (fx1, fy1, fx2, fy2))
# #             if face_roi is not None and face_roi.size > 0:
# #                 try:
# #                     roi = cv2.resize(face_roi, (IN_W, IN_H), interpolation=cv2.INTER_CUBIC)
# #                     roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)

# #                     cv2.imshow("What AI Sees", cv2.resize(roi_rgb, (200, 200)))

# #                     # PyTorch preprocessing
# #                     roi_pp = roi_rgb.astype(np.float32) / 255.0
# #                     roi_tensor = torch.from_numpy(roi_pp).permute(2,0,1).unsqueeze(0).to(DEVICE)
                    
# #                     # --- ADD NORMALIZATION HERE --- )  i added this ;;;;
# #                     mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1).to(DEVICE)
# #                     std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1).to(DEVICE)

# #                     roi_tensor = (roi_tensor - mean) / std
# #                     # -------------------------------

# #                     # inference
# #                     with torch.no_grad():
# #                         outputs = model(roi_tensor)
# #                         probs = torch.nn.functional.softmax(outputs, dim=1)
# #                         conf, idx_tensor = torch.max(probs, 1)
# #                         idx = idx_tensor.item()
# #                         conf = conf.item()
# #                         label = EMOTIONS[idx]

# #                     color = (0,255,0) if label == 'happy' else (0,0,255)
# #                     cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), color, 2)
# #                     label_text = f"{label} {int(conf*100)}%"
# #                     cv2.rectangle(frame, (fx1, fy1-30), (fx1+200, fy1), color, -1)
# #                     cv2.putText(frame, label_text, (fx1 + 5, fy1 - 5),
# #                                 cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

# #                     if frame_count % 15 == 0:
# #                         entry = {
# #                             "timestamp": time.time(),
# #                             "emotion": label,
# #                             "confidence": round(conf, 4)
# #                         }
# #                         memory_buffer.append(entry)
# #                         print(f"Logged: {label}")

# #                         if len(memory_buffer) >= 4:
# #                             save_emotion_batch(memory_buffer)
# #                             memory_buffer = []

# #                 except Exception as ex:
# #                     print(f"Error in prediction loop: {ex}")

# #         # IRIS TRACKING
# #         if LEFT_IRIS_CENTER < len(pts) and RIGHT_IRIS_CENTER < len(pts):
# #             l_pt = pts[LEFT_IRIS_CENTER]
# #             r_pt = pts[RIGHT_IRIS_CENTER]
# #             l_smooth = smooth_point(l_iris_hist, l_pt)
# #             r_smooth = smooth_point(r_iris_hist, r_pt)
# #             cv2.circle(frame, l_smooth, 4, (0,255,255), -1, cv2.LINE_AA)
# #             cv2.circle(frame, r_smooth, 4, (0,255,255), -1, cv2.LINE_AA)
# #             cv2.line(frame, l_smooth, r_smooth, (255,255,0), 1, cv2.LINE_AA)

# #     if DISPLAY_FPS:
# #         now = time.time()
# #         fps = 0.9 * fps + 0.1 * (1 / (now - prev_time)) if (now-prev_time) > 0 else 0
# #         prev_time = now
# #         cv2.putText(frame, f"FPS: {int(fps)}", (10, h - 10), 
# #                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

# #     cv2.imshow("AffectNet Hybrid System", frame)
# #     if cv2.waitKey(1) & 0xFF == ord('q'):
# #         break

# # # CLEANUP
# # save_emotion_batch(memory_buffer)
# # compute_baseline()
# # cap.release()
# # cv2.destroyAllWindows()
# # print("👋 System exited safely.")

