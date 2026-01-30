# # import os
# # import sys
# # from sqlalchemy import create_engine
# # from sqlalchemy.orm import sessionmaker
# # from sqlalchemy.ext.declarative import declarative_base

# # # ==============================
# # # 1. SMART PATH CALCULATION
# # # ==============================
# # # Get the folder where THIS file lives
# # CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# # # Check if we are inside the 'services' subfolder
# # if os.path.basename(CURRENT_DIR) == "services":
# #     # If yes, go up one level to find 'agent'
# #     AGENT_DIR = os.path.dirname(CURRENT_DIR)
# # else:
# #     # If no, we are already in 'agent' (or the root we want)
# #     AGENT_DIR = CURRENT_DIR

# # # Now we define data inside 'agent/data'
# # DATA_DIR = os.path.join(AGENT_DIR, "data")
# # os.makedirs(DATA_DIR, exist_ok=True)

# # DB_PATH = os.path.join(DATA_DIR, "memory.db")
# # SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# # print(f"📂 DATABASE SET TO: {DB_PATH}")

# # # ==============================
# # # 2. SQLALCHEMY SETUP
# # # ==============================
# # engine = create_engine(
# #     SQLALCHEMY_DATABASE_URL, 
# #     connect_args={"check_same_thread": False}
# # )
# # SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# # Base = declarative_base()

# # def get_db():
# #     db = SessionLocal()
# #     try:
# #         yield db
# #     finally:
# #         db.close()

# # # ==============================
# # # 3. INITIALIZATION
# # # ==============================
# # def main():
# #     # If setup_db is in agent/, we need to make sure python can find 'services' if models are there
# #     if os.path.basename(CURRENT_DIR) != "services":
# #          sys.path.append(os.path.join(AGENT_DIR, "services"))

# #     try:
# #         # Import models to register tables
# #         # Try importing as if we are in root, then as if we are in package
# #         try:
# #             import models 
# #         except ImportError:
# #             from services import models

# #         print("🔄 Updating database tables...")
# #         Base.metadata.create_all(bind=engine)
# #         print("✅ SUCCESS: Tables ready in 'agent/data/memory.db'")
        
# #     except Exception as e:
# #         print(f"❌ Error creating tables: {e}")

# # if __name__ == "__main__":
# #     main()



# import os
# import sys
# import sqlite3
# import random
# import time
# from datetime import datetime, timedelta
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base

# # ==============================
# # 1. SMART PATH CALCULATION (From V1)
# # ==============================
# CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# # Navigate to the 'agent' root directory
# if os.path.basename(CURRENT_DIR) == "services":
#     AGENT_DIR = os.path.dirname(CURRENT_DIR)
# else:
#     AGENT_DIR = CURRENT_DIR

# DATA_DIR = os.path.join(AGENT_DIR, "data")
# os.makedirs(DATA_DIR, exist_ok=True)

# DB_PATH = os.path.join(DATA_DIR, "memory.db")
# SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# # ==============================
# # 2. SQLALCHEMY SETUP (From V1)
# # ==============================
# engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # ==============================
# # 3. SCHEMA DEFINITIONS & SEEDING (Hybrid)
# # ==============================
# def setup_tables():
#     """Uses raw sqlite3 for complex constraints and seeding."""
#     print(f"🔄 Initializing database at: {DB_PATH}")
#     con = sqlite3.connect(DB_PATH)
#     cur = con.cursor()

#     # 1. USERS
#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS users (
#         user_id TEXT PRIMARY KEY,
#         username TEXT UNIQUE,
#         name TEXT,
#         role TEXT,
#         age INTEGER,
#         photo_url TEXT,
#         description TEXT,
#         connections INTEGER DEFAULT 0,
#         streak INTEGER DEFAULT 0,
#         preferences_json TEXT,
#         created_at REAL,
#         updated_at REAL
#     )""")

#     # 2. COMMUNITY POSTS
#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS community_posts (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         user_id TEXT NOT NULL,
#         content TEXT NOT NULL,
#         likes INTEGER DEFAULT 0,
#         comments INTEGER DEFAULT 0,
#         date_created REAL
#     )""")

#     # 3. COMMENTS
#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS comments (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         post_id INTEGER NOT NULL,
#         user_id TEXT NOT NULL,
#         content TEXT NOT NULL,
#         date_created REAL
#     )""")

