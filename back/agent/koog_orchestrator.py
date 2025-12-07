# Here is the bridge
# Koog: 
# Runs workflows
# Connects tools
# Controls execution graph
# Think of this as the conductor.

#This is the main loop that ties your vision models to the agent. This script runs the "Sense -> Think -> Act" loop.

import time
import sys
import os

# Add parent directory to path to import sibling modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from agent.react_agent import AgenticBrain
from analytics.vision_models.emotion_detector import EmotionDetector
# Assuming you have a gaze detector class similarly
# from analytics.vision_models.gaze_detector import GazeDetector

def main_loop():
    print("--- Starting Agentic Orchestrator (Python Prototype) ---")
    
    # Initialize Modules
    brain = AgenticBrain()
    eyes = EmotionDetector() # Your vision model class
    
    try:
        while True:
            # 1. SENSE: Get data from Vision Models
            # specific implementation depends on your vision_models code
            current_emotion = eyes.detect_latest_frame() 
            current_gaze = "looking_at_screen" # Placeholder for your iris code
            
            vision_packet = {
                "emotion": current_emotion,
                "gaze": current_gaze,
                "timestamp": time.time()
            }
            
            # 2. TRIGGER: Did the user say something? (Simulated input for now)
            # In a real app, this waits for microphone input or text input
            user_input = input("User (You): ") 
            
            if user_input.lower() in ['exit', 'quit']:
                break
                
            # 3. THINK & ACT: Pass vision + text to Llama
            print(f"DEBUG: Processing with Emotion={current_emotion}...")
            response = brain.decide_response(vision_packet, user_input)
            
            # 4. RESPOND
            print(f"Agent: {response}")
            print("------------------------------------------------")

    except KeyboardInterrupt:
        print("\nShutting down agent...")

if __name__ == "__main__":
    main_loop()