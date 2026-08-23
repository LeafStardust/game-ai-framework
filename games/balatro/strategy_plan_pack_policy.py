from __future__ import annotations

"""Bounded booster-pack preference from the applied StrategyPlan.

Normal pack admission stays authoritative.  This layer only ranks already-positive
choices toward the highest-priority Bond goals of the pinned strategy.
"""

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.planets import PLANET_CARDS


_MAX_BONUS = 1.50
_MAX_TRACKED_GOALS = 3


def _token(value) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _rank(value) -> str:
    raw = str(value or "").upper()
    return {"KING": "K", "QUEEN": "Q", "JACK": "J", "ACE": "A", "T": "10"}.get(raw, raw)


def _suit(value) -> str:
    return str(value or "").lower().rstrip("s")


def _enhancement(value) -> str:
    token = _token(value)
    if token.startswith("m") and token in {"msteel", "mglass", "mgold", "mlucky"}:
        return token[1:]
    return token.removesuffix("card")


def _planet_hand(label: str) -> str | None:
    target = _token(label)
    for planet in PLANET_CARDS.values():
        if _token(planet.name) == target:
            return str(planet.hand_type).lower().replace(" ", "_")
    return None


def _plan(state):
    try:
        _, composition = evaluate_bond_composition(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return None
    return getattr(composition, "strategy_plan", None)


def _goal_ids(plan) -> tuple[str, ...]:
    if plan is None:
        return ()
    return tuple(goal.bond_id for goal in tuple(plan.bond_goals or ())[:_MAX_TRACKED_GOALS])


def _choice(action):
    choice = getattr(action, "target", None)
    if choice is None:
        return "", "", {}
    return (
        str(getattr(choice, "kind", "") or "").upper(),
        str(getattr(choice, "label", "") or ""),
        dict(getattr(choice, "data", {}) or {}),
    )


def _playing_card_matches(goal: str, data: dict) -> bool:
    rank = _rank(data.get("rank") or data.get("value"))
    suit = _suit(data.get("suit"))
    enhancement = _enhancement(data.get("enhancement") or data.get("ability_name"))
    if goal == "kings": return rank == "K"
    if goal == "queens": return rank == "Q"
    if goal == "jacks": return rank == "J"
    if goal == "aces": return rank == "A"
    if goal == "low_ranks": return rank in {"2", "3", "4", "5"}
    if goal in {"hearts", "spades", "clubs", "diamonds"}: return suit == goal.rstrip("s")
    if goal == "steel": return enhancement == "steel"
    if goal == "glass": return enhancement == "glass"
    if goal == "lucky": return enhancement == "lucky"
    if goal == "gold_economy": return enhancement == "gold"
    if goal == "enhanced_cards": return bool(enhancement)
    return False


_HAND_GOALS = {
    "high_card": "high_card",
    "pair": "pair",
    "two_pair": "two_pair",
    "three_kind": "three_of_a_kind",
    "four_kind": "four_of_a_kind",
    "straight": "straight",
    "flush": "flush",
    "full_house": "full_house",
    "straight_flush": "straight_flush",
    "five_kind": "five_of_a_kind",
    "flush_house": "flush_house",
    "flush_five": "flush_five",
}


def install_strategy_plan_pack_policy() -> None:
    if getattr(BalatroPackPolicy, "_strategy_plan_pack_policy_installed", False):
        return
    original = BalatroPackPolicy.score_action

    def score_action(self, state, action):
        scored = original(self, state, action)
        if scored.total <= 0.0:
            return scored
        plan = _plan(state)
        goals = _goal_ids(plan)
        if not goals:
            return scored
        kind, label, data = _choice(scored.action)
        matched: list[str] = []
        if kind == "PLAYING_CARD":
            matched = [goal for goal in goals if _playing_card_matches(goal, data)]
        elif kind == "PLANET":
            hand = _planet_hand(label)
            matched = [goal for goal in goals if _HAND_GOALS.get(goal) == hand]
        if not matched:
            return scored
        # Earlier goals are more important.  Keep the whole layer bounded beneath
        # admission/survival authorities.
        bonus = 0.0
        for goal in matched:
            index = goals.index(goal)
            bonus += 0.75 if index == 0 else 0.50 if index == 1 else 0.35
        bonus = min(_MAX_BONUS, bonus)
        return PackActionScore(
            scored.action,
            float(scored.total) + bonus,
            (
                *scored.notes,
                f"applied strategy pack-goal bonus={bonus:.3f}",
                "matched Bond goals=" + ", ".join(matched),
                "base pack admission remains authoritative",
            ),
        )

    BalatroPackPolicy.score_action = score_action
    BalatroPackPolicy._strategy_plan_pack_policy_installed = True
