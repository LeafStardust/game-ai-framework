from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.bootstraps import BootstrapsJoker
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.jokers.ice_cream import IceCreamJoker
from games.balatro.jokers.luchador import LuchadorJoker
from games.balatro.live.boss_blind_integration import (
    BossAwareLiveHandDecisionEvaluator,
    boss_blind_planning_rule,
    boss_play_action_is_legal,
)
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.live.post_hand_outcomes import LiveVisibleCardScoreOutcomeModel
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
    eye = boss_blind_planning_rule(_state("The Eye"))
    mouth = boss_blind_planning_rule(_state("The Mouth"))
    head = boss_blind_planning_rule(_state("The Head"))
    house = boss_blind_planning_rule(_state("The House"))
    goad = boss_blind_planning_rule(_state("The Goad"))

    assert psychic is not None
    assert psychic.required_play_cards is None
    assert eye is not None
    assert eye.required_play_cards is None
    assert mouth is not None
    assert mouth.required_play_cards is None
    assert head is not None
    assert head.evaluator_factory is not None
    assert house is not None
    assert house.required_play_cards is None
    assert house.evaluator_factory is None
    assert goad is not None
    assert goad.required_play_cards is None
    assert goad.evaluator_factory is None


def test_d1_psychic_keeps_short_and_five_card_play_candidates_legal():
    state = _state("The Psychic")
    planner = D1LiveBlindClearPlanner(
        play_width=100,
        discard_width=0,
        horizon=2,
    )

    root = planner._candidate_actions(state, allow_discards=False)
    root_plays = [action for action in root if action.name == PLAY_CARDS]

    assert root_plays
    assert any(len(action.cards) < 5 for action in root_plays)
    assert any(len(action.cards) == 5 for action in root_plays)

    planner.nodes_evaluated = 1
    recursive = planner._candidate_actions(
        state,
        allow_discards=False,
        play_width=100,
        discard_width=0,
    )
    recursive_plays = [action for action in recursive if action.name == PLAY_CARDS]

    assert recursive_plays
    assert any(len(action.cards) < 5 for action in recursive_plays)
    assert any(len(action.cards) == 5 for action in recursive_plays)


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


def test_d1_head_prefers_non_debuffed_clearing_card_over_higher_debuffed_rank():
    state = _state("The Head")
    debuffed_king = BalatroCard("K", "Hearts", live_id=0)
    live_queen = BalatroCard("Q", "Clubs", live_id=1)
    state.hand = [debuffed_king, live_queen]
    state.deck = []
    state.jokers = []
    state.hands_remaining = 1
    state.discards_remaining = 0
    state.blind = Blind(BlindType.BOSS, 15)

    plan = D1LiveBlindClearPlanner(
        horizon=1,
        play_width=8,
        discard_width=0,
    ).plan(state)

    # If The Head's disabled Heart were valued like an ordinary King, it would
    # outrank the Queen. Correct boss scoring gives the King only the High Card
    # base (5), while the live Queen contributes 10 rank chips and clears at 15.
    assert plan.action.name == PLAY_CARDS
    assert plan.action.cards == [live_queen]
    assert plan.value.clear_probability == 1.0


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


def test_chicot_disables_psychic_boss_rule_while_short_play_remains_legal():
    state = _state("The Psychic")
    state.jokers = [ChicotJoker()]
    short_play = BalatroAction(PLAY_CARDS, cards=[state.hand[0]])

    assert boss_blind_planning_rule(state) is None
    assert boss_play_action_is_legal(state, short_play) is True

    plays = D1LiveBlindClearPlanner(
        play_width=20,
        discard_width=0,
        horizon=1,
    )._candidate_actions(state, allow_discards=False)
    assert plays
    assert any(len(action.cards) < 5 for action in plays)


def test_chicot_disables_head_specific_evaluator_while_owned():
    state = _state("The Head")
    state.jokers = [ChicotJoker()]
    evaluator = BossAwareLiveHandDecisionEvaluator()

    assert boss_blind_planning_rule(state) is None
    assert evaluator.evaluator_for_state(state) is evaluator


def test_luchador_keeps_psychic_rule_active_but_does_not_make_short_play_illegal():
    state = _state("The Psychic")
    state.jokers = [LuchadorJoker()]
    short_play = BalatroAction(PLAY_CARDS, cards=[state.hand[0]])

    rule = boss_blind_planning_rule(state)
    assert rule is not None
    assert rule.required_play_cards is None
    assert boss_play_action_is_legal(state, short_play) is True


def test_chicot_and_luchador_do_not_block_current_hand_score_projection():
    ace = BalatroCard("A", "Spades")
    state = _state("The House")
    state.hand = [ace]
    state.deck = []
    state.jokers = [ChicotJoker(), LuchadorJoker()]

    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 16
    assert transition.distribution.maximum == 16
