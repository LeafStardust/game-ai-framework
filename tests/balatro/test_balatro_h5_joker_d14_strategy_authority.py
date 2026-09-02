from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from games.balatro.shop_utility_scale import ShopUtilityScale


def _scale() -> ShopUtilityScale:
    scale = ShopUtilityScale(SimpleNamespace())
    scale._money_transaction_cost = lambda *args, **kwargs: SimpleNamespace(total=0.0)
    return scale


def _executable(*, build_gain: float = 2.5):
    selected = SimpleNamespace(
        build_gain=build_gain,
        replace_index=0,
        economics=SimpleNamespace(net_spend=0, edition_delta=0.0),
    )
    return SimpleNamespace(
        source="JOKER_REPLACE_SELL",
        candidate=SimpleNamespace(discovered=True),
        decision=SimpleNamespace(selected=selected),
    )


def _state(**extra):
    values = {
        "jokers": (SimpleNamespace(),),
        "joker_slots": 5,
    }
    values.update(extra)
    return SimpleNamespace(**values)


def test_h5_d14_joker_gain_ignores_legacy_strategy_metadata():
    scale = _scale()
    executable = _executable(build_gain=2.5)
    clean = _state()
    legacy = _state(
        strategy_plan=SimpleNamespace(
            strategy_id="legacy_strategy",
            pinned_strategy_id="legacy_strategy",
            missing_features=("rank:K",),
            bond_goals=(SimpleNamespace(bond_id="kings"),),
        ),
        strategy_candidates=(
            SimpleNamespace(
                strategy_id="legacy_strategy",
                pinned=True,
                commitment=3,
                confidence=1.0,
                strength=1.0,
                prescriptions=("seek_feature:rank:K", "seek_bond:kings:R3"),
            ),
        ),
    )

    clean_utility = scale.joker_gain(clean, executable)
    legacy_utility = scale.joker_gain(legacy, executable)

    assert clean_utility.gain == pytest.approx(2.5)
    assert legacy_utility.gain == pytest.approx(clean_utility.gain)
    assert "D2 build gain=2.500" in legacy_utility.notes
    assert all("strategy goal bonus" not in note for note in legacy_utility.notes)


def test_h5_production_package_does_not_install_pinned_shop_goal_wrapper():
    package_source = (
        Path(__file__).resolve().parents[2] / "games" / "balatro" / "__init__.py"
    ).read_text(encoding="utf-8")

    assert "pinned_strategy_shop_goal_policy" not in package_source
    assert "install_pinned_strategy_shop_goal_policy" not in package_source
