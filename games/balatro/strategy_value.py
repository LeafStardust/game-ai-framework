from __future__ import annotations

from dataclasses import dataclass, replace

from games.balatro.build.consumable_synergy import ContextualConsumableSynergyEvaluator
from games.balatro.build.joker_strategy import (
    JokerBuildTransitionPlanner,
    JokerBuildValue,
    JokerBuildValueEvaluator,
)

from .strategy import (
    BANNED,
    BRONZE,
    COMMITTED,
    GOLD,
    HIGHLIGHTED,
    MATURE,
    SILVER,
    BalatroStrategyTracker,
)
from .strategy_compat import NeutralLegacyPlaystyleIntentTracker
from .strategy_joker_applicability import (
    ALIGNED,
    CONFLICT,
    NEUTRAL_APPLICABILITY,
    OFF_PATH,
    PIVOT,
    UNIVERSAL,
    joker_is_strategy_bound,
)


@dataclass(frozen=True)
class StrategyAdjustedJokerBuildValue(JokerBuildValue):
    """Whole-build Joker value with the strategy term kept auditable."""

    base_total_gain: float
    strategic_adjustment: float
    strategy_id: str | None
    strategy_tier: str | None
    active_alignment: bool
    pivot_candidate: bool
    applicability: str


@dataclass(frozen=True)
class StrategyAdjustedConsumableEvaluation:
    """B4 consumable value plus universal-strategy environment adjustment."""

    total_gain: float
    rationale: tuple[str, ...]
    base_evaluation: object
    strategic_adjustment: float

    @property
    def build_path_gain(self):
        return self.base_evaluation.build_path_gain

    @property
    def paths(self):
        return self.base_evaluation.paths

    @property
    def contributions(self):
        return self.base_evaluation.contributions

    @property
    def descriptor(self):
        return self.base_evaluation.descriptor


