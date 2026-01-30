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

# =========================================================
# TEMPORARY TEST SECTION (comment out anytime)
# ---------------------------------------------------------
# Purpose:
#   Seed special test users to force recommendation modes:
#     - test_weekly  -> has emotion_daily (last 7 days) => mode=weekly
#     - test_recent  -> no weekly, but has emotion_logs in last 72h => mode=recent
#     - test_new     -> no logs, no daily => mode=new_user
#
# How to use:
#   1) Keep ENABLE_RECO_TEST_SEEDS = True
#   2) Run: python setup.py
#   3) Call:
#        /api/recommendation/today?user_id=test_weekly
#        /api/recommendation/today?user_id=test_recent
#        /api/recommendation/today?user_id=test_new
#   4) When done, set ENABLE_RECO_TEST_SEEDS=False or comment this block.
# =========================================================
ENABLE_RECO_TEST_SEEDS = False  # <-- turn off anytime

RECO_TEST_USERS = {
    # Weekly user: angry-heavy last 7 days
    "test_weekly": {
        "dominant": "Anger",
        "profile": ("Weekly Tester", "member", 22, "For testing weekly recommendations."),
    },
    # Recent user: NO weekly, but has one recent log (sad)
    "test_recent": {
        "recent_emotion": "Sad",
        "profile": ("Recent Tester", "member", 22, "For testing recent fallback recommendations."),
    },
    # New user: no data at all
    "test_new": {
        "profile": ("New Tester", "member", 22, "For testing new-user onboarding recommendations."),
    },
}


def _today_yyyy_mm_dd() -> str:
    return datetime.now().date().strftime("%Y-%m-%d")


def _last_days_yyyy_mm_dd(n: int = 7) -> list[str]:
    today = datetime.now().date()
    return [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in reversed(range(n))]


def _upsert_user(cur, user_id: str, name: str, role: str, age: int, description: str, now_ts: float):
    # keep minimal fields; matches your users schema
    cur.execute("""
    INSERT INTO users (
        user_id, name, role, age, description, photo, streak, connections, username,
        preferences_json, created_at, updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
        name=excluded.name,
        role=excluded.role,
        age=excluded.age,
        description=excluded.description,
        updated_at=excluded.updated_at
    """, (
        user_id,
        name,
        role,
        age,
        description,
        "",
        0,
        0,
        user_id,  # username = user_id for test users
        json_preferences(name),
        now_ts,
        now_ts
    ))


def _clear_emotion_data_for_user(cur, user_id: str):
    cur.execute("DELETE FROM emotion_daily WHERE user_id = ?", (user_id,))
    cur.execute("DELETE FROM emotion_logs WHERE user_id = ?", (user_id,))


def _seed_weekly_emotion_daily(cur, user_id: str, now_ts: float, dominant: str = "Anger"):
    # Create a 7-day distribution where "dominant" wins
    days = _last_days_yyyy_mm_dd(7)

    for d in days:
        # baseline
        base = {
            "Happy": random.randint(0, 3),
            "Sad": random.randint(0, 3),
            "Neutral": random.randint(0, 4),
            "Anger": random.randint(0, 3),
            "Fear": random.randint(0, 2),
            "Surprise": random.randint(0, 1),
            "Disgust": random.randint(0, 1),
        }

        # dominant boost
        base[dominant] += random.randint(8, 16)

        for emo in EMOTIONS:
            cnt = int(base.get(emo, 0))
            cur.execute("""
            INSERT INTO emotion_daily (user_id, day, emotion, count, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, day, emotion)
            DO UPDATE SET count=excluded.count, updated_at=excluded.updated_at;
            """, (user_id, d, emo, cnt, now_ts))

        # a few logs too (optional)
        # Keep logs small
        dom_cnt = min(base[dominant], 6)
        for _ in range(dom_cnt):
            cur.execute("""
            INSERT INTO emotion_logs (user_id, emotion, confidence, timestamp)
            VALUES (?, ?, ?, ?)
            """, (
                user_id,
                dominant,
                round(random.uniform(0.65, 0.98), 2),
                now_ts - random.randint(0, 60 * 60 * 24 * 3),
            ))


def _seed_recent_emotion_log_only(cur, user_id: str, now_ts: float, emotion: str = "Sad"):
    # Ensure NO emotion_daily in last 7 days (or at all)
    # Insert a single recent log within last 72 hours
    cur.execute("""
    INSERT INTO emotion_logs (user_id, emotion, confidence, timestamp)
    VALUES (?, ?, ?, ?)
    """, (user_id, emotion, 0.9, now_ts - random.randint(0, 60 * 60 * 24 * 2)))


def _seed_new_user_no_emotion(cur, user_id: str):
    # Do nothing: no emotion_daily, no emotion_logs
    pass


