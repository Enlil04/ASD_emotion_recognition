import time
import json
import sqlite3
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

# Imports from your project structure
from .guardian import _connect_db_row, _guardian_can_access_patient
from services.usage_stats import _calculate_stats, _fetch_recent_raw_logs
from setup_db import DB_PATH

from services.usage_stats import get_current_vision_context 


router = APIRouter(tags=["dashboard"])

# --- CORE ENDPOINTS ---

@router.get("/api/emotions/latest")
async def latest_emotion(user_id: str, request: Request, requester_id: str = None):
    """Returns the most recent emotion for the dashboard UI."""
    con = _connect_db_row()
    try:
        cur = con.cursor()
        if requester_id and requester_id != user_id:
            if not _guardian_can_access_patient(cur, requester_id, user_id):
                raise HTTPException(status_code=403, detail="Not allowed")
        
        return _latest_emotion_display(user_id)
    finally:
        con.close()

@router.get("/api/emotions/weekly")
async def weekly_emotions(user_id: str, request: Request, requester_id: str = None):
    """Returns the 7-day trend data for the chart."""
    con = _connect_db_row()
    try:
        cur = con.cursor()
        if requester_id and requester_id != user_id:
            if not _guardian_can_access_patient(cur, requester_id, user_id):
                raise HTTPException(status_code=403, detail="Not allowed")
        
        return _fetch_emotion_daily(user_id)
    finally:
        con.close()

@router.get("/api/recommendation/today")
async def daily_recommendation(request: Request, user_id: str = "user_001"):
    """
    AI-generated advice based on 7-day trends and live camera data.
    """
    vision_packet = get_current_vision_context(request, user_id)

    today_str = date.today().isoformat()
    brain = request.app.state.brain
    
    if not brain:
        return {"recommendation": "AI Brain not initialized."}

    # 1. ANALYTICS: Fetch Weekly and Recent Data
    weekly_counts = _fetch_emotion_totals_last_7_days(user_id)
    week_stats = _calculate_stats(weekly_counts)

    recent_counts = {}
    recent_stats = {"total": 0}
    
    if week_stats["total"] == 0:
        recent_counts = _fetch_recent_raw_logs(user_id, hours=72)
        recent_stats = _calculate_stats(recent_counts)

    is_new = _is_new_user(user_id)

    # 2. DETERMINE DOMINANT MOOD & MODE
    if week_stats["total"] > 0:
        mode, dominant = "weekly", week_stats["dominant"]
        stats_text = f"Weekly summary: {week_stats['total']} logs. Dominant mood: {dominant} ({week_stats['percent']})."
    elif recent_stats["total"] > 0:
        mode, dominant = "recent", recent_stats["dominant"]
        stats_text = f"Recent 72h summary: {recent_stats['total']} logs. Dominant mood: {dominant}."
    elif is_new:
        mode, dominant = "new_user", "Neutral"
        stats_text = "New user: No history yet."
    else:
        mode, dominant = "none", "Neutral"
        stats_text = "No recent logs found."

    # 3. VISION: Get live data from App State
    system_state = getattr(request.app.state, "system_state", {})
    vision_packet = {
        "emotion": system_state.get("latest_emotion", "Neutral"),
        "face_detected": system_state.get("face_detected", False),
        "timestamp": time.time(),
    }

    # 4. CONSTRUCT PROMPT
    if mode in ("new_user", "none"):
        prompt = (
            f"Context: {stats_text}\n"
            "Task: Welcome the user and give one tiny actionable wellness tip (breathing/water). 1 sentence max."
        )
    else:
        prompt = (
            f"History: {stats_text}\n"
            f"Current live mood: {vision_packet['emotion']}.\n"
            f"Task: Give one specific recommendation for today based on the dominant mood: {dominant}. "
            "Angry/Sad = coping; Happy = habits; Neutral = gentle routine. 1-2 short sentences."
        )

    # 5. EXECUTE AI
    response_text = await run_in_threadpool(
        brain.decide_response,
        vision_data=vision_packet,
        prompt_text=prompt,
        extra_context={"mode": mode, "stats": week_stats}
    )

    return {
        "date": today_str,
        "mode": mode,
        "dominant": dominant,
        "recommendation": response_text
    }

