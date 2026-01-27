import json
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class LlamaReasoner:
    def __init__(self, model_name="llama3.2"):
        # 1. Connect to Local Ollama
        self.llm = ChatOllama(
            model=model_name,
            temperature=0.3,
            format="json", 
            base_url="http://localhost:11434"
        )

        # 2. Define the Prompt Template
        # Note: I added specific instructions to "Avoid generic questions"
        self.prompt = PromptTemplate(
            template="""
            You are Nimi, an empathetic companion for an ASD individual.
            
            CONTEXT:
            User Name: {user_name}
            Triggers: {triggers}
            Conversation History: {conversation_summary}
            Current Goal: {current_goal}
            
            SENSORS:
            Dominant Emotion: {dominant_emotion}
            Stability: {stability}
            Face Detected: {face_detected}
            Gaze: {gaze}
            Iris: {iris}
            Recent Emotions: {recent_emotions}
            Top 7 Days: {top7_emotions}

            USER INPUT:
            "{user_input}"

            TASK:
            Analyze the input and context. Stay on topic. Do not aggressively change the subject.
            Respond in valid JSON:
            {{
                "thought_process": "brief reasoning...",
                "social_cue_interpretation": "what the sensors imply...",
                "suggested_action": "none or offer_coping_strategy",
                "speech_response": "natural response (max 2 sentences)..."
            }}
            """,
            input_variables=[
                "user_name", "triggers", "conversation_summary", "current_goal",
                "dominant_emotion", "stability", "face_detected", "gaze", "iris",
                "recent_emotions", "top7_emotions", "user_input"
            ]
        )

        self.parser = JsonOutputParser()
        self.chain = self.prompt | self.llm | self.parser

    # --- FIX: Indentation is now correct (inside the class) ---
    def think(self, context_data, user_prompt):
        print("🧠 1. Brain thinking...")
        
        # Safely extract nested dictionaries
        session_state = context_data.get("session_state", {})
        emotion_state = context_data.get("emotion_state", {})

        # --- FIX: Build the History String Correctly ---
        # If we have a list of messages, format them. Otherwise use the summary.
        history_list = session_state.get("chat_history", [])
        if history_list and isinstance(history_list, list):
            # Take last 5 interactions to keep context fresh
            history_str = "\n".join([f"{m.get('role','unknown')}: {m.get('content','')}" for m in history_list[-5:]])
        else:
            history_str = session_state.get("conversation_summary", "No recent history.")

        # --- FIX: "Crash Proof" Payload ---
        # We ensure EVERY variable in the prompt template has a value here.
        payload = {
            "user_name": str(context_data.get("user_name", "User")),
            "triggers": str(context_data.get("triggers", "None")),
            "conversation_summary": history_str, 
            "current_goal": str(session_state.get("current_goal", "Supportive Conversation")),
            "dominant_emotion": str(emotion_state.get("dominant", "neutral")),
            "stability": str(emotion_state.get("stability", "stable")),
            "face_detected": str(emotion_state.get("face_detected", "false")),
            "gaze": str(context_data.get("gaze", "center")),
            "iris": str(context_data.get("iris", "normal")),
            "recent_emotions": str(session_state.get("recent_emotions", [])),
            "top7_emotions": str(context_data.get("top_emotions_7d", "No data")),
            "user_input": str(user_prompt)
        }

        try:
            # Invoke the chain
            response = self.chain.invoke(payload)
            
            # Robustness: Handle string response if JSON parsing fails slightly
            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except:
                    # Fallback if LLM outputs garbage
                    return {
                        "speech_response": response,
                        "suggested_action": "none"
                    }
            
            return response

        except Exception as e:
            print(f"❌ Brain Error: {e}")
            # Return a valid dict so the app doesn't hang
            return {
                "thought_process": "Error in reasoning engine",
                "speech_response": "I'm having a little trouble connecting to my thoughts right now. Can you say that again?",
                "suggested_action": "none"
            }