from __future__ import annotations

from dataclasses import dataclass
from math import comb

from games.balatro.hand import PokerHand
from games.balatro.scoring import BalatroScorer


@dataclass(frozen=True)
class ScoreOutcome:
    score: int
    probability: float


@dataclass(frozen=True)
class ScoreOutcomeDistribution:
    """Discrete scoring outcomes for one visible play.

    The current implementation models deterministic visible card effects and the
    scoring branch of Lucky cards. Joker randomness is intentionally outside this
    layer until side-effect-free Joker projection is available.
    """

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


class VisibleCardScoreOutcomeModel:
    """Project public visible-card scoring without consuming game RNG.

    This layer deliberately strips Jokers from hypothetical scoring. It therefore
    matches the current live hand evaluator's scope while giving the planner a
    deterministic floor and a discrete Lucky-card distribution instead of a
    sampled guess.
    """

    LUCKY_MULT_PROBABILITY = 0.2
    LUCKY_MULT_BONUS = 20

    def __init__(self, scorer: BalatroScorer | None = None):
        self.scorer = scorer or BalatroScorer()

    def project(
        self,
        hand: PokerHand,
        state,
        cards,
        *,
        include_card_chips: bool = True,
    ) -> ScoreOutcomeDistribution:
        safe_state = state.copy() if state is not None else None
        if safe_state is not None:
            safe_state.jokers = []

        base = self.scorer.score(
            hand,
            safe_state,
            cards=cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=False,
        )

        lucky_triggers = self._lucky_scoring_triggers(hand, cards)
        if lucky_triggers == 0:
            return ScoreOutcomeDistribution(
                outcomes=(ScoreOutcome(base.total, 1.0),),
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

        outcomes = tuple(
            ScoreOutcome(score, probability)
            for score, probability in sorted(probabilities.items())
        )
        return ScoreOutcomeDistribution(
            outcomes=outcomes,
            random_sources=(f"Lucky mult x{lucky_triggers}",),
        )

    def _lucky_scoring_triggers(self, hand: PokerHand, cards) -> int:
        triggers = 0
        for card in self.scorer.scoring_cards(hand, cards):
            if getattr(card, "enhancement", None) != "Lucky":
                continue
            triggers += 2 if getattr(card, "seal", None) == "Red" else 1
        return triggers
