from sqlalchemy import Column, Integer, String, Float
from setup_db import Base

# 1. EMOTION LOGS
class MoodSession(Base):
    __tablename__ = "emotion_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    emotion = Column(String, index=True)
    confidence = Column(Float)
    timestamp = Column(Float)  # ✅ CHANGED from 'ts' to 'timestamp'

# 2. DAILY SUMMARY
class DailySummary(Base):
    __tablename__ = "emotion_daily"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    day = Column(String) 
    emotion = Column(String)
    emotion_counts = Column(Integer, default=0)
    updated_at = Column(Float)

# 3. USERS
class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    name = Column(String)
    role = Column(String)
    age = Column(Integer)
    photo_url = Column(String)
    description = Column(String)
    connections = Column(Integer, default=0)
    streak = Column(Integer, default=0)
    preferences_json = Column(String)
    created_at = Column(Float)
    updated_at = Column(Float)

# 4. COMMUNITY POSTS
class CommunityPost(Base):
    __tablename__ = "community_posts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    content = Column(String)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    date_created = Column(Float)

# 5. COMMENTS
class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, index=True)
    user_id = Column(String)
    content = Column(String)
    date_created = Column(Float)

# 6. INTERACTIONS
class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    
    # Standard AI Memory Columns
    role = Column(String)      
    content = Column(String)   
    timestamp = Column(Float)  # ✅ CHANGED from 'ts' to 'timestamp'
    
    # Optional metadata
    readable_time = Column(String, nullable=True)
    event_type = Column(String, nullable=True)