def seed_reco_test_users(con):
    """
    Creates the three test users to force each recommendation mode.
    Safe to re-run: it clears only emotion tables for these test users.
    """
    cur = con.cursor()
    now_ts = time.time()

    # test_weekly
    uid = "test_weekly"
    name, role, age, desc = RECO_TEST_USERS[uid]["profile"]
    _upsert_user(cur, uid, name, role, age, desc, now_ts)
    _clear_emotion_data_for_user(cur, uid)
    _seed_weekly_emotion_daily(cur, uid, now_ts, dominant=RECO_TEST_USERS[uid].get("dominant", "Anger"))

    # test_recent
    uid = "test_recent"
    name, role, age, desc = RECO_TEST_USERS[uid]["profile"]
    _upsert_user(cur, uid, name, role, age, desc, now_ts)
    _clear_emotion_data_for_user(cur, uid)
    _seed_recent_emotion_log_only(cur, uid, now_ts, emotion=RECO_TEST_USERS[uid].get("recent_emotion", "Sad"))

    # test_new
    uid = "test_new"
    name, role, age, desc = RECO_TEST_USERS[uid]["profile"]
    _upsert_user(cur, uid, name, role, age, desc, now_ts)
    _clear_emotion_data_for_user(cur, uid)
    _seed_new_user_no_emotion(cur, uid)

    con.commit()
    print("✅ Seeded recommendation test users: test_weekly, test_recent, test_new")


