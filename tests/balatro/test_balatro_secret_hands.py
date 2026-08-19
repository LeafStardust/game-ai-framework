from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.live.final_joker_outcomes import LiveFinalJokerScoreOutcomeModel
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.state import BalatroState


def _state(cards):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.owned_deck = list(cards)
    return state


def test_hand_evaluator_recognizes_all_three_secret_hands():
    five_kind = [
        BalatroCard("K", suit)
        for suit in ("Hearts", "Diamonds", "Clubs", "Spades", "Hearts")
    ]
    flush_house = [
        BalatroCard("K", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("Q", "Hearts"),
    ]
    flush_five = [BalatroCard("K", "Hearts") for _ in range(5)]

    evaluator = HandEvaluator()

    assert evaluator.evaluate(five_kind) == PokerHand.FIVE_OF_A_KIND
    assert evaluator.evaluate(flush_house) == PokerHand.FLUSH_HOUSE
    assert evaluator.evaluate(flush_five) == PokerHand.FLUSH_FIVE


def test_secret_hands_preserve_lower_component_membership():
    flush_house = [
        BalatroCard("K", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("Q", "Hearts"),
    ]
    flush_five = [BalatroCard("K", "Hearts") for _ in range(5)]
    evaluator = HandEvaluator()

    assert evaluator.contains(flush_house, PokerHand.FLUSH_HOUSE)
    assert evaluator.contains(flush_house, PokerHand.FULL_HOUSE)
    assert evaluator.contains(flush_house, PokerHand.FLUSH)
    assert evaluator.contains(flush_five, PokerHand.FLUSH_FIVE)
    assert evaluator.contains(flush_five, PokerHand.FIVE_OF_A_KIND)
    assert evaluator.contains(flush_five, PokerHand.FOUR_OF_A_KIND)
    assert evaluator.contains(flush_five, PokerHand.FLUSH)


def test_final_live_scorer_uses_exact_secret_hand_base_values():
    five_kind = [
        BalatroCard("K", suit)
        for suit in ("Hearts", "Diamonds", "Clubs", "Spades", "Hearts")
    ]
    flush_house = [
        BalatroCard("K", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("Q", "Hearts"),
    ]
    flush_five = [BalatroCard("K", "Hearts") for _ in range(5)]
    model = LiveFinalJokerScoreOutcomeModel()

    five = model.project(PokerHand.FIVE_OF_A_KIND, _state(five_kind), five_kind)
    house = model.project(PokerHand.FLUSH_HOUSE, _state(flush_house), flush_house)
    flush = model.project(PokerHand.FLUSH_FIVE, _state(flush_five), flush_five)

    # Five Kings contribute 50 card chips after each category's base chips.
    assert five.minimum == (120 + 50) * 12
    assert house.minimum == (140 + 50) * 14
    assert flush.minimum == (160 + 50) * 16


def test_secret_planet_level_gain_is_used_by_live_projection():
    cards = [BalatroCard("K", "Hearts") for _ in range(5)]
    state = _state(cards)
    state.hand_levels["FLUSH_FIVE"] = 2

    distribution = LiveFinalJokerScoreOutcomeModel().project(
        PokerHand.FLUSH_FIVE,
        state,
        cards,
    )

    # Eris adds +50 Chips and +3 Mult per level.
    assert distribution.minimum == (160 + 50 + 50) * (16 + 3)


def test_live_translator_imports_secret_hand_levels_and_history():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "hands": {
                "Five of a Kind": {
                    "level": 2,
                    "played": 3,
                    "played_this_round": 1,
                },
                "Flush House": {
                    "level": 4,
                    "played": 2,
                    "played_this_round": 0,
                },
                "Flush Five": {
                    "level": 5,
                    "played": 1,
                    "played_this_round": 1,
                },
            }
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.hand_levels["FIVE_OF_A_KIND"] == 2
    assert state.hand_play_counts["FIVE_OF_A_KIND"] == 3
    assert state.round_hand_play_counts["FIVE_OF_A_KIND"] == 1
    assert state.hand_levels["FLUSH_HOUSE"] == 4
    assert state.hand_levels["FLUSH_FIVE"] == 5
    assert state.hand_play_counts["FLUSH_FIVE"] == 1
