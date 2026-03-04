from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, UniqueConstraint
from setup_db import Base

# 1. USERS
class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)      
    password_hash = Column(String)                       
    is_active = Column(Integer, default=1)               
    name = Column(String)
    role = Column(String)
    age = Column(Integer)
    dob = Column(String)                                 # <--- ADDED to match setup_db.py
    photo = Column(String)
    description = Column(String)
    connections = Column(Integer, default=0)
    streak = Column(Integer, default=0)
    preferences_json = Column(String)
    created_at = Column(Float)
    updated_at = Column(Float)
    therapist_code = Column(String, unique=True, index=True, nullable=True) 

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

# 9. THERAPIST / GUARDIAN CONNECTIONS (FIXED PK)
class TherapistPatient(Base):
    __tablename__ = "therapist_patient"
    # setup_db.py defines a composite primary key, so we remove the `id` column 
    # and mark both therapist_id and patient_id as primary_key=True
    therapist_id = Column(String, primary_key=True, index=True)  
    patient_id = Column(String, primary_key=True, index=True)    
    date_assigned = Column(Float)

# 10. SIGNIFICANT EVENTS (ADDED to match setup_db.py)
class SignificantEvent(Base):
    __tablename__ = "significant_events"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    timestamp = Column(Float)
    event_type = Column(String)
    description = Column(String)
    context_json = Column(String)

# 11. USER PROFILES (ADDED to match setup_db.py)
class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id = Column(String, primary_key=True, index=True)
    preferences_json = Column(String)








class GardenPot(Base):
    __tablename__ = "garden_pots"

    id = Column(Integer, primary_key=True, index=True)
    # CHANGE THIS LINE TO String 👇
    user_id = Column(String, index=True, nullable=False) 
    pot_index = Column(Integer, nullable=False) 
    seed_type = Column(String, nullable=True)   
    stage = Column(Integer, default=0)
    last_watered = Column(String, nullable=True) 

    __table_args__ = (UniqueConstraint('user_id', 'pot_index', name='_user_pot_uc'),)

class HarvestedPlant(Base):
    __tablename__ = "harvested_plants"

    id = Column(Integer, primary_key=True, index=True)
    # CHANGE THIS LINE TO String 👇
    user_id = Column(String, index=True, nullable=False)
    plant_type = Column(String, nullable=False)
    harvest_date = Column(String, nullable=False)

# --- Pydantic Schemas (For API Validation) ---

class PlantRequest(BaseModel):
    pot_index: int
    seed_type: str

class WaterRequest(BaseModel):
    pot_index: int
    date: str

class HarvestRequest(BaseModel):
    pot_index: int
    plant_type: str
    harvest_date: str