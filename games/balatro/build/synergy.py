from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass

from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext
from games.balatro.scoring import HandScore
from games.balatro.state import BalatroState

from .effects import (
    CONSUMABLE_GENERATE,
    DECK_REMOVE,
    DECK_TRANSFORM,
    ECONOMY,
    HAND_LEVEL,
    HELD_EFFECT,
    HELD_RETRIGGER,
    JOKER_GENERATE,
    SCORE_CHIPS,
    SCORE_MULT,
    SCORE_XMULT,
    EffectDescriptor,
    JokerBehaviorAnalyzer,
)
from .profile import BalatroBuildProfiler, BuildProfile


@dataclass(frozen=True)
class BuildSynergyWeights:
    """Unitless structural weights for B3 build-context comparison.

    These are not shop prices or direct chip estimates. They make independently
    inferred effect relationships comparable while keeping every contribution
    visible for later D2/D4/D9 threshold layers.
    """

    score_chips: float = 1.00
    score_mult: float = 1.50
    score_xmult: float = 2.50
    economy: float = 1.25
    held_retrigger: float = 1.50
    hand_level: float = 1.25
    deck_transform: float = 0.75
    deck_remove: float = 0.50
    joker_generate: float = 1.00
    consumable_generate: float = 0.75
    generic_structural_output: float = 0.25
    satisfied_requirement: float = 1.00
    unmet_requirement: float = 1.00
    scaling_match: float = 0.40
    amplification_match: float = 0.80
    reverse_amplification_match: float = 0.80
    copy_multiplier: float = 1.00
    pair_score_delta_multiplier: float = 0.75


@dataclass(frozen=True)
class SynergyContribution:
    kind: str
    feature: str
    amount: float
    source: str
    detail: str


@dataclass(frozen=True)
class JokerPairInteraction:
    """Behavior observed only when two Joker implementations coexist.

    ``COPY`` is emitted when one real implementation exposes the other through
    ``context.data['copy_joker']``. ``CONTEXT_DELTA`` means an actor's score
    output changed relative to the same actor alone. ``CONTEXT_SIGNAL`` records
    new pair-only context data conservatively without assigning fabricated value.
    """

    kind: str
    actor_role: str
    actor: str
    target_role: str | None = None
    target: str | None = None
    features: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContextualBuildEvaluation:
    candidate: str
    descriptor: EffectDescriptor
    intrinsic_gain: float
    interaction_gain: float
    total_gain: float
    matched_requirements: tuple[str, ...]
    unmet_requirements: tuple[str, ...]
    matched_scaling: tuple[str, ...]
    amplified_features: tuple[str, ...]
    reverse_amplified_features: tuple[str, ...]
    pair_interactions: tuple[JokerPairInteraction, ...]
    contributions: tuple[SynergyContribution, ...]

    @property
    def rationale(self) -> tuple[str, ...]:
        return tuple(contribution.detail for contribution in self.contributions)


@dataclass(frozen=True)
class _ActorProbe:
    chips: float
    mult: float
    x_mult: float
    signals: frozenset[str]
    copy_target_role: str | None = None
    copy_target_name: str | None = None


