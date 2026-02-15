import time
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import Request

# ✅ IMPORT MODELS ONLY (No Routers, No Main)
import services.models as models

# --- 1. Pure Math Helper (No DB) ---
def _calculate_stats(counts: dict):
    """
    Takes raw counts {'Happy': 10, 'Sad': 2} and returns the 
    structure expected by the endpoint (total, dominant, percents).
    """
    total = sum(counts.values())
    if total == 0:
        return {"total": 0, "dominant": "Neutral", "percent": {}}

    # Sort emotions by count (descending)
    sorted_emos = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    dominant_emotion = sorted_emos[0][0]
    
    # Calculate percentages
    percents = {k: f"{(v / total * 100):.1f}%" for k, v in counts.items() if v > 0}
    
    return {
        "total": total,
        "dominant": dominant_emotion,
        "percent": percents,
        "counts": counts
    }

# --- 2. DB Helper: Fetch Recent Logs ---
def _fetch_recent_raw_logs(user_id: str, db: Session, limit: int = 5):
    """
    Fetches the last N raw logs for the live feed.
    """
    logs = db.query(models.MoodSession)\
        .filter(models.MoodSession.user_id == user_id)\
        .order_by(models.MoodSession.timestamp.desc())\
        .limit(limit)\
        .all()
        
    return [
        {
            "emotion": log.emotion,
            "confidence": round(log.confidence, 1),
            "timestamp": datetime.fromtimestamp(log.timestamp).strftime("%H:%M:%S")
        }
        for log in logs
    ]

# --- 3. DB Helper: Check if New User ---
def _is_new_user(user_id: str, db: Session) -> bool:
    """
    Checks if the user has less than 2 days of Daily Summaries.
    """
    count = db.query(models.DailySummary).filter(
        models.DailySummary.user_id == user_id
    ).count()
    return count < 2

# --- 4. DB Helper: Get Latest Single Emotion ---
def _fetch_latest_emotion_from_db(user_id: str, db: Session):
    """
    Replaces the import from routers.dashboard.
    Fetches the single most recent emotion log.
    """
    latest = db.query(models.MoodSession)\
        .filter(models.MoodSession.user_id == user_id)\
        .order_by(models.MoodSession.timestamp.desc())\
        .first()

    if latest:
        return {"emotion": latest.emotion, "confidence": latest.confidence}
    return {"emotion": "Neutral", "confidence": 0.0}

# --- 5. Context Helper for AI (RAM + DB) ---
def get_current_vision_context(request: Request, user_id: str, db: Session):
    """
    Combines live 'RAM' state with 'DB' history for the AI.
    """
    # A. Try to get live detection from RAM (FastAPI State)
    # We use getattr safely so it doesn't crash if state is missing
    system_state = getattr(request.app.state, "system_state", {})
    live_emotion = system_state.get("latest_emotion")
    
    # B. If RAM is empty (camera off), fallback to DB
    if not live_emotion or live_emotion == "Neutral":
        db_data = _fetch_latest_emotion_from_db(user_id, db)
        live_emotion = db_data.get("emotion", "Neutral")

    return {
        "emotion": live_emotion,
        "face_detected": system_state.get("face_detected", False),
        "timestamp": time.time()
    }