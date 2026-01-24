from reasoner import Reasoner
from emotion_tool import get_state  # your function name

# You must pass a function that returns emotion state dict
def get_emotion_state_fn():
    return get_state(summarizer)

reasoner = Reasoner(
    model="llama3.1",  # or your ollama reasoner model name
    get_emotion_state_fn=get_emotion_state_fn,
    session_manager=session_manager
)

result = reasoner.respond("I feel stressed.")
print(result["assistant_message"])
print(result["recommended_action"])
