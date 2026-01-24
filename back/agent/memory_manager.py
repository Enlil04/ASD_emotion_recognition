import sys
import os

# Get the path to the current directory (agent)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory (back)
parent_dir = os.path.dirname(current_dir)
# Add 'back' to the system path so Python can find 'analytics'
sys.path.append(parent_dir)

# --- YOUR EXISTING IMPORTS BELOW ---
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
<<<<<<< HEAD
from analytics.vision_models.long_term_memory import LongTermMemoryStore  # your existing SQLite store

=======

# This will now work
from analytics.vision_models.local_memory.long_term_memory import LongTermMemoryStore
>>>>>>> 8e35c0d7cb8c6ab1075f672816fbdd08d72a0a33

class MemoryManager:
    """
    SQLite-backed memory manager (NO JSON files).
    - Profile/preferences stored in LongTermMemoryStore.users.preferences_json
    - Emotion aggregates stored in LongTermMemoryStore.emotion_daily
    - Interaction log stored in an 'interactions' table in the same DB.
    """

    def __init__(self, db_path: str = "memory.db", user_id: str = "user_001"):
        self.user_id = user_id
        self.store = LongTermMemoryStore(db_path)
        self.db_path = db_path
        self._init_interactions_table()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA synchronous=NORMAL;")
        return con

    def _init_interactions_table(self) -> None:
        con = self._connect()
        try:
            con.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                ts REAL NOT NULL,
                readable_time TEXT NOT NULL,
                event_type TEXT NOT NULL,       -- 'conversation' or 'observation'
                user_input TEXT,
                agent_response TEXT,
                detected_emotion TEXT,
                confidence REAL
            );
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_interactions_user_ts ON interactions(user_id, ts);")
            con.commit()
        finally:
            con.close()

    # --------------------------
    # Profile / preferences
    # --------------------------
    def load_profile(self) -> Dict[str, Any]:
        """
        Returns: {"name": "...", "preferences": {...}, "triggers": [...]}
        Stored under users.preferences_json (single JSON).
        """
        prefs = self.store.get_preferences(self.user_id)  # dict
        # default structure
        name = prefs.get("name", "User")
        triggers = prefs.get("triggers", [])
        preferences = prefs.get("preferences", {})
        if not isinstance(triggers, list):
            triggers = []
        if not isinstance(preferences, dict):
            preferences = {}
        return {"name": name, "preferences": preferences, "triggers": triggers}

    def save_profile(self, name: Optional[str] = None, triggers: Optional[List[str]] = None,
                     preferences: Optional[Dict[str, Any]] = None) -> None:
        prefs = self.store.get_preferences(self.user_id)
        if not isinstance(prefs, dict):
            prefs = {}

        if name is not None:
            prefs["name"] = name
        if triggers is not None:
            prefs["triggers"] = triggers
        if preferences is not None:
            prefs["preferences"] = preferences

        self.store.set_preferences(self.user_id, prefs)

    # --------------------------
    # Interaction logs
    # --------------------------
    def save_interaction(self, user_text: str, agent_response: str, detected_emotion: str) -> None:
        con = self._connect()
        try:
            now = time.time()
            con.execute("""
                INSERT INTO interactions
                (user_id, ts, readable_time, event_type, user_input, agent_response, detected_emotion, confidence)
                VALUES (?, ?, ?, 'conversation', ?, ?, ?, NULL);
            """, (
                self.user_id,
                now,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                user_text,
                agent_response,
                detected_emotion
            ))
            con.commit()
        finally:
            con.close()

    def log_emotional_event(self, emotion: str, confidence: float = 1.0) -> None:
        con = self._connect()
        try:
            now = time.time()
            con.execute("""
                INSERT INTO interactions
                (user_id, ts, readable_time, event_type, user_input, agent_response, detected_emotion, confidence)
                VALUES (?, ?, ?, 'observation', NULL, NULL, ?, ?);
            """, (
                self.user_id,
                now,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                emotion,
                float(confidence)
            ))
            con.commit()
        finally:
            con.close()

    def get_recent_summary(self, limit: int = 3) -> str:
        con = self._connect()
        try:
            rows = con.execute("""
                SELECT user_input, agent_response, detected_emotion
                FROM interactions
                WHERE user_id=? AND event_type='conversation'
                ORDER BY ts DESC
                LIMIT ?;
            """, (self.user_id, int(limit))).fetchall()

            if not rows:
                return "No recent interactions."

            # reverse to chronological
            rows = list(reversed(rows))
            lines = []
            for u_text, a_text, emo in rows:
                u_text = u_text or ""
                a_text = a_text or ""
                emo = emo or "unknown"
                lines.append(f"- User ({emo}): {u_text} | Agent: {a_text}")
            return "\n".join(lines)
        finally:
            con.close()

    def find_patterns(self, days: int = 7) -> str:
        """
        Uses emotion_daily aggregates (not raw frame logs).
        """
        top = self.store.get_top_emotions_last_days(self.user_id, days=int(days))
        if not top:
            return "No strong patterns detected yet."
        # Example output
        formatted = ", ".join([f"{emo}:{cnt}" for emo, cnt in top[:4]])
        return f"Top emotions last {days} days: {formatted}"
