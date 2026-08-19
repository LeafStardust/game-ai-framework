from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.abstract_joker import AbstractJoker
from games.balatro.jokers.acrobat import AcrobatJoker
from games.balatro.jokers.blue_joker import BlueJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.cavendish import CavendishJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.mystic_summit import MysticSummitJoker
from games.balatro.jokers.supernova import SupernovaJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(
    jokers,
    *,
    hands_remaining=3,
    discards_remaining=2,
    money=0,
    deck_size=0,
    high_card_plays=0,
):
    ace = BalatroCard("A", "Spades")
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [ace]
    state.deck = [BalatroCard("2", "Clubs") for _ in range(deck_size)]
    state.owned_deck = [BalatroCard("3", "Hearts") for _ in range(12)]
    state.hands_remaining = hands_remaining
    state.discards_remaining = discards_remaining
    state.money = money
    state.hand_play_counts[PokerHand.HIGH_CARD.value] = high_card_plays
    state.jokers = list(jokers)
    return state, ace


def _project(state, card):
    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [card],
    )
    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    return transition


def test_base_joker_projects_exact_plus_four_mult():
    state, ace = _state([FlatMultJoker()])

    transition = _project(state, ace)

    assert transition.distribution.minimum == 80


def test_abstract_counts_itself_and_every_owned_supported_joker():
    state, ace = _state([AbstractJoker(), FlatMultJoker()])

    transition = _project(state, ace)

    # 16 Chips; base 1 Mult + Abstract +6 + base Joker +4 = 11 Mult.
    assert transition.distribution.minimum == 176


def test_mystic_summit_uses_public_remaining_discards():
    active_state, active_ace = _state(
        [MysticSummitJoker()],
        discards_remaining=0,
    )
    inactive_state, inactive_ace = _state(
        [MysticSummitJoker()],
        discards_remaining=1,
    )

    assert _project(active_state, active_ace).distribution.minimum == 256
    assert _project(inactive_state, inactive_ace).distribution.minimum == 16


def test_acrobat_activates_only_on_final_remaining_hand():
    active_state, active_ace = _state(
        [AcrobatJoker()],
        hands_remaining=1,
    )
    inactive_state, inactive_ace = _state(
        [AcrobatJoker()],
        hands_remaining=2,
    )

    assert _project(active_state, active_ace).distribution.minimum == 48
    assert _project(inactive_state, inactive_ace).distribution.minimum == 16


def test_blue_joker_uses_remaining_draw_deck_not_owned_deck():
    state, ace = _state([BlueJoker()], deck_size=3)

    transition = _project(state, ace)

    # 16 ordinary High Card chips + 2 Chips for each of three remaining cards.
    assert transition.distribution.minimum == 22


def test_bull_adds_two_chips_per_positive_dollar_and_never_penalizes_debt():
    rich_state, rich_ace = _state([BullJoker()], money=12)
    debt_state, debt_ace = _state([BullJoker()], money=-8)

    assert _project(rich_state, rich_ace).distribution.minimum == 40
    assert _project(debt_state, debt_ace).distribution.minimum == 16


def test_supernova_includes_current_hand_in_run_play_count():
    state, ace = _state([SupernovaJoker()], high_card_plays=3)

    transition = _project(state, ace)

    # Fourth High Card this run gives +4 Mult: 16 Chips * (1 + 4) Mult.
    assert transition.distribution.minimum == 80
    assert transition.state_after_scoring.hand_play_counts[PokerHand.HIGH_CARD.value] == 4


def test_independent_joker_xmult_respects_left_to_right_row_order():
    xmult_first, first_ace = _state([CavendishJoker(), FlatMultJoker()])
    additive_first, second_ace = _state([FlatMultJoker(), CavendishJoker()])

    first = _project(xmult_first, first_ace)
    second = _project(additive_first, second_ace)

    # Cavendish first: (base 1 * 3) + 4 = 7 Mult => 112.
    assert first.distribution.minimum == 112
    # Base Joker first: (base 1 + 4) * 3 = 15 Mult => 240.
    assert second.distribution.minimum == 240