# --- DATABASE HELPERS ---

def _is_new_user(user_id: str) -> bool:
    con = sqlite3.connect(DB_PATH)
    try:
        row = con.execute("SELECT 1 FROM emotion_logs WHERE user_id = ? LIMIT 1", (user_id,)).fetchone()
        return row is None
    finally:
        con.close()

def _fetch_emotion_totals_last_7_days(user_id: str) -> dict:
    days = _get_last_7_days()
    totals = {emo: 0 for emo in ["Happy", "Sad", "Neutral", "Anger", "Fear", "Surprise", "Disgust"]}
    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute(
            "SELECT emotion_counts FROM emotion_daily WHERE user_id = ? AND date_str >= ?",
            (user_id, days[0]),
        ).fetchall()
        for (counts_json,) in rows:
            if not counts_json: continue
            day_data = json.loads(counts_json)
            for emo, count in day_data.items():
                if emo in totals: totals[emo] += int(count)
        return totals
    finally:
        con.close()

def _fetch_emotion_daily(user_id: str) -> dict:
    days = _get_last_7_days()
    day_set = set(days)
    series_counts = {}
    totals = {d: 0 for d in days}

    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute(
            "SELECT date_str, emotion_counts FROM emotion_daily WHERE user_id = ? AND date_str >= ?",
            (user_id, days[0]),
        ).fetchall()
        for d, counts_json in rows:
            if d not in day_set: continue
            daily_data = json.loads(counts_json)
            for emo, cnt in daily_data.items():
                series_counts.setdefault(emo, {dd: 0 for dd in days})
                series_counts[emo][d] += int(cnt)
                totals[d] += int(cnt)
    finally:
        con.close()

    series = {emo: [(counts[d]/totals[d] if totals[d]>0 else 0.0) for d in days] 
              for emo, counts in series_counts.items()}
    
    # Ensure all emotions exist for chart consistency
    for emo in ["Happy", "Sad", "Anger", "Fear", "Surprise", "Disgust", "Neutral"]:
        series.setdefault(emo, [0.0] * 7)
    return {"days": days, "series": series}

def _get_last_7_days():
    return [(date.today() - timedelta(days=i)).strftime("%Y-%m-%d") for i in reversed(range(7))]

def _latest_emotion_display(user_id: str) -> dict:
    con = sqlite3.connect(DB_PATH)
    try:
        row = con.execute(
            "SELECT emotion, confidence, timestamp FROM emotion_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1",
            (user_id,)
        ).fetchone()
        if not row:
            return {"emotion": "No emotion detected", "confidence": 0.0, "timestamp": None}
        return {"emotion": row[0], "confidence": row[1], "timestamp": row[2]}
    finally:
        con.close()




# from fastapi import APIRouter, HTTPException
# import sqlite3
# import json
# import time
# from datetime import date, timedelta


# from fastapi.concurrency import run_in_threadpool
# from torch import mode
# from back.agent.routers.guardian import _connect_db_row, _guardian_can_access_patient
# from back.agent.services.analytics import _calculate_stats, _fetch_recent_raw_logs
# from back.agent.setup_db import DB_PATH


# router = APIRouter(prefix="/dashboard", tags=["dashboard"]) 


# @router.get("/api/emotions/latest")
# async def latest_emotion(user_id: str, requester_id: str = None):
#     """Latest detected emotion pulled from emotion_logs (for dashboard)."""
#     con = _connect_db_row()
#     try:
#         cur = con.cursor()

#         if requester_id and requester_id != user_id:
#             if not _guardian_can_access_patient(cur, requester_id, user_id):
#                 raise HTTPException(status_code=403, detail="Not allowed")

#         return _latest_emotion_display(user_id)
#     finally:
#         con.close()


# @router.get("/api/emotions/weekly")
# async def weekly_emotions(user_id: str, requester_id: str = None):
#     """Weekly mood series (last 7 days) used by dashboard.dart."""
#     con = _connect_db_row()
#     try:
#         cur = con.cursor()

