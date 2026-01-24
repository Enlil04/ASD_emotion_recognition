import sqlite3
import json
import time
from typing import Dict, Any, Optional, List, Tuple


class LongTermMemoryStore:
    """
    Persistent per-user memory using SQLite.

    Stores:
      - users.preferences_json (small personalization settings)
      - emotion_daily counts per day per emotion (aggregated, not raw logs)
    """

    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.execute("PRAGMA journal_mode=WAL;")       # safer concurrent writes
        con.execute("PRAGMA synchronous=NORMAL;")
        return con

    def _init_db(self) -> None:
        con = self._connect()
        try:
            con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                preferences_json TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """)
            con.execute("""
            CREATE TABLE IF NOT EXISTS emotion_daily (
                user_id TEXT NOT NULL,
                day TEXT NOT NULL,            -- YYYY-MM-DD (local)
                emotion TEXT NOT NULL,
                count INTEGER NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY (user_id, day, emotion),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
            """)
            con.commit()
        finally:
            con.close()

    # ---------- Users / preferences ----------
    def ensure_user(self, user_id: str) -> None:
        now = time.time()
        con = self._connect()
        try:
            con.execute("""
            INSERT INTO users (user_id, preferences_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET updated_at=excluded.updated_at;
            """, (user_id, "{}", now, now))
            con.commit()
        finally:
            con.close()

    def get_preferences(self, user_id: str) -> Dict[str, Any]:
        self.ensure_user(user_id)
        con = self._connect()
        try:
            row = con.execute(
                "SELECT preferences_json FROM users WHERE user_id=?;",
                (user_id,)
            ).fetchone()
            return json.loads(row[0]) if row and row[0] else {}
        finally:
            con.close()

    def set_preferences(self, user_id: str, prefs: Dict[str, Any]) -> None:
        self.ensure_user(user_id)
        now = time.time()
        con = self._connect()
        try:
            con.execute("""
            UPDATE users
            SET preferences_json=?, updated_at=?
            WHERE user_id=?;
            """, (json.dumps(prefs, ensure_ascii=False), now, user_id))
            con.commit()
        finally:
            con.close()

    # ---------- Emotion aggregates ----------
    def add_emotion_counts(self, user_id: str, day: str, counts: Dict[str, int]) -> None:
        """
        counts example: {"Sad": 12, "Happy": 3}
        """
        self.ensure_user(user_id)
        now = time.time()
        con = self._connect()
        try:
            for emotion, inc in counts.items():
                if inc <= 0:
                    continue
                con.execute("""
                INSERT INTO emotion_daily (user_id, day, emotion, count, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, day, emotion)
                DO UPDATE SET
                    count = count + excluded.count,
                    updated_at = excluded.updated_at;
                """, (user_id, day, emotion, int(inc), now))
            con.commit()
        finally:
            con.close()

    def get_top_emotions_last_days(self, user_id: str, days: int = 7) -> List[Tuple[str, int]]:
        """
        Returns list of (emotion, total_count) for last N days.
        NOTE: This query expects you to pass day strings consistently as YYYY-MM-DD.
        """
        self.ensure_user(user_id)
        con = self._connect()
        try:
            rows = con.execute("""
            SELECT emotion, SUM(count) as total
            FROM emotion_daily
            WHERE user_id=?
              AND day >= date('now', ?)
            GROUP BY emotion
            ORDER BY total DESC;
            """, (user_id, f"-{int(days)} day")).fetchall()
            return [(r[0], int(r[1])) for r in rows]
        finally:
            con.close()

# helpers for flushing session emotions -> SQLite aggregates

def day_string_local() -> str:
    # Simple local day stamp; good enough for prototype
    # (If you need Baghdad timezone correctness across systems, use zoneinfo later.)
    return time.strftime("%Y-%m-%d", time.localtime())

def aggregate_recent_emotions(recent_emotions: list) -> Dict[str, int]:
    """
    Input: list of dicts like SessionMemoryManager.get_state()["recent_emotions"]
    Output: counts per dominant emotion (ignoring uncertain or None)
    """
    counts: Dict[str, int] = {}
    for e in recent_emotions:
        dom = e.get("dominant")
        uncertain = bool(e.get("uncertain"))
        if dom is None or uncertain:
            continue
        counts[dom] = counts.get(dom, 0) + 1
    return counts
