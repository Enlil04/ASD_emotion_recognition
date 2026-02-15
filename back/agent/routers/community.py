from typing import Optional
from pydantic import BaseModel
from fastapi import HTTPException, Query
import time
import sqlite3


from koog_orchestrator import DB_PATH
from fastapi import APIRouter

# from guardian import _connect_db_row
def _connect_db_row() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


router = APIRouter(tags=["community"])


# --- Pydantic Schemas ---
class CreatePostRequest(BaseModel):
    user_id: str
    content: str

class CreateCommentRequest(BaseModel):
    user_id: str
    content: str

class LikeRequest(BaseModel):
    user_id: str

class ReportRequest(BaseModel):
    reporter_user_id: str
    reason: str


def _ensure_community_schema():
    """
    Light migrations so server doesn't crash if DB was created before you added new tables/cols.
    Safe to run on startup.
    """
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()

        # community_reports (for /report endpoint)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS community_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            reporter_user_id TEXT NOT NULL,
            reason TEXT,
            date_created REAL
        )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_post_id ON community_reports(post_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_date_created ON community_reports(date_created)")

        # soft delete support on community_posts
        cols = {c[1] for c in cur.execute("PRAGMA table_info(community_posts)").fetchall()}
        if "is_deleted" not in cols:
            cur.execute("ALTER TABLE community_posts ADD COLUMN is_deleted INTEGER DEFAULT 0")

        con.commit()
    except Exception as e:
        print(f"❌ Community schema ensure failed: {e}")
    finally:
        con.close()


# --------------------------------------------------------------------
# (1) GET /api/community/posts  - Feed (paged)
# --------------------------------------------------------------------

# Ensure schema on startup
@router.on_event("startup")
def _startup_community_schema():
    _ensure_community_schema()


@router.get("/api/community/posts")
async def list_community_posts(
    user_id: Optional[str] = None,  # optional: compute liked_by_me
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Returns the latest community posts with author info (and liked_by_me if user_id is provided)."""
    con = _connect_db_row()
    try:
        cur = con.cursor()

        rows = cur.execute(
            """
            SELECT
                p.id as post_id,
                p.content,
                p.likes,
                p.comments,
                p.date_created,
                COALESCE(p.is_deleted, 0) as is_deleted,
                u.user_id,
                u.name,
                u.username,
                u.role,
                u.age,
                u.description,
                u.photo,
                u.streak,
                u.connections
            FROM community_posts p
            LEFT JOIN users u ON u.user_id = p.user_id
            WHERE COALESCE(p.is_deleted, 0) = 0
            ORDER BY p.date_created DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

        posts = []
        for r in rows:
            liked_by_me = False
            if user_id:
                liked_by_me = cur.execute(
                    "SELECT 1 FROM post_likes WHERE post_id = ? AND user_id = ?",
                    (r["post_id"], user_id),
                ).fetchone() is not None

            posts.append({
                "id": r["post_id"],
                "content": r["content"],
                "likes": int(r["likes"] or 0),
                "comments": int(r["comments"] or 0),
                "date_created": r["date_created"],
                "liked_by_me": liked_by_me,
                "author": _dict_user_public(r),
            })

        return {"items": posts, "limit": limit, "offset": offset}
    finally:
        con.close()


# --------------------------------------------------------------------
# (2) POST /api/community/posts  - Create a post
# --------------------------------------------------------------------
@router.post("/api/community/posts")
async def create_community_post(req: CreatePostRequest):
    """Creates a new post for a user."""
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="content is required")

    con = _connect_db_row()
    now = time.time()
    try:
        cur = con.cursor()

        # verify user exists
        u = cur.execute("SELECT user_id FROM users WHERE user_id = ?", (req.user_id,)).fetchone()
        if u is None:
            raise HTTPException(status_code=404, detail="user not found")

        cur.execute(
            """
            INSERT INTO community_posts (user_id, content, likes, comments, date_created, is_deleted)
            VALUES (?, ?, 0, 0, ?, 0)
            """,
            (req.user_id, req.content, now),
        )
        post_id = cur.lastrowid
        con.commit()

        # return the created post (with author info)
        row = cur.execute(
            """
            SELECT p.id as post_id, p.content, p.likes, p.comments, p.date_created,
                   u.user_id, u.name, u.username, u.role, u.age, u.description, u.photo, u.streak, u.connections
            FROM community_posts p
            LEFT JOIN users u ON u.user_id = p.user_id
            WHERE p.id = ?
            """,
            (post_id,),
        ).fetchone()

        return {
            "id": row["post_id"],
            "content": row["content"],
            "likes": int(row["likes"] or 0),
            "comments": int(row["comments"] or 0),
            "date_created": row["date_created"],
            "liked_by_me": False,
            "author": _dict_user_public(row),
        }
    finally:
        con.close()


# --------------------------------------------------------------------
# (3) GET /api/community/posts/{post_id}  - Post detail
# --------------------------------------------------------------------
@router.get("/api/community/posts/{post_id}")
async def get_community_post(post_id: int, user_id: Optional[str] = None):
    """Returns a single post (with author info). Optionally includes liked_by_me when user_id is provided."""
    con = _connect_db_row()
    try:
        cur = con.cursor()
        r = cur.execute(
            """
            SELECT
                p.id as post_id, p.content, p.likes, p.comments, p.date_created,
                COALESCE(p.is_deleted, 0) as is_deleted,
                u.user_id, u.name, u.username, u.role, u.age, u.description, u.photo, u.streak, u.connections
            FROM community_posts p
            LEFT JOIN users u ON u.user_id = p.user_id
            WHERE p.id = ?
            """,
            (post_id,),
        ).fetchone()

        if r is None or int(r["is_deleted"] or 0) == 1:
            raise HTTPException(status_code=404, detail="post not found")

        liked_by_me = False
        if user_id:
            liked_by_me = cur.execute(
                "SELECT 1 FROM post_likes WHERE post_id = ? AND user_id = ?",
                (post_id, user_id),
            ).fetchone() is not None

        return {
            "id": r["post_id"],
            "content": r["content"],
            "likes": int(r["likes"] or 0),
            "comments": int(r["comments"] or 0),
            "date_created": r["date_created"],
            "liked_by_me": liked_by_me,
            "author": _dict_user_public(r),
        }
    finally:
        con.close()


# --------------------------------------------------------------------
# (4) GET /api/community/posts/{post_id}/comments  - List comments
# --------------------------------------------------------------------
@router.get("/api/community/posts/{post_id}/comments")
async def list_post_comments(
    post_id: int,
    limit: int = Query(30, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Returns comments for a post (paged) with author info."""
    con = _connect_db_row()
    try:
        cur = con.cursor()

        # ensure post exists (and not deleted)
        p = cur.execute(
            "SELECT id, COALESCE(is_deleted,0) as is_deleted FROM community_posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if p is None or int(p["is_deleted"] or 0) == 1:
            raise HTTPException(status_code=404, detail="post not found")

        rows = cur.execute(
            """
            SELECT
                c.id as comment_id,
                c.post_id,
                c.content,
                c.date_created,
                u.user_id, u.name, u.username, u.role, u.age, u.description, u.photo, u.streak, u.connections
            FROM comments c
            LEFT JOIN users u ON u.user_id = c.user_id
            WHERE c.post_id = ?
            ORDER BY c.date_created ASC
            LIMIT ? OFFSET ?
            """,
            (post_id, limit, offset),
        ).fetchall()

        items = []
        for r in rows:
            items.append({
                "id": r["comment_id"],
                "post_id": r["post_id"],
                "content": r["content"],
                "date_created": r["date_created"],
                "author": _dict_user_public(r),
            })

        return {"items": items, "limit": limit, "offset": offset}
    finally:
        con.close()


# --------------------------------------------------------------------
# (5) POST /api/community/posts/{post_id}/comments  - Add comment
# --------------------------------------------------------------------
@router.post("/api/community/posts/{post_id}/comments")
async def add_post_comment(post_id: int, req: CreateCommentRequest):
    """Adds a comment to a post and updates the cached comments count on the post."""
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="content is required")

    con = _connect_db_row()
    now = time.time()
    try:
        cur = con.cursor()

        # ensure post exists and not deleted
        p = cur.execute(
            "SELECT id, COALESCE(is_deleted,0) as is_deleted FROM community_posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if p is None or int(p["is_deleted"] or 0) == 1:
            raise HTTPException(status_code=404, detail="post not found")

        # ensure user exists
        u = cur.execute("SELECT user_id FROM users WHERE user_id = ?", (req.user_id,)).fetchone()
        if u is None:
            raise HTTPException(status_code=404, detail="user not found")

        cur.execute(
            """
            INSERT INTO comments (post_id, user_id, content, date_created)
            VALUES (?, ?, ?, ?)
            """,
            (post_id, req.user_id, req.content, now),
        )

        # update cached counter
        comment_count = cur.execute(
            "SELECT COUNT(*) FROM comments WHERE post_id = ?",
            (post_id,),
        ).fetchone()[0]
        cur.execute("UPDATE community_posts SET comments = ? WHERE id = ?", (comment_count, post_id))

        con.commit()
        return {"ok": True, "post_id": post_id, "comments": int(comment_count)}
    finally:
        con.close()


# --------------------------------------------------------------------
# (6) POST /api/community/posts/{post_id}/like  - Like post (idempotent)
# --------------------------------------------------------------------
@router.post("/api/community/posts/{post_id}/like")
async def like_post(post_id: int, req: LikeRequest):
    """Likes a post (idempotent). Uses post_likes UNIQUE(post_id,user_id) to prevent duplicates."""
    con = _connect_db_row()
    now = time.time()
    try:
        cur = con.cursor()

        # ensure post exists and not deleted
        p = cur.execute(
            "SELECT id, COALESCE(is_deleted,0) as is_deleted FROM community_posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if p is None or int(p["is_deleted"] or 0) == 1:
            raise HTTPException(status_code=404, detail="post not found")

        # ensure user exists
        u = cur.execute("SELECT user_id FROM users WHERE user_id = ?", (req.user_id,)).fetchone()
        if u is None:
            raise HTTPException(status_code=404, detail="user not found")

        cur.execute(
            "INSERT OR IGNORE INTO post_likes (post_id, user_id, date_created) VALUES (?, ?, ?)",
            (post_id, req.user_id, now),
        )

        like_count = cur.execute(
            "SELECT COUNT(*) FROM post_likes WHERE post_id = ?",
            (post_id,),
        ).fetchone()[0]
        cur.execute("UPDATE community_posts SET likes = ? WHERE id = ?", (like_count, post_id))

        con.commit()
        return {"ok": True, "post_id": post_id, "likes": int(like_count)}
    finally:
        con.close()


# --------------------------------------------------------------------
# (7) POST /api/community/posts/{post_id}/unlike  - Unlike post
# --------------------------------------------------------------------
@router.post("/api/community/posts/{post_id}/unlike")
async def unlike_post(post_id: int, req: LikeRequest):
    """Removes a like from a post and updates the cached likes count."""
    con = _connect_db_row()
    try:
        cur = con.cursor()

        # ensure post exists and not deleted
        p = cur.execute(
            "SELECT id, COALESCE(is_deleted,0) as is_deleted FROM community_posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if p is None or int(p["is_deleted"] or 0) == 1:
            raise HTTPException(status_code=404, detail="post not found")

        cur.execute("DELETE FROM post_likes WHERE post_id = ? AND user_id = ?", (post_id, req.user_id))

        like_count = cur.execute(
            "SELECT COUNT(*) FROM post_likes WHERE post_id = ?",
            (post_id,),
        ).fetchone()[0]
        cur.execute("UPDATE community_posts SET likes = ? WHERE id = ?", (like_count, post_id))

        con.commit()
        return {"ok": True, "post_id": post_id, "likes": int(like_count)}
    finally:
        con.close()


# --------------------------------------------------------------------
# (8) GET /api/users/{user_id}  - Public user profile
# --------------------------------------------------------------------
@router.get("/api/users/{user_id}")
async def get_user_profile(user_id: str):
    """Returns public profile fields for a user (used by community author/profile UI)."""
    con = _connect_db_row()
    try:
        cur = con.cursor()
        r = cur.execute(
            """
            SELECT user_id, name, username, role, age, description, photo, streak, connections
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        if r is None:
            raise HTTPException(status_code=404, detail="user not found")
        return _dict_user_public(r)
    finally:
        con.close()


# --------------------------------------------------------------------
# (9) POST /api/community/posts/{post_id}/report  - Report a post
# --------------------------------------------------------------------
@router.post("/api/community/posts/{post_id}/report")
async def report_post(post_id: int, req: ReportRequest):
    """Creates a report record for moderation review."""
    con = _connect_db_row()
    now = time.time()
    try:
        cur = con.cursor()

        # ensure post exists and not deleted
        p = cur.execute(
            "SELECT id, COALESCE(is_deleted,0) as is_deleted FROM community_posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if p is None or int(p["is_deleted"] or 0) == 1:
            raise HTTPException(status_code=404, detail="post not found")

        # ensure reporter exists
        u = cur.execute("SELECT user_id FROM users WHERE user_id = ?", (req.reporter_user_id,)).fetchone()
        if u is None:
            raise HTTPException(status_code=404, detail="reporter user not found")

        cur.execute(
            """
            INSERT INTO community_reports (post_id, reporter_user_id, reason, date_created)
            VALUES (?, ?, ?, ?)
            """,
            (post_id, req.reporter_user_id, req.reason, now),
        )
        con.commit()
        return {"ok": True, "post_id": post_id}
    finally:
        con.close()


# --------------------------------------------------------------------
# (10) DELETE /api/community/posts/{post_id}  - Delete (soft delete)
# --------------------------------------------------------------------
@router.delete("/api/community/posts/{post_id}")
async def delete_post(post_id: int, requester_user_id: str):
    """
    Soft-deletes a post.
    Allowed if requester is:
    - the author of the post, OR
    - a user with role 'admin' or 'moderator'
    """
    con = _connect_db_row()
    try:
        cur = con.cursor()

        post = cur.execute(
            "SELECT id, user_id, COALESCE(is_deleted,0) as is_deleted FROM community_posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if post is None or int(post["is_deleted"] or 0) == 1:
            raise HTTPException(status_code=404, detail="post not found")

        requester = cur.execute(
            "SELECT user_id, role FROM users WHERE user_id = ?",
            (requester_user_id,),
        ).fetchone()
        if requester is None:
            raise HTTPException(status_code=404, detail="requester user not found")

        is_author = requester_user_id == post["user_id"]
        role = (requester["role"] or "").lower()
        is_admin = role in ("admin", "moderator")

        if not (is_author or is_admin):
            raise HTTPException(status_code=403, detail="not allowed")

        cur.execute("UPDATE community_posts SET is_deleted = 1 WHERE id = ?", (post_id,))
        con.commit()
        return {"ok": True, "post_id": post_id}
    finally:
        con.close()



def _dict_user_public(row: sqlite3.Row) -> dict:
    """Return only the public fields your community UI needs."""
    # sqlite3.Row supports dict-style access; .get is not guaranteed, so use safe indexing
    def safe(key, default=None):
        try:
            return row[key]
        except Exception:
            return default

    return {
        "user_id": safe("user_id"),
        "name": safe("name"),
        "username": safe("username"),
        "role": safe("role"),
        "age": safe("age"),
        "description": safe("description"),
        "photo": safe("photo"),
        "streak": safe("streak", 0),
        "connections": safe("connections", 0),
    }
