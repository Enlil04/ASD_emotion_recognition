# The Memory Manager / Long-term Storage.
"Storage / Long-term Memory. Note: Your file content was empty/pseudocode."
" For an ASD user, memory is vital for tracking triggers and successful coping strategies over time."
import json
import os
import time
from datetime import datetime

class MemoryManager:
    def __init__(self):
        # 1. Define paths relative to this script (back/agent/memory_manager.py)
        # We go '..' to get to 'back/', then into 'analytics/local_memory'
        base_dir = os.path.dirname(__file__)
        self.memory_dir = os.path.join(base_dir, '..', 'analytics', 'local_memory')
        
        # 2. Map to your EXISTING files shown in the screenshot
        self.profile_path = os.path.join(self.memory_dir, "user_profile.json")
        self.emotion_log_path = os.path.join(self.memory_dir, "emotion_log.json")
        self.gaze_path = os.path.join(self.memory_dir, "gaze_pattern.json")
        self.baseline_path = os.path.join(self.memory_dir, "baseline.json")

    def _read_json(self, path):
        """Helper to read JSON safely. Returns empty dict/list if file is missing/empty."""
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                return data
        except json.JSONDecodeError:
            return {} # Return empty if file is corrupt or empty

    def _write_json(self, path, data):
        """Helper to write JSON safely."""
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error writing to {path}: {e}")


    def load_profile(self):
        """
        Reads from your existing 'user_profile.json'.
        Returns the user's name, triggers, and preferences.
        """
        data = self._read_json(self.profile_path)
        # If the file is empty, return a default fallback so the app doesn't crash
        if not data:
            return {"name": "User", "preferences": {}, "triggers": []}
        return data

    def load_baseline(self):
        """Reads 'baseline.json' to understand the user's 'normal' state."""
        return self._read_json(self.baseline_path)

    def save_interaction(self, user_text, agent_response, detected_emotion):
        """
        Appends the new interaction to 'emotion_log.json'.
        """
        # Load existing log
        log_data = self._read_json(self.emotion_log_path)
        
        # If log_data is a list, append. If it's a dict, we might need to adjust structure.
        # Assuming it's a list of events:
        if not isinstance(log_data, list):
            log_data = []

        new_entry = {
            "timestamp": time.time(),
            "readable_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": "conversation",
            "user_input": user_text,
            "agent_response": agent_response,
            "detected_emotion": detected_emotion
        }

        log_data.append(new_entry)
        
        # Optional: Keep log size manageable (last 100 entries)
        if len(log_data) > 100:
            log_data = log_data[-100:]

        self._write_json(self.emotion_log_path, log_data)

    def get_recent_summary(self, limit=3):
        """
        Reads the last few entries from 'emotion_log.json' to give context to Llama.
        """
        log_data = self._read_json(self.emotion_log_path)
        
        if not log_data or not isinstance(log_data, list):
            return "No recent interactions."

        # Get last 'limit' items
        recent_items = log_data[-limit:]
        summary = []
        
        for item in recent_items:
            # Safely get fields in case your log format varies
            u_text = item.get("user_input", "")
            a_text = item.get("agent_response", "")
            emo = item.get("detected_emotion", "unknown")
            summary.append(f"- User ({emo}): {u_text} | Agent: {a_text}")
            
        return "\n".join(summary)
    
    
def log_emotional_event(self, emotion, confidence=1.0):
        """
        Logs a passive emotional observation (e.g., camera sees 'Sad' 
        but user hasn't said anything).
        """
        # Load existing log
        log_data = self._read_json(self.emotion_log_path)
        if not isinstance(log_data, list):
            log_data = []

        new_entry = {
            "timestamp": time.time(),
            "readable_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "hour": datetime.now().hour,  # Save hour specifically for pattern matching
            "event_type": "observation",  # Distinct from 'conversation'
            "detected_emotion": emotion,
            "confidence": confidence
        }

        log_data.append(new_entry)
        
        # Keep log size manageable
        if len(log_data) > 500: # Keep more observations than conversations
            log_data = log_data[-500:]

        self._write_json(self.emotion_log_path, log_data)


def find_patterns(self):
        """
        Analyzes emotion_log.json to find simple triggers/patterns.
        Returns a string summary of findings.
        """
        log_data = self._read_json(self.emotion_log_path)
        if not log_data:
            return "No data to analyze."

        # simple counter: { 16: {'anxious': 5, 'happy': 1}, 17: ... }
        hour_map = {} 

        for entry in log_data:
            # We only care about negative emotions for triggers
            emotion = entry.get("detected_emotion", "neutral")
            if emotion in ["contempt", "sad", "fear", "angry", "disgust"]:
                # Parse the hour if we didn't save it explicitly before
                if "hour" in entry:
                    hour = entry["hour"]
                else:
                    # Fallback for old data
                    dt = datetime.strptime(entry["readable_time"], "%Y-%m-%d %H:%M:%S")
                    hour = dt.hour
                
                if hour not in hour_map:
                    hour_map[hour] = {}
                hour_map[hour][emotion] = hour_map[hour].get(emotion, 0) + 1

        # Generate insights
        insights = []
        for hour, counts in hour_map.items():
            top_emotion = max(counts, key=counts.get)
            count = counts[top_emotion]
            if count >= 3: # Threshold to call it a "pattern"
                insights.append(f"Trend: You tend to feel {top_emotion} around {hour}:00 ({count} times).")

        if not insights:
            return "No strong patterns detected yet."
        
        return "\n".join(insights)


# Simple test to run this file directly
if __name__ == "__main__":
    mm = MemoryManager()
    print("Profile:", mm.load_profile())
    print("\nBaseline:", mm.load_baseline())
# Simulate a few events to test pattern recognition
    print("Logging simulated events...")
    mm.log_emotional_event("anxious") 
    mm.log_emotional_event("anxious") 
    mm.log_emotional_event("anxious") 
    
    print("\n--- Recent Context ---")
    print(mm.get_recent_summary())
    
    print("\n--- Pattern Analysis ---")
    print(mm.find_patterns())
    #how to implement:
    # Use JSON or simple text files to store user profiles and interaction logs.
    # Trigger Mapping: Create a function log_emotional_event(emotion, time). Over time, the agent can learn patterns (e.g., "You tend to get anxious around 4 PM")