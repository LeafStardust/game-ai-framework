from __future__ import annotations

from pathlib import Path
from typing import Any

from games.balatro.playbook import default_balatro_playbooks

from .run_experience import BalatroRunExperienceLogger, BalatroRunIdentity


TERMINAL_PHASES = frozenset({"GAME_OVER"})

_BUILD_ACTION_FAMILIES = {
    "PLAY_CARDS": "HAND",
    "DISCARD_CARDS": "HAND",
    "BUY_JOKER": "PURCHASE",
    "SELL_JOKER": "SALE",
    "BUY_CONSUMABLE": "PURCHASE",
    "BUY_AND_USE_CONSUMABLE": "USE",
    "BUY_BOOSTER": "PURCHASE",
    "BUY_VOUCHER": "PURCHASE",
    "USE_CONSUMABLE": "USE",
    "SELECT_PACK_CARD": "PACK_CHOICE",
}
_BUILD_SIGNAL_PREFIXES = {
    "B3 ": "B3",
    "B4 ": "B4",
    "B6 ": "B6",
    "D1 ": "D1",
    "D3 ": "D3",
    "D9 ": "D9",
}
_BUILD_SIGNAL_TERMS = (
    "build gain",
    "build delta",
    "whole-build",
    "build path",
    "synergy",
    "interaction",
    "requirement",
    "scales with",
    "scaling source",
    "amplif",
    "playstyle",
    "prospective deck feature",
    "target gain",
)


def _sanitize_public_value(value: Any) -> Any:
    """Keep JSON-safe public semantics while dropping presentation-only UI data."""
    if isinstance(value, dict):
        return {
            str(key): _sanitize_public_value(item)
            for key, item in value.items()
            if str(key) != "ui"
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize_public_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _hand_indices(state: object, cards) -> tuple[int, ...]:
    selected_ids = {id(card) for card in cards}
    return tuple(
        index
        for index, card in enumerate(getattr(state, "hand", ()))
        if id(card) in selected_ids
    )


def _target_payload(target: object) -> dict[str, Any]:
    if target is None:
        return {}
    if isinstance(target, dict):
        source = target
        read = source.get
    else:
        read = lambda name, default=None: getattr(target, name, default)

    payload: dict[str, Any] = {}
    for key in ("area_index", "label", "name", "center", "cost", "price"):
        value = read(key)
        if value is not None:
            payload[key] = _sanitize_public_value(value)
    return payload


def action_log_payload(decision) -> dict[str, Any]:
    action = decision.action
    payload: dict[str, Any] = {"name": str(action.name)}
    indices = _hand_indices(decision.state, getattr(action, "cards", ()))
    if indices:
        payload["indices"] = list(indices)
    target = _target_payload(getattr(action, "target", None))
    if target:
        payload["target"] = target
    return payload


def _build_signal_kind(note: str) -> str | None:
    for prefix, kind in _BUILD_SIGNAL_PREFIXES.items():
        if note.startswith(prefix):
            return kind

    lowered = note.lower()
    if "playstyle" in lowered:
        return "PLAYSTYLE"
    if any(term in lowered for term in _BUILD_SIGNAL_TERMS):
        return "INTERACTION"
    return None


def build_rationale_log_payload(decision) -> dict[str, Any] | None:
    """Project chosen policy rationale into structured build-causal telemetry."""
    action_name = str(decision.action.name)
    action_family = _BUILD_ACTION_FAMILIES.get(action_name)
    if action_family is None:
        return None

    signals: list[dict[str, str]] = []
    for raw_note in getattr(decision, "notes", ()):
        note = str(raw_note)
        kind = _build_signal_kind(note)
        if kind is not None:
            signals.append({"kind": kind, "text": note})

    if not signals:
        return None

    payload: dict[str, Any] = {
        "action_family": action_family,
        "decision_source": str(decision.source),
        "signals": signals,
    }
    prepared_build_intent = getattr(decision, "build_intent", None)
    if prepared_build_intent is not None:
        prepared_payload = getattr(prepared_build_intent, "payload", None)
        if isinstance(prepared_payload, dict):
            intent = prepared_payload.get("intent")
            if intent is not None:
                payload["intent_before"] = _sanitize_public_value(intent)
    return payload


def _snapshot_log_state(snapshot) -> dict[str, Any]:
    return {
        "sequence": int(snapshot.sequence),
        "phase": str(snapshot.phase),
        "state_complete": bool(snapshot.state_complete),
        "payload": _sanitize_public_value(snapshot.payload),
    }


def log_successful_live_transition(
    decision,
    result,
    *,
    run_id: str,
    directory: str | Path = "logs/balatro/runs",
    build_intent: dict[str, Any] | None = None,
) -> BalatroRunExperienceLogger:
    """Append one already-successful guarded live transition to a durable run log.

    This function deliberately runs only after the injected dispatcher has returned
    a settled authoritative post-action snapshot. Preview, stale-state rejection,
    achievement-gate rejection and failed bridge execution therefore write nothing.
    A structured ``build_intent`` event may be inserted before the decision when
    the production run-scoped tracker reports a meaningful public build change.
    """
    normalized_run_id = str(run_id).strip()
    if not normalized_run_id:
        raise ValueError("run_id cannot be empty")

    state = decision.state
    playbook = default_balatro_playbooks().for_state(state)
    identity = BalatroRunIdentity(
        run_id=normalized_run_id,
        deck=str(getattr(state, "deck_name", "UNKNOWN")).upper(),
        stake=str(getattr(state, "stake_name", "UNKNOWN")).upper(),
        playbook=str(playbook.name),
        playbook_version=str(playbook.version),
    )
    logger = BalatroRunExperienceLogger(identity, directory=directory)

    before_state = _snapshot_log_state(decision.snapshot)
    after_state = _snapshot_log_state(result.after)
    action = action_log_payload(decision)
    build_rationale = build_rationale_log_payload(decision)
    prepared_build_intent = getattr(decision, "build_intent", None)
    commit_prepared_build_intent = False
    if build_intent is None and prepared_build_intent is not None:
        build_intent = getattr(
            prepared_build_intent,
            "payload",
            prepared_build_intent,
        )
        commit_prepared_build_intent = hasattr(prepared_build_intent, "commit")

    if logger.sequence == 0:
        logger.run_started(state=before_state)

    logger.observation(before_state)
    if build_intent is not None:
        logger.record(
            "build_intent",
            **_sanitize_public_value(build_intent),
        )
        if commit_prepared_build_intent:
            prepared_build_intent.commit()
    rationale = {
        "decision_source": str(decision.source),
        "notes": [str(note) for note in decision.notes],
    }
    if build_rationale is not None:
        rationale["build_rationale"] = build_rationale
    decision_diagnostics = getattr(decision, "decision_diagnostics", None)
    if isinstance(decision_diagnostics, dict) and decision_diagnostics:
        rationale["postmortem"] = _sanitize_public_value(decision_diagnostics)
    logger.decision(
        action=action,
        rationale=rationale,
    )
    logger.action_result(
        action=action,
        success=True,
        state=after_state,
    )

    if str(result.after.phase) in TERMINAL_PHASES:
        logger.run_finished(
            won=bool(result.after.payload.get("won")),
            state=after_state,
            reason=str(result.after.phase).lower(),
        )

    return logger
