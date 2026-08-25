from __future__ import annotations

"""Retention guard for already-realized canonical Bond engines.

A replacement must not destroy an ACTIVE/MATURE Bond merely because diagnostics
happen to rank some other Bond as the single current ``power_engine``. The selected
power engine is also protected once it reaches R2, even while its realization is
still PARTIAL. Retention is therefore source-aware: every realized or developed
Bond materially contributed by the incumbent being sold is protected unless the
projected build preserves that Bond or the replacement itself creates a materially
stronger engine.

This layer also prevents canonical Bond-transition bonuses from rescuing a Joker
replacement that is already worse on the common whole-build baseline. Structural
progress is useful evidence, but it is not permission to sell a proven scoring
component for a weaker candidate.
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
    """Return incumbent Bonds that are already too developed to discard casually.

    ACTIVE/MATURE Bonds remain protected regardless of which engine is currently
    strongest.  The selected power engine also becomes protected at R2 even when
    realization is still PARTIAL: that is a developed composition, not scouting.
    This distinction prevents a short-lived standalone tempo Joker from deleting
    one half of the run's strongest forming engine merely because its immediate
    representative score is higher.
    """
    tokens = _joker_tokens(incumbent)
    power_engine = str(current.get("power_engine") or "")
    protected: list[dict] = []
    for payload in current.get("relevant_bonds", ()) or ():
        realization = str(payload.get("realization", "")).upper()
        developed_power_engine = (
            str(payload.get("bond_id") or "") == power_engine
            and int(payload.get("rank_value", 0) or 0) >= 2
        )
        if realization not in {"ACTIVE", "MATURE"} and not developed_power_engine:
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


def _raw_replacement_delta(policy, state, candidate, index: int) -> float | None:
    """Return the common-baseline D2 delta before Bond-transition bonuses."""
    try:
        transition = policy.transition_planner.plan(state, candidate)
    except (AttributeError, TypeError, ValueError):
        return None
    for option in tuple(getattr(transition, "alternatives", ()) or ()):
        try:
            if int(option.replace_index) == int(index):
                return float(option.build_delta)
        except (AttributeError, TypeError, ValueError):
            continue
    return None


def _best_material_projected_engine(
    current: dict,
    projected: dict,
) -> tuple[str | None, float, float]:
    """Return only engine strength genuinely created/improved by the replacement.

    A strong engine that already existed before the hypothetical sale is not
    evidence that selling some other realized engine is safe. This distinction is
    what prevents an unrelated pinned engine from laundering destructive pivots.
    """
    current_map = _relevant_map(current)
    best_id: str | None = None
    best_after = 0.0
    best_gain = 0.0
    for payload in tuple(projected.get("relevant_bonds", ()) or ()):
        bond_id = str(payload.get("bond_id") or "")
        if not bond_id:
            continue
        after = _strength(payload)
        before = _strength(current_map.get(bond_id))
        gain = after - before
        if gain <= 1e-12:
            continue
        if (gain, after) > (best_gain, best_after):
            best_id = bond_id
            best_after = after
            best_gain = gain
    return best_id, best_after, best_gain


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

        # A structural/Bond bonus may improve long-horizon confidence, but it must
        # never turn a whole-build regression into an incumbent sale. The common
        # baseline already includes immediate score and contextual mechanical
        # semantics. If the candidate loses that comparison, keep the incumbent.
        raw_delta = _raw_replacement_delta(self, state, candidate, index)
        minimum_raw_delta = float(
            getattr(getattr(decision, "thresholds", None), "minimum_replacement_build_delta", 0.0)
            or 0.0
        )
        if raw_delta is not None and raw_delta <= minimum_raw_delta + 1e-12:
            return replace(
                decision,
                action=HOLD,
                selected=None,
                rationale=(
                    *decision.rationale,
                    f"whole-build incumbent retention veto: raw replacement delta={raw_delta:.3f} must exceed {minimum_raw_delta:.3f} before Bond-transition bonuses",
                    "structural/Bond progress cannot rescue a candidate that is already worse than the incumbent on the common baseline",
                ),
            )

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

        lost: list[tuple[dict, float, float]] = []
        for payload in protected:
            bond_id = str(payload.get("bond_id"))
            before = _strength(payload)
            after = _strength(projected_map.get(bond_id))
            if after + 1e-12 >= before:
                continue
            lost.append((payload, before, after))

        if not lost:
            return replace(
                decision,
                rationale=(
                    *decision.rationale,
                    "developed incumbent Bond retention check passed: replacement preserves all ACTIVE/MATURE or R2+ selected-engine Bonds",
                ),
            )

        # Sticky, not immortal: abandoning a realized incumbent engine is allowed
        # only when this replacement itself creates/materially strengthens another
        # engine. Pre-existing engine strength cannot justify the sale.
        strongest_lost = max(lost, key=lambda item: item[1])
        required_strength = strongest_lost[1] + 0.75
        projected_engine, projected_engine_strength, projected_engine_gain = (
            _best_material_projected_engine(current, projected)
        )
        required_gain = max(0.75, strongest_lost[1] - strongest_lost[2])
        if (
            projected_engine_strength + 1e-12 >= required_strength
            and projected_engine_gain + 1e-12 >= required_gain
        ):
            return replace(
                decision,
                rationale=(
                    *decision.rationale,
                    "developed incumbent Bond pivot allowed because the replacement itself creates materially stronger power",
                    f"lost {strongest_lost[0].get('bond_id')} strength={strongest_lost[1]:.2f}->{strongest_lost[2]:.2f}; projected {projected_engine or 'NONE'} strength={projected_engine_strength:.2f} gain={projected_engine_gain:.2f}; required strength={required_strength:.2f} gain={required_gain:.2f}",
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
                f"canonical developed-incumbent retention veto: selling {type(incumbent).__name__} would weaken {lost_text}",
                f"replacement-created best engine {projected_engine or 'NONE'} strength={projected_engine_strength:.2f} gain={projected_engine_gain:.2f}; required strength={required_strength:.2f} gain={required_gain:.2f}",
                "pre-existing engine strength and fresh structural progress do not justify dismantling an already realized/developed incumbent-contributed engine",
            ),
        )

    PlaybookJokerAcquisitionPolicy.decide = decide
    PlaybookJokerAcquisitionPolicy._bond_power_engine_retention_installed = True
