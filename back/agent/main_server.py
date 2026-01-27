"""
MAIN SERVER
------------------------------
Integrates:
1. FastAPI (for Flutter Chat & Events)
2. Vision Loop (Background Thread)
3. Agentic Brain (Shared Logic)

Run this to start the entire backend.
"""
import threading
import time
import os
import uvicorn
import cv2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# --- IMPORTS FROM YOUR PROJECT ---
from react_agent import AgenticBrain
from analytics.vision_models.emotion_detector import EmotionDetector, MODEL_FILE, LABELS
from analytics.vision_models.local_memory.emotion_summary import EmotionSummarizer
from analytics.vision_models.local_memory.session_memory import SessionMemoryManager

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "memory.db")
USER_ID = "user_001"

# --- GLOBAL STATE ---
# We use this to share data between the Camera Thread and the API
system_state = {
    "latest_emotion": "Neutral",
    "face_detected": False,
    "brain_busy": False,
    "camera_active": True
}

# Initialize FastAPI
app = FastAPI()

# Global Brain Instance (Loaded on startup)
brain = None
detector = None

# --- DATA MODELS (What Flutter sends us) ---
class ChatMessage(BaseModel):
    user_id: str
    message: str

class GameEvent(BaseModel):
    user_id: str
    event_type: str  # "level_failed", "game_started"
    activity: str = "memory_game"

# --- VISION THREAD ---
def vision_loop():
    """Runs the camera in the background continuously."""
    global detector
    print("📷 Vision Thread Started...")
    
    cap = cv2.VideoCapture(0)
    summarizer = EmotionSummarizer()
    session_mem = SessionMemoryManager()

    while system_state["camera_active"]:
        ret, frame = cap.read()
        if not ret:
            break

        # 1. Detect
        emotion, conf, box, probs = detector.predict(frame)
        
        # 2. Update Global State (So the Chat API knows what the user feels!)
        system_state["latest_emotion"] = emotion if box is not None else "No Face"
        system_state["face_detected"] = (box is not None)

        # 3. (Optional) Update Session Memory
        summarizer.update(emotion, conf, probs, LABELS, (box is not None))
        
        # 4. Display Window (Optional - good for testing)
        cv2.imshow("Server Vision", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break
            
    cap.release()
    cv2.destroyAllWindows()

# --- API ENDPOINTS (Flutter connects here) ---

@app.on_event("startup")
def startup_event():
    """Load heavy AI models once when server starts."""
    global brain, detector
    print("🧠 Loading Llama Brain & Vision Models...")
    
    # 1. Load Brain
    brain = AgenticBrain(db_path=DB_PATH, user_id=USER_ID)
    
    # 2. Load Vision
    detector = EmotionDetector(MODEL_FILE)
    
    # 3. Start Vision Loop in Background
    t = threading.Thread(target=vision_loop, daemon=True)
    t.start()
    print("✅ System Ready!")

@app.post("/chat")
async def chat_endpoint(chat: ChatMessage):
    """
    Flutter sends: {"user_id": "123", "message": "I'm feeling sad"}
    We return: {"response": "I'm sorry to hear that..."}
    """
    if system_state["brain_busy"]:
        return {"response": "Give me a moment, I'm thinking..."}
    
    system_state["brain_busy"] = True
    try:
        # 1. Create a Vision Packet (What is the user looking like RIGHT NOW?)
        vision_packet = {
            "emotion": system_state["latest_emotion"],
            "timestamp": time.time()
        }
        
        print(f"📩 Chat received: '{chat.message}' | Emotion: {vision_packet['emotion']}")

        # 2. Ask the Brain
        response = brain.decide_response(
            vision_data=vision_packet,
            prompt_text=chat.message, # The user's text
            extra_context={} 
        )
        
        return {"response": response}
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        system_state["brain_busy"] = False

@app.post("/event")
async def event_endpoint(event: GameEvent):
    """Handles Game Events (Win/Fail)"""
    print(f"🎮 Event: {event.event_type}")
    
    # Logic to trigger brain automatically if needed...
    return {"status": "processed"}

# --- RUNNER ---
if __name__ == "__main__":
    # This runs the Server on your local network
    # 0.0.0.0 allows your phone to connect
    uvicorn.run(app, host="0.0.0.0", port=8000)