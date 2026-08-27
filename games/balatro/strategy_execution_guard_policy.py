from __future__ import annotations

"""Canonical D1 evidence for realized hand-repetition engines.

Canonical D1 owns the Play/Discard action class and candidate arbitration. This
installer augments only the existing strategy-fit evidence used by that policy;
it does not wrap ``decide`` or reselect an action after arbitration.
"""

from games.balatro.actions import PLAY_CARDS
from games.balatro.bonds.diagnostics import bond_strategy_diagnostics
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


HAND_REPETITION_FIT = 2.0


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _realized_bond(state, bond_id: str) -> bool:
    try:
        diagnostics = bond_strategy_diagnostics(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return False
    for payload in diagnostics.get("relevant_bonds", ()) or ():
        if str(payload.get("bond_id")) != bond_id:
            continue
        return str(payload.get("realization", "")).upper() in {"ACTIVE", "MATURE"}
    return False


def _played_this_round(state) -> set[str]:
    counts = getattr(state, "round_hand_play_counts", None)
    if not isinstance(counts, dict):
        counts = getattr(state, "hand_play_counts_this_round", None)
    if not isinstance(counts, dict):
        return set()
    return {_normalize(name) for name, count in counts.items() if int(count or 0) > 0}


def _play_repeats_hand(policy, state, action) -> bool:
    if action.name != PLAY_CARDS or not _realized_bond(state, "hand_repetition"):
        return False
    repeated = _played_this_round(state)
    if not repeated:
        return False
    rules = hand_rules_for_state(state)
    hand = policy._hand_evaluator.evaluate(list(action.cards), rules=rules)
    return _normalize(hand.value) in repeated


def install_strategy_execution_guard_policy() -> None:
    if getattr(
        StrategyAwareLiveHandActionPolicy,
        "_strategy_execution_guard_policy_installed",
        False,
    ):
        return

    original_strategy_fit = StrategyAwareLiveHandActionPolicy._strategy_fit

    def strategy_fit(self, state, action):
        value, rationale = original_strategy_fit(self, state, action)
        if not _play_repeats_hand(self, state, action):
            return value, rationale
        return (
            value + HAND_REPETITION_FIT,
            (
                *rationale,
                "realized hand_repetition evidence: this PLAY repeats a hand already used this round",
                "repetition fit is consulted only inside canonical D1 safe/equivalent candidate ranking",
            ),
        )

    StrategyAwareLiveHandActionPolicy._strategy_fit = strategy_fit
    StrategyAwareLiveHandActionPolicy._strategy_execution_guard_policy_installed = True
