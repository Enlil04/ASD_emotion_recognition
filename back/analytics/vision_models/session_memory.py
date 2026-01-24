from dataclasses import dataclass, field
from typing import List, Optional
import time

@dataclass
class EmotionSnapshot:
    timestamp: float
    dominant: Optional[str]
    stability: float
    uncertain: bool

@dataclass
class SessionMemory:
    conversation_summary: str = ""
    current_goal: Optional[str] = None
    recent_emotions: List[EmotionSnapshot] = field(default_factory=list)


class SessionMemoryManager:
    def __init__(self, emotion_window_sec: float = 60.0):
        self.memory = SessionMemory()
        self.emotion_window_sec = emotion_window_sec

    # -------- Emotion memory --------
    def update_emotion(self, emotion_summary):
        if emotion_summary is None:
            return

        snap = EmotionSnapshot(
            timestamp=emotion_summary.timestamp,
            dominant=emotion_summary.dominant,
            stability=emotion_summary.stability,
            uncertain=emotion_summary.uncertain
        )

        self.memory.recent_emotions.append(snap)

        # keep only last N seconds
        cutoff = time.time() - self.emotion_window_sec
        self.memory.recent_emotions = [
            e for e in self.memory.recent_emotions if e.timestamp >= cutoff
        ]

    # -------- Conversation summary --------
    def update_conversation_summary(self, new_summary: str):
        """
        This should be written by the AGENT, not heuristics.
        """
        self.memory.conversation_summary = new_summary.strip()

    # -------- Goal tracking --------
    def set_goal(self, goal: Optional[str]):
        self.memory.current_goal = goal.strip() if goal else None

    # -------- Read-only for agent --------
    def get_state(self) -> dict:
        return {
            "conversation_summary": self.memory.conversation_summary,
            "current_goal": self.memory.current_goal,
            "recent_emotions": [
                {
                    "timestamp": e.timestamp,
                    "dominant": e.dominant,
                    "stability": e.stability,
                    "uncertain": e.uncertain
                }
                for e in self.memory.recent_emotions
            ]
        }
