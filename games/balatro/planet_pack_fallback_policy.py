from __future__ import annotations

"""Final Celestial-pack fallback authority.

When no offered Planet already belongs to a materially developed hand or the applied
strategy, prefer the historically established safe fallback ladder:
High Card > Pair > Three of a Kind / Two Pair.

This is deliberately a pack-ranking rule only.  It does not make an otherwise
invalid/negative Planet selectable and it does not override an already-good Planet
for the current build.
"""

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.planets import PLANET_CARDS


_FALLBACK_PRIORITY = {
    "HIGH_CARD": 4,
    "PAIR": 3,
    "THREE_OF_A_KIND": 2,
    "TWO_PAIR": 2,
}


def _token(value: object) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def _planet_hand(action) -> str | None:
    choice = getattr(action, "target", None)
    if choice is None or str(getattr(choice, "kind", "") or "").upper() != "PLANET":
        return None
    label = _token(getattr(choice, "label", ""))
    for planet in PLANET_CARDS.values():
        if _token(planet.name) == label:
            return str(planet.hand_type).upper().replace(" ", "_")
    return None


def _plan_hand_goals(state) -> set[str]:
    try:
        _, composition = evaluate_bond_composition(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return set()
    plan = getattr(composition, "strategy_plan", None)
    if plan is None or getattr(plan, "commitment", StrategyCommitment.EXPLORATORY) < StrategyCommitment.PINNED:
        return set()
    aliases = {
        "high_card": "HIGH_CARD",
        "pair": "PAIR",
        "two_pair": "TWO_PAIR",
        "three_kind": "THREE_OF_A_KIND",
        "four_kind": "FOUR_OF_A_KIND",
        "straight": "STRAIGHT",
        "flush": "FLUSH",
        "full_house": "FULL_HOUSE",
        "straight_flush": "STRAIGHT_FLUSH",
        "five_kind": "FIVE_OF_A_KIND",
        "flush_house": "FLUSH_HOUSE",
        "flush_five": "FLUSH_FIVE",
    }
    result: set[str] = set()
    for goal in tuple(getattr(plan, "bond_goals", ()) or ()):
        hand = aliases.get(str(getattr(goal, "bond_id", "")))
        if hand:
            result.add(hand)
    return result


def _materially_good(state, hand: str, plan_hands: set[str]) -> bool:
    if hand in plan_hands:
        return True
    levels = getattr(state, "hand_levels", {}) or {}
    plays = getattr(state, "hand_play_counts", {}) or {}
    level = int(levels.get(hand, levels.get(hand.replace("_", " "), 1)) or 1)
    played = int(plays.get(hand, plays.get(hand.replace("_", " "), 0)) or 0)
    # A genuine permanent upgrade or repeated use is enough to count as a current
    # good target.  One incidental play is not.
    return level > 1 or played >= 3


def install_planet_pack_fallback_policy() -> None:
    if getattr(BalatroPackPolicy, "_planet_pack_fallback_installed", False):
        return

    original_rank = BalatroPackPolicy.rank_actions

    def rank_actions(self, state, actions):
        ranked = original_rank(self, state, actions)
        positive_planets: list[tuple[PackActionScore, str]] = []
        for scored in ranked:
            hand = _planet_hand(scored.action)
            if hand is not None and float(scored.total) > 0.0:
                positive_planets.append((scored, hand))
        if not positive_planets:
            return ranked

        plan_hands = _plan_hand_goals(state)
        # Existing developed/strategy-owned targets remain authoritative; the
        # fallback ladder exists only when the pack offers none of them.
        if any(_materially_good(state, hand, plan_hands) for _, hand in positive_planets):
            return ranked

        fallback = [
            (scored, hand)
            for scored, hand in positive_planets
            if hand in _FALLBACK_PRIORITY
        ]
        if not fallback:
            return ranked

        best_score, best_hand = max(
            fallback,
            key=lambda item: (
                _FALLBACK_PRIORITY[item[1]],
                float(item[0].total),
            ),
        )
        promoted = PackActionScore(
            best_score.action,
            max(float(best_score.total), float(ranked[0].total) + 0.001),
            (
                *best_score.notes,
                "Planet pack fallback authority",
                "fallback order=HIGH_CARD > PAIR > THREE_OF_A_KIND/TWO_PAIR",
                f"selected fallback hand={best_hand}",
            ),
        )
        return [promoted] + [item for item in ranked if item.action != best_score.action]

    BalatroPackPolicy.rank_actions = rank_actions
    BalatroPackPolicy._planet_pack_fallback_installed = True
