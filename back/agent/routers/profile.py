from fastapi import APIRouter, Query
import sqlite3
from setup_db import DB_PATH

# ✅ Fix: No prefix here, because main.py handles "/api/profile"
router = APIRouter(tags=["profile"])


# ==============================
# HELPERS
# ==============================

def _connect_db_row() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _activity_item(ts: float, kind: str, title: str, subtitle: str = "", meta: dict | None = None) -> dict:
    return {
        "timestamp": float(ts),
        "type": kind,              # e.g. "emotion", "post", "comment", "like"
        "title": title,            # UI title
        "subtitle": subtitle,      # UI subtitle
        "meta": meta or {},        # optional extra fields
    }


# ==============================
# ENDPOINTS
# ==============================

@router.get("/activity")  # ✅ Result URL: /api/profile/activity
async def profile_activity(
    user_id: str = "user_001",
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    """
    Recent activity feed for Profile screen.
    Merges emotions, posts, comments, and likes.
    """
    con = _connect_db_row()
    try:
        cur = con.cursor()
        items: list[dict] = []

        # 1) Emotion check-ins
        emo_rows = cur.execute(
            "SELECT emotion, confidence, timestamp FROM emotion_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50",
            (user_id,),
        ).fetchall()

        for r in emo_rows:
            items.append(_activity_item(
                ts=float(r["timestamp"] or 0.0),
                kind="emotion",
                title=f"Emotion check-in: {r['emotion'] or 'Neutral'}",
                subtitle=f"Confidence: {float(r['confidence'] or 0):.0f}%",
                meta={"emotion": r["emotion"], "confidence": r["confidence"]},
            ))

        # 2) Community posts
        post_rows = cur.execute(
            "SELECT id, content, date_created FROM community_posts WHERE user_id = ? AND COALESCE(is_deleted, 0) = 0 ORDER BY date_created DESC LIMIT 50",
            (user_id,),
        ).fetchall()

        for r in post_rows:
            content = (r["content"] or "").strip()
            preview = content[:60] + ("…" if len(content) > 60 else "")
            items.append(_activity_item(
                ts=float(r["date_created"] or 0.0),
                kind="post",
                title="Posted in Community",
                subtitle=preview,
                meta={"post_id": int(r["id"])},
            ))

        # 3) Comments
        comment_rows = cur.execute(
            "SELECT id, post_id, content, date_created FROM comments WHERE user_id = ? ORDER BY date_created DESC LIMIT 50",
            (user_id,),
        ).fetchall()

        for r in comment_rows:
            content = (r["content"] or "").strip()
            preview = content[:60] + ("…" if len(content) > 60 else "")
            items.append(_activity_item(
                ts=float(r["date_created"] or 0.0),
                kind="comment",
                title="Commented on a post",
                subtitle=preview,
                meta={"comment_id": int(r["id"]), "post_id": int(r["post_id"])},
            ))

        # 4) Likes
        like_rows = cur.execute(
            "SELECT post_id, date_created FROM post_likes WHERE user_id = ? ORDER BY date_created DESC LIMIT 50",
            (user_id,),
        ).fetchall()

        for r in like_rows:
            items.append(_activity_item(
                ts=float(r["date_created"] or 0.0),
                kind="like",
                title="Liked a post",
                subtitle="",
                meta={"post_id": int(r["post_id"])},
            ))

        # Merge & Sort
        items.sort(key=lambda x: x["timestamp"], reverse=True)
        sliced = items[offset: offset + limit]

        return {"user_id": user_id, "limit": limit, "offset": offset, "items": sliced}
    finally:
        con.close()


@router.get("/stats")  # ✅ Result URL: /api/profile/stats
async def profile_stats(user_id: str = "user_001"):
    """
    Profile stats header data.
    """
    con = _connect_db_row()
    try:
        cur = con.cursor()
        
        # User Streaks/Connections
        u = cur.execute("SELECT streak, connections FROM users WHERE user_id = ?", (user_id,)).fetchone()
        streak = int((u["streak"] if u else 0) or 0)
        connections = int((u["connections"] if u else 0) or 0)

        # Counters
        emo_count = cur.execute("SELECT COUNT(*) as c FROM emotion_logs WHERE user_id = ?", (user_id,)).fetchone()["c"]
        post_count = cur.execute("SELECT COUNT(*) as c FROM community_posts WHERE user_id = ? AND COALESCE(is_deleted,0)=0", (user_id,)).fetchone()["c"]
        comment_count = cur.execute("SELECT COUNT(*) as c FROM comments WHERE user_id = ?", (user_id,)).fetchone()["c"]
        like_count = cur.execute("SELECT COUNT(*) as c FROM post_likes WHERE user_id = ?", (user_id,)).fetchone()["c"]

        activities = int(emo_count or 0) + int(post_count or 0) + int(comment_count or 0) + int(like_count or 0)

        return {
            "user_id": user_id,
            "streak": streak,
            "connections": connections,
            "activities": activities,
            "breakdown": {
                "emotion_logs": int(emo_count or 0),
                "posts": int(post_count or 0),
                "comments": int(comment_count or 0),
                "likes": int(like_count or 0),
            }
        }
    finally:
        con.close()





# from fastapi import APIRouter, Query
# import sqlite3
# from setup_db import DB_PATH


# router = APIRouter(prefix="/profile", tags=["profile"])


# # ==============================
# # PROFILE ACTIVITY + STATS (new)
# # ==============================

# def _connect_db_row() -> sqlite3.Connection:
#     con = sqlite3.connect(DB_PATH)
#     con.row_factory = sqlite3.Row
#     return con


# def _activity_item(ts: float, kind: str, title: str, subtitle: str = "", meta: dict | None = None) -> dict:
#     return {
#         "timestamp": float(ts),
#         "type": kind,              # e.g. "emotion", "post", "comment", "like"
#         "title": title,            # UI title
#         "subtitle": subtitle,      # UI subtitle
#         "meta": meta or {},        # optional extra fields
#     }


# @router.get("/api/profile/activity")
# async def profile_activity(
#     user_id: str = "user_001",
#     limit: int = Query(10, ge=1, le=50),
#     offset: int = Query(0, ge=0),
# ):
#     """
#     Recent activity feed for Profile screen.
#     Merges:
#       - emotion logs (emotion_logs)
#       - community posts (community_posts)
#       - comments (comments)
#       - likes (post_likes)
#     Returns newest-first, paged via limit/offset.
#     """
#     con = _connect_db_row()
#     try:
#         cur = con.cursor()

#         items: list[dict] = []

#         # 1) Emotion check-ins
#         emo_rows = cur.execute(
#             """
#             SELECT emotion, confidence, timestamp
#             FROM emotion_logs
#             WHERE user_id = ?
#             ORDER BY timestamp DESC
#             LIMIT 50
#             """,
#             (user_id,),
#         ).fetchall()

#         for r in emo_rows:
#             emotion = (r["emotion"] or "Neutral")
#             conf = float(r["confidence"] or 0.0)
#             ts = float(r["timestamp"] or 0.0)
#             items.append(_activity_item(
#                 ts=ts,
#                 kind="emotion",
#                 title=f"Emotion check-in: {emotion}",
#                 subtitle=f"Confidence: {conf:.0f}%",
#                 meta={"emotion": emotion, "confidence": conf},
#             ))

#         # 2) Community posts by this user
#         post_rows = cur.execute(
#             """
#             SELECT id, content, date_created
#             FROM community_posts
#             WHERE user_id = ? AND COALESCE(is_deleted, 0) = 0
#             ORDER BY date_created DESC
#             LIMIT 50
#             """,
#             (user_id,),
#         ).fetchall()

#         for r in post_rows:
#             ts = float(r["date_created"] or 0.0)
#             content = (r["content"] or "").strip()
#             preview = content[:60] + ("…" if len(content) > 60 else "")
#             items.append(_activity_item(
#                 ts=ts,
#                 kind="post",
#                 title="Posted in Community",
#                 subtitle=preview,
#                 meta={"post_id": int(r["id"])},
#             ))

#         # 3) Comments by this user
#         comment_rows = cur.execute(
#             """
#             SELECT id, post_id, content, date_created
#             FROM comments
#             WHERE user_id = ?
#             ORDER BY date_created DESC
#             LIMIT 50
#             """,
#             (user_id,),
#         ).fetchall()

#         for r in comment_rows:
#             ts = float(r["date_created"] or 0.0)
#             content = (r["content"] or "").strip()
#             preview = content[:60] + ("…" if len(content) > 60 else "")
#             items.append(_activity_item(
#                 ts=ts,
#                 kind="comment",
#                 title="Commented on a post",
#                 subtitle=preview,
#                 meta={"comment_id": int(r["id"]), "post_id": int(r["post_id"])},
#             ))

#         # 4) Likes by this user
#         like_rows = cur.execute(
#             """
#             SELECT post_id, date_created
#             FROM post_likes
#             WHERE user_id = ?
#             ORDER BY date_created DESC
#             LIMIT 50
#             """,
#             (user_id,),
#         ).fetchall()

#         for r in like_rows:
#             ts = float(r["date_created"] or 0.0)
#             items.append(_activity_item(
#                 ts=ts,
#                 kind="like",
#                 title="Liked a post",
#                 subtitle="",
#                 meta={"post_id": int(r["post_id"])},
#             ))

#         # Merge + sort newest first
#         items.sort(key=lambda x: x["timestamp"], reverse=True)

#         # Apply paging after merge
#         sliced = items[offset: offset + limit]

#         return {
#             "user_id": user_id,
#             "limit": limit,
#             "offset": offset,
#             "items": sliced,
#         }
#     finally:
#         con.close()


# @router.get("/api/profile/stats")
# async def profile_stats(user_id: str = "user_001"):
#     """
#     Profile stats including total 'activities' count (for the Profile stats row).
#     Pulls streak/connections from users table if present.
#     """
#     con = _connect_db_row()
#     try:
#         cur = con.cursor()

#         # user fields
#         u = cur.execute(
#             """
#             SELECT streak, connections
#             FROM users
#             WHERE user_id = ?
#             """,
#             (user_id,),
#         ).fetchone()

#         streak = int((u["streak"] if u else 0) or 0)
#         connections = int((u["connections"] if u else 0) or 0)

#         # activity counts
#         emo_count = cur.execute(
#             "SELECT COUNT(*) as c FROM emotion_logs WHERE user_id = ?",
#             (user_id,),
#         ).fetchone()["c"]

#         post_count = cur.execute(
#             "SELECT COUNT(*) as c FROM community_posts WHERE user_id = ? AND COALESCE(is_deleted,0)=0",
#             (user_id,),
#         ).fetchone()["c"]

#         comment_count = cur.execute(
#             "SELECT COUNT(*) as c FROM comments WHERE user_id = ?",
#             (user_id,),
#         ).fetchone()["c"]

#         like_count = cur.execute(
#             "SELECT COUNT(*) as c FROM post_likes WHERE user_id = ?",
#             (user_id,),
#         ).fetchone()["c"]

#         activities = int(emo_count or 0) + int(post_count or 0) + int(comment_count or 0) + int(like_count or 0)

#         return {
#             "user_id": user_id,
#             "streak": streak,
#             "connections": connections,
#             "activities": activities,
#             "breakdown": {
#                 "emotion_logs": int(emo_count or 0),
#                 "posts": int(post_count or 0),
#                 "comments": int(comment_count or 0),
#                 "likes": int(like_count or 0),
#             }
#         }
#     finally:
#         con.close()
# #-------------------------------------------------------------------------