class StrategyAwareJokerBuildValueEvaluator(JokerBuildValueEvaluator):
    """Ordinary Joker value plus the universal playbook strategy adjustment."""

    def __init__(self, *args, strategy_tracker: BalatroStrategyTracker, **kwargs) -> None:
        kwargs["intent_tracker"] = NeutralLegacyPlaystyleIntentTracker()
        super().__init__(*args, **kwargs)
        self.strategy_tracker = strategy_tracker

    def _active_probe_hands(self, state) -> tuple[str, ...]:
        resolution = self.strategy_tracker.observe(state)
        if resolution.active_status not in {HIGHLIGHTED, COMMITTED, MATURE}:
            return ()
        strategy_id = resolution.dominant_strategy_id
        primary_getter = getattr(self.strategy_tracker, "primary_strategy_id", None)
        if callable(primary_getter):
            strategy_id = primary_getter(resolution)
        if strategy_id is None:
            return ()
        inherited = getattr(self.strategy_tracker, "primary_hands_for", None)
        if callable(inherited):
            return tuple(str(value) for value in inherited(strategy_id))
        definition = self.strategy_tracker.definitions.get(strategy_id)
        return tuple(definition.primary_hands) if definition is not None else ()

    def _scoring_probes(self, state):
        active_hands = set(self._active_probe_hands(state))
        if not active_hands:
            return super()._scoring_probes(state)
        scoped = tuple(
            probe
            for probe in super()._scoring_probes(state)
            if probe[0].value in active_hands
        )
        return scoped or super()._scoring_probes(state)

    def evaluate(self, state, joker):
        base = super().evaluate(state, joker)
        strategic = self.strategy_tracker.evaluate_item(state, joker, kind="JOKER")
        adjustment = float(strategic.value)
        policy_rationale: tuple[str, ...] = ()
        active_probe_hands = self._active_probe_hands(state)
        probe_rationale = (
            ("strategy-scoped scoring probes=" + ", ".join(active_probe_hands)),
        ) if active_probe_hands else (
            "no active poker-hand prescription; broad scoring probes retained",
        )
        resolution = self.strategy_tracker.observe(state)
        strategy_bound = joker_is_strategy_bound(joker)

        # Weak highlighted evidence remains exploratory so one early pickup does not
        # lock the run. Once the leading route is strongly highlighted, however,
        # strategy-bound off-path Jokers must stop beating aligned support merely
        # because their generic one-hand probe is large. This keeps the agent
        # actively strengthening an established route at every ante while still
        # allowing an explicit pivot candidate to win.
        if resolution.active_status == HIGHLIGHTED and strategic.tier == BANNED:
            if adjustment < 0.0:
                policy_rationale = (
                    "highlighted strategy remains exploratory; defer hard Banned Joker penalty until COMMITTED/MATURE",
                )
                adjustment = 0.0

        if resolution.active_status == HIGHLIGHTED and strategy_bound:
            primary_id = resolution.dominant_strategy_id
            primary_getter = getattr(self.strategy_tracker, "primary_strategy_id", None)
            if callable(primary_getter):
                primary_id = primary_getter(resolution)
            primary = resolution.assessment(primary_id) if primary_id is not None else None
            strong_floor = self.strategy_tracker._number(
                self.strategy_tracker._config(state),
                "strong_highlighted_strategy_floor",
                6.0,
            )
            if (
                primary is not None
                and float(primary.score) >= strong_floor
                and strategic.tier in {GOLD, SILVER, BRONZE}
                and not strategic.active_alignment
                and not strategic.pivot_candidate
            ):
                base_discount = max(0.0, float(base.total_gain))
                adjustment -= base_discount
                policy_rationale = (
                    *policy_rationale,
                    "strong highlighted route actively pursued; off-path Joker generic probe discount="
                    f"-{base_discount:.3f}",
                )

        if (
            resolution.active_status in {COMMITTED, MATURE}
            and strategic.tier in {GOLD, SILVER, BRONZE}
            and not strategic.active_alignment
            and not strategic.pivot_candidate
            and strategy_bound
        ):
            config = self.strategy_tracker._config(state)
            base_discount = (
                max(0.0, float(base.total_gain))
                * self.strategy_tracker._number(
                    config,
                    "off_strategy_joker_base_discount",
                    1.0,
                )
            )
            adjustment -= base_discount
            policy_rationale = (*policy_rationale,
                "committed-strategy off-path Joker generic probe discount="
                f"-{base_discount:.3f}; candidate is neither aligned nor a valid pivot",
            )

        if strategic.tier == BANNED and adjustment < 0.0:
            applicability = CONFLICT
        elif strategic.active_alignment and strategic.tier in {GOLD, SILVER, BRONZE}:
            applicability = ALIGNED
        elif strategic.pivot_candidate:
            applicability = PIVOT
        elif (
            strategy_bound
            and strategic.tier in {GOLD, SILVER, BRONZE}
            and resolution.active_status in {HIGHLIGHTED, COMMITTED, MATURE}
        ):
            applicability = OFF_PATH
        elif float(base.total_gain) > 0.0:
            applicability = UNIVERSAL
        else:
            applicability = NEUTRAL_APPLICABILITY

        total = float(base.total_gain) + adjustment
        return StrategyAdjustedJokerBuildValue(
            joker=base.joker,
            direct_scoring_gain=base.direct_scoring_gain,
            direct_scoring_value=base.direct_scoring_value,
            contextual=base.contextual,
            playstyle_fit=base.playstyle_fit,
            playstyle_value=base.playstyle_value,
            playstyle_locked=base.playstyle_locked,
            total_gain=total,
            rationale=(
                *base.rationale,
                *probe_rationale,
                *strategic.rationale,
                *policy_rationale,
                f"Joker applicability={applicability}",
                "legacy playstyle strategy influence=0.000 in universal-strategy path",
                f"environment-adjusted universal strategy value={adjustment:+.3f}",
                f"strategy-adjusted whole-build gain={total:.3f}",
            ),
            base_total_gain=float(base.total_gain),
            strategic_adjustment=adjustment,
            strategy_id=strategic.strategy_id,
            strategy_tier=strategic.tier,
            active_alignment=bool(strategic.active_alignment),
            pivot_candidate=bool(strategic.pivot_candidate),
            applicability=applicability,
        )