#     # 4. POST LIKES
#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS post_likes (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         post_id INTEGER NOT NULL,
#         user_id TEXT NOT NULL,
#         date_created REAL,
#         UNIQUE(post_id, user_id)
#     )""")

#     # 5. EMOTION LOGS (Raw data)
#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS emotion_logs (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         user_id TEXT,
#         emotion TEXT,
#         confidence REAL,
#         timestamp REAL
#     )""")

#     # 6. EMOTION DAILY (Summary) - CRITICAL: 'emotion_counts'
#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS emotion_daily (
#         user_id TEXT,
#         date_str TEXT,
#         emotion_counts TEXT,
#         total_frames INTEGER,
#         PRIMARY KEY (user_id, date_str)
#     )""")

#     # 7. INTERACTIONS (Standardized for AI Chat)
# # --- TABLE 1: INTERACTIONS (Chat History) ---
#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS interactions (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         user_id TEXT NOT NULL,
#         timestamp REAL NOT NULL,        -- Matches 'timestamp' usage
#         readable_time TEXT NOT NULL,
#         event_type TEXT NOT NULL,       
#         user_input TEXT,
#         agent_response TEXT,
#         detected_emotion TEXT,
#         confidence REAL
#     )""")

#     # 8. SIGNIFICANT EVENTS
#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS significant_events (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         user_id TEXT,
#         timestamp REAL,                  -- Matches 'timestamp' usage
#         event_type TEXT,
#         description TEXT,
#         context_json TEXT
#     )""")

#     # 9. USER PROFILES
#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS user_profiles (
#         user_id TEXT PRIMARY KEY,
#         preferences_json TEXT
#     )""")

    

#     con.commit()
#     con.close()

# # ==============================
# # 4. EXECUTION
# # ==============================
# if __name__ == "__main__":
#     # Ensure services are in path for model importing
#     if os.path.basename(CURRENT_DIR) != "services":
#         sys.path.append(os.path.join(AGENT_DIR, "services"))
    
#     # Run the setup
#     setup_tables()
#     print("🚀 Database is synchronized and ready.")

import os
import sys
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ... (Path calculation remains the same as previous) ...
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(CURRENT_DIR) == "services":
    AGENT_DIR = os.path.dirname(CURRENT_DIR)
else:
    AGENT_DIR = CURRENT_DIR

DATA_DIR = os.path.join(AGENT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "memory.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# ... (SQLAlchemy setup remains the same) ...
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def setup_tables():
    print(f"🔄 Initializing database at: {DB_PATH}")
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # 1. USERS (Updated photo_url -> photo)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        name TEXT,
        role TEXT,
        age INTEGER,
        photo TEXT,               -- ✅ FIXED
        description TEXT,
        connections INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0,
        preferences_json TEXT,
        created_at REAL,
        updated_at REAL
    )""")

    # ... (Rest of the tables remain the same) ...
    
    # 2. COMMUNITY POSTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS community_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        content TEXT NOT NULL,
        likes INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        date_created REAL,
        is_deleted INTEGER DEFAULT 0
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

    # 5. COMMUNITY REPORTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS community_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        reporter_user_id TEXT NOT NULL,
        reason TEXT,
        date_created REAL
    )""")

    # 6. EMOTION LOGS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS emotion_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        emotion TEXT,
        confidence REAL,
        timestamp REAL
    )""")

    # 7. EMOTION DAILY
    cur.execute("""
    CREATE TABLE IF NOT EXISTS emotion_daily (
        user_id TEXT,
        date_str TEXT,
        emotion_counts TEXT,
        total_frames INTEGER,
        PRIMARY KEY (user_id, date_str)
    )""")

    # 8. INTERACTIONS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        timestamp REAL NOT NULL,
        readable_time TEXT NOT NULL,
        event_type TEXT NOT NULL,       
        user_input TEXT,
        agent_response TEXT,
        detected_emotion TEXT,
        confidence REAL
    )""")

    # 9. SIGNIFICANT EVENTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS significant_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        timestamp REAL,
        event_type TEXT,
        description TEXT,
        context_json TEXT
    )""")

    # 10. USER PROFILES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id TEXT PRIMARY KEY,
        preferences_json TEXT
    )""")

    con.commit()
    con.close()

if __name__ == "__main__":
    setup_tables()
    print("🚀 Database is synchronized and ready.")