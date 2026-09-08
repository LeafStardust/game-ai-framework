import pytest

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.live.boss_blind_integration import (
    BossAwareLiveHandDecisionEvaluator,
    boss_blind_planning_rule,
    boss_play_action_is_legal,
)
from games.balatro.state import BalatroState


VISIBILITY_ONLY_BOSSES = (
    "The House",
    "The Wheel",
    "The Fish",
    "The Mark",
)


def _state(boss_name: str) -> tuple[BalatroState, BalatroCard]:
    ace = BalatroCard("A", "Spades", live_id=1)
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.blind = Blind(BlindType.BOSS, 100)
    state.boss_name = boss_name
    state.hand = [ace]
    state.deck = []
    state.owned_deck = [ace]
    state.hands_remaining = 4
    state.discards_remaining = 3
    return state, ace


@pytest.mark.parametrize("boss_name", VISIBILITY_ONLY_BOSSES)
def test_visibility_only_boss_is_explicit_identity_transparent_rule(boss_name):
    state, ace = _state(boss_name)

    rule = boss_blind_planning_rule(state)

    assert rule is not None
    assert rule.boss_name == boss_name
    assert rule.required_play_cards is None
    assert rule.evaluator_factory is None
    assert boss_play_action_is_legal(
        state,
        BalatroAction(PLAY_CARDS, cards=[ace]),
    ) is True


@pytest.mark.parametrize("boss_name", VISIBILITY_ONLY_BOSSES)
def test_visibility_only_boss_scores_underlying_card_identity_normally(boss_name):
    state, ace = _state(boss_name)
    evaluator = BossAwareLiveHandDecisionEvaluator()

    projection = evaluator.project_play(
        state,
        BalatroAction(PLAY_CARDS, cards=[ace]),
    )

    # The project intentionally permits process-memory card identities even when
    # Balatro renders them face down. Visibility alone therefore has no score or
    # transition transform: High Card base 5x1 + Ace 11 chips = 16.
    assert projection.hand_score == 16
    assert projection.expected_hand_score == 16.0
    assert projection.joker_projection_complete is True
    assert state.hand == [ace]
