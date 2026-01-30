import sqlite3
import random
import time
from datetime import datetime, timedelta

# Import the source of truth for the database path
try:
    from setup_db import DB_PATH
except ImportError:
    DB_PATH = "data/memory.db"

PRIMARY_USER = "user_001"
EMOTIONS = ["Happy", "Sad", "Neutral", "Anger", "Fear", "Surprise", "Disgust"]
DUMMY_USERS = [
    ("user_002", "Amina", "student", 20, "Loves coding and coffee."),
    ("user_003", "Liam", "mentor", 32, "Here to help others grow."),
    ("user_004", "Sophia", "parent", 45, "Supporting my kids' journey."),
    ("user_005", "Omar", "member", 28, "Focused on mindfulness.")
]

POST_IDEAS = [
    "Just finished a 10-minute meditation. Feeling much better!",
    "Does anyone have tips for dealing with social anxiety at work?",
    "Small win: I actually stuck to my morning routine today.",
    "The weather is amazing today. Don't forget to step outside!",
    "Struggling a bit today, but reminding myself that it's okay to rest."
]

def seed_all():
    print(f"🌱 Starting seed process for: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = time.time()

    # 1) USERS
    print("👤 Seeding users...")
    cur.execute("""
        INSERT OR REPLACE INTO users
        (user_id, username, name, role, age, description, streak, connections, created_at, updated_at)
        VALUES (?, 'nimi_user', 'Test User', 'member', 21, 'Main test account.', 7, 150, ?, ?)
    """, (PRIMARY_USER, now, now))

    for uid, name, role, age, desc in DUMMY_USERS:
        cur.execute("""
            INSERT OR REPLACE INTO users
            (user_id, username, name, role, age, description, streak, connections, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uid,
            f"{name.lower()}_alt",
            name,
            role,
            age,
            desc,
            random.randint(1, 15),
            random.randint(5, 50),
            now,
            now
        ))

    # 2) EMOTION DAILY (uses emotion_counts per setup_db.py)
    print("📊 Seeding weekly emotion history...")
    cur.execute("DELETE FROM emotion_daily WHERE user_id = ?", (PRIMARY_USER,))
    today = datetime.now().date()
    for i in range(7):
        day_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        for emo in EMOTIONS:
            count = random.randint(5, 20) if emo in ["Neutral", "Happy"] else random.randint(0, 5)
            if count > 0:
                cur.execute("""
                    INSERT INTO emotion_daily (user_id, day, emotion, emotion_counts, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (PRIMARY_USER, day_str, emo, count, now))

    # 3) COMMUNITY POSTS + COMMENTS (if comments table exists)
    print("📝 Seeding community posts...")
    cur.execute("DELETE FROM community_posts")

    try:
        cur.execute("DELETE FROM comments")
        has_comments_table = True
    except sqlite3.OperationalError:
        has_comments_table = False
        print("⚠️ Skipping comments: 'comments' table not found in DB.")

    post_ids = []
    for _ in range(5):
        poster = random.choice([u[0] for u in DUMMY_USERS] + [PRIMARY_USER])
        cur.execute("""
            INSERT INTO community_posts (user_id, content, likes, comments, date_created)
            VALUES (?, ?, ?, ?, ?)
        """, (poster, random.choice(POST_IDEAS), random.randint(0, 10), 0, now))
        post_ids.append(cur.lastrowid)

    # Optional: seed a few comments
    if has_comments_table and post_ids:
        for _ in range(6):
            commenter = random.choice([u[0] for u in DUMMY_USERS] + [PRIMARY_USER])
            pid = random.choice(post_ids)
            cur.execute("""
                INSERT INTO comments (post_id, user_id, content, date_created)
                VALUES (?, ?, ?, ?)
            """, (pid, commenter, "Thanks for sharing — you’re not alone.", now))

    # 4) INTERACTIONS (matches setup_db.py columns)
    print("💬 Seeding chat history...")
    cur.execute("DELETE FROM interactions")

    readable = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO interactions (user_id, ts, readable_time, event_type, user_input)
        VALUES (?, ?, ?, ?, ?)
    """, (
        PRIMARY_USER,
        now,
        readable,
        "conversation",
        "Hello! I am Nimi, your emotional health assistant."
    ))

    conn.commit()
    conn.close()
    print("✅ Database successfully seeded!")

if __name__ == "__main__":
    seed_all()


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