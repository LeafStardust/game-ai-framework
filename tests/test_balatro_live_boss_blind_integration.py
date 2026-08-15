from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.jokers.bootstraps import BootstrapsJoker
from games.balatro.jokers.ice_cream import IceCreamJoker
from games.balatro.live.boss_blind_integration import (
    BossAwareLiveHandDecisionEvaluator,
    boss_blind_planning_rule,
)
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.state import BalatroState


def _state(boss_name: str) -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.score = 0
    state.money = 20
    state.hands_remaining = 4
    state.discards_remaining = 4
    state.blind = Blind(BlindType.BOSS, 1600)
    state.boss_name = boss_name
    state.hand = [
        BalatroCard("K", "Diamonds", live_id=0),
        BalatroCard("Q", "Diamonds", live_id=1),
        BalatroCard("J", "Hearts", live_id=2),
        BalatroCard("10", "Spades", live_id=3),
        BalatroCard("8", "Clubs", live_id=4),
        BalatroCard("6", "Clubs", live_id=5),
        BalatroCard("2", "Hearts", live_id=6),
        BalatroCard("2", "Clubs", live_id=7),
    ]
    state.deck = [
        BalatroCard(str((index % 9) + 2), "Spades")
        for index in range(20)
    ]
    return state


def test_boss_rule_registry_exposes_validated_planner_mechanics():
    psychic = boss_blind_planning_rule(_state("The Psychic"))
    head = boss_blind_planning_rule(_state("The Head"))
    house = boss_blind_planning_rule(_state("The House"))
    unknown = boss_blind_planning_rule(_state("The Goad"))

    assert psychic is not None
    assert psychic.required_play_cards == 5
    assert head is not None
    assert head.evaluator_factory is not None
    assert house is not None
    assert house.required_play_cards is None
    assert house.evaluator_factory is None
    assert unknown is None


def test_d1_psychic_filters_root_and_recursive_play_candidates_to_five_cards():
    state = _state("The Psychic")
    planner = D1LiveBlindClearPlanner(
        play_width=20,
        discard_width=0,
        horizon=2,
    )

    root = planner._candidate_actions(state, allow_discards=False)
    root_plays = [action for action in root if action.name == PLAY_CARDS]

    assert root_plays
    assert all(len(action.cards) == 5 for action in root_plays)

    planner.nodes_evaluated = 1
    recursive = planner._candidate_actions(
        state,
        allow_discards=False,
        play_width=20,
        discard_width=0,
    )
    recursive_plays = [action for action in recursive if action.name == PLAY_CARDS]

    assert recursive_plays
    assert all(len(action.cards) == 5 for action in recursive_plays)


def test_d1_head_uses_validated_head_score_projection_automatically():
    state = _state("The Head")
    ice_cream = IceCreamJoker()
    ice_cream.chips = 70
    state.jokers = [ice_cream, BootstrapsJoker()]

    planner = D1LiveBlindClearPlanner(horizon=1)
    assert isinstance(planner.evaluator, BossAwareLiveHandDecisionEvaluator)

    cards = [state.hand[6], state.hand[7]]
    projection = planner.evaluator.project_play(
        state,
        BalatroAction(PLAY_CARDS, cards=cards),
    )

    # Pair base 10 chips + only the non-debuffed 2 of Clubs + Ice Cream 70.
    # Pair base 2 mult + Bootstraps at $20 (+8 mult) = 820 total.
    assert projection.hand_score == 820
    assert projection.expected_hand_score == 820.0


def test_d1_house_keeps_normal_play_legality():
    state = _state("The House")
    planner = D1LiveBlindClearPlanner(
        play_width=20,
        discard_width=0,
        horizon=1,
    )

    candidates = planner._candidate_actions(state, allow_discards=False)
    plays = [action for action in candidates if action.name == PLAY_CARDS]

    assert plays
    assert any(len(action.cards) < 5 for action in plays)
