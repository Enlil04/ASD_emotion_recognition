import sqlite3
import random
import time
import json
import os
import sys
from datetime import datetime, timedelta

# ==============================
# 1. ROBUST PATH SETUP (Matches setup_db.py)
# ==============================
# Get the folder where THIS file (seed_db.py) lives
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Smartly find the 'agent' folder
if os.path.basename(CURRENT_DIR) == "services":
    # If we are in 'services', go up one level
    AGENT_DIR = os.path.dirname(CURRENT_DIR)
elif os.path.basename(CURRENT_DIR) == "agent":
    # If we are already in 'agent', stay here
    AGENT_DIR = CURRENT_DIR
else:
    # If we are in the project root, look for 'agent'
    if os.path.exists(os.path.join(CURRENT_DIR, "agent")):
        AGENT_DIR = os.path.join(CURRENT_DIR, "agent")
    else:
        # Fallback: Assume current dir is the root
        AGENT_DIR = CURRENT_DIR

# Define the path exactly where setup_db.py put it
DB_PATH = os.path.join(AGENT_DIR, "data", "memory.db")

print(f"📂 TARGET DATABASE: {DB_PATH}")

# ==============================
# 2. SEED DATA
# ==============================
PRIMARY_USER = "user_001"
EMOTIONS = ["Happy", "Sad", "Neutral", "Anger", "Fear", "Surprise", "Disgust"]

DUMMY_USERS = [
    ("user_002", "amina_alt", "Amina", "student", 20, "Loves coding and coffee."),
    ("user_003", "liam_alt", "Liam", "mentor", 32, "Here to help others grow."),
    ("user_004", "sophia_alt", "Sophia", "parent", 45, "Supporting my kids' journey."),
    ("user_005", "omar_alt", "Omar", "member", 28, "Focused on mindfulness.")
]

POST_IDEAS = [
    "Just finished a 10-minute meditation. Feeling much better!",
    "Does anyone have tips for dealing with social anxiety at work?",
    "Small win: I actually stuck to my morning routine today.",
    "The weather is amazing today. Don't forget to step outside!",
    "Struggling a bit today, but reminding myself that it's okay to rest."
]

def seed_all():
    if not os.path.exists(DB_PATH):
        print(f"❌ ERROR: Database not found at {DB_PATH}")
        print("   👉 Please run 'python setup_db.py' first!")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now_ts = time.time()

    try:
        # --- 1. USERS ---
        print("👤 Seeding users...")
        cur.execute("DELETE FROM users")
        
        # Insert Primary User
        cur.execute("""
            INSERT OR REPLACE INTO users 
            (user_id, username, name, role, age, description, streak, connections, created_at, updated_at)
            VALUES (?, 'nimi_user', 'Test User', 'member', 25, 'Main test account.', 7, 150, ?, ?)
        """, (PRIMARY_USER, now_ts, now_ts))

        # Insert Dummy Users
        for uid, uname, name, role, age, desc in DUMMY_USERS:
            cur.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, username, name, role, age, description, streak, connections, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, uname, name, role, age, desc, random.randint(1, 15), random.randint(5, 50), now_ts, now_ts))

        # --- 2. USER PROFILES ---
        print("⚙️ Seeding user profile preferences...")
        # Check if table exists to avoid crash if setup_db was old
        try:
            cur.execute("DELETE FROM user_profiles")
            default_prefs = {
                "name": "Test User",
                "theme": "dark",
                "notifications": True,
                "triggers": ["loud noises", "crowds"]
            }
            cur.execute("""
                INSERT INTO user_profiles (user_id, preferences_json)
                VALUES (?, ?)
            """, (PRIMARY_USER, json.dumps(default_prefs)))
        except sqlite3.OperationalError:
            print("⚠️ Warning: 'user_profiles' table missing. Run setup_db.py again.")

        # --- 3. EMOTION DAILY ---
        print("📊 Seeding weekly emotion history...")
        cur.execute("DELETE FROM emotion_daily WHERE user_id = ?", (PRIMARY_USER,))
        
        today = datetime.now().date()
        for i in range(7):
            date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            
            daily_counts = {}
            total_frames = 0
            for emo in EMOTIONS:
                count = random.randint(5, 50) if emo in ["Neutral", "Happy"] else random.randint(0, 10)
                daily_counts[emo] = count
                total_frames += count
                
            cur.execute("""
                INSERT INTO emotion_daily (user_id, date_str, emotion_counts, total_frames)
                VALUES (?, ?, ?, ?)
            """, (PRIMARY_USER, date_str, json.dumps(daily_counts), total_frames))

        # --- 4. COMMUNITY POSTS ---
        print("📝 Seeding community posts...")
        cur.execute("DELETE FROM community_posts")
        
        post_ids = []
        for _ in range(5):
            poster_id = random.choice([u[0] for u in DUMMY_USERS] + [PRIMARY_USER])
            cur.execute("""
                INSERT INTO community_posts (user_id, content, likes, comments, date_created)
                VALUES (?, ?, ?, ?, ?)
            """, (poster_id, random.choice(POST_IDEAS), random.randint(0, 20), 0, now_ts))
            post_ids.append(cur.lastrowid)

        # --- 5. COMMENTS ---
        print("💬 Seeding comments...")
        cur.execute("DELETE FROM comments")
        
        generic_comments = ["Great post!", "I feel this too.", "Thanks for sharing.", "Hang in there!"]
        
        if post_ids: 
            for pid in post_ids:
                if random.choice([True, False]): 
                    commenter = random.choice([u[0] for u in DUMMY_USERS])
                    cur.execute("""
                        INSERT INTO comments (post_id, user_id, content, date_created)
                        VALUES (?, ?, ?, ?)
                    """, (pid, commenter, random.choice(generic_comments), now_ts))

        # --- 6. INTERACTIONS ---
        print("🤖 Seeding chat history...")
        cur.execute("DELETE FROM interactions")
        
        cur.execute("""
            INSERT INTO interactions 
            (user_id, timestamp, readable_time, event_type, user_input, agent_response, detected_emotion, confidence)
            VALUES (?, ?, ?, 'conversation', ?, ?, ?, ?)
        """, (
            PRIMARY_USER, 
            now_ts, 
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Hello Nimi!", 
            "Hello! I am Nimi, your emotional health assistant. How are you feeling today?", 
            "Neutral", 
            0.99
        ))

        conn.commit()
        print("✅ Database successfully seeded!")

    except sqlite3.OperationalError as e:
        print(f"❌ DATABASE ERROR: {e}")
        print("   This means the tables don't exist yet.")
        print("   👉 PLEASE RUN: python setup_db.py")
    
    finally:
        conn.close()

if __name__ == "__main__":
    seed_all()