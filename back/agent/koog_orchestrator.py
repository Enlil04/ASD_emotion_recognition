# koog_orchestrator.py  (SQLite + in-process vision, NO JSON polling, NO subprocess)
import time
import threading

import cv2

from react_agent import AgenticBrain

from analytics.vision_models.emotion_detector import EmotionDetector, MODEL_FILE, LABELS
from back.analytics.vision_models.local_memory.emotion_summary import EmotionSummarizer
from back.analytics.vision_models.local_memory.session_memory import SessionMemoryManager
from back.analytics.vision_models.local_memory.long_term_memory import LongTermMemoryStore, aggregate_recent_emotions, day_string_local
from analytics.vision_models.tools.emotion_tool import get_emotion_state, get_session_state


# This mimics what the Flutter App would send to the backend
app_state = {
    "current_activity": "idle",
    "last_event": None,
    "active_session": True,
    "user_typed_message": None
}

USER_ID = "user_001"
DB_PATH = "memory.db"

SESSION_WINDOW_SEC = 60
FLUSH_INTERVAL_SEC = 30  # push session emotion counts -> sqlite every 30s


def input_listener():
    print("\n--- SIMULATION CONTROLS ---")
    print(" [TYPE TEXT]: Simulates user talking to AI")
    print(" 'g' -> Event: User starts Game")
    print(" 'f' -> Event: User FAILS level")
    print(" 'w' -> Event: User WINS level")
    print(" 'exit' -> Quit System")
    print("---------------------------\n")

    while app_state["active_session"]:
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


def main_loop():
    print("Starting Orchestrator (Body)...")

    # 1) Agent brain (uses SQLite MemoryManager internally)
    print("Loading Agentic Brain (Llama 3.2)...")
    try:
        brain = AgenticBrain(db_path=DB_PATH, user_id=USER_ID)
        print("Brain Loaded.")
    except Exception as e:
        print(f"Failed to load Brain: {e}")
        brain = None

    # 2) Vision pipeline (in-process)
    detector = EmotionDetector(MODEL_FILE)
    summarizer = EmotionSummarizer()
    session_mem = SessionMemoryManager(emotion_window_sec=SESSION_WINDOW_SEC)
    ltm = LongTermMemoryStore(DB_PATH)

    # 3) Camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("CRITICAL: Could not open webcam.")
        return

    # 4) Input listener thread
    input_thread = threading.Thread(target=input_listener, daemon=True)
    input_thread.start()

    consecutive_negative_frames = 0
    last_flush = time.time()

    try:
        while app_state["active_session"]:
            ret, frame = cap.read()
            if not ret:
                break

            # ----- PHASE 1: SENSE (frame -> detector -> summarizer -> session) -----
            emotion, conf, box, probs = detector.predict(frame)
            face_detected = box is not None

            summarizer.update(
                emotion=emotion,
                conf=conf,
                probs=probs,
                labels=LABELS,
                face_detected=face_detected
            )
            summary = summarizer.get_summary()
            if summary is not None:
                session_mem.update_emotion(summary)

            # Flush session -> SQLite aggregates periodically
            now = time.time()
            if now - last_flush >= FLUSH_INTERVAL_SEC:
                state = session_mem.get_state()
                counts = aggregate_recent_emotions(state["recent_emotions"])
                if counts:
                    ltm.add_emotion_counts(USER_ID, day_string_local(), counts)
                last_flush = now

            # Tool outputs (agent-facing)
            emotion_state = get_emotion_state(summarizer)     # best: includes face_detected/top2/etc
            session_state = get_session_state(session_mem)    # conversation_summary/current_goal/recent_emotions

            current_emotion = (emotion_state.get("dominant") or "Neutral")
            activity = app_state["current_activity"]
            event = app_state["last_event"]
            user_msg = app_state["user_typed_message"]

            # reset transient states
            if event:
                app_state["last_event"] = None
            if user_msg:
                app_state["user_typed_message"] = None

            # ----- PHASE 2: EVALUATE TRIGGERS -----
            trigger_reason = None
            prompt_text = ""

            if user_msg:
                trigger_reason = "user_chat"
                prompt_text = user_msg

            elif event == "level_failed":
                trigger_reason = "app_event"
                prompt_text = f"System Alert: The user just failed a difficult level in {activity}."

            elif event == "level_complete":
                trigger_reason = "app_event"
                prompt_text = f"System Alert: The user just won the level in {activity}!"

            # Emotional persistence (use your label casing)
            elif activity != "idle" and current_emotion in ["Anger", "Sad", "Fear"]:
                consecutive_negative_frames += 1
                if consecutive_negative_frames > 15:  # ~7.5 seconds if sleep=0.5
                    trigger_reason = "emotion_pattern"
                    prompt_text = (
                        f"System Alert: The user has looked {current_emotion} for several seconds "
                        f"while {activity}. They may be struggling."
                    )
                    consecutive_negative_frames = 0
            else:
                consecutive_negative_frames = 0

            # ----- PHASE 3: THINK & ACT -----
            if trigger_reason and brain:
                print(f"\nTRIGGER: {trigger_reason} | Emotion: {current_emotion}")

                vision_packet = {
                    "emotion": current_emotion,
                    "gaze": "screen_center",
                    "iris": "normal",
                    "timestamp": time.time()
                }

                # extra context for the reasoner
                extra_context = {
                    "emotion_state": emotion_state,
                    "session_state": session_state,
                    "top_emotions_7d": ltm.get_top_emotions_last_days(USER_ID, 7),
                }

                response_speech = brain.decide_response(vision_packet, prompt_text, extra_context=extra_context)

                print(f'COMPANION: "{response_speech}"')
                print("------------------------------------------------")

            # Optional: show camera window
            cv2.imshow("Orchestrator", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        app_state["active_session"] = False


if __name__ == "__main__":
    main_loop()
