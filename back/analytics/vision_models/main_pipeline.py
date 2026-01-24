import cv2
import time

from emotion_detector import EmotionDetector, LABELS, MODEL_FILE
from emotion_summary import EmotionSummarizer
from session_memory import SessionMemoryManager
from long_term_memory import LongTermMemoryStore, aggregate_recent_emotions, day_string_local
from tools.emotion_tool import get_emotion_state, get_session_state

USER_ID = "user_001"  # later: per-login user id
FLUSH_INTERVAL = 30   # seconds

def run():
    # 1) init modules
    detector = EmotionDetector(MODEL_FILE)
    summarizer = EmotionSummarizer()
    session_mem = SessionMemoryManager(emotion_window_sec=60)
    ltm = LongTermMemoryStore("memory.db")

    cap = cv2.VideoCapture(0)
    last_flush = time.time()
    last_print = 0.0

    print("Running pipeline... ESC to exit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 2) detector -> raw outputs
        emotion, conf, box, probs = detector.predict(frame)
        face_detected = box is not None

        # 3) summarizer (1Hz summary)
        summarizer.update(
            emotion=emotion,
            conf=conf,
            probs=probs,
            labels=LABELS,
            face_detected=face_detected
        )

        # 4) summarizer -> session memory (store snapshot)
        summary = summarizer.get_summary()
        if summary is not None:
            session_mem.update_emotion(summary)

        # 5) TOOL OUTPUTS (what your agent will call)
        # option A: read latest summarizer summary
        tool_emotion = get_emotion_state(summarizer)

        # option B: read latest session snapshot (backwards compatible)
        tool_emotion_from_session = get_emotion_state(session_mem)

        # full session state for agent
        tool_session = get_session_state(session_mem)

        # print tool payload sometimes (debug)
        now = time.time()
        if now - last_print > 2.0:
            last_print = now
            print("TOOL emotion(summarizer):", tool_emotion)
            # print("TOOL emotion(session):", tool_emotion_from_session)
            # print("TOOL session:", tool_session)

        # 6) Periodically flush session -> long-term SQLite aggregates
        if now - last_flush >= FLUSH_INTERVAL:
            state = session_mem.get_state()
            counts = aggregate_recent_emotions(state["recent_emotions"])
            if counts:
                day = day_string_local()
                ltm.add_emotion_counts(USER_ID, day, counts)
                print(f"Flushed to DB for {USER_ID} on {day}:", counts)
            last_flush = now

        # 7) UI
        if box:
            x1, y1, x2, y2 = box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"{emotion} {int(conf*100)}%",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

        cv2.imshow("Emotion Pipeline", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run()
