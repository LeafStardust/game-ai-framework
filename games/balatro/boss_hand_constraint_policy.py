from __future__ import annotations

"""Hard public boss constraints and subordinate Mouth redraw evidence for D1.

The Eye cannot repeat poker-hand types during the current blind. The Mouth accepts
only its locked poker-hand type after the first scored hand. Those are exact public
mechanics and remain pre-arbitration candidate constraints.

When The Mouth is already locked and D1 chooses DISCARD, retained forced-hand
structure and redraw width are candidate evidence only; they no longer replace the
post-policy decision through a second arbiter.
"""

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


MOUTH_FORCED_STRUCTURE_FIT = 2.0
MOUTH_REDRAW_WIDTH_FIT = 0.10


def _hand_type(policy, state, plan) -> str:
    rules = hand_rules_for_state(state)
    return str(
        policy._hand_evaluator.evaluate(
            list(plan.action.cards),
            rules=rules,
        ).value
    ).upper()


def _psychic_filter(state, plans):
    """Compatibility no-op: Psychic short plays are legal actions in Balatro."""
    return tuple(plans)


def _eye_filter(policy, state, plans):
    if str(getattr(state, "boss_name", "") or "") != "The Eye":
        return tuple(plans)
    if boss_blind_disabled_by_owned_jokers(state):
        return tuple(plans)

    supplied = tuple(plans)
    used = {
        str(value).upper()
        for value in (getattr(state, "boss_blind_hands", set()) or set())
    }
    # Fall back to the public current-round counters when the blind-owned table was
    # not observed. Do not use lifetime run counts.
    if not used and not bool(getattr(state, "boss_blind_state_observed", False)):
        used = {
            str(hand).upper()
            for hand, count in (getattr(state, "round_hand_play_counts", {}) or {}).items()
            if int(count or 0) > 0
        }

    if not used:
        return supplied

    unused_plays = tuple(
        plan
        for plan in supplied
        if plan.action.name == PLAY_CARDS and _hand_type(policy, state, plan) not in used
    )
    if not unused_plays:
        return supplied
    discards = tuple(plan for plan in supplied if plan.action.name == DISCARD_CARDS)
    return (*unused_plays, *discards)


def _mouth_locked_hand(state) -> str | None:
    if str(getattr(state, "boss_name", "") or "") != "The Mouth":
        return None
    if boss_blind_disabled_by_owned_jokers(state):
        return None
    value = getattr(state, "boss_blind_only_hand", None)
    return str(value).upper() if value else None


def _mouth_filter(policy, state, plans):
    """Remove zero-score Mouth plays while a legal recovery line exists."""
    supplied = tuple(plans)
    forced = _mouth_locked_hand(state)
    if forced is None:
        return supplied

    matching = tuple(
        plan
        for plan in supplied
        if plan.action.name == PLAY_CARDS and _hand_type(policy, state, plan) == forced
    )
    discards = tuple(plan for plan in supplied if plan.action.name == DISCARD_CARDS)
    if matching or discards:
        return (*matching, *discards)
    # With no matching play and no discard, Balatro still requires a legal hand
    # burn. Preserve the original plans so D1 can advance to the terminal state.
    return supplied


def _mouth_discard_fit(policy, state, action) -> tuple[float, tuple[str, ...]]:
    forced = _mouth_locked_hand(state)
    if forced is None or action.name != DISCARD_CARDS:
        return 0.0, ()

    removed = {id(card) for card in getattr(action, "cards", ()) or ()}
    kept = [
        card
        for card in tuple(getattr(state, "hand", ()) or ())
        if id(card) not in removed
    ]
    rules = hand_rules_for_state(state)
    structure = float(policy._structure_fit(kept, forced, rules=rules))
    redraw_width = len(tuple(getattr(action, "cards", ()) or ()))
    value = (
        structure * MOUTH_FORCED_STRUCTURE_FIT
        + redraw_width * MOUTH_REDRAW_WIDTH_FIT
    )
    return value, (
        f"The Mouth locked to {forced}: retained forced-hand structure={structure:.3f}",
        f"The Mouth redraw width={redraw_width}; forced-hand evidence={value:+.3f}",
        "Mouth redraw shaping is candidate evidence beneath canonical D1 survival ordering",
    )


def install_boss_hand_constraint_policy() -> None:
    if getattr(
        StrategyAwareLiveHandActionPolicy,
        "_boss_hand_constraints_installed",
        False,
    ):
        return

    original_decide = StrategyAwareLiveHandActionPolicy.decide
    original_strategy_fit = StrategyAwareLiveHandActionPolicy._strategy_fit

    def strategy_fit(self, state, action):
        base, rationale = original_strategy_fit(self, state, action)
        mouth_value, mouth_notes = _mouth_discard_fit(self, state, action)
        if mouth_value <= 0.0:
            return base, rationale
        return base + mouth_value, (*rationale, *mouth_notes)

    def decide(self, state, plans, **kwargs):
        constrained = _eye_filter(self, state, plans)
        constrained = _mouth_filter(self, state, constrained)
        return original_decide(self, state, constrained, **kwargs)

    StrategyAwareLiveHandActionPolicy._strategy_fit = strategy_fit
    StrategyAwareLiveHandActionPolicy.decide = decide
    StrategyAwareLiveHandActionPolicy._boss_hand_constraints_installed = True
