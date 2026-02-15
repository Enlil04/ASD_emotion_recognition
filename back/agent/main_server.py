import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# --- ROUNTING IMPORTS ---
from routers import chat, guardian, auth, camera, community, dashboard, profile

# --- SERVICE IMPORTS ---
from services.video_service import video_service
from react_agent import AgenticBrain
from setup_db import DB_PATH, setup_tables  # Import the setup function we wrote

# --- CONFIG ---
app = FastAPI(
    title="Nimi Guardian API",
    description="Backend for the AI Therapist & Guardian System",
    version="1.0.0"
)

# 1. CORS (CRITICAL FOR FRONTEND)
# This allows your Flutter app (or localhost:3000) to talk to this server
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8080",
    "*",  # For development only - allows all connections
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. MOUNT STATIC FILES (If you want to serve generated images/videos)
# app.mount("/static", StaticFiles(directory="static"), name="static")


# 3. ROUTERS
# We add /api/auth to keep it consistent with the others
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/chat", tags=["Nimi Chat"])
app.include_router(camera.router, prefix="/api/camera", tags=["Camera"])
app.include_router(community.router, prefix="/api/community", tags=["Community"])
app.include_router(guardian.router, prefix="/api/guardian", tags=["Guardian"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])


# 4. STARTUP LIFECYCLE
@app.on_event("startup")
async def startup_event():
    print("\n🧠 STARTING NIMI ENGINE...")
    
    # A. Run Database Migrations
    # This ensures your 'therapist_code' and 'email' columns exist every time you restart
    print(f"📂 Checking Database at: {DB_PATH}")
    setup_tables() 
    
    # B. Initialize Global Services
    app.state.video_service = video_service
    
    # C. Initialize the AI Brain
    # (We assume AgenticBrain takes db_path as an argument)
    try:
        app.state.brain = AgenticBrain(db_path=DB_PATH, user_id="user_001")
        print("🤖 AgenticBrain Online")
    except Exception as e:
        print(f"⚠️ Warning: AgenticBrain failed to load (Chat may be broken): {e}")

    # D. Initialize System State (Shared Mailbox)
    app.state.system_state = {
        "latest_emotion": "Neutral",
        "face_detected": False,
        "last_updated": 0
    }
    
    print("✅ SYSTEM READY: Waiting for connections...\n")


@app.on_event("shutdown")
def shutdown_event():
    print("🛑 Shutting down Nimi Engine...")


# 5. ENTRY POINT
if __name__ == "__main__":
    # Use port 8000. '0.0.0.0' makes it accessible on your local network (for testing on phone)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)