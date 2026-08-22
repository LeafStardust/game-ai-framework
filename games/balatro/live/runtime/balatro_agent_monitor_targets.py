from __future__ import annotations

from typing import Any

from . import balatro_agent_monitor as base_monitor


_original_build_dashboard = base_monitor.build_dashboard


def _latest_postmortem(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latest = base_monitor._latest(rows, "decision") or {}
    data = latest.get("data") if isinstance(latest.get("data"), dict) else {}
    rationale = data.get("rationale") if isinstance(data.get("rationale"), dict) else {}
    return rationale.get("postmortem") if isinstance(rationale.get("postmortem"), dict) else {}


def _latest_build_health_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    postmortem = _latest_postmortem(rows)
    return postmortem.get("build_health") if isinstance(postmortem.get("build_health"), dict) else {}


def _bond_strategy_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    postmortem = _latest_postmortem(rows)
    return postmortem.get("bond_strategy") if isinstance(postmortem.get("bond_strategy"), dict) else {}


def _pretty(value: Any) -> str:
    return str(value or "-").replace("_", " ").title()


def _pair_text(values: Any) -> str:
    if not isinstance(values, list) or not values:
        return "NONE"
    parts = []
    for value in values:
        if isinstance(value, (list, tuple)):
            parts.append(" <-> ".join(_pretty(item) for item in value))
        else:
            parts.append(_pretty(value))
    return " | ".join(parts)


def _strategy_lines(rows: list[dict[str, Any]]) -> list[str]:
    payload = _bond_strategy_payload(rows)
    if not payload:
        return [
            "STRATEGY / COMPOSITION",
            "-" * 78,
            "Power engine    : -",
            "Relevant Bonds  : -",
            "Motifs          : -",
            "Synergies       : -",
            "Conflicts       : -",
            "Prescriptions   : -",
        ]

    composition = payload.get("composition") if isinstance(payload.get("composition"), dict) else {}
    bonds = payload.get("relevant_bonds") if isinstance(payload.get("relevant_bonds"), list) else []
    lines = [
        "STRATEGY / COMPOSITION",
        "-" * 78,
        f"Power engine    : {_pretty(payload.get('power_engine'))}",
        "Relevant Bonds  :" if bonds else "Relevant Bonds  : NONE",
    ]
    for bond in bonds:
        if not isinstance(bond, dict):
            continue
        rank = str(bond.get("rank") or "-")
        contribution = bond.get("contribution")
        threshold = bond.get("next_rank_threshold")
        realization = str(bond.get("realization") or "-")
        if isinstance(contribution, (int, float)):
            if isinstance(threshold, (int, float)):
                progress = f"{float(contribution):.1f} / {float(threshold):.1f} -> next rank"
            else:
                progress = f"{float(contribution):.1f} / MAX"
        else:
            progress = "-"
        lines.extend(
            [
                f"  {_pretty(bond.get('bond_id'))}",
                f"    Rank         : {rank}",
                f"    Contribution : {progress}",
                f"    Realization  : {realization}",
            ]
        )

    motifs = composition.get("motifs") if isinstance(composition.get("motifs"), list) else []
    motif_text = []
    for motif in motifs:
        if isinstance(motif, dict):
            text = f"{_pretty(motif.get('motif_id'))}={motif.get('state') or '-'}"
            missing = motif.get("missing_components")
            if isinstance(missing, list) and missing:
                text += " missing[" + ", ".join(map(str, missing)) + "]"
            motif_text.append(text)
    lines.extend(
        [
            "Motifs          : " + (" | ".join(motif_text) if motif_text else "NONE"),
            f"Synergies       : {_pair_text(composition.get('synergies'))}",
            f"Conflicts       : {_pair_text(composition.get('conflicts'))}",
            "Prescriptions   : "
            + (
                " | ".join(str(item) for item in composition.get("prescriptions", []))
                if isinstance(composition.get("prescriptions"), list) and composition.get("prescriptions")
                else "NONE"
            ),
        ]
    )
    return lines


def _health_number(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.1f}"
    return str(value) if value not in {None, ""} else "-"


def _build_health_lines(rows: list[dict[str, Any]]) -> list[str]:
    health = _latest_build_health_payload(rows)
    if not health:
        return []
    lines = [
        f"Build Health    : {_health_number(health.get('total'))}" + (" [CRITICAL]" if bool(health.get("critical", False)) else ""),
        f"Survival        : {_health_number(health.get('survival'))}",
        f"Immediate       : {_health_number(health.get('immediate'))}",
        f"Scaling         : {_health_number(health.get('scaling'))}" + (" [DEFICIT]" if bool(health.get("scaling_deficit", False)) else ""),
        f"Coherence       : {_health_number(health.get('coherence'))}",
        f"Runway          : {_health_number(health.get('runway'))}",
    ]
    components = health.get("components") if isinstance(health.get("components"), list) else []
    component_text = []
    for component in components:
        if not isinstance(component, dict):
            continue
        name = component.get("name") or component.get("joker") or component.get("component") or component.get("id")
        role = component.get("role") or component.get("state")
        if name and role:
            text = f"{name}={role}"
            engine_id = component.get("realized_engine_id") or component.get("engine_id")
            if engine_id:
                text += f"/{engine_id}"
            component_text.append(text)
    if component_text:
        lines.append("Components      : " + " | ".join(component_text))
    warnings = health.get("warnings")
    if isinstance(warnings, (list, tuple)) and warnings:
        lines.append("Health warnings : " + " | ".join(str(item) for item in warnings))
    return lines


def build_dashboard(status, *, supervisor_pid, balatro_running, rows, telemetry=None):
    rendered = _original_build_dashboard(
        status,
        supervisor_pid=supervisor_pid,
        balatro_running=balatro_running,
        rows=rows,
        telemetry=telemetry,
    )
    lines = rendered.splitlines()
    try:
        start = lines.index("CURRENT STRATEGY")
        end = lines.index("BUILD HEALTH / REALIZED STRENGTH")
    except ValueError:
        return rendered

    replacement = _strategy_lines(rows)
    replacement.append("")
    lines[start:end] = replacement
    return "\n".join(lines)


base_monitor.build_dashboard = build_dashboard


if __name__ == "__main__":
    raise SystemExit(base_monitor.main())
