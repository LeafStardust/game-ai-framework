from __future__ import annotations

from typing import Any

from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES

from . import balatro_agent_monitor as base_monitor


_original_build_dashboard = base_monitor.build_dashboard
_original_health_dashboard_fields = base_monitor._health_dashboard_fields


_PRETTY = {
    "dna": "DNA",
    "oopsall6s": "Oops! All 6s",
    "theidol": "The Idol",
    "theduo": "The Duo",
    "thetrio": "The Trio",
    "theorder": "The Order",
    "thetribe": "The Tribe",
    "thefamily": "The Family",
    "hittheroad": "Hit the Road",
    "shootthemoon": "Shoot the Moon",
    "walkietalkie": "Walkie Talkie",
    "fourfingers": "Four Fingers",
    "hangingchad": "Hanging Chad",
    "cardsharp": "Card Sharp",
    "bluejoker": "Blue Joker",
    "steel": "Steel",
    "glass": "Glass",
}

_CONDITIONAL_TARGETS = {
    "aces": (("S", "DNA"), ("S", "Fibonacci"), ("S", "Odd Todd")),
    "planet_constellation": (("S", "Constellation"),),
    "planet_satellite": (("G", "Constellation"),),
    "planet_constellation_satellite": (("G", "Constellation"),),
}


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _pretty_token(token: str) -> str:
    value = _normalize(token)
    if value.endswith("joker"):
        value = value[:-5]
    if value in _PRETTY:
        return _PRETTY[value]
    return value.replace("_", " ").title() if value else "?"


def _latest_postmortem_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latest = base_monitor._latest(rows, "decision") or {}
    data = latest.get("data") if isinstance(latest.get("data"), dict) else {}
    rationale = data.get("rationale") if isinstance(data.get("rationale"), dict) else {}
    postmortem = rationale.get("postmortem") if isinstance(rationale.get("postmortem"), dict) else {}
    return postmortem


def _latest_strategy_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    postmortem = _latest_postmortem_payload(rows)
    strategy = postmortem.get("strategy") if isinstance(postmortem.get("strategy"), dict) else {}
    return strategy


def _latest_build_health_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    postmortem = _latest_postmortem_payload(rows)
    health = postmortem.get("build_health") if isinstance(postmortem.get("build_health"), dict) else {}
    return health


