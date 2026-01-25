"""
ORCHESTRATOR (THE BODY)
-----------------------
This script runs the main execution loop. It mimics the mobile application state, 
captures real-time vision data, detects triggers (like game events or 
sustained negative emotions), and coordinates calls to the 'Brain' (LLM) 
only when necessary.
"""

"""
ORCHESTRATOR (NON-BLOCKING / ASYNC)
-----------------------------------
This script runs the main execution loop using THREADING.
- Main Thread: Captures video, runs emotion detection (30 FPS).
- Background Thread: Sends data to the AgenticBrain (LLM) when triggered.

This prevents the camera from "freezing" while the AI is thinking.
"""
import time
import threading
import os
import cv2

# --- CONFIGURATION ---
# Ensure database is found in the 'data' folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "memory.db")
USER_ID = "user_001"
SESSION_WINDOW_SEC = 60
FLUSH_INTERVAL_SEC = 30 

from react_agent import AgenticBrain
from analytics.vision_models.emotion_detector import EmotionDetector, MODEL_FILE, LABELS
from analytics.vision_models.local_memory.emotion_summary import EmotionSummarizer
from analytics.vision_models.local_memory.session_memory import SessionMemoryManager
from analytics.vision_models.local_memory.long_term_memory import LongTermMemoryStore, aggregate_recent_emotions, day_string_local
from analytics.vision_models.local_memory.tools.emotion_tool import get_emotion_state, get_session_state

# --- SHARED STATE (Thread-Safe) ---
app_state = {
    "current_activity": "idle",
    "last_event": None,
    "active_session": True,
    "user_typed_message": None,
    
    # New: Stores the latest AI response to display on screen
    "latest_ai_speech": "Listening...",
    "latest_ai_action": None,
    
    # New: Flag to prevent spamming the brain while it's already thinking
    "is_brain_thinking": False
}

def input_listener():
    """Reads keyboard input without stopping the camera."""
    print("\n--- CONTROLS ---")
    print(" Type text to chat.")
    print(" 'g'=Game Start, 'f'=Fail, 'w'=Win, 'exit'=Quit")
    print("----------------\n")

    while app_state["active_session"]:
        try:
            user_in = input()
            if user_in.lower() in ["exit", "quit"]:
                app_state["active_session"] = False
                break
            elif user_in == "g":
                app_state["current_activity"] = "playing_memory_game"
                app_state["last_event"] = "game_started"
                print("📱 APP: Game Started")
            elif user_in == "f":
                app_state["last_event"] = "level_failed"
                print("📱 APP: Level Failed")
            elif user_in == "w":
                app_state["last_event"] = "level_complete"
                print("📱 APP: Level Won")
            else:
                app_state["user_typed_message"] = user_in
        except EOFError:
            break

def brain_task(brain, vision_packet, prompt_text, extra_context):
    """
    The 'Slow' task that runs in the background.
    """
    try:
        # This takes 2-5 seconds, but won't freeze the camera now!
        response_speech = brain.decide_response(vision_packet, prompt_text, extra_context=extra_context)
        
        # Update shared state so the Main Loop can display it
        app_state["latest_ai_speech"] = response_speech
        print(f"\n💬 COMPANION: {response_speech}\n")
        
    except Exception as e:
        print(f"❌ Brain Error: {e}")
    finally:
        # Unlock the brain so it can be triggered again
        app_state["is_brain_thinking"] = False

