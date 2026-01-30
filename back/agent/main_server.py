import os
import time
import sqlite3
from realtime import Optional
import uvicorn
from datetime import date, timedelta

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.orm import Session

# --- 1. IMPORT PATHS & DB FROM SETUP_DB (Source of Truth) ---
# We import DB_PATH and DATA_DIR so we don't accidentally create a second file
from setup_db import Base, engine, get_db, DB_PATH, DATA_DIR
import services.models as models

from react_agent import AgenticBrain
from analytics.vision_models.emotion_detector import EmotionDetector, MODEL_FILE
from services.video_service import VideoProcessor

# Ensure tables exist (using the imported engine)
Base.metadata.create_all(bind=engine)

# --- CONFIG ---
# We use the DATA_DIR imported from setup_db
TEMP_DIR = os.path.join(DATA_DIR, "temp_sessions")
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

# -----------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------


def _get_last_7_days() -> list[str]:
    today = date.today()
    return [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in reversed(range(7))]

def _fetch_emotion_totals_last_7_days(user_id: str, hours: int = 72) -> Optional[str]:
    since_ts = time.time() - (hours * 3600)

    days = _get_last_7_days()
    # Use the imported DB_PATH to ensure we read the correct file
    con = sqlite3.connect(DB_PATH) 
    try:
        rows = con.execute(
            """
            SELECT emotion, SUM(emotion_counts) as total_count
            FROM emotion_daily
            WHERE user_id = ? AND day >= ?
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

def _fetch_emotion_daily(user_id: str) -> dict:
    days = _get_last_7_days()
    day_set = set(days)
    series_counts: dict[str, dict[str, int]] = {}
    totals: dict[str, int] = {d: 0 for d in days}

    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute(
            """
            SELECT day, emotion, emotion_counts
            FROM emotion_daily
            WHERE user_id = ? AND day >= ?
            """,
            (user_id, days[0]),
        ).fetchall()

        for d, emo, cnt in rows:
            if d not in day_set: continue
            series_counts.setdefault(emo, {dd: 0 for dd in days})
            series_counts[emo][d] += int(cnt or 0)
            totals[d] += int(cnt or 0)
    finally:
        con.close()

    series: dict[str, list[float]] = {}
    for emo, per_day in series_counts.items():
        series[emo] = [
            (per_day[d] / totals[d]) if totals[d] > 0 else 0.0
            for d in days
        ]
    
    # Fill missing keys
    for emo in ["Happy", "Sad", "Anger", "Fear", "Surprise", "Disgust", "Neutral"]:
        series.setdefault(emo, [0.0] * 7)

    return {"days": days, "series": series}

# -----------------------------------------------------------------
# LIFECYCLE & ENDPOINTS
# -----------------------------------------------------------------

@app.on_event("startup")
def startup_event():
    global brain, detector, video_service
    print("🧠 Starting Nimi Engine...")
    
    try:
        # Use imported DB_PATH
        brain = AgenticBrain(db_path=DB_PATH, user_id="user_001")
        detector = EmotionDetector(MODEL_FILE)
        video_service = VideoProcessor(detector)
        print(f"✅ All systems go! Connected to DB at: {DB_PATH}")
    except Exception as e:
        print(f"❌ Startup Error: {e}")

@app.get("/api/emotions/weekly")
async def weekly_emotions(user_id: str = "user_001"):
    """Weekly mood series (last 7 days) used by dashboard.dart."""
    return _fetch_emotion_daily(user_id)

@app.post("/chat")
async def chat_endpoint(chat: ChatMessage):
    if system_state["brain_busy"]:
        return {"response": "Thinking..."}
    
    system_state["brain_busy"] = True
    try:
        vision_packet = {
            "emotion": system_state["latest_emotion"],
            "face_detected": system_state["face_detected"],
            "timestamp": time.time()
        }
        
        response_text = await run_in_threadpool(
            brain.decide_response, 
            vision_data=vision_packet,
            prompt_text=chat.message,
            extra_context={}
        )
        return {"response": response_text}
    except Exception as e:
        print(f"❌ Chat Error: {e}")
        return {"response": "Error processing chat."}
    finally:
        system_state["brain_busy"] = False

# -----------------------------------------------------------------
# THE VIDEO ENDPOINT (With Fixed DB Logic)
# -----------------------------------------------------------------
@app.post("/api/analyze_session")
async def analyze_session_endpoint(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    temp_path = os.path.join(TEMP_DIR, f"temp_{int(time.time())}_{file.filename}")
    
    try:
        with open(temp_path, "wb") as buffer:
            buffer.write(await file.read())

        if video_service is None: raise Exception("Video Service not initialized")

        # 1. Process Video
        result = await run_in_threadpool(video_service.process_session, temp_path)
        
        # 2. Extract & Filter Emotion
        emotion = result.get("dominant_emotion", "Neutral")
        confidence = float(result.get("confidence", 0.0))

        if confidence < 0.35: # Using the updated 0.35 threshold
            emotion = "Neutral"

        # 3. SAVE TO RAW LOGS
        try:
            new_session = models.MoodSession(
                user_id="user_001",
                emotion=emotion,
                confidence=confidence,
                timestamp=time.time()
            )
            db.add(new_session)
            db.commit() # Save the log first
            print(f"✅ Log Saved: {emotion}")

            # 4. UPDATE DAILY SUMMARY (This populates the charts)
            # We use an UPSERT strategy: Try to insert, if exists, update count.
            today_str = date.today().isoformat()
            
            # Check if entry exists
            daily_entry = db.query(models.DailySummary).filter(
                models.DailySummary.user_id == "user_001",
                models.DailySummary.day == today_str,
                models.DailySummary.emotion == emotion
            ).first()

            if daily_entry:
                daily_entry.emotion_counts += 1
            else:
                new_daily = models.DailySummary(
                    user_id="user_001",
                    day=today_str,
                    emotion=emotion,
                    emotion_counts=1
                )
                db.add(new_daily)
            
            db.commit() # Save the daily count
            print(f"✅ Daily Stats Updated for {today_str}")

        except Exception as db_e:
            db.rollback()
            print(f"❌ DB Save Failed: {db_e}")

        # 5. Update System State
        system_state["latest_emotion"] = emotion
        system_state["face_detected"] = result.get("face_detected", False)
        
        return result

    except Exception as e:
        print(f"❌ Processing Error: {e}")
        return {"dominant_emotion": "Neutral", "confidence": 0.0}
    finally:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass



def _is_new_user(user_id: str) -> bool:
    con = sqlite3.connect(DB_PATH)  
    try:
        row = con.execute(
            "SELECT 1 FROM emotion_logs WHERE user_id = ? LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        con.close()
    return row is None


@app.get("/api/recommendation/today")
async def daily_recommendation(user_id: str = "user_001"):
    """
    Generates a short daily recommendation based on:
    - last 7 days emotion aggregates (emotion_daily)
    - fallback to recent logs if no weekly data
    - onboarding if new user / no data
    """
    today_str = date.today().isoformat()
    if brain is None:
        return {"date": today_str, "recommendation": "Brain not ready."}

    week = _fetch_emotion_totals_last_7_days(user_id)
    weekly_total = week["total"]

    recent = _fetch_emotion_totals_last_7_days(user_id, hours=72)
    is_new = _is_new_user(user_id)

    if weekly_total > 0:
        mode = "weekly"
        dominant = week["dominant"]
        stats_text = f"""weekly emotion summary:
        - Total emotions logged: {week['total']}
        - Dominant emotion: {dominant}
        -percentages: {week['percent']}""".strip()

    elif recent is not None:
        mode = "recent"
        dominant = recent["dominant"]
        stats_text = f"""
        recent emotion summary (last 72h):
        - Total emotions logged: {recent['total']}
        - Dominant emotion: {dominant}
        - percentages: {recent['percent']}""".strip()

    elif is_new:
        mode = "new_user"
        dominant = "Neutral"
        stats_text = "new user detected, no emotion history yet.".strip()

    else:
        mode = "none"
        dominant = "Neutral"
        stats_text = "no emotion data available.".strip()

    vision_packet = {
        "emotion": system_state.get("latest_emotion", "Neutral"),
        "face_detected": system_state.get("face_detected", False),
        "timestamp": time.time(),
    }

    if mode in ("new_user", "none"):
        prompt = f"""
    Today is {today_str}.
    {stats_text}

    TASK:    
    Welcome the user briefly, explain that recommendations personalize after a few check-ins,
    and give ONE small actionable suggestion they can do now (breathing, short walk, hydration, journaling prompt).
    Keep it 1-2 short sentences.""".strip()
    else:
        prompt = f"""

    Today is {today_str}.
    {stats_text}

    current mood right now (latest detected) {vision_packet["emotion"]}.

    Task:
    Give ONE practical recommendation for today tailored to the chosen dominant emotion: {dominant}.
    - If dominant is Angry or Sad: use calming / coping / support suggestions.
    - If dominant is Happy: suggest maintaining habits + a small growth challenge.
    - If dominant is Neutral: suggest exploration + gentle routine.
    Keep it 1–2 short sentences. Be specific and actionable.""".strip()
        

    response_text = await run_in_threadpool(
        brain.decide_response,
        vision_data=vision_packet,
        prompt_text=prompt,
        extra_context={"weekly_7d": week, "mode": mode, "dominant": dominant},
    )
    return {"date": today_str, "mode": mode, "dominant": dominant, "recommendation": response_text}


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