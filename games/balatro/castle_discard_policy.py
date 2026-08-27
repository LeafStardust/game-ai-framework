from __future__ import annotations

"""Canonical D1 evidence for Castle discard progression.

Castle rewards discarding cards of its current public suit. The mechanic is useful
only as a preference among discard candidates already admitted by canonical D1;
this installer therefore augments strategy-fit evidence instead of wrapping
``decide`` or replacing the selected action afterwards.
"""

from games.balatro.actions import DISCARD_CARDS
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


CASTLE_MATCH_FIT = 0.75


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _joker_token(joker: object) -> str:
    return _normalize(
        getattr(joker, "name", None)
        or getattr(joker, "label", None)
        or getattr(joker, "ability_name", None)
        or type(joker).__name__
    )


def _castle_suit(state) -> str | None:
    for joker in getattr(state, "jokers", ()) or ():
        if _joker_token(joker) not in {"castle", "castlejoker"}:
            continue
        public = getattr(joker, "public_state", None)
        if isinstance(public, dict):
            suit = public.get("suit")
        else:
            suit = getattr(public, "suit", None) if public is not None else None
        suit = suit or getattr(joker, "suit", None) or getattr(joker, "current_suit", None)
        if suit:
            return str(suit)
    return None


def _castle_match_count(action, suit: str) -> int:
    if action.name != DISCARD_CARDS:
        return 0
    return sum(
        1
        for card in (getattr(action, "cards", ()) or ())
        if str(getattr(card, "suit", "")) == suit
    )


def install_castle_discard_policy() -> None:
    if getattr(
        StrategyAwareLiveHandActionPolicy,
        "_castle_discard_policy_installed",
        False,
    ):
        return

    original_strategy_fit = StrategyAwareLiveHandActionPolicy._strategy_fit

    def strategy_fit(self, state, action):
        value, rationale = original_strategy_fit(self, state, action)
        suit = _castle_suit(state)
        if not suit:
            return value, rationale
        matches = _castle_match_count(action, suit)
        if matches <= 0:
            return value, rationale
        return (
            value + CASTLE_MATCH_FIT * matches,
            (
                *rationale,
                f"Castle discard evidence: {matches} discarded card(s) match current suit {suit}",
                "Castle fit is subordinate to canonical D1 full-blind survival/resource ordering",
            ),
        )

    StrategyAwareLiveHandActionPolicy._strategy_fit = strategy_fit
    StrategyAwareLiveHandActionPolicy._castle_discard_policy_installed = True