def _owned_cards(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    state = base_monitor._last_state(rows)
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    jokers = payload.get("jokers") if isinstance(payload.get("jokers"), dict) else {}
    cards = jokers.get("cards") if isinstance(jokers.get("cards"), list) else []
    return [card for card in cards if isinstance(card, dict)]


def _owned_tokens(rows: list[dict[str, Any]]) -> set[str]:
    owned: set[str] = set()
    for card in _owned_cards(rows):
        for key in ("label", "name", "center", "key"):
            token = _normalize(card.get(key, ""))
            if token:
                owned.add(token)
                if token.endswith("joker"):
                    owned.add(token[:-5])
    return owned


def _dominant_strategy_id(rows: list[dict[str, Any]]) -> str | None:
    value = _latest_strategy_payload(rows).get("dominant_strategy_id")
    return str(value) if value else None


def _dominant_assessment(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    strategy = _latest_strategy_payload(rows)
    dominant_id = strategy.get("dominant_strategy_id")
    ranked = strategy.get("ranked")
    if dominant_id is None or not isinstance(ranked, list):
        return None
    target = str(dominant_id)
    for row in ranked:
        if isinstance(row, dict) and str(row.get("strategy_id")) == target:
            return row
    return None


def _unique_components(values) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        normalized = _normalize(raw)
        canonical = normalized[:-5] if normalized.endswith("joker") else normalized
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        result.append(_pretty_token(raw))
    return result


def _tiered_owned_components(rows: list[dict[str, Any]], strategy_id: str) -> list[str]:
    definition = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES.get(strategy_id)
    if definition is None:
        return []
    owned = _owned_tokens(rows)
    result: list[str] = []
    for label, values in (("G", definition.gold_jokers), ("S", definition.silver_jokers), ("B", definition.bronze_jokers)):
        matched = []
        for raw in values:
            token = _normalize(raw)
            base = token[:-5] if token.endswith("joker") else token
            if token in owned or base in owned:
                matched.append(raw)
        names = _unique_components(matched)
        if names:
            result.append(f"{label}: " + ", ".join(names))
    return result


def _strategy_has(rows: list[dict[str, Any]]) -> list[str]:
    strategy_id = _dominant_strategy_id(rows)
    if not strategy_id:
        return []
    assessment = _dominant_assessment(rows)
    evidence: list[str] = []
    if assessment is not None:
        rationale = assessment.get("rationale")
        if isinstance(rationale, list):
            for raw in rationale:
                note = str(raw)
                lowered = note.lower()
                if lowered.startswith("owned "):
                    evidence.append(note)
                elif "evidence=" in lowered and not lowered.startswith("tree "):
                    evidence.append(note)
                elif "requirement not met" in lowered:
                    evidence.append(note)
    if not evidence:
        evidence = _tiered_owned_components(rows, strategy_id)
    return evidence[:6]


def _strategy_targets(rows: list[dict[str, Any]]) -> list[str]:
    strategy_id = _dominant_strategy_id(rows)
    if not strategy_id:
        return []
    definition = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES.get(strategy_id)
    if definition is None:
        return []
    owned = _owned_tokens(rows)

    def missing(values):
        result = []
        for raw in values:
            token = _normalize(raw)
            base = token[:-5] if token.endswith("joker") else token
            if token in owned or base in owned:
                continue
            result.append(raw)
        return _unique_components(result)

    targets: list[str] = []
    for label, values in (("G", definition.gold_jokers), ("S", definition.silver_jokers), ("B", definition.bronze_jokers)):
        names = missing(values)
        if names:
            targets.append(f"{label}: " + ", ".join(names))
    for tier, label in _CONDITIONAL_TARGETS.get(strategy_id, ()):
        token = _normalize(label)
        if token not in owned and (token + "joker") not in owned:
            text = f"{tier}: {label}"
            if text not in targets:
                targets.append(text)
    utility: list[str] = []
    if definition.directed_tarots:
        utility.append("Tarot: " + ", ".join(_unique_components(definition.directed_tarots)))
    if definition.gold_planets or definition.silver_planets or definition.bronze_planets:
        planets = _unique_components((*definition.gold_planets, *definition.silver_planets, *definition.bronze_planets))
        if planets:
            utility.append("Planet: " + ", ".join(planets))
    if definition.directed_spectrals:
        utility.append("Spectral: " + ", ".join(_unique_components(definition.directed_spectrals)))
    if definition.preferred_enhancements:
        utility.append("Enhance: " + ", ".join(map(str, definition.preferred_enhancements)))
    if definition.preferred_ranks:
        utility.append("Ranks: " + ", ".join(map(str, definition.preferred_ranks)))
    if definition.preferred_suits:
        utility.append("Suits: " + ", ".join(map(str, definition.preferred_suits)))
    targets.extend(utility)
    return targets


def _canonical_health_fields(rationale: dict[str, Any]) -> dict[str, Any]:
    fields = _original_health_dashboard_fields(rationale)
    postmortem = rationale.get("postmortem") if isinstance(rationale.get("postmortem"), dict) else {}
    health = postmortem.get("build_health") if isinstance(postmortem.get("build_health"), dict) else {}
    components = health.get("components") if isinstance(health.get("components"), list) else []
    if fields.get("roles") in {None, "", "NONE"} and components:
        fields["roles"] = base_monitor._roles_text(components)
    if fields.get("engines") in {None, "", "NONE"} and components:
        engines: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for component in components:
            if not isinstance(component, dict):
                continue
            engine_id = component.get("realized_engine_id") or component.get("engine_id")
            state = component.get("realized_engine_state") or component.get("engine_state")
            if not engine_id:
                continue
            key = (str(engine_id), str(state or "-"))
            if key in seen:
                continue
            seen.add(key)
            engines.append({"engine_id": engine_id, "state": state or "-"})
        if engines:
            fields["engines"] = base_monitor._engine_text(engines)
    return fields


def _health_number(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.1f}"
    return str(value) if value not in {None, ""} else "-"


def _build_health_lines(rows: list[dict[str, Any]]) -> list[str]:
    health = _latest_build_health_payload(rows)
    if not health:
        return []

    total = _health_number(health.get("total"))
    critical = bool(health.get("critical", False))
    scaling_deficit = bool(health.get("scaling_deficit", False))
    lines = [
        f"Build Health    : {total}" + (" [CRITICAL]" if critical else ""),
        f"Survival        : {_health_number(health.get('survival'))}",
        f"Immediate       : {_health_number(health.get('immediate'))}",
        f"Scaling         : {_health_number(health.get('scaling'))}" + (" [DEFICIT]" if scaling_deficit else ""),
        f"Coherence       : {_health_number(health.get('coherence'))}",
        f"Runway          : {_health_number(health.get('runway'))}",
    ]

    components = health.get("components") if isinstance(health.get("components"), list) else []
    component_text: list[str] = []
    for component in components:
        if not isinstance(component, dict):
            continue
        name = component.get("name") or component.get("joker") or component.get("component") or component.get("id")
        role = component.get("role") or component.get("state")
        if not name or not role:
            continue
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
    rendered = _original_build_dashboard(status, supervisor_pid=supervisor_pid, balatro_running=balatro_running, rows=rows, telemetry=telemetry)
    evidence = _strategy_has(rows)
    has_text = "NONE" if not evidence else " | ".join(evidence)
    targets = _strategy_targets(rows)
    target_text = "NONE" if not targets else " | ".join(targets)
    health_lines = _build_health_lines(rows)
    marker = "Path            : "
    lines = rendered.splitlines()
    for index, line in enumerate(lines):
        if line.startswith(marker):
            insertion = [f"Has             : {has_text}", f"Seeking         : {target_text}"]
            insertion.extend(health_lines)
            lines[index + 1:index + 1] = insertion
            break
    return "\n".join(lines)


base_monitor._health_dashboard_fields = _canonical_health_fields
base_monitor.build_dashboard = build_dashboard


if __name__ == "__main__":
    raise SystemExit(base_monitor.main())
