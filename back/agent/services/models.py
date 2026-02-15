from sqlalchemy import Column, Integer, String, Float
from setup_db import Base

# 1. USERS
class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)      # <--- ADDED
    password_hash = Column(String)                       # <--- ADDED
    is_active = Column(Integer, default=1)               # <--- ADDED
    name = Column(String)
    role = Column(String)
    age = Column(Integer)
    photo = Column(String)
    description = Column(String)
    connections = Column(Integer, default=0)
    streak = Column(Integer, default=0)
    preferences_json = Column(String)
    created_at = Column(Float)
    updated_at = Column(Float)
    therapist_code = Column(String,unique=True, index=True, nullable=True)  # For patients, who is their therapist? (Nullable for therapists)

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

# 9. THERAPIST / GUARDIAN CONNECTIONS (MISSING!)
class TherapistPatient(Base):
    __tablename__ = "therapist_patient"
    id = Column(Integer, primary_key=True, index=True)
    therapist_id = Column(String, index=True)  # The Parent/Therapist User ID
    patient_id = Column(String, index=True)    # The Child/Patient User ID
    date_assigned = Column(Float)