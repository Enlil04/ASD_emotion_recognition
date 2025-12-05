import time
import cv2
import numpy as np
from pathlib import Path
import collections
import os

# ---- MEDIAPIPE ----
import mediapipe as mp
mp_face_mesh = mp.solutions.face_mesh

# ---- PYTORCH ----
import torch
import torch.nn as nn
from torchvision.models import mobilenet_v3_small


# 1. Ensure the model architecture matches the 8 classes used in training
class EmotionModel(nn.Module):
    # CRITICAL FIX: Changed num_classes from 7 to 8
    def __init__(self, num_classes=8): 
        super().__init__()
        self.model = mobilenet_v3_small(weights="DEFAULT")
        in_features = self.model.classifier[3].in_features
        self.model.classifier[3] = nn.Linear(in_features, num_classes)

    def forward(self, x):
        return self.model(x)


class EmotionDetector:
    
    # 2. Update model path and class count to match training script
    # ASSUMPTION: The model is saved in a 'models' directory next to the script, 
    # as suggested in the previous response, or in the current directory.
    # We will use the direct filename since that was in your original file list.
    MODEL_FILENAME = "mobilenet_best_AffectNet.pth"
    
    # CRITICAL FIX: Changed num_classes from 7 to 8
    def __init__(self, model_path=MODEL_FILENAME, num_classes=8): 
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.model = EmotionModel(num_classes=num_classes).to(self.device)
        self.load_model(model_path)

        self.face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # 3. Update Class labels for 8 classes (Assuming AffectNet/FER-2013 plus Contempt)
        # You MUST verify the order of these labels against your training dataset's folder names!
        self.labels = ["angry", "contempt", "digust", "fear", "happy", "neutral", "sad", "surprise"]

        # FPS tracking
        self.fps_queue = collections.deque(maxlen=10)

    def load_model(self, path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"[ERROR] Model file not found: {path}. Please run the training script and ensure the model path is correct.")
            
        self.model.load_state_dict(torch.load(path, map_location=self.device))
        self.model.eval()
        print(f"[INFO] Model loaded successfully from {path}.")

    # 4. CRITICAL FIX: Add normalization to match training preprocessing
    def preprocess(self, image):
        img = cv2.resize(image, (224, 224))
        
        # NOTE: Cropped face is BGR from cv2.cap.read(), but model expects RGB.
        # This conversion is often necessary for correct color channel order.
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        img = img.astype(np.float32) / 255.0
        
        # Normalization values used in your training script (val_transform)
        mean = np.array([0.485, 0.456, 0.406]).reshape(1, 1, 3)
        std = np.array([0.229, 0.224, 0.225]).reshape(1, 1, 3)
        img = (img - mean) / std

        img = img.transpose(2, 0, 1) # HWC to CHW
        # Use torch.from_numpy() for potentially faster tensor creation
        img_tensor = torch.from_numpy(img).unsqueeze(0).to(self.device, dtype=torch.float)
        return img_tensor

    def predict(self, face_img):
        with torch.no_grad():
            output = self.model(self.preprocess(face_img))
        return torch.softmax(output, dim=1)[0].cpu().numpy()

    def draw_results(self, frame, results, emotions):
        if not results or not results.multi_face_landmarks:
            return frame

        h, w, _ = frame.shape
        face = results.multi_face_landmarks[0]

        # Draw key landmarks (eyes + nose)
        landmark_indices = [33, 133, 362, 263, 1]
        for idx in landmark_indices:
            lm = face.landmark[idx]
            x, y = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (x, y), 2, (255, 255, 0), -1)

        # Show emotion on screen
        best_idx = np.argmax(emotions)
        text = f"{self.labels[best_idx]} ({emotions[best_idx]:.2f})"
        cv2.putText(frame, text, (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        return frame

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[ERROR] Cannot access the webcam.")
            return

        while True:
            start = time.time()
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Failed to read frame.")
                break
            
            # Mediapipe requires RGB
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb)

            emotions = None
            if results.multi_face_landmarks:
                # Crop face using bounding box
                h, w, _ = frame.shape
                face = results.multi_face_landmarks[0]
                xs = [lm.x for lm in face.landmark]
                ys = [lm.y for lm in face.landmark]
                x1, x2 = int(min(xs) * w), int(max(xs) * w)
                y1, y2 = int(min(ys) * h), int(max(ys) * h)

                # Add margin and clamp bounds
                margin = int((x2 - x1) * 0.1) 
                x1, y1 = max(0, x1 - margin), max(0, y1 - margin)
                x2, y2 = min(w, x2 + margin), min(h, y2 + margin)

                face_img = frame[y1:y2, x1:x2]
                
                # Draw the bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                
                if face_img.size > 0:
                    emotions = self.predict(face_img)

            # Pass a zero array of size 8 if no face is found (since model is 8-class)
            frame = self.draw_results(frame, results, emotions if emotions is not None else [0]*8)

            # FPS
            fps = 1.0 / (time.time() - start)
            self.fps_queue.append(fps)
            cv2.putText(frame, f"FPS: {int(np.mean(self.fps_queue))}", (10, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

            cv2.imshow("Emotion Detector", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    detector = EmotionDetector()
    detector.run()

 # emotion_detector.py
# import time
# import collections
# import cv2
# import numpy as np
# import mediapipe as mp
# import json
# from pathlib import Path

# # --- PYTORCH IMPORTS ---
# import torch
# import torch.nn as nn
# from torchvision.models import mobilenet_v3_small
# # -------------------------

# # -------------------------
# # CONFIG
# # -------------------------
# MODEL_PATH = "mobilenet_best_AffectNet.pth" 
# EMOTIONS = ['anger', 'contempt', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']

# MAX_HISTORY = 5 
# MIN_FACE_SIZE = 60
# DISPLAY_FPS = True

# MEMORY_FILE = Path("local_memory/emotion_log.json")
# BASELINE_FILE = Path("local_memory/baseline.json")
# MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

# IN_H, IN_W = 224, 224  # input size

# # -------------------------
# # HELPERS
# # -------------------------
# def smooth_point(history_deque, new_point):
#     history_deque.append(new_point)
#     pts = np.array(history_deque)
#     return tuple(np.mean(pts, axis=0).astype(int))

# def smooth_box(history_deque, new_box):
#     history_deque.append(new_box)
#     arr = np.array(history_deque)
#     mean = arr.mean(axis=0).astype(int)
#     return tuple(mean.tolist())

# def safe_crop(img, box):
#     x1, y1, x2, y2 = box
#     h, w = img.shape[:2]
#     x1 = max(0, min(w, x1))
#     x2 = max(0, min(w, x2))
#     y1 = max(0, min(h, y1))
#     y2 = max(0, min(h, y2))
#     if x2 <= x1 or y2 <= y1:
#         return None
#     return img[y1:y2, x1:x2]

# # -------------- MEMORY FUNCTIONS -------------------
# def save_emotion_batch(entries):
#     if not entries:
#         return
#     current_data = []
#     if MEMORY_FILE.exists():
#         try:
#             current_data = json.loads(MEMORY_FILE.read_text())
#         except:
#             current_data = []
#     current_data.extend(entries)
#     MEMORY_FILE.write_text(json.dumps(current_data, indent=2))

# def compute_baseline():
#     if not MEMORY_FILE.exists(): 
#         return
#     try:
#         data = json.loads(MEMORY_FILE.read_text())
#         counts = {}
#         for d in data:
#             e = d['emotion']
#             counts[e] = counts.get(e, 0) + 1
#         total = sum(counts.values())
#         if total > 0:
#             baseline = {k: round(v/total, 3) for k,v in counts.items()}
#             BASELINE_FILE.write_text(json.dumps(baseline, indent=2))
#             print(f"📊 Baseline Updated: {baseline}")
#     except Exception as e:
#         print(f"Baseline error: {e}")

# # -------------------------
# # LOAD PYTORCH MODEL (MobileNetV3 Small)
# # -------------------------
# print(f"Loading PyTorch model: {MODEL_PATH}...")
# DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# print("Device:", DEVICE)

# NUM_CLASSES = len(EMOTIONS)

# try:
#     # instantiate model architecture
#     model = mobilenet_v3_small(weights=None)
#     # Replace final classifier layer robustly
#     # many torchvision versions use classifier[-1] as the final linear
#     if hasattr(model, "classifier") and isinstance(model.classifier, nn.Sequential):
#         last = model.classifier[-1]
#         if isinstance(last, nn.Linear):
#             in_features = last.in_features
#             model.classifier[-1] = nn.Linear(in_features, NUM_CLASSES)
#         else:
#             # fallback: replace whole classifier
#             model.classifier = nn.Sequential(nn.Linear(model.classifier[0].in_features, NUM_CLASSES))
#     else:
#         # fallback generic
#         model.classifier = nn.Sequential(nn.Linear(576, NUM_CLASSES))

#     # load weights
#     state = torch.load(MODEL_PATH, map_location=DEVICE)
#     model.load_state_dict(state)
#     model = model.to(DEVICE)
#     model.eval()
#     print(f"✅ PyTorch MobileNetV3 model loaded. Input: {IN_H}x{IN_W}")
# except Exception as e:
#     print(f"❌ Error loading PyTorch model: {e}")
#     raise SystemExit(1)

# # -------------------------
# # INITIALIZE MEDIAPIPE
# # -------------------------
# mp_face_mesh = mp.solutions.face_mesh
# face_mesh = mp_face_mesh.FaceMesh(
#     max_num_faces=1,
#     refine_landmarks=True, 
#     min_detection_confidence=0.5,
#     min_tracking_confidence=0.5
# )

# LEFT_IRIS_CENTER = 468
# RIGHT_IRIS_CENTER = 473
# bbox_history = collections.deque(maxlen=MAX_HISTORY)
# l_iris_hist = collections.deque(maxlen=MAX_HISTORY)
# r_iris_hist = collections.deque(maxlen=MAX_HISTORY)

# memory_buffer = []

# # -------------------------
# # VIDEO LOOP
# # -------------------------
# cap = cv2.VideoCapture(0)
# prev_time = time.time()
# frame_count = 0
# fps = 0.0

# print("🚀 AffectNet Hybrid System Running with PyTorch MobileNetV3...")

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

#         # SQUARE CROP LOGIC
#         x_min, y_min = np.min(pts[:,0]), np.min(pts[:,1])
#         x_max, y_max = np.max(pts[:,0]), np.max(pts[:,1])
#         box_w = x_max - x_min
#         box_h = y_max - y_min
#         cx = x_min + box_w // 2
#         cy = y_min + box_h // 2
#         max_dim = max(box_w, box_h)
#         pad = int(max_dim * 0.15) 
#         size = max_dim + pad
#         sx1 = cx - size // 2
#         sy1 = cy - size // 2
#         sx2 = cx + size // 2
#         sy2 = cy + size // 2

#         smooth_bbox = smooth_box(bbox_history, (sx1, sy1, sx2, sy2))
#         fx1, fy1, fx2, fy2 = smooth_bbox

#         if (fx2 - fx1) > MIN_FACE_SIZE:
#             face_roi = safe_crop(frame, (fx1, fy1, fx2, fy2))
#             if face_roi is not None and face_roi.size > 0:
#                 try:
#                     roi = cv2.resize(face_roi, (IN_W, IN_H), interpolation=cv2.INTER_CUBIC)
#                     roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)

#                     cv2.imshow("What AI Sees", cv2.resize(roi_rgb, (200, 200)))

#                     # PyTorch preprocessing
#                     roi_pp = roi_rgb.astype(np.float32) / 255.0
#                     roi_tensor = torch.from_numpy(roi_pp).permute(2,0,1).unsqueeze(0).to(DEVICE)
                    
#                     # --- ADD NORMALIZATION HERE --- )  i added this ;;;;
#                     mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1).to(DEVICE)
#                     std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1).to(DEVICE)

#                     # inference
#                     with torch.no_grad():
#                         outputs = model(roi_tensor)
#                         probs = torch.nn.functional.softmax(outputs, dim=1)
#                         conf, idx_tensor = torch.max(probs, 1)
#                         idx = idx_tensor.item()
#                         conf = conf.item()
#                         label = EMOTIONS[idx]

#                     color = (0,255,0) if label == 'happy' else (0,0,255)
#                     cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), color, 2)
#                     label_text = f"{label} {int(conf*100)}%"
#                     cv2.rectangle(frame, (fx1, fy1-30), (fx1+200, fy1), color, -1)
#                     cv2.putText(frame, label_text, (fx1 + 5, fy1 - 5),
#                                 cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

#                     if frame_count % 15 == 0:
#                         entry = {
#                             "timestamp": time.time(),
#                             "emotion": label,
#                             "confidence": round(conf, 4)
#                         }
#                         memory_buffer.append(entry)
#                         print(f"📝 Logged: {label}")

#                         if len(memory_buffer) >= 4:
#                             save_emotion_batch(memory_buffer)
#                             memory_buffer = []

#                 except Exception as ex:
#                     print(f"Error in prediction loop: {ex}")

#         # IRIS TRACKING
#         if LEFT_IRIS_CENTER < len(pts) and RIGHT_IRIS_CENTER < len(pts):
#             l_pt = pts[LEFT_IRIS_CENTER]
#             r_pt = pts[RIGHT_IRIS_CENTER]
#             l_smooth = smooth_point(l_iris_hist, l_pt)
#             r_smooth = smooth_point(r_iris_hist, r_pt)
#             cv2.circle(frame, l_smooth, 4, (0,255,255), -1, cv2.LINE_AA)
#             cv2.circle(frame, r_smooth, 4, (0,255,255), -1, cv2.LINE_AA)
#             cv2.line(frame, l_smooth, r_smooth, (255,255,0), 1, cv2.LINE_AA)

#     if DISPLAY_FPS:
#         now = time.time()
#         fps = 0.9 * fps + 0.1 * (1 / (now - prev_time)) if (now-prev_time) > 0 else 0
#         prev_time = now
#         cv2.putText(frame, f"FPS: {int(fps)}", (10, h - 10), 
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

#     cv2.imshow("AffectNet Hybrid System", frame)
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break

# # CLEANUP
# save_emotion_batch(memory_buffer)
# compute_baseline()
# cap.release()
# cv2.destroyAllWindows()
# print("👋 System exited safely.")

