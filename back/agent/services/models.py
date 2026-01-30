from sqlalchemy import Column, Integer, String, Float
from setup_db import Base

class MoodSession(Base):
    __tablename__ = "emotion_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String)
    emotion = Column(String, index=True)
    confidence = Column(Float)
    timestamp = Column(Float)

class DailySummary(Base):
    __tablename__ = "emotion_daily"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String)
    day = Column(String) # "2024-05-20"
    emotion = Column(String)
    emotion_counts = Column(Integer)