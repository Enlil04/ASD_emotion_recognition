#after dashboard

import os
import time
import sqlite3
from datetime import date, timedelta
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
    
#-----------------------------------------------------------------
    
def _fetch_emotion_totals_last_7_days(user_id: str) -> dict:
    """
    Returns totals across last 7 days:
      {
        "totals": {"Happy": 12, "Sad": 3, ...},
        "total": 30,
        "dominant": "Happy",
        "percent": {"Happy": 0.4, ...}
      }
    """
    days = _get_last_7_days()
    con = sqlite3.connect(_get_db_path())
    try:
        rows = con.execute(
            """
            SELECT emotion, SUM(count) as total_count
            FROM emotion_daily
            WHERE user_id = ?
              AND day >= ?
            GROUP BY emotion
            """,
            (user_id, days[0]),
        ).fetchall()
    finally:
        con.close()

    emotions = ["Happy", "Sad", "Anger", "Fear", "Surprise", "Disgust", "Neutral"]
    totals = {e: 0 for e in emotions}

    for emo, cnt in rows:
        if emo in totals:
            totals[emo] = int(cnt or 0)

    total = sum(totals.values())
    dominant = max(totals, key=lambda k: totals[k]) if total > 0 else "Neutral"
    percent = {e: (totals[e] / total) if total > 0 else 0.0 for e in emotions}

    return {"totals": totals, "total": total, "dominant": dominant, "percent": percent}
#-------------------------------------------------------------------------------------------

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

def _get_db_path() -> str:
    # Keep a single source of truth for DB location
    return os.path.join(DATA_DIR, "memory.db")


def _get_last_7_days() -> list[str]:
    today = date.today()
    return [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in reversed(range(7))]


def _fetch_emotion_daily(user_id: str) -> dict:
    """
    Returns:
      {
        "days": ["YYYY-MM-DD", ... 7],
        "series": { "Happy": [0..1], ... }  # per-day proportions
      }
    """
    days = _get_last_7_days()
    day_set = set(days)

    # Initialize raw counts
    series_counts: dict[str, dict[str, int]] = {}
    totals: dict[str, int] = {d: 0 for d in days}

    con = sqlite3.connect(_get_db_path())
    try:
        rows = con.execute(
            """
            SELECT day, emotion, count
            FROM emotion_daily
            WHERE user_id = ?
              AND day >= ?
            """,
            (user_id, days[0]),
        ).fetchall()

        for d, emo, cnt in rows:
            if d not in day_set:
                continue
            series_counts.setdefault(emo, {dd: 0 for dd in days})
            series_counts[emo][d] += int(cnt or 0)
            totals[d] += int(cnt or 0)
    finally:
        con.close()

    # Convert to proportions per day for chart (0..1)
    series: dict[str, list[float]] = {}
    for emo, per_day in series_counts.items():
        series[emo] = [
            (per_day[d] / totals[d]) if totals[d] > 0 else 0.0
            for d in days
        ]

    # Ensure stable keys even if DB has no rows yet
    for emo in ["Happy", "Sad", "Anger", "Fear", "Surprise", "Disgust", "Neutral"]:
        series.setdefault(emo, [0.0] * 7)

    return {"days": days, "series": series}


@app.get("/api/emotions/weekly")
async def weekly_emotions(user_id: str = "user_001"):
    """Weekly mood series (last 7 days) used by dashboard.dart."""
    return _fetch_emotion_daily(user_id)


@app.get("/api/recommendation/today")
async def daily_recommendation(user_id: str = "user_001"):
    """
    Generates a short daily recommendation based on:
    - last 7 days emotion aggregates
    - the latest detected emotion (if available)
    """
    today_str = date.today().isoformat()

    if brain is None:
        return {"date": today_str, "recommendation": "No brain available yet."}

    week = _fetch_emotion_totals_last_7_days(user_id)

    vision_packet = {
        "emotion": system_state.get("latest_emotion", "Neutral"),
        "face_detected": system_state.get("face_detected", False),
        "timestamp": time.time(),
    }


    prompt = f"""
Today is {today_str}.

Weekly emotion summary (last 7 days):
- Totals: {week["totals"]}
- Dominant emotion over the week: {week["dominant"]}
- Percentages: {week["percent"]}

Current mood right now (latest detected): {vision_packet["emotion"]}

Task:
Give ONE practical recommendation for today tailored to the dominant weekly emotion.
- If dominant is Angry or Sad: use calming / coping / support suggestions.
- If dominant is Happy: suggest maintaining habits + small growth challenge.
- If dominant is Neutral: suggest exploration + gentle routine.
Keep it 1–2 short sentences. Be specific and actionable.
""".strip()

    response_text = await run_in_threadpool(
        brain.decide_response,
        vision_data=vision_packet,
        prompt_text=prompt,
        extra_context={"weekly_7d": week},  # optional; prompt_text is the key part
    )

    return {"date": today_str, "recommendation": response_text}


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

















