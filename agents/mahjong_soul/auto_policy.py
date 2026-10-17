"""Restrict automatic strategy to visually supported input paths.

Manual suggestions retain every ATK action. Automatic play omits kan and
multi-combination calls until their choice panels have a visual recognizer.
The strategy chooses again from remaining legal actions instead of pausing.
"""
from collections import Counter
from copy import deepcopy


class AutomaticPolicy:
    def __init__(self, policy):
        self.policy = policy
        self.last_analysis = None

    def choose(self, request):
        counts = Counter(a["kind"] for a in request["actions"])
        allowed = [a for a in request["actions"]
                   if a["kind"] in ("discard", "skip", "riichi", "ron", "tsumo")
                   or a["kind"] in ("chi", "pon") and counts[a["kind"]] == 1]
        if not allowed:
            raise ValueError("No automatically executable legal action")
        filtered = deepcopy(request)
        filtered["actions"] = allowed
        result = self.policy.choose(filtered)
        if result not in allowed:
            raise ValueError("Automatic policy returned an unavailable action")
        self.last_analysis = deepcopy(getattr(self.policy, "last_analysis", None)) or {}
        self.last_analysis["automatic_omitted_actions"] = [a for a in request["actions"] if a not in allowed]
        return result
