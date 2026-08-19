from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import SELL_JOKER, BalatroAction
from games.balatro.build import JokerBuildValueEvaluator
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
    """Open up to two Joker slots before selecting a blind for Riff-Raff.

    Riff-Raff creates up to two Common Jokers when a blind is selected. The policy
    sells at most one low-retention Joker per autonomous checkpoint, then relies on
    the normal re-observe/replan loop. Once two slots are open, it stops naturally;
    this prevents duplicate sells while still allowing two sequential sales before
    the blind is selected.
    """

    TARGET_FREE_SLOTS = 2
    MAX_RETENTION_COST = 1.0

    def __init__(self, *, evaluator: JokerBuildValueEvaluator | None = None) -> None:
        self.evaluator = evaluator or JokerBuildValueEvaluator()

    def recommend(self, state, *, will_select_blind: bool) -> RiffRaffCycleDecision | None:
        if str(getattr(state, "phase", "")) != "BLIND_SELECT":
            return None
        if not will_select_blind:
            return None

        jokers = list(getattr(state, "jokers", ()) or ())
        if not any(self._is_riff_raff(joker) for joker in jokers):
            return None

        slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
        free_slots = max(0, slots - len(jokers))
        if free_slots >= self.TARGET_FREE_SLOTS:
            return None

        candidates: list[RiffRaffCycleDecision] = []
        for index, joker in enumerate(jokers):
            if not isinstance(joker, Joker):
                continue
            if self._is_riff_raff(joker) or not self._sellable(joker):
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

            label = str(getattr(joker, "label", None) or getattr(joker, "name", None) or type(joker).__name__)
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
        return any(token in {"riffraff", "riffraffjoker", "jriffraff"} for token in cls._tokens(joker))

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
