from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel
from games.balatro.state import BalatroState


def _state(hand, deck, *, score=0, target=300, hands=2, discards=1):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = hand
    state.deck = deck
    state.score = score
    state.hands_remaining = hands
    state.discards_remaining = discards
    state.blind = Blind(BlindType.SMALL, target)
    state.jokers = []
    return state


def _planner(**kwargs):
    return LiveBlindClearPlanner(
        draw_outcomes=PublicDrawOutcomeModel(
            exact_combination_limit=10_000,
            sample_count=64,
            seed=1,
        ),
        play_width=8,
        discard_width=6,
        horizon=2,
        **kwargs,
    )


def test_planner_takes_guaranteed_immediate_pair_clear():
    state = _state(
        [
            BalatroCard("10", "Spades", live_id=0),
            BalatroCard("10", "Diamonds", live_id=1),
            BalatroCard("8", "Clubs", live_id=2),
            BalatroCard("5", "Hearts", live_id=3),
        ],
        [BalatroCard("2", "Clubs")],
        target=60,
        hands=2,
        discards=1,
    )

    plan = _planner().plan(state)

    assert plan.action.name == PLAY_CARDS
    assert [card.rank for card in plan.action.cards] == ["10", "10"]
    assert plan.value.clear_probability == 1.0
    assert plan.exact is True


def test_planner_discards_offsuit_card_for_guaranteed_flush_next_play():
    off_suit = BalatroCard("2", "Hearts", live_id=4)
    state = _state(
        [
            BalatroCard("A", "Spades", live_id=0),
            BalatroCard("K", "Spades", live_id=1),
            BalatroCard("Q", "Spades", live_id=2),
            BalatroCard("8", "Spades", live_id=3),
            off_suit,
        ],
        [BalatroCard("3", "Spades")],
        target=300,
        hands=1,
        discards=1,
    )

    plan = _planner().plan(state)

    assert plan.action.name == DISCARD_CARDS
    assert plan.action.cards == [off_suit]
    assert plan.value.clear_probability == 1.0
    assert plan.exact is True


def test_planner_reports_contingent_half_chance_flush_from_public_draw():
    off_suit = BalatroCard("2", "Hearts", live_id=4)
    state = _state(
        [
            BalatroCard("A", "Spades", live_id=0),
            BalatroCard("K", "Spades", live_id=1),
            BalatroCard("Q", "Spades", live_id=2),
            BalatroCard("8", "Spades", live_id=3),
            off_suit,
        ],
        [
            BalatroCard("3", "Spades"),
            BalatroCard("3", "Hearts"),
        ],
        target=300,
        hands=1,
        discards=1,
    )

    plan = _planner().plan(state)

    assert plan.action.name == DISCARD_CARDS
    assert plan.action.cards == [off_suit]
    assert abs(plan.value.clear_probability - 0.5) < 1e-12
    assert plan.exact is True


def test_planner_can_choose_play_that_sets_up_guaranteed_second_play():
    ace = BalatroCard("A", "Spades", live_id=0)
    state = _state(
        [
            ace,
            BalatroCard("K", "Hearts", live_id=1),
            BalatroCard("2", "Clubs", live_id=2),
        ],
        [BalatroCard("K", "Spades")],
        target=70,
        hands=2,
        discards=0,
    )

    plan = _planner().plan(state)

    assert plan.action.name == PLAY_CARDS
    assert plan.action.cards == [ace]
    assert plan.value.clear_probability == 1.0
    assert plan.exact is True


def test_guaranteed_immediate_clear_preserves_discard_over_two_action_clear():
    state = _state(
        [
            BalatroCard("10", "Spades", live_id=0),
            BalatroCard("10", "Diamonds", live_id=1),
            BalatroCard("A", "Clubs", live_id=2),
            BalatroCard("4", "Hearts", live_id=3),
        ],
        [BalatroCard("10", "Clubs")],
        target=60,
        hands=2,
        discards=1,
    )

    plan = _planner().plan(state)

    assert plan.action.name == PLAY_CARDS
    assert plan.value.clear_probability == 1.0
    assert plan.value.expected_discards_remaining == 1.0


def test_default_live_planner_bounds_draw_branching():
    planner = LiveBlindClearPlanner()

    assert (
        planner.draw_outcomes.exact_combination_limit
        == LiveBlindClearPlanner.DEFAULT_EXACT_DRAW_COMBINATION_LIMIT
        == 128
    )
    assert (
        planner.draw_outcomes.sample_count
        == LiveBlindClearPlanner.DEFAULT_DRAW_SAMPLE_COUNT
        == 64
    )
