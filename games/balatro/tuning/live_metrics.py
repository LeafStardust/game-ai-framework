from __future__ import annotations

"""Public-log metric extraction for authoritative unseeded Balatro tuning.

This parser is deliberately tolerant of older *fields*: unavailable metrics remain
zero rather than being invented. Structural provenance is strict. Corrupt identity,
schema, sequence, or incomplete episode logs fail closed and cannot become Optuna
training signal.
"""

import json
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from games.balatro.tuning.metrics import EpisodeMetrics


RUN_SCHEMA = "balatro-run-experience-v1"


def _rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    rows: list[dict[str, Any]] = []
    expected_run_id = path.name.removesuffix(".jsonl")
    expected_sequence = 1
    identity: tuple[str, str, str, str] | None = None
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at {path}:{line_number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"run log row is not an object at {path}:{line_number}")
        if row.get("schema") != RUN_SCHEMA:
            raise ValueError(f"unexpected run schema at {path}:{line_number}")
        if str(row.get("run_id")) != expected_run_id:
            raise ValueError(f"run id mismatch at {path}:{line_number}")
        sequence = row.get("sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence != expected_sequence:
            raise ValueError(
                f"non-contiguous run sequence at {path}:{line_number}: "
                f"expected {expected_sequence}, observed {sequence!r}"
            )
        expected_sequence += 1
        current_identity = tuple(
            str(row.get(key) or "")
            for key in ("deck", "stake", "playbook", "playbook_version")
        )
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise ValueError(f"run identity changed at {path}:{line_number}")
        rows.append(row)
    return rows


def _state_payload(row: dict[str, Any]) -> dict[str, Any]:
    data = row.get("data") if isinstance(row.get("data"), dict) else {}
    state = data.get("state") if isinstance(data.get("state"), dict) else {}
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    return payload


def _number(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _integer(value: object, default: int = 0) -> int:
    return int(_number(value, float(default)))


def _ante(payload: dict[str, Any]) -> int:
    return max(0, _integer(payload.get("ante_num", payload.get("ante", 0))))


def _score(payload: dict[str, Any]) -> float:
    return _number(payload.get("score", payload.get("blind_score", 0.0)))


def _blind_requirement(payload: dict[str, Any]) -> float:
    blind = payload.get("blind") if isinstance(payload.get("blind"), dict) else {}
    return _number(
        blind.get("score", blind.get("requirement", payload.get("blind_requirement", 0.0)))
    )


def _postmortem(row: dict[str, Any]) -> dict[str, Any]:
    data = row.get("data") if isinstance(row.get("data"), dict) else {}
    rationale = data.get("rationale") if isinstance(data.get("rationale"), dict) else {}
    return rationale.get("postmortem") if isinstance(rationale.get("postmortem"), dict) else {}


def _bond_strategy(postmortem: dict[str, Any]) -> dict[str, Any]:
    return postmortem.get("bond_strategy") if isinstance(postmortem.get("bond_strategy"), dict) else {}


def _build_signature(bond_rows: list[dict[str, Any]]) -> str:
    if not bond_rows:
        return ""
    latest = bond_rows[-1]
    engine = str(latest.get("power_engine") or "")
    relevant = latest.get("relevant_bonds")
    ids: list[str] = []
    if isinstance(relevant, list):
        for item in relevant:
            if isinstance(item, dict):
                bond_id = item.get("bond_id", item.get("id", item.get("name")))
                if bond_id:
                    ids.append(str(bond_id))
    elif isinstance(relevant, dict):
        ids.extend(str(key) for key in relevant)
    return "|".join([engine, *sorted(set(ids))]).strip("|")


def episode_metrics_from_run_log(path: str | Path) -> EpisodeMetrics:
    path = Path(path)
    rows = _rows(path)
    if not rows:
        raise ValueError(f"empty Balatro run log: {path}")

    terminal_rows = [row for row in rows if row.get("event") == "run_finished"]
    if len(terminal_rows) != 1:
        raise ValueError(
            f"completed tuning run must contain exactly one run_finished event: {path}"
        )
    terminal = terminal_rows[0]

    state_rows = [row for row in rows if row.get("event") in {"observation", "action_result", "run_finished"}]
    payloads = [_state_payload(row) for row in state_rows]
    terminal_data = terminal.get("data") if isinstance(terminal.get("data"), dict) else {}
    won = bool(terminal_data.get("won", False))

    ante_reached = max((_ante(payload) for payload in payloads), default=0)
    last_payload = _state_payload(terminal)
    score = _score(last_payload)
    requirement = _blind_requirement(last_payload)
    blind_clear_margin = (score - requirement) / requirement if requirement > 0 else 0.0

    boss_attempts = 0
    boss_clears = 0
    for row in rows:
        if row.get("event") != "action_result":
            continue
        payload = _state_payload(row)
        blind = payload.get("blind") if isinstance(payload.get("blind"), dict) else {}
        is_boss = str(blind.get("type", "")).upper() == "BOSS" or bool(blind.get("boss"))
        if not is_boss:
            continue
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        state = data.get("state") if isinstance(data.get("state"), dict) else {}
        phase = str(state.get("phase", ""))
        if phase in {"ROUND_EVAL", "GAME_OVER"}:
            boss_attempts += 1
            if phase == "ROUND_EVAL" or bool(payload.get("won")):
                boss_clears += 1
    boss_clear_rate = boss_clears / boss_attempts if boss_attempts else 0.0

    decisions = [row for row in rows if row.get("event") == "decision"]
    postmortems = [_postmortem(row) for row in decisions]
    bonds = [_bond_strategy(item) for item in postmortems]
    bonds = [item for item in bonds if item]

    d1_seconds: list[float] = []
    scaling_values: list[float] = []
    survival_values: list[float] = []
    engine_utilization: list[float] = []
    destructive_pivots = 0
    unused_engines = 0
    mature_motifs = 0
    cash_failures = 0
    illegal_actions = 0

    for item in postmortems:
        for key in ("d1_decision_seconds", "decision_seconds"):
            if key in item:
                d1_seconds.append(max(0.0, _number(item[key])))
                break
        health = item.get("build_health") if isinstance(item.get("build_health"), dict) else {}
        if health:
            scaling_values.append(_number(health.get("scaling")))
            survival_values.append(_number(health.get("survival")))
        text = json.dumps(item, ensure_ascii=False).lower()
        if "destructive pivot" in text or "power-engine disruption" in text:
            destructive_pivots += 1
        if "unused active engine" in text:
            unused_engines += 1
        if "cash reserve failure" in text:
            cash_failures += 1
        if "illegal action" in text or "action rejected" in text:
            illegal_actions += 1

    for bond in bonds:
        realization = str(bond.get("power_engine_realization", "")).upper()
        if bond.get("power_engine"):
            engine_utilization.append(
                1.0 if realization in {"ACTIVE", "MATURE"}
                else 0.5 if realization == "PARTIAL"
                else 0.0
            )
        motifs = bond.get("motifs")
        if isinstance(motifs, list):
            mature_motifs += sum(
                1 for motif in motifs
                if isinstance(motif, dict) and str(motif.get("state", "")).upper() == "MATURE"
            )

    scaling = mean(scaling_values) / 100.0 if scaling_values else 0.0
    survival = mean(survival_values) / 100.0 if survival_values else 0.0

    return EpisodeMetrics(
        seed=None,
        won=won,
        ante_reached=ante_reached,
        blind_clear_margin=blind_clear_margin,
        boss_clear_rate=boss_clear_rate,
        scaling_score=scaling,
        survival_margin=survival,
        power_engine_utilization=mean(engine_utilization) if engine_utilization else 0.0,
        unused_active_engine_count=unused_engines,
        destructive_pivot_count=destructive_pivots,
        motif_mature_count=mature_motifs,
        cash_reserve_failure_count=cash_failures,
        illegal_action_count=illegal_actions,
        d1_mean_seconds=mean(d1_seconds) if d1_seconds else 0.0,
        d1_max_seconds=max(d1_seconds, default=0.0),
        build_signature=_build_signature(bonds),
    )


def episode_metrics_from_run_ids(
    run_ids: Iterable[str], *, directory: str | Path = "logs/balatro/runs"
) -> tuple[EpisodeMetrics, ...]:
    root = Path(directory)
    normalized = tuple(str(run_id).strip() for run_id in run_ids)
    if any(not run_id for run_id in normalized):
        raise ValueError("run IDs must not be empty")
    if len(set(normalized)) != len(normalized):
        raise ValueError("run IDs must be unique within one tuning batch")
    return tuple(episode_metrics_from_run_log(root / f"{run_id}.jsonl") for run_id in normalized)
