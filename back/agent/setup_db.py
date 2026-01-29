import sqlite3
import os
import time
from datetime import datetime, timedelta
import random

# ==============================
# DB PATH (same as server)
# ==============================
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "memory.db")

EMOTIONS = ["Happy", "Sad", "Neutral", "Anger", "Fear", "Surprise", "Disgust"]

def setup_tables(con):
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        preferences_json TEXT,
        created_at REAL,
        updated_at REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS emotion_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        emotion TEXT,
        confidence REAL,
        timestamp REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS emotion_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        day TEXT,
        emotion TEXT,
        count INTEGER,
        updated_at REAL,
        UNIQUE(user_id, day, emotion)
    )
    """)

    con.commit()


def seed_dummy_data(con):
    user_id = "user_001"
    now = time.time()

    cur = con.cursor()

    # Ensure user exists
    cur.execute("""
    INSERT INTO users (user_id, preferences_json, created_at, updated_at)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET updated_at=excluded.updated_at;
    """, (user_id, '{"name":"Test User"}', now, now))

    # Clear old data
    cur.execute("DELETE FROM emotion_daily WHERE user_id = ?", (user_id,))
    cur.execute("DELETE FROM emotion_logs WHERE user_id = ?", (user_id,))

    today = datetime.now().date()

    for i in range(7):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")

        # 🔴 SAD-HEAVY DISTRIBUTION
        daily_counts = {
            "Sad": random.randint(15, 30),
            "Neutral": random.randint(5, 12),
            "Happy": random.randint(2, 8),
            "Anger": random.randint(1, 6),
            "Fear": random.randint(1, 6),
            "Surprise": random.randint(0, 3),
            "Disgust": random.randint(0, 3),
        }

        for emo in EMOTIONS:
            cnt = int(daily_counts.get(emo, 0))

            cur.execute("""
            INSERT INTO emotion_daily (user_id, day, emotion, count, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, day, emotion)
            DO UPDATE SET count=excluded.count, updated_at=excluded.updated_at;
            """, (user_id, d, emo, cnt, now))

            for _ in range(cnt):
                cur.execute("""
                INSERT INTO emotion_logs (user_id, emotion, confidence, timestamp)
                VALUES (?, ?, ?, ?)
                """, (
                    user_id,
                    emo,
                    round(random.uniform(0.6, 0.99), 2),
                    now
                ))

    con.commit()
    print("✅ Seeded last 7 days with SAD-dominant emotion data.")


def main():
    print(f"Initializing database at: {os.path.abspath(DB_PATH)}")
    con = sqlite3.connect(DB_PATH)

    setup_tables(con)
    seed_dummy_data(con)

    con.close()
    print("✅ Database ready.")


if __name__ == "__main__":
    main()
