from __future__ import annotations

from types import SimpleNamespace

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.live.external.live_pack_validation_coverage import (
    D10_REQUIRED_FLOWS,
    D9_REQUIRED_FAMILIES,
    analyze_run_logs,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.run_experience_transition import log_successful_live_transition


def _snapshot(
    sequence: int,
    phase: str,
    *,
    source: str = "process_memory",
) -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload={
            "live_state_source": source,
            "won": False,
            "hand": {"cards": []},
        },
    )


def _record_transition(
    directory,
    *,
    run_id: str,
    sequence: int,
    phase: str,
    action: BalatroAction,
    notes: tuple[str, ...],
    source: str = "process_memory",
):
    state = SimpleNamespace(
        deck_name="RED",
        stake_name="WHITE",
        phase=phase,
        hand=list(action.cards),
    )
    decision = SimpleNamespace(
        snapshot=_snapshot(sequence, phase, source=source),
        state=state,
        action=action,
        source="pack policy",
        notes=notes,
    )
    result = SimpleNamespace(
        after=_snapshot(sequence + 1, "SHOP", source=source),
    )
    log_successful_live_transition(
        decision,
        result,
        run_id=run_id,
        directory=directory,
    )


def _select(label: str, *, cards=()):
    return BalatroAction(
        SELECT_PACK_CARD,
        cards=list(cards),
        target=SimpleNamespace(area_index=0, label=label),
    )


def test_run_log_analyzer_completes_d9_and_d10_from_successful_live_transitions(tmp_path):
    run_id = "pack-coverage-live"
    tarot_card = object()
    spectral_card = object()

    _record_transition(
        tmp_path,
        run_id=run_id,
        sequence=10,
        phase="BUFFOON_PACK",
        action=BalatroAction(SKIP_BOOSTER),
        notes=("policy_score=0.350000",),
    )
    _record_transition(
        tmp_path,
        run_id=run_id,
        sequence=20,
        phase="STANDARD_PACK",
        action=_select("Steel King"),
        notes=(
            "policy_score=2.000000",
            "B6 playing-card build gain=1.650",
        ),
    )
    _record_transition(
        tmp_path,
        run_id=run_id,
        sequence=30,
        phase="CELESTIAL_PACK",
        action=BalatroAction(SKIP_BOOSTER),
        notes=("policy_score=0.350000",),
    )
    _record_transition(
        tmp_path,
        run_id=run_id,
        sequence=40,
        phase="TAROT_PACK",
        action=_select("The Chariot", cards=(tarot_card,)),
        notes=(
            "policy_score=3.000000",
            "B6 pack target gain=2.000",
            "target_indices=(0,)",
        ),
    )
    _record_transition(
        tmp_path,
        run_id=run_id,
        sequence=50,
        phase="SPECTRAL_PACK",
        action=_select("Deja Vu", cards=(spectral_card,)),
        notes=(
            "policy_score=3.500000",
            "B6 pack target gain=2.500",
            "target_indices=(0,)",
        ),
    )

    report = analyze_run_logs(tmp_path)

    assert report["d9"]["observed"] == D9_REQUIRED_FAMILIES
    assert report["d9"]["missing"] == ()
    assert report["d9"]["complete"] is True
    assert report["d10"]["observed"] == D10_REQUIRED_FLOWS
    assert report["d10"]["missing"] == ()
    assert report["d10"]["complete"] is True
    assert all(record["postcondition_verified"] for record in report["d9"]["evidence"])
    assert all(
        record["live_state_source"] == "process_memory"
        for record in report["d10"]["evidence"]
    )


def test_run_log_analyzer_rejects_non_process_memory_pack_evidence(tmp_path):
    _record_transition(
        tmp_path,
        run_id="synthetic-pack",
        sequence=1,
        phase="STANDARD_PACK",
        action=_select("Steel King"),
        notes=("B6 playing-card build gain=1.000",),
        source="fixture",
    )

    report = analyze_run_logs(tmp_path)

    assert report["d9"]["observed"] == ()
    assert report["d9"]["complete"] is False
    assert report["d10"]["observed"] == ()
    assert report["d10"]["complete"] is False


def test_d10_requires_real_target_indices_and_b6_target_rationale(tmp_path):
    card = object()
    _record_transition(
        tmp_path,
        run_id="untargeted-tarot",
        sequence=1,
        phase="TAROT_PACK",
        action=_select("The Hermit"),
        notes=("B4 build-path gain=4.000",),
    )
    _record_transition(
        tmp_path,
        run_id="unexplained-target",
        sequence=10,
        phase="SPECTRAL_PACK",
        action=_select("Deja Vu", cards=(card,)),
        notes=("policy_score=3.000000", "target_indices=(0,)",),
    )

    report = analyze_run_logs(tmp_path)

    assert report["d9"]["observed"] == ("TAROT", "SPECTRAL")
    assert report["d10"]["observed"] == ()
    assert report["d10"]["missing"] == D10_REQUIRED_FLOWS