class JokerPairInteractionProbe:
    """Probe pair-only Joker semantics using the actual ``apply`` methods.

    Both relative orders are examined because Joker order is public and can be
    rearranged. Each actor is compared against itself in isolation, so generic
    pair dependence (for example Joker-count effects) is detectable even when no
    explicit semantic marker exists. No live state is touched.
    """

    def probe(self, candidate: Joker, existing: Joker) -> tuple[JokerPairInteraction, ...]:
        if not isinstance(candidate, Joker) or not isinstance(existing, Joker):
            return ()

        layouts = (
            (("candidate", candidate), ("existing", existing)),
            (("existing", existing), ("candidate", candidate)),
        )
        interactions: list[JokerPairInteraction] = []
        seen: set[tuple] = set()

        for layout in layouts:
            for actor_index in (0, 1):
                actor_role, actor_template = layout[actor_index]
                other_role, other_template = layout[1 - actor_index]
                pair = self._probe_pair_actor(layout, actor_index)
                single = self._probe_single_actor(actor_template)

                if pair.copy_target_role == other_role:
                    interaction = JokerPairInteraction(
                        kind="COPY",
                        actor_role=actor_role,
                        actor=type(actor_template).__name__,
                        target_role=other_role,
                        target=type(other_template).__name__,
                        evidence=(
                            f"{type(actor_template).__name__} exposes "
                            f"{type(other_template).__name__} through copy_joker",
                        ),
                    )
                    self._append_unique(interactions, seen, interaction)

                changed_features: list[str] = []
                if abs(pair.chips - single.chips) > 1e-12:
                    changed_features.append(SCORE_CHIPS)
                if abs(pair.mult - single.mult) > 1e-12:
                    changed_features.append(SCORE_MULT)
                if abs(pair.x_mult - single.x_mult) > 1e-12:
                    changed_features.append(SCORE_XMULT)

                if changed_features:
                    interaction = JokerPairInteraction(
                        kind="CONTEXT_DELTA",
                        actor_role=actor_role,
                        actor=type(actor_template).__name__,
                        target_role=other_role,
                        target=type(other_template).__name__,
                        features=tuple(sorted(changed_features)),
                        evidence=(
                            f"{type(actor_template).__name__} changes output when "
                            f"{type(other_template).__name__} is present",
                        ),
                    )
                    self._append_unique(interactions, seen, interaction)

                new_signals = sorted(pair.signals - single.signals - {"copy_joker"})
                if new_signals:
                    interaction = JokerPairInteraction(
                        kind="CONTEXT_SIGNAL",
                        actor_role=actor_role,
                        actor=type(actor_template).__name__,
                        target_role=other_role,
                        target=type(other_template).__name__,
                        evidence=tuple(f"context:{signal}" for signal in new_signals),
                    )
                    self._append_unique(interactions, seen, interaction)

        return tuple(interactions)

    @staticmethod
    def _append_unique(
        interactions: list[JokerPairInteraction],
        seen: set[tuple],
        interaction: JokerPairInteraction,
    ) -> None:
        key = (
            interaction.kind,
            interaction.actor_role,
            interaction.actor,
            interaction.target_role,
            interaction.target,
            interaction.features,
            interaction.evidence,
        )
        if key in seen:
            return
        seen.add(key)
        interactions.append(interaction)

    def _probe_pair_actor(self, layout, actor_index: int) -> _ActorProbe:
        objects = copy.deepcopy([entry[1] for entry in layout])
        roles = [entry[0] for entry in layout]
        actor = objects[actor_index]
        return self._run_actor(
            actor,
            jokers=objects,
            other=objects[1 - actor_index],
            other_role=roles[1 - actor_index],
        )

    def _probe_single_actor(self, actor_template: Joker) -> _ActorProbe:
        actor = copy.deepcopy(actor_template)
        return self._run_actor(actor, jokers=[actor])

    def _run_actor(
        self,
        actor: Joker,
        *,
        jokers: list[Joker],
        other: Joker | None = None,
        other_role: str | None = None,
    ) -> _ActorProbe:
        state = BalatroState()
        state.jokers = jokers
        cards = self._neutral_cards()
        state.hand = copy.deepcopy(cards)
        context = JokerContext(
            state=state,
            score=HandScore(100, 10, 1.0),
            poker_hand=PokerHand.HIGH_CARD,
            cards=copy.deepcopy(cards),
            held_cards=copy.deepcopy(cards),
            trigger="HAND_SCORED",
            data={},
        )

        random_state = random.getstate()
        try:
            random.seed(0)
            result = actor.apply(context)
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return _ActorProbe(100.0, 10.0, 1.0, frozenset())
        finally:
            random.setstate(random_state)

        score = getattr(result, "score", None)
        if score is None:
            chips, mult, x_mult = 100.0, 10.0, 1.0
        else:
            chips = float(score.chips)
            mult = float(score.mult)
            x_mult = float(score.x_mult)

        data = getattr(result, "data", {}) or {}
        signals = frozenset(
            str(key)
            for key, value in data.items()
            if value not in (None, False, 0, "", [], {}, ())
        )
        copy_target = data.get("copy_joker")
        copy_target_role = other_role if other is not None and copy_target is other else None
        copy_target_name = type(other).__name__ if copy_target_role is not None else None

        return _ActorProbe(
            chips=chips,
            mult=mult,
            x_mult=x_mult,
            signals=signals,
            copy_target_role=copy_target_role,
            copy_target_name=copy_target_name,
        )

    @staticmethod
    def _neutral_cards() -> list[BalatroCard]:
        return [
            BalatroCard("A", "Spades"),
            BalatroCard("Q", "Hearts"),
            BalatroCard("J", "Clubs"),
            BalatroCard("9", "Diamonds"),
            BalatroCard("2", "Spades"),
        ]


