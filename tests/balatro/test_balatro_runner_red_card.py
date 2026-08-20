from games.balatro.events import BalatroEvent, BalatroEventType
from games.balatro.hand import PokerHand
from games.balatro.joker import JokerContext
from games.balatro.jokers.red_card import RedCardJoker
from games.balatro.jokers.runner import RunnerJoker
from games.balatro.scoring import HandScore
from games.balatro.state import BalatroState


def _context(*, hand=None, event=None, chips=0, mult=1):
    return JokerContext(
        state=BalatroState(),
        score=HandScore(chips=chips, mult=mult),
        poker_hand=hand,
        event=event,
    )


def test_red_card_only_scales_when_booster_pack_is_skipped():
    joker = RedCardJoker()

    joker.apply(_context(event=BalatroEvent(BalatroEventType.VOUCHER_SKIPPED)))
    assert joker.mult == 0

    skipped = _context(event=BalatroEvent(BalatroEventType.BOOSTER_SKIPPED))
    joker.apply(skipped)
    assert joker.mult == 3
    assert skipped.score.mult == 4

    scored = _context(hand=PokerHand.HIGH_CARD)
    joker.apply(scored)
    assert scored.score.mult == 4


def test_red_card_booster_skips_stack():
    joker = RedCardJoker()
    joker.apply(_context(event=BalatroEvent(BalatroEventType.BOOSTER_SKIPPED)))
    joker.apply(_context(event=BalatroEvent(BalatroEventType.BOOSTER_SKIPPED)))

    scored = _context(hand=PokerHand.PAIR)
    joker.apply(scored)

    assert joker.mult == 6
    assert scored.score.mult == 7


def test_runner_keeps_accumulated_chips_on_non_straight_hands():
    joker = RunnerJoker()

    straight = _context(hand=PokerHand.STRAIGHT)
    joker.apply(straight)
    assert joker.chips == 15
    assert straight.score.chips == 15

    pair = _context(hand=PokerHand.PAIR)
    joker.apply(pair)
    assert joker.chips == 15
    assert pair.score.chips == 15


def test_runner_straight_flush_contains_a_straight_for_growth():
    joker = RunnerJoker()
    joker.chips = 15

    straight_flush = _context(hand=PokerHand.STRAIGHT_FLUSH)
    joker.apply(straight_flush)

    assert joker.chips == 30
    assert straight_flush.score.chips == 30