class StrategyAwareJokerBuildTransitionPlanner(JokerBuildTransitionPlanner):
    """Keep hypothetical replacements anchored to the authoritative build."""

    @staticmethod
    def _annotate_option(option):
        incumbent = option.incumbent_value
        candidate = option.candidate_value
        notes = list(option.rationale)
        if (
            isinstance(incumbent, StrategyAdjustedJokerBuildValue)
            and incumbent.strategy_tier == BANNED
            and incumbent.strategic_adjustment < 0.0
        ):
            notes.append(
                "universal-strategy conflict replacement pressure="
                f"{incumbent.strategic_adjustment:+.3f} on incumbent"
            )
            if incumbent.base_total_gain > 0.0:
                notes.append(
                    "incumbent retains non-strategy scoring/context value="
                    f"{incumbent.base_total_gain:.3f}; whole-build delta remains authoritative"
                )
        if (
            isinstance(candidate, StrategyAdjustedJokerBuildValue)
            and candidate.strategy_tier in {GOLD, SILVER, BRONZE}
            and candidate.strategic_adjustment > 0.0
        ):
            notes.append(
                "candidate universal-strategy reinforcement="
                f"{candidate.strategic_adjustment:+.3f} ({candidate.strategy_tier})"
            )
        return replace(option, rationale=tuple(notes))

    def plan(self, state, candidate):
        transition = super().plan(state, candidate)
        if not transition.alternatives:
            return transition
        resolution = self.evaluator.strategy_tracker.observe(state)
        incumbent_strategy = {}
        for index, incumbent in enumerate(state.jokers):
            incumbent_strategy[index] = self.evaluator.strategy_tracker.evaluate_item(
                state, incumbent, kind="JOKER"
            )
        has_off_path_incumbent = any(
            (
                strategic.tier == BANNED and float(strategic.value) < 0.0
            )
            or (
                joker_is_strategy_bound(state.jokers[index])
                and strategic.tier in {GOLD, SILVER, BRONZE}
                and not strategic.active_alignment
                and not strategic.pivot_candidate
            )
            for index, strategic in incumbent_strategy.items()
        )
        prefer_off_path_replacement = (
            resolution.active_status in {COMMITTED, MATURE}
            and getattr(transition.candidate_value, "applicability", None) == UNIVERSAL
            and has_off_path_incumbent
        )
        anchored = []
        for option in transition.alternatives:
            index = int(option.replace_index)
            strategic = incumbent_strategy[index]
            retention = float(strategic.value)
            protected_aligned_core = (
                prefer_off_path_replacement
                and strategic.active_alignment
                and strategic.tier in {GOLD, SILVER, BRONZE}
            )
            blocked_reason = option.blocked_reason
            eligible = option.eligible
            rationale = [
                *option.rationale,
                "authoritative pre-sale strategy retention=" f"{retention:+.3f}",
                "strategy-anchored replacement delta=" f"{float(option.build_delta) - retention:.3f}",
            ]
            if protected_aligned_core:
                eligible = False
                blocked_reason = blocked_reason or "committed aligned Joker protected while an off-path incumbent remains"
                rationale.append(
                    "universal candidate must replace an off-path/Banned incumbent before an aligned committed-strategy Joker"
                )
            anchored.append(
                self._annotate_option(
                    replace(
                        option,
                        build_delta=float(option.build_delta) - retention,
                        rationale=tuple(rationale),
                        eligible=eligible,
                        blocked_reason=blocked_reason,
                    )
                )
            )
        alternatives = tuple(sorted(anchored, key=lambda option: (-option.build_delta, option.replace_index)))
        eligible_alternatives = tuple(option for option in alternatives if option.eligible)
        replacement = (
            eligible_alternatives[0]
            if eligible_alternatives and eligible_alternatives[0].build_delta > self.minimum_replacement_delta
            else None
        )
        action = "REPLACE" if replacement is not None else "HOLD"
        notes = list(transition.rationale)
        conflict_options = [
            option for option in alternatives
            if option.eligible
            if isinstance(option.incumbent_value, StrategyAdjustedJokerBuildValue)
            and option.incumbent_value.strategy_tier == BANNED
            and option.incumbent_value.strategic_adjustment < 0.0
        ]
        if replacement is not None and replacement in conflict_options:
            notes.append("strategy-conflicting incumbent selected only after whole-build replacement delta cleared threshold")
        elif action == "HOLD" and conflict_options:
            notes.append("strategy-conflicting incumbent retained because no whole-build replacement cleared threshold; scoring/context survival value can override strategic purity")
        protected_negative_options = [
            option for option in alternatives
            if not option.eligible
            and option.blocked_reason is not None
            and "Negative Joker" in option.blocked_reason
        ]
        if protected_negative_options:
            notes.append("Negative retention protected replacement slots=" + ",".join(str(option.replace_index) for option in protected_negative_options))
        return replace(
            transition,
            action=action,
            replacement=replacement,
            alternatives=alternatives,
            rationale=tuple(notes),
        )


