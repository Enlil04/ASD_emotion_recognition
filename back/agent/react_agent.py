from llama_reasoner import LlamaReasoner
from memory_manager import MemoryManager


class AgenticBrain:
    def __init__(self, db_path: str = "memory.db", user_id: str = "user_001"):
        self.brain = LlamaReasoner(model_name="llama3.2")
        self.memory = MemoryManager(db_path=db_path, user_id=user_id)

    def decide_response(self, vision_data, user_text, extra_context: dict | None = None):
        """
        Context sources:
        - vision_data: basic sensors (emotion/gaze/iris/timestamp)
        - MemoryManager(SQLite): profile + recent conversation summary (interactions)
        - extra_context: session_state/emotion_state/top_emotions_7d (from tool + session + SQLite)
        """

        user_profile = self.memory.load_profile()

        context_snapshot = {
            **(vision_data or {}),
            "user_name": user_profile.get("name", "User"),
            "triggers": user_profile.get("triggers", []),
            "memory_summary": self.memory.get_recent_summary(),
        }

        if extra_context and isinstance(extra_context, dict):
            context_snapshot.update(extra_context)

        plan = self.brain.think(context_snapshot, user_text)

        speech = plan.get("speech_response", "I am listening.")
        action = plan.get("suggested_action", "none")

        action_result = self._execute_tool(action)
        if action_result:
            print(f"DEBUG: Executed Tool [{action}] -> {action_result}")

        # Save the interaction in SQLite
        detected_emotion = vision_data.get("emotion", "unknown") if isinstance(vision_data, dict) else "unknown"
        self.memory.save_interaction(user_text, speech, detected_emotion)

        return speech

    def _execute_tool(self, action_name):
        action_name = (action_name or "").lower().strip()

        if action_name == "offer_coping_strategy":
            return "TRIGGER_BREATHING_UI"
        elif action_name == "suggest_break":
            return "DIM_SCREEN_50%"
        elif action_name == "log_stress_event":
            # Optional: also log a special event
            self.memory.log_emotional_event("stress", confidence=1.0)
            return "LOGGED_STRESS"
        elif action_name in ("none", ""):
            return None
        else:
            return f"UNKNOWN_TOOL: {action_name}"
