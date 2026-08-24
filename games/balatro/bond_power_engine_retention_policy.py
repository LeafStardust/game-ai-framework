from __future__ import annotations

"""Retention guard for already-realized canonical Bond engines.

A replacement must not destroy an ACTIVE/MATURE Bond merely because diagnostics
happen to rank some other Bond as the single current ``power_engine``.  Retention is
therefore source-aware: every realized Bond materially contributed by the incumbent
being sold is protected unless the projected build preserves that Bond or produces
a materially stronger replacement engine.
"""

from dataclasses import replace

from games.balatro.bonds.diagnostics import bond_strategy_diagnostics
from games.balatro.build_health_runtime import projected_state_with_jokers
from games.balatro.joker_policy import HOLD, REPLACE
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy


_REALIZATION_VALUE = {
    "DORMANT": 0.0,
    "PARTIAL": 0.5,
    "ACTIVE": 1.0,
    "MATURE": 1.5,
}


def _normalize(value: object) -> str:
    token = "".join(character for character in str(value or "").lower() if character.isalnum())
    return token[:-5] if token.endswith("joker") else token


def _joker_tokens(joker) -> set[str]:
    values = {
        type(joker).__name__,
        getattr(joker, "name", ""),
        getattr(joker, "label", ""),
        getattr(joker, "ability_name", ""),
        getattr(joker, "center", ""),
    }
    tokens = {_normalize(value) for value in values}
    return {token for token in tokens if token and token not in {"simplenamespace", "object"}}


def _strength(payload: dict | None) -> float:
    if not payload:
        return 0.0
    return float(payload.get("rank_value", 0) or 0) + _REALIZATION_VALUE.get(
        str(payload.get("realization", "DORMANT")).upper(), 0.0
    )


def _relevant_map(diagnostics: dict) -> dict[str, dict]:
    return {
        str(item.get("bond_id")): item
        for item in diagnostics.get("relevant_bonds", ())
        if item.get("bond_id")
    }


def _projected_jokers(state, candidate, index: int):
    jokers = list(getattr(state, "jokers", ()) or ())
    if index < 0 or index >= len(jokers):
        return None
    jokers[index] = candidate
    return tuple(jokers)


def _incumbent_realized_bonds(current: dict, incumbent) -> tuple[dict, ...]:
    tokens = _joker_tokens(incumbent)
    protected: list[dict] = []
    for payload in current.get("relevant_bonds", ()) or ():
        if str(payload.get("realization", "")).upper() not in {"ACTIVE", "MATURE"}:
            continue
        contributes = False
        for contribution in payload.get("contributors", ()) or ():
            source = _normalize(contribution.get("source", ""))
            if source and any(source == token or source in token or token in source for token in tokens):
                contributes = True
                break
        if contributes:
            protected.append(payload)
    return tuple(protected)


def _best_projected_strength(projected: dict) -> tuple[str | None, float]:
    relevant = tuple(projected.get("relevant_bonds", ()) or ())
    if not relevant:
        return None, 0.0
    best = max(relevant, key=_strength)
    return str(best.get("bond_id")), _strength(best)


def install_bond_power_engine_retention_policy() -> None:
    if getattr(PlaybookJokerAcquisitionPolicy, "_bond_power_engine_retention_installed", False):
        return

    original_decide = PlaybookJokerAcquisitionPolicy.decide

    def decide(self, state, candidate):
        decision = original_decide(self, state, candidate)
        if getattr(decision, "action", None) != REPLACE or getattr(decision, "selected", None) is None:
            return decision

        try:
            index = int(decision.selected.replace_index)
            incumbent = tuple(getattr(state, "jokers", ()) or ())[index]
        except (AttributeError, TypeError, ValueError, IndexError):
            return decision

        current = bond_strategy_diagnostics(state)
        protected = _incumbent_realized_bonds(current, incumbent)
        if not protected:
            return decision

        projected_jokers = _projected_jokers(state, candidate, index)
        if projected_jokers is None:
            return decision
        projected_state = projected_state_with_jokers(state, projected_jokers)
        projected = bond_strategy_diagnostics(projected_state)
        projected_map = _relevant_map(projected)
        projected_engine, projected_engine_strength = _best_projected_strength(projected)

        lost: list[tuple[dict, float, float]] = []
        for payload in protected:
            bond_id = str(payload.get("bond_id"))
            before = _strength(payload)
            after = _strength(projected_map.get(bond_id))
            # Retain when the same realized Bond survives at equal/greater strength.
            if after + 1e-12 >= before:
                continue
            lost.append((payload, before, after))

        if not lost:
            return replace(
                decision,
                rationale=(
                    *decision.rationale,
                    "realized incumbent Bond retention check passed: replacement preserves all ACTIVE/MATURE incumbent-contributed Bonds",
                ),
            )

        # Sticky, not immortal: a genuine materially stronger projected engine may
        # justify abandoning the weakest protected realized engine.
        strongest_lost = max(lost, key=lambda item: item[1])
        required = strongest_lost[1] + 0.75
        if projected_engine_strength + 1e-12 >= required:
            return replace(
                decision,
                rationale=(
                    *decision.rationale,
                    "realized incumbent Bond pivot allowed because projected power materially exceeds the lost realized engine",
                    f"lost {strongest_lost[0].get('bond_id')} strength={strongest_lost[1]:.2f}; projected {projected_engine or 'NONE'} strength={projected_engine_strength:.2f}; required={required:.2f}",
                ),
            )

        lost_text = ", ".join(
            f"{payload.get('bond_id')} {payload.get('rank')}/{payload.get('realization')} {before:.2f}->{after:.2f}"
            for payload, before, after in lost
        )
        return replace(
            decision,
            action=HOLD,
            selected=None,
            rationale=(
                *decision.rationale,
                f"canonical realized-incumbent retention veto: selling {type(incumbent).__name__} would weaken {lost_text}",
                f"best projected engine {projected_engine or 'NONE'} strength={projected_engine_strength:.2f}; required={required:.2f}",
                "fresh structural/Bond progress does not justify dismantling an already realized incumbent-contributed engine",
            ),
        )

    PlaybookJokerAcquisitionPolicy.decide = decide
    PlaybookJokerAcquisitionPolicy._bond_power_engine_retention_installed = True
