from games.balatro.bonds.diagnostics import bond_strategy_diagnostics
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.burnt_joker import BurntJoker
from games.balatro.jokers.erosion import ErosionJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.state import BalatroState


def _state(*jokers):
    state = BalatroState()
    state.jokers = list(jokers)
    state.owned_deck = list(state.deck)
    return state


def _candidate(payload, strategy_id):
    return next(
        candidate
        for candidate in payload["strategy_candidates"]
        if candidate["strategy_id"] == strategy_id
    )


def test_burnt_diagnostics_expose_forming_plan_and_missing_goals():
    payload = bond_strategy_diagnostics(_state(BurntJoker()))

    candidate = _candidate(payload, "burnt_target_level")
    plan = payload["strategy_plan"]

    assert candidate["commitment"] == "FORMING"
    assert plan is not None
    assert plan["strategy_id"] == "burnt_target_level"
    assert plan["commitment"] == "FORMING"
    assert "BURNT_JOKER" in plan["present_components"]
    assert plan["missing_components"]
    assert any(
        prescription.startswith("seek_")
        for prescription in plan["prescriptions"]
    )


def test_deck_thinning_diagnostics_expose_forming_construction_plan():
    payload = bond_strategy_diagnostics(_state(ErosionJoker()))

    candidate = _candidate(payload, "semantic:deck_thinning")
    plan = payload["strategy_plan"]

    assert candidate["commitment"] == "FORMING"
    assert plan is not None
    assert plan["strategy_id"] == "semantic:deck_thinning"
    assert plan["commitment"] == "FORMING"
    assert any(goal["bond_id"] == "deck_thinning" for goal in plan["bond_goals"])
    assert any(
        prescription.startswith("seek_bond:deck_thinning:")
        for prescription in plan["prescriptions"]
    )


def test_held_card_diagnostics_expose_pinned_strategy_and_preservation_plan():
    payload = bond_strategy_diagnostics(_state(BaronJoker(), MimeJoker()))

    candidate = _candidate(payload, "baron_mime_steel")
    plan = payload["strategy_plan"]

    assert candidate["commitment"] in {"PINNED", "ESTABLISHED", "DOMINANT"}
    assert payload["pinned_strategy"] == "baron_mime_steel"
    assert plan is not None
    assert plan["strategy_id"] == "baron_mime_steel"
    assert plan["commitment"] in {"PINNED", "ESTABLISHED", "DOMINANT"}
    assert "BARON" in plan["present_components"]
    assert "MIME" in plan["present_components"]
    assert "preserve_held_kings_and_steel" in plan["prescriptions"]