# ------------------------------
# Helpers (lightweight migrations)
# ------------------------------
def _table_exists(cur, name: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None

def _get_columns(cur, table: str) -> set[str]:
    cols = cur.execute(f"PRAGMA table_info({table})").fetchall()
    return {c[1] for c in cols}  # (cid, name, type, notnull, dflt_value, pk)

def _ensure_columns(cur, table: str, columns_sql: list[str]):
    """
    columns_sql: list of strings like 'name TEXT' or 'age INTEGER'
    Adds missing columns via ALTER TABLE.
    """
    existing = _get_columns(cur, table)
    for col_def in columns_sql:
        col_name = col_def.split()[0].strip()
        if col_name not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")

def setup_tables(con):
    cur = con.cursor()

    # ------------------------------
    # USERS
    # ------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        name TEXT,
        role TEXT,
        age INTEGER,
        description TEXT,
        photo TEXT,
        streak INTEGER DEFAULT 0,
        connections INTEGER DEFAULT 0,
        username TEXT UNIQUE,
        preferences_json TEXT,
        created_at REAL,
        updated_at REAL
    )
    """)

    _ensure_columns(cur, "users", [
        "name TEXT",
        "role TEXT",
        "age INTEGER",
        "description TEXT",
        "photo TEXT",
        "streak INTEGER DEFAULT 0",
        "connections INTEGER DEFAULT 0",
        "username TEXT",
        "preferences_json TEXT",
        "created_at REAL",
        "updated_at REAL",
    ])

    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")

    # ------------------------------
    # EMOTIONS
    # ------------------------------
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

    # ------------------------------
    # COMMUNITY
    # ------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS community_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        content TEXT NOT NULL,
        likes INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        date_created REAL
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_date_created ON community_posts(date_created)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_user_id ON community_posts(user_id)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        content TEXT NOT NULL,
        date_created REAL
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_comments_date_created ON comments(date_created)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS post_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        date_created REAL,
        UNIQUE(post_id, user_id)
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_post_likes_post_id ON post_likes(post_id)")

    con.commit()


# ------------------------------
# Seeding
# ------------------------------
NAMES = [
    "Maryam", "Ali", "Zainab", "Hussein", "Noor", "Sara", "Omar", "Hala",
    "Yasmin", "Mustafa", "Rana", "Ahmed"
]
ROLES = ["student", "parent", "teacher", "therapist", "mentor", "member"]

POST_TEMPLATES = [
    "Had a tough day today. Any tips to calm down?",
    "My routine worked well today — feeling proud.",
    "Does anyone know good breathing exercises?",
    "I got overwhelmed in a noisy place. What helps you?",
    "Small win: I completed my tasks and took breaks.",
    "Any advice for staying consistent with habits?"
]

COMMENT_TEMPLATES = [
    "I relate to this. Short walks help me.",
    "Try box breathing for 2 minutes — it’s simple.",
    "You’re not alone. One step at a time.",
    "For noise, earplugs can really help.",
    "Proud of you. Keep the routine gentle and consistent.",
    "Maybe write a short checklist and take breaks."
]

def _random_username(name: str, i: int) -> str:
    suffix = random.randint(10, 999)
    base = name.lower()
    return f"{base}{i}{suffix}"

def seed_dummy_data(con):
    """
    Seeds:
    - Several users
    - 7 days of emotion data for user_001 (and a bit for others)
    - Community posts + comments + likes
    """
    cur = con.cursor()
    now = time.time()

    # Create a primary test user (keeps your existing assumption user_001)
    primary_user_id = "user_001"
    primary_username = "user_001"

    cur.execute("""
    INSERT INTO users (
        user_id, name, role, age, description, photo, streak, connections, username,
        preferences_json, created_at, updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
        updated_at=excluded.updated_at
    """, (
        primary_user_id,
        "Test User",
        "member",
        21,
        "Starter account for testing.",
        "",  # photo url/path later
        random.randint(1, 14),
        random.randint(10, 200),
        primary_username,
        '{"name":"Test User"}',
        now, now
    ))

    # Create additional users
    user_ids = [primary_user_id]
    for i in range(2, 9):  # 7 more users
        name = random.choice(NAMES)
        user_id = f"user_{i:03d}"
        username = _random_username(name, i)
        user_ids.append(user_id)

        cur.execute("""
        INSERT INTO users (
            user_id, name, role, age, description, photo, streak, connections, username,
            preferences_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET updated_at=excluded.updated_at
        """, (
            user_id,
            name,
            random.choice(ROLES),
            random.randint(10, 40),
            "Community member.",
            "",
            random.randint(0, 30),
            random.randint(0, 500),
            username,
            json_preferences(name),
            now, now
        ))

    # ---- Emotion seed (keep your existing behavior, but don't wipe community) ----
    cur.execute("DELETE FROM emotion_daily WHERE user_id = ?", (primary_user_id,))
    cur.execute("DELETE FROM emotion_logs WHERE user_id = ?", (primary_user_id,))

    today = datetime.now().date()

    for i in range(7):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")

        # SAD-HEAVY distribution (you had this already)
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
            """, (primary_user_id, d, emo, cnt, now))

            # Keep emotion_logs reasonably sized (don't spam thousands)
            for _ in range(min(cnt, 12)):
                cur.execute("""
                INSERT INTO emotion_logs (user_id, emotion, confidence, timestamp)
                VALUES (?, ?, ?, ?)
                """, (
                    primary_user_id,
                    emo,
                    round(random.uniform(0.6, 0.99), 2),
                    now - random.randint(0, 60 * 60 * 24 * 7),
                ))

    # Light emotion data for other users (optional)
    for uid in user_ids[1:]:
        # only a couple of days so it doesn't bloat
        for i in range(2):
            d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            emo = random.choice(EMOTIONS)
            cnt = random.randint(2, 10)
            cur.execute("""
            INSERT INTO emotion_daily (user_id, day, emotion, count, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, day, emotion)
            DO UPDATE SET count=excluded.count, updated_at=excluded.updated_at;
            """, (uid, d, emo, cnt, now))

    # ---- Community seed ----
    existing_posts = cur.execute("SELECT COUNT(*) FROM community_posts").fetchone()[0]
    if existing_posts == 0:
        post_ids = []
        for _ in range(12):
            uid = random.choice(user_ids)
            content = random.choice(POST_TEMPLATES)
            created = now - random.randint(0, 60 * 60 * 24 * 14)  # last 2 weeks

            cur.execute("""
            INSERT INTO community_posts (user_id, content, likes, comments, date_created)
            VALUES (?, ?, 0, 0, ?)
            """, (uid, content, created))

            post_id = cur.lastrowid
            post_ids.append(post_id)

        # Add comments + likes and keep cached counters consistent
        for post_id in post_ids:
            n_comments = random.randint(0, 6)
            commenters = random.sample(user_ids, k=min(len(user_ids), max(1, random.randint(1, 4))))
            for i in range(n_comments):
                uid = random.choice(commenters)
                content = random.choice(COMMENT_TEMPLATES)
                created = now - random.randint(0, 60 * 60 * 24 * 14)

                cur.execute("""
                INSERT INTO comments (post_id, user_id, content, date_created)
                VALUES (?, ?, ?, ?)
                """, (post_id, uid, content, created))

            n_likes = random.randint(0, 8)
            likers = random.sample(user_ids, k=min(len(user_ids), n_likes))
            for uid in likers:
                created = now - random.randint(0, 60 * 60 * 24 * 14)
                cur.execute("""
                INSERT OR IGNORE INTO post_likes (post_id, user_id, date_created)
                VALUES (?, ?, ?)
                """, (post_id, uid, created))

            like_count = cur.execute("SELECT COUNT(*) FROM post_likes WHERE post_id = ?", (post_id,)).fetchone()[0]
            comment_count = cur.execute("SELECT COUNT(*) FROM comments WHERE post_id = ?", (post_id,)).fetchone()[0]
            cur.execute("""
            UPDATE community_posts
            SET likes = ?, comments = ?
            WHERE id = ?
            """, (like_count, comment_count, post_id))

    con.commit()
    print("✅ Seeded users, emotions, and community data.")


def json_preferences(name: str) -> str:
    return f'{{"name":"{name}","language":"en","notifications":true}}'


def main():
    print(f"Initializing database at: {os.path.abspath(DB_PATH)}")
    con = sqlite3.connect(DB_PATH)

    setup_tables(con)
    seed_dummy_data(con)

    # ---- TEMP: seed recommendation test users (comment out anytime) ----
    if ENABLE_RECO_TEST_SEEDS:
        seed_reco_test_users(con)

    con.close()
    print("✅ Database ready.")


if __name__ == "__main__":
    main()


