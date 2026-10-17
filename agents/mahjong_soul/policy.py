"""Policy boundary and deterministic integration baseline; no game input."""
from copy import deepcopy
from typing import Protocol


class Policy(Protocol):
    def choose(self, request: dict) -> dict:
        """Return one action intent from the request, without modifying it."""
        ...


def proposal_from_policy(policy: Policy, request):
    # Policy code receives an isolated copy, not the validator's request object.
    action = policy.choose(deepcopy(request))
    if not isinstance(action, dict):
        raise ValueError("Policy must return an action object")
    return {"version":1,"request_id":request["request_id"],
            "board_token":request["board_token"],"action":deepcopy(action)}


class BaselinePolicy:
    """Accept offered wins, decline calls, otherwise discard the draw if allowed.

    This tests contracts and replay coverage, not Mahjong strength. It does not
    compute shanten, defend, declare Riichi, or choose calls/kans.
    """
    def choose(self, request):
        actions = request.get("actions", [])
        for kind in ("tsumo", "ron"):
            matches = [a for a in actions if a["kind"] == kind]
            if matches: return deepcopy(matches[0])
        discards = [a for a in actions if a["kind"] == "discard"]
        if discards:
            drawn = request["observation"]["board"]["self"]["drawn_tile"]
            match = next((a for a in discards if a["tile"] == drawn), None)
            # A deterministic tile choice, never a screen slot or hand-array index.
            return deepcopy(match or min(discards, key=lambda a:(a["tile"].startswith("0"),a["tile"])))
        skip = next((a for a in actions if a["kind"] == "skip"), None)
        if skip: return deepcopy(skip)
        raise ValueError("Baseline has no supported choice for this request")


def make_policy(name, playstyle="balanced"):
    if name != "playbook" and playstyle != "balanced":
        raise ValueError("Playstyles require the playbook policy")
    if name == "baseline": return BaselinePolicy()
    if name == "playbook":
        from agents.mahjong_soul.playbook_policy import PlaybookPolicy
        return PlaybookPolicy(style=playstyle)
    if name == "efficiency":
        from agents.mahjong_soul.efficiency import EfficiencyPolicy
        return EfficiencyPolicy()
    raise ValueError("Unknown policy")
