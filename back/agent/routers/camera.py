from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
import json
import time
import os
import shutil
from datetime import date
from typing import Dict, Any

# Adjust these imports to match your project structure
from setup_db import get_db, DB_PATH
import models  # Assuming your models.py is in the root or accessible
from services.video_service import video_service

# ✅ Fix: No internal prefix, handled by main.py
router = APIRouter(tags=["camera"])

# Temp directory for processing uploads
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

@router.post("/analyze_session")  # ✅ Result: /api/camera/analyze_session
async def analyze_session_endpoint(
    file: UploadFile = File(...), 
    user_id: str = "user_001",  # In production, get this from Auth header
    db: Session = Depends(get_db)
):
    """
    Receives a video blob, analyzes emotions, saves to DB, returns stats.
    """
    # 1. Save Video to Temp File
    temp_filename = f"temp_{int(time.time())}_{file.filename}"
    temp_path = os.path.join(TEMP_DIR, temp_filename)
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Process Video (Heavy CPU task -> run in threadpool)
        result = await run_in_threadpool(video_service.process_session, temp_path)
        
        # Log to console for debugging
        print(f"✅ Analysis for {user_id}: {result['dominant_emotion']} ({result['confidence']}%)")

        # 3. Extract Data
        emotion = result.get("dominant_emotion", "Neutral")
        confidence = float(result.get("confidence", 0.0))
        percentages = result.get("percentages", {})

        # Low confidence guardrail
        if confidence < 15.0:
            emotion = "Neutral"

        # 4. Save to Database
        try:
            today_str = date.today().isoformat()
            timestamp = time.time()

            # A. Save Raw Session Log
            new_log = models.MoodSession(
                user_id=user_id,
                emotion=emotion,
                confidence=confidence,
                timestamp=timestamp
            )
            db.add(new_log)

            # B. Update Daily Summary
            # Check if summary exists for today
            daily = db.query(models.DailySummary).filter(
                models.DailySummary.user_id == user_id,
                models.DailySummary.date_str == today_str
            ).first()

            if daily:
                # Load existing counts, update, and save back
                current_counts = json.loads(daily.emotion_counts)
                current_counts[emotion] = current_counts.get(emotion, 0) + 1
                daily.emotion_counts = json.dumps(current_counts)
                daily.total_frames = (daily.total_frames or 0) + 1
            else:
                # Create new daily entry
                daily = models.DailySummary(
                    user_id=user_id,
                    date_str=today_str,
                    emotion_counts=json.dumps({emotion: 1}),
                    total_frames=1
                )
                db.add(daily)

            db.commit()

        except Exception as db_e:
            db.rollback()
            print(f"❌ Database Error: {db_e}")
            # We don't raise here because we still want to return the analysis to the user

        # 5. Return JSON to Client
        return {
            "dominant_emotion": emotion,
            "confidence": confidence,
            "percentages": percentages,
            "raw_counts": result.get("emotion_counts", {})
        }

    except Exception as e:
        print(f"❌ Critical Error: {e}")
        raise HTTPException(status_code=500, detail="Video processing failed")
        
    finally:
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)