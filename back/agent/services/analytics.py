import time
from datetime import date, timedelta

from agent.setup_db import DB_PATH
from sqlalchemy import create_engine
import sqlite3

# --- Helper 1: Calculate Statistics from a counts dictionary ---
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

# --- Helper 2: Fetch Recent RAW Logs (Fallback) ---
def _fetch_recent_raw_logs(user_id: str, hours: int = 72) -> dict:
    """
    Queries the RAW 'emotion_logs' table for very recent activity 
    (useful if the user is new and has no 'daily summaries' yet).
    """
    cutoff = time.time() - (hours * 3600)
    counts = {}
    
    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute(
            "SELECT emotion FROM emotion_logs WHERE user_id = ? AND timestamp >= ?", 
            (user_id, cutoff)
        ).fetchall()
        
        for (emo,) in rows:
            counts[emo] = counts.get(emo, 0) + 1
            
    finally:
        con.close()
        
    return counts

# --- Helper 3: Check if User is New ---
def _is_new_user(user_id: str) -> bool:
    con = sqlite3.connect(DB_PATH)
    try:
        # Check if user was created in the last 24 hours
        row = con.execute(
            "SELECT created_at FROM users WHERE user_id = ?", 
            (user_id,)
        ).fetchone()
        
        if row and row[0]:
            is_recent = (time.time() - row[0]) < 86400  # 24 hours
            return is_recent
        return False
    finally:
        con.close()