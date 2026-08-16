from __future__ import annotations

import argparse
import json
from typing import Any, Callable

from .finisher_state_translator import FinisherAwareBalatroStateTranslator
from .live_memory_discard_history_observer import (
    DiscardHistorySupervisorLiveMemoryBalatroObserver,
)
from .playstyle_autonomous_runner import (
    PlaystyleAwareLiveMemoryInjectedSingleStepRunner,
)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def d13_preview_payload(decision) -> dict[str, Any]:
    snapshot = decision.snapshot
    payload = snapshot.payload if isinstance(snapshot.payload, dict) else {}
    blind = payload.get("blind") if isinstance(payload.get("blind"), dict) else {}
    state = decision.state
    diagnostics = getattr(decision, "decision_diagnostics", None)

    result: dict[str, Any] = {
        "mode": "READ_ONLY_D13_PREVIEW",
        "gameplay_command_sent": False,
        "phase": str(snapshot.phase),
        "checkpoint_sequence": int(snapshot.sequence),
        "deck": str(getattr(state, "deck_name", payload.get("deck", ""))).upper(),
        "stake": str(getattr(state, "stake_name", payload.get("stake", ""))).upper(),
        "ante": int(getattr(state, "ante", payload.get("ante_num", 0)) or 0),
        "money": int(getattr(state, "money", payload.get("money", 0)) or 0),
        "blind_type": str(blind.get("type") or "UNKNOWN").upper(),
        "tag_key": blind.get("tag"),
        "recommended_action": str(decision.action.name),
        "decision_source": str(decision.source),
        "notes": [str(note) for note in getattr(decision, "notes", ())],
        "diagnostics": _sanitize(diagnostics) if isinstance(diagnostics, dict) else {},
    }
    if str(snapshot.phase) != "BLIND_SELECT":
        result["status"] = "BLOCKED_NOT_BLIND_SELECT"
    elif str(decision.source) != "D13 contextual blind play-vs-skip policy":
        result["status"] = "BLOCKED_NOT_CONTEXTUAL_D13"
    else:
        result["status"] = "READY"
    return result


def collect_d13_preview(
    *,
    observer_factory: Callable[[], object] = (
        DiscardHistorySupervisorLiveMemoryBalatroObserver
    ),
    runner_factory: Callable[[object], object] | None = None,
) -> dict[str, Any]:
    """Collect one production D13 recommendation without submitting gameplay."""
    with observer_factory() as observer:
        if runner_factory is None:
            runner = PlaystyleAwareLiveMemoryInjectedSingleStepRunner(
                observer,
                translator=FinisherAwareBalatroStateTranslator(),
            )
        else:
            runner = runner_factory(observer)
        decision = runner.decide()
    return d13_preview_payload(decision)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read the current authoritative Balatro checkpoint and print the "
            "production D13 blind play-vs-skip recommendation. This command is "
            "strictly read-only and never submits a gameplay action."
        )
    )
    parser.parse_args()

    try:
        result = collect_d13_preview()
    except Exception as error:
        print("D13 live preview -> FAIL")
        print(f"Reason -> {type(error).__name__}: {error}")
        print("Gameplay command sent -> False")
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
