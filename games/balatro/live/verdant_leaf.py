from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import SELL_JOKER, BalatroAction
from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.build import JokerBuildValueEvaluator
from games.balatro.joker import Joker
from games.balatro.joker_edition import joker_edition_universal_value


@dataclass(frozen=True)
class VerdantLeafSaleDecision:
    """One emergency sale that removes Verdant Leaf's playing-card debuff."""

    joker_index: int
    joker: str
    retention_cost: float
    rationale: tuple[str, ...]

    def to_action(self) -> BalatroAction:
        return BalatroAction(
            SELL_JOKER,
            target={
                "area_index": self.joker_index,
                "label": self.joker,
            },
        )


class VerdantLeafSalePolicy:
    """Sell the least valuable legal Joker while Verdant Leaf is active.

    Verdant Leaf disables every playing card until one Joker is sold. This policy
    is intentionally boss-scoped: it cannot recommend an in-round sale for any
    other blind, after the debuff has lifted, or while Chicot disables the boss.
    """

    def __init__(self, *, evaluator: JokerBuildValueEvaluator | None = None) -> None:
        self.evaluator = evaluator or JokerBuildValueEvaluator()

    def recommend(self, state) -> VerdantLeafSaleDecision | None:
        if str(getattr(state, "phase", "")) != "SELECTING_HAND":
            return None
        if str(getattr(state, "boss_name", "")) != "Verdant Leaf":
            return None
        if boss_blind_disabled_by_owned_jokers(state):
            return None
        if not any(
            bool(getattr(card, "debuffed", False))
            for card in getattr(state, "hand", ())
        ):
            return None

        candidates: list[VerdantLeafSaleDecision] = []
        for index, joker in enumerate(getattr(state, "jokers", ())):
            if not isinstance(joker, Joker) or not self._sellable(joker):
                continue

            baseline = state.copy()
            removed = baseline.jokers.pop(index)
            value = self.evaluator.evaluate(baseline, removed)
            retention_cost = (
                float(value.total_gain)
                + float(joker_edition_universal_value(joker))
            )
            candidates.append(
                VerdantLeafSaleDecision(
                    joker_index=int(getattr(joker, "area_index", index)),
                    joker=str(
                        getattr(joker, "label", None) or type(joker).__name__
                    ),
                    retention_cost=retention_cost,
                    rationale=(
                        "Verdant Leaf is actively debuffing playing cards",
                        "sell exactly one Joker to lift the blind-wide card debuff",
                        f"strategy-aware retention cost={retention_cost:.3f}",
                    ),
                )
            )

        if not candidates:
            return None
        return min(
            candidates,
            key=lambda candidate: (candidate.retention_cost, candidate.joker_index),
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
