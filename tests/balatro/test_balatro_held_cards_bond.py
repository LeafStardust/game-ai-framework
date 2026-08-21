from types import SimpleNamespace

from games.balatro.bonds import BondRank, evaluate_held_cards_bond


def _joker(name: str):
    return SimpleNamespace(name=name)


def _card(*, enhancement="", seal=""):
    return SimpleNamespace(enhancement=enhancement, seal=seal)


def _state(*, jokers=(), deck=(), hand_size=8):
    return SimpleNamespace(
        jokers=list(jokers),
        owned_deck=list(deck),
        deck=list(deck),
        hand_size=hand_size,
    )


def test_held_cards_has_no_hard_unlock_and_can_remain_r0():
    result = evaluate_held_cards_bond(_state())
    assert result.unlocked is True
    assert result.rank == BondRank.R0
    assert result.contribution == 0.0


def test_baron_alone_establishes_r1_but_not_r2():
    result = evaluate_held_cards_bond(_state(jokers=(_joker("Baron"),)))
    assert result.rank == BondRank.R1
    assert result.contribution == 6.0


def test_shoot_the_moon_is_an_independent_r1_path():
    result = evaluate_held_cards_bond(
        _state(jokers=(_joker("Shoot the Moon"),))
    )
    assert result.rank == BondRank.R1
    assert result.contribution == 4.0


def test_steel_density_can_establish_held_cards_without_a_held_joker():
    result = evaluate_held_cards_bond(
        _state(deck=tuple(_card(enhancement="Steel") for _ in range(4)))
    )
    assert result.rank == BondRank.R1
    assert result.contribution == 5.0


def test_mime_is_a_bridge_not_enough_to_establish_held_cards_by_itself():
    result = evaluate_held_cards_bond(_state(jokers=(_joker("Mime"),)))
    assert result.rank == BondRank.R0
    assert result.contribution == 2.0


def test_baron_plus_mime_crosses_r2_without_steel():
    result = evaluate_held_cards_bond(
        _state(jokers=(_joker("Baron"), _joker("Mime")))
    )
    assert result.rank == BondRank.R2
    assert result.contribution == 8.0


def test_alternative_held_sources_share_one_pool():
    result = evaluate_held_cards_bond(
        _state(
            jokers=(
                _joker("Shoot the Moon"),
                _joker("Raised Fist"),
                _joker("Mime"),
            ),
            deck=(
                _card(enhancement="Steel"),
                _card(enhancement="Steel"),
                _card(enhancement="Gold"),
                _card(enhancement="Gold"),
                _card(enhancement="Gold"),
                _card(seal="Blue"),
                _card(seal="Blue"),
                _card(seal="Blue"),
            ),
            hand_size=10,
        )
    )
    # 4 Shoot + 2 Fist + 2 Mime + 3 Steel + 1.5 Gold + 1.5 Blue + 2 hand size = 16
    assert result.contribution == 16.0
    assert result.rank == BondRank.R3


def test_hand_size_support_is_capped():
    result = evaluate_held_cards_bond(_state(hand_size=30))
    assert result.contribution == 3.0
    assert result.rank == BondRank.R0
