from dataclasses import dataclass, field

from games.balatro.strategy import BalatroStrategyTracker, StrategyDefinition


@dataclass
class _State:
    ante: int = 1
    jokers: tuple = ()
    vouchers: tuple = ()
    owned_deck: tuple = ()
    hand_levels: dict[str, int] = field(default_factory=dict)
    hand_play_counts: dict[str, int] = field(default_factory=dict)


def _tracker():
    definition = StrategyDefinition(
        strategy_id="high_card_test",
        name="High Card Test",
        primary_hands=("HIGH_CARD",),
    )
    return BalatroStrategyTracker({definition.strategy_id: definition})


def test_generic_poker_hand_play_count_is_not_strategy_evidence():
    state = _State(hand_play_counts={"HIGH_CARD": 99})

    assessment = _tracker().assess(state)[0]

    assert assessment.score == 0.0
    assert not any("history" in note.lower() for note in assessment.rationale)


def test_persistent_hand_level_investment_remains_strategy_evidence():
    state = _State(
        hand_levels={"HIGH_CARD": 4},
        hand_play_counts={"HIGH_CARD": 99},
    )

    assessment = _tracker().assess(state)[0]

    assert assessment.score == 1.5


def test_play_count_does_not_change_score_when_hand_level_is_held_constant():
    tracker = _tracker()
    without_history = _State(hand_levels={"HIGH_CARD": 3})
    with_history = _State(
        hand_levels={"HIGH_CARD": 3},
        hand_play_counts={"HIGH_CARD": 999},
    )

    assert tracker.assess(without_history)[0].score == tracker.assess(with_history)[0].score
