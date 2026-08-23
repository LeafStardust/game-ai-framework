from __future__ import annotations

"""Correct premature strategy authority while preserving forming-plan recruitment.

Live validation showed two failure modes after the first StrategyPlan rollout:
- known motifs could pin from peripheral infrastructure while a defining core Joker
  was still missing (for example Baron + ordinary King density pinning
  ``baron_mime_steel`` without Mime);
- generic behavior graphs could pin from one concrete Joker plus ambient feature
  nodes (for example Superposition creating an aces+straight+tarot strategy).

This layer keeps those candidates visible as FORMING and exposes a bounded scouting
plan for missing core components, but withholds pinned-strategy authority until the
actual strategy core exists.
"""

from dataclasses import replace

import games.balatro.bonds.composer as composer_module
import games.balatro.bonds.evaluation as evaluation_module
import games.balatro.pinned_strategy_shop_goal_policy as shop_goal_module
import games.balatro.strategy_plan_pack_policy as pack_goal_module
from games.balatro.bonds.motifs import MotifState
from games.balatro.bonds.strategy_plan import StrategyPlan, build_strategy_plan
from games.balatro.bonds.strategy_semantics import (
    StrategyCandidate,
    StrategyCommitment,
    pinned_strategy,
)
from games.balatro.shop_utility_scale import ShopUtilityScale


# Defining Joker/component cores. Infrastructure remains valuable while FORMING,
# but cannot by itself confer applied-strategy authority.
_MOTIF_CORES: dict[str, frozenset[str]] = {
    "baron_mime_steel": frozenset({"BARON", "MIME"}),
    "photograph_hanging_chad": frozenset({"PHOTOGRAPH", "HANGING_CHAD"}),
    "vampire_midas": frozenset({"VAMPIRE", "MIDAS_MASK"}),
    "burnt_target_level": frozenset({"BURNT_JOKER"}),
    "low_rank_hack_retrigger": frozenset({"HACK"}),
}

_FORMING_COMPONENT_BONUS = 0.75
_PINNED_COMPONENT_BONUS = 1.25


def _token(value: object) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def _motif_map(motifs) -> dict[str, object]:
    return {str(motif.motif_id): motif for motif in tuple(motifs or ())}


def _core_ready(candidate: StrategyCandidate, motifs) -> bool:
    by_id = _motif_map(motifs)
    primary = str(candidate.strategy_id)
    required = _MOTIF_CORES.get(primary)
    if not required:
        return True
    motif = by_id.get(primary)
    if motif is None:
        return False
    present = {_token(value) for value in tuple(motif.present_components or ())}
    return required.issubset(present)


def _concrete_sources(candidate: StrategyCandidate) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            str(source)
            for source in tuple(candidate.sources or ())
            if not str(source).lower().startswith("feature:")
        )
    )


def _correct_candidate(candidate: StrategyCandidate, motifs) -> StrategyCandidate:
    commitment = candidate.commitment

    # Known package: the defining core must exist before PINNED authority. Keep the
    # candidate visible so the missing-piece tracker can recruit the core.
    if candidate.motif_ids and not _core_ready(candidate, motifs):
        commitment = min(commitment, StrategyCommitment.FORMING)

    # Generic graph: one Joker plus any number of ambient deck/feature nodes is not
    # an applied strategy. It can still be FORMING and continue accumulating proof.
    if not candidate.motif_ids and len(_concrete_sources(candidate)) < 2:
        commitment = min(commitment, StrategyCommitment.FORMING)

    if commitment == candidate.commitment:
        return candidate
    return replace(candidate, commitment=commitment)


def _forming_plan(
    candidate: StrategyCandidate | None,
    developments,
    motifs,
) -> StrategyPlan | None:
    # No FORMING candidate is a normal state for many valid composer scenarios.
    # Treat it as absence of strategy authority, not as an exceptional condition.
    if (
        candidate is None
        or candidate.commitment != StrategyCommitment.FORMING
        or not candidate.motif_ids
    ):
        return None

    # Reuse the canonical plan builder for goal ranking/completion, but do not expose
    # execution prescriptions or Bond-rank pursuit until the strategy is truly pinned.
    provisional = replace(candidate, commitment=StrategyCommitment.PINNED)
    plan = build_strategy_plan(provisional, developments, motifs)
    if plan is None:
        return None

    scouting: list[str] = []
    for feature in tuple(plan.missing_features or ()):
        scouting.append(f"seek_feature:{feature}")
    for component in tuple(plan.missing_components or ()):
        scouting.append(f"seek_component:{component}")

    return replace(
        plan,
        commitment=StrategyCommitment.FORMING,
        prescriptions=tuple(dict.fromkeys(scouting)),
    )


