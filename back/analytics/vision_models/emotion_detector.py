import time
import collections
import cv2
import numpy as np
import mediapipe as mp
import json
import torch
import torch.nn as nn
from pathlib import Path
from torchvision.models import mobilenet_v3_small

# ==========================================
# CONFIGURATION
# ==========================================
# Make sure this matches the filename saved by train.py
MODEL_PATH = "mobilenet_best_FER2013.pth" 
CLASS_NAMES_PATH = "class_names.json"

# FER-2013 Standard Defaults (Fallback if json missing)
# Note: FER-2013 has 7 classes. AffectNet had 8.
DEFAULT_EMOTIONS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']

MAX_HISTORY = 5 
MIN_FACE_SIZE = 60
DISPLAY_FPS = True

# Memory paths
MEMORY_FILE = Path("analytics/local_memory/emotion_log.json")
BASELINE_FILE = Path("analytics/local_memory/baseline.json")

# Ensure directories exist
MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

# Input size for MobileNetV3
IN_H, IN_W = 224, 224 

# ==========================================
# SETUP & LOADING
# ==========================================

# 1. LOAD CLASS NAMES
# -------------------
try:
    if Path(CLASS_NAMES_PATH).exists():
        with open(CLASS_NAMES_PATH, 'r') as f:
            EMOTIONS = json.load(f)
        print(f"Loaded class names from file: {EMOTIONS}")
    else:
        EMOTIONS = DEFAULT_EMOTIONS
        print(f"⚠️ {CLASS_NAMES_PATH} not found. Using default FER-2013 labels.")
except Exception as e:
    EMOTIONS = DEFAULT_EMOTIONS
    print(f"Error loading class names: {e}")

NUM_CLASSES = len(EMOTIONS)
print(f"Expecting model with {NUM_CLASSES} classes.")

# 2. LOAD PYTORCH MODEL
# ---------------------
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Loading Model on: {DEVICE}")

try:
    # Initialize Architecture (Must match train.py exactly)
    model = mobilenet_v3_small(weights=None) # No weights needed, we load our own
    
    # Replace the last layer to match our number of classes (7)
    # MobileNetV3 classifier structure: Sequential(Linear, Hardswish, Dropout, Linear)
    # We are changing that last Linear layer.
    model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, NUM_CLASSES)
    
    # Load the trained weights
    state_dict = torch.load(MODEL_PATH, map_location=DEVICE)
    model.load_state_dict(state_dict)
    
    model.to(DEVICE)
    model.eval() # Set to evaluation mode (freezes Dropout/BatchNorm)
    print("✅ Model loaded successfully!")
    
except FileNotFoundError:
    print(f"❌ CRITICAL ERROR: Could not find model file '{MODEL_PATH}'")
    print("   Did you run train.py?")
    exit()
except Exception as e:
    print(f"❌ Error loading model: {e}")
    exit()

# 3. SETUP MEDIAPIPE (FACE DETECTOR)
# ----------------------------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True, 
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# 4. MEMORY & HISTORY BUFFERS
# ---------------------------
bbox_history = collections.deque(maxlen=MAX_HISTORY)
memory_buffer = []

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def smooth_box(history_deque, new_box):
    history_deque.append(new_box)
    arr = np.array(history_deque)
    return tuple(arr.mean(axis=0).astype(int))

def safe_crop(img, box):
    x1, y1, x2, y2 = box
    h, w = img.shape[:2]
    x1, x2 = max(0, x1), min(w, x2)
    y1, y2 = max(0, y1), min(h, y2)
    if x2 <= x1 or y2 <= y1: return None
    return img[y1:y2, x1:x2]

def save_emotion_batch(entries):
    """Appends recent emotions to the JSON log file."""
    if not entries: return
    
    try:
        current_data = []
        if MEMORY_FILE.exists():
            try:
                content = MEMORY_FILE.read_text()
                if content.strip(): current_data = json.loads(content)
            except: pass # File might be corrupt/empty
            
        current_data.extend(entries)
        # Keep file size sane (last 1000 entries)
        if len(current_data) > 1000: current_data = current_data[-1000:]
        
        MEMORY_FILE.write_text(json.dumps(current_data, indent=2))
        # Update baseline after saving
        compute_baseline(current_data)
    except Exception as e:
        print(f"Memory Save Error: {e}")

def compute_baseline(data):
    """Updates the baseline distribution (e.g., User is 50% Happy usually)."""
    try:
        counts = {}
        for d in data:
            e = d.get('emotion')
            if e: counts[e] = counts.get(e, 0) + 1
        
        total = sum(counts.values())
        if total > 0:
            baseline = {k: round(v/total, 3) for k,v in counts.items()}
            BASELINE_FILE.write_text(json.dumps(baseline, indent=2))
    except Exception: pass

