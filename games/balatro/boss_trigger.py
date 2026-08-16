from __future__ import annotations

from dataclasses import dataclass

from games.balatro.hand import PokerHand


@dataclass(frozen=True)
class BossHandTriggerResult:
    """Public-state result for whether one played hand triggers a boss effect."""

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

_HAND_DEBUFF_BOSSES = frozenset(
    {
        "The Psychic",
        "The Eye",
        "The Mouth",
    }
)


def boss_blind_disabled_by_owned_jokers(state) -> bool:
    """Return whether an owned passive Joker disables the current boss blind."""
    return any(
        type(joker).__name__ == "ChicotJoker"
        for joker in getattr(state, "jokers", []) or []
    )


def boss_hand_is_debuffed(state, hand, cards) -> BossHandTriggerResult:
    """Classify boss effects that reject an entire played poker hand.

    Psychic/Eye/Mouth hands are still legal Play actions in Balatro. When their
    condition fires, the hand enters the blind-debuff path instead of normal
    scoring. Eye/Mouth use the active Blind object's own public state when live
    observation supplied it; legacy/manual states fall back to round hand counts.
    """
    if state is None or boss_blind_disabled_by_owned_jokers(state):
        return BossHandTriggerResult(False)

    boss_name = str(getattr(state, "boss_name", "") or "")
    if boss_name not in _HAND_DEBUFF_BOSSES:
        return BossHandTriggerResult(False)

    played_cards = list(cards or [])
    if boss_name == "The Psychic":
        return BossHandTriggerResult(len(played_cards) < 5)

    hand_value = _hand_value(hand)
    blind_state_observed = bool(
        getattr(state, "boss_blind_state_observed", False)
    )

    if boss_name == "The Eye":
        if blind_state_observed:
            played = getattr(state, "boss_blind_hands", None)
            if not isinstance(played, set):
                return BossHandTriggerResult(False, resolvable=False)
            return BossHandTriggerResult(hand_value in played)

        counts = getattr(state, "round_hand_play_counts", None)
        if not isinstance(counts, dict):
            return BossHandTriggerResult(False, resolvable=False)
        return BossHandTriggerResult(_hand_count(counts, hand) > 0)

    if blind_state_observed:
        only_hand = getattr(state, "boss_blind_only_hand", None)
        if only_hand is None:
            return BossHandTriggerResult(False)
        return BossHandTriggerResult(str(only_hand) != hand_value)

    played = _round_played_hands(state)
    if len(played) > 1:
        return BossHandTriggerResult(False, resolvable=False)
    if not played:
        return BossHandTriggerResult(False)
    return BossHandTriggerResult(next(iter(played)) != hand_value)


def record_accepted_boss_hand(state, hand) -> None:
    """Advance Eye/Mouth Blind-owned history after a non-debuffed play."""
    if state is None or boss_blind_disabled_by_owned_jokers(state):
        return

    boss_name = str(getattr(state, "boss_name", "") or "")
    hand_value = _hand_value(hand)

    if boss_name == "The Eye":
        played = getattr(state, "boss_blind_hands", None)
        if not isinstance(played, set):
            played = set()
            state.boss_blind_hands = played
        played.add(hand_value)
        state.boss_blind_state_observed = True
        return

    if boss_name == "The Mouth":
        if getattr(state, "boss_blind_only_hand", None) is None:
            state.boss_blind_only_hand = hand_value
        state.boss_blind_state_observed = True


def matador_state_resolvable(state) -> bool:
    """Return whether public state is sufficient to classify Matador exactly."""
    if state is None or boss_blind_disabled_by_owned_jokers(state):
        return True

    boss_name = str(getattr(state, "boss_name", "") or "")
    if boss_name == "The Ox":
        return _unique_most_played_hand(state) is not None
    if boss_name == "The Eye":
        if bool(getattr(state, "boss_blind_state_observed", False)):
            return isinstance(getattr(state, "boss_blind_hands", None), set)
        return isinstance(getattr(state, "round_hand_play_counts", None), dict)
    if boss_name == "The Mouth":
        if bool(getattr(state, "boss_blind_state_observed", False)):
            return True
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

    if boss_name in _HAND_DEBUFF_BOSSES:
        return boss_hand_is_debuffed(state, hand, played_cards)

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
    run_counts = getattr(state, "hand_play_counts", None)
    round_counts = getattr(state, "round_hand_play_counts", None)
    if not isinstance(run_counts, dict) or not isinstance(round_counts, dict):
        return None

    # G.GAME.current_round.most_played_poker_hand is fixed for the round. Live
    # run counts already include hands played during the current blind, so subtract
    # current-round usage to reconstruct the public run totals at round start.
    by_hand = {
        hand.value: max(
            0,
            _hand_count(run_counts, hand) - _hand_count(round_counts, hand),
        )
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