class StrategyAwareConsumableSynergyEvaluator(ContextualConsumableSynergyEvaluator):
    """B4 consumable value under the universal strategy feedback loop."""

    def __init__(self, *args, strategy_tracker: BalatroStrategyTracker, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_tracker = strategy_tracker

    def evaluate(self, candidate, state, *, profile=None):
        base = super().evaluate(candidate, state, profile=profile)
        category = str(getattr(candidate, "category", "")).upper()
        kind = "PLANET" if category == "PLANET" else "CONSUMABLE"
        strategic = self.strategy_tracker.evaluate_item(state, candidate, kind=kind)
        resolution = self.strategy_tracker.observe(state)

        # Planets are refinement purchases, not exploration purchases. They receive
        # no autonomous build value until a poker-hand strategy is at least
        # HIGHLIGHTED, and the Planet must reinforce that active route.
        if kind == "PLANET" and (
            resolution.active_status not in {HIGHLIGHTED, COMMITTED, MATURE}
            or strategic.tier is None
            or not strategic.active_alignment
        ):
            adjustment = -max(6.0, float(base.total_gain) + 2.0)
            rationale = (
                *base.rationale,
                *strategic.rationale,
                "Planet blocked until a poker-hand strategy is solidified (HIGHLIGHTED or stronger) and this Planet reinforces it",
                f"environment strategy adjustment={adjustment:+.3f}",
            )
        else:
            adjustment = float(strategic.value)
            rationale_parts = [*base.rationale, *strategic.rationale]
            ante = max(1, int(getattr(state, "ante", 1) or 1))
            positive_relationship = strategic.tier in {GOLD, SILVER, BRONZE}
            if (
                category in {"TAROT", "SPECTRAL"}
                and ante >= 3
                and resolution.dominant_strategy_id is not None
                and positive_relationship
                and not strategic.active_alignment
            ):
                config = self.strategy_tracker._config(state)
                if ante >= 6:
                    penalty = self.strategy_tracker._number(config, "late_off_strategy_consumable_penalty", 3.0)
                    phase = "late"
                else:
                    penalty = self.strategy_tracker._number(config, "mid_off_strategy_consumable_penalty", 0.75)
                    phase = "convergence"
                adjustment -= max(0.0, penalty)
                rationale_parts.append(f"{phase} off-shortlist {category} penalty={max(0.0, penalty):.3f}")
            elif category in {"TAROT", "SPECTRAL"} and ante <= 2:
                rationale_parts.append(f"early {category} remains exploration-eligible; no off-strategy penalty")
            rationale_parts.append(f"environment strategy adjustment={adjustment:+.3f}")
            rationale = tuple(rationale_parts)

        return StrategyAdjustedConsumableEvaluation(
            total_gain=float(base.total_gain) + adjustment,
            rationale=tuple(rationale),
            base_evaluation=base,
            strategic_adjustment=adjustment,
        )
