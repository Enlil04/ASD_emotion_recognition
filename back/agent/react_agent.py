# The Strategist / Decision Maker.
""" 
Thought → Action → Observation → Thought → ...
This file decides what to do with the information. It uses the "ReAct" (Reason + Act) pattern.
"""

import json
from .llama_reasoner import LlamaReasoner
from .memory_manager import MemoryManager 

class AgenticBrain:
    def __init__(self):
        self.brain = LlamaReasoner(model_name="llama3.2")
        self.memory = MemoryManager()
    
    def decide_response(self, vision_data, user_text):
        """
        Orchestrates the ReAct Loop:
        1. CONTEXT: Gather Memory + Vision
        2. REASON: Ask Llama what to do (Think)
        3. ACT: Execute specific tools (e.g., enable focus mode)
        4. SAVE: Record the interaction
        """
        
        # 1. Retrieve Context
        user_profile = self.memory.load_profile()
        
        # Create the full picture for the brain
        context_snapshot = {
            **vision_data,
            "user_name": user_profile.get("name", "User"),
            "triggers": user_profile.get("triggers", []),
            "memory_summary": self.memory.get_recent_summary() #create this function in memory manager
        }
        
        # 2. Reason (Get structured plan from Llama)
        # Returns a dict: {"speech_response": "...", "suggested_action": "..."}
        plan = self.brain.think(context_snapshot, user_text)
        
        # Extract parts of the plan
        speech = plan.get("speech_response", "I am listening.")
        action = plan.get("suggested_action", "none")
        
        # 3. Act (Tool Execution)
        # This checks if the brain wanted to DO something, not just talk.
        action_result = self._execute_tool(action)
        
        # If an action was taken, maybe append that to the speech?
        if action_result:
            print(f"DEBUG: Executed Tool [{action}] -> {action_result}")
            # Optional: You could append "[Action Started]" to the text shown to user
        
        # 4. Save to Memory
        # We save what we SAID, not necessarily the internal JSON
        self.memory.save_interaction(user_text, speech, vision_data.get('emotion', 'unknown'))
        
        # Return just the speech to the UI (koog.py handles printing this)
        return speech

    def _execute_tool(self, action_name):
        """
        The 'Hands' of the agent. Executes code based on the 'action_name'.
        """
        action_name = action_name.lower().strip()
        
        if action_name == "offer_coping_strategy":
            # In a real app, this might trigger a specific UI screen
            return "TRIGGER_BREATHING_UI"
            
        elif action_name == "suggest_break":
            # Could dim the screen or silence notifications
            return "DIM_SCREEN_50%"
            
        elif action_name == "log_stress_event":
            # Force a log entry specifically for stress
            # self.memory.log_emotional_event("stress", confidence=1.0)
            return "LOGGED_STRESS"
            
        elif action_name == "none":
            return None
            
        else:
            return f"UNKNOWN_TOOL: {action_name}"
        
# from .llama_reasoner import LlamaReasoner
# from .memory_manger import MemoryManager # Assuming you fix the typo 'manger' to 'manager'

# class AgenticBrain:
#     def __init__(self):
#         self.brain = LlamaReasoner(model_name="llama3.2")
#         self.memory = MemoryManager()
    
#     def decide_response(self, vision_data, user_text):
#         """
#         Orchestrates the decision process:
#         1. Fetches memories
#         2. Merges memories with current vision data.
#         3. Asks Llama for a decision.
#         4. Saves the result.
#         """
#         # 1. Retrieve relevant past context
#         user_profile = self.memory.load_profile()
        
#         # 2. Merge vision data with profile
#         context_snapshot = {
#             **vision_data,
#             "user_name": user_profile.get("name"),
#             "memory_summary": self.memory.get_recent_summary()
#         }
        
#         # 3. Ask Llama 3.2 for the response
#         response = self.brain.think(context_snapshot, user_text)
        
#         # 4. Save this interaction to memory
#         self.memory.save_interaction(user_text, response, vision_data['emotion'])
        
#         return response