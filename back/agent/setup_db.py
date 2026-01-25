"""
DATABASE SETUP UTILITY
----------------------
A standalone script to initialize the SQLite database. It creates the required 
tables (users, emotion_daily, interactions) if they do not exist. 
Run this once before starting the main application.
"""

import os
import sqlite3
import time

# This ensures the database goes into back/agent/data/memory.db
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "memory.db")

def init_db():
    # Automatically create the 'data' folder if it is missing
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"📁 Created directory: {DATA_DIR}")

    print(f"Initializing database at: {DB_PATH}")
    # ... rest of your init_db code ...
    
    con = sqlite3.connect(DB_PATH)
    try:
        # 1. Enable WAL mode for better concurrency (writing while reading)
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA synchronous=NORMAL;")
        
        # 2. Table: Users (Preferences & Profile)
        print("Creating table: users...")
        con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            preferences_json TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        """)

        # 3. Table: Emotion Daily (Long-term aggregates)
        print("Creating table: emotion_daily...")
        con.execute("""
        CREATE TABLE IF NOT EXISTS emotion_daily (
            user_id TEXT NOT NULL,
            day TEXT NOT NULL,            -- YYYY-MM-DD
            emotion TEXT NOT NULL,
            count INTEGER NOT NULL,
            updated_at REAL NOT NULL,
            PRIMARY KEY (user_id, day, emotion),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        """)

        # 4. Table: Interactions (Chat logs & Event history)
        print("Creating table: interactions...")
        con.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            ts REAL NOT NULL,
            readable_time TEXT NOT NULL,
            event_type TEXT NOT NULL,      -- 'conversation' or 'observation'
            user_input TEXT,
            agent_response TEXT,
            detected_emotion TEXT,
            confidence REAL
        );
        """)
        
        # 5. Create Indices for speed
        con.execute("CREATE INDEX IF NOT EXISTS idx_interactions_user_ts ON interactions(user_id, ts);")

        con.commit()
        print("✅ Database initialized successfully.")

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
    finally:
        con.close()

def seed_dummy_data():
    """Optional: Adds some fake data to test the 'Long-term trends' logic immediately."""
    user_id = "user_001"
    print(f"Seeding dummy data for {user_id}...")
    
    con = sqlite3.connect(DB_PATH)
    now = time.time()
    day = time.strftime("%Y-%m-%d", time.localtime())
    
    try:
        # Ensure user exists
        con.execute("""
        INSERT INTO users (user_id, preferences_json, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO NOTHING;
        """, (user_id, '{"name": "Alex", "triggers": ["loud noises"]}', now, now))
        
        # Add some fake emotion counts for "today"
        # Happy: 15, Sad: 5, Neutral: 20
        emotions = [("Happy", 15), ("Sad", 5), ("Neutral", 20)]
        for emo, count in emotions:
            con.execute("""
            INSERT INTO emotion_daily (user_id, day, emotion, count, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, day, emotion) DO UPDATE SET count = count + excluded.count;
            """, (user_id, day, emo, count, now))
            
        con.commit()
        print("✅ Dummy data seeded.")
    finally:
        con.close()

if __name__ == "__main__":
    init_db()
    
    # Uncomment the line below if you want to start with some fake history
    # seed_dummy_data()