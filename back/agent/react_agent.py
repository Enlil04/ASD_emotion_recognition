#Here is the core logic which implement reAct loop
# Thought → Action → Observation → Thought → ...
#This file decides what to do with the information. It uses the "ReAct" (Reason + Act) pattern.



from .llama_reasoner import LlamaReasoner
from .memory_manger import MemoryManager # Assuming you fix the typo 'manger' to 'manager'

class AgenticBrain:
    def __init__(self):
        self.brain = LlamaReasoner(model_name="llama3.2")
        self.memory = MemoryManager()
    
    def decide_response(self, vision_data, user_text):
        """
        Orchestrates the decision process:
        1. Read Memory
        2. Analyze Vision Data
        3. Generate Response
        """
        # 1. Retrieve relevant past context
        user_profile = self.memory.load_profile()
        
        # 2. Merge vision data with profile
        context_snapshot = {
            **vision_data,
            "user_name": user_profile.get("name"),
            "memory_summary": self.memory.get_recent_summary()
        }
        
        # 3. Ask Llama 3.2 for the response
        response = self.brain.think(context_snapshot, user_text)
        
        # 4. Save this interaction to memory
        self.memory.save_interaction(user_text, response, vision_data['emotion'])
        
        return response