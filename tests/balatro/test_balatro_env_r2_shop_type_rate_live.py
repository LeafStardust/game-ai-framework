import pytest

from games.balatro.env.voucher_capabilities import shop_generation_vouchers_are_exact
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator


def _translate(payload):
    return DefaultBalatroStateTranslator().translate(
        LiveBalatroSnapshot(
            sequence=1,
            phase="SHOP",
            state_complete=True,
            payload=payload,
        )
    )


@pytest.mark.parametrize(
    ("payload", "tarot", "planet"),
    [
        ({}, 4.0, 4.0),
        ({"tarot_rate": 9.6}, 9.6, 4.0),
        ({"planet_rate": 9.6}, 4.0, 9.6),
        ({"tarot_rate": 32, "planet_rate": 32.0}, 32.0, 32.0),
    ],
)
def test_env_r2_live_translator_preserves_exact_shop_type_rates(payload, tarot, planet):
    state = _translate(payload)

    assert state.tarot_rate == tarot
    assert state.planet_rate == planet


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tarot_rate", True),
        ("tarot_rate", "9.6"),
        ("tarot_rate", -1),
        ("planet_rate", False),
        ("planet_rate", "32"),
        ("planet_rate", -0.5),
    ],
)
def test_env_r2_live_translator_malformed_shop_type_rate_falls_back_to_base(field, value):
    state = _translate({field: value})

    assert state.tarot_rate == 4.0
    assert state.planet_rate == 4.0


def test_env_r2_observed_merchant_ownership_with_missing_rate_fails_closed():
    state = _translate(
        {
            "vouchers_observed": True,
            "vouchers": ["v_tarot_merchant"],
        }
    )

    assert state.tarot_rate == 4.0
    assert not shop_generation_vouchers_are_exact(state)


def test_env_r2_live_rate_does_not_infer_unobserved_voucher_ownership():
    state = _translate({"tarot_rate": 9.6, "planet_rate": 32.0})

    assert state.vouchers_observed is False
    assert state.vouchers == []
    assert not shop_generation_vouchers_are_exact(state)
