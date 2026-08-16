import pytest

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.jokers.ice_cream import IceCreamJoker
from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel
from games.balatro.live.psychic_blind_planner import PsychicBlindClearPlanner
from games.balatro.state import BalatroState


def _psychic_state() -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.score = 0
    state.hands_remaining = 4
    state.discards_remaining = 4
    state.blind = Blind(BlindType.BOSS, 600)
    state.boss_name = "The Psychic"
    state.hand = [
        BalatroCard("J", "Hearts", live_id=0),
        BalatroCard("J", "Diamonds", live_id=1),
        BalatroCard("9", "Clubs", live_id=2),
        BalatroCard("6", "Hearts", live_id=3),
        BalatroCard("5", "Clubs", live_id=4),
        BalatroCard("2", "Spades", live_id=5),
        BalatroCard("2", "Hearts", live_id=6),
        BalatroCard("2", "Clubs", live_id=7),
    ]
    state.deck = [
        BalatroCard(str((index % 9) + 2), "Spades")
        for index in range(20)
    ]
    ice_cream = IceCreamJoker()
    ice_cream.chips = 90
    state.jokers = [ice_cream]
    return state


def _planner() -> PsychicBlindClearPlanner:
    return PsychicBlindClearPlanner(
        draw_outcomes=PublicDrawOutcomeModel(
            exact_combination_limit=128,
            sample_count=64,
            seed=1,
        ),
        play_width=6,
        discard_width=4,
        horizon=2,
    )


def test_psychic_only_generates_five_card_plays_but_keeps_discards_available():
    state = _psychic_state()
    candidates = _planner()._candidate_actions(state, allow_discards=True)

    plays = [action for action in candidates if action.name == PLAY_CARDS]
    discards = [action for action in candidates if action.name == DISCARD_CARDS]

    assert plays
    assert all(len(action.cards) == 5 for action in plays)
    assert discards
    assert any(len(action.cards) != 5 for action in discards)


def test_psychic_live_hand_has_exact_full_house_clear_with_ice_cream():
    state = _psychic_state()
    plan = _planner().plan(state)

    assert plan.action.name == PLAY_CARDS
    assert len(plan.action.cards) == 5
    assert [card.rank for card in plan.action.cards] == ["J", "J", "2", "2", "2"]
    assert plan.value.clear_probability == 1.0
    assert plan.value.expected_score == 624.0
    assert plan.exact is True
    assert state.jokers[0].chips == 90


def test_psychic_planner_refuses_other_bosses():
    state = _psychic_state()
    state.boss_name = "The Goad"

    with pytest.raises(ValueError, match="Psychic planner requires The Psychic"):
        _planner().plan(state)
