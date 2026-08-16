from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.bootstraps import BootstrapsJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.jokers.matador import MatadorJoker
from games.balatro.jokers.misprint import MisprintJoker
from games.balatro.live.final_joker_outcomes import LiveFinalJokerScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(boss_name: str, cards):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.blind = Blind(BlindType.BOSS, 10_000)
    state.boss_name = boss_name
    state.hand = list(cards)
    state.owned_deck = list(cards)
    state.deck = []
    state.hands_remaining = 4
    state.discards_remaining = 3
    state.discards_used = 0
    state.hand_size = len(cards)
    return state


def _project(state, hand, cards):
    return LiveFinalJokerScoreOutcomeModel().project_transition(
        hand,
        state,
        cards,
    )


def test_arm_scores_with_lower_level_then_persists_level_loss_and_pays_matador():
    ace = BalatroCard("A", "Spades", live_id=1)
    state = _state("The Arm", [ace])
    state.hand_levels[PokerHand.HIGH_CARD.value] = 2
    state.money = 0
    state.jokers = [MatadorJoker()]

    transition = _project(state, PokerHand.HIGH_CARD, [ace])
    branch = transition.distribution.outcomes[0].state_after_scoring

    # Level 2 High Card is normally 15x2 before cards. Arm scores it at Level 1:
    # 5x1 + Ace's 11 chips = 16. Matador sees the pre-effect Level 2 and earns $8.
    assert transition.distribution.minimum == 16
    assert branch.hand_levels[PokerHand.HIGH_CARD.value] == 1
    assert branch.money == 8
    assert state.hand_levels[PokerHand.HIGH_CARD.value] == 2
    assert state.money == 0


def test_arm_cannot_reduce_level_one_and_does_not_trigger_matador_there():
    ace = BalatroCard("A", "Spades", live_id=1)
    state = _state("The Arm", [ace])
    state.hand_levels[PokerHand.HIGH_CARD.value] = 1
    state.money = 0
    state.jokers = [MatadorJoker()]

    transition = _project(state, PokerHand.HIGH_CARD, [ace])
    branch = transition.distribution.outcomes[0].state_after_scoring

    assert transition.distribution.minimum == 16
    assert branch.hand_levels[PokerHand.HIGH_CARD.value] == 1
    assert branch.money == 0


def test_chicot_suppresses_arm_level_loss_and_base_transform():
    ace = BalatroCard("A", "Spades", live_id=1)
    state = _state("The Arm", [ace])
    state.hand_levels[PokerHand.HIGH_CARD.value] = 2
    state.jokers = [ChicotJoker()]

    transition = _project(state, PokerHand.HIGH_CARD, [ace])
    branch = transition.distribution.outcomes[0].state_after_scoring

    # Level 2 High Card: (5+10 + Ace 11) x (1+1) = 52.
    assert transition.distribution.minimum == 52
    assert branch.hand_levels[PokerHand.HIGH_CARD.value] == 2


def test_flint_halves_only_leveled_base_chips_and_mult_with_round_up():
    two_a = BalatroCard("2", "Spades", live_id=1)
    two_b = BalatroCard("2", "Hearts", live_id=2)
    state = _state("The Flint", [two_a, two_b])
    state.hand_levels[PokerHand.PAIR.value] = 2

    transition = _project(state, PokerHand.PAIR, [two_a, two_b])

    # Level 2 Pair base is 25x3. Flint rounds that to 13x2, then the two 2s
    # contribute their ordinary 4 card chips: 17x2 = 34.
    assert transition.distribution.minimum == 34
    assert transition.distribution.maximum == 34


def test_flint_does_not_halve_playing_card_or_edition_chips():
    ace = BalatroCard("A", "Spades", edition="Foil", live_id=1)
    state = _state("The Flint", [ace])

    transition = _project(state, PokerHand.HIGH_CARD, [ace])

    # Base 5x1 -> Flint 3x1; Ace +11 and Foil +50 remain untouched.
    assert transition.distribution.minimum == 64


def test_flint_transform_survives_misprint_stochastic_replay():
    ace = BalatroCard("A", "Spades", live_id=1)
    state = _state("The Flint", [ace])
    state.jokers = [MisprintJoker()]

    transition = _project(state, PokerHand.HIGH_CARD, [ace])

    # Flint leaves 14 chips x1 before Misprint. Exact +0..23 Mult branches must
    # therefore span 14 through 14*24, proving nested stochastic scorers inherit it.
    assert len(transition.distribution.outcomes) == 24
    assert transition.distribution.minimum == 14
    assert transition.distribution.maximum == 336


def test_chicot_suppresses_flint():
    ace = BalatroCard("A", "Spades", live_id=1)
    state = _state("The Flint", [ace])
    state.jokers = [ChicotJoker()]

    transition = _project(state, PokerHand.HIGH_CARD, [ace])

    assert transition.distribution.minimum == 16


def test_tooth_charges_every_played_card_before_bull_scores():
    cards = [
        BalatroCard("A", "Spades", live_id=1),
        BalatroCard("2", "Hearts", live_id=2),
        BalatroCard("3", "Clubs", live_id=3),
    ]
    state = _state("The Tooth", cards)
    state.money = 5
    state.jokers = [BullJoker()]

    transition = _project(state, PokerHand.HIGH_CARD, cards)
    branch = transition.distribution.outcomes[0].state_after_scoring

    # Tooth: $5 -> $2 before Bull, so Bull adds only 4 chips. High Card Ace is 16.
    assert transition.distribution.minimum == 20
    assert branch.money == 2
    assert state.money == 5


def test_tooth_reduced_money_is_visible_to_bootstraps_in_same_hand():
    cards = [
        BalatroCard("A", "Spades", live_id=1),
        BalatroCard("2", "Hearts", live_id=2),
        BalatroCard("3", "Clubs", live_id=3),
    ]
    state = _state("The Tooth", cards)
    state.money = 12
    state.jokers = [BootstrapsJoker()]

    transition = _project(state, PokerHand.HIGH_CARD, cards)
    branch = transition.distribution.outcomes[0].state_after_scoring

    # $12 -> $9, so Bootstraps contributes +2 Mult rather than +4.
    assert transition.distribution.minimum == 48
    assert branch.money == 9


def test_tooth_can_push_money_negative_and_does_not_trigger_matador():
    cards = [
        BalatroCard("A", "Spades", live_id=1),
        BalatroCard("2", "Hearts", live_id=2),
        BalatroCard("3", "Clubs", live_id=3),
    ]
    state = _state("The Tooth", cards)
    state.money = 1
    state.jokers = [MatadorJoker()]

    transition = _project(state, PokerHand.HIGH_CARD, cards)
    branch = transition.distribution.outcomes[0].state_after_scoring

    assert branch.money == -2


def test_chicot_suppresses_tooth_money_loss():
    cards = [
        BalatroCard("A", "Spades", live_id=1),
        BalatroCard("2", "Hearts", live_id=2),
        BalatroCard("3", "Clubs", live_id=3),
    ]
    state = _state("The Tooth", cards)
    state.money = 5
    state.jokers = [ChicotJoker(), BullJoker()]

    transition = _project(state, PokerHand.HIGH_CARD, cards)
    branch = transition.distribution.outcomes[0].state_after_scoring

    assert branch.money == 5
    assert transition.distribution.minimum == 26
