import sqlite3
import random
import time
import os
from datetime import datetime, timedelta
import json

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

COMMENT_IDEAS = [
    "Proud of you 💙",
    "That’s a good step.",
    "Same here, you’re not alone.",
    "Try slow breathing, it helps me.",
    "Thanks for sharing this."
]

def _table_exists(cur, name: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None

def seed_all():
    if not os.path.exists(DB_PATH):
        print(f"❌ ERROR: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now_ts = time.time()

    try:
        # --- 0) QUICK SAFETY: make sure tables exist ---
        # (If setup_db.py already ran, you're fine. This just avoids crashing.)
        required_tables = ["users", "community_posts", "post_likes", "comments"]
        for t in required_tables:
            if not _table_exists(cur, t):
                print(f"❌ ERROR: Missing table '{t}'. Run setup_db.py first.")
                return

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

        # --- 2. CLEAN COMMUNITY TABLES (ORDER MATTERS) ---
        print("🧹 Clearing community tables...")
        # delete children first
        cur.execute("DELETE FROM post_likes")
        cur.execute("DELETE FROM comments")

        # optional tables (if exist)
        if _table_exists(cur, "community_reports"):
            cur.execute("DELETE FROM community_reports")

        # then delete posts
        cur.execute("DELETE FROM community_posts")

        # --- 3. COMMUNITY POSTS + REAL LIKES ---
        print("📝 Seeding community posts (with real likes)...")

        all_user_ids = [u[0] for u in DUMMY_USERS] + [PRIMARY_USER]

        post_ids = []
        for _ in range(5):
            poster_id = random.choice(all_user_ids)

            # IMPORTANT: likes start at 0 (truth is post_likes table)
            cur.execute("""
                INSERT INTO community_posts (user_id, content, likes, comments, date_created, is_deleted)
                VALUES (?, ?, 0, 0, ?, 0)
            """, (poster_id, random.choice(POST_IDEAS), now_ts))

            post_id = cur.lastrowid
            post_ids.append(post_id)

            # Seed likes properly by inserting rows into post_likes
            # Each row = one distinct user liked this post (UNIQUE(post_id, user_id))
            k = random.randint(0, min(4, len(all_user_ids)))  # up to 4 likes
            liked_users = random.sample(all_user_ids, k)
            for uid in liked_users:
                cur.execute("""
                    INSERT OR IGNORE INTO post_likes (post_id, user_id, date_created)
                    VALUES (?, ?, ?)
                """, (post_id, uid, now_ts))

        # --- 4. OPTIONAL: Seed a few comments (and sync comment counts) ---
        # (Your backend also recalculates comments count using COUNT(comments).)
        for post_id in post_ids:
            num_comments = random.randint(0, 3)
            for _ in range(num_comments):
                commenter = random.choice(all_user_ids)
                cur.execute("""
                    INSERT INTO comments (post_id, user_id, content, date_created)
                    VALUES (?, ?, ?, ?)
                """, (post_id, commenter, random.choice(COMMENT_IDEAS), now_ts))

        # --- 5. SYNC CACHED COUNTS (likes + comments) ---
        # likes = COUNT(post_likes)
        cur.execute("""
            UPDATE community_posts
            SET likes = (
                SELECT COUNT(*)
                FROM post_likes pl
                WHERE pl.post_id = community_posts.id
            )
        """)

        # comments = COUNT(comments)
        cur.execute("""
            UPDATE community_posts
            SET comments = (
                SELECT COUNT(*)
                FROM comments c
                WHERE c.post_id = community_posts.id
            )
        """)

        # ... (after the mock emotion data loop) ...

        # --- 6. SEED GUARDIAN RELATIONSHIPS (CRITICAL FOR TESTING) ---
        print("🔗 Seeding Guardian/Patient links...")
        
        # We link 'user_004' (Sophia - Parent) to watch over 'user_001' (You - Patient)
        # We also link 'user_003' (Liam - Mentor) to watch 'user_002' (Amina)
        relationships = [
            ("user_004", PRIMARY_USER), 
            ("user_003", "user_002")
        ]
        
        for guardian_id, patient_id in relationships:
            cur.execute("""
                INSERT OR REPLACE INTO therapist_patient 
                (therapist_id, patient_id, date_assigned)
                VALUES (?, ?, ?)
            """, (guardian_id, patient_id, now_ts))

        # Update the patients to have the codes too (for consistency)
        cur.execute(f"UPDATE users SET therapist_code = 'CODE_123' WHERE user_id = '{PRIMARY_USER}'")
        
        print("✅ Guardian links established.")

        # ... (conn.commit() follows here) ...
        conn.commit()
        
                # =====================================================
        # 🔹 MOCK LAST 7 DAYS FOR DASHBOARD + RECOMMENDATION
        # (SAFE TO COMMENT OUT LATER)
        # =====================================================
        print("📊 Seeding mock emotion data for last 7 days...")

        cur.execute("DELETE FROM emotion_daily WHERE user_id = ?", (PRIMARY_USER,))

        today = datetime.now().date()

        # mock_week = [
        #     {"Happy": 12, "Neutral": 6, "Sad": 2},           # 6 days ago
        #     {"Happy": 8,  "Neutral": 7, "Sad": 3},           # 5 days ago
        #     {"Neutral": 10, "Sad": 4, "Anger": 2},           # 4 days ago
        #     {"Happy": 6, "Neutral": 6, "Fear": 2},           # 3 days ago
        #     {"Happy": 10, "Surprise": 3, "Neutral": 4},      # 2 days ago
        #     {"Sad": 6, "Neutral": 5, "Anger": 3},            # yesterday
        #     {"Happy": 9, "Neutral": 6, "Sad": 1},            # today
        # ]
        
        mock_week = [
    {"Sad": 10, "Neutral": 5, "Happy": 2},          # 6 days ago
    {"Sad": 8,  "Neutral": 6, "Happy": 3},          # 5 days ago
    {"Sad": 9,  "Anger": 3, "Neutral": 4},          # 4 days ago
    {"Sad": 7,  "Neutral": 5, "Fear": 2},           # 3 days ago
    {"Sad": 11, "Neutral": 3, "Happy": 2},          # 2 days ago
    {"Sad": 6,  "Neutral": 4, "Anger": 3},          # yesterday
    {"Sad": 8,  "Neutral": 5, "Happy": 1},          # today
]

        for i, emotions in enumerate(reversed(mock_week)):
            day_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            total_frames = sum(emotions.values())

            cur.execute("""
                INSERT OR REPLACE INTO emotion_daily
                (user_id, date_str, emotion_counts, total_frames)
                VALUES (?, ?, ?, ?)
            """, (
                PRIMARY_USER,
                day_str,
                json.dumps(emotions),
                total_frames
            ))

        print("✅ Mock 7-day emotion history seeded.")
        
        #---------------------------------

        conn.commit()
        print("✅ Database successfully seeded!")
        print(f"📍 DB: {DB_PATH}")

    except sqlite3.OperationalError as e:
        print(f"❌ DATABASE ERROR: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    seed_all()



# import sqlite3
# import random
# import time
# import json
# import os
# import sys
# from datetime import datetime, timedelta

# # ... (Path logic same as setup_db.py) ...
# CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# if os.path.basename(CURRENT_DIR) == "services":
#     AGENT_DIR = os.path.dirname(CURRENT_DIR)
# else:
#     AGENT_DIR = CURRENT_DIR

# DB_PATH = os.path.join(AGENT_DIR, "data", "memory.db")

# PRIMARY_USER = "user_001"
# EMOTIONS = ["Happy", "Sad", "Neutral", "Anger", "Fear", "Surprise", "Disgust"]

# # Added photo placeholder
# DUMMY_USERS = [
#     ("user_002", "amina_alt", "Amina", "student", 20, "Loves coding.", "https://i.pravatar.cc/150?u=amina"),
#     ("user_003", "liam_alt", "Liam", "mentor", 32, "Here to help.", "https://i.pravatar.cc/150?u=liam"),
#     ("user_004", "sophia_alt", "Sophia", "parent", 45, "Supporting kids.", "https://i.pravatar.cc/150?u=sophia"),
#     ("user_005", "omar_alt", "Omar", "member", 28, "Mindfulness.", "https://i.pravatar.cc/150?u=omar")
# ]

# POST_IDEAS = [
#     "Just finished a 10-minute meditation!",
#     "Tips for social anxiety?",
#     "Small win: Stuck to my routine.",
#     "The weather is amazing today.",
#     "Struggling a bit, but that is okay."
# ]

# def seed_all():
#     if not os.path.exists(DB_PATH):
#         print(f"❌ ERROR: Database not found at {DB_PATH}")
#         return

#     conn = sqlite3.connect(DB_PATH)
#     cur = conn.cursor()
#     now_ts = time.time()

#     try:
#         # --- 1. USERS ---
#         print("👤 Seeding users...")
#         cur.execute("DELETE FROM users")
        
#         # Insert Primary User (Added 'photo')
#         cur.execute("""
#             INSERT OR REPLACE INTO users 
#             (user_id, username, name, role, age, description, photo, streak, connections, created_at, updated_at)
#             VALUES (?, 'nimi_user', 'Test User', 'member', 25, 'Main account.', 'https://i.pravatar.cc/150?u=test', 7, 150, ?, ?)
#         """, (PRIMARY_USER, now_ts, now_ts))

#         # Insert Dummy Users (Added 'photo')
#         for uid, uname, name, role, age, desc, photo in DUMMY_USERS:
#             cur.execute("""
#                 INSERT OR REPLACE INTO users 
#                 (user_id, username, name, role, age, description, photo, streak, connections, created_at, updated_at)
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """, (uid, uname, name, role, age, desc, photo, random.randint(1, 15), random.randint(5, 50), now_ts, now_ts))

#         # ... (Rest of seed logic for profiles, posts, etc. remains the same) ...
#         # (Copy the rest of the previous seed script here)

#         # --- 4. COMMUNITY POSTS ---
#         print("📝 Seeding community posts...")
#         cur.execute("DELETE FROM community_posts")
        
#         for _ in range(5):
#             poster_id = random.choice([u[0] for u in DUMMY_USERS] + [PRIMARY_USER])
#             cur.execute("""
#                 INSERT INTO community_posts (user_id, content, likes, comments, date_created, is_deleted)
#                 VALUES (?, ?, ?, ?, ?, 0)
#             """, (poster_id, random.choice(POST_IDEAS), random.randint(0, 20), 0, now_ts))

#         conn.commit()
#         print("✅ Database successfully seeded!")

#     except sqlite3.OperationalError as e:
#         print(f"❌ DATABASE ERROR: {e}")
#     finally:
#         conn.close()

# if __name__ == "__main__":
#     seed_all()


# import sqlite3
# import random
# import time
# from datetime import datetime, timedelta

# # Import the source of truth for the database path
# try:
#     from setup_db import DB_PATH
# except ImportError:
#     DB_PATH = "data/memory.db"

# PRIMARY_USER = "user_001"
# EMOTIONS = ["Happy", "Sad", "Neutral", "Anger", "Fear", "Surprise", "Disgust"]
# DUMMY_USERS = [
#     ("user_002", "Amina", "student", 20, "Loves coding and coffee."),
#     ("user_003", "Liam", "mentor", 32, "Here to help others grow."),
#     ("user_004", "Sophia", "parent", 45, "Supporting my kids' journey."),
#     ("user_005", "Omar", "member", 28, "Focused on mindfulness.")
# ]

# POST_IDEAS = [
#     "Just finished a 10-minute meditation. Feeling much better!",
#     "Does anyone have tips for dealing with social anxiety at work?",
#     "Small win: I actually stuck to my morning routine today.",
#     "The weather is amazing today. Don't forget to step outside!",
#     "Struggling a bit today, but reminding myself that it's okay to rest."
# ]

# def seed_all():
#     print(f"🌱 Starting seed process for: {DB_PATH}")
#     conn = sqlite3.connect(DB_PATH)
#     cur = conn.cursor()
#     now = time.time()

#     # 1. USERS (Updated to fit your new columns: age, description, etc.)
#     print("👤 Seeding users...")
#     cur.execute("""
#         INSERT OR REPLACE INTO users (user_id, username, name, role, age, description, streak, connections, created_at, updated_at)
#         VALUES (?, 'nimi_user', 'Test User', 'member', 21, 'Main test account.', 7, 150, ?, ?)
#     """, (PRIMARY_USER, now, now))

#     for uid, name, role, age, desc in DUMMY_USERS:
#         cur.execute("""
#             INSERT OR REPLACE INTO users (user_id, username, name, role, age, description, streak, connections, created_at, updated_at)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """, (uid, f"{name.lower()}_alt", name, role, age, desc, random.randint(1, 15), random.randint(5, 50), now, now))

#     # 2. EMOTION HISTORY (Matches your emotion_daily table)
#     print("📊 Seeding weekly emotion history...")
#     cur.execute("DELETE FROM emotion_daily WHERE user_id = ?", (PRIMARY_USER,))
#     today = datetime.now().date()
#     for i in range(7):
#         day_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
#         for emo in EMOTIONS:
#             count = random.randint(5, 20) if emo in ["Neutral", "Happy"] else random.randint(0, 5)
#             if count > 0:
#                 cur.execute("""
#                     INSERT INTO emotion_daily (user_id, day, emotion, emotion_counts, updated_at)
#                     VALUES (?, ?, ?, ?, ?)
#                 """, (PRIMARY_USER, day_str, emo, count, now))

#     # 3. COMMUNITY (Checking if table exists first to prevent crash)
#     print("📝 Seeding community posts...")
#     cur.execute("DELETE FROM community_posts")
    
#     # IMPORTANT: Only seed comments if you have added the table to setup_db.py
#     try:
#         cur.execute("DELETE FROM comments")
#         has_comments_table = True
#     except sqlite3.OperationalError:
#         has_comments_table = False
#         print("⚠️ Skipping comments: 'comments' table not found in DB.")

#     for _ in range(5):
#         poster = random.choice([u[0] for u in DUMMY_USERS] + [PRIMARY_USER])
#         cur.execute("""
#             INSERT INTO community_posts (user_id, content, likes, comments, date_created)
#             VALUES (?, ?, ?, ?, ?)
#         """, (poster, random.choice(POST_IDEAS), random.randint(0, 10), 0, now))

#     # 4. CHAT HISTORY
#     print("💬 Seeding chat history...")
#     cur.execute("DELETE FROM interactions")
#     cur.execute("""
#         INSERT INTO interactions (user_id, content, timestamp)
#         VALUES (?, 'assistant', 'Hello! I am Nimi, your emotional health assistant.', ?)
#     """, (PRIMARY_USER, now))

#     conn.commit()
#     conn.close()
#     print("✅ Database successfully seeded!")

# if __name__ == "__main__":
#     seed_all()