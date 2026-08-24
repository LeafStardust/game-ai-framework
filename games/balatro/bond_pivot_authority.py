from __future__ import annotations

from dataclasses import replace

from games.balatro.bond_shop_health_policy import last_strategy_health
from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.motifs import MotifState
from games.balatro.bonds.strategy_semantics import StrategyCommitment
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


def _token(value: object) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def _joker_token(joker) -> str:
    return _token(
        getattr(joker, "name", None)
        or getattr(joker, "label", None)
        or getattr(joker, "center", None)
        or joker.__class__.__name__
    )


def _projected_jokers(state, candidate, index: int):
    jokers = list(getattr(state, "jokers", ()) or ())
    if index < 0 or index >= len(jokers):
        return None
    jokers[index] = candidate
    return tuple(jokers)


def _motif_map(composition):
    return {motif.motif_id: motif for motif in composition.motifs}


def _distance_score(composition) -> float:
    return -sum(int(missing) for _, missing in composition.motif_distance)


def _transition_score(current, projected) -> tuple[float, tuple[str, ...]]:
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
    disruption = resistance_loss + lost_realized_motif
    net = coherence_delta + 0.5 * distance_delta - disruption
    return net, (
        f"canonical pivot coherence delta={coherence_delta:+.3f}",
        "canonical pivot motif-state value is already included in coherence delta",
        f"canonical pivot motif-distance delta={distance_delta:+.3f}",
        f"canonical pivot disruption cost={disruption:.3f}",
        f"canonical pivot net structural gain={net:+.3f}",
    )


def _forming_core_replacement_veto(current, projected, removed_joker) -> tuple[bool, tuple[str, ...]]:
    """Keep a known strategy's defining singleton/core while it is still forming.

    Before the missing-piece tracker existed, D2 could freely churn early Jokers.
    Once a concrete known strategy is FORMING, selling one of its concrete core
    sources should require the replacement to preserve that same plan or establish a
    genuinely stronger pinned plan. Ambient feature sources never receive this guard.
    """

    current_plan = getattr(current, "strategy_plan", None)
    if current_plan is None or getattr(current_plan, "commitment", StrategyCommitment.EXPLORATORY) != StrategyCommitment.FORMING:
        return False, ()

    removed = _joker_token(removed_joker)
    if not removed:
        return False, ()
    core_tokens = {
        _token(source)
        for source in tuple(getattr(current_plan, "core_sources", ()) or ())
        if not str(source).lower().startswith("feature:")
    }
    if removed not in core_tokens:
        return False, ()

    projected_plan = getattr(projected, "strategy_plan", None)
    if projected_plan is not None:
        if str(getattr(projected_plan, "strategy_id", "")) == str(getattr(current_plan, "strategy_id", "")):
            return False, ()
        projected_commitment = getattr(projected_plan, "commitment", StrategyCommitment.EXPLORATORY)
        current_strength = float(getattr(current_plan, "strength", 0.0) or 0.0)
        projected_strength = float(getattr(projected_plan, "strength", 0.0) or 0.0)
        if projected_commitment >= StrategyCommitment.PINNED and projected_strength > current_strength + 1.0:
            return False, ()

    return True, (
        f"forming strategy core retention veto: removing {removed_joker.__class__.__name__}",
        f"current forming strategy={getattr(current_plan, 'strategy_id', 'unknown')}",
        "replacement would dismantle a known missing-piece plan before establishing a materially stronger pinned strategy",
    )


def _canonical_pivot_decision(state, candidate, decision):
    health = last_strategy_health(state)
    if health is None or getattr(decision, "action", None) not in {HOLD, REPLACE}:
        return decision

    options = tuple(getattr(decision, "options", ()) or ())
    if not options:
        return decision

    slots_raw = getattr(state, "joker_slots", None)
    try:
        slots = int(slots_raw)
    except (TypeError, ValueError):
        return decision
    if slots <= 0:
        return decision
    jokers_now = tuple(getattr(state, "jokers", ()) or ())
    if len(jokers_now) < slots:
        return decision

    threshold = _REQUIRED_NET_GAIN.get(getattr(health, "mode", None))
    if threshold is None:
        return decision

    _, current = evaluate_bond_composition(state)
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
        veto, veto_notes = _forming_core_replacement_veto(current, projected, jokers_now[index])
        if veto:
            scored.append((float("-inf"), float(option.total_advantage), -index, option, veto_notes))
            continue
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
