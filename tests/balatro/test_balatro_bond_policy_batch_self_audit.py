from dataclasses import dataclass
from types import SimpleNamespace

import games.balatro.bond_pivot_authority as pivot
import games.balatro.bond_prescription_policy as prescription
from games.balatro.bonds.motifs import MotifState
from games.balatro.joker_policy import BUY, HOLD, REPLACE
from games.balatro.live.strategy_health import StrategyHealthMode


@dataclass(frozen=True)
class Option:
    eligible: bool = True
    total_advantage: float = 2.0
    replace_index: int | None = 0


@dataclass(frozen=True)
class Decision:
    action: str
    selected: object | None = None
    options: tuple = ()
    rationale: tuple[str, ...] = ()


def _no_eval(*args, **kwargs):
    raise AssertionError("composition evaluation should have been bypassed")


def _health(mode=StrategyHealthMode.SURVIVE):
    return SimpleNamespace(mode=mode)


def test_pivot_missing_slot_telemetry_cannot_invent_replacement(monkeypatch):
    monkeypatch.setattr(pivot, "last_strategy_health", lambda state: _health())
    monkeypatch.setattr(pivot, "evaluate_bond_composition", _no_eval)
    decision = Decision(HOLD, options=(Option(),))
    state = SimpleNamespace(jokers=("A",))
    assert pivot._canonical_pivot_decision(state, "B", decision) is decision


def test_pivot_zero_slots_cannot_invent_replacement(monkeypatch):
    monkeypatch.setattr(pivot, "last_strategy_health", lambda state: _health())
    monkeypatch.setattr(pivot, "evaluate_bond_composition", _no_eval)
    decision = Decision(HOLD, options=(Option(),))
    state = SimpleNamespace(jokers=("A",), joker_slots=0)
    assert pivot._canonical_pivot_decision(state, "B", decision) is decision


def test_pivot_malformed_slots_cannot_invent_replacement(monkeypatch):
    monkeypatch.setattr(pivot, "last_strategy_health", lambda state: _health())
    monkeypatch.setattr(pivot, "evaluate_bond_composition", _no_eval)
    decision = Decision(HOLD, options=(Option(),))
    state = SimpleNamespace(jokers=("A",), joker_slots="unknown")
    assert pivot._canonical_pivot_decision(state, "B", decision) is decision


def test_pivot_free_slot_defers_to_child_add_authority(monkeypatch):
    monkeypatch.setattr(pivot, "last_strategy_health", lambda state: _health())
    monkeypatch.setattr(pivot, "evaluate_bond_composition", _no_eval)
    decision = Decision(HOLD, options=(Option(),))
    state = SimpleNamespace(jokers=("A",), joker_slots=2)
    assert pivot._canonical_pivot_decision(state, "B", decision) is decision


def test_pivot_nonreplacement_action_is_not_rewritten(monkeypatch):
    monkeypatch.setattr(pivot, "last_strategy_health", lambda state: _health())
    monkeypatch.setattr(pivot, "evaluate_bond_composition", _no_eval)
    decision = Decision(BUY, options=(Option(),))
    state = SimpleNamespace(jokers=("A",), joker_slots=1)
    assert pivot._canonical_pivot_decision(state, "B", decision) is decision


def test_pivot_unknown_health_mode_defers_without_evaluation(monkeypatch):
    monkeypatch.setattr(pivot, "last_strategy_health", lambda state: SimpleNamespace(mode="NEW_MODE"))
    monkeypatch.setattr(pivot, "evaluate_bond_composition", _no_eval)
    decision = Decision(HOLD, options=(Option(),))
    state = SimpleNamespace(jokers=("A",), joker_slots=1)
    assert pivot._canonical_pivot_decision(state, "B", decision) is decision


def _motifs(monkeypatch, *ids):
    monkeypatch.setattr(prescription, "_active_motif_ids", lambda state: frozenset(ids))


def _card(rank="", enhancement="", seal=""):
    return SimpleNamespace(rank=rank, enhancement=enhancement, seal=seal)


def test_prescription_accepts_compact_dejavu_label(monkeypatch):
    _motifs(monkeypatch, "baron_mime_steel")
    bonus, _ = prescription.prescription_bonus(object(), kind="SPECTRAL", label="DejaVu")
    assert bonus == 1.10


def test_prescription_accepts_case_and_separator_chariot_label(monkeypatch):
    _motifs(monkeypatch, "baron_mime_steel")
    bonus, _ = prescription.prescription_bonus(object(), kind="TAROT", label="THE_CHARIOT")
    assert bonus == 1.25


def test_prescription_accepts_steel_card_enhancement_telemetry(monkeypatch):
    _motifs(monkeypatch, "baron_mime_steel")
    bonus, _ = prescription.prescription_bonus(
        object(), kind="PLAYING_CARD", label="x", playing_card=_card(enhancement="Steel Card")
    )
    assert bonus == 0.90


def test_prescription_accepts_red_seal_telemetry(monkeypatch):
    _motifs(monkeypatch, "baron_mime_steel")
    bonus, _ = prescription.prescription_bonus(
        object(), kind="PLAYING_CARD", label="x", playing_card=_card(seal="Red Seal")
    )
    assert bonus == 0.70


def test_prescription_accepts_blue_seal_telemetry(monkeypatch):
    _motifs(monkeypatch, "burnt_target_level")
    monkeypatch.setattr(prescription, "_burnt_target_hand", lambda state: "PAIR")
    bonus, _ = prescription.prescription_bonus(
        object(), kind="PLAYING_CARD", label="x", playing_card=_card(seal="Blue Seal")
    )
    assert bonus == 0.65


def test_burnt_planet_name_and_target_format_are_canonicalized(monkeypatch):
    _motifs(monkeypatch, "burnt_target_level")
    monkeypatch.setattr(prescription, "_burnt_target_hand", lambda state: prescription._hand_type("five of a kind"))
    bonus, _ = prescription.prescription_bonus(object(), kind="PLANET", label="planet_x")
    assert bonus == 1.50


def test_burnt_target_helper_canonicalizes_hyphenated_hand(monkeypatch):
    composition = SimpleNamespace(motifs=())
    developments = (SimpleNamespace(bond_id="burnt", target="three-of-a-kind"),)
    monkeypatch.setattr(prescription, "evaluate_bond_composition", lambda state: (developments, composition))
    assert prescription._burnt_target_hand(object()) == "THREE_OF_A_KIND"


def test_rank_ten_alias_is_canonical_for_policy_cards():
    assert prescription._rank(_card(rank="TEN")) == "10"


def test_potential_motif_still_does_not_receive_prescription(monkeypatch):
    composition = SimpleNamespace(
        motifs=(SimpleNamespace(motif_id="baron_mime_steel", state=MotifState.POTENTIAL),)
    )
    monkeypatch.setattr(prescription, "evaluate_bond_composition", lambda state: ((), composition))
    bonus, notes = prescription.prescription_bonus(object(), kind="TAROT", label="The Chariot")
    assert bonus == 0.0
    assert notes == ()
