import json
import time
from pathlib import Path
from statistics import mode
from collections import Counter

class VisionSession:
    def __init__(self, user_id="default_user"):
        self.user_id = user_id

        # Paths
        self.base_dir = Path(__file__).resolve().parent
        self.memory_file = self.base_dir / ".." / "local_memory" / "emotion_log.json"
        self.baseline_file = self.base_dir / ".." / "local_memory" / "baseline.json"

        # Session variables
        self.session_id = f"{time.strftime('%Y%m%d_%H%M%S')}"
        self.timestamp_start = time.time()
        self.timestamp_end = None

        # Placeholders
        self.session_data = []
        self.gaze_events = []      # you will fill later
        self.baseline = {}

    # ----------------------------------------
    # LOADERS
    # ----------------------------------------
    def load_baseline(self):
        if self.baseline_file.exists():
            try:
                self.baseline = json.loads(self.baseline_file.read_text())
            except:
                self.baseline = {}
        else:
            self.baseline = {}

    def load_session_logs(self):
        """Loads logs only between session_start & session_end."""
        if not self.memory_file.exists():
            return []

        try:
            logs = json.loads(self.memory_file.read_text())
        except:
            logs = []

        session_logs = [
            entry for entry in logs
            if self.timestamp_start <= entry["timestamp"] <= self.timestamp_end
        ]

        return session_logs

    # ----------------------------------------
    # ANALYTICS
    # ----------------------------------------
    def compute_session_summary(self, entries):
        if not entries:
            return {
                "dominant_emotion": "neutral",
                "emotion_distribution": {},
                "most_intense_event": None
            }

        emotions = [e["emotion"] for e in entries]
        dist = Counter(emotions)

        total = sum(dist.values())
        emotion_dist = {k: round(v / total, 3) for k, v in dist.items()}

        # dominant
        dominant = max(dist, key=dist.get)

        # most intense
        intense = max(entries, key=lambda x: x["confidence"])

        most_intense = {
            "emotion": intense["emotion"],
            "confidence": intense["confidence"],
            "timestamp": intense["timestamp"]
        }

        return {
            "dominant_emotion": dominant,
            "emotion_distribution": emotion_dist,
            "most_intense_event": most_intense
        }

    # ----------------------------------------
    # PUBLIC API
    # ----------------------------------------
    def end_session(self):
        self.timestamp_end = time.time()

    def generate_json(self, save=True):
        self.load_baseline()
        session_entries = self.load_session_logs()
        summary = self.compute_session_summary(session_entries)

        final_json = {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,

            "baseline_emotions": self.baseline,

            "session_summary": summary,
            "emotion_stream": session_entries,
            "gaze_events": self.gaze_events,

            "notes": ""
        }

        if save:
            out_path = self.base_dir / f"session_{self.session_id}.json"
            out_path.write_text(json.dumps(final_json, indent=2))
            print(f"💾 Session JSON saved: {out_path}")

        return final_json
