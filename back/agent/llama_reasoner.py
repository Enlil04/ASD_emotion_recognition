# llama_reasoner.py
import ollama
import json
import re


class LlamaReasoner:
    def __init__(self, model_name="llama3.2"):
        self.model = model_name

    def think(self, context_data, user_prompt):
        system_instructions = """
            You are a Social Communication Coach for a user with ASD (Autism Spectrum Disorder).
            Your goal is to help the user interpret social situations and manage emotional regulation.

            You will be given:
            - user profile (name, triggers, preferences)
            - session memory (conversation summary, current goal, recent emotions)
            - emotion state (dominant, stability, uncertain, top2)
            - optional long-term trends (top emotions last 7 days)

            RESPONSE FORMAT:
            Return valid JSON with keys:
            {
            "thought_process": "...",
            "social_cue_interpretation": "...",
            "suggested_action": "offer_coping_strategy|continue_conversation|suggest_break|none",
            "speech_response": "..."
            }
            """

        user_name = context_data.get("user_name", "User")
        profile_triggers = ", ".join(context_data.get("triggers", [])) or "None known"

        memory_summary = context_data.get("memory_summary", "No recent history")
        session_state = context_data.get("session_state", {})
        emotion_state = context_data.get("emotion_state", {})
        top7 = context_data.get("top_emotions_7d", [])

        # fallbacks for old callers
        emotion = context_data.get("emotion", "unknown")
        gaze = context_data.get("gaze", "center")
        iris = context_data.get("iris", "normal")

        full_prompt = f"""
--- CURRENT CONTEXT ---
USER PROFILE:
- Name: {user_name}
- Triggers: {profile_triggers}

SESSION MEMORY:
- Conversation summary: {session_state.get("conversation_summary", memory_summary)}
- Current goal: {session_state.get("current_goal", None)}
- Recent emotions (short): {session_state.get("recent_emotions", [])}

EMOTION STATE (tool):
- face_detected: {emotion_state.get("face_detected", None)}
- dominant: {emotion_state.get("dominant", emotion)}
- stability: {emotion_state.get("stability", None)}
- uncertain: {emotion_state.get("uncertain", None)}
- top2: {emotion_state.get("top2", None)}

LONG-TERM TRENDS:
- top_emotions_7d: {top7}

VISUAL SENSORS (placeholders if not implemented):
- Gaze: {gaze}
- Iris/Stress Level: {iris}

USER INPUT/SCENARIO:
"{user_prompt}"

Respond ONLY in JSON.
"""

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_instructions.strip()},
                    {"role": "user", "content": full_prompt.strip()},
                ],
            )
            raw = response["message"]["content"]
            return self._parse_json_response(raw)

        except Exception as e:
            print(f"Brain Error: {e}")
            return {
                "speech_response": "I'm having trouble processing that, but I'm here with you.",
                "suggested_action": "none",
            }

    def _parse_json_response(self, text):
        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return {"speech_response": text, "suggested_action": "none"}
        except json.JSONDecodeError:
            return {"speech_response": text, "suggested_action": "none"}
