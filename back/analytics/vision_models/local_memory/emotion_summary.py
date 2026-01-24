import time
from collections import deque
from dataclasses import dataclass
from typing import Optional, List, Tuple
import numpy as np

# ==============================
# CONFIG (agent-facing, SAFE to tune)
# ==============================
SUMMARY_HZ = 1.0              # produce 1 summary per second
WINDOW_SEC = 1.0              # how much history to evaluate
STABILITY_MIN = 0.65          # below this => uncertain
CONF_MIN = 0.35               # dominant prob too weak
TOP2_GAP_MIN = 0.08           # dominant vs runner-up too close


# ==============================
# DATA STRUCTURE
# ==============================
@dataclass
class EmotionSummary:
    timestamp: float
    face_detected: bool
    dominant: Optional[str]
    top2: Optional[List[Tuple[str, float]]]
    stability: float
    uncertain: bool


# ==============================
# EMOTION SUMMARY ENGINE
# ==============================
class EmotionSummarizer:
    """
    Consumes output from EmotionDetector.predict()
    WITHOUT modifying the detector itself.
    """

    def __init__(self):
        self.history = deque()
        self.last_summary_time = 0.0
        self.latest_summary: Optional[EmotionSummary] = None

    def update(
        self,
        emotion: Optional[str],
        conf: float,
        probs: Optional[np.ndarray],
        labels: List[str],
        face_detected: bool
    ):
        """
        Call this ONCE per frame (or frame-skip),
        passing the detector outputs.
        """

        now = time.time()

        if not face_detected or probs is None:
            self.history.clear()
            self._emit_no_face(now)
            return

        # sort raw probs (NOT weighted ones)
        order = np.argsort(probs)[::-1]
        top1_i, top2_i = int(order[0]), int(order[1])
        top1_p, top2_p = float(probs[top1_i]), float(probs[top2_i])

        dominant = labels[top1_i]
        top2 = [(labels[top1_i], top1_p), (labels[top2_i], top2_p)]

        # store history
        self.history.append((now, top1_i))
        cutoff = now - WINDOW_SEC
        while self.history and self.history[0][0] < cutoff:
            self.history.popleft()

        # compute stability
        if len(self.history) >= 2:
            last_idx = self.history[-1][1]
            stability = sum(1 for _, i in self.history if i == last_idx) / len(self.history)
        else:
            stability = 0.0

        uncertain = (
            conf < CONF_MIN or
            (top1_p - top2_p) < TOP2_GAP_MIN or
            stability < STABILITY_MIN
        )

        # emit summary at 1Hz
        if now - self.last_summary_time >= (1.0 / SUMMARY_HZ):
            self.last_summary_time = now
            self.latest_summary = EmotionSummary(
                timestamp=now,
                face_detected=True,
                dominant=dominant,
                top2=top2,
                stability=stability,
                uncertain=uncertain
            )

    def _emit_no_face(self, now):
        if now - self.last_summary_time >= (1.0 / SUMMARY_HZ):
            self.last_summary_time = now
            self.latest_summary = EmotionSummary(
                timestamp=now,
                face_detected=False,
                dominant=None,
                top2=None,
                stability=0.0,
                uncertain=True
            )

    def get_summary(self) -> Optional[EmotionSummary]:
        return self.latest_summary
