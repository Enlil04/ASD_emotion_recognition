from typing import Any, Dict


def _empty_emotion_payload() -> Dict[str, Any]:
    return {
        "timestamp": 0.0,
        "face_detected": False,
        "dominant": None,
        "top2": None,
        "stability": 0.0,
        "uncertain": True,
    }


def get_session_state(session_memory_manager) -> Dict[str, Any]:
    """
    Tool: get_session_state

    Returns the agent-facing session memory state (local memory).
    Expected input: an instance of SessionMemoryManager.
    """
    if session_memory_manager is None or not hasattr(session_memory_manager, "get_state"):
        return {
            "conversation_summary": "",
            "current_goal": None,
            "recent_emotions": [],
        }

    state = session_memory_manager.get_state() or {}
    # Ensure JSON-serializable + required keys
    return {
        "conversation_summary": state.get("conversation_summary", ""),
        "current_goal": state.get("current_goal", None),
        "recent_emotions": state.get("recent_emotions", []),
    }


def get_emotion_state(source) -> Dict[str, Any]:
    """
    Tool: get_emotion_state (backwards compatible)

    - If `source` is an EmotionSummarizer (has .get_summary()), returns the latest 1 Hz summary.
    - If `source` is a SessionMemoryManager (has .get_state()), returns the latest snapshot from memory
      using the same JSON schema (some fields like top2/face_detected may be None/False).

    This lets you migrate safely:
      old code: get_emotion_state(summarizer)
      new code: get_emotion_state(session_memory_manager)   OR   get_session_state(session_memory_manager)
    """
    if source is None:
        return _empty_emotion_payload()

    # Case A: SessionMemoryManager-like
    if hasattr(source, "get_state") and callable(getattr(source, "get_state")):
        state = source.get_state() or {}
        recent = state.get("recent_emotions") or []
        if not recent:
            return _empty_emotion_payload()

        last = recent[-1]  # most recent snapshot
        return {
            "timestamp": float(last.get("timestamp", 0.0)),
            "face_detected": None,  # not stored in current SessionMemory schema
            "dominant": last.get("dominant", None),
            "top2": None,  # not stored in current SessionMemory schema
            "stability": float(last.get("stability", 0.0)),
            "uncertain": bool(last.get("uncertain", True)),
        }

    # Case B: EmotionSummarizer-like
    if hasattr(source, "get_summary") and callable(getattr(source, "get_summary")):
        summary = source.get_summary()
        if summary is None:
            return _empty_emotion_payload()

        return {
            "timestamp": float(getattr(summary, "timestamp", 0.0)),
            "face_detected": bool(getattr(summary, "face_detected", False)),
            "dominant": getattr(summary, "dominant", None),
            "top2": getattr(summary, "top2", None),
            "stability": float(getattr(summary, "stability", 0.0)),
            "uncertain": bool(getattr(summary, "uncertain", True)),
        }

    return _empty_emotion_payload()
