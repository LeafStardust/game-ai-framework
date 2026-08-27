from __future__ import annotations

"""Canonical D1 evidence for Runner and To Do List target-hand mechanics.

Canonical D1 owns the Play/Discard action class and all final candidate arbitration.
This installer augments only the strategy-fit evidence consumed by that policy; it
does not wrap ``decide`` or reselect an action after arbitration.
"""

from games.balatro.actions import PLAY_CARDS
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


TARGET_HAND_FIT = 2.5


def _normalize(value: object) -> str:
    return "_".join(str(value or "").upper().replace("-", " ").replace("_", " ").split())


def _joker_name(joker: object) -> str:
    value = (
        getattr(joker, "label", None)
        or getattr(joker, "name", None)
        or getattr(joker, "ability_name", None)
        or type(joker).__name__
    )
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _target_hands(state) -> tuple[str, ...]:
    targets: list[str] = []
    for joker in tuple(getattr(state, "jokers", ()) or ()):
        name = _joker_name(joker)
        if name in {"runner", "runnerjoker"}:
            targets.extend(("STRAIGHT", "STRAIGHT_FLUSH"))
            continue
        if name in {"todolist", "todolistjoker"}:
            value = getattr(joker, "target_hand", None)
            if value is None:
                public = getattr(joker, "public_state", None)
                if isinstance(public, dict):
                    value = public.get("target_hand")
            normalized = _normalize(getattr(value, "value", value))
            if normalized:
                targets.append(normalized)
    return tuple(dict.fromkeys(targets))


def _play_targets_engine(policy, state, action) -> tuple[bool, tuple[str, ...], str]:
    targets = _target_hands(state)
    if action.name != PLAY_CARDS or not targets:
        return False, targets, ""
    rules = hand_rules_for_state(state)
    hand = _normalize(
        policy._hand_evaluator.evaluate(list(action.cards), rules=rules).value
    )
    return hand in set(targets), targets, hand


def install_target_hand_engine_policy() -> None:
    if getattr(
        StrategyAwareLiveHandActionPolicy,
        "_target_hand_engine_policy_installed",
        False,
    ):
        return

    original_strategy_fit = StrategyAwareLiveHandActionPolicy._strategy_fit

    def strategy_fit(self, state, action):
        value, rationale = original_strategy_fit(self, state, action)
        matches, targets, hand = _play_targets_engine(self, state, action)
        if not matches:
            return value, rationale
        return (
            value + TARGET_HAND_FIT,
            (
                *rationale,
                f"target-hand engine evidence: {hand} matches {','.join(targets)}",
                "Runner/To Do List fit is consulted only inside canonical D1 safe/equivalent candidate ranking",
            ),
        )

    StrategyAwareLiveHandActionPolicy._strategy_fit = strategy_fit
    StrategyAwareLiveHandActionPolicy._target_hand_engine_policy_installed = True
