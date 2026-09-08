from types import SimpleNamespace

from games.balatro.shop_semantic_quiet_policy import shop_semantic_signature


def _snapshot(*, ui_x: int, money: int = 22, offer_label: str = "Supernova"):
    return SimpleNamespace(
        phase="SHOP",
        state_complete=True,
        payload={
            "money": money,
            "shop_jokers": {
                "cards": [
                    {
                        "live_id": 101,
                        "label": offer_label,
                        "center": "j_supernova",
                        "ui": {"x": ui_x, "y": 20},
                    }
                ],
                "count": 1,
                "limit": 2,
            },
            "jokers": {
                "cards": [
                    {
                        "live_id": 1,
                        "label": "Abstract Joker",
                        "center": "j_abstract",
                        "ui": {"x": ui_x + 5, "y": 30},
                    }
                ],
                "count": 1,
                "limit": 5,
            },
        },
    )


def test_shop_semantic_signature_ignores_ui_animation_churn():
    before = _snapshot(ui_x=10)
    animated = _snapshot(ui_x=47)

    assert shop_semantic_signature(before) == shop_semantic_signature(animated)


def test_shop_semantic_signature_detects_real_shop_change():
    baseline = _snapshot(ui_x=10)
    money_changed = _snapshot(ui_x=47, money=18)
    offer_changed = _snapshot(ui_x=47, offer_label="Misprint")

    assert shop_semantic_signature(baseline) != shop_semantic_signature(money_changed)
    assert shop_semantic_signature(baseline) != shop_semantic_signature(offer_changed)
