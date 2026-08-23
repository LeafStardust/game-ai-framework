from __future__ import annotations

from types import SimpleNamespace

import pytest

import games.balatro.pinned_strategy_execution_policy as pack_execution
from games.balatro.bonds.strategy_semantics import StrategyCandidate, StrategyCommitment
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def _candidate(*, bonds, strategy_id="engine", prescriptions=()):
    return StrategyCandidate(
        strategy_id=strategy_id,
        bond_ids=tuple(bonds),
        sources=("source",),
        roles=(),
        links=(),
        motif_ids=(),
        commitment=StrategyCommitment.PINNED,
        confidence=0.8,
        strength=10.0,
        prescriptions=tuple(prescriptions),
    )


def _card(*, rank="2", enhancement=None, seal=None):
    return SimpleNamespace(rank=rank, enhancement=enhancement, seal=seal)


def test_pinned_held_king_engine_values_king_remaining_in_hand():
    candidate = _candidate(bonds=("held_cards", "held_retrigger", "kings"))
    value, notes = StrategyAwareLiveHandActionPolicy._pinned_held_card_value(
        candidate,
        _card(rank="K"),
    )
    assert value > 0.0
    assert any("held K" in note for note in notes)


def test_pinned_held_steel_engine_values_steel_remaining_in_hand():
    candidate = _candidate(bonds=("held_cards", "held_retrigger", "steel"))
    plain, _ = StrategyAwareLiveHandActionPolicy._pinned_held_card_value(
        candidate,
        _card(rank="7", enhancement="Steel"),
    )
    red, notes = StrategyAwareLiveHandActionPolicy._pinned_held_card_value(
        candidate,
        _card(rank="7", enhancement="Steel", seal="Red"),
    )
    assert plain > 0.0
    assert red > plain
    assert any("Red Seal" in note for note in notes)


def test_non_held_strategy_does_not_protect_rank_merely_because_rank_bond_exists():
    candidate = _candidate(bonds=("kings", "face_cards"))
    value, notes = StrategyAwareLiveHandActionPolicy._pinned_held_card_value(
        candidate,
        _card(rank="K"),
    )
    assert value == pytest.approx(0.0)
    assert notes == ()


def test_standard_pack_king_matches_generic_held_king_goal(monkeypatch):
    candidate = _candidate(
        bonds=("held_cards", "kings"),
        prescriptions=("seek_feature:held:rank:K",),
    )
    monkeypatch.setattr(pack_execution, "_pinned_candidate", lambda state: candidate)
    action = SimpleNamespace(
        target=SimpleNamespace(
            kind="PLAYING_CARD",
            data={"value": {"rank": "King", "suit": "Hearts"}},
        )
    )

    bonus, notes = pack_execution._generic_pack_goal_bonus(SimpleNamespace(), action)

    assert bonus > 0.0
    assert any("held:rank:K" in note for note in notes)


def test_unrelated_standard_pack_card_gets_no_generic_strategy_bonus(monkeypatch):
    candidate = _candidate(
        bonds=("held_cards", "kings"),
        prescriptions=("seek_feature:held:rank:K",),
    )
    monkeypatch.setattr(pack_execution, "_pinned_candidate", lambda state: candidate)
    action = SimpleNamespace(
        target=SimpleNamespace(
            kind="PLAYING_CARD",
            data={"value": {"rank": "4", "suit": "Clubs"}},
        )
    )

    bonus, notes = pack_execution._generic_pack_goal_bonus(SimpleNamespace(), action)

    assert bonus == pytest.approx(0.0)
    assert notes == ()
