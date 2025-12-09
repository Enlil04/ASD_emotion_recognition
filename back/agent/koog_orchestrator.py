# The Conductor / Orchestrator.
# """ Here is the bridge
#     Koog:  Runs workflows, Connects tools, Controls execution graph
#     This is the entry point. It connects your "eyes" (cameras/sensors) to your "brain" (Llama). 
#  It runs the continuous cycle of life: Sense -> Think -> Act."""

# This is the main loop that ties your vision models to the agent. 

# STILLL NEEDS THOUGHTS


import time
import sys
import os
import json
import subprocess
import threading
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from agent.react_agent import AgenticBrain
CURRENT_DIR = Path(__file__).parent
VISION_DIR = CURRENT_DIR.parent / "analytics" / "vision_models"
DETECTOR_SCRIPT = VISION_DIR / "emotion_detector.py"
LOG_FILE = VISION_DIR / "local_memory" / "emotion_log.json"


# This mimics what the Flutter App would send to the backend
app_state = {
    "current_activity": "idle",      
    "last_event": None,               
    "active_session": True,
    "user_typed_message": None        
}

class VisionBridge:
    #Launches emotion_detector.py as a background process and reads its JSON logs.
    def __init__(self):
        self.process = None
        self.ensure_vision_system_running()

    def ensure_vision_system_running(self):
        if not DETECTOR_SCRIPT.exists():
            print(f"CRITICAL: Vision script not found at {DETECTOR_SCRIPT}")
            return
        
        print(f"Launching Vision System...")
        # Uses the same python interpreter to run the detector
        self.process = subprocess.Popen([sys.executable, str(DETECTOR_SCRIPT)])
        time.sleep(3) # Warmup time for camera

    def detect_latest_frame(self):
        #Reads the last known emotion from the shared JSON file
        if not LOG_FILE.exists(): return "neutral"
        try:
            text_data = LOG_FILE.read_text()
            if not text_data: return "neutral"
            
            data = json.loads(text_data)
            if not data: return "neutral"
            
            # Return the most recent entry
            return data[-1].get("detected_emotion", "neutral")
        except:
            return "neutral"

    def kill(self):
        if self.process: 
            self.process.terminate()
            print("Vision System closed.")

def input_listener():
    #Listens for keyboard input to simulate:
    
    print("\n--- SIMULATION CONTROLS ---")
    print(" [TYPE TEXT]: Simulates user talking to AI")
    print(" 'g' -> Event: User starts Game")
    print(" 'f' -> Event: User FAILS level")
    print(" 'w' -> Event: User WINS level")
    print(" 'exit' -> Quit System")
    print("---------------------------\n")
    
    while app_state["active_session"]:
        user_in = input() # Blocking wait
        # hard coded for now
        if user_in.lower() in ['exit', 'quit']:
            app_state["active_session"] = False
            break
        elif user_in == 'g':
            app_state["current_activity"] = "playing_memory_game"
            app_state["last_event"] = "game_started"
            print("📱 APP: Game Started")
        elif user_in == 'f':
            app_state["last_event"] = "level_failed"
            print("📱 APP: Level Failed")
        elif user_in == 'w':
            app_state["last_event"] = "level_complete"
            print("📱 APP: Level Won")
        else:
            # Treat anything else as a direct chat message
            app_state["user_typed_message"] = user_in

# --- MAIN ORCHESTRATOR LOOP ---
def main_loop():
    print("Starting Orchestrator (Body)...")
    
    # 1. Initialize the Mind
    print("Loading Agentic Brain (Llama 3.2)...")
    try:
        brain = AgenticBrain()
        print("Brain Loaded.")
    except Exception as e:
        print(f"Failed to load Brain: {e}")
        brain = None

    # 2. Initialize the Eyes
    eyes = VisionBridge()

    # 3. Start Input Listener (Thread)
    input_thread = threading.Thread(target=input_listener, daemon=True)
    input_thread.start()

    # Tracking variables for triggers
    consecutive_negative_frames = 0
    
    try:
        while app_state["active_session"]:
            # --- PHASE 1: SENSE (Gather Data) ---
            current_emotion = eyes.detect_latest_frame()
            activity = app_state["current_activity"]
            event = app_state["last_event"]
            user_msg = app_state["user_typed_message"]

            # Reset transient states
            if event: app_state["last_event"] = None
            if user_msg: app_state["user_typed_message"] = None

            # --- PHASE 2: EVALUATE TRIGGERS ---
            trigger_reason = None
            prompt_text = ""

            # Trigger A: User Typed Something
            if user_msg:
                trigger_reason = "user_chat"
                prompt_text = user_msg

            # Trigger B: App Event (Win/Fail)
            elif event == "level_failed":
                trigger_reason = "app_event"
                # We translate the event into a sentence for the LLM
                prompt_text = f"System Alert: The user just failed a difficult level in {activity}."
            
            elif event == "level_complete":
                trigger_reason = "app_event"
                prompt_text = f"System Alert: The user just won the level in {activity}!"

            # Trigger C: Emotional Persistence (Behavioral)
            # If user is NOT idle, and looks negative for ~5 seconds
            elif activity != "idle" and current_emotion in ["anger", "sad", "fear"]:
                consecutive_negative_frames += 1
                if consecutive_negative_frames > 15: # 15 cycles * 0.5s sleep = ~7.5 seconds
                    trigger_reason = "emotion_pattern"
                    prompt_text = f"System Alert: The user has looked {current_emotion} for several seconds while {activity}. They may be struggling."
                    consecutive_negative_frames = 0 # Reset so we don't spam
            else:
                consecutive_negative_frames = 0 # Reset if they smile or look neutral

            # --- PHASE 3: THINK & ACT (If Triggered) ---
            if trigger_reason and brain:
                print(f"\nTRIGGER: {trigger_reason} | Emotion: {current_emotion}")
                
                # 1. Construct the Vision/Context Packet for react_agent.py
                vision_packet = {
                    "emotion": current_emotion,
                    "gaze": "screen_center", # Placeholder for iris data
                    "iris": "normal",
                    "timestamp": time.time()
                }

                # 2. Call the ReAct Agent
                response_speech = brain.decide_response(vision_packet, prompt_text)
                
                # 3. Output the Result
                print(f"COMPANION: \"{response_speech}\"")
                print("------------------------------------------------")

            
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        eyes.kill()
        app_state["active_session"] = False

if __name__ == "__main__":
    main_loop()