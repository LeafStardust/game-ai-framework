from __future__ import annotations

import math
from dataclasses import dataclass

from games.balatro.state import BalatroState

from .consumable_synergy import BuildFeatureClosure
from .effects import (
    edition_feature,
    enhancement_feature,
    rank_feature,
    seal_feature,
    suit_feature,
)
from .profile import BalatroBuildProfiler, BuildProfile
from .synergy import BuildSynergyWeights, SynergyContribution


@dataclass(frozen=True)
class ContextualPlayingCardEvaluation:
    """B6 build-context value for one visible playing-card candidate.

    The evaluator describes only public card properties and their relationship to
    the current build. It does not model draw order, future RNG, or the probability
    that this specific card will be drawn in a future hand.
    """

    features: tuple[str, ...]
    prospective_features: tuple[str, ...]
    interaction_gain: float
    contributions: tuple[SynergyContribution, ...]

    @property
    def total_gain(self) -> float:
        return self.interaction_gain

    @property
    def rationale(self) -> tuple[str, ...]:
        return tuple(contribution.detail for contribution in self.contributions)


class ContextualPlayingCardSynergyEvaluator:
    """Value a visible card by semantic compatibility with the current build.

    Direct card quality belongs to the decision layer consuming this evaluator.
    This class contributes only build interaction: enabling/reinforcing Joker
    requirements, adding sources a Joker scales with, and creating features an
    owned Joker amplifies. The relationship vocabulary is shared with B3/B4.
    """

    RANK_ALIASES = {
        "ACE": "A",
        "KING": "K",
        "QUEEN": "Q",
        "JACK": "J",
    }
    ENHANCEMENT_ALIASES = {
        "M_BONUS": "Bonus",
        "M_MULT": "Mult",
        "M_WILD": "Wild",
        "M_GLASS": "Glass",
        "M_STEEL": "Steel",
        "M_STONE": "Stone",
        "M_GOLD": "Gold",
        "M_LUCKY": "Lucky",
    }
    EDITION_ALIASES = {
        "FOIL": "Foil",
        "HOLO": "Holographic",
        "HOLOGRAPHIC": "Holographic",
        "POLYCHROME": "Polychrome",
        "NEGATIVE": "Negative",
    }

    def __init__(
        self,
        *,
        profiler: BalatroBuildProfiler | None = None,
        weights: BuildSynergyWeights | None = None,
        closure: BuildFeatureClosure | None = None,
    ) -> None:
        self.profiler = profiler or BalatroBuildProfiler()
        self.weights = weights or BuildSynergyWeights()
        self.closure = closure or BuildFeatureClosure()

    def evaluate(
        self,
        state: BalatroState,
        *,
        rank: object | None = None,
        suit: object | None = None,
        enhancement: object | None = None,
        seal: object | None = None,
        edition: object | None = None,
        profile: BuildProfile | None = None,
    ) -> ContextualPlayingCardEvaluation:
        build = profile or self.profiler.profile(state)
        direct = self._direct_features(
            rank=rank,
            suit=suit,
            enhancement=enhancement,
            seal=seal,
            edition=edition,
        )
        closure = self.closure.expand(direct)
        all_features = set(closure)
        # BuildFeatureClosure intentionally handles rank/suit/enhancement/seal.
        # Editions have no held alias, so retaining their direct feature is enough.
        all_features.update(direct)

        contributions: list[SynergyContribution] = []
        seen: set[tuple[str, str, str]] = set()

        for descriptor in build.descriptors(kind="JOKER"):
            for feature in sorted(all_features):
                if feature in descriptor.requires:
                    already_present = self._context_strength(build, feature) > 0.0
                    kind = "REINFORCES_REQUIREMENT" if already_present else "ENABLES_REQUIREMENT"
                    amount = (
                        self.weights.satisfied_requirement * 0.40
                        if already_present
                        else self.weights.unmet_requirement
                    )
                    self._append(
                        contributions,
                        seen,
                        kind=kind,
                        feature=feature,
                        source=descriptor.source,
                        amount=amount,
                    )

                if feature in descriptor.scales_with:
                    strength = self._context_strength(build, feature)
                    amount = self.weights.scaling_match / math.sqrt(1.0 + strength)
                    self._append(
                        contributions,
                        seen,
                        kind="ADDS_SCALING_SOURCE",
                        feature=feature,
                        source=descriptor.source,
                        amount=amount,
                    )

                if feature in descriptor.amplifies:
                    self._append(
                        contributions,
                        seen,
                        kind="AMPLIFIED_BY_BUILD",
                        feature=feature,
                        source=descriptor.source,
                        amount=self.weights.amplification_match,
                    )

        gain = sum(contribution.amount for contribution in contributions)
        return ContextualPlayingCardEvaluation(
            features=tuple(sorted(direct)),
            prospective_features=tuple(sorted(all_features - direct)),
            interaction_gain=gain,
            contributions=tuple(contributions),
        )

    @classmethod
    def _direct_features(
        cls,
        *,
        rank: object | None,
        suit: object | None,
        enhancement: object | None,
        seal: object | None,
        edition: object | None,
    ) -> set[str]:
        features: set[str] = set()

        if rank not in (None, ""):
            value = str(rank)
            canonical = cls.RANK_ALIASES.get(value.upper(), value)
            features.add(rank_feature(canonical))
        if suit not in (None, ""):
            features.add(suit_feature(str(suit)))
        if enhancement not in (None, ""):
            raw = str(enhancement)
            canonical = cls.ENHANCEMENT_ALIASES.get(raw.upper(), raw)
            features.add(enhancement_feature(canonical))
        if seal not in (None, ""):
            raw = str(seal)
            canonical = raw[:1].upper() + raw[1:].lower()
            features.add(seal_feature(canonical))
        if edition not in (None, ""):
            raw = str(edition)
            canonical = cls.EDITION_ALIASES.get(
                raw.upper(),
                raw[:1].upper() + raw[1:].lower(),
            )
            features.add(edition_feature(canonical))

        return features

    @staticmethod
    def _context_strength(build: BuildProfile, feature: str) -> float:
        direct = build.strength(feature)
        if feature.startswith("held:") and feature != "held:effect":
            return max(direct, build.strength(feature[len("held:") :]))
        return direct

    @staticmethod
    def _append(
        contributions: list[SynergyContribution],
        seen: set[tuple[str, str, str]],
        *,
        kind: str,
        feature: str,
        source: str,
        amount: float,
    ) -> None:
        key = (kind, feature, source)
        if key in seen or amount <= 0.0:
            return
        seen.add(key)
        contributions.append(
            SynergyContribution(
                kind=kind,
                feature=feature,
                amount=amount,
                source=source,
                detail=(
                    f"visible card creates {feature}; "
                    f"{kind.lower().replace('_', ' ')} for {source} (+{amount:.3f})"
                ),
            )
        )
