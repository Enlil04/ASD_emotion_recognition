import os
import time
import sqlite3
from realtime import Optional
import uvicorn
from datetime import date, timedelta

from fastapi import FastAPI, Query, UploadFile, File, Depends, HTTPException
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


from services.analytics import _calculate_stats, _fetch_recent_raw_logs, _is_new_user

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
# -------------------------------------- i added these codes for fetching the latest emotions detected
def _fetch_latest_emotion_from_db(user_id: str) -> dict:
    """
    Returns latest detected emotion from emotion_logs.
    If none exists, returns {"emotion": None, "confidence": None, "timestamp": None}.
    """
    con = sqlite3.connect(DB_PATH)
    try:
        row = con.execute(
            """
            SELECT emotion, confidence, timestamp
            FROM emotion_logs
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

        if not row:
            return {"emotion": None, "confidence": None, "timestamp": None}

        emo, conf, ts = row
        return {"emotion": emo, "confidence": conf, "timestamp": ts}
    finally:
        con.close()


def _latest_emotion_display(user_id: str) -> dict:
    """
    UI-friendly payload.
    If no emotion exists => "No emotion detected"
    """
    latest = _fetch_latest_emotion_from_db(user_id)
    if not latest["emotion"]:
        return {"emotion": "No emotion detected", "confidence": 0.0, "timestamp": None}

    return {
        "emotion": str(latest["emotion"]),
        "confidence": float(latest["confidence"] or 0.0),
        "timestamp": latest["timestamp"],
    }
#-------------------------------------------------------------------------

def _get_last_7_days() -> list[str]:
    today = date.today()
    return [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in reversed(range(7))]

import json
import sqlite3

def _fetch_emotion_totals_last_7_days(user_id: str) -> dict:
    """
    Aggregates total emotion counts for the last 7 days from the emotion_daily summary table.
    """
    days = _get_last_7_days()
    start_date = days[0]
    
    # Initialize totals with 0 to ensure all keys exist
    totals = {
        "Happy": 0, "Sad": 0, "Neutral": 0, "Anger": 0, 
        "Fear": 0, "Surprise": 0, "Disgust": 0
    }

    con = sqlite3.connect(DB_PATH)
    try:
        # Fetch the JSON blobs for the last 7 days
        rows = con.execute(
            "SELECT emotion_counts FROM emotion_daily WHERE user_id = ? AND date_str >= ?",
            (user_id, start_date),
        ).fetchall()

        for (counts_json,) in rows:
            if not counts_json:
                continue
            
            try:
                # Parse JSON: {"Happy": 15, "Neutral": 5, ...}
                day_data = json.loads(counts_json)
                
                # Sum the values into our running totals
                for emo, count in day_data.items():
                    # Normalize key casing if necessary, or just sum directly
                    # (assuming keys in JSON match the keys in 'totals')
                    if emo in totals:
                        totals[emo] += int(count)
                    else:
                        # Handle potential new/unexpected keys safely
                        totals[emo] = totals.get(emo, 0) + int(count)
                        
            except (ValueError, TypeError):
                continue
                
    finally:
        con.close()

    return totals
import json
import sqlite3

def _fetch_emotion_daily(user_id: str) -> dict:
    days = _get_last_7_days()
    day_set = set(days)
    series_counts: dict[str, dict[str, int]] = {}
    totals: dict[str, int] = {d: 0 for d in days}

    con = sqlite3.connect(DB_PATH)
    try:
        # ✅ Corrected Query: Only fetch date and the JSON blob
        rows = con.execute(
            """
            SELECT date_str, emotion_counts
            FROM emotion_daily
            WHERE user_id = ? AND date_str >= ?
            """,
            (user_id, days[0]),
        ).fetchall()

        for d, counts_json in rows:
            if d not in day_set: continue
            
            # ✅ Parse the JSON data
            try:
                daily_data = json.loads(counts_json) # e.g. {"Happy": 10, "Sad": 2}
            except (ValueError, TypeError):
                continue

            # ✅ Iterate through the parsed dictionary
            for emo, cnt in daily_data.items():
                series_counts.setdefault(emo, {dd: 0 for dd in days})
                series_counts[emo][d] += int(cnt)
                totals[d] += int(cnt)
                
    finally:
        con.close()

    # --- (The rest of your aggregation logic remains exactly the same) ---
    series: dict[str, list[float]] = {}
    for emo, per_day in series_counts.items():
        series[emo] = [
            (per_day[d] / totals[d]) if totals[d] > 0 else 0.0
            for d in days
        ]
    
    # Fill missing keys ensures the chart always has colors for every emotion
    for emo in ["Happy", "Sad", "Anger", "Fear", "Surprise", "Disgust", "Neutral"]:
        series.setdefault(emo, [0.0] * 7)

    return {"days": days, "series": series}
    days = _get_last_7_days()
    day_set = set(days)
    series_counts: dict[str, dict[str, int]] = {}
    totals: dict[str, int] = {d: 0 for d in days}

    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute(
            """
            SELECT date_str, emotion, emotion_counts
            FROM emotion_daily
            WHERE user_id = ? AND date_str >= ?
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
        
#-----------------also added this new endpoint for the latest detected
@app.get("/api/emotions/latest")
async def latest_emotion(user_id: str = "user_001"):
    """Latest detected emotion pulled from emotion_logs (for dashboard)."""
    return _latest_emotion_display(user_id)


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


from fastapi.concurrency import run_in_threadpool

@app.get("/api/recommendation/today")
async def daily_recommendation(user_id: str = "user_001"):
    """
    Generates a short daily recommendation based on:
    - last 7 days emotion aggregates (emotion_daily)
    - fallback to recent logs if no weekly data
    - onboarding if new user / no data
    """
    today_str = date.today().isoformat()
    
    # 1. Fetch Weekly Data (from emotion_daily summary)
    weekly_counts = _fetch_emotion_totals_last_7_days(user_id)
    week_stats = _calculate_stats(weekly_counts)

    # 2. Fetch Recent Data (Fallback to raw logs if weekly is empty)
    recent_counts = {}
    recent_stats = {"total": 0}
    
    if week_stats["total"] == 0:
        recent_counts = _fetch_recent_raw_logs(user_id, hours=72)
        recent_stats = _calculate_stats(recent_counts)

    is_new = _is_new_user(user_id)

    # 3. Determine Mode
    if week_stats["total"] > 0:
        mode = "weekly"
        dominant = week_stats["dominant"]
        stats_text = (
            f"Weekly emotion summary (last 7 days):\n"
            f"- Total logged: {week_stats['total']}\n"
            f"- Dominant: {dominant}\n"
            f"- Breakdown: {week_stats['percent']}"
        )
    elif recent_stats["total"] > 0:
        mode = "recent"
        dominant = recent_stats["dominant"]
        stats_text = (
            f"Recent emotion summary (last 72h raw logs):\n"
            f"- Total logged: {recent_stats['total']}\n"
            f"- Dominant: {dominant}\n"
            f"- Breakdown: {recent_stats['percent']}"
        )
    elif is_new:
        mode = "new_user"
        dominant = "Neutral"
        stats_text = "New user detected, no emotion history yet."
    else:
        mode = "none"
        dominant = "Neutral"
        stats_text = "No emotion data available."

    # 4. Prepare Vision/System State (Safe access)
    # Ensure system_state exists, otherwise default to empty
    current_state = globals().get("system_state", {})
    vision_packet = {
        "emotion": current_state.get("latest_emotion", "Neutral"),
        "face_detected": current_state.get("face_detected", False),
        "timestamp": time.time(),
    }

    # 5. Construct Prompt
    if mode in ("new_user", "none"):
        prompt = (
            f"Today is {today_str}.\n"
            f"{stats_text}\n\n"
            f"TASK:\n"
            f"Welcome the user briefly, explain that recommendations personalize after a few check-ins, "
            f"and give ONE small actionable suggestion they can do now (breathing, short walk, hydration).\n"
            f"Keep it 1-2 short sentences."
        )
    else:
        prompt = (
            f"Today is {today_str}.\n"
            f"{stats_text}\n\n"
            f"Current mood right now (latest detected): {vision_packet['emotion']}.\n\n"
            f"TASK:\n"
            f"Give ONE practical recommendation for today tailored to the chosen dominant emotion: {dominant}.\n"
            f"- If dominant is Angry or Sad: suggest calming / coping / support.\n"
            f"- If dominant is Happy: suggest maintaining habits + a small growth challenge.\n"
            f"- If dominant is Neutral: suggest exploration + gentle routine.\n"
            f"Keep it 1–2 short sentences. Be specific and actionable."
        )

    # 6. Execute AI Decision (Check if brain exists)
    brain_module = globals().get("brain")
    if not brain_module:
        return {
            "date": today_str, 
            "mode": "error", 
            "recommendation": "AI Brain module not loaded."
        }

    response_text = await run_in_threadpool(
        brain_module.decide_response,
        vision_data=vision_packet,
        prompt_text=prompt,
        extra_context={
            "weekly_stats": week_stats, 
            "mode": mode, 
            "dominant": dominant
        },
    )

    return {
        "date": today_str, 
        "mode": mode, 
        "dominant": dominant, 
        "recommendation": response_text
    }

# ==============================
# COMMUNITY + USERS API (new)
# ==============================

# --- Pydantic Schemas ---
class CreatePostRequest(BaseModel):
    user_id: str
    content: str

class CreateCommentRequest(BaseModel):
    user_id: str
    content: str

class LikeRequest(BaseModel):
    user_id: str

class ReportRequest(BaseModel):
    reporter_user_id: str
    reason: str


def _dict_user_public(row: sqlite3.Row) -> dict:
    """Return only the public fields your community UI needs."""
    # sqlite3.Row supports dict-style access; .get is not guaranteed, so use safe indexing
    def safe(key, default=None):
        try:
            return row[key]
        except Exception:
            return default

    return {
        "user_id": safe("user_id"),
        "name": safe("name"),
        "username": safe("username"),
        "role": safe("role"),
        "age": safe("age"),
        "description": safe("description"),
        "photo": safe("photo"),
        "streak": safe("streak", 0),
        "connections": safe("connections", 0),
    }


def _ensure_community_schema():
    """
    Light migrations so server doesn't crash if DB was created before you added new tables/cols.
    Safe to run on startup.
    """
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()

        # community_reports (for /report endpoint)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS community_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            reporter_user_id TEXT NOT NULL,
            reason TEXT,
            date_created REAL
        )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_post_id ON community_reports(post_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_date_created ON community_reports(date_created)")

        # soft delete support on community_posts
        cols = {c[1] for c in cur.execute("PRAGMA table_info(community_posts)").fetchall()}
        if "is_deleted" not in cols:
            cur.execute("ALTER TABLE community_posts ADD COLUMN is_deleted INTEGER DEFAULT 0")

        con.commit()
    except Exception as e:
        print(f"❌ Community schema ensure failed: {e}")
    finally:
        con.close()


# Ensure schema on startup
@app.on_event("startup")
def _startup_community_schema():
    _ensure_community_schema()


def _connect_db_row() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


# --------------------------------------------------------------------
# (1) GET /api/community/posts  - Feed (paged)
# --------------------------------------------------------------------
@app.get("/api/community/posts")
async def list_community_posts(
    user_id: Optional[str] = None,  # optional: compute liked_by_me
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Returns the latest community posts with author info (and liked_by_me if user_id is provided)."""
    con = _connect_db_row()
    try:
        cur = con.cursor()

        rows = cur.execute(
            """
            SELECT
                p.id as post_id,
                p.content,
                p.likes,
                p.comments,
                p.date_created,
                COALESCE(p.is_deleted, 0) as is_deleted,
                u.user_id,
                u.name,
                u.username,
                u.role,
                u.age,
                u.description,
                u.photo,
                u.streak,
                u.connections
            FROM community_posts p
            LEFT JOIN users u ON u.user_id = p.user_id
            WHERE COALESCE(p.is_deleted, 0) = 0
            ORDER BY p.date_created DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

        posts = []
        for r in rows:
            liked_by_me = False
            if user_id:
                liked_by_me = cur.execute(
                    "SELECT 1 FROM post_likes WHERE post_id = ? AND user_id = ?",
                    (r["post_id"], user_id),
                ).fetchone() is not None

            posts.append({
                "id": r["post_id"],
                "content": r["content"],
                "likes": int(r["likes"] or 0),
                "comments": int(r["comments"] or 0),
                "date_created": r["date_created"],
                "liked_by_me": liked_by_me,
                "author": _dict_user_public(r),
            })

        return {"items": posts, "limit": limit, "offset": offset}
    finally:
        con.close()


# --------------------------------------------------------------------
# (2) POST /api/community/posts  - Create a post
# --------------------------------------------------------------------
@app.post("/api/community/posts")
async def create_community_post(req: CreatePostRequest):
    """Creates a new post for a user."""
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="content is required")

    con = _connect_db_row()
    now = time.time()
    try:
        cur = con.cursor()

        # verify user exists
        u = cur.execute("SELECT user_id FROM users WHERE user_id = ?", (req.user_id,)).fetchone()
        if u is None:
            raise HTTPException(status_code=404, detail="user not found")

        cur.execute(
            """
            INSERT INTO community_posts (user_id, content, likes, comments, date_created, is_deleted)
            VALUES (?, ?, 0, 0, ?, 0)
            """,
            (req.user_id, req.content, now),
        )
        post_id = cur.lastrowid
        con.commit()

        # return the created post (with author info)
        row = cur.execute(
            """
            SELECT p.id as post_id, p.content, p.likes, p.comments, p.date_created,
                   u.user_id, u.name, u.username, u.role, u.age, u.description, u.photo, u.streak, u.connections
            FROM community_posts p
            LEFT JOIN users u ON u.user_id = p.user_id
            WHERE p.id = ?
            """,
            (post_id,),
        ).fetchone()

        return {
            "id": row["post_id"],
            "content": row["content"],
            "likes": int(row["likes"] or 0),
            "comments": int(row["comments"] or 0),
            "date_created": row["date_created"],
            "liked_by_me": False,
            "author": _dict_user_public(row),
        }
    finally:
        con.close()


# --------------------------------------------------------------------
# (3) GET /api/community/posts/{post_id}  - Post detail
# --------------------------------------------------------------------
@app.get("/api/community/posts/{post_id}")
async def get_community_post(post_id: int, user_id: Optional[str] = None):
    """Returns a single post (with author info). Optionally includes liked_by_me when user_id is provided."""
    con = _connect_db_row()
    try:
        cur = con.cursor()
        r = cur.execute(
            """
            SELECT
                p.id as post_id, p.content, p.likes, p.comments, p.date_created,
                COALESCE(p.is_deleted, 0) as is_deleted,
                u.user_id, u.name, u.username, u.role, u.age, u.description, u.photo, u.streak, u.connections
            FROM community_posts p
            LEFT JOIN users u ON u.user_id = p.user_id
            WHERE p.id = ?
            """,
            (post_id,),
        ).fetchone()

        if r is None or int(r["is_deleted"] or 0) == 1:
            raise HTTPException(status_code=404, detail="post not found")

        liked_by_me = False
        if user_id:
            liked_by_me = cur.execute(
                "SELECT 1 FROM post_likes WHERE post_id = ? AND user_id = ?",
                (post_id, user_id),
            ).fetchone() is not None

        return {
            "id": r["post_id"],
            "content": r["content"],
            "likes": int(r["likes"] or 0),
            "comments": int(r["comments"] or 0),
            "date_created": r["date_created"],
            "liked_by_me": liked_by_me,
            "author": _dict_user_public(r),
        }
    finally:
        con.close()


# --------------------------------------------------------------------
# (4) GET /api/community/posts/{post_id}/comments  - List comments
# --------------------------------------------------------------------
@app.get("/api/community/posts/{post_id}/comments")
async def list_post_comments(
    post_id: int,
    limit: int = Query(30, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Returns comments for a post (paged) with author info."""
    con = _connect_db_row()
    try:
        cur = con.cursor()

        # ensure post exists (and not deleted)
        p = cur.execute(
            "SELECT id, COALESCE(is_deleted,0) as is_deleted FROM community_posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if p is None or int(p["is_deleted"] or 0) == 1:
            raise HTTPException(status_code=404, detail="post not found")

        rows = cur.execute(
            """
            SELECT
                c.id as comment_id,
                c.post_id,
                c.content,
                c.date_created,
                u.user_id, u.name, u.username, u.role, u.age, u.description, u.photo, u.streak, u.connections
            FROM comments c
            LEFT JOIN users u ON u.user_id = c.user_id
            WHERE c.post_id = ?
            ORDER BY c.date_created ASC
            LIMIT ? OFFSET ?
            """,
            (post_id, limit, offset),
        ).fetchall()

        items = []
        for r in rows:
            items.append({
                "id": r["comment_id"],
                "post_id": r["post_id"],
                "content": r["content"],
                "date_created": r["date_created"],
                "author": _dict_user_public(r),
            })

        return {"items": items, "limit": limit, "offset": offset}
    finally:
        con.close()


# --------------------------------------------------------------------
# (5) POST /api/community/posts/{post_id}/comments  - Add comment
# --------------------------------------------------------------------
@app.post("/api/community/posts/{post_id}/comments")
async def add_post_comment(post_id: int, req: CreateCommentRequest):
    """Adds a comment to a post and updates the cached comments count on the post."""
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="content is required")

    con = _connect_db_row()
    now = time.time()
    try:
        cur = con.cursor()

        # ensure post exists and not deleted
        p = cur.execute(
            "SELECT id, COALESCE(is_deleted,0) as is_deleted FROM community_posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if p is None or int(p["is_deleted"] or 0) == 1:
            raise HTTPException(status_code=404, detail="post not found")

        # ensure user exists
        u = cur.execute("SELECT user_id FROM users WHERE user_id = ?", (req.user_id,)).fetchone()
        if u is None:
            raise HTTPException(status_code=404, detail="user not found")

        cur.execute(
            """
            INSERT INTO comments (post_id, user_id, content, date_created)
            VALUES (?, ?, ?, ?)
            """,
            (post_id, req.user_id, req.content, now),
        )

        # update cached counter
        comment_count = cur.execute(
            "SELECT COUNT(*) FROM comments WHERE post_id = ?",
            (post_id,),
        ).fetchone()[0]
        cur.execute("UPDATE community_posts SET comments = ? WHERE id = ?", (comment_count, post_id))

        con.commit()
        return {"ok": True, "post_id": post_id, "comments": int(comment_count)}
    finally:
        con.close()


# --------------------------------------------------------------------
# (6) POST /api/community/posts/{post_id}/like  - Like post (idempotent)
# --------------------------------------------------------------------
@app.post("/api/community/posts/{post_id}/like")
async def like_post(post_id: int, req: LikeRequest):
    """Likes a post (idempotent). Uses post_likes UNIQUE(post_id,user_id) to prevent duplicates."""
    con = _connect_db_row()
    now = time.time()
    try:
        cur = con.cursor()

        # ensure post exists and not deleted
        p = cur.execute(
            "SELECT id, COALESCE(is_deleted,0) as is_deleted FROM community_posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if p is None or int(p["is_deleted"] or 0) == 1:
            raise HTTPException(status_code=404, detail="post not found")

        # ensure user exists
        u = cur.execute("SELECT user_id FROM users WHERE user_id = ?", (req.user_id,)).fetchone()
        if u is None:
            raise HTTPException(status_code=404, detail="user not found")

        cur.execute(
            "INSERT OR IGNORE INTO post_likes (post_id, user_id, date_created) VALUES (?, ?, ?)",
            (post_id, req.user_id, now),
        )

        like_count = cur.execute(
            "SELECT COUNT(*) FROM post_likes WHERE post_id = ?",
            (post_id,),
        ).fetchone()[0]
        cur.execute("UPDATE community_posts SET likes = ? WHERE id = ?", (like_count, post_id))

        con.commit()
        return {"ok": True, "post_id": post_id, "likes": int(like_count)}
    finally:
        con.close()


# --------------------------------------------------------------------
# (7) POST /api/community/posts/{post_id}/unlike  - Unlike post
# --------------------------------------------------------------------
@app.post("/api/community/posts/{post_id}/unlike")
async def unlike_post(post_id: int, req: LikeRequest):
    """Removes a like from a post and updates the cached likes count."""
    con = _connect_db_row()
    try:
        cur = con.cursor()

        # ensure post exists and not deleted
        p = cur.execute(
            "SELECT id, COALESCE(is_deleted,0) as is_deleted FROM community_posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if p is None or int(p["is_deleted"] or 0) == 1:
            raise HTTPException(status_code=404, detail="post not found")

        cur.execute("DELETE FROM post_likes WHERE post_id = ? AND user_id = ?", (post_id, req.user_id))

        like_count = cur.execute(
            "SELECT COUNT(*) FROM post_likes WHERE post_id = ?",
            (post_id,),
        ).fetchone()[0]
        cur.execute("UPDATE community_posts SET likes = ? WHERE id = ?", (like_count, post_id))

        con.commit()
        return {"ok": True, "post_id": post_id, "likes": int(like_count)}
    finally:
        con.close()


# --------------------------------------------------------------------
# (8) GET /api/users/{user_id}  - Public user profile
# --------------------------------------------------------------------
@app.get("/api/users/{user_id}")
async def get_user_profile(user_id: str):
    """Returns public profile fields for a user (used by community author/profile UI)."""
    con = _connect_db_row()
    try:
        cur = con.cursor()
        r = cur.execute(
            """
            SELECT user_id, name, username, role, age, description, photo, streak, connections
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        if r is None:
            raise HTTPException(status_code=404, detail="user not found")
        return _dict_user_public(r)
    finally:
        con.close()


# --------------------------------------------------------------------
# (9) POST /api/community/posts/{post_id}/report  - Report a post
# --------------------------------------------------------------------
@app.post("/api/community/posts/{post_id}/report")
async def report_post(post_id: int, req: ReportRequest):
    """Creates a report record for moderation review."""
    con = _connect_db_row()
    now = time.time()
    try:
        cur = con.cursor()

        # ensure post exists and not deleted
        p = cur.execute(
            "SELECT id, COALESCE(is_deleted,0) as is_deleted FROM community_posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if p is None or int(p["is_deleted"] or 0) == 1:
            raise HTTPException(status_code=404, detail="post not found")

        # ensure reporter exists
        u = cur.execute("SELECT user_id FROM users WHERE user_id = ?", (req.reporter_user_id,)).fetchone()
        if u is None:
            raise HTTPException(status_code=404, detail="reporter user not found")

        cur.execute(
            """
            INSERT INTO community_reports (post_id, reporter_user_id, reason, date_created)
            VALUES (?, ?, ?, ?)
            """,
            (post_id, req.reporter_user_id, req.reason, now),
        )
        con.commit()
        return {"ok": True, "post_id": post_id}
    finally:
        con.close()


# --------------------------------------------------------------------
# (10) DELETE /api/community/posts/{post_id}  - Delete (soft delete)
# --------------------------------------------------------------------
@app.delete("/api/community/posts/{post_id}")
async def delete_post(post_id: int, requester_user_id: str):
    """
    Soft-deletes a post.
    Allowed if requester is:
    - the author of the post, OR
    - a user with role 'admin' or 'moderator'
    """
    con = _connect_db_row()
    try:
        cur = con.cursor()

        post = cur.execute(
            "SELECT id, user_id, COALESCE(is_deleted,0) as is_deleted FROM community_posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if post is None or int(post["is_deleted"] or 0) == 1:
            raise HTTPException(status_code=404, detail="post not found")

        requester = cur.execute(
            "SELECT user_id, role FROM users WHERE user_id = ?",
            (requester_user_id,),
        ).fetchone()
        if requester is None:
            raise HTTPException(status_code=404, detail="requester user not found")

        is_author = requester_user_id == post["user_id"]
        role = (requester["role"] or "").lower()
        is_admin = role in ("admin", "moderator")

        if not (is_author or is_admin):
            raise HTTPException(status_code=403, detail="not allowed")

        cur.execute("UPDATE community_posts SET is_deleted = 1 WHERE id = ?", (post_id,))
        con.commit()
        return {"ok": True, "post_id": post_id}
    finally:
        con.close()




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