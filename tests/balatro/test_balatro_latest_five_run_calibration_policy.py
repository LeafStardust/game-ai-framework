from types import SimpleNamespace

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.latest_five_run_calibration_policy import (
    _banner_pack_replacement_is_speculative,
    _enforce_latest_pack_calibration,
    hieroglyph_blocked,
    sock_scary_face_synergy,
    stencil_would_be_dead,
)
from games.balatro.pack_policy import PackActionScore


def _joker(name, *, edition=""):
    return SimpleNamespace(name=name, label=name, edition=edition)


def _state(*jokers, ante=3, slots=5):
    return SimpleNamespace(
        jokers=list(jokers),
        joker_slots=slots,
        ante=ante,
        deck_name="RED",
        stake_name="WHITE",
    )


def _choice(label, *, edition=""):
    target = SimpleNamespace(label=label, data={"edition": edition})
    return PackActionScore(
        BalatroAction(SELECT_PACK_CARD, target=target),
        -1.0,
        ("baseline",),
    )


def test_scary_face_is_immediate_retrigger_support_when_sock_is_owned():
    state = _state(_joker("Sock and Buskin"))

    assert sock_scary_face_synergy(state, "Scary Face") is True
    assert sock_scary_face_synergy(state, "Smiley Face") is True
    assert sock_scary_face_synergy(state, "Faceless Joker") is False

    ranked = _enforce_latest_pack_calibration(
        state,
        [
            PackActionScore(BalatroAction(SKIP_BOOSTER), 0.35, ("skip",)),
            _choice("Scary Face"),
        ],
    )
    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].action.target.label == "Scary Face"
    assert ranked[0].total > 0.35


def test_ordinary_stencil_is_dead_when_only_x1_would_remain():
    full = _state(
        _joker("Jolly Joker"),
        _joker("Sly Joker"),
        _joker("Supernova"),
        _joker("Spare Trousers"),
        _joker("Golden Joker"),
    )
    four_of_five = _state(
        _joker("Jolly Joker"),
        _joker("Sly Joker"),
        _joker("Supernova"),
        _joker("Spare Trousers"),
    )

    assert stencil_would_be_dead(full, _joker("Joker Stencil")) is True
    assert stencil_would_be_dead(four_of_five, _joker("Joker Stencil")) is True
    assert stencil_would_be_dead(full, _joker("Joker Stencil", edition="NEGATIVE")) is False


def test_dead_stencil_pack_choice_loses_to_skip():
    state = _state(
        _joker("Jolly Joker"),
        _joker("Sly Joker"),
        _joker("Supernova"),
        _joker("Spare Trousers"),
        _joker("Golden Joker"),
    )
    ranked = _enforce_latest_pack_calibration(
        state,
        [
            PackActionScore(BalatroAction(SKIP_BOOSTER), 0.35, ("skip",)),
            _choice("Joker Stencil"),
        ],
    )

    assert ranked[0].action.name == SKIP_BOOSTER


def test_full_roster_banner_replacement_requires_real_no_discard_support():
    ordinary = _state(
        _joker("Swashbuckler"),
        _joker("Crafty Joker"),
        _joker("Sly Joker"),
        _joker("Droll Joker"),
        _joker("Golden Joker"),
        ante=5,
    )
    no_discard = _state(
        _joker("Swashbuckler"),
        _joker("Crafty Joker"),
        _joker("Sly Joker"),
        _joker("Droll Joker"),
        _joker("Ramen"),
        ante=5,
    )

    assert _banner_pack_replacement_is_speculative(ordinary, _choice("Banner")) is True
    assert _banner_pack_replacement_is_speculative(no_discard, _choice("Banner")) is False


def test_red_white_hieroglyph_is_blocked_from_formation_onward():
    voucher = SimpleNamespace(label="Hieroglyph")

    assert hieroglyph_blocked(_state(ante=2), voucher) is False
    assert hieroglyph_blocked(_state(ante=3), voucher) is True
    assert hieroglyph_blocked(_state(ante=7), voucher) is True