def main_loop():
    print(f"✅ Starting Orchestrator with DB: {DB_PATH}")

    # 1. Initialize Components
    try:
        brain = AgenticBrain(db_path=DB_PATH, user_id=USER_ID)
        print("🧠 Brain Loaded.")
    except Exception as e:
        print(f"❌ Failed to load Brain: {e}")
        return

    detector = EmotionDetector(MODEL_FILE)
    summarizer = EmotionSummarizer()
    session_mem = SessionMemoryManager(emotion_window_sec=SESSION_WINDOW_SEC)
    ltm = LongTermMemoryStore(DB_PATH)

    # 2. Start Camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ CRITICAL: Could not open webcam.")
        return

    # 3. Start Input Thread
    input_thread = threading.Thread(target=input_listener, daemon=True)
    input_thread.start()

    consecutive_negative_frames = 0
    last_flush = time.time()

    print("🎥 Camera Active. Press 'exit' to quit.")

    while app_state["active_session"]:
        ret, frame = cap.read()
        if not ret:
            break

        # --- FAST LOOP: Vision (30ms) ---
        emotion, conf, box, probs = detector.predict(frame)
        face_detected = box is not None

        summarizer.update(emotion, conf, probs, LABELS, face_detected)
        summary = summarizer.get_summary()
        if summary:
            session_mem.update_emotion(summary)

        # Periodic DB Flush
        now = time.time()
        if now - last_flush >= FLUSH_INTERVAL_SEC:
            state = session_mem.get_state()
            counts = aggregate_recent_emotions(state["recent_emotions"])
            if counts:
                ltm.add_emotion_counts(USER_ID, day_string_local(), counts)
            last_flush = now

        # Prepare Context
        emotion_state = get_emotion_state(summarizer)
        session_state = get_session_state(session_mem)
        current_emotion = emotion_state.get("dominant", "Neutral")
        
        # Grab (and clear) transient events
        activity = app_state["current_activity"]
        event = app_state["last_event"]
        user_msg = app_state["user_typed_message"]
        
        if event: app_state["last_event"] = None
        if user_msg: app_state["user_typed_message"] = None

        # --- TRIGGER LOGIC ---
        trigger_reason = None
        prompt_text = ""

        if user_msg:
            trigger_reason = "user_chat"
            prompt_text = user_msg
        elif event == "level_failed":
            trigger_reason = "app_event"
            prompt_text = f"System Alert: User failed level in {activity}."
        elif activity != "idle" and current_emotion in ["Anger", "Sad", "Fear"]:
            consecutive_negative_frames += 1
            if consecutive_negative_frames > 20: # Sustained emotion
                trigger_reason = "emotion_pattern"
                prompt_text = f"User looks {current_emotion} for a while during {activity}."
                consecutive_negative_frames = 0
        else:
            consecutive_negative_frames = 0

        # --- ASYNC BRAIN CALL ---
        # Only trigger if the brain is NOT already busy thinking
        if trigger_reason and not app_state["is_brain_thinking"]:
            print(f"⚡ Triggered: {trigger_reason} (Thinking...)")
            app_state["is_brain_thinking"] = True
            
            vision_packet = {
                "emotion": current_emotion,
                "timestamp": time.time()
            }
            extra_context = {
                "emotion_state": emotion_state,
                "session_state": session_state,
                "top_emotions_7d": ltm.get_top_emotions_last_days(USER_ID, 7),
            }
            
            # Start the "Brain" in a separate thread
            t = threading.Thread(
                target=brain_task, 
                args=(brain, vision_packet, prompt_text, extra_context)
            )
            t.start()
        
        # --- UI DISPLAY (Visualizing the 'Brain' status) ---
        # Draw status on the video frame
        status_color = (0, 255, 0) if not app_state["is_brain_thinking"] else (0, 165, 255) # Green vs Orange
        status_text = "Status: Thinking..." if app_state["is_brain_thinking"] else f"Status: {current_emotion}"
        
        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        
        # Show last AI message at the bottom
        ai_msg = f"AI: {app_state['latest_ai_speech']}"
        cv2.putText(frame, ai_msg[:50], (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        cv2.imshow("Orchestrator (Async)", frame)
        if cv2.waitKey(1) & 0xFF == 27: # ESC
            break

    cap.release()
    cv2.destroyAllWindows()
    app_state["active_session"] = False

if __name__ == "__main__":
    main_loop()
# import time
# import threading

# import cv2

# from react_agent import AgenticBrain

# from analytics.vision_models.emotion_detector import EmotionDetector, MODEL_FILE, LABELS
# from analytics.vision_models.local_memory.emotion_summary import EmotionSummarizer
# from analytics.vision_models.local_memory.session_memory import SessionMemoryManager
# from analytics.vision_models.local_memory.long_term_memory import LongTermMemoryStore, aggregate_recent_emotions, day_string_local
# from analytics.vision_models.local_memory.tools.emotion_tool import get_emotion_state, get_session_state

# import os

# # Ensure this points to the same 'data' folder
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DB_PATH = os.path.join(BASE_DIR, "data", "memory.db")

# # Now when you initialize the brain, it uses the correct path:
# # brain = AgenticBrain(db_path=DB_PATH, user_id=USER_ID)


# # This mimics what the Flutter App would send to the backend
# app_state = {
#     "current_activity": "idle",
#     "last_event": None,
#     "active_session": True,
#     "user_typed_message": None
# }

# USER_ID = "user_001"
# DB_PATH = "memory.db"

# SESSION_WINDOW_SEC = 60
# FLUSH_INTERVAL_SEC = 30  # push session emotion counts -> sqlite every 30s


# def input_listener():
#     print("\n--- SIMULATION CONTROLS ---")
#     print(" [TYPE TEXT]: Simulates user talking to AI")
#     print(" 'g' -> Event: User starts Game")
#     print(" 'f' -> Event: User FAILS level")
#     print(" 'w' -> Event: User WINS level")
#     print(" 'exit' -> Quit System")
#     print("---------------------------\n")

#     while app_state["active_session"]:
#         user_in = input()
#         if user_in.lower() in ["exit", "quit"]:
#             app_state["active_session"] = False
#             break
#         elif user_in == "g":
#             app_state["current_activity"] = "playing_memory_game"
#             app_state["last_event"] = "game_started"
#             print("📱 APP: Game Started")
#         elif user_in == "f":
#             app_state["last_event"] = "level_failed"
#             print("📱 APP: Level Failed")
#         elif user_in == "w":
#             app_state["last_event"] = "level_complete"
#             print("📱 APP: Level Won")
#         else:
#             app_state["user_typed_message"] = user_in


# def main_loop():
#     print("Starting Orchestrator (Body)...")

#     # 1) Agent brain (uses SQLite MemoryManager internally)
#     print("Loading Agentic Brain (Llama 3.2)...")
#     try:
#         brain = AgenticBrain(db_path=DB_PATH, user_id=USER_ID)
#         print("Brain Loaded.")
#     except Exception as e:
#         print(f"Failed to load Brain: {e}")
#         brain = None

#     # 2) Vision pipeline (in-process)
#     detector = EmotionDetector(MODEL_FILE)
#     summarizer = EmotionSummarizer()
#     session_mem = SessionMemoryManager(emotion_window_sec=SESSION_WINDOW_SEC)
#     ltm = LongTermMemoryStore(DB_PATH)

#     # 3) Camera
#     cap = cv2.VideoCapture(0)
#     if not cap.isOpened():
#         print("CRITICAL: Could not open webcam.")
#         return

#     # 4) Input listener thread
#     input_thread = threading.Thread(target=input_listener, daemon=True)
#     input_thread.start()

#     consecutive_negative_frames = 0
#     last_flush = time.time()

#     try:
#         while app_state["active_session"]:
#             ret, frame = cap.read()
#             if not ret:
#                 break

#             # ----- PHASE 1: SENSE (frame -> detector -> summarizer -> session) -----
#             emotion, conf, box, probs = detector.predict(frame)
#             face_detected = box is not None

#             summarizer.update(
#                 emotion=emotion,
#                 conf=conf,
#                 probs=probs,
#                 labels=LABELS,
#                 face_detected=face_detected
#             )
#             summary = summarizer.get_summary()
#             if summary is not None:
#                 session_mem.update_emotion(summary)

#             # Flush session -> SQLite aggregates periodically
#             now = time.time()
#             if now - last_flush >= FLUSH_INTERVAL_SEC:
#                 state = session_mem.get_state()
#                 counts = aggregate_recent_emotions(state["recent_emotions"])
#                 if counts:
#                     ltm.add_emotion_counts(USER_ID, day_string_local(), counts)
#                 last_flush = now

#             # Tool outputs (agent-facing)
#             emotion_state = get_emotion_state(summarizer)     # best: includes face_detected/top2/etc
#             session_state = get_session_state(session_mem)    # conversation_summary/current_goal/recent_emotions

#             current_emotion = (emotion_state.get("dominant") or "Neutral")
#             activity = app_state["current_activity"]
#             event = app_state["last_event"]
#             user_msg = app_state["user_typed_message"]

#             # reset transient states
#             if event:
#                 app_state["last_event"] = None
#             if user_msg:
#                 app_state["user_typed_message"] = None

#             # ----- PHASE 2: EVALUATE TRIGGERS -----
#             trigger_reason = None
#             prompt_text = ""

#             if user_msg:
#                 trigger_reason = "user_chat"
#                 prompt_text = user_msg

#             elif event == "level_failed":
#                 trigger_reason = "app_event"
#                 prompt_text = f"System Alert: The user just failed a difficult level in {activity}."

#             elif event == "level_complete":
#                 trigger_reason = "app_event"
#                 prompt_text = f"System Alert: The user just won the level in {activity}!"

#             # Emotional persistence (use your label casing)
#             elif activity != "idle" and current_emotion in ["Anger", "Sad", "Fear"]:
#                 consecutive_negative_frames += 1
#                 if consecutive_negative_frames > 15:  # ~7.5 seconds if sleep=0.5
#                     trigger_reason = "emotion_pattern"
#                     prompt_text = (
#                         f"System Alert: The user has looked {current_emotion} for several seconds "
#                         f"while {activity}. They may be struggling."
#                     )
#                     consecutive_negative_frames = 0
#             else:
#                 consecutive_negative_frames = 0

#             # ----- PHASE 3: THINK & ACT -----
#             if trigger_reason and brain:
#                 print(f"\nTRIGGER: {trigger_reason} | Emotion: {current_emotion}")

#                 vision_packet = {
#                     "emotion": current_emotion,
#                     "gaze": "screen_center",
#                     "iris": "normal",
#                     "timestamp": time.time()
#                 }

#                 # extra context for the reasoner
#                 extra_context = {
#                     "emotion_state": emotion_state,
#                     "session_state": session_state,
#                     "top_emotions_7d": ltm.get_top_emotions_last_days(USER_ID, 7),
#                 }

#                 response_speech = brain.decide_response(vision_packet, prompt_text, extra_context=extra_context)

#                 print(f'COMPANION: "{response_speech}"')
#                 print("------------------------------------------------")

#             # Optional: show camera window
#             cv2.imshow("Orchestrator", frame)
#             if cv2.waitKey(1) & 0xFF == 27:
#                 break

#             time.sleep(0.5)

#     except KeyboardInterrupt:
#         print("\nShutting down...")
#     finally:
#         cap.release()
#         cv2.destroyAllWindows()
#         app_state["active_session"] = False


# if __name__ == "__main__":
#     main_loop()
