<<<<<<< HEAD
from __future__ import annotations

from sqlalchemy import Column, Integer, String, Float, Text, UniqueConstraint, Index
from setup_db import Base

<<<<<<< HEAD
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
=======
# 1. EMOTION LOGS
>>>>>>> 41b5596b9655c069b2c6e86136950a535324208a
class MoodSession(Base):
    __tablename__ = "emotion_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    emotion = Column(String, index=True)
    confidence = Column(Float)
<<<<<<< HEAD
    timestamp = Column(Float, index=True)

=======
    timestamp = Column(Float)  # ✅ CHANGED from 'ts' to 'timestamp'
>>>>>>> 41b5596b9655c069b2c6e86136950a535324208a

# 2. DAILY SUMMARY
class DailySummary(Base):
    __tablename__ = "emotion_daily"
    __table_args__ = (
        UniqueConstraint("user_id", "day", "emotion", name="uq_emotion_daily_user_day_emotion"),
        Index("idx_emotion_daily_user_day", "user_id", "day"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
<<<<<<< HEAD
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
=======
    day = Column(String) 
    emotion = Column(String)
    emotion_counts = Column(Integer, default=0)
    updated_at = Column(Float)

# 3. USERS
=======
# from sqlalchemy import Column, Integer, String, Float
# from setup_db import Base

# # 1. EMOTION LOGS
# class MoodSession(Base):
#     __tablename__ = "emotion_logs"
#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(String, index=True)
#     emotion = Column(String, index=True)
#     confidence = Column(Float)
#     timestamp = Column(Float)  # ✅ CHANGED from 'ts' to 'timestamp'

# # 2. DAILY SUMMARY
# class DailySummary(Base):
#     __tablename__ = "emotion_daily"
#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(String, index=True)
#     day = Column(String) 
#     emotion = Column(String)
#     emotion_counts = Column(Integer, default=0)
#     updated_at = Column(Float)

# # 3. USERS
# class User(Base):
#     __tablename__ = "users"
#     user_id = Column(String, primary_key=True, index=True)
#     username = Column(String, unique=True, index=True)
#     name = Column(String)
#     role = Column(String)
#     age = Column(Integer)
#     photo_url = Column(String)
#     description = Column(String)
#     connections = Column(Integer, default=0)
#     streak = Column(Integer, default=0)
#     preferences_json = Column(String)
#     created_at = Column(Float)
#     updated_at = Column(Float)

# # 4. COMMUNITY POSTS
# class CommunityPost(Base):
#     __tablename__ = "community_posts"
#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(String, index=True)
#     content = Column(String)
#     likes = Column(Integer, default=0)
#     comments = Column(Integer, default=0)
#     date_created = Column(Float)

# # 5. COMMENTS
# class Comment(Base):
#     __tablename__ = "comments"
#     id = Column(Integer, primary_key=True, index=True)
#     post_id = Column(Integer, index=True)
#     user_id = Column(String)
#     content = Column(String)
#     date_created = Column(Float)

# # 6. INTERACTIONS
# class Interaction(Base):
#     __tablename__ = "interactions"
#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(String, index=True)
    
#     # Standard AI Memory Columns
#     role = Column(String)      
#     content = Column(String)   
#     timestamp = Column(Float)  # ✅ CHANGED from 'ts' to 'timestamp'
    
#     # Optional metadata
#     readable_time = Column(String, nullable=True)
#     event_type = Column(String, nullable=True)
from sqlalchemy import Column, Integer, String, Float
from setup_db import Base

# 1. USERS
>>>>>>> f097ba3bf547ebcc72d0f8aefc910dda298d2118
class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    name = Column(String)
    role = Column(String)
    age = Column(Integer)
    photo = Column(String)  # ✅ CHANGED from photo_url to photo
    description = Column(String)
    connections = Column(Integer, default=0)
    streak = Column(Integer, default=0)
    preferences_json = Column(String)
    created_at = Column(Float)
    updated_at = Column(Float)

# 2. COMMUNITY POSTS
class CommunityPost(Base):
    __tablename__ = "community_posts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    content = Column(String)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    date_created = Column(Float)
    is_deleted = Column(Integer, default=0)

# 3. COMMENTS
class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, index=True)
    user_id = Column(String)
    content = Column(String)
    date_created = Column(Float)

# 4. POST LIKES
class PostLike(Base):
    __tablename__ = "post_likes"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, index=True)
    user_id = Column(String, index=True)
    date_created = Column(Float)

# 5. COMMUNITY REPORTS
class CommunityReport(Base):
    __tablename__ = "community_reports"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, index=True)
    reporter_user_id = Column(String)
    reason = Column(String)
    date_created = Column(Float)

# 6. INTERACTIONS
class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
<<<<<<< HEAD
    
    # Standard AI Memory Columns
    role = Column(String)      
    content = Column(String)   
    timestamp = Column(Float)  # ✅ CHANGED from 'ts' to 'timestamp'
    
    # Optional metadata
    readable_time = Column(String, nullable=True)
    event_type = Column(String, nullable=True)
>>>>>>> 41b5596b9655c069b2c6e86136950a535324208a
=======
    timestamp = Column(Float)
    readable_time = Column(String)
    event_type = Column(String)
    user_input = Column(String)      
    agent_response = Column(String)  
    detected_emotion = Column(String)
    confidence = Column(Float)

# 7. DAILY EMOTION SUMMARY
class DailySummary(Base):
    __tablename__ = "emotion_daily"
    user_id = Column(String, primary_key=True)
    date_str = Column(String, primary_key=True)
    emotion_counts = Column(String) 
    total_frames = Column(Integer)

# 8. RAW EMOTION LOGS
class MoodSession(Base):
    __tablename__ = "emotion_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    emotion = Column(String)
    confidence = Column(Float)
    timestamp = Column(Float)
>>>>>>> f097ba3bf547ebcc72d0f8aefc910dda298d2118
