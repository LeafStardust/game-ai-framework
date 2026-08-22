from __future__ import annotations

from dataclasses import replace

from games.balatro.bond_shop_health_policy import last_strategy_health
from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.motifs import MotifState
from games.balatro.build_health_runtime import projected_state_with_jokers
from games.balatro.joker_policy import HOLD, REPLACE
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.live.strategy_health import StrategyHealthMode


_REQUIRED_NET_GAIN = {
    StrategyHealthMode.SURVIVE: 0.50,
    StrategyHealthMode.REPAIR: 1.00,
    StrategyHealthMode.HOLD: 2.50,
    StrategyHealthMode.REINFORCE: 4.00,
    StrategyHealthMode.EXPLOIT: 6.00,
}

_MOTIF_VALUE = {
    MotifState.ABSENT: 0.0,
    MotifState.POTENTIAL: 1.0,
    MotifState.ACTIVE: 4.0,
    MotifState.MATURE: 7.0,
}


def _projected_jokers(state, candidate, index: int):
    jokers = list(getattr(state, "jokers", ()) or ())
    if index < 0 or index >= len(jokers):
        return None
    jokers[index] = candidate
    return tuple(jokers)


def _motif_map(composition):
    return {motif.motif_id: motif for motif in composition.motifs}


def _distance_score(composition) -> float:
    # Lower missing-count is better. Only visible/potential motifs are represented.
    return -sum(int(missing) for _, missing in composition.motif_distance)


def _transition_score(current, projected) -> tuple[float, tuple[str, ...]]:
    # Composition coherence already contains rank/realization, sparse synergy,
    # motif-state bonus and conflict penalty. Do not add motif-state delta again
    # here: doing so double-counts the same structural evidence.
    coherence_delta = float(projected.coherence_score) - float(current.coherence_score)
    distance_delta = _distance_score(projected) - _distance_score(current)

    current_motifs = _motif_map(current)
    projected_motifs = _motif_map(projected)
    lost_realized_motif = 0.0
    for motif_id, motif in current_motifs.items():
        before = _MOTIF_VALUE.get(motif.state, 0.0)
        after = _MOTIF_VALUE.get(
            getattr(projected_motifs.get(motif_id), "state", MotifState.ABSENT),
            0.0,
        )
        if before >= _MOTIF_VALUE[MotifState.ACTIVE] and after < before:
            lost_realized_motif += before - after

    resistance_loss = max(
        0.0,
        float(current.pivot_resistance) - float(projected.pivot_resistance),
    )
    # Explicit disruption is intentionally asymmetric. Coherence says the new
    # composition is better/worse overall; this extra cost represents the practical
    # risk of dismantling already-realized machinery and established structure.
    disruption = resistance_loss + lost_realized_motif
    net = coherence_delta + 0.5 * distance_delta - disruption
    return net, (
        f"canonical pivot coherence delta={coherence_delta:+.3f}",
        "canonical pivot motif-state value is already included in coherence delta",
        f"canonical pivot motif-distance delta={distance_delta:+.3f}",
        f"canonical pivot disruption cost={disruption:.3f}",
        f"canonical pivot net structural gain={net:+.3f}",
    )


def _canonical_pivot_decision(state, candidate, decision):
    health = last_strategy_health()
    if health is None:
        return decision
    options = tuple(getattr(decision, "options", ()) or ())
    if not options or len(getattr(state, "jokers", ()) or ()) < int(getattr(state, "joker_slots", 0) or 0):
        return decision

    _, current = evaluate_bond_composition(state)
    threshold = _REQUIRED_NET_GAIN[health.mode]
    scored = []
    for option in options:
        if not bool(getattr(option, "eligible", False)):
            continue
        if float(getattr(option, "total_advantage", 0.0) or 0.0) <= 0.0:
            continue
        try:
            index = int(option.replace_index)
        except (AttributeError, TypeError, ValueError):
            continue
        jokers = _projected_jokers(state, candidate, index)
        if jokers is None:
            continue
        projected_state = projected_state_with_jokers(state, jokers)
        _, projected = evaluate_bond_composition(projected_state)
        net, notes = _transition_score(current, projected)
        scored.append((net, float(option.total_advantage), -index, option, notes))

    if not scored:
        return decision

    best_net, _, _, best_option, notes = max(scored, key=lambda item: item[:3])
    mode_note = (
        f"canonical pivot authority mode={health.mode.value}; required structural gain={threshold:.3f}"
    )

    if decision.action == REPLACE:
        selected = getattr(decision, "selected", None)
        selected_entry = next((entry for entry in scored if entry[3] is selected), None)
        if selected_entry is None:
            return decision
        selected_net = selected_entry[0]
        selected_notes = selected_entry[4]
        if selected_net + 1e-12 < threshold:
            return replace(
                decision,
                action=HOLD,
                selected=None,
                rationale=(
                    *getattr(decision, "rationale", ()),
                    *selected_notes,
                    mode_note,
                    "replacement vetoed: realized Bond/motif disruption exceeds canonical pivot authority",
                ),
            )
        return replace(
            decision,
            rationale=(*getattr(decision, "rationale", ()), *selected_notes, mode_note),
        )

    if decision.action == HOLD and best_net + 1e-12 >= threshold:
        return replace(
            decision,
            action=REPLACE,
            selected=best_option,
            rationale=(
                *getattr(decision, "rationale", ()),
                *notes,
                mode_note,
                "replacement promoted: eligible positive D2 transition materially improves canonical realized structure",
            ),
        )
    return decision


def install_bond_pivot_authority() -> None:
    if getattr(PlaybookJokerAcquisitionPolicy, "_bond_pivot_authority_installed", False):
        return
    original_decide = PlaybookJokerAcquisitionPolicy.decide

    def decide(self, state, candidate):
        decision = original_decide(self, state, candidate)
        return _canonical_pivot_decision(state, candidate, decision)

    PlaybookJokerAcquisitionPolicy.decide = decide
    PlaybookJokerAcquisitionPolicy._bond_pivot_authority_installed = True
