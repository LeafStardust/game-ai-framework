from __future__ import annotations

from dataclasses import dataclass

from games.balatro.build.profile import (
    BalatroBuildProfiler,
    BalatroPlaystyleIntentTracker,
    PlaystyleIntent,
)
from games.balatro.joker import Playstyle


_SUIT_AXES = {
    Playstyle.SPADES.value: "Spades",
    Playstyle.HEARTS.value: "Hearts",
    Playstyle.CLUBS.value: "Clubs",
    Playstyle.DIAMONDS.value: "Diamonds",
}
_FACE_RANKS = {"J", "Q", "K", "Jack", "Queen", "King"}


@dataclass(frozen=True)
class PackPlaystyleWeights:
    """Bounded D4 influence for directly interpretable booster choices."""

    gain: float = 3.0
    locked_conflict_multiplier: float = 1.5

    def __post_init__(self) -> None:
        if float(self.gain) < 0.0:
            raise ValueError("gain cannot be negative")
        if float(self.locked_conflict_multiplier) < 1.0:
            raise ValueError("locked_conflict_multiplier must be at least 1")


@dataclass(frozen=True)
class PackPlaystyleEvaluation:
    fit: float
    value: float
    intent: PlaystyleIntent
    ante: int
    rationale: tuple[str, ...]


class PackPlaystyleEvaluator:
    """Score only direct booster-choice alignment with the run's build intent.

    This layer deliberately does not infer Tarot/Spectral strategy from names or
    hidden outcomes. Planet cards expose their target poker hand directly, and a
    playing card exposes rank/suit directly, so those signals are safe to consume.
    Joker choices return zero here because ``JokerBuildValueEvaluator`` already
    applies the same run intent; adding a second pack-level Joker bonus would double
    count it.
    """

    def __init__(
        self,
        *,
        profiler: BalatroBuildProfiler | None = None,
        intent_tracker: BalatroPlaystyleIntentTracker | None = None,
        weights: PackPlaystyleWeights | None = None,
    ) -> None:
        self.profiler = profiler or BalatroBuildProfiler()
        self.intent_tracker = intent_tracker or BalatroPlaystyleIntentTracker()
        self.weights = weights or PackPlaystyleWeights()

    @staticmethod
    def _exploratory_influence(ante: int) -> float:
        if ante <= 1:
            return 0.25
        if ante == 2:
            return 0.50
        if ante == 3:
            return 0.75
        return 1.0

    def evaluate(
        self,
        state,
        *,
        kind: str,
        target=None,
        rank=None,
        suit=None,
    ) -> PackPlaystyleEvaluation:
        profile = self.profiler.profile(state)
        intent = self.intent_tracker.resolve(profile)
        ante = int(profile.ante)
        kind = str(kind).upper()

        if kind == "PLANET":
            hand_type = str(getattr(target, "hand_type", ""))
            signals = {hand_type: 1.0} if hand_type else {}
            source = f"Planet hand={hand_type or 'UNKNOWN'}"
        elif kind == "PLAYING_CARD":
            signals = self._playing_card_signals(rank=rank, suit=suit)
            source = f"playing card rank={rank} suit={suit}"
        elif kind == "JOKER":
            return self._neutral(
                intent,
                ante,
                "D4 direct playstyle=0.000; Joker intent is already included by D2",
            )
        else:
            return self._neutral(
                intent,
                ante,
                f"D4 direct playstyle=0.000; {kind} has no explicit direct intent signal",
            )

        fit, details = self._fit(intent, signals)
        influence = 1.0 if intent.locked else self._exploratory_influence(ante)
        value = fit * float(self.weights.gain) * influence
        if intent.locked and value < 0.0:
            value *= float(self.weights.locked_conflict_multiplier)

        mode = "LOCKED" if intent.locked else "PIVOTABLE"
        rationale = (
            f"D4 playstyle fit={fit:.3f} value={value:.3f} mode={mode}",
            f"D4 direct signal={source}",
            *details,
        )
        return PackPlaystyleEvaluation(
            fit=fit,
            value=value,
            intent=intent,
            ante=ante,
            rationale=rationale,
        )

    @staticmethod
    def _playing_card_signals(*, rank, suit) -> dict[str, float]:
        rank_text = str(rank or "")
        suit_text = str(suit or "")
        face = rank_text in _FACE_RANKS
        signals = {
            Playstyle.FACE_CARDS.value: 1.0 if face else 0.0,
            Playstyle.NO_FACE_CARDS.value: 0.0 if face else 1.0,
        }
        for axis, expected_suit in _SUIT_AXES.items():
            signals[axis] = 1.0 if suit_text == expected_suit else 0.0
        return signals

    @staticmethod
    def _fit(
        intent: PlaystyleIntent,
        signals: dict[str, float],
    ) -> tuple[float, tuple[str, ...]]:
        total = 0.0
        denominator = 0.0
        details: list[str] = []
        for key, raw_strength in intent.strengths:
            signal = float(signals.get(str(key), 0.0))
            if signal == 0.0:
                continue
            strength = max(-1.0, min(1.0, float(raw_strength)))
            contribution = strength * signal
            total += contribution
            denominator += abs(strength)
            details.append(
                f"D4 axis {key}: strength={strength:+.3f} "
                f"signal={signal:+.3f} contribution={contribution:+.3f}"
            )
        return (total / denominator if denominator > 0.0 else 0.0), tuple(details)

    @staticmethod
    def _neutral(
        intent: PlaystyleIntent,
        ante: int,
        detail: str,
    ) -> PackPlaystyleEvaluation:
        return PackPlaystyleEvaluation(
            fit=0.0,
            value=0.0,
            intent=intent,
            ante=ante,
            rationale=(detail,),
        )
