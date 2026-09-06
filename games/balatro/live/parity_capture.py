"""Adapt durable live run logs into canonical R5 tactical evidence."""

from __future__ import annotations

from typing import Any, Iterable

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.env.parity import (
    PublicTacticalTrajectoryParityComparison,
    compare_public_tactical_trajectory,
)
from games.balatro.env.tactical_evidence import PublicTacticalTransitionEvidence
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator


_TACTICAL_ACTIONS = frozenset({PLAY_CARDS, DISCARD_CARDS})


def _snapshot_from_log_state(value: Any) -> LiveBalatroSnapshot:
    if not isinstance(value, dict):
        raise ValueError("run-log state must be an object")
    sequence = value.get("sequence")
    phase = value.get("phase")
    state_complete = value.get("state_complete")
    payload = value.get("payload")
    if isinstance(sequence, bool) or not isinstance(sequence, int):
        raise ValueError("run-log state sequence must be an integer")
    if not isinstance(phase, str) or not phase:
        raise ValueError("run-log state phase must be a non-empty string")
    if not isinstance(state_complete, bool):
        raise ValueError("run-log state state_complete must be boolean")
    if not isinstance(payload, dict):
        raise ValueError("run-log state payload must be an object")
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=state_complete,
        payload=payload,
    )


def _canonical_tactical_action(value: Any, state) -> tuple[BalatroAction, tuple[int, ...]] | None:
    if not isinstance(value, dict):
        raise ValueError("run-log action must be an object")
    name = str(value.get("name") or "")
    if name not in _TACTICAL_ACTIONS:
        return None
    raw_indices = value.get("indices")
    if not isinstance(raw_indices, list) or not raw_indices:
        raise ValueError(f"{name} run-log action requires visible hand indices")
    if any(isinstance(index, bool) or not isinstance(index, int) for index in raw_indices):
        raise ValueError("run-log hand indices must be integers")
    indices = tuple(raw_indices)
    if len(set(indices)) != len(indices):
        raise ValueError("run-log hand indices must be distinct")
    if any(index < 0 or index >= len(state.hand) for index in indices):
        raise ValueError("run-log hand index is outside the translated public hand")
    cards = [state.hand[index] for index in indices]
    return BalatroAction(name, cards=cards), indices


def successful_tactical_evidence_from_run_rows(
    rows: Iterable[dict[str, Any]],
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> tuple[PublicTacticalTransitionEvidence, ...]:
    """Extract successful live Play/Discard transitions from run-experience rows.

    The live logger records an observation before a decision and the authoritative
    post-action snapshot in the successful action_result row. Non-tactical rows
    (including bond telemetry and semantic events) are ignored. Malformed tactical
    records fail closed rather than being repaired heuristically.
    """
    translator = translator or DefaultBalatroStateTranslator()
    last_observation: dict[str, Any] | None = None
    pending_decision: dict[str, Any] | None = None
    evidence: list[PublicTacticalTransitionEvidence] = []

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("run-log row must be an object")
        event = str(row.get("event") or "")
        data = row.get("data")
        if not isinstance(data, dict):
            continue

        if event == "observation":
            state = data.get("state")
            if not isinstance(state, dict):
                raise ValueError("observation row requires state")
            last_observation = state
            pending_decision = None
            continue

        if event == "decision":
            action = data.get("action")
            if not isinstance(action, dict):
                raise ValueError("decision row requires action")
            if str(action.get("name") or "") in _TACTICAL_ACTIONS:
                if last_observation is None:
                    raise ValueError("tactical decision has no preceding observation")
                pending_decision = action
            else:
                pending_decision = None
            continue

        if event != "action_result" or data.get("success") is not True:
            continue
        action = data.get("action")
        if not isinstance(action, dict) or str(action.get("name") or "") not in _TACTICAL_ACTIONS:
            continue
        if last_observation is None or pending_decision is None:
            raise ValueError("successful tactical action has no captured decision boundary")
        if action != pending_decision:
            raise ValueError("successful tactical action does not match captured decision")

        before = translator.translate(_snapshot_from_log_state(last_observation))
        after_state = data.get("state")
        after = translator.translate(_snapshot_from_log_state(after_state))
        canonical = _canonical_tactical_action(action, before)
        if canonical is None:
            raise AssertionError("tactical action classification changed unexpectedly")
        balatro_action, indices = canonical
        evidence.append(
            PublicTacticalTransitionEvidence(
                before=before,
                action=balatro_action,
                selected_hand_indices=indices,
                after=after,
            )
        )
        pending_decision = None

    return tuple(evidence)


def compare_run_rows_to_simulator_tactical_evidence(
    rows: Iterable[dict[str, Any]],
    simulator_evidence: Iterable[PublicTacticalTransitionEvidence],
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> PublicTacticalTrajectoryParityComparison:
    """Compare durable live tactical rows with an ordered headless trajectory.

    Live rows are first converted through the canonical translator/evidence
    boundary above. The simulator side must already be public-safe R4 evidence;
    this function does not reconstruct private simulator authority from live logs.
    """
    live_evidence = successful_tactical_evidence_from_run_rows(
        rows,
        translator=translator,
    )
    return compare_public_tactical_trajectory(live_evidence, simulator_evidence)
