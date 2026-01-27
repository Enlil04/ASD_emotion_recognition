import os
import time
import uvicorn
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from fastapi.concurrency import run_in_threadpool # <--- IMPORT THIS
from react_agent import AgenticBrain
from analytics.vision_models.emotion_detector import EmotionDetector, MODEL_FILE
from services.video_service import VideoProcessor

# --- CONFIG & SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TEMP_DIR = os.path.join(DATA_DIR, "temp_sessions")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# --- GLOBAL STATE ---
system_state = {
    "latest_emotion": "Neutral",
    "face_detected": False,
    "brain_busy": False,
}

app = FastAPI()
brain = None
detector = None
video_service = None

class ChatMessage(BaseModel):
    user_id: str
    message: str

@app.on_event("startup")
def startup_event():
    global brain, detector, video_service
    print("🧠 Starting Nimi Engine...")
    
    # Initialize Core Components
    try:
        brain = AgenticBrain(db_path=os.path.join(DATA_DIR, "memory.db"), user_id="user_001")
        detector = EmotionDetector(MODEL_FILE)
        video_service = VideoProcessor(detector)
        print("✅ All systems go! Server ready.")
    except Exception as e:
        print(f"❌ Startup Error: {e}")

# --- ENDPOINTS ---

@app.post("/chat")
@app.post("/api/chat")
async def chat_endpoint(chat: ChatMessage):
    if system_state["brain_busy"]:
        return {"response": "I'm thinking... give me a second."}
    
    system_state["brain_busy"] = True
    try:
        vision_packet = {
            "emotion": system_state["latest_emotion"],
            "face_detected": system_state["face_detected"],
            "timestamp": time.time()
        }

        print(f"📩 Chat: '{chat.message}' | Mood: {vision_packet['emotion']}")

        # Use run_in_threadpool here too if brain.decide_response is slow
        response_text = await run_in_threadpool(
            brain.decide_response, 
            vision_data=vision_packet,
            prompt_text=chat.message,
            extra_context={}
        )
        
        return {"response": response_text}
        
    except Exception as e:
        print(f"❌ Chat Error: {e}")
        return {"response": "I lost my train of thought."}
    finally:
        system_state["brain_busy"] = False

@app.post("/api/analyze_session")
async def analyze_session_endpoint(file: UploadFile = File(...)):
    # 1. Save file (Async I/O is fine here)
    temp_path = os.path.join(TEMP_DIR, f"temp_{int(time.time())}_{file.filename}")
    
    try:
        with open(temp_path, "wb") as buffer:
            buffer.write(await file.read())

        if video_service is None:
            raise Exception("Video Service not initialized")

        print(f"⏳ Processing Video: {file.filename}...")

        # 2. RUN BLOCKING CODE IN THREADPOOL (Critical Fix)
        # This prevents the server from freezing while OpenCV runs
        result = await run_in_threadpool(video_service.process_session, temp_path)
        
        # 3. Update State
        system_state["latest_emotion"] = result.get("dominant_emotion", "Neutral")
        system_state["face_detected"] = True
        
        print(f"✅ Video Result: {system_state['latest_emotion']}")
        return result

    except Exception as e:
        print(f"❌ Video Error: {e}")
        return {"dominant_emotion": "Neutral", "confidence": 0.0}
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)