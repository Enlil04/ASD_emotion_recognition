
from tools.emotion_tool import get_emotion_state
from emotion_detector import summarizer, session_manager
from reasoner import Reasoner


# dummy wrappers (replace with your real objects)
def get_emotion_state_fn():
    return get_emotion_state(summarizer)

reasoner = Reasoner(
    model="llama3.2:3b",
    get_emotion_state_fn=get_emotion_state_fn,
    
)

while True:
    txt = input("You: ")
    if txt.lower() in {"q", "quit"}:
        break

    out = reasoner.respond(txt)
    print("\nRAW JSON:\n", out)
    print("\nAssistant says:", out["assistant_message"])
    print("Action:", out["recommended_action"])
