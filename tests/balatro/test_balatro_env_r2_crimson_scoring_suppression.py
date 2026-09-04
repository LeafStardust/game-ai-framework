from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.seltzer import SeltzerJoker
from games.balatro.live.joker_projection import LiveJokerScoreProjector
from games.balatro.state import BalatroState


class UnsupportedTestJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is not None:
            context.score.mult += 999
        return context


def _state(joker) -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.jokers = [joker]
    return state


def test_env_r2_debuffed_joker_is_removed_from_entire_score_projection():
    joker = FlatMultJoker(4)
    joker.edition = "Foil"
    joker.debuffed = True
    card = BalatroCard("A", "Spades")

    result = LiveJokerScoreProjector().score(
        PokerHand.HIGH_CARD,
        _state(joker),
        [card],
        include_card_chips=True,
    )

    # Base High Card 5/1 plus Ace chips 11; neither +4 Mult nor Foil +50 chips.
    assert result.score.chips == 16
    assert result.score.mult == 1
    assert result.complete
    assert result.unsupported_jokers == ()
    assert result.state_after_scoring.jokers[0].debuffed is True


def test_env_r2_debuffed_seltzer_does_not_retrigger_or_consume_round_counter():
    joker = SeltzerJoker()
    joker.debuffed = True
    card = BalatroCard("2", "Clubs")

    result = LiveJokerScoreProjector().score(
        PokerHand.HIGH_CARD,
        _state(joker),
        [card],
        include_card_chips=True,
    )

    assert result.played_card_retriggers == 0
    assert result.state_after_scoring.jokers[0].rounds_remaining == 10
    assert result.state_after_scoring.jokers[0].debuffed is True


def test_env_r2_debuffed_unsupported_joker_does_not_make_projection_incomplete():
    joker = UnsupportedTestJoker()
    joker.debuffed = True

    result = LiveJokerScoreProjector().score(
        PokerHand.HIGH_CARD,
        _state(joker),
        [],
        include_card_chips=True,
    )

    assert result.complete
    assert result.unsupported_jokers == ()
    assert result.score.mult == 1


def test_env_r2_active_unsupported_joker_still_fails_closed():
    joker = UnsupportedTestJoker()
    joker.debuffed = False

    result = LiveJokerScoreProjector().score(
        PokerHand.HIGH_CARD,
        _state(joker),
        [],
        include_card_chips=True,
    )

    assert not result.complete
    assert result.unsupported_jokers == ("UnsupportedTest",)


def test_env_r2_cleared_debuff_restores_normal_projection():
    joker = FlatMultJoker(4)
    joker.debuffed = False

    result = LiveJokerScoreProjector().score(
        PokerHand.HIGH_CARD,
        _state(joker),
        [],
        include_card_chips=True,
    )

    assert result.complete
    assert result.score.mult == 5
