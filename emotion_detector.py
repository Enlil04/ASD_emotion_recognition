import time
import collections
import cv2
import numpy as np
import mediapipe as mp
import tensorflow as tf

# -------------------------
# CONFIG
# -------------------------
MODEL_PATH = "mobilenet_best.h5"   
# Standard alphabetical order for FER-2013
EMOTIONS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']

MAX_HISTORY = 5                       
MIN_FACE_SIZE = 60                    
DISPLAY_FPS = True

# -------------------------
# HELPERS
# -------------------------
def smooth_point(history_deque, new_point):
    history_deque.append(new_point)
    pts = np.array(history_deque)
    return tuple(np.mean(pts, axis=0).astype(int))

def smooth_box(history_deque, new_box):
    history_deque.append(new_box)
    arr = np.array(history_deque)
    mean = arr.mean(axis=0).astype(int)
    return tuple(mean.tolist())

def safe_crop(img, box):
    x1, y1, x2, y2 = box
    h, w = img.shape[:2]
    x1 = max(0, min(w, x1))
    x2 = max(0, min(w, x2))
    y1 = max(0, min(h, y1))
    y2 = max(0, min(h, y2))
    if x2 <= x1 or y2 <= y1:
        return None
    return img[y1:y2, x1:x2]

# -------------------------
# LOAD MODEL
# -------------------------
print(f"Loading model: {MODEL_PATH}...")
try:
    model = tf.keras.models.load_model(MODEL_PATH, compile=False)
    _, IN_H, IN_W, IN_C = model.input_shape
    print(f"✅ Model loaded! Expecting input: {IN_H}x{IN_W}")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    exit()

# -------------------------
# INITIALIZE MEDIAPIPE
# -------------------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,   
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

LEFT_IRIS_CENTER = 468
RIGHT_IRIS_CENTER = 473
bbox_history = collections.deque(maxlen=MAX_HISTORY)
l_iris_hist = collections.deque(maxlen=MAX_HISTORY)
r_iris_hist = collections.deque(maxlen=MAX_HISTORY)

# -------------------------
# VIDEO LOOP
# -------------------------
cap = cv2.VideoCapture(0)
prev_time = time.time()
frame_count = 0
fps = 0.0

print("🚀 Hybrid System Running. Look for the 'What AI Sees' window.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    frame_count += 1
    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    if results.multi_face_landmarks:
        face_landmarks = results.multi_face_landmarks[0]
        pts = np.array([[int(p.x * w), int(p.y * h)] for p in face_landmarks.landmark])

        # 1. FORCE SQUARE CROP
        x_min, y_min = np.min(pts[:,0]), np.min(pts[:,1])
        x_max, y_max = np.max(pts[:,0]), np.max(pts[:,1])
        
        box_w = x_max - x_min
        box_h = y_max - y_min
        cx = x_min + box_w // 2
        cy = y_min + box_h // 2
        
        max_dim = max(box_w, box_h)
        pad = int(max_dim * 0.15) 
        size = max_dim + pad
        
        sx1 = cx - size // 2
        sy1 = cy - size // 2
        sx2 = cx + size // 2
        sy2 = cy + size // 2

        smooth_bbox = smooth_box(bbox_history, (sx1, sy1, sx2, sy2))
        fx1, fy1, fx2, fy2 = smooth_bbox

        if (fx2 - fx1) > MIN_FACE_SIZE:
            face_roi = safe_crop(frame, (fx1, fy1, fx2, fy2))
            
            if face_roi is not None and face_roi.size > 0:
                try:
                    # Resize to model input
                    roi = cv2.resize(face_roi, (224, 224), interpolation=cv2.INTER_CUBIC)

                    # ----------------------------------------
                    # 🟢 NEW: PREPROCESSING FIX
                    # ----------------------------------------
                    # 1. Convert to Grayscale (removes color noise)
                    roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                    
                    # 2. Equalize Histogram (Boosts contrast - makes features POP)
                    roi_gray = cv2.equalizeHist(roi_gray)
                    
                    # 3. Convert BACK to RGB (MobileNet needs 3 channels)
                    roi_rgb = cv2.cvtColor(roi_gray, cv2.COLOR_GRAY2RGB)

                    # Show exactly what the AI sees
                    debug_view = cv2.resize(roi_rgb, (200, 200))
                    cv2.imshow("What AI Sees", debug_view)

                    # 4. Normalize (0.0 - 1.0)
                    roi_pp = roi_rgb.astype(np.float32) / 255.0
                    roi_pp = np.expand_dims(roi_pp, axis=0)
                    # ----------------------------------------

                    # Predict
                    preds = model.predict(roi_pp, verbose=0)
                    
                    # DEBUG: Print scores to see if it's stuck
                    # print(f"Scores: {np.round(preds[0], 2)}")

                    idx = int(np.argmax(preds[0]))
                    conf = float(preds[0][idx])
                    label = EMOTIONS[idx]

                    # Visualization
                    color = (0, 255, 0) if label == 'happy' else (0, 0, 255)
                    cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), color, 2)
                    
                    label_text = f"{label} {int(conf*100)}%"
                    cv2.rectangle(frame, (fx1, fy1-30), (fx1+200, fy1), color, -1)
                    cv2.putText(frame, label_text, (fx1 + 5, fy1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

                except Exception as ex:
                    print(f"Error: {ex}")

        # IRIS TRACKING
        if LEFT_IRIS_CENTER < len(pts) and RIGHT_IRIS_CENTER < len(pts):
            l_pt = pts[LEFT_IRIS_CENTER]
            r_pt = pts[RIGHT_IRIS_CENTER]
            l_smooth = smooth_point(l_iris_hist, l_pt)
            r_smooth = smooth_point(r_iris_hist, r_pt)
            
            cv2.circle(frame, l_smooth, 4, (0, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, r_smooth, 4, (0, 255, 255), -1, cv2.LINE_AA)
            cv2.line(frame, l_smooth, r_smooth, (255, 255, 0), 1, cv2.LINE_AA)

    if DISPLAY_FPS:
        now = time.time()
        fps = 0.9 * fps + 0.1 * (1 / (now - prev_time)) if (now-prev_time) > 0 else 0
        prev_time = now
        cv2.putText(frame, f"FPS: {int(fps)}", (10, h - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

    cv2.imshow("Hybrid System", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()