# ==========================================
# MAIN LOOP
# ==========================================
cap = cv2.VideoCapture(0)
prev_time = time.time()
fps = 0.0
frame_count = 0

print("\n🚀 Starting Emotion Recognition System...")
print("   Press 'q' to quit.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    frame_count += 1
    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # 1. Detect Face Landmarks
    results = face_mesh.process(rgb)

    if results.multi_face_landmarks:
        face_landmarks = results.multi_face_landmarks[0]
        pts = np.array([[int(p.x * w), int(p.y * h)] for p in face_landmarks.landmark])

        # 2. Calculate Bounding Box
        x_min, y_min = np.min(pts, axis=0)
        x_max, y_max = np.max(pts, axis=0)
        
        # Make it square + padding
        box_w, box_h = x_max - x_min, y_max - y_min
        cx, cy = x_min + box_w // 2, y_min + box_h // 2
        size = int(max(box_w, box_h) * 1.4) # 40% padding
        
        x1, y1 = cx - size // 2, cy - size // 2
        x2, y2 = cx + size // 2, cy + size // 2

        # Smooth the jittery box
        fx1, fy1, fx2, fy2 = smooth_box(bbox_history, (x1, y1, x2, y2))

        # 3. Process Face if large enough
        if (fx2 - fx1) > MIN_FACE_SIZE:
            face_roi = safe_crop(frame, (fx1, fy1, fx2, fy2))
            
            if face_roi is not None and face_roi.size > 0:
                try:
                    # [PREPROCESS] Resize -> RGB -> Normalize
                    roi = cv2.resize(face_roi, (IN_W, IN_H), interpolation=cv2.INTER_CUBIC)
                    roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
                    
                    # Debug View: See what the AI sees
                    cv2.imshow("AI Vision", cv2.resize(roi_rgb, (150, 150)))

                    # To Tensor
                    roi_tensor = torch.from_numpy(roi_rgb).permute(2,0,1).float() / 255.0
                    
                    # Normalize (Standard ImageNet stats)
                    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
                    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
                    roi_tensor = (roi_tensor - mean) / std
                    
                    # Add batch dimension -> [1, 3, 224, 224]
                    roi_tensor = roi_tensor.unsqueeze(0).to(DEVICE)

                    # [INFERENCE]
                    with torch.no_grad():
                        outputs = model(roi_tensor)
                        probs = torch.nn.functional.softmax(outputs, dim=1)
                        conf, idx = torch.max(probs, 1)
                        
                        emotion_label = EMOTIONS[idx.item()]
                        confidence = conf.item()

                    # [VISUALIZE]
                    color = (0, 255, 0) if emotion_label == 'happy' else (0, 0, 255)
                    
                    # Draw Box
                    cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), color, 2)
                    
                    # Draw Label Background
                    cv2.rectangle(frame, (fx1, fy1-30), (fx1+200, fy1), color, -1)
                    cv2.putText(frame, f"{emotion_label} {int(confidence*100)}%", 
                                (fx1+5, fy1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

                    # [LOGGING] Every 15 frames (approx 0.5 sec)
                    if frame_count % 15 == 0:
                        entry = {
                            "timestamp": time.time(),
                            "emotion": emotion_label,
                            "confidence": round(confidence, 4)
                        }
                        memory_buffer.append(entry)
                        print(f"🧠 Logged: {emotion_label} ({int(confidence*100)}%)")

                        # Flush to disk every 5 logs
                        if len(memory_buffer) >= 5:
                            save_emotion_batch(memory_buffer)
                            memory_buffer = []

                except Exception as e:
                    print(f"Prediction Error: {e}")

    # FPS Counter
    if DISPLAY_FPS:
        now = time.time()
        fps = 0.9 * fps + 0.1 * (1 / (now - prev_time)) if (now-prev_time) > 0 else 0
        prev_time = now
        cv2.putText(frame, f"FPS: {int(fps)}", (10, h - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

    cv2.imshow("Emotion Detector (FER-2013)", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
save_emotion_batch(memory_buffer)
cap.release()
cv2.destroyAllWindows()
print("👋 System exited.")


#  # emotion_detector.py
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
# #This file writes to the emotion_log.json
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
#             print(f"Baseline Updated: {baseline}")
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
#     print(f" PyTorch MobileNetV3 model loaded. Input: {IN_H}x{IN_W}")
# except Exception as e:
#     print(f" Error loading PyTorch model: {e}")
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

# print("AffectNet Hybrid System Running with PyTorch MobileNetV3...")

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
#         pad = int(max_dim * 0.40) 
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

#                     roi_tensor = (roi_tensor - mean) / std
#                     # -------------------------------

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
#                         print(f"Logged: {label}")

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

