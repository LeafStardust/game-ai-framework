from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import SELL_JOKER, BalatroAction
from games.balatro.build import JokerBuildValueEvaluator
from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator
from games.balatro.joker import Joker
from games.balatro.joker_edition import joker_edition_universal_value


@dataclass(frozen=True)
class RiffRaffCycleDecision:
    joker_index: int
    joker: str
    retention_cost: float
    free_slots_before: int
    rationale: tuple[str, ...]

    def to_action(self) -> BalatroAction:
        return BalatroAction(
            SELL_JOKER,
            target={
                "area_index": self.joker_index,
                "label": self.joker,
            },
        )


class RiffRaffCyclePolicy:
    """Pre-blind Joker cleanup plus Riff-Raff slot cycling.

    Temporary scoring Jokers may be cashed out once their native effect is on its
    final legs, but never by knowingly reducing modeled next-blind survival.

    When Riff-Raff is owned, the same survival condition applies to opening up to
    two Joker slots before selecting a blind. At most one Joker is sold per
    autonomous checkpoint; the normal re-observe/replan loop prevents stale indices
    and duplicate transactions.
    """

    TARGET_FREE_SLOTS = 2
    MAX_RETENTION_COST = 1.0
    POPCORN_LAST_LEGS_MULT = 4
    ICE_CREAM_LAST_LEGS_CHIPS = 20
    EPSILON = 1e-12

    def __init__(
        self,
        *,
        evaluator: JokerBuildValueEvaluator | None = None,
        build_health: RuntimeBuildHealthEvaluator | None = None,
    ) -> None:
        self.evaluator = evaluator or JokerBuildValueEvaluator()
        self.build_health = build_health or RuntimeBuildHealthEvaluator()

    def recommend(self, state, *, will_select_blind: bool) -> RiffRaffCycleDecision | None:
        if str(getattr(state, "phase", "")) != "BLIND_SELECT":
            return None
        if not will_select_blind:
            return None

        jokers = list(getattr(state, "jokers", ()) or ())
        slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
        free_slots = max(0, slots - len(jokers))
        current_survival = float(self.build_health.evaluate(state).survival)

        # Temporary Jokers should be cashed out only when their remaining scoring
        # contribution is no longer needed for modeled next-blind survival. This
        # remains independent of Riff-Raff ownership.
        exhausted = []
        for index, joker in enumerate(jokers):
            if not isinstance(joker, Joker) or not self._sellable(joker):
                continue
            tokens = self._tokens(joker)
            label = str(
                getattr(joker, "label", None)
                or getattr(joker, "name", None)
                or type(joker).__name__
            )
            area_index = int(getattr(joker, "area_index", index))

            if self._is_popcorn(tokens):
                mult = int(getattr(joker, "mult", 0) or 0)
                if mult <= self.POPCORN_LAST_LEGS_MULT:
                    projected_survival = self._survival_after_sale(state, index)
                    if projected_survival + self.EPSILON < current_survival:
                        continue
                    exhausted.append(
                        RiffRaffCycleDecision(
                            joker_index=area_index,
                            joker=label,
                            retention_cost=float(mult),
                            free_slots_before=free_slots,
                            rationale=(
                                "Popcorn is on its final legs before the next blind",
                                f"current Popcorn Mult=+{mult}; sell threshold=+{self.POPCORN_LAST_LEGS_MULT}",
                                f"Build Health survival remains {current_survival:.1f}->{projected_survival:.1f}",
                                "bank remaining sell value only because removing Popcorn does not reduce modeled clear viability",
                            ),
                        )
                    )
                    continue

            if self._is_ice_cream(tokens):
                chips = int(getattr(joker, "chips", 0) or 0)
                if chips <= self.ICE_CREAM_LAST_LEGS_CHIPS:
                    projected_survival = self._survival_after_sale(state, index)
                    if projected_survival + self.EPSILON < current_survival:
                        continue
                    exhausted.append(
                        RiffRaffCycleDecision(
                            joker_index=area_index,
                            joker=label,
                            retention_cost=float(chips) / 20.0,
                            free_slots_before=free_slots,
                            rationale=(
                                "Ice Cream is on its final legs before the next blind",
                                f"current Ice Cream Chips=+{chips}; sell threshold=+{self.ICE_CREAM_LAST_LEGS_CHIPS}",
                                f"Build Health survival remains {current_survival:.1f}->{projected_survival:.1f}",
                                "bank remaining sell value only because removing Ice Cream does not reduce modeled clear viability",
                            ),
                        )
                    )

        if exhausted:
            return min(
                exhausted,
                key=lambda candidate: (candidate.retention_cost, candidate.joker_index),
            )

        if not any(self._is_riff_raff(joker) for joker in jokers):
            return None

        if free_slots >= self.TARGET_FREE_SLOTS:
            return None

        candidates: list[RiffRaffCycleDecision] = []
        for index, joker in enumerate(jokers):
            if not isinstance(joker, Joker):
                continue
            if self._is_riff_raff(joker) or not self._sellable(joker):
                continue

            projected_survival = self._survival_after_sale(state, index)
            if projected_survival + self.EPSILON < current_survival:
                continue

            baseline = state.copy()
            removed = baseline.jokers.pop(index)
            value = self.evaluator.evaluate(baseline, removed)
            retention_cost = (
                max(0.0, float(value.total_gain))
                + float(joker_edition_universal_value(joker))
            )
            if retention_cost > self.MAX_RETENTION_COST:
                continue

            label = str(
                getattr(joker, "label", None)
                or getattr(joker, "name", None)
                or type(joker).__name__
            )
            candidates.append(
                RiffRaffCycleDecision(
                    joker_index=int(getattr(joker, "area_index", index)),
                    joker=label,
                    retention_cost=retention_cost,
                    free_slots_before=free_slots,
                    rationale=(
                        "Riff-Raff is owned and the agent is about to select a blind",
                        f"free Joker slots={free_slots}; target={self.TARGET_FREE_SLOTS}",
                        "sell one low-retention non-Riff-Raff Joker, then re-observe before any second sale",
                        f"strategy-aware retention cost={retention_cost:.3f}",
                        f"Build Health survival remains {current_survival:.1f}->{projected_survival:.1f}",
                        "Riff-Raff slot cycling cannot trade away modeled next-blind clear viability",
                        "sale also banks the Joker sell value while opening Riff-Raff generation capacity",
                    ),
                )
            )

        if not candidates:
            return None
        return min(
            candidates,
            key=lambda candidate: (candidate.retention_cost, candidate.joker_index),
        )

    def _survival_after_sale(self, state, index: int) -> float:
        projected = state.copy()
        projected.jokers.pop(index)
        return float(self.build_health.evaluate(projected).survival)

    @staticmethod
    def _tokens(joker) -> set[str]:
        values = {
            type(joker).__name__,
            str(getattr(joker, "name", "") or ""),
            str(getattr(joker, "label", "") or ""),
            str(getattr(joker, "center", "") or ""),
        }
        return {
            "".join(ch.lower() for ch in value if ch.isalnum())
            for value in values
            if value
        }

    @classmethod
    def _is_riff_raff(cls, joker) -> bool:
        return any(
            token in {"riffraff", "riffraffjoker", "jriffraff"}
            for token in cls._tokens(joker)
        )

    @staticmethod
    def _is_popcorn(tokens: set[str]) -> bool:
        return any(token in {"popcorn", "popcornjoker", "jpopcorn"} for token in tokens)

    @staticmethod
    def _is_ice_cream(tokens: set[str]) -> bool:
        return any(
            token in {"icecream", "icecreamjoker", "jicecream"}
            for token in tokens
        )

    @staticmethod
    def _sellable(joker: Joker) -> bool:
        if bool(getattr(joker, "eternal", False)):
            return False
        if bool(getattr(joker, "unsellable", False)):
            return False
        if getattr(joker, "sellable", None) is False:
            return False
        if getattr(joker, "can_sell", None) is False:
            return False
        return True
