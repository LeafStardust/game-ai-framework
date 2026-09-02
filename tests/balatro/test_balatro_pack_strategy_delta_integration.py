from types import SimpleNamespace

import inspect

import pytest

import games.balatro.strategy_plan_pack_policy as pack_strategy
from games.balatro.state import BalatroState


def _action(kind: str, label: str, data=None):
    return SimpleNamespace(
        target=SimpleNamespace(
            kind=kind,
            label=label,
            data=dict(data or {}),
        )
    )


def test_playing_card_pack_projection_adds_persistent_card_without_mutating_current_state():
    state = BalatroState()
    state.owned_deck = []
    action = _action(
        "PLAYING_CARD",
        "Steel King of Hearts",
        {
            "value": {"rank": "King", "suit": "Hearts"},
            "enhancement": "m_steel",
            "seal": "red_seal",
        },
    )

    projected = pack_strategy._project_pack_choice(state, action)

    assert projected is not state
    assert state.owned_deck == []
    assert len(projected.owned_deck) == 1
    card = projected.owned_deck[0]
    assert card.rank == "King"
    assert card.suit == "Hearts"
    assert card.enhancement == "Steel"
    assert card.seal == "Red"


def test_planet_pack_projection_increments_public_hand_level_without_mutating_current_state():
    state = BalatroState()
    state.hand_levels["FLUSH"] = 3
    action = _action("PLANET", "Jupiter")

    projected = pack_strategy._project_pack_choice(state, action)

    assert projected is not state
    assert state.hand_levels["FLUSH"] == 3
    assert projected.hand_levels["FLUSH"] == 4


def test_pack_strategy_adjustment_uses_canonical_strategy_delta(monkeypatch):
    state = BalatroState()
    action = _action("PLANET", "Jupiter")
    observed = {}

    def fake_delta(current, projected):
        observed["current"] = current
        observed["projected"] = projected
        return SimpleNamespace(value=8.0, raw_delta=9.5, transition_cost=1.5)

    monkeypatch.setattr(pack_strategy, "strategy_delta_from_states", fake_delta)

    adjustment, notes = pack_strategy._strategy_adjustment(state, action)

    assert observed["current"] is state
    assert observed["projected"] is not state
    assert adjustment == pytest.approx(0.8)
    assert any("canonical StrategyDelta=+8.000" in note for note in notes)
    assert any("pack strategy weight=0.100" in note for note in notes)


def test_unprojected_pack_kinds_receive_no_strategy_adjustment():
    state = BalatroState()
    action = _action("TAROT", "The Hermit")

    adjustment, notes = pack_strategy._strategy_adjustment(state, action)

    assert adjustment == 0.0
    assert notes == ()


def test_pack_production_scorer_no_longer_uses_legacy_plan_or_composition_authority():
    source_names = set(pack_strategy.__dict__)
    assert "evaluate_bond_composition" not in source_names
    assert "StrategyCommitment" not in source_names
    assert "StrategyPlan" not in source_names

    installer_source = inspect.getsource(pack_strategy.install_strategy_plan_pack_policy)
    assert "_goal_ids(" not in installer_source
    assert "_playing_card_matches(" not in installer_source
    assert "strategy_delta" in installer_source or "_strategy_adjustment" in installer_source


def test_legacy_pack_helpers_are_inert_compatibility_only():
    assert pack_strategy._goal_ids(None) == ()
    assert pack_strategy._playing_card_matches("kings", {"rank": "King", "suit": "Hearts"})
