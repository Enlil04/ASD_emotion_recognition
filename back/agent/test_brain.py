"""
BRAIN DIAGNOSTICS
-----------------
A standalone test script to measure LLM latency and verify reasoning logic 
without initializing the full sensor pipeline. Use this to benchmark 
performance and debug the AI's personality.
"""
import time
from llama_reasoner import LlamaReasoner

def test_brain_latency():
    print("--- Testing Llama 3.2 Latency ---")
    agent = LlamaReasoner(model_name="llama3.2")

    test_inputs = [ 
        {
            "context": {
                "user_name": "User",
                "triggers": [],
                "emotion": "Happy",
                "emotion_state": {"dominant": "Happy", "stability": 0.9, "uncertain": False, "face_detected": True},
                "session_state": {"conversation_summary": "User was discussing a game.", "current_goal": None, "recent_emotions": []},
                "top_emotions_7d": [("Happy", 12), ("Neutral", 7)],
            },
            "prompt": "I just got a promotion!"
        },
        {
            "context": {
                "user_name": "User",
                "triggers": [],
                "emotion": "Sad",
                "emotion_state": {"dominant": "Sad", "stability": 0.8, "uncertain": False, "face_detected": True},
                "session_state": {"conversation_summary": "User seemed tired today.", "current_goal": None, "recent_emotions": []},
                "top_emotions_7d": [("Sad", 10), ("Neutral", 6)],
            },
            "prompt": "I dropped my ice cream."
        },
        {
            "context": {
                "user_name": "User",
                "triggers": [],
                "emotion": "Anger",
                "emotion_state": {"dominant": "Anger", "stability": 0.9, "uncertain": False, "face_detected": True},
                "session_state": {"conversation_summary": "ended a game", "current_goal": None, "recent_emotions": []},
                "top_emotions_7d": [("Anger", 12), ("Neutral", 7)],
            },
            "prompt": "hi"
        },

        {
            "context": {
                "user_name": "User",
                "triggers": [],
                "emotion": "Fear",
                "emotion_state": {"dominant": "Fear", "stability": 0.9, "uncertain": False, "face_detected": True},
                "session_state": {"conversation_summary": "just launched the app.", "current_goal": None, "recent_emotions": []},
                "top_emotions_7d": [("Fear", 12), ("Neutral", 7)],
            },
            "prompt": "hi im scared"
        }
    ]

    for test in test_inputs:
        start = time.time()
        print(f'\nUser: {test["prompt"]} (Emotion: {test["context"].get("emotion")})')

        response = agent.think(test["context"], test["prompt"])

        dur = time.time() - start
        print(f"Agent: {response}")
        print(f"⏱️ Time taken: {dur:.2f}s")

if __name__ == "__main__":
    test_brain_latency()
