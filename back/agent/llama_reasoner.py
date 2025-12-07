# This Wraps Llama

import ollama

class LlamaReasoner:
    def __init__(self, model_name="llama3.2"):
        self.model = model_name

    def think(self, context_data, prompt):
        """
        Sends vision data and user context to Llama 3.2 to generate a thought/response.
        """
        # here is the prompt the Llama uses to think
        full_prompt = f"""
        SYSTEM: You are an empathetic AI assistant on a mobile device.
        
        CURRENT VISUAL CONTEXT:
        - User Emotion: {context_data.get('emotion', 'unknown')}
        - Gaze Direction: {context_data.get('gaze', 'center')}
        - Iris Status: {context_data.get('iris', 'normal')}
        
        USER PROFILE:
        - Name: {context_data.get('user_name', 'User')}
        - Recent Topics: {context_data.get('memory_summary', 'None')}

        TASK: {prompt}
        
        Respond naturally, acknowledging their emotional state implicitly (e.g., if sad, be gentle).
        """

        try:
            response = ollama.chat(model=self.model, messages=[
                {'role': 'user',
                 'content': full_prompt},
            ])
            return response['message']['content']
        except Exception as e:
            return f"Error connecting to brain: {e}"