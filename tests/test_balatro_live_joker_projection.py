from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.bootstraps import BootstrapsJoker
from games.balatro.jokers.green_joker import GreenJoker
from games.balatro.jokers.ice_cream import IceCreamJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.loyalty_card import LoyaltyCardJoker
from games.balatro.jokers.lucky_cat import LuckyCatJoker
from games.balatro.jokers.runner import RunnerJoker
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.external.save_observer import _normalize_item
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(hand, deck=None, *, target=1000, hands=2, discards=0):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(hand)
    state.deck = list(deck or [])
    state.score = 0
    state.hands_remaining = hands
    state.discards_remaining = discards
    state.blind = Blind(BlindType.BIG, target)
    return state


def test_ice_cream_projection_scores_and_decays_only_copied_joker():
    cards = [
        BalatroCard("K", "Spades", live_id=0),
        BalatroCard("K", "Diamonds", live_id=1),
    ]
    state = _state(cards)
    ice_cream = IceCreamJoker()
    state.jokers = [ice_cream]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    # Pair: (10 base + 20 rank chips + 100 Ice Cream) * 2 Mult.
    assert transition.distribution.minimum == 260
    assert transition.joker_projection_complete is True
    assert ice_cream.chips == 100
    assert transition.state_after_scoring is not state
    assert transition.state_after_scoring.hand is not state.hand
    # Playing cards intentionally retain identity across the cheap branch copy;
    # scorer held-card logic depends on the played objects matching branch.hand.
    assert transition.state_after_scoring.hand[0] is cards[0]
    assert transition.state_after_scoring.hand[1] is cards[1]
    assert transition.state_after_scoring.jokers[0] is not ice_cream
    assert transition.state_after_scoring.jokers[0].chips == 95


def test_green_joker_projection_starts_from_hydrated_mult_and_updates_only_copy():
    cards = [
        BalatroCard("K", "Spades", live_id=0),
        BalatroCard("K", "Diamonds", live_id=1),
    ]
    state = _state(cards)
    green = GreenJoker()
    green.mult = 19
    state.jokers = [green]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    # HAND_SCORED grows Green Joker from +19 to +20 Mult on the copied branch.
    # Pair K,K contributes 30 Chips and base Mult 2, so 30 * 22 = 660.
    assert transition.distribution.minimum == 660
    assert transition.distribution.maximum == 660
    assert transition.joker_projection_complete is True
    assert green.mult == 19
    assert transition.state_after_scoring.jokers[0].mult == 20


def test_runner_projection_starts_from_hydrated_chips_and_carries_growth():
    cards = [
        BalatroCard("2", "Spades", live_id=0),
        BalatroCard("3", "Hearts", live_id=1),
        BalatroCard("4", "Clubs", live_id=2),
        BalatroCard("5", "Diamonds", live_id=3),
        BalatroCard("6", "Spades", live_id=4),
    ]
    state = _state(cards)
    runner = RunnerJoker()
    runner.chips = 45
    state.jokers = [runner]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.STRAIGHT,
        state,
        cards,
    )

    # Visible straight is 30 base + 20 card Chips. Runner grows 45 -> 60 and then
    # contributes the copied value: (50 + 60) * 4 = 440.
    assert transition.distribution.minimum == 440
    assert transition.distribution.maximum == 440
    assert transition.joker_projection_complete is True
    assert runner.chips == 45
    assert transition.state_after_scoring.jokers[0].chips == 60


def test_bootstraps_projection_adds_only_mult_from_public_money():
    ace = BalatroCard("A", "Spades", live_id=0)
    state = _state([ace])
    state.money = 5
    bootstraps = BootstrapsJoker()
    state.jokers = [bootstraps]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    # High Card A is 16 Chips x 1 Mult before Jokers. At $5 Bootstraps adds
    # exactly +2 Mult and no Chips: 16 x 3 = 48.
    assert transition.distribution.minimum == 48
    assert transition.distribution.maximum == 48
    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert state.money == 5
    assert transition.state_after_scoring.money == 5
    assert transition.state_after_scoring.jokers[0] is not bootstraps


def test_bootstraps_and_ice_cream_project_together_without_mutating_observed_state():
    cards = [
        BalatroCard("K", "Spades", live_id=0),
        BalatroCard("K", "Diamonds", live_id=1),
    ]
    state = _state(cards)
    state.money = 5
    ice_cream = IceCreamJoker()
    ice_cream.chips = 85
    bootstraps = BootstrapsJoker()
    state.jokers = [ice_cream, bootstraps]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    # Pair K,K: 10 base + 20 rank chips + 85 Ice Cream = 115 Chips.
    # Pair base Mult 2 + Bootstraps 2 at $5 = 4 Mult. 115 x 4 = 460.
    assert transition.distribution.minimum == 460
    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert ice_cream.chips == 85
    assert transition.state_after_scoring.jokers[0].chips == 80
    assert isinstance(transition.state_after_scoring.jokers[1], BootstrapsJoker)


def test_two_action_planner_carries_ice_cream_decay_into_second_play():
    ace = BalatroCard("A", "Spades", live_id=0)
    state = _state(
        [ace],
        [BalatroCard("K", "Hearts")],
        target=1000,
        hands=2,
        discards=0,
    )
    ice_cream = IceCreamJoker()
    state.jokers = [ice_cream]

    planner = LiveBlindClearPlanner(
        play_width=1,
        discard_width=0,
        horizon=2,
    )
    plan = planner.plan(state)

    # First High Card A: (5 + 11 + 100) * 1 = 116.
    # Second High Card K after Ice Cream decay: (5 + 10 + 95) * 1 = 110.
    assert plan.action.name == PLAY_CARDS
    assert plan.value.expected_score == 226.0
    assert plan.exact is True
    assert ice_cream.chips == 100


def test_event_incompatible_hydrated_jokers_remain_fail_closed():
    ace = BalatroCard("A", "Spades")
    state = _state([ace])

    loyalty = LoyaltyCardJoker()
    loyalty.hands = 5
    lucky_cat = LuckyCatJoker()
    lucky_cat.x_mult = 2.0
    state.jokers = [loyalty, lucky_cat]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    # The projector must not claim exactness while HAND_PLAYED/LUCKY_TRIGGERED
    # branch semantics are still absent. Neither deferred Joker is partially
    # applied to the score.
    assert transition.distribution.minimum == 16
    assert transition.joker_projection_complete is False
    assert transition.unsupported_jokers == ("LoyaltyCard", "LuckyCat")
    assert loyalty.hands == 5
    assert lucky_cat.x_mult == 2.0


def test_unsupported_joker_is_reported_and_not_silently_applied():
    cards = [
        BalatroCard("10", "Spades"),
        BalatroCard("10", "Diamonds"),
    ]
    state = _state(cards)
    state.jokers = [JollyJoker()]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    assert transition.distribution.minimum == 60
    assert transition.joker_projection_complete is False
    assert transition.unsupported_jokers == ("Jolly",)


def test_ice_cream_public_save_state_is_narrowly_whitelisted_and_restored():
    normalized = _normalize_item(
        {
            "sort_id": 77,
            "label": "Ice Cream",
            "save_fields": {"center": "j_ice_cream"},
            "ability": {
                "name": "Ice Cream",
                "set": "Joker",
                "extra": {
                    "chips": 65,
                    "chip_mod": 5,
                    "private_test_field": 12345,
                },
            },
        }
    )

    assert normalized["public_state"] == {
        "chips": 65,
        "chip_mod": 5,
    }
    assert "ability" not in normalized
    assert "private_test_field" not in normalized["public_state"]

    joker = LiveJokerFactory().create(normalized)
    assert isinstance(joker, IceCreamJoker)
    assert joker.chips == 65
    assert joker.chip_mod == 5
    assert joker.live_id == 77