#before dashboard endpoints
# import os
# import time
# import uvicorn
# from fastapi import FastAPI, UploadFile, File
# from pydantic import BaseModel
# from fastapi.concurrency import run_in_threadpool # <--- IMPORT THIS
# from react_agent import AgenticBrain
# from analytics.vision_models.emotion_detector import EmotionDetector, MODEL_FILE
# from services.video_service import VideoProcessor

# # --- CONFIG & SETUP ---
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DATA_DIR = os.path.join(BASE_DIR, "data")
# TEMP_DIR = os.path.join(DATA_DIR, "temp_sessions")

# os.makedirs(DATA_DIR, exist_ok=True)
# os.makedirs(TEMP_DIR, exist_ok=True)

# # --- GLOBAL STATE ---
# system_state = {
#     "latest_emotion": "Neutral",
#     "face_detected": False,
#     "brain_busy": False,
# }

# app = FastAPI()
# brain = None
# detector = None
# video_service = None

# class ChatMessage(BaseModel):
#     user_id: str
#     message: str

# @app.on_event("startup")
# def startup_event():
#     global brain, detector, video_service
#     print("🧠 Starting Nimi Engine...")
    
#     # Initialize Core Components
#     try:
#         brain = AgenticBrain(db_path=os.path.join(DATA_DIR, "memory.db"), user_id="user_001")
#         detector = EmotionDetector(MODEL_FILE)
#         video_service = VideoProcessor(detector)
#         print("✅ All systems go! Server ready.")
#     except Exception as e:
#         print(f"❌ Startup Error: {e}")

# # --- ENDPOINTS ---

# @app.post("/chat")
# @app.post("/api/chat")
# async def chat_endpoint(chat: ChatMessage):
#     if system_state["brain_busy"]:
#         return {"response": "I'm thinking... give me a second."}
    
#     system_state["brain_busy"] = True
#     try:
#         vision_packet = {
#             "emotion": system_state["latest_emotion"],
#             "face_detected": system_state["face_detected"],
#             "timestamp": time.time()
#         }

#         print(f"📩 Chat: '{chat.message}' | Mood: {vision_packet['emotion']}")

#         # Use run_in_threadpool here too if brain.decide_response is slow
#         response_text = await run_in_threadpool(
#             brain.decide_response, 
#             vision_data=vision_packet,
#             prompt_text=chat.message,
#             extra_context={}
#         )
        
#         return {"response": response_text}
        
#     except Exception as e:
#         print(f"❌ Chat Error: {e}")
#         return {"response": "I lost my train of thought."}
#     finally:
#         system_state["brain_busy"] = False

# @app.post("/api/analyze_session")
# async def analyze_session_endpoint(file: UploadFile = File(...)):
#     # 1. Save file (Async I/O is fine here)
#     temp_path = os.path.join(TEMP_DIR, f"temp_{int(time.time())}_{file.filename}")
    
#     try:
#         with open(temp_path, "wb") as buffer:
#             buffer.write(await file.read())

#         if video_service is None:
#             raise Exception("Video Service not initialized")

#         print(f"⏳ Processing Video: {file.filename}...")

#         # 2. RUN BLOCKING CODE IN THREADPOOL (Critical Fix)
#         # This prevents the server from freezing while OpenCV runs
#         result = await run_in_threadpool(video_service.process_session, temp_path)
        
#         # 3. Update State
#         system_state["latest_emotion"] = result.get("dominant_emotion", "Neutral")
#         system_state["face_detected"] = True
        
#         print(f"✅ Video Result: {system_state['latest_emotion']}")
#         return result

#     except Exception as e:
#         print(f"❌ Video Error: {e}")
#         return {"dominant_emotion": "Neutral", "confidence": 0.0}
#     finally:
#         # Cleanup
#         if os.path.exists(temp_path):
#             try:
#                 os.remove(temp_path)
#             except:
#                 pass

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)