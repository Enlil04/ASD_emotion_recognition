import sqlite3
import random
import time
import json
import os
import sys
from datetime import datetime, timedelta

# ... (Path logic same as setup_db.py) ...
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(CURRENT_DIR) == "services":
    AGENT_DIR = os.path.dirname(CURRENT_DIR)
else:
    AGENT_DIR = CURRENT_DIR

DB_PATH = os.path.join(AGENT_DIR, "data", "memory.db")

PRIMARY_USER = "user_001"
EMOTIONS = ["Happy", "Sad", "Neutral", "Anger", "Fear", "Surprise", "Disgust"]

# Added photo placeholder
DUMMY_USERS = [
    ("user_002", "amina_alt", "Amina", "student", 20, "Loves coding.", "https://i.pravatar.cc/150?u=amina"),
    ("user_003", "liam_alt", "Liam", "mentor", 32, "Here to help.", "https://i.pravatar.cc/150?u=liam"),
    ("user_004", "sophia_alt", "Sophia", "parent", 45, "Supporting kids.", "https://i.pravatar.cc/150?u=sophia"),
    ("user_005", "omar_alt", "Omar", "member", 28, "Mindfulness.", "https://i.pravatar.cc/150?u=omar")
]

POST_IDEAS = [
    "Just finished a 10-minute meditation!",
    "Tips for social anxiety?",
    "Small win: Stuck to my routine.",
    "The weather is amazing today.",
    "Struggling a bit, but that is okay."
]

def seed_all():
    if not os.path.exists(DB_PATH):
        print(f"❌ ERROR: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now_ts = time.time()

    try:
        # --- 1. USERS ---
        print("👤 Seeding users...")
        cur.execute("DELETE FROM users")
        
        # Insert Primary User (Added 'photo')
        cur.execute("""
            INSERT OR REPLACE INTO users 
            (user_id, username, name, role, age, description, photo, streak, connections, created_at, updated_at)
            VALUES (?, 'nimi_user', 'Test User', 'member', 25, 'Main account.', 'https://i.pravatar.cc/150?u=test', 7, 150, ?, ?)
        """, (PRIMARY_USER, now_ts, now_ts))

        # Insert Dummy Users (Added 'photo')
        for uid, uname, name, role, age, desc, photo in DUMMY_USERS:
            cur.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, username, name, role, age, description, photo, streak, connections, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, uname, name, role, age, desc, photo, random.randint(1, 15), random.randint(5, 50), now_ts, now_ts))

        # ... (Rest of seed logic for profiles, posts, etc. remains the same) ...
        # (Copy the rest of the previous seed script here)

        # --- 4. COMMUNITY POSTS ---
        print("📝 Seeding community posts...")
        cur.execute("DELETE FROM community_posts")
        
        for _ in range(5):
            poster_id = random.choice([u[0] for u in DUMMY_USERS] + [PRIMARY_USER])
            cur.execute("""
                INSERT INTO community_posts (user_id, content, likes, comments, date_created, is_deleted)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (poster_id, random.choice(POST_IDEAS), random.randint(0, 20), 0, now_ts))

        conn.commit()
        print("✅ Database successfully seeded!")

    except sqlite3.OperationalError as e:
        print(f"❌ DATABASE ERROR: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    seed_all()