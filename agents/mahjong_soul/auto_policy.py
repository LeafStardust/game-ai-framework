"""Validate automatic strategy actions without suppressing call choices."""
from copy import deepcopy


class AutomaticPolicy:
    def __init__(self, policy):
        self.policy = policy
        self.last_analysis = None

    def choose(self, request):
        allowed = list(request["actions"])
        if not allowed:
            raise ValueError("No legal action")
        filtered = deepcopy(request)
        filtered["actions"] = allowed
        result = self.policy.choose(filtered)
        if result not in allowed:
            raise ValueError("Automatic policy returned an unavailable action")
        self.last_analysis = deepcopy(getattr(self.policy, "last_analysis", None)) or {}
        return result
