from types import SimpleNamespace

from games.balatro.bonds.catalogue_batch_four import evaluate_planet_bond, evaluate_tarot_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name):
    return SimpleNamespace(name=name)


def _voucher(name):
    return SimpleNamespace(name=name)


def _state(*, jokers=(), vouchers=(), hand=(), deck=()):
    return SimpleNamespace(
        jokers=list(jokers),
        vouchers=list(vouchers),
        consumables=[],
        consumable_cards=[],
        hand=list(hand),
        current_hand=list(hand),
        cards_in_hand=list(hand),
        owned_deck=list(deck),
        deck=list(deck),
    )


def test_eight_ball_is_registered_as_minor_tarot_engine_support():
    dev = evaluate_tarot_bond(_state(jokers=(_joker("8 Ball"),)))
    assert dev.contribution == 2.0


def test_tarot_merchant_voucher_is_live_tarot_infrastructure():
    state = _state(vouchers=(_voucher("Tarot Merchant"),))
    dev = evaluate_tarot_bond(state)
    assert dev.rank.value >= 1
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.ACTIVE


def test_telescope_is_live_planet_infrastructure():
    state = _state(vouchers=(_voucher("Telescope"),))
    dev = evaluate_planet_bond(state)
    assert dev.rank.value >= 1
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.ACTIVE


def test_planet_merchant_voucher_is_live_planet_infrastructure():
    state = _state(vouchers=(_voucher("Planet Merchant"),))
    dev = evaluate_planet_bond(state)
    assert dev.rank.value >= 1
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.ACTIVE
