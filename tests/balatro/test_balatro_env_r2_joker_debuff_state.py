from games.balatro.hand import PokerHand
from games.balatro.joker import JokerContext
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.green_joker import GreenJoker
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.scoring import HandScore
from games.balatro.state import BalatroState


def test_env_r2_live_joker_factory_hydrates_public_debuff_bit():
    factory = LiveJokerFactory()

    joker = factory.create(
        {
            "center": "j_joker",
            "label": "Joker",
            "debuff": True,
        }
    )

    assert isinstance(joker, FlatMultJoker)
    assert joker.debuffed is True


def test_env_r2_live_joker_factory_rejects_malformed_debuff_bit():
    factory = LiveJokerFactory()

    assert factory.create(
        {
            "center": "j_joker",
            "label": "Joker",
            "debuff": 1,
        }
    ) is None


def test_env_r2_debuffed_joker_apply_is_inert_for_hand_scored_effect():
    state = BalatroState()
    joker = FlatMultJoker(4)
    joker.debuffed = True
    context = JokerContext(
        state=state,
        score=HandScore(5, 1),
        poker_hand=PokerHand.HIGH_CARD,
        trigger="HAND_SCORED",
    )

    result = joker.apply(context)

    assert result is context
    assert result.score.mult == 1


def test_env_r2_debuffed_joker_apply_is_inert_for_mutating_trigger():
    state = BalatroState()
    joker = GreenJoker()
    joker.mult = 7
    joker.debuffed = True
    context = JokerContext(
        state=state,
        score=HandScore(5, 1),
        poker_hand=PokerHand.HIGH_CARD,
        trigger="HAND_SCORED",
    )

    result = joker.apply(context)

    assert result is context
    assert joker.mult == 7
    assert result.score.mult == 1


def test_env_r2_clearing_debuff_restores_ordinary_joker_behavior():
    state = BalatroState()
    joker = FlatMultJoker(4)
    joker.debuffed = True
    joker.debuffed = False
    context = JokerContext(
        state=state,
        score=HandScore(5, 1),
        poker_hand=PokerHand.HIGH_CARD,
        trigger="HAND_SCORED",
    )

    result = joker.apply(context)

    assert result.score.mult == 5
