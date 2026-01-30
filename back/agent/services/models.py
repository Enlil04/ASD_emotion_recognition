from __future__ import annotations

from sqlalchemy import Column, Integer, String, Float, Text, UniqueConstraint, Index
from setup_db import Base

# ------------------------------
# USERS
# ------------------------------
class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=True)
    role = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    photo = Column(Text, nullable=True)
    streak = Column(Integer, default=0)
    connections = Column(Integer, default=0)
    username = Column(String, unique=True, index=True, nullable=True)

    preferences_json = Column(Text, nullable=True)
    created_at = Column(Float, nullable=True)
    updated_at = Column(Float, nullable=True)


# ------------------------------
# EMOTIONS
# ------------------------------
class MoodSession(Base):
    __tablename__ = "emotion_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    emotion = Column(String, index=True)
    confidence = Column(Float)
    timestamp = Column(Float, index=True)


class DailySummary(Base):
    __tablename__ = "emotion_daily"
    __table_args__ = (
        UniqueConstraint("user_id", "day", "emotion", name="uq_emotion_daily_user_day_emotion"),
        Index("idx_emotion_daily_user_day", "user_id", "day"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    day = Column(String, index=True)  # YYYY-MM-DD
    emotion = Column(String, index=True)
    count = Column(Integer, default=0)
    updated_at = Column(Float, nullable=True)


# ------------------------------
# COMMUNITY
# ------------------------------
class CommunityPost(Base):
    __tablename__ = "community_posts"
    __table_args__ = (
        Index("idx_posts_date_created", "date_created"),
        Index("idx_posts_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    date_created = Column(Float, index=True, nullable=True)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        Index("idx_comments_post_id", "post_id"),
        Index("idx_comments_date_created", "date_created"),
    )

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    date_created = Column(Float, index=True, nullable=True)


class PostLike(Base):
    __tablename__ = "post_likes"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_likes_post_user"),
        Index("idx_post_likes_post_id", "post_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    date_created = Column(Float, index=True, nullable=True)


# from sqlalchemy import Column, Integer, String, Float
# from setup_db import Base

# class MoodSession(Base):
#     __tablename__ = "emotion_logs"
#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(String)
#     emotion = Column(String, index=True)
#     confidence = Column(Float)
#     timestamp = Column(Float)

# class DailySummary(Base):
#     __tablename__ = "emotion_daily"
#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(String)
#     day = Column(String) # "2024-05-20"
#     emotion = Column(String)
#     emotion_counts = Column(Integer)