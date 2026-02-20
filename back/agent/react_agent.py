
"""
AGENTIC BRAIN (THE MANAGER)
---------------------------
This module implements the ReAct loop. It aggregates context from all sensors 
and memory systems, queries the LLM for a decision, executes the resulting 
tools (actions), and logs the interaction to the database for future recall.
"""

from agent.llama_reasoner import LlamaReasoner
from agent.memory_manager import MemoryManager

class AgenticBrain:
    def __init__(self, db_path: str = None, user_id: str = "user_001"):
        self.brain = LlamaReasoner(model_name="llama3.2")
        self.memory = MemoryManager(db_path=db_path, user_id=user_id)

    def decide_response(self, vision_data: dict, prompt_text: str = None, extra_context: dict = None):
        """
        Main entry point for the server to ask for a response.
        """
        # 1. Load User Profile & Memory
        user_profile = self.memory.load_profile()
        
        # 2. Extract Emotion
        detected_emotion = vision_data.get("emotion", "Neutral") if isinstance(vision_data, dict) else "Neutral"
        face_detected = vision_data.get("face_detected", False)

        # 3. Determine User Input Context
        if prompt_text:
            user_text = prompt_text
            # Internal context helps the AI know the user's emotion while they typed
            internal_context_string = f"User said: '{prompt_text}'. (Visual context: User looks {detected_emotion})"
        else:
            user_text = f"[Silent Visual Event: {detected_emotion}]"
            internal_context_string = f"User is silent. Observed emotion: {detected_emotion}."

        # 4. Build the "Rich Context" (Enriched Payload)
        # This matches the structure expected by LlamaReasoner.think()
        context_snapshot = {
            "user_name": user_profile.get("name", "User"),
            "triggers": user_profile.get("triggers", []),
            
            # Raw sensor data passed through
            "gaze": vision_data.get("gaze", "center"),
            "iris": vision_data.get("iris", "normal"),
            "top_emotions_7d": extra_context.get("top_emotions_7d", "No recent data") if extra_context else "No data",

            # Structured states
            "session_state": {
                # FETCH HISTORY FROM DB HERE so the agent isn't "stupid"
                "chat_history": self.memory.get_recent_interactions(limit=10),
                "conversation_summary": self.memory.get_recent_summary(),
                "recent_emotions": [detected_emotion] 
            },
            "emotion_state": {
                "dominant": detected_emotion,
                "face_detected": face_detected,
                "stability": "stable" # You can calculate this based on variance later
            }
        }

        # 5. Think (Call the corrected LlamaReasoner)
        print(f"🤔 Asking Llama with mood: {detected_emotion}")
        plan = self.brain.think(context_snapshot, internal_context_string)

        speech = plan.get("speech_response", "I am listening.")
        action = plan.get("suggested_action", "none")

        # 6. Execute Tools (if any)
        action_result = self._execute_tool(action)
        if action_result:
            print(f"⚙️ Tool Triggered: {action} -> {action_result}")

        # 7. Save the interaction in SQLite (Critical for memory!)
        self.memory.save_interaction(user_text, speech, detected_emotion)

        return speech

    def _execute_tool(self, action_name):
        action_name = (action_name or "").lower().strip()

        if action_name == "offer_coping_strategy":
            return "TRIGGER_BREATHING_UI"
        elif action_name == "suggest_break":
            return "DIM_SCREEN_50%"
        elif action_name == "log_stress_event":
            self.memory.log_emotional_event("stress", confidence=1.0)
            return "LOGGED_STRESS"
        elif action_name in ("none", ""):
            return None
        else:
            return f"UNKNOWN_TOOL: {action_name}"