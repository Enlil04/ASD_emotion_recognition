# import os
# import sys
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.ext.declarative import declarative_base

# # ==============================
# # 1. SMART PATH CALCULATION
# # ==============================
# # Get the folder where THIS file lives
# CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# # Check if we are inside the 'services' subfolder
# if os.path.basename(CURRENT_DIR) == "services":
#     # If yes, go up one level to find 'agent'
#     AGENT_DIR = os.path.dirname(CURRENT_DIR)
# else:
#     # If no, we are already in 'agent' (or the root we want)
#     AGENT_DIR = CURRENT_DIR

# # Now we define data inside 'agent/data'
# DATA_DIR = os.path.join(AGENT_DIR, "data")
# os.makedirs(DATA_DIR, exist_ok=True)

# DB_PATH = os.path.join(DATA_DIR, "memory.db")
# SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# print(f"📂 DATABASE SET TO: {DB_PATH}")

# # ==============================
# # 2. SQLALCHEMY SETUP
# # ==============================
# engine = create_engine(
#     SQLALCHEMY_DATABASE_URL, 
#     connect_args={"check_same_thread": False}
# )
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # ==============================
# # 3. INITIALIZATION
# # ==============================
# def main():
#     # If setup_db is in agent/, we need to make sure python can find 'services' if models are there
#     if os.path.basename(CURRENT_DIR) != "services":
#          sys.path.append(os.path.join(AGENT_DIR, "services"))

#     try:
#         # Import models to register tables
#         # Try importing as if we are in root, then as if we are in package
#         try:
#             import models 
#         except ImportError:
#             from services import models

#         print("🔄 Updating database tables...")
#         Base.metadata.create_all(bind=engine)
#         print("✅ SUCCESS: Tables ready in 'agent/data/memory.db'")
        
#     except Exception as e:
#         print(f"❌ Error creating tables: {e}")

# if __name__ == "__main__":
#     main()



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

    # Users Schema 
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
    # Community Posts table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS community_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        content TEXT NOT NULL,
        likes INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        date_created REAL
    )""")
    # Comments table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        content TEXT NOT NULL,
        date_created REAL
    )""")

    # likes table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS post_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        date_created REAL,
        UNIQUE(post_id, user_id)
    )""")
    # Emotion Logs table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS emotion_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        emotion TEXT,
        confidence REAL,
        timestamp REAL
    )
    """)

    # Daily Summary table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS emotion_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        day TEXT,
        emotion TEXT,
        emotion_counts INTEGER DEFAULT 0, 
        updated_at REAL,
        UNIQUE(user_id, day, emotion)
    )""")

    # 1. NEW: INTERACTIONS TABLE (Chat History)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        ts REAL NOT NULL,
        readable_time TEXT NOT NULL,
        event_type TEXT NOT NULL,       -- 'conversation' or 'observation'
        user_input TEXT,
    )""")

    # 2. NEW: SIGNIFICANT EVENTS (Milestones/Triggers)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS significant_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        event_type TEXT, -- e.g., 'mood_swing', 'goal_reached'
        description TEXT,
        timestamp REAL
    )""")

    con.commit()
    # seed_dummy_data(con)
    con.close()

# def seed_dummy_data(con):
#     """Seeds test data if the database is empty (From V2 logic)."""
#     cur = con.cursor()
#     # Check if we already have users
#     if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
#         print("🌱 Seeding initial data...")
#         now = time.time()
#         cur.execute("""
#             INSERT INTO users (user_id, username, name, role, streak) 
#             VALUES ('user_001', 'test_user', 'Test User', 'member', 5)
#         """)
        
#         # Seed 7 days of sample emotions
#         today = datetime.now().date()
#         for i in range(7):
#             day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
#             cur.execute("""
#                 INSERT INTO emotion_daily (user_id, day, emotion, emotion_counts, updated_at)
#                 VALUES (?, ?, ?, ?, ?)
#             """, ('user_001', day, 'Neutral', random.randint(5, 15), now))
        
#         con.commit()
#         print("✅ Seeding complete.")

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