class ContextualJokerSynergyEvaluator:
    """Compare a Joker's isolated semantics with its fit in the current build.

    B3 intentionally stops short of deciding whether to spend money or replace a
    slot. It returns a transparent structural marginal score that D2 can combine
    later with price, sell value, slot pressure, stake modifiers and survival
    constraints.
    """

    def __init__(
        self,
        *,
        weights: BuildSynergyWeights | None = None,
        profiler: BalatroBuildProfiler | None = None,
        joker_analyzer: JokerBehaviorAnalyzer | None = None,
        pair_probe: JokerPairInteractionProbe | None = None,
    ) -> None:
        self.weights = weights or BuildSynergyWeights()
        self.joker_analyzer = joker_analyzer or JokerBehaviorAnalyzer()
        self.profiler = profiler or BalatroBuildProfiler(joker_analyzer=self.joker_analyzer)
        self.pair_probe = pair_probe or JokerPairInteractionProbe()

    def evaluate(
        self,
        candidate: object,
        state: BalatroState,
        *,
        profile: BuildProfile | None = None,
    ) -> ContextualBuildEvaluation:
        build = profile or self.profiler.profile(state)
        if not isinstance(candidate, Joker):
            descriptor = EffectDescriptor(source=type(candidate).__name__, kind="UNKNOWN")
            return ContextualBuildEvaluation(
                candidate=type(candidate).__name__,
                descriptor=descriptor,
                intrinsic_gain=0.0,
                interaction_gain=0.0,
                total_gain=0.0,
                matched_requirements=(),
                unmet_requirements=(),
                matched_scaling=(),
                amplified_features=(),
                reverse_amplified_features=(),
                pair_interactions=(),
                contributions=(),
            )

        descriptor = self.joker_analyzer.describe(candidate)
        contributions: list[SynergyContribution] = []
        intrinsic_gain = self._intrinsic_gain(descriptor, contributions)

        matched_requirements: list[str] = []
        unmet_requirements: list[str] = []
        matched_scaling: list[str] = []
        amplified_features: list[str] = []
        reverse_amplified_features: list[str] = []
        interaction_gain = 0.0

        for feature in sorted(descriptor.requires):
            strength = self._context_strength(build, feature)
            if strength > 0.0:
                matched_requirements.append(feature)
                amount = self.weights.satisfied_requirement
                interaction_gain += amount
                contributions.append(
                    SynergyContribution(
                        kind="REQUIREMENT_MATCH",
                        feature=feature,
                        amount=amount,
                        source=descriptor.source,
                        detail=(
                            f"requirement {feature} is present in the build "
                            f"(strength={strength:.3f}, +{amount:.3f})"
                        ),
                    )
                )
            else:
                unmet_requirements.append(feature)
                amount = -self.weights.unmet_requirement
                interaction_gain += amount
                contributions.append(
                    SynergyContribution(
                        kind="REQUIREMENT_MISSING",
                        feature=feature,
                        amount=amount,
                        source=descriptor.source,
                        detail=f"requirement {feature} is absent ({amount:.3f})",
                    )
                )

        for feature in sorted(descriptor.scales_with):
            strength = self._context_strength(build, feature)
            if strength <= 0.0:
                continue
            matched_scaling.append(feature)
            amount = self.weights.scaling_match * math.log2(1.0 + strength)
            interaction_gain += amount
            contributions.append(
                SynergyContribution(
                    kind="SCALING_MATCH",
                    feature=feature,
                    amount=amount,
                    source=descriptor.source,
                    detail=(
                        f"scales with {feature} already present at strength "
                        f"{strength:.3f} (+{amount:.3f})"
                    ),
                )
            )

        for feature in sorted(descriptor.amplifies):
            strength = self._context_strength(build, feature)
            if strength <= 0.0:
                continue
            amplified_features.append(feature)
            amount = self.weights.amplification_match * math.log2(1.0 + strength)
            interaction_gain += amount
            contributions.append(
                SynergyContribution(
                    kind="AMPLIFIES_BUILD",
                    feature=feature,
                    amount=amount,
                    source=descriptor.source,
                    detail=(
                        f"amplifies existing {feature} strength {strength:.3f} "
                        f"(+{amount:.3f})"
                    ),
                )
            )

        candidate_features = self._effective_features(descriptor)
        for existing in build.descriptors(kind="JOKER"):
            for feature in sorted(existing.amplifies & candidate_features):
                reverse_amplified_features.append(feature)
                amount = self.weights.reverse_amplification_match
                interaction_gain += amount
                contributions.append(
                    SynergyContribution(
                        kind="AMPLIFIED_BY_BUILD",
                        feature=feature,
                        amount=amount,
                        source=existing.source,
                        detail=(
                            f"existing {existing.source} amplifies candidate feature "
                            f"{feature} (+{amount:.3f})"
                        ),
                    )
                )

        pair_interactions: list[JokerPairInteraction] = []
        existing_jokers = list(getattr(state, "jokers", ()))
        existing_descriptors = list(build.descriptors(kind="JOKER"))
        for index, existing_joker in enumerate(existing_jokers):
            if not isinstance(existing_joker, Joker):
                continue
            interactions = self.pair_probe.probe(candidate, existing_joker)
            pair_interactions.extend(interactions)
            existing_descriptor = (
                existing_descriptors[index]
                if index < len(existing_descriptors)
                else self.joker_analyzer.describe(existing_joker)
            )
            for interaction in interactions:
                amount, feature = self._pair_interaction_gain(
                    interaction,
                    candidate_descriptor=descriptor,
                    existing_descriptor=existing_descriptor,
                    build=build,
                )
                if amount <= 0.0:
                    continue
                interaction_gain += amount
                contributions.append(
                    SynergyContribution(
                        kind=f"PAIR_{interaction.kind}",
                        feature=feature,
                        amount=amount,
                        source=interaction.actor,
                        detail=(
                            f"pair {interaction.kind.lower()} {interaction.actor} -> "
                            f"{interaction.target or 'context'} (+{amount:.3f})"
                        ),
                    )
                )

        total_gain = intrinsic_gain + interaction_gain
        return ContextualBuildEvaluation(
            candidate=type(candidate).__name__,
            descriptor=descriptor,
            intrinsic_gain=intrinsic_gain,
            interaction_gain=interaction_gain,
            total_gain=total_gain,
            matched_requirements=tuple(sorted(set(matched_requirements))),
            unmet_requirements=tuple(sorted(set(unmet_requirements))),
            matched_scaling=tuple(sorted(set(matched_scaling))),
            amplified_features=tuple(sorted(set(amplified_features))),
            reverse_amplified_features=tuple(sorted(set(reverse_amplified_features))),
            pair_interactions=tuple(pair_interactions),
            contributions=tuple(contributions),
        )

    def rank(
        self,
        candidates: list[object] | tuple[object, ...],
        state: BalatroState,
        *,
        profile: BuildProfile | None = None,
    ) -> tuple[ContextualBuildEvaluation, ...]:
        build = profile or self.profiler.profile(state)
        evaluations = [
            self.evaluate(candidate, state, profile=build)
            for candidate in candidates
        ]
        return tuple(
            sorted(
                evaluations,
                key=lambda evaluation: (-evaluation.total_gain, evaluation.candidate),
            )
        )

    def _intrinsic_gain(
        self,
        descriptor: EffectDescriptor,
        contributions: list[SynergyContribution] | None = None,
    ) -> float:
        total = 0.0
        for feature in sorted(self._effective_features(descriptor)):
            amount = self._feature_value(feature)
            if amount <= 0.0:
                continue
            total += amount
            if contributions is not None:
                contributions.append(
                    SynergyContribution(
                        kind="INTRINSIC",
                        feature=feature,
                        amount=amount,
                        source=descriptor.source,
                        detail=f"intrinsic {feature} (+{amount:.3f})",
                    )
                )
        return total

    def _descriptor_context_score(
        self,
        descriptor: EffectDescriptor,
        build: BuildProfile,
    ) -> float:
        score = self._intrinsic_gain(descriptor)
        for feature in descriptor.requires:
            score += (
                self.weights.satisfied_requirement
                if self._context_strength(build, feature) > 0.0
                else -self.weights.unmet_requirement
            )
        for feature in descriptor.scales_with:
            strength = self._context_strength(build, feature)
            if strength > 0.0:
                score += self.weights.scaling_match * math.log2(1.0 + strength)
        return max(0.0, score)

    def _pair_interaction_gain(
        self,
        interaction: JokerPairInteraction,
        *,
        candidate_descriptor: EffectDescriptor,
        existing_descriptor: EffectDescriptor,
        build: BuildProfile,
    ) -> tuple[float, str]:
        if interaction.kind == "COPY":
            target_descriptor = (
                candidate_descriptor
                if interaction.target_role == "candidate"
                else existing_descriptor
            )
            amount = (
                self.weights.copy_multiplier
                * self._descriptor_context_score(target_descriptor, build)
            )
            return amount, "copy_joker"

        if interaction.kind == "CONTEXT_DELTA":
            amount = self.weights.pair_score_delta_multiplier * sum(
                self._feature_value(feature)
                for feature in interaction.features
            )
            return amount, "+".join(interaction.features)

        # Pair-only signals are retained as evidence but remain zero-valued until
        # their semantics are explicitly understood.
        return 0.0, "context_signal"

    def _context_strength(self, build: BuildProfile, feature: str) -> float:
        direct = build.strength(feature)

        if feature == HELD_EFFECT:
            semantic = sum(
                1.0
                for descriptor in build.descriptors(kind="JOKER")
                if self._is_held_effect(descriptor)
            )
            return direct + semantic

        if feature.startswith("held:") and feature not in {HELD_EFFECT, HELD_RETRIGGER}:
            # Public deck composition supplies the potential source for held-rank,
            # held-suit, held-enhancement and held-seal effects without predicting
            # which specific future cards will be held.
            return max(direct, build.strength(feature[len("held:") :]))

        return direct

    @classmethod
    def _effective_features(cls, descriptor: EffectDescriptor) -> frozenset[str]:
        features = set(descriptor.produces) | set(descriptor.transforms)
        if cls._is_held_effect(descriptor):
            features.add(HELD_EFFECT)
        return frozenset(features)

    @staticmethod
    def _is_held_effect(descriptor: EffectDescriptor) -> bool:
        return any(
            feature.startswith("held:")
            and feature not in {HELD_EFFECT, HELD_RETRIGGER}
            for feature in descriptor.requires | descriptor.scales_with
        )

    def _feature_value(self, feature: str) -> float:
        weights = self.weights
        explicit = {
            SCORE_CHIPS: weights.score_chips,
            SCORE_MULT: weights.score_mult,
            SCORE_XMULT: weights.score_xmult,
            ECONOMY: weights.economy,
            HELD_RETRIGGER: weights.held_retrigger,
            HAND_LEVEL: weights.hand_level,
            DECK_TRANSFORM: weights.deck_transform,
            DECK_REMOVE: weights.deck_remove,
            JOKER_GENERATE: weights.joker_generate,
            CONSUMABLE_GENERATE: weights.consumable_generate,
            HELD_EFFECT: 0.0,
        }
        if feature in explicit:
            return explicit[feature]
        if feature.startswith(
            ("rank:", "suit:", "enhancement:", "seal:", "edition:", "hand:", "consumable:")
        ):
            return weights.generic_structural_output
        return 0.0
