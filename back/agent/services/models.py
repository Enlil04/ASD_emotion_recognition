from sqlalchemy import Column, Integer, String, Float, Text, UniqueConstraint
from setup_db import Base

# ----------------------------
# EMOTIONS
# ----------------------------
class MoodSession(Base):
    __tablename__ = "emotion_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    emotion = Column(String, index=True)
    confidence = Column(Float)
    timestamp = Column(Float, index=True)

class DailySummary(Base):
    __tablename__ = "emotion_daily"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    day = Column(String, index=True, nullable=False)      # "YYYY-MM-DD"
    emotion = Column(String, index=True, nullable=False)
    count = Column(Integer, nullable=False, default=0)    # <-- unified column name
    updated_at = Column(Float)

    __table_args__ = (
        UniqueConstraint("user_id", "day", "emotion", name="ux_emotion_daily_user_day_emotion"),
    )

# ----------------------------
# USERS (union)
# ----------------------------
class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True)
    name = Column(String)
    role = Column(String)
    age = Column(Integer)
    description = Column(Text)
    photo = Column(String)
    streak = Column(Integer, default=0)
    connections = Column(Integer, default=0)
    username = Column(String, unique=True, index=True)

    preferences_json = Column(Text)
    created_at = Column(Float)
    updated_at = Column(Float)

# ----------------------------
# COMMUNITY (union)
# ----------------------------
class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    date_created = Column(Float, index=True)
    is_deleted = Column(Integer, default=0)  # <-- keep your old DB column

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    date_created = Column(Float, index=True)

class PostLike(Base):
    __tablename__ = "post_likes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    date_created = Column(Float)

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="ux_post_likes_post_user"),
    )

# ----------------------------
# EXTRA TABLES YOU HAD (keep them)
# ----------------------------
class DailyEmotionStats(Base):
    __tablename__ = "daily_emotion_stats"
    user_id = Column(String, primary_key=True)
    date_str = Column(String, primary_key=True)
    emotion_counts = Column(Text)
    total_frames = Column(Integer)

class SignificantEvent(Base):
    __tablename__ = "significant_events"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    timestamp = Column(Float, index=True)
    event_type = Column(String, index=True)
    description = Column(Text)
    context_json = Column(Text)

class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    ts = Column(Float, index=True, nullable=False)
    readable_time = Column(String)
    event_type = Column(String)
    user_input = Column(Text)
    agent_response = Column(Text)
    detected_emotion = Column(String)
    confidence = Column(Float)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id = Column(String, primary_key=True)
    preferences_json = Column(Text)

class CommunityReport(Base):
    __tablename__ = "community_reports"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, index=True, nullable=False)
    reporter_user_id = Column(String, index=True, nullable=False)
    reason = Column(Text)
    date_created = Column(Float, index=True)



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