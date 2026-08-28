from __future__ import annotations

from collections import Counter
from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.safe_pace_timeout_patch import _select_structural_timeout_action


class _Policy:
    evaluator = SimpleNamespace(_retained_structure_value=lambda cards: float(len(cards)))

    def _structure_fit(self, cards, target_hand, *, rules=None):
        del rules
        counts = Counter(str(getattr(card, "rank", "")) for card in cards)
        values = sorted(counts.values(), reverse=True)
        target = str(target_hand).upper().replace(" ", "_")
        if target == "PAIR":
            return 1.0 if values and values[0] >= 2 else 0.0
        if target == "FULL_HOUSE":
            first = values[0] if values else 0
            second = values[1] if len(values) > 1 else 0
            return 0.6 * min(1.0, first / 3.0) + 0.4 * min(1.0, second / 2.0)
        return 0.0


class _NoDiscardGeneratorEngine:
    policy = _Policy()
    planner = SimpleNamespace(play_width=6)


class _DiscardGenerator:
    @staticmethod
    def generate_discard_actions(state):
        return [
            BalatroAction(DISCARD_CARDS, cards=[card])
            for card in state.hand
        ]


class _BoundedDiscardEngine:
    policy = _Policy()
    planner = SimpleNamespace(
        play_width=6,
        action_generator=_DiscardGenerator(),
    )


def _card(rank: str):
    return SimpleNamespace(
        rank=rank,
        suit="Spades",
        enhancement=None,
        edition=None,
        seal=None,
    )


def _state(ranks, *, boss_name="", only_hand=None, discards=4, hands=4):
    return SimpleNamespace(
        hand=[_card(rank) for rank in ranks],
        boss_name=boss_name,
        boss_blind_only_hand=only_hand,
        boss_blind_state_observed=True,
        discards_remaining=discards,
        hands_remaining=hands,
        jokers=[],
    )


def test_structural_timeout_uses_direct_subsets_for_nine_card_hand():
    state = _state(["A", "K", "Q", "J", "10", "9", "8", "7", "6"])

    action, best_play, selected_kind, play_count = _select_structural_timeout_action(
        _NoDiscardGeneratorEngine(),
        state,
    )

    assert play_count == 381
    assert action.name == PLAY_CARDS
    assert best_play.name == PLAY_CARDS
    assert selected_kind == "Play"


def test_mouth_timeout_does_not_fabricate_discard_without_generator_authority():
    state = _state(
        ["A", "K", "Q", "J", "10", "9", "8", "7", "6"],
        boss_name="The Mouth",
        only_hand="Pair",
        discards=4,
        hands=3,
    )

    action, _, selected_kind, _ = _select_structural_timeout_action(
        _NoDiscardGeneratorEngine(),
        state,
    )

    assert action.name == PLAY_CARDS
    assert selected_kind == "Play"


def test_mouth_timeout_uses_bounded_generated_discard_when_locked_hand_unavailable():
    state = _state(
        ["A", "K", "Q", "J", "10", "9", "8", "7", "6"],
        boss_name="The Mouth",
        only_hand="Pair",
        discards=4,
        hands=3,
    )

    action, best_play, selected_kind, _ = _select_structural_timeout_action(
        _BoundedDiscardEngine(),
        state,
    )

    assert action.name == DISCARD_CARDS
    assert best_play.name == PLAY_CARDS
    assert selected_kind == "Discard"


def test_mouth_timeout_keeps_matching_locked_hand_when_available():
    state = _state(
        ["6", "6", "A", "K", "Q", "J", "10", "9", "8"],
        boss_name="The Mouth",
        only_hand="Pair",
        discards=4,
        hands=3,
    )

    action, _, selected_kind, _ = _select_structural_timeout_action(
        _BoundedDiscardEngine(),
        state,
    )

    assert action.name == PLAY_CARDS
    assert selected_kind == "Play"
    assert Counter(card.rank for card in action.cards)["6"] == 2


def test_mouth_timeout_without_discards_uses_widest_zero_score_redraw():
    state = _state(
        ["A", "K", "Q", "J", "10", "9", "8", "7", "6"],
        boss_name="The Mouth",
        only_hand="Pair",
        discards=0,
        hands=2,
    )

    action, _, selected_kind, _ = _select_structural_timeout_action(
        _BoundedDiscardEngine(),
        state,
    )

    assert action.name == PLAY_CARDS
    assert selected_kind == "Play"
    assert len(action.cards) == 5
