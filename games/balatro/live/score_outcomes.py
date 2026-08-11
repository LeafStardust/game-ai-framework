from __future__ import annotations

from dataclasses import dataclass
from math import comb

from games.balatro.hand import PokerHand
from games.balatro.live.joker_projection import LiveJokerScoreProjector
from games.balatro.scoring import BalatroScorer


@dataclass(frozen=True)
class ScoreOutcome:
    score: int
    probability: float


@dataclass(frozen=True)
class ScoreOutcomeDistribution:
    """Discrete scoring outcomes for one visible play."""

    outcomes: tuple[ScoreOutcome, ...]
    random_sources: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.outcomes:
            raise ValueError("score outcome distribution requires at least one outcome")
        total_probability = sum(outcome.probability for outcome in self.outcomes)
        if abs(total_probability - 1.0) > 1e-9:
            raise ValueError(
                "score outcome probabilities must sum to 1.0, got "
                f"{total_probability}"
            )

    @property
    def minimum(self) -> int:
        return min(outcome.score for outcome in self.outcomes)

    @property
    def maximum(self) -> int:
        return max(outcome.score for outcome in self.outcomes)

    @property
    def expected(self) -> float:
        return sum(
            outcome.score * outcome.probability
            for outcome in self.outcomes
        )

    @property
    def deterministic(self) -> bool:
        return len(self.outcomes) == 1

    def probability_at_least(self, threshold: int | float) -> float:
        return sum(
            outcome.probability
            for outcome in self.outcomes
            if outcome.score >= threshold
        )


@dataclass(frozen=True)
class ScoreProjectionTransition:
    """Score distribution plus the isolated post-scoring branch state."""

    distribution: ScoreOutcomeDistribution
    state_after_scoring: object | None
    unsupported_jokers: tuple[str, ...] = ()

    @property
    def joker_projection_complete(self) -> bool:
        return not self.unsupported_jokers


class VisibleCardScoreOutcomeModel:
    """Project public visible scoring without consuming Balatro's hidden RNG.

    Card-level Lucky Mult is represented analytically. Joker scoring is delegated
    to ``LiveJokerScoreProjector``, which deep-copies the state and only executes
    Joker implementations that have been explicitly validated for live projection.
    Stateful mutations therefore belong to the hypothetical branch, never to the
    authoritative observed state.
    """

    LUCKY_MULT_PROBABILITY = 0.2
    LUCKY_MULT_BONUS = 20

    def __init__(
        self,
        scorer: BalatroScorer | None = None,
        joker_projector: LiveJokerScoreProjector | None = None,
    ):
        self.scorer = scorer or BalatroScorer()
        self.joker_projector = joker_projector or LiveJokerScoreProjector(self.scorer)

    def project(
        self,
        hand: PokerHand,
        state,
        cards,
        *,
        include_card_chips: bool = True,
    ) -> ScoreOutcomeDistribution:
        return self.project_transition(
            hand,
            state,
            cards,
            include_card_chips=include_card_chips,
        ).distribution

    def project_transition(
        self,
        hand: PokerHand,
        state,
        cards,
        *,
        include_card_chips: bool = True,
    ) -> ScoreProjectionTransition:
        joker_projection = self.joker_projector.score(
            hand,
            state,
            cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=False,
        )
        base = joker_projection.score
        copied_cards = joker_projection.cards_after_copy

        lucky_triggers = self._lucky_scoring_triggers(hand, copied_cards)
        if lucky_triggers == 0:
            distribution = ScoreOutcomeDistribution(
                outcomes=(ScoreOutcome(base.total, 1.0),),
            )
            return ScoreProjectionTransition(
                distribution=distribution,
                state_after_scoring=joker_projection.state_after_scoring,
                unsupported_jokers=joker_projection.unsupported_jokers,
            )

        probabilities: dict[int, float] = {}
        p = self.LUCKY_MULT_PROBABILITY
        for successes in range(lucky_triggers + 1):
            probability = (
                comb(lucky_triggers, successes)
                * (p ** successes)
                * ((1.0 - p) ** (lucky_triggers - successes))
            )
            total = int(
                base.chips
                * (base.mult + self.LUCKY_MULT_BONUS * successes)
                * base.x_mult
            )
            probabilities[total] = probabilities.get(total, 0.0) + probability

        distribution = ScoreOutcomeDistribution(
            outcomes=tuple(
                ScoreOutcome(score, probability)
                for score, probability in sorted(probabilities.items())
            ),
            random_sources=(f"Lucky mult x{lucky_triggers}",),
        )
        return ScoreProjectionTransition(
            distribution=distribution,
            state_after_scoring=joker_projection.state_after_scoring,
            unsupported_jokers=joker_projection.unsupported_jokers,
        )

    def _lucky_scoring_triggers(self, hand: PokerHand, cards) -> int:
        triggers = 0
        for card in self.scorer.scoring_cards(hand, cards):
            if self.scorer.is_card_debuffed(card):
                continue
            if getattr(card, "enhancement", None) != "Lucky":
                continue
            triggers += 2 if getattr(card, "seal", None) == "Red" else 1
        return triggers