#         if requester_id and requester_id != user_id:
#             if not _guardian_can_access_patient(cur, requester_id, user_id):
#                 raise HTTPException(status_code=403, detail="Not allowed")

#         return _fetch_emotion_daily(user_id)
#     finally:
#         con.close()


# def _is_new_user(user_id: str) -> bool:
#     con = sqlite3.connect(DB_PATH)  
#     try:
#         row = con.execute(
#             "SELECT 1 FROM emotion_logs WHERE user_id = ? LIMIT 1",
#             (user_id,),
#         ).fetchone()
#     finally:
#         con.close()
#     return row is None


# # @router.get("/api/recommendation/today")
# # async def daily_recommendation(user_id: str = "user_001"):
# #     """
# #     Generates a short daily recommendation based on:
# #     - last 7 days emotion aggregates (emotion_daily)
# #     - fallback to recent logs if no weekly data
# #     - onboarding if new user / no data
# #     """
# #     today_str = date.today().isoformat()
    
# #     # 1. Fetch Weekly Data (from emotion_daily summary)
# #     weekly_counts = _fetch_emotion_totals_last_7_days(user_id)
# #     week_stats = _calculate_stats(weekly_counts)

# #     # 2. Fetch Recent Data (Fallback to raw logs if weekly is empty)
# #     recent_counts = {}
# #     recent_stats = {"total": 0}
    
# #     if week_stats["total"] == 0:
# #         recent_counts = _fetch_recent_raw_logs(user_id, hours=72)
# #         recent_stats = _calculate_stats(recent_counts)

# #     is_new = _is_new_user(user_id)

# #     # 3. Determine Mode
# #     if week_stats["total"] > 0:
# #         mode = "weekly"
# #         dominant = week_stats["dominant"]
# #         stats_text = (
# #             f"Weekly emotion summary (last 7 days):\n"
# #             f"- Total logged: {week_stats['total']}\n"
# #             f"- Dominant: {dominant}\n"
# #             f"- Breakdown: {week_stats['percent']}"
# #         )
# #     elif recent_stats["total"] > 0:
# #         mode = "recent"
# #         dominant = recent_stats["dominant"]
# #         stats_text = (
# #             f"Recent emotion summary (last 72h raw logs):\n"
# #             f"- Total logged: {recent_stats['total']}\n"
# #             f"- Dominant: {dominant}\n"
# #             f"- Breakdown: {recent_stats['percent']}"
# #         )
# #     elif is_new:
# #         mode = "new_user"
# #         dominant = "Neutral"
# #         stats_text = "New user detected, no emotion history yet."
# #     else:
# #         mode = "none"
# #         dominant = "Neutral"
# #         stats_text = "No emotion data available."

# #     # 4. Prepare Vision/System State (Safe access)
# #     # Ensure system_state exists, otherwise default to empty
# #     current_state = globals().get("system_state", {})
# #     vision_packet = {
# #         "emotion": current_state.get("latest_emotion", "Neutral"),
# #         "face_detected": current_state.get("face_detected", False),
# #         "timestamp": time.time(),
# #     }

# #     # 5. Construct Prompt
# #     if mode in ("new_user", "none"):
# #         prompt = (
# #             f"Today is {today_str}.\n"
# #             f"{stats_text}\n\n"
# #             f"TASK:\n"
# #             f"Welcome the user briefly, explain that recommendations personalize after a few check-ins, "
# #             f"and give ONE small actionable suggestion they can do now (breathing, short walk, hydration).\n"
# #             f"Keep it 1-2 short sentences."
# #         )
# #     else:
# #         prompt = (
# #             f"Today is {today_str}.\n"
# #             f"{stats_text}\n\n"
# #             f"Current mood right now (latest detected): {vision_packet['emotion']}.\n\n"
# #             f"TASK:\n"
# #             f"Give ONE practical recommendation for today tailored to the chosen dominant emotion: {dominant}.\n"
# #             f"- If dominant is Angry or Sad: suggest calming / coping / support.\n"
# #             f"- If dominant is Happy: suggest maintaining habits + a small growth challenge.\n"
# #             f"- If dominant is Neutral: suggest exploration + gentle routine.\n"
# #             f"Keep it 1–2 short sentences. Be specific and actionable."
# #         )

