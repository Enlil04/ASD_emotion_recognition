import json
import time
from pathlib import Path
from collections import Counter

class VisionSession:
    def __init__(self, user_id="default_user"):
        self.user_id = user_id

        # Paths
        self.base_dir = Path(__file__).resolve().parent
        # The master logs that accumulate data over time
        self.memory_file = self.base_dir / ".." / "local_memory" / "emotion_log.json" 
        
        # Files holding aggregate/static user data
        self.baseline_file = self.base_dir / ".." / "local_memory" / "baseline.json"
        self.gaze_file = self.base_dir / ".." / "local_memory" / "gaze_pattern.json"
        self.profile_file = self.base_dir / ".." / "local_memory" / "user_profile.json"

        # Session variables
        self.session_id = f"{time.strftime('%Y%m%d_%H%M%S')}"
        self.timestamp_start = time.time()
        self.timestamp_end = None

        # Placeholders
        self.session_data = [] # Unused in current logic, can be removed or kept for future expansion
        # Raw gaze data collected during *this* session
        self.gaze_events = [] 
        
        # Loaded data
        self.baseline = {}
        self.gaze_patterns = {}
        self.user_profile = {}


    # ----------------------------------------
    # DATA LOGGING (NEW)
    # ----------------------------------------
    def log_gaze_event(self, x: float, y: float, event_type: str, duration: float, aoi: str = "unclassified"):
        """Logs a single gaze event captured during the current session."""
        self.gaze_events.append({
            "timestamp": time.time(),
            "x": x,
            "y": y,
            "event_type": event_type,  # e.g., "Fixation", "Saccade", "Dwell"
            "duration": duration,      # In seconds
            "aoi": aoi                 # Area of Interest, e.g., "Main Video", "Chat Window"
        })
        
    def log_emotion_event(self, emotion: str, confidence: float):
        """
        Logs a single emotion event to the in-memory list and potentially 
        to the master log file (emotion_log.json) for historical tracking.
        """
        # NOTE: For simplicity, we only log it to the master file here.
        # In a real system, you'd append this to emotion_log.json immediately.
        
        new_entry = {
            "timestamp": time.time(),
            "emotion": emotion,
            "confidence": confidence,
            "session_id": self.session_id, # Link back to this session
        }
        
        # --- (Add logic here to append 'new_entry' to self.memory_file) ---
        # For now, we assume the external system handles writing to memory_file
        # self.session_data.append(new_entry) # If we were using this list


    # ----------------------------------------
    # LOADERS (Previous implementation retained/updated)
    # ----------------------------------------
    def _load_json_file(self, file_path: Path):
        if file_path.exists():
            try:
                return json.loads(file_path.read_text())
            except:
                return {}
        return {}

    def load_baseline(self):
        self.baseline = self._load_json_file(self.baseline_file)

    def load_gaze_patterns(self):
        self.gaze_patterns = self._load_json_file(self.gaze_file)

    def load_user_profile(self):
        self.user_profile = self._load_json_file(self.profile_file)

    def load_session_logs(self):
        """Loads emotion logs only between session_start & session_end."""
        # Note: self.memory_file contains ALL emotion logs.
        logs = self._load_json_file(self.memory_file)
        
        if not logs or self.timestamp_end is None:
            return []

        session_logs = [
            entry for entry in logs
            if self.timestamp_start <= entry.get("timestamp", 0) <= self.timestamp_end
        ]
        return session_logs

    # ----------------------------------------
    # ANALYTICS (Retained)
    # ----------------------------------------
    def compute_session_summary(self, entries):
        # ... (Original implementation remains here) ...
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
        dominant = max(dist, key=dist.get)
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
        if self.timestamp_end is None:
             self.end_session()

        # Load contextual data
        self.load_baseline()
        self.load_gaze_patterns() 
        self.load_user_profile()
        
        # Process session data
        session_entries = self.load_session_logs()
        summary = self.compute_session_summary(session_entries)

        final_json = {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,

            "user_profile": self.user_profile,
            "baseline_emotions": self.baseline,
            "gaze_patterns_historical": self.gaze_patterns,

            "session_summary": summary,
            "emotion_stream": session_entries,
            "gaze_events_session_raw": self.gaze_events, # <--- THIS LIST NOW HOLDS THE DATA

            "notes": ""
        }

        if save:
            out_path = self.base_dir / f"session_{self.session_id}.json"
            # The current session data, including gaze_events, is now SAVED
            # in this session-specific file.
            out_path.write_text(json.dumps(final_json, indent=2))
            print(f"💾 Session JSON saved: {out_path}")

        return final_json
