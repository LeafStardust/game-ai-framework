"""R5 public parity extraction for exact shop consumable purchases."""

from __future__ import annotations

from typing import Any, Iterable

from games.balatro.env.actions import EnvAction
from games.balatro.env.parity import (
    PublicStrategicTrajectoryParityComparison,
    compare_public_strategic_trajectory,
)
from games.balatro.env.strategic_evidence import (
    PublicStrategicTransitionEvidence,
    build_public_strategic_transition_evidence,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator


BUY_CONSUMABLE = "BUY_CONSUMABLE"


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


def _canonical_consumable_purchase_action(value: Any, state) -> EnvAction:
    if not isinstance(value, dict):
        raise ValueError("run-log action must be an object")
    if str(value.get("name") or "") != BUY_CONSUMABLE:
        raise ValueError("not a BUY_CONSUMABLE action")
    target = value.get("target")
    if not isinstance(target, dict):
        raise ValueError("BUY_CONSUMABLE run-log action requires a target object")
    area_index = target.get("area_index")
    if isinstance(area_index, bool) or not isinstance(area_index, int):
        raise ValueError("BUY_CONSUMABLE target requires an integer area_index")

    slots = [
        slot
        for slot, item in enumerate(state.shop_consumables)
        if getattr(item, "area_index", None) == area_index
    ]
    if len(slots) != 1:
        raise ValueError(
            "BUY_CONSUMABLE target does not identify exactly one translated shop consumable"
        )
    slot = slots[0]
    item = state.shop_consumables[slot]

    label = target.get("label")
    if label is not None:
        if not isinstance(label, str) or label != getattr(item, "name", None):
            raise ValueError("BUY_CONSUMABLE target label does not match translated item")

    cost = target.get("cost")
    if cost is not None:
        if isinstance(cost, bool) or not isinstance(cost, int):
            raise ValueError("BUY_CONSUMABLE target cost must be an integer")
        if cost != getattr(item, "price", None):
            raise ValueError("BUY_CONSUMABLE target cost does not match translated item")

    return EnvAction.from_alias(BUY_CONSUMABLE, {"slot": slot})


def successful_consumable_purchase_evidence_from_run_rows(
    rows: Iterable[dict[str, Any]],
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> tuple[PublicStrategicTransitionEvidence, ...]:
    """Extract successful exact BUY_CONSUMABLE transitions from durable live rows."""
    translator = translator or DefaultBalatroStateTranslator()
    last_observation: dict[str, Any] | None = None
    pending_purchase: dict[str, Any] | None = None
    evidence: list[PublicStrategicTransitionEvidence] = []

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
            pending_purchase = None
            continue

        if event == "decision":
            action = data.get("action")
            if not isinstance(action, dict):
                raise ValueError("decision row requires action")
            if str(action.get("name") or "") == BUY_CONSUMABLE:
                if last_observation is None:
                    raise ValueError("BUY_CONSUMABLE decision has no preceding observation")
                pending_purchase = action
            else:
                pending_purchase = None
            continue

        if event != "action_result":
            continue
        action = data.get("action")
        if not isinstance(action, dict) or str(action.get("name") or "") != BUY_CONSUMABLE:
            continue
        if last_observation is None or pending_purchase is None:
            raise ValueError("BUY_CONSUMABLE action_result has no captured decision boundary")
        if action != pending_purchase:
            raise ValueError("BUY_CONSUMABLE action_result does not match captured decision")
        if data.get("success") is not True:
            raise ValueError("BUY_CONSUMABLE parity requires a successful action_result")

        before = translator.translate(_snapshot_from_log_state(last_observation))
        after = translator.translate(_snapshot_from_log_state(data.get("state")))
        if before.phase != "SHOP" or after.phase != "SHOP":
            raise ValueError("BUY_CONSUMABLE parity requires SHOP before and after")
        canonical = _canonical_consumable_purchase_action(action, before)
        evidence.append(
            build_public_strategic_transition_evidence(before, canonical, after)
        )
        pending_purchase = None

    return tuple(evidence)


def compare_run_rows_to_simulator_consumable_purchase_evidence(
    rows: Iterable[dict[str, Any]],
    simulator_evidence: Iterable[PublicStrategicTransitionEvidence],
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> PublicStrategicTrajectoryParityComparison:
    live_evidence = successful_consumable_purchase_evidence_from_run_rows(
        rows,
        translator=translator,
    )
    return compare_public_strategic_trajectory(live_evidence, simulator_evidence)
