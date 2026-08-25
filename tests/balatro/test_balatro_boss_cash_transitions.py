from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.state import BalatroState


def _state(boss_name: str, *, money: int, jokers=None) -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.boss_name = boss_name
    state.blind = Blind(BlindType.BOSS, 10_000)
    state.money = money
    state.hand = [
        BalatroCard("A", "Spades", live_id=1),
        BalatroCard("9", "Hearts", live_id=2),
        BalatroCard("4", "Clubs", live_id=3),
    ]
    state.jokers = list(jokers or [])
    return state


def test_tooth_charges_each_played_card_before_cash_scaler_scoring():
    state = _state("The Tooth", money=2, jokers=[BullJoker()])
    action = BalatroAction(PLAY_CARDS, cards=list(state.hand))

    projection = LiveHandDecisionEvaluator().project_play(state, action)

    assert projection.state_after_scoring is not None
    assert projection.state_after_scoring.money == -1
    # Bull clamps its own chip contribution at zero once The Tooth has already
    # driven the branch below $0; it must not score from the pre-Tooth $2.
    assert projection.hand_score == 19


def test_ox_resets_money_before_cash_scaler_scoring_on_target_hand():
    state = _state("The Ox", money=100, jokers=[BullJoker()])
    state.round_most_played_hand = "HIGH_CARD"
    action = BalatroAction(PLAY_CARDS, cards=[state.hand[0]])

    projection = LiveHandDecisionEvaluator().project_play(state, action)

    assert projection.state_after_scoring is not None
    assert projection.state_after_scoring.money == 0
    # Aces contribute 11 card chips to High Card's 5x1 base. If Bull had read
    # the pre-Ox $100 this branch would contain another +200 chips.
    assert projection.hand_score == 16


def test_chicot_disables_tooth_cash_loss():
    state = _state("The Tooth", money=2, jokers=[ChicotJoker(), BullJoker()])
    action = BalatroAction(PLAY_CARDS, cards=list(state.hand))

    projection = LiveHandDecisionEvaluator().project_play(state, action)

    assert projection.state_after_scoring is not None
    assert projection.state_after_scoring.money == 2
    assert projection.hand_score > 19


def test_chicot_disables_ox_cash_reset():
    state = _state("The Ox", money=100, jokers=[ChicotJoker(), BullJoker()])
    state.round_most_played_hand = "HIGH_CARD"
    action = BalatroAction(PLAY_CARDS, cards=[state.hand[0]])

    projection = LiveHandDecisionEvaluator().project_play(state, action)

    assert projection.state_after_scoring is not None
    assert projection.state_after_scoring.money == 100
    assert projection.hand_score > 16