# import json
# import time
# from pathlib import Path
# from statistics import mode
# from collections import Counter

# class VisionSession:
#     def __init__(self, user_id="default_user"):
#         self.user_id = user_id

#         # Paths
#         self.base_dir = Path(__file__).resolve().parent
#         self.memory_file = self.base_dir / ".." / "local_memory" / "emotion_log.json"
#         self.baseline_file = self.base_dir / ".." / "local_memory" / "baseline.json"

#         # Session variables
#         self.session_id = f"{time.strftime('%Y%m%d_%H%M%S')}"
#         self.timestamp_start = time.time()
#         self.timestamp_end = None

#         # Placeholders
#         self.session_data = []
#         self.gaze_events = []      # you will fill later
#         self.baseline = {}

#     # ----------------------------------------
#     # LOADERS
#     # ----------------------------------------
#     def load_baseline(self):
#         if self.baseline_file.exists():
#             try:
#                 self.baseline = json.loads(self.baseline_file.read_text())
#             except:
#                 self.baseline = {}
#         else:
#             self.baseline = {}

#     def load_session_logs(self):
#         """Loads logs only between session_start & session_end."""
#         if not self.memory_file.exists():
#             return []

#         try:
#             logs = json.loads(self.memory_file.read_text())
#         except:
#             logs = []

#         session_logs = [
#             entry for entry in logs
#             if self.timestamp_start <= entry["timestamp"] <= self.timestamp_end
#         ]

#         return session_logs

#     # ----------------------------------------
#     # ANALYTICS
#     # ----------------------------------------
#     def compute_session_summary(self, entries):
#         if not entries:
#             return {
#                 "dominant_emotion": "neutral",
#                 "emotion_distribution": {},
#                 "most_intense_event": None
#             }

#         emotions = [e["emotion"] for e in entries]
#         dist = Counter(emotions)

#         total = sum(dist.values())
#         emotion_dist = {k: round(v / total, 3) for k, v in dist.items()}

#         # dominant
#         dominant = max(dist, key=dist.get)

#         # most intense
#         intense = max(entries, key=lambda x: x["confidence"])

#         most_intense = {
#             "emotion": intense["emotion"],
#             "confidence": intense["confidence"],
#             "timestamp": intense["timestamp"]
#         }

#         return {
#             "dominant_emotion": dominant,
#             "emotion_distribution": emotion_dist,
#             "most_intense_event": most_intense
#         }

#     # ----------------------------------------
#     # PUBLIC API
#     # ----------------------------------------
#     def end_session(self):
#         self.timestamp_end = time.time()

#     def generate_json(self, save=True):
#         self.load_baseline()
#         session_entries = self.load_session_logs()
#         summary = self.compute_session_summary(session_entries)

#         final_json = {
#             "user_id": self.user_id,
#             "session_id": self.session_id,
#             "timestamp_start": self.timestamp_start,
#             "timestamp_end": self.timestamp_end,

#             "baseline_emotions": self.baseline,

#             "session_summary": summary,
#             "emotion_stream": session_entries,
#             "gaze_events": self.gaze_events,

#             "notes": ""
#         }

#         if save:
#             out_path = self.base_dir / f"session_{self.session_id}.json"
#             out_path.write_text(json.dumps(final_json, indent=2))
#             print(f"💾 Session JSON saved: {out_path}")

#         return final_json
