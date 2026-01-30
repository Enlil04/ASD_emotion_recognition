
import os
import sys
import sqlite3
import random
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ==============================
# 1. SMART PATH CALCULATION (From V1)
# ==============================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Navigate to the 'agent' root directory
if os.path.basename(CURRENT_DIR) == "services":
    AGENT_DIR = os.path.dirname(CURRENT_DIR)
else:
    AGENT_DIR = CURRENT_DIR

DATA_DIR = os.path.join(AGENT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "memory.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# ==============================
# 2. SQLALCHEMY SETUP (From V1)
# ==============================
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==============================
# 3. SCHEMA DEFINITIONS & SEEDING (Hybrid)
# ==============================
def setup_tables():
    """Uses raw sqlite3 for complex constraints and seeding."""
    print(f"🔄 Initializing database at: {DB_PATH}")
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # 1. USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        name TEXT,
        role TEXT,
        age INTEGER,
        photo_url TEXT,
        description TEXT,
        connections INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0,
        preferences_json TEXT,
        created_at REAL,
        updated_at REAL
    )""")

    # 2. COMMUNITY POSTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS community_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        content TEXT NOT NULL,
        likes INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        date_created REAL
    )""")

    # 3. COMMENTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        content TEXT NOT NULL,
        date_created REAL
    )""")

    # 4. POST LIKES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS post_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        date_created REAL,
        UNIQUE(post_id, user_id)
    )""")

    # 5. EMOTION LOGS (Raw data)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS emotion_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        emotion TEXT,
        confidence REAL,
        timestamp REAL
    )""")

    # 6. EMOTION DAILY (Summary) - CRITICAL: 'emotion_counts'
    cur.execute("""
    CREATE TABLE IF NOT EXISTS emotion_daily (
        user_id TEXT,
        date_str TEXT,
        emotion_counts TEXT,
        total_frames INTEGER,
        PRIMARY KEY (user_id, date_str)
    )""")

    # 7. INTERACTIONS (Standardized for AI Chat)
# --- TABLE 1: INTERACTIONS (Chat History) ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        timestamp REAL NOT NULL,        -- Matches 'timestamp' usage
        readable_time TEXT NOT NULL,
<<<<<<< HEAD
        event_type TEXT NOT NULL,       -- 'conversation' or 'observation'
        user_input TEXT
=======
        event_type TEXT NOT NULL,       
        user_input TEXT,
        agent_response TEXT,
        detected_emotion TEXT,
        confidence REAL
>>>>>>> 41b5596b9655c069b2c6e86136950a535324208a
    )""")

    # 8. SIGNIFICANT EVENTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS significant_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        timestamp REAL,                  -- Matches 'timestamp' usage
        event_type TEXT,
        description TEXT,
        context_json TEXT
    )""")

    # 9. USER PROFILES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id TEXT PRIMARY KEY,
        preferences_json TEXT
    )""")

    

    con.commit()
    con.close()

# ==============================
# 4. EXECUTION
# ==============================
if __name__ == "__main__":
    # Ensure services are in path for model importing
    if os.path.basename(CURRENT_DIR) != "services":
        sys.path.append(os.path.join(AGENT_DIR, "services"))
    
    # Run the setup
    setup_tables()
    print("🚀 Database is synchronized and ready.")