# #     # 6. Execute AI Decision (Check if brain exists)
# #     brain_module = globals().get("brain")
# #     if not brain_module:
# #         return {
# #             "date": today_str, 
# #             "mode": "error", 
# #             "recommendation": "AI Brain module not loaded."
# #         }

# #     response_text = await run_in_threadpool(
# #         brain_module.decide_response,
# #         vision_data=vision_packet,
# #         prompt_text=prompt,
# #         extra_context={
# #             "weekly_stats": week_stats, 
# #             "mode": mode, 
# #             "dominant": dominant
# #         },
# #     )

# #     return {
# #         "date": today_str, 
# #         "mode": mode, 
# #         "dominant": dominant, 
# #         "recommendation": response_text
# #     }

# from fastapi import APIRouter, HTTPException, Request # Add Request

# @router.get("/api/recommendation/today")
# async def daily_recommendation(request: Request, user_id: str = "user_001"):

#     # ... logic (steps 1-3) stays the same ...

#     # 4. Grab Brain and Vision from App State (Not globals!)
#     brain = request.app.state.brain
#     system_state = getattr(request.app.state, "system_state", {}) 
    
#     vision_packet = {
#         "emotion": system_state.get("latest_emotion", "Neutral"),
#         "face_detected": system_state.get("face_detected", False),
#         "timestamp": time.time(),
#     }

#     if not brain:
#         return {"recommendation": "AI Brain not initialized in main app state."}

#     # 5. Execute using the shared brain
#     response_text = await run_in_threadpool(
#         brain.decide_response, # Use the brain from request.app.state
#         vision_data=vision_packet,
#         prompt_text=prompt,
#         extra_context={"weekly_stats": week_stats, "mode": mode}
#     )
    
#     return {
#         "date": today_str, 
#         "mode": mode, 
#         "recommendation": response_text
#     }


# def _get_last_7_days() -> list[str]:
#     today = date.today()
#     return [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in reversed(range(7))]


# def _fetch_emotion_totals_last_7_days(user_id: str) -> dict:
#     """
#     Aggregates total emotion counts for the last 7 days from the emotion_daily summary table.
#     """
#     days = _get_last_7_days()
#     start_date = days[0]
    
#     # Initialize totals with 0 to ensure all keys exist
#     totals = {
#         "Happy": 0, "Sad": 0, "Neutral": 0, "Anger": 0, 
#         "Fear": 0, "Surprise": 0, "Disgust": 0
#     }

#     con = sqlite3.connect(DB_PATH)
#     try:
#         # Fetch the JSON blobs for the last 7 days
#         rows = con.execute(
#             "SELECT emotion_counts FROM emotion_daily WHERE user_id = ? AND date_str >= ?",
#             (user_id, start_date),
#         ).fetchall()

#         for (counts_json,) in rows:
#             if not counts_json:
#                 continue
            
#             try:
#                 # Parse JSON: {"Happy": 15, "Neutral": 5, ...}
#                 day_data = json.loads(counts_json)
                
#                 # Sum the values into our running totals
#                 for emo, count in day_data.items():
#                     # Normalize key casing if necessary, or just sum directly
#                     # (assuming keys in JSON match the keys in 'totals')
#                     if emo in totals:
#                         totals[emo] += int(count)
#                     else:
#                         # Handle potential new/unexpected keys safely
#                         totals[emo] = totals.get(emo, 0) + int(count)
                        
#             except (ValueError, TypeError):
#                 continue
                
#     finally:
#         con.close()

#     return totals


# def _fetch_emotion_daily(user_id: str) -> dict:
#     days = _get_last_7_days()
#     day_set = set(days)
#     series_counts: dict[str, dict[str, int]] = {}
#     totals: dict[str, int] = {d: 0 for d in days}

