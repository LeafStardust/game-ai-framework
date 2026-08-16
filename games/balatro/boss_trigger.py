from __future__ import annotations

from dataclasses import dataclass

from games.balatro.hand import PokerHand


@dataclass(frozen=True)
class BossHandTriggerResult:
    """Public-state result for whether one played hand triggers Matador."""

    triggered: bool
    resolvable: bool = True


_MATADOR_CARD_DEBUFF_BOSSES = frozenset(
    {
        "The Window",
        "The Head",
        "The Club",
        "The Goad",
        "The Plant",
        "The Pillar",
        "Verdant Leaf",
    }
)


def boss_blind_disabled_by_owned_jokers(state) -> bool:
    """Return whether an owned passive Joker disables the current boss blind."""
    return any(
        type(joker).__name__ == "ChicotJoker"
        for joker in getattr(state, "jokers", []) or []
    )


def matador_state_resolvable(state) -> bool:
    """Return whether public state is sufficient to classify Matador exactly."""
    if state is None or boss_blind_disabled_by_owned_jokers(state):
        return True

    boss_name = str(getattr(state, "boss_name", "") or "")
    if boss_name == "The Ox":
        return _unique_most_played_hand(state) is not None
    if boss_name == "The Mouth":
        played = _round_played_hands(state)
        return len(played) <= 1
    return True


def matador_boss_hand_triggered(state, hand, cards) -> BossHandTriggerResult:
    """Classify Balatro's exact hand-trigger condition used by Matador.

    The result intentionally distinguishes ``False`` from ``unresolvable`` so
    live projection can fail closed when the game tracks a tie-broken/public
    boss target that the current framework state does not expose directly.
    """
    if state is None or boss_blind_disabled_by_owned_jokers(state):
        return BossHandTriggerResult(False)

    boss_name = str(getattr(state, "boss_name", "") or "")
    played_cards = list(cards or [])

    if boss_name in _MATADOR_CARD_DEBUFF_BOSSES:
        return BossHandTriggerResult(
            any(bool(getattr(card, "debuffed", False)) for card in played_cards)
        )

    if boss_name == "The Flint":
        return BossHandTriggerResult(True)

    if boss_name == "The Psychic":
        return BossHandTriggerResult(len(played_cards) < 5)

    if boss_name == "The Eye":
        counts = getattr(state, "round_hand_play_counts", None)
        if not isinstance(counts, dict):
            return BossHandTriggerResult(False, resolvable=False)
        return BossHandTriggerResult(_hand_count(counts, hand) > 0)

    if boss_name == "The Mouth":
        played = _round_played_hands(state)
        if len(played) > 1:
            return BossHandTriggerResult(False, resolvable=False)
        if not played:
            return BossHandTriggerResult(False)
        return BossHandTriggerResult(next(iter(played)) != _hand_value(hand))

    if boss_name == "The Arm":
        levels = getattr(state, "hand_levels", None)
        if not isinstance(levels, dict):
            return BossHandTriggerResult(False, resolvable=False)
        level = int(levels.get(_hand_value(hand), levels.get(hand, 1)) or 1)
        return BossHandTriggerResult(level > 1)

    if boss_name == "The Ox":
        most_played = _unique_most_played_hand(state)
        if most_played is None:
            return BossHandTriggerResult(False, resolvable=False)
        return BossHandTriggerResult(most_played == _hand_value(hand))

    return BossHandTriggerResult(False)


def _round_played_hands(state) -> set[str]:
    counts = getattr(state, "round_hand_play_counts", None)
    if not isinstance(counts, dict):
        return set()
    return {
        _hand_value(hand)
        for hand in PokerHand
        if _hand_count(counts, hand) > 0
    }


def _unique_most_played_hand(state) -> str | None:
    counts = getattr(state, "hand_play_counts", None)
    if not isinstance(counts, dict):
        return None

    by_hand = {
        hand.value: _hand_count(counts, hand)
        for hand in PokerHand
    }
    maximum = max(by_hand.values(), default=0)
    leaders = [name for name, count in by_hand.items() if count == maximum]
    if len(leaders) != 1:
        return None
    return leaders[0]


def _hand_count(counts: dict, hand) -> int:
    return int(counts.get(_hand_value(hand), counts.get(hand, 0)) or 0)


def _hand_value(hand) -> str:
    return str(getattr(hand, "value", hand))
