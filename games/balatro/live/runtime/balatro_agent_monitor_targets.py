from __future__ import annotations

from typing import Any

from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES

from . import balatro_agent_monitor as base_monitor


_original_build_dashboard = base_monitor.build_dashboard


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

# Conditional runtime relationships are deliberately absent from some static
# catalogue buckets. Keep the monitor honest for the most important dependent
# routes by surfacing their candidate supports here as targets; the evaluator still
# decides whether the dependency is currently satisfied.
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


def _owned_tokens(rows: list[dict[str, Any]]) -> set[str]:
    state = base_monitor._last_state(rows)
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    jokers = payload.get("jokers") if isinstance(payload.get("jokers"), dict) else {}
    cards = jokers.get("cards") if isinstance(jokers.get("cards"), list) else []
    owned: set[str] = set()
    for card in cards:
        if not isinstance(card, dict):
            continue
        for key in ("label", "name", "center", "key"):
            token = _normalize(card.get(key, ""))
            if token:
                owned.add(token)
                if token.endswith("joker"):
                    owned.add(token[:-5])
    return owned


def _dominant_strategy_id(rows: list[dict[str, Any]]) -> str | None:
    latest = base_monitor._latest(rows, "decision") or {}
    data = latest.get("data") if isinstance(latest.get("data"), dict) else {}
    rationale = data.get("rationale") if isinstance(data.get("rationale"), dict) else {}
    postmortem = rationale.get("postmortem") if isinstance(rationale.get("postmortem"), dict) else {}
    strategy = postmortem.get("strategy") if isinstance(postmortem.get("strategy"), dict) else {}
    value = strategy.get("dominant_strategy_id")
    return str(value) if value else None


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
    for label, values in (
        ("G", definition.gold_jokers),
        ("S", definition.silver_jokers),
        ("B", definition.bronze_jokers),
    ):
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
        planets = _unique_components(
            (*definition.gold_planets, *definition.silver_planets, *definition.bronze_planets)
        )
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


def build_dashboard(status, *, supervisor_pid, balatro_running, rows, telemetry=None):
    rendered = _original_build_dashboard(
        status,
        supervisor_pid=supervisor_pid,
        balatro_running=balatro_running,
        rows=rows,
        telemetry=telemetry,
    )
    targets = _strategy_targets(rows)
    target_text = "NONE" if not targets else " | ".join(targets)
    marker = "Path            : "
    lines = rendered.splitlines()
    for index, line in enumerate(lines):
        if line.startswith(marker):
            lines.insert(index + 1, f"Seeking         : {target_text}")
            break
    return "\n".join(lines)


base_monitor.build_dashboard = build_dashboard


if __name__ == "__main__":
    raise SystemExit(base_monitor.main())
