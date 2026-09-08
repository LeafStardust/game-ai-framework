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


def test_mime_never_contributes_direct_held_cards_quota():
    alone = evaluate_held_cards_bond(_state(jokers=(_joker("Mime"),)))
    assert alone.rank == BondRank.R0
    assert alone.contribution == 0.0

    with_baron = evaluate_held_cards_bond(
        _state(jokers=(_joker("Baron"), _joker("Mime")))
    )
    assert with_baron.contribution == 6.0
    assert with_baron.rank == BondRank.R1

    with_steel = evaluate_held_cards_bond(
        _state(
            jokers=(_joker("Mime"),),
            deck=tuple(_card(enhancement="Steel") for _ in range(4)),
        )
    )
    assert with_steel.contribution == 5.0
    assert with_steel.rank == BondRank.R1


def test_gold_cards_and_blue_seals_do_not_add_held_cards_quota():
    result = evaluate_held_cards_bond(
        _state(
            deck=(
                *tuple(_card(enhancement="Gold") for _ in range(8)),
                *tuple(_card(seal="Blue") for _ in range(8)),
            )
        )
    )
    assert result.contribution == 0.0
    assert result.rank == BondRank.R0


def test_alternative_direct_held_sources_share_one_pool():
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
            ),
            hand_size=10,
        )
    )
    # 4 Shoot + 2 Fist + 3 Steel + 2 hand size = 11. Mime belongs only to
    # Held Retrigger and contributes no Held Cards quota.
    assert result.contribution == 11.0
    assert result.rank == BondRank.R2


def test_hand_size_support_is_capped():
    result = evaluate_held_cards_bond(_state(hand_size=30))
    assert result.contribution == 3.0
    assert result.rank == BondRank.R0