def _best_forming_known(candidates) -> StrategyCandidate | None:
    return next(
        (
            candidate
            for candidate in tuple(candidates or ())
            if candidate.commitment == StrategyCommitment.FORMING
            and bool(candidate.motif_ids)
        ),
        None,
    )


def _component_match(plan: StrategyPlan | None, candidate) -> str | None:
    if plan is None:
        return None
    name = _token(getattr(candidate, "name", None) or candidate.__class__.__name__)
    if not name:
        return None
    for component in tuple(plan.missing_components or ()):
        token = _token(component)
        # Only exact named components get this recruitment bonus. Infrastructure
        # labels such as KING_INFRASTRUCTURE cannot accidentally match a Joker.
        if token and name == token:
            return str(component)
    return None


def install_strategy_authority_correction_policy() -> None:
    if getattr(composer_module, "_strategy_authority_correction_installed", False):
        return

    original_compose = composer_module.compose_build

    def compose_build(state, developments):
        developments = tuple(developments)
        base = original_compose(state, developments)
        corrected = tuple(
            _correct_candidate(candidate, base.motifs)
            for candidate in tuple(base.strategy_candidates or ())
        )
        pinned = pinned_strategy(corrected)
        if pinned is not None:
            plan = build_strategy_plan(pinned, developments, base.motifs)
        else:
            plan = _forming_plan(_best_forming_known(corrected), developments, base.motifs)
            # A lower wrapper may already have produced a valid FORMING scouting
            # plan for a defining-core singleton (for example Burnt Joker before a
            # corresponding BondDevelopment exists). Do not erase that plan merely
            # because candidate reconstruction has insufficient Bond evidence yet.
            if (
                plan is None
                and base.strategy_plan is not None
                and getattr(base.strategy_plan, "commitment", StrategyCommitment.EXPLORATORY)
                == StrategyCommitment.FORMING
                and bool(getattr(base.strategy_plan, "strategy_id", ""))
            ):
                plan = base.strategy_plan

        prescriptions: list[str] = []
        for motif in tuple(base.motifs or ()):
            if motif.state >= MotifState.ACTIVE:
                prescriptions.extend(tuple(motif.prescriptions or ()))
        if plan is not None:
            prescriptions.extend(tuple(plan.prescriptions or ()))

        return replace(
            base,
            strategy_candidates=corrected,
            pinned_strategy_id=None if pinned is None else pinned.strategy_id,
            strategy_plan=plan,
            prescriptions=tuple(dict.fromkeys(prescriptions)),
        )

    # evaluate_bond_composition imported compose_build by value. Patch both names so
    # the correction happens on the raw pass before coherence reinforcement.
    composer_module.compose_build = compose_build
    evaluation_module.compose_build = compose_build

    # A FORMING scouting plan may identify useful missing core components, but it
    # must not steer card/Planet pack development before the core strategy exists.
    original_goal_ids = pack_goal_module._goal_ids

    def goal_ids(plan):
        if plan is not None and getattr(plan, "commitment", StrategyCommitment.EXPLORATORY) < StrategyCommitment.PINNED:
            return ()
        return original_goal_ids(plan)

    pack_goal_module._goal_ids = goal_ids

    # Add exact missing-core recruitment on top of the existing bounded strategy
    # feature bonus. D2 admission/affordability/replacement authorities still run.
    original_joker_gain = ShopUtilityScale.joker_gain

    def joker_gain(self, state, executable):
        utility = original_joker_gain(self, state, executable)
        candidate = getattr(executable, "candidate", None)
        if candidate is None:
            return utility
        try:
            _, composition = evaluation_module.evaluate_bond_composition(state)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            return utility
        plan = getattr(composition, "strategy_plan", None)
        matched = _component_match(plan, candidate)
        if matched is None:
            return utility
        commitment = getattr(plan, "commitment", StrategyCommitment.EXPLORATORY)
        bonus = (
            _PINNED_COMPONENT_BONUS
            if commitment >= StrategyCommitment.PINNED
            else _FORMING_COMPONENT_BONUS
        )
        return replace(
            utility,
            gain=float(utility.gain) + bonus,
            notes=(
                *utility.notes,
                f"strategy missing-core recruitment bonus={bonus:.3f}",
                f"matched missing component={matched}",
                "forming strategies may recruit core pieces without receiving pinned authority",
            ),
        )

    ShopUtilityScale.joker_gain = joker_gain
    composer_module._strategy_authority_correction_installed = True