#     con = sqlite3.connect(DB_PATH)
#     try:
#         # ✅ Corrected Query: Only fetch date and the JSON blob
#         rows = con.execute(
#             """
#             SELECT date_str, emotion_counts
#             FROM emotion_daily
#             WHERE user_id = ? AND date_str >= ?
#             """,
#             (user_id, days[0]),
#         ).fetchall()

#         for d, counts_json in rows:
#             if d not in day_set: continue
            
#             # ✅ Parse the JSON data
#             try:
#                 daily_data = json.loads(counts_json) # e.g. {"Happy": 10, "Sad": 2}
#             except (ValueError, TypeError):
#                 continue

#             # ✅ Iterate through the parsed dictionary
#             for emo, cnt in daily_data.items():
#                 series_counts.setdefault(emo, {dd: 0 for dd in days})
#                 series_counts[emo][d] += int(cnt)
#                 totals[d] += int(cnt)
                
#     finally:
#         con.close()

#     # --- (The rest of your aggregation logic remains exactly the same) ---
#     series: dict[str, list[float]] = {}
#     for emo, per_day in series_counts.items():
#         series[emo] = [
#             (per_day[d] / totals[d]) if totals[d] > 0 else 0.0
#             for d in days
#         ]
    
#     # Fill missing keys ensures the chart always has colors for every emotion
#     for emo in ["Happy", "Sad", "Anger", "Fear", "Surprise", "Disgust", "Neutral"]:
#         series.setdefault(emo, [0.0] * 7)

#     return {"days": days, "series": series}
#     days = _get_last_7_days()
#     day_set = set(days)
#     series_counts: dict[str, dict[str, int]] = {}
#     totals: dict[str, int] = {d: 0 for d in days}

#     con = sqlite3.connect(DB_PATH)
#     try:
#         rows = con.execute(
#             """
#             SELECT date_str, emotion, emotion_counts
#             FROM emotion_daily
#             WHERE user_id = ? AND date_str >= ?
#             """,
#             (user_id, days[0]),
#         ).fetchall()

#         for d, emo, cnt in rows:
#             if d not in day_set: continue
#             series_counts.setdefault(emo, {dd: 0 for dd in days})
#             series_counts[emo][d] += int(cnt or 0)
#             totals[d] += int(cnt or 0)
#     finally:
#         con.close()

#     series: dict[str, list[float]] = {}
#     for emo, per_day in series_counts.items():
#         series[emo] = [
#             (per_day[d] / totals[d]) if totals[d] > 0 else 0.0
#             for d in days
#         ]
    
#     # Fill missing keys
#     for emo in ["Happy", "Sad", "Anger", "Fear", "Surprise", "Disgust", "Neutral"]:
#         series.setdefault(emo, [0.0] * 7)

#     return {"days": days, "series": series}


# def _fetch_latest_emotion_from_db(user_id: str) -> dict:
#     """
#     Returns latest detected emotion from emotion_logs.
#     If none exists, returns {"emotion": None, "confidence": None, "timestamp": None}.
#     """
#     con = sqlite3.connect(DB_PATH)
#     try:
#         row = con.execute(
#             """
#             SELECT emotion, confidence, timestamp
#             FROM emotion_logs
#             WHERE user_id = ?
#             ORDER BY timestamp DESC
#             LIMIT 1
#             """,
#             (user_id,),
#         ).fetchone()

#         if not row:
#             return {"emotion": None, "confidence": None, "timestamp": None}

#         emo, conf, ts = row
#         return {"emotion": emo, "confidence": conf, "timestamp": ts}
#     finally:
#         con.close()


# def _latest_emotion_display(user_id: str) -> dict:
#     """
#     UI-friendly payload.
#     If no emotion exists => "No emotion detected"
#     """
#     latest = _fetch_latest_emotion_from_db(user_id)
#     if not latest["emotion"]:
#         return {"emotion": "No emotion detected", "confidence": 0.0, "timestamp": None}

#     return {
#         "emotion": str(latest["emotion"]),
#         "confidence": float(latest["confidence"] or 0.0),
#         "timestamp": latest["timestamp"],
#     }
# #-------------------------------------------------------------------------

