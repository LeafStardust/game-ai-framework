from types import SimpleNamespace

from games.balatro.bonds.mechanical_residue import (
    evaluate_aces_bond,
    evaluate_cash_bond,
    evaluate_clubs_bond,
    evaluate_face_cards_bond,
    evaluate_glass_bond,
    evaluate_hearts_bond,
    evaluate_low_ranks_bond,
    evaluate_lucky_bond,
    evaluate_no_discard_bond,
    evaluate_stone_bond,
)
from games.balatro.mechanics import (
    ACE_CHIPS_MULT,
    ADD_STONE_CARD,
    ALL_CARDS_FACE,
    CASH_CHIPS,
    CASH_MULT,
    DISCARDS_TO_HANDS,
    FACE_CHIPS,
    FACE_MULT,
    GLASS_PAYOFF,
    LOW_RANK_FIBONACCI_MULT,
    LOW_RANK_RETRIGGER,
    LOW_RANK_TWO_SCALING,
    LUCKY_TRIGGER_SCALING,
    NO_DISCARD_SCALING,
    NO_DISCARD_XMULT,
    PROBABILITY_DOUBLING,
    STONE_PAYOFF,
    SUIT_CLUBS_MULT,
    SUIT_HEARTS_MULT,
    SUIT_HEARTS_XMULT,
)


def _component(*mechanics):
    return SimpleNamespace(name="arbitrary-component-name", mechanics=frozenset(mechanics))


def _card(rank="7", suit="Hearts", enhancement=""):
    return SimpleNamespace(rank=rank, suit=suit, enhancement=enhancement, seal="")


def _state(*, jokers=(), deck=(), **extra):
    data = dict(jokers=list(jokers), owned_deck=list(deck), money=0, glass_cards_destroyed=0)
    data.update(extra)
    return SimpleNamespace(**data)


def test_residual_rank_and_no_discard_axes_ignore_display_names():
    aces = evaluate_aces_bond(_state(
        jokers=(_component(ACE_CHIPS_MULT), _component(LOW_RANK_FIBONACCI_MULT)),
        deck=tuple(_card(rank="A") for _ in range(12)),
    ))
    no_discard = evaluate_no_discard_bond(_state(jokers=(
        _component(NO_DISCARD_SCALING),
        _component(DISCARDS_TO_HANDS),
        _component(NO_DISCARD_XMULT),
    )))
    assert aces.contribution == 16.0
    assert no_discard.contribution == 16.0


def test_residual_cash_lucky_glass_and_stone_axes_ignore_display_names():
    cash = evaluate_cash_bond(_state(jokers=(_component(CASH_CHIPS), _component(CASH_MULT)), money=150))
    lucky = evaluate_lucky_bond(_state(
        jokers=(_component(LUCKY_TRIGGER_SCALING), _component(PROBABILITY_DOUBLING)),
        deck=tuple(_card(enhancement="Lucky") for _ in range(10)),
    ))
    glass = evaluate_glass_bond(_state(
        jokers=(_component(GLASS_PAYOFF),),
        deck=tuple(_card(enhancement="Glass") for _ in range(10)),
        glass_cards_destroyed=10,
    ))
    stone = evaluate_stone_bond(_state(
        jokers=(_component(STONE_PAYOFF), _component(ADD_STONE_CARD)),
        deck=tuple(_card(enhancement="Stone") for _ in range(10)),
    ))
    assert cash.contribution == 17.0
    assert lucky.contribution == 17.0
    assert glass.contribution == 19.0
    assert stone.contribution == 20.0


def test_residual_face_suit_and_low_rank_axes_ignore_display_names():
    face = evaluate_face_cards_bond(_state(
        jokers=(_component(ALL_CARDS_FACE), _component(FACE_CHIPS), _component(FACE_MULT)),
        deck=tuple(_card(rank="K") for _ in range(26)),
    ))
    hearts = evaluate_hearts_bond(_state(
        jokers=(_component(SUIT_HEARTS_XMULT), _component(SUIT_HEARTS_MULT)),
        deck=tuple(_card(suit="Hearts") for _ in range(32)),
    ))
    clubs = evaluate_clubs_bond(_state(
        jokers=(_component(SUIT_CLUBS_MULT), _component(SUIT_CLUBS_MULT)),
        deck=tuple(_card(suit="Clubs") for _ in range(32)),
    ))
    low = evaluate_low_ranks_bond(_state(
        jokers=(
            _component(LOW_RANK_RETRIGGER),
            _component(LOW_RANK_TWO_SCALING),
            _component(LOW_RANK_FIBONACCI_MULT),
        ),
        deck=tuple(_card(rank="2") for _ in range(30)),
    ))
    assert face.contribution == 21.0
    assert hearts.contribution == 20.0
    assert clubs.contribution == 19.0
    assert low.contribution == 22.0
