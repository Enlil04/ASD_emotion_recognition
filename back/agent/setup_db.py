import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# ==============================
# 1. SMART PATH CALCULATION
# ==============================
# Get the folder where THIS file lives
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Check if we are inside the 'services' subfolder
if os.path.basename(CURRENT_DIR) == "services":
    # If yes, go up one level to find 'agent'
    AGENT_DIR = os.path.dirname(CURRENT_DIR)
else:
    # If no, we are already in 'agent' (or the root we want)
    AGENT_DIR = CURRENT_DIR

# Now we define data inside 'agent/data'
DATA_DIR = os.path.join(AGENT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "memory.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

print(f"📂 DATABASE SET TO: {DB_PATH}")

# ==============================
# 2. SQLALCHEMY SETUP
# ==============================
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==============================
# 3. INITIALIZATION
# ==============================
def main():
    # If setup_db is in agent/, we need to make sure python can find 'services' if models are there
    if os.path.basename(CURRENT_DIR) != "services":
         sys.path.append(os.path.join(AGENT_DIR, "services"))

    try:
        # Import models to register tables
        # Try importing as if we are in root, then as if we are in package
        try:
            import models 
        except ImportError:
            from services import models

        print("🔄 Updating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ SUCCESS: Tables ready in 'agent/data/memory.db'")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")

if __name__ == "__main__":
    main()






# import sqlite3
# import os
# import time
# from datetime import datetime, timedelta
# import random

# from sqlmodel import create_engine
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.ext.declarative import declarative_base

# # ==============================
# # DB PATH (same as server)
# # ==============================

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# DB_PATH = os.path.join(BASE_DIR, "data", "memory.db")
# SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"


# engine = create_engine(
#     SQLALCHEMY_DATABASE_URL, 
#     connect_args={"check_same_thread": False} # Required for SQLite
# )

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# # 4. Base class for models (used in models.py)
# Base = declarative_base()

# # 5. Dependency (This is the get_db you need!)
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # ==============================
# # DB SETUP AND SEEDING
# # ==============================

# DATA_DIR = "data"
# os.makedirs(DATA_DIR, exist_ok=True)
# DB_PATH = os.path.join(DATA_DIR, "memory.db")

# EMOTIONS = ["Happy", "Sad", "Neutral", "Anger", "Fear", "Surprise", "Disgust"]

# def setup_tables(con):
#     cur = con.cursor()

#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS users (
#         user_id TEXT PRIMARY KEY,
#         preferences_json TEXT,
#         created_at REAL,
#         updated_at REAL
#     )
#     """)

#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS emotion_logs (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         user_id TEXT,
#         emotion TEXT,
#         confidence REAL,
#         timestamp REAL
#     )
#     """)

#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS emotion_daily (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         user_id TEXT,
#         day TEXT,
#         emotion TEXT,
#         count INTEGER,
#         updated_at REAL,
#         UNIQUE(user_id, day, emotion)
#     )
#     """)

#     con.commit()


# def seed_dummy_data(con):
#     user_id = "user_001"
#     now = time.time()

#     cur = con.cursor()

#     # Ensure user exists
#     cur.execute("""
#     INSERT INTO users (user_id, preferences_json, created_at, updated_at)
#     VALUES (?, ?, ?, ?)
#     ON CONFLICT(user_id) DO UPDATE SET updated_at=excluded.updated_at;
#     """, (user_id, '{"name":"Test User"}', now, now))

#     # Clear old data
#     cur.execute("DELETE FROM emotion_daily WHERE user_id = ?", (user_id,))
#     cur.execute("DELETE FROM emotion_logs WHERE user_id = ?", (user_id,))

#     today = datetime.now().date()

#     for i in range(7):
#         d = (today - timedelta(days=i)).strftime("%Y-%m-%d")

#         # 🔴 SAD-HEAVY DISTRIBUTION
#         daily_counts = {
#             "Sad": random.randint(15, 30),
#             "Neutral": random.randint(5, 12),
#             "Happy": random.randint(2, 8),
#             "Anger": random.randint(1, 6),
#             "Fear": random.randint(1, 6),
#             "Surprise": random.randint(0, 3),
#             "Disgust": random.randint(0, 3),
#         }

#         for emo in EMOTIONS:
#             cnt = int(daily_counts.get(emo, 0))

#             cur.execute("""
#             INSERT INTO emotion_daily (user_id, day, emotion, count, updated_at)
#             VALUES (?, ?, ?, ?, ?)
#             ON CONFLICT(user_id, day, emotion)
#             DO UPDATE SET count=excluded.count, updated_at=excluded.updated_at;
#             """, (user_id, d, emo, cnt, now))

#             for _ in range(cnt):
#                 cur.execute("""
#                 INSERT INTO emotion_logs (user_id, emotion, confidence, timestamp)
#                 VALUES (?, ?, ?, ?)
#                 """, (
#                     user_id,
#                     emo,
#                     round(random.uniform(0.6, 0.99), 2),
#                     now
#                 ))

#     con.commit()
#     print("✅ Seeded last 7 days with SAD-dominant emotion data.")


# def main():
#     print(f"Initializing database at: {os.path.abspath(DB_PATH)}")
#     con = sqlite3.connect(DB_PATH)

#     setup_tables(con)
#     seed_dummy_data(con)

#     con.close()
#     print("✅ Database ready.")


# if __name__ == "__main__":
#     main()
