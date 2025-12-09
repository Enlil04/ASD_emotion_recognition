# The Brain (LLM Wrapper)
"""The Interpreter / Social Coach. This wraps the raw Ollama API. It translates the "computer" data (JSON) into "human" context for the LLM"""
import ollama
import json
import re

class LlamaReasoner:
    def __init__(self, model_name="llama3.2"):
        self.model = model_name

    def think(self, context_data, user_prompt):
        """
        Sends vision data and user context to Llama to generate a structured JSON response.
        """
        
        # 1. CONSTRUCT THE PERSONA & TASK
        # We tell Llama it is a "Social Communication Coach" specifically for ASD.
        system_instructions = """
        SYSTEM: You are a Social Communication Coach for a user with ASD (Autism Spectrum Disorder).
        Your goal is to help the user interpret social situations and manage emotional regulation.

        INPUT DATA ANALYSIS:
        1. Compare 'User Emotion' with the 'User Prompt' context. Are they congruent?
        2. Look at 'Gaze Direction'. Is the user avoiding eye contact during a conversation?
        3. Check 'User Profile' for known triggers (e.g., loud noises, sarcasm).

        RESPONSE FORMAT:
        You must respond in valid JSON format with the following keys:
        {
            "thought_process": "Analyze the social dynamic here. Is the user stressed?",
            "social_cue_interpretation": "Explain what is happening socially (e.g., 'They are joking').",
            "suggested_action": "One specific action (e.g., 'offer_coping_strategy', 'continue_conversation', 'suggest_break')",
            "speech_response": "The actual text to say to the user (warm, clear, and direct)."
        }
        """

        # 2. FORMAT THE DYNAMIC CONTEXT
        # We handle "None" values gracefully so the LLM doesn't get confused.
        user_name = context_data.get('user_name', 'User')
        profile_triggers = ", ".join(context_data.get('triggers', [])) or "None known"
        #This is where the "Live Data" meets the "Static Instructions." It fills in the blanks with the data from the koog_orchestrator.
        full_prompt = f"""
        {system_instructions}

        --- CURRENT CONTEXT ---
        USER PROFILE:
        - Name: {user_name}
        - Triggers: {profile_triggers}
        - Recent Memory: {context_data.get('memory_summary', 'No recent history')} #reAct is creating this file

        VISUAL SENSORS:
        - Emotion: {context_data.get('emotion', 'unknown')}
        - Gaze: {context_data.get('gaze', 'center')}
        - Iris/Stress Level: {context_data.get('iris', 'normal')}

        USER INPUT/SCENARIO:
        "{user_prompt}"
        
        Respond ONLY in JSON.
        """

        try:
            # 3. CALL OLLAMA
            response = ollama.chat(model=self.model, messages=[
                {'role': 'user', 'content': full_prompt},
            ])
            
            raw_content = response['message']['content']
            
            # 4. PARSE THE JSON
            # Llama might sometimes wrap JSON in ```json ... ``` blocks, so we clean it.
            return self._parse_json_response(raw_content)

        except Exception as e:
            # Fallback if the brain fails
            print(f"Brain Error: {e}")
            return {
                "speech_response": "I'm having trouble processing that, but I'm here with you.",
                "suggested_action": "none"
            }

    def _parse_json_response(self, text):
        """
        Helper to extract valid JSON from the LLM's output.
        """
        try:
            # Attempt to find the first '{' and last '}'
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                json_str = match.group(0)
                return json.loads(json_str)
            else:
                # If no JSON found, treat the whole text as speech
                return {"speech_response": text, "suggested_action": "none"}
        except json.JSONDecodeError:
             return {"speech_response": text, "suggested_action": "none"}

# import ollama

# class LlamaReasoner:
#     def __init__(self, model_name="llama3.2"):
#         self.model = model_name

#     def think(self, context_data, prompt):
#         """
#         Sends vision data and user context to Llama 3.2 to generate a thought/response.
#         """
#         # here is the prompt the Llama uses to think
#         full_prompt = f"""
#         SYSTEM: You are an empathetic AI assistant on a mobile device.
        
#         CURRENT VISUAL CONTEXT:
#         - User Emotion: {context_data.get('emotion', 'unknown')}
#         - Gaze Direction: {context_data.get('gaze', 'center')}
#         - Iris Status: {context_data.get('iris', 'normal')}
        
#         USER PROFILE:
#         - Name: {context_data.get('user_name', 'User')}
#         - Recent Topics: {context_data.get('memory_summary', 'None')}

#         TASK: {prompt}
        
#         Respond naturally, acknowledging their emotional state implicitly (e.g., if sad, be gentle).
#         """

#         try:
#             response = ollama.chat(model=self.model, messages=[
#                 {'role': 'user',
#                  'content': full_prompt},
#             ])
#             return response['message']['content']
#         except Exception as e:
#             return f"Error connecting to brain: {e}"