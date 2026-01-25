"""
LONG-TERM MEMORY (PERSISTENCE)
------------------------------
This module manages the SQLite database for persistent storage. It handles 
user preferences and aggregates daily emotion counts (long-term trends), 
ensuring data survives after the program restarts.
"""
import sqlite3
import time
import json
from datetime import datetime, timedelta

class LongTermMemoryStore:
    def __init__(self, db_path):
        # 1. Store the path
        self.db_path = db_path  
        
        # 2. Connect to the database
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """
        Creates the necessary tables if they don't exist.
        """
        # Table 1: Aggregated Daily Stats
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_emotion_stats (
                user_id TEXT,
                date_str TEXT,
                emotion_counts TEXT,
                total_frames INTEGER,
                PRIMARY KEY (user_id, date_str)
            )
        """)
        
        # Table 2: Significant Events
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS significant_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                timestamp REAL,
                event_type TEXT,
                description TEXT,
                context_json TEXT
            )
        """)

        # Table 3: User Profiles (Preferred Name, Triggers, etc.)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                preferences_json TEXT
            )
        """)
        
        self.conn.commit()

    # --- MISSING METHOD ADDED HERE ---
    def get_preferences(self, user_id):
        """
        Retrieves the user's profile/preferences.
        Returns a dict (e.g., {'name': 'Nimi', 'triggers': ['loud noises']})
        """
        self.cursor.execute("SELECT preferences_json FROM user_profiles WHERE user_id=?", (user_id,))
        row = self.cursor.fetchone()
        
        if row:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                return {}
        else:
            # If no profile exists yet, return a safe default
            return {"name": "User", "triggers": []}

    def update_preferences(self, user_id, new_prefs: dict):
        """
        Saves/Updates user preferences.
        """
        # Get existing to merge
        current = self.get_preferences(user_id)
        current.update(new_prefs)
        
        self.cursor.execute("""
            INSERT OR REPLACE INTO user_profiles (user_id, preferences_json)
            VALUES (?, ?)
        """, (user_id, json.dumps(current)))
        self.conn.commit()

    def add_emotion_counts(self, user_id, date_str, new_counts):
        """
        Updates the daily aggregate for a specific user.
        """
        self.cursor.execute("SELECT emotion_counts, total_frames FROM daily_emotion_stats WHERE user_id=? AND date_str=?", (user_id, date_str))
        row = self.cursor.fetchone()

        if row:
            existing_counts = json.loads(row[0])
            total_frames = row[1]
            for emo, count in new_counts.items():
                existing_counts[emo] = existing_counts.get(emo, 0) + count
                total_frames += count
        else:
            existing_counts = new_counts
            total_frames = sum(new_counts.values())

        self.cursor.execute("""
            INSERT OR REPLACE INTO daily_emotion_stats (user_id, date_str, emotion_counts, total_frames)
            VALUES (?, ?, ?, ?)
        """, (user_id, date_str, json.dumps(existing_counts), total_frames))
        self.conn.commit()

    def get_top_emotions_last_days(self, user_id, days=7):
        """
        Returns the most frequent emotions over the last X days.
        """
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        self.cursor.execute("""
            SELECT emotion_counts FROM daily_emotion_stats 
            WHERE user_id=? AND date_str >= ?
        """, (user_id, start_date))
        
        rows = self.cursor.fetchall()
        if not rows:
            return "No recent data."

        grand_total = {}
        for row in rows:
            day_counts = json.loads(row[0])
            for emo, count in day_counts.items():
                grand_total[emo] = grand_total.get(emo, 0) + count

        sorted_emotions = sorted(grand_total.items(), key=lambda x: x[1], reverse=True)
        return ", ".join([f"{k} ({v})" for k, v in sorted_emotions[:3]])

    def log_significant_event(self, user_id, event_type, description, context=None):
        timestamp = time.time()
        context_json = json.dumps(context) if context else "{}"
        
        self.cursor.execute("""
            INSERT INTO significant_events (user_id, timestamp, event_type, description, context_json)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, timestamp, event_type, description, context_json))
        self.conn.commit()

    def close(self):
        self.conn.close()

# Helper functions
def day_string_local():
    return datetime.now().strftime("%Y-%m-%d")

def aggregate_recent_emotions(recent_emotions_list):
    counts = {}
    for emo in recent_emotions_list:
        counts[emo] = counts.get(emo, 0) + 1
    return counts