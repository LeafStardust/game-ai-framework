from __future__ import annotations

"""Runtime-schema adapter for authoritative live tuning metrics.

The production decision logger emits some timing/build-health values in rationale
notes rather than structured postmortem fields.  This adapter augments the strict
base parser using those durable notes and derives engine realization from the Bond
rows that are actually logged.
"""

from dataclasses import replace
import json
from pathlib import Path
import re
from statistics import mean
from typing import Iterable

from games.balatro.tuning.live_metrics import episode_metrics_from_run_log as _base_episode_metrics
from games.balatro.tuning.metrics import EpisodeMetrics

_D1_RE = re.compile(r"\bd1_decision_seconds=([0-9]+(?:\.[0-9]+)?)")
_HEALTH_RE = re.compile(
    r"\bBuild Health\s+survival=([0-9]+(?:\.[0-9]+)?)\s+immediate=([0-9]+(?:\.[0-9]+)?)\s+scaling=([0-9]+(?:\.[0-9]+)?)",
    re.IGNORECASE,
)
_REALIZATION_VALUE = {"DORMANT": 0.0, "PARTIAL": 0.5, "ACTIVE": 1.0, "MATURE": 1.0}


def _rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            rows.append(json.loads(raw))
    return rows


def _decision_parts(row: dict) -> tuple[list[str], dict]:
    data = row.get("data") if isinstance(row.get("data"), dict) else {}
    rationale = data.get("rationale") if isinstance(data.get("rationale"), dict) else {}
    notes = rationale.get("notes") if isinstance(rationale.get("notes"), list) else []
    postmortem = rationale.get("postmortem") if isinstance(rationale.get("postmortem"), dict) else {}
    bond_strategy = postmortem.get("bond_strategy") if isinstance(postmortem.get("bond_strategy"), dict) else {}
    return [str(note) for note in notes], bond_strategy


def _engine_realization(bond_strategy: dict) -> float | None:
    engine = str(bond_strategy.get("power_engine") or "")
    if not engine:
        return None
    relevant = bond_strategy.get("relevant_bonds")
    if not isinstance(relevant, list):
        return 0.0
    for bond in relevant:
        if not isinstance(bond, dict):
            continue
        if str(bond.get("bond_id") or "") == engine:
            return _REALIZATION_VALUE.get(str(bond.get("realization") or "").upper(), 0.0)
    return 0.0


def episode_metrics_from_run_log(path: str | Path) -> EpisodeMetrics:
    path = Path(path)
    base = _base_episode_metrics(path)
    rows = _rows(path)

    d1_seconds: list[float] = []
    survival_values: list[float] = []
    scaling_values: list[float] = []
    engine_values: list[float] = []
    mature_motifs = 0

    for row in rows:
        if row.get("event") != "decision":
            continue
        notes, bond_strategy = _decision_parts(row)
        for note in notes:
            match = _D1_RE.search(note)
            if match:
                d1_seconds.append(float(match.group(1)))
            health = _HEALTH_RE.search(note)
            if health:
                survival_values.append(float(health.group(1)))
                scaling_values.append(float(health.group(3)))

        realization = _engine_realization(bond_strategy)
        if realization is not None:
            engine_values.append(realization)

        composition = bond_strategy.get("composition") if isinstance(bond_strategy.get("composition"), dict) else {}
        motifs = composition.get("motifs") if isinstance(composition.get("motifs"), list) else []
        mature_motifs += sum(
            1
            for motif in motifs
            if isinstance(motif, dict) and str(motif.get("state") or "").upper() == "MATURE"
        )

    return replace(
        base,
        d1_mean_seconds=mean(d1_seconds) if d1_seconds else 0.0,
        d1_max_seconds=max(d1_seconds, default=0.0),
        survival_margin=(mean(survival_values) / 100.0) if survival_values else base.survival_margin,
        scaling_score=(mean(scaling_values) / 100.0) if scaling_values else base.scaling_score,
        power_engine_utilization=mean(engine_values) if engine_values else 0.0,
        motif_mature_count=mature_motifs,
    )


def episode_metrics_from_run_ids(
    run_ids: Iterable[str], *, directory: str | Path = "logs/balatro/tuning/runs"
) -> tuple[EpisodeMetrics, ...]:
    root = Path(directory)
    normalized = tuple(str(run_id).strip() for run_id in run_ids)
    if any(not run_id for run_id in normalized):
        raise ValueError("run IDs must not be empty")
    if len(set(normalized)) != len(normalized):
        raise ValueError("run IDs must be unique within one tuning batch")
    return tuple(episode_metrics_from_run_log(root / f"{run_id}.jsonl") for run_id in normalized)
