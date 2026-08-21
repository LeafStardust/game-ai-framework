from types import SimpleNamespace

from games.balatro.bonds import BondRank, BurntBondContext, evaluate_burnt_bond


def _joker(name: str):
    return SimpleNamespace(name=name)


def _voucher(name: str):
    return SimpleNamespace(name=name)


def _card(*, seal=""):
    return SimpleNamespace(seal=seal)


def _state(*, jokers=(), vouchers=(), deck=(), hand_levels=None):
    return SimpleNamespace(
        jokers=list(jokers),
        vouchers=list(vouchers),
        owned_deck=list(deck),
        deck=list(deck),
        hand_levels=dict(hand_levels or {}),
    )


def test_burnt_is_the_only_unlock_requirement():
    locked = evaluate_burnt_bond(
        _state(
            vouchers=(_voucher("Telescope"),),
            deck=(_card(seal="Blue"),) * 4,
            hand_levels={"HIGH_CARD": 12},
        )
    )
    assert locked.unlocked is False
    assert locked.rank == BondRank.LOCKED
    assert locked.contribution == 0.0

    unlocked = evaluate_burnt_bond(_state(jokers=(_joker("Burnt Joker"),)))
    assert unlocked.unlocked is True
    assert unlocked.rank == BondRank.R1
    assert unlocked.contribution == 8.0


def test_telescope_is_one_alternative_path_to_r2_not_a_gate():
    result = evaluate_burnt_bond(
        _state(
            jokers=(_joker("Burnt Joker"),),
            vouchers=(_voucher("Telescope"),),
        )
    )
    assert result.rank == BondRank.R2
    assert result.contribution == 12.0


def test_strong_blue_seal_infrastructure_reaches_r2_without_telescope():
    result = evaluate_burnt_bond(
        _state(
            jokers=(_joker("Burnt Joker"),),
            deck=tuple(_card(seal="Blue") for _ in range(3)),
        )
    )
    assert result.rank == BondRank.R2
    assert result.contribution == 13.0


def test_blueprint_reaches_r2_without_telescope_or_blue_seals():
    result = evaluate_burnt_bond(
        _state(jokers=(_joker("Burnt Joker"), _joker("Blueprint")))
    )
    assert result.rank == BondRank.R2
    assert result.contribution == 13.0


def test_alternative_sources_add_into_one_pool_for_higher_ranks():
    result = evaluate_burnt_bond(
        _state(
            jokers=(
                _joker("Burnt Joker"),
                _joker("Blueprint"),
                _joker("Brainstorm"),
            ),
            vouchers=(_voucher("Telescope"),),
            deck=tuple(_card(seal="Blue") for _ in range(3)),
            hand_levels={"PAIR": 8},
        ),
        context=BurntBondContext(target_hand="PAIR"),
    )
    assert result.rank == BondRank.R5
    assert result.contribution == 32.0
    assert result.target == "PAIR"


def test_target_defaults_to_high_card_until_composer_supplies_hand_bond():
    result = evaluate_burnt_bond(
        _state(
            jokers=(_joker("Burnt Joker"),),
            hand_levels={"HIGH_CARD": 7, "PAIR": 12},
        )
    )
    assert result.target == "HIGH_CARD"
    assert result.contribution == 13.0


def test_composer_selected_target_uses_that_hands_permanent_investment():
    result = evaluate_burnt_bond(
        _state(
            jokers=(_joker("Burnt Joker"),),
            hand_levels={"HIGH_CARD": 1, "PAIR": 8},
        ),
        context=BurntBondContext(target_hand="PAIR"),
    )
    assert result.target == "PAIR"
    assert result.contribution == 13.0
    assert result.rank == BondRank.R2


def test_extra_discard_capacity_is_capped_support_not_a_defining_engine():
    result = evaluate_burnt_bond(
        _state(jokers=(_joker("Burnt Joker"),)),
        context=BurntBondContext(discards_per_round=20),
    )
    assert result.contribution == 11.0
    assert result.rank == BondRank.R1
