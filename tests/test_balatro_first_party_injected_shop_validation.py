from games.balatro.actions import (
    BUY_CONSUMABLE,
    BUY_JOKER,
    REFRESH_SHOP,
)
from games.balatro.live.external.live_memory_shop_action_injected_validation import (
    _fingerprint,
    _guard_errors,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


def _shop_snapshot(*, sequence=1, money=10, cards=None):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase="SHOP",
        state_complete=True,
        payload={
            "money": money,
            "shop_jokers": {"cards": list(cards or [])},
            "shop_vouchers": {"cards": []},
            "shop_boosters": {"cards": []},
        },
    )


def test_shop_guard_accepts_exact_joker_target():
    snapshot = _shop_snapshot(
        cards=[
            {
                "area_index": 0,
                "label": "Joker",
                "ability_set": "Joker",
                "cost": 2,
            }
        ]
    )

    assert _guard_errors(
        snapshot,
        action_name=BUY_JOKER,
        expected_money=10,
        index=0,
        expected_label="Joker",
        expected_cost=2,
    ) == []


def test_shop_guard_rejects_changed_money_label_and_cost():
    snapshot = _shop_snapshot(
        money=9,
        cards=[
            {
                "area_index": 0,
                "label": "Greedy Joker",
                "ability_set": "Joker",
                "cost": 5,
            }
        ],
    )

    errors = _guard_errors(
        snapshot,
        action_name=BUY_JOKER,
        expected_money=10,
        index=0,
        expected_label="Joker",
        expected_cost=4,
    )

    assert any("expected money" in error for error in errors)
    assert any("expected label" in error for error in errors)
    assert any("expected cost" in error for error in errors)


def test_shop_guard_rejects_joker_as_consumable():
    snapshot = _shop_snapshot(
        cards=[
            {
                "area_index": 0,
                "label": "Joker",
                "ability_set": "Joker",
                "cost": 2,
            }
        ]
    )

    errors = _guard_errors(
        snapshot,
        action_name=BUY_CONSUMABLE,
        expected_money=10,
        index=0,
        expected_label="Joker",
        expected_cost=2,
    )

    assert any("not Tarot/Planet/Spectral" in error for error in errors)


def test_shop_guard_reroll_requires_only_stable_shop_and_money_expectation():
    snapshot = _shop_snapshot(money=10)

    assert _guard_errors(
        snapshot,
        action_name=REFRESH_SHOP,
        expected_money=10,
    ) == []


def test_shop_guard_fingerprint_detects_public_shop_change():
    before = _shop_snapshot(
        sequence=4,
        cards=[
            {
                "area_index": 0,
                "label": "Joker",
                "ability_set": "Joker",
                "cost": 2,
            }
        ],
    )
    after = _shop_snapshot(
        sequence=4,
        cards=[
            {
                "area_index": 0,
                "label": "Greedy Joker",
                "ability_set": "Joker",
                "cost": 5,
            }
        ],
    )

    assert _fingerprint(before) != _fingerprint(after)
