# back/agent/test_brain.py
import time
from llama_reasoner import LlamaReasoner

def test_brain_latency():
    print("--- Testing Llama 3.2 3B Latency ---")
    agent = LlamaReasoner(model_name="llama3.2")
    
    test_inputs = [
        {"context": {"emotion": "happy"}, "prompt": "I just got a promotion!"},
        {"context": {"emotion": "sad"}, "prompt": "I dropped my ice cream."},
    ]

    for test in test_inputs:
        start_time = time.time()
        print(f"\nUser: {test['prompt']} (Emotion: {test['context']['emotion']})")
        
        response = agent.think(test['context'], test['prompt'])
        
        duration = time.time() - start_time
        print(f"Agent: {response}")
        print(f"⏱️ Time taken: {duration:.2f} seconds")

if __name__ == "__main__":
    test_brain_latency()