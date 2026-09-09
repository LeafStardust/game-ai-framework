"""Adapt durable live run logs into canonical R5 parity evidence."""

from __future__ import annotations

from typing import Any, Iterable

from games.balatro.actions import (
    BUY_JOKER,
    BUY_VOUCHER,
    DISCARD_CARDS,
    PLAY_CARDS,
    REFRESH_SHOP,
    SELECT_BLIND,
    BalatroAction,
)
from games.balatro.env.actions import EnvAction
from games.balatro.env.parity import (
    PublicStrategicTrajectoryParityComparison,
    PublicTacticalTrajectoryParityComparison,
    compare_public_strategic_trajectory,
    compare_public_tactical_trajectory,
)
from games.balatro.env.strategic_evidence import (
    PublicStrategicTransitionEvidence,
    build_public_strategic_transition_evidence,
)
from games.balatro.env.tactical_evidence import PublicTacticalTransitionEvidence
from games.balatro.env.voucher_capabilities import (
    EXACT_ANTE_VOUCHER_KEYS,
    EXACT_DISCOUNT_VOUCHER_KEYS,
    EXACT_EDITION_RATE_VOUCHER_KEYS,
    EXACT_INTEREST_CAP_VOUCHER_KEYS,
    EXACT_REROLL_COST_VOUCHER_KEYS,
    EXACT_RESOURCE_VOUCHER_KEYS,
    EXACT_SHOP_SIZE_VOUCHER_KEYS,
    EXACT_SHOP_TYPE_RATE_VOUCHER_KEYS,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator


_TACTICAL_ACTIONS = frozenset({PLAY_CARDS, DISCARD_CARDS})
_REROLL_SHOP_LOG_ACTION = {"name": REFRESH_SHOP}
_SELECT_BLIND_LOG_ACTION = {"name": SELECT_BLIND}
_EXACT_REDEEMABLE_VOUCHER_KEYS = (
    EXACT_RESOURCE_VOUCHER_KEYS
    | EXACT_EDITION_RATE_VOUCHER_KEYS
    | EXACT_DISCOUNT_VOUCHER_KEYS
    | EXACT_SHOP_TYPE_RATE_VOUCHER_KEYS
    | EXACT_REROLL_COST_VOUCHER_KEYS
    | EXACT_INTEREST_CAP_VOUCHER_KEYS
    | EXACT_SHOP_SIZE_VOUCHER_KEYS
    | EXACT_ANTE_VOUCHER_KEYS
)


def _canonical_targeted_purchase_action(
    value: Any,
    state,
    *,
    action_name: str,
    shop_items: list[Any],
    item_kind: str,
) -> EnvAction | None:
    if not isinstance(value, dict):
        raise ValueError("run-log action must be an object")
    if str(value.get("name") or "") != action_name:
        return None
    target = value.get("target")
    if not isinstance(target, dict):
        raise ValueError(f"{action_name} run-log action requires a target object")
    area_index = target.get("area_index")
    if isinstance(area_index, bool) or not isinstance(area_index, int):
        raise ValueError(f"{action_name} target requires an integer area_index")
    slots = [
        slot
        for slot, item in enumerate(shop_items)
        if getattr(item, "area_index", None) == area_index
    ]
    if len(slots) != 1:
        raise ValueError(
            f"{action_name} target does not identify exactly one translated shop {item_kind}"
        )
    slot = slots[0]
    item = shop_items[slot]
    target_center = target.get("center")
    if target_center is not None and target_center != getattr(item, "center", None):
        raise ValueError(f"{action_name} target center does not match translated shop {item_kind}")
    return EnvAction.from_alias(action_name, {"slot": slot})


def _canonical_joker_purchase_action(value: Any, state) -> EnvAction | None:
    return _canonical_targeted_purchase_action(
        value,
        state,
        action_name=BUY_JOKER,
        shop_items=state.shop_jokers,
        item_kind="Joker",
    )


def _canonical_voucher_purchase_action(value: Any, state) -> EnvAction | None:
    canonical = _canonical_targeted_purchase_action(
        value,
        state,
        action_name=BUY_VOUCHER,
        shop_items=state.shop_vouchers,
        item_kind="Voucher",
    )
    if canonical is None:
        return None
    item = state.shop_vouchers[canonical.payload()["slot"]]
    key = getattr(item, "center", None)
    if key not in _EXACT_REDEEMABLE_VOUCHER_KEYS:
        raise ValueError("BUY_VOUCHER target is not in the exact redeemable Voucher subset")
    return canonical


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


def _canonical_tactical_action(
    value: Any,
    state,
) -> tuple[BalatroAction, tuple[int, ...]] | None:
    if not isinstance(value, dict):
        raise ValueError("run-log action must be an object")
    name = str(value.get("name") or "")
    if name not in _TACTICAL_ACTIONS:
        return None
    raw_indices = value.get("indices")
    if not isinstance(raw_indices, list) or not raw_indices:
        raise ValueError(f"{name} run-log action requires visible hand indices")
    if any(
        isinstance(index, bool) or not isinstance(index, int)
        for index in raw_indices
    ):
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
        if (
            not isinstance(action, dict)
            or str(action.get("name") or "") not in _TACTICAL_ACTIONS
        ):
            continue
        if last_observation is None or pending_decision is None:
            raise ValueError(
                "successful tactical action has no captured decision boundary"
            )
        if action != pending_decision:
            raise ValueError(
                "successful tactical action does not match captured decision"
            )
        before = translator.translate(_snapshot_from_log_state(last_observation))
        after = translator.translate(_snapshot_from_log_state(data.get("state")))
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
    live_evidence = successful_tactical_evidence_from_run_rows(
        rows,
        translator=translator,
    )
    return compare_public_tactical_trajectory(live_evidence, simulator_evidence)


def successful_reroll_shop_evidence_from_run_rows(
    rows: Iterable[dict[str, Any]],
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> tuple[PublicStrategicTransitionEvidence, ...]:
    """Extract exact ordinary paid shop-reroll transitions from durable live rows.

    Production logs serialize the canonical live action as exactly
    ``{"name": "REFRESH_SHOP"}``. Extra parameters are rejected instead of being
    ignored because R3 maps this parameterless production action to REROLL_SHOP.
    """
    translator = translator or DefaultBalatroStateTranslator()
    last_observation: dict[str, Any] | None = None
    pending_reroll: dict[str, Any] | None = None
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
            pending_reroll = None
            continue

        if event == "decision":
            action = data.get("action")
            if not isinstance(action, dict):
                raise ValueError("decision row requires action")
            if str(action.get("name") or "") == REFRESH_SHOP:
                if action != _REROLL_SHOP_LOG_ACTION:
                    raise ValueError(
                        "REFRESH_SHOP run-log action must not contain parameters"
                    )
                if last_observation is None:
                    raise ValueError(
                        "REFRESH_SHOP decision has no preceding observation"
                    )
                pending_reroll = action
            else:
                pending_reroll = None
            continue

        if event != "action_result":
            continue
        action = data.get("action")
        if (
            not isinstance(action, dict)
            or str(action.get("name") or "") != REFRESH_SHOP
        ):
            continue
        if action != _REROLL_SHOP_LOG_ACTION:
            raise ValueError("REFRESH_SHOP run-log action must not contain parameters")
        if last_observation is None or pending_reroll is None:
            raise ValueError(
                "REFRESH_SHOP action_result has no captured decision boundary"
            )
        if action != pending_reroll:
            raise ValueError(
                "REFRESH_SHOP action_result does not match captured decision"
            )
        if data.get("success") is not True:
            raise ValueError("REROLL_SHOP parity requires a successful action_result")

        before = translator.translate(_snapshot_from_log_state(last_observation))
        after = translator.translate(_snapshot_from_log_state(data.get("state")))
        if before.phase != "SHOP" or after.phase != "SHOP":
            raise ValueError("REROLL_SHOP parity requires SHOP before and after")
        evidence.append(
            build_public_strategic_transition_evidence(
                before,
                EnvAction.from_alias("REROLL_SHOP"),
                after,
            )
        )
        pending_reroll = None

    return tuple(evidence)


def compare_run_rows_to_simulator_reroll_shop_evidence(
    rows: Iterable[dict[str, Any]],
    simulator_evidence: Iterable[PublicStrategicTransitionEvidence],
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> PublicStrategicTrajectoryParityComparison:
    live_evidence = successful_reroll_shop_evidence_from_run_rows(
        rows,
        translator=translator,
    )
    return compare_public_strategic_trajectory(live_evidence, simulator_evidence)


def _successful_targeted_purchase_evidence_from_run_rows(
    rows: Iterable[dict[str, Any]],
    *,
    action_name: str,
    canonical_action,
    translator: DefaultBalatroStateTranslator | None = None,
) -> tuple[PublicStrategicTransitionEvidence, ...]:
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
            if str(action.get("name") or "") == action_name:
                if last_observation is None:
                    raise ValueError(
                        f"{action_name} decision has no preceding observation"
                    )
                pending_purchase = action
            else:
                pending_purchase = None
            continue
        if event != "action_result":
            continue
        action = data.get("action")
        if (
            not isinstance(action, dict)
            or str(action.get("name") or "") != action_name
        ):
            continue
        if last_observation is None or pending_purchase is None:
            raise ValueError(
                f"{action_name} action_result has no captured decision boundary"
            )
        if action != pending_purchase:
            raise ValueError(
                f"{action_name} action_result does not match captured decision"
            )
        if data.get("success") is not True:
            raise ValueError(
                f"{action_name} parity requires a successful action_result"
            )

        before = translator.translate(_snapshot_from_log_state(last_observation))
        after = translator.translate(_snapshot_from_log_state(data.get("state")))
        if before.phase != "SHOP" or after.phase != "SHOP":
            raise ValueError(f"{action_name} parity requires SHOP before and after")
        canonical = canonical_action(action, before)
        if canonical is None:
            raise AssertionError(
                f"{action_name} purchase classification changed unexpectedly"
            )
        evidence.append(
            build_public_strategic_transition_evidence(before, canonical, after)
        )
        pending_purchase = None

    return tuple(evidence)


def successful_joker_purchase_evidence_from_run_rows(
    rows: Iterable[dict[str, Any]],
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> tuple[PublicStrategicTransitionEvidence, ...]:
    """Extract successful supported Joker purchases from durable live rows."""
    return _successful_targeted_purchase_evidence_from_run_rows(
        rows,
        action_name=BUY_JOKER,
        canonical_action=_canonical_joker_purchase_action,
        translator=translator,
    )


def compare_run_rows_to_simulator_joker_purchase_evidence(
    rows: Iterable[dict[str, Any]],
    simulator_evidence: Iterable[PublicStrategicTransitionEvidence],
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> PublicStrategicTrajectoryParityComparison:
    live_evidence = successful_joker_purchase_evidence_from_run_rows(
        rows,
        translator=translator,
    )
    return compare_public_strategic_trajectory(live_evidence, simulator_evidence)


def successful_voucher_purchase_evidence_from_run_rows(
    rows: Iterable[dict[str, Any]],
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> tuple[PublicStrategicTransitionEvidence, ...]:
    """Extract successful exact-redeemable Voucher purchases from durable live rows."""
    return _successful_targeted_purchase_evidence_from_run_rows(
        rows,
        action_name=BUY_VOUCHER,
        canonical_action=_canonical_voucher_purchase_action,
        translator=translator,
    )


def compare_run_rows_to_simulator_voucher_purchase_evidence(
    rows: Iterable[dict[str, Any]],
    simulator_evidence: Iterable[PublicStrategicTransitionEvidence],
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> PublicStrategicTrajectoryParityComparison:
    live_evidence = successful_voucher_purchase_evidence_from_run_rows(
        rows,
        translator=translator,
    )
    return compare_public_strategic_trajectory(live_evidence, simulator_evidence)


def successful_select_blind_evidence_from_run_rows(
    rows: Iterable[dict[str, Any]],
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> tuple[PublicStrategicTransitionEvidence, ...]:
    """Extract exact settled parameterless SELECT_BLIND transitions."""
    translator = translator or DefaultBalatroStateTranslator()
    last_observation: dict[str, Any] | None = None
    pending_select: dict[str, Any] | None = None
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
            pending_select = None
            continue
        if event == "decision":
            action = data.get("action")
            if not isinstance(action, dict):
                raise ValueError("decision row requires action")
            if str(action.get("name") or "") == SELECT_BLIND:
                if action != _SELECT_BLIND_LOG_ACTION:
                    raise ValueError("SELECT_BLIND run-log action must not contain parameters")
                if last_observation is None:
                    raise ValueError("SELECT_BLIND decision has no preceding observation")
                pending_select = action
            else:
                pending_select = None
            continue
        if event != "action_result":
            continue
        action = data.get("action")
        if not isinstance(action, dict) or str(action.get("name") or "") != SELECT_BLIND:
            continue
        if action != _SELECT_BLIND_LOG_ACTION:
            raise ValueError("SELECT_BLIND run-log action must not contain parameters")
        if last_observation is None or pending_select is None:
            raise ValueError("SELECT_BLIND action_result has no captured decision boundary")
        if action != pending_select:
            raise ValueError("SELECT_BLIND action_result does not match captured decision")
        if data.get("success") is not True:
            raise ValueError("SELECT_BLIND parity requires a successful action_result")

        before = translator.translate(_snapshot_from_log_state(last_observation))
        after = translator.translate(_snapshot_from_log_state(data.get("state")))
        if before.phase != "BLIND_SELECT" or after.phase != "SELECTING_HAND":
            raise ValueError(
                "SELECT_BLIND parity requires BLIND_SELECT before and SELECTING_HAND after"
            )
        evidence.append(
            build_public_strategic_transition_evidence(
                before,
                EnvAction.from_alias("SELECT_BLIND"),
                after,
            )
        )
        pending_select = None

    return tuple(evidence)


def compare_run_rows_to_simulator_select_blind_evidence(
    rows: Iterable[dict[str, Any]],
    simulator_evidence: Iterable[PublicStrategicTransitionEvidence],
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> PublicStrategicTrajectoryParityComparison:
    live_evidence = successful_select_blind_evidence_from_run_rows(
        rows,
        translator=translator,
    )
    return compare_public_strategic_trajectory(live_evidence, simulator_evidence)
