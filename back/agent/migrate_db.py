import os
import sqlite3

DB_PATH = os.path.join("data", "memory.db")

def _table_exists(cur, table: str) -> bool:
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None

def _cols(cur, table: str) -> set[str]:
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}

def _add_col(cur, table: str, col_sql: str):
    name = col_sql.split()[0]
    if name not in _cols(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_sql}")
        print(f"➕ Added {table}.{name}")

def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ DB not found at {DB_PATH}")
        return

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # -------------------------
    # emotion_daily fixes
    # -------------------------
    if _table_exists(cur, "emotion_daily"):
        cols = _cols(cur, "emotion_daily")

        # rename emotion_counts -> count (if old partner version)
        if "emotion_counts" in cols and "count" not in cols:
            cur.execute("ALTER TABLE emotion_daily RENAME COLUMN emotion_counts TO count")
            print("🔁 Renamed emotion_daily.emotion_counts -> count")

        # ensure columns exist (non-destructive)
        _add_col(cur, "emotion_daily", "updated_at REAL")
        _add_col(cur, "emotion_daily", "id INTEGER")  # if old table had no id

        # enforce uniqueness via unique index (safe)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_emotion_daily_user_day_emotion
            ON emotion_daily(user_id, day, emotion)
        """)
        print("✅ Ensured unique index on emotion_daily(user_id, day, emotion)")

    # -------------------------
    # community_posts fixes
    # -------------------------
    if _table_exists(cur, "community_posts"):
        _add_col(cur, "community_posts", "is_deleted INTEGER DEFAULT 0")

    # -------------------------
    # post_likes uniqueness (safe)
    # -------------------------
    if _table_exists(cur, "post_likes"):
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_post_likes_post_user
            ON post_likes(post_id, user_id)
        """)
        print("✅ Ensured unique index on post_likes(post_id, user_id)")

    con.commit()
    con.close()
    print("✅ Migration completed (no data wiped).")

if __name__ == "__main__":
    main()
