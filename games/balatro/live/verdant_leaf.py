from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from games.balatro.actions import SELL_JOKER, BalatroAction
from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.build import JokerBuildValueEvaluator
from games.balatro.joker import Joker
from games.balatro.joker_edition import joker_edition_universal_value
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner


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
    """Sell a Joker only when disabling Verdant Leaf improves clear probability.

    Verdant Leaf debuffs every playing card until one Joker is sold. The production
    runner invokes this after D1, so an unconditional sale can destroy a viable
    Joker-only clear that D1 already found. This policy therefore compares the same
    public-information blind planner before and after each legal sale. A sale is
    allowed only when lifting the Verdant debuff strictly improves modeled clear
    probability, then the least costly sale among equally good survival outcomes is
    chosen.
    """

    EPSILON = 1e-12

    def __init__(
        self,
        *,
        evaluator: JokerBuildValueEvaluator | None = None,
        planner: LiveBlindClearPlanner | None = None,
    ) -> None:
        self.evaluator = evaluator or JokerBuildValueEvaluator()
        self.planner = planner or LiveBlindClearPlanner()

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

        baseline_clear = self._clear_probability(state)
        if baseline_clear is None:
            # This is a late override of the authoritative D1 action. If we cannot
            # establish that selling helps, fail closed and preserve D1.
            return None

        candidates: list[tuple[float, VerdantLeafSaleDecision]] = []
        for index, joker in enumerate(getattr(state, "jokers", ())):
            if not isinstance(joker, Joker) or not self._sellable(joker):
                continue

            projected = self._state_after_sale(state, index)
            projected_clear = self._clear_probability(projected)
            if projected_clear is None:
                continue
            clear_gain = float(projected_clear) - float(baseline_clear)
            if clear_gain <= self.EPSILON:
                continue

            baseline = state.copy()
            removed = baseline.jokers.pop(index)
            value = self.evaluator.evaluate(baseline, removed)
            retention_cost = (
                float(value.total_gain)
                + float(joker_edition_universal_value(joker))
            )
            candidates.append(
                (
                    float(projected_clear),
                    VerdantLeafSaleDecision(
                        joker_index=int(getattr(joker, "area_index", index)),
                        joker=str(
                            getattr(joker, "label", None) or type(joker).__name__
                        ),
                        retention_cost=retention_cost,
                        rationale=(
                            "Verdant Leaf is actively debuffing playing cards",
                            "selling exactly one Joker lifts the blind-wide card debuff",
                            f"public D1 clear probability improves {float(baseline_clear):.6f}->{float(projected_clear):.6f}",
                            f"clear-probability gain={clear_gain:.6f}",
                            f"strategy-aware retention cost={retention_cost:.3f}",
                            "late boss override is permitted only because the sale improves modeled survival",
                        ),
                    ),
                )
            )

        if not candidates:
            return None
        _, decision = max(
            candidates,
            key=lambda item: (
                item[0],
                -item[1].retention_cost,
                -item[1].joker_index,
            ),
        )
        return decision

    def _clear_probability(self, state) -> float | None:
        try:
            plan = self.planner.plan(state)
        except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
            return None
        return max(0.0, min(1.0, float(plan.value.clear_probability)))

    @staticmethod
    def _state_after_sale(state, index: int):
        projected = deepcopy(state)
        if index < 0 or index >= len(projected.jokers):
            return projected
        projected.jokers.pop(index)

        # Selling any Joker disables Verdant Leaf for the rest of the blind. Live
        # observation marks the affected playing cards debuffed; clear that exact
        # boss effect in the hypothetical post-sale branch so D1 scores the branch
        # that the game will actually produce. Red/White has no persistent card
        # debuff source competing with the active boss here.
        for area_name in ("hand", "deck", "discard_pile"):
            for card in tuple(getattr(projected, area_name, ()) or ()):
                if hasattr(card, "debuffed"):
                    card.debuffed = False
        owned = getattr(projected, "owned_deck", None)
        if owned is not None:
            for card in tuple(owned):
                if hasattr(card, "debuffed"):
                    card.debuffed = False
        return projected

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
