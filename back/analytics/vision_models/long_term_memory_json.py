# long_term_memory_json.py
import json
import time
import os
from typing import Dict, Any, List, Tuple

DATA_DIR = "data/users"


def day_string_local() -> str:
    return time.strftime("%Y-%m-%d", time.localtime())


def aggregate_recent_emotions(recent_emotions: list) -> Dict[str, int]:
    """
    Input: list of dicts like SessionMemoryManager.get_state()["recent_emotions"]
    Output: counts per dominant emotion (ignoring uncertain or None)
    """
    counts: Dict[str, int] = {}
    for e in recent_emotions:
        dom = e.get("dominant")
        uncertain = bool(e.get("uncertain"))
        if dom is None or uncertain:
            continue
        counts[dom] = counts.get(dom, 0) + 1
    return counts


class LongTermMemoryJSON:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)

    def _path(self, user_id: str) -> str:
        return os.path.join(DATA_DIR, f"{user_id}.json")

    def ensure_user(self, user_id: str) -> None:
        path = self._path(user_id)
        if not os.path.exists(path):
            data = {
                "user_id": user_id,
                "preferences": {},
                "emotion_daily": {},
                "updated_at": time.time()
            }
            self._write_atomic(path, data)

    def _load(self, user_id: str) -> dict:
        self.ensure_user(user_id)
        path = self._path(user_id)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_atomic(self, path: str, data: dict) -> None:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)

    # ---------- Preferences ----------
    def get_preferences(self, user_id: str) -> Dict[str, Any]:
        data = self._load(user_id)
        return data.get("preferences", {})

    def set_preferences(self, user_id: str, prefs: Dict[str, Any]) -> None:
        data = self._load(user_id)
        data["preferences"] = prefs
        data["updated_at"] = time.time()
        self._write_atomic(self._path(user_id), data)

    # ---------- Emotion aggregates ----------
    def add_emotion_counts(self, user_id: str, day: str, counts: Dict[str, int]) -> None:
        data = self._load(user_id)

        daily = data.setdefault("emotion_daily", {})
        day_bucket = daily.setdefault(day, {})

        for emotion, inc in counts.items():
            if inc <= 0:
                continue
            day_bucket[emotion] = day_bucket.get(emotion, 0) + int(inc)

        data["updated_at"] = time.time()
        self._write_atomic(self._path(user_id), data)

    def get_top_emotions_last_days(self, user_id: str, days: int = 7) -> List[Tuple[str, int]]:
        data = self._load(user_id)
        daily = data.get("emotion_daily", {})

        cutoff = time.time() - days * 86400
        totals: Dict[str, int] = {}

        for day_str, emo_map in daily.items():
            try:
                day_ts = time.mktime(time.strptime(day_str, "%Y-%m-%d"))
            except:
                continue
            if day_ts < cutoff:
                continue
            for emo, cnt in emo_map.items():
                totals[emo] = totals.get(emo, 0) + cnt

        return sorted(totals.items(), key=lambda x: x[1], reverse=True)
