from collections import Counter
from dataclasses import dataclass, field

from framework.logging.logger import get_logger
from games.balatro.actions import BalatroAction
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.state import BalatroState


@dataclass
class BalatroRunStats:
    decisions: int = 0
    recoveries: int = 0
    errors: int = 0
    max_ante: int = 1
    max_round: int = 1
    max_money: int = 0
    actions: Counter = field(default_factory=Counter)


class BalatroConsoleTelemetry:
    """Compact console trace and aggregate statistics for live runs."""

    def __init__(self, logger=None):
        self.logger = logger or get_logger("balatro.live")
        self.stats = BalatroRunStats()

    def run_started(
        self,
        snapshot: LiveBalatroSnapshot,
        state: BalatroState,
    ) -> None:
        self._update_stats(state)
        seed = snapshot.payload.get("seed") or "random"
        self._info(
            "RUN START | deck=%s stake=%s seed=%s",
            state.deck_name,
            state.stake_name,
            seed,
        )
        self.state_observed(snapshot, state)

    def state_observed(
        self,
        snapshot: LiveBalatroSnapshot,
        state: BalatroState,
    ) -> None:
        self._update_stats(state)
        requirement = state.blind_requirement
        progress = self._progress(state.blind_score, requirement)
        self._info(
            "STATE | seq=%s phase=%s ante=%s round=%s "
            "score=%s/%s (%s) money=$%s hands=%s discards=%s",
            snapshot.sequence,
            snapshot.phase,
            state.ante,
            state.round,
            state.blind_score,
            requirement,
            progress,
            state.money,
            state.hands_remaining,
            state.discards_remaining,
        )

    def decision(
        self,
        action: BalatroAction,
        state: BalatroState,
    ) -> None:
        self.stats.decisions += 1
        self.stats.actions[action.name] += 1
        self._update_stats(state)

        details = self._action_details(action)
        suffix = f" | {details}" if details else ""

        self._info(
            "DECISION #%s | %s%s",
            self.stats.decisions,
            action.name,
            suffix,
        )

    def recovery(
        self,
        reason: str,
        snapshot: LiveBalatroSnapshot | None = None,
    ) -> None:
        self.stats.recoveries += 1
        phase = snapshot.phase if snapshot is not None else "unknown"
        self._warning(
            "RECOVERY #%s | phase=%s reason=%s",
            self.stats.recoveries,
            phase,
            reason,
        )

    def error(self, error: Exception) -> None:
        self.stats.errors += 1
        self._error(
            "ERROR #%s | %s: %s",
            self.stats.errors,
            type(error).__name__,
            error,
        )

    def run_finished(
        self,
        snapshot: LiveBalatroSnapshot,
        state: BalatroState,
        outcome: str | None = None,
    ) -> None:
        self._update_stats(state)

        if outcome is None:
            if snapshot.payload.get("won") is True:
                outcome = "WIN"
            elif snapshot.payload.get("won") is False:
                outcome = "LOSS"
            else:
                outcome = "UNKNOWN"

        actions = ", ".join(
            f"{name}={count}"
            for name, count in sorted(self.stats.actions.items())
        ) or "none"

        self._info(
            "RUN END | outcome=%s max_ante=%s max_round=%s "
            "decisions=%s recoveries=%s errors=%s max_money=$%s "
            "actions=[%s]",
            outcome,
            self.stats.max_ante,
            self.stats.max_round,
            self.stats.decisions,
            self.stats.recoveries,
            self.stats.errors,
            self.stats.max_money,
            actions,
        )

    def _update_stats(self, state: BalatroState) -> None:
        self.stats.max_ante = max(self.stats.max_ante, state.ante)
        self.stats.max_round = max(self.stats.max_round, state.round)
        self.stats.max_money = max(self.stats.max_money, state.money)

    @staticmethod
    def _progress(score: int, requirement: int) -> str:
        if requirement <= 0:
            return "n/a"
        return f"{min(100.0, 100.0 * score / requirement):.1f}%"

    @classmethod
    def _action_details(cls, action: BalatroAction) -> str:
        parts = []

        if action.cards:
            cards = ",".join(
                cls._card_label(card)
                for card in action.cards
            )
            parts.append(f"cards=[{cards}]")

        if action.target is not None:
            target = getattr(action.target, "name", None)
            if target is None and isinstance(action.target, dict):
                target = action.target.get("label") or action.target.get("id")
            if target is None:
                target = getattr(action.target, "live_id", action.target)
            parts.append(f"target={target}")

        return " ".join(parts)

    @staticmethod
    def _card_label(card) -> str:
        rank = getattr(card, "rank", "?")
        suit = getattr(card, "suit", "?")
        suit_code = {
            "Hearts": "H",
            "Diamonds": "D",
            "Clubs": "C",
            "Spades": "S",
        }.get(suit, str(suit)[:1])
        return f"{rank}{suit_code}"

    def _info(self, message: str, *args) -> None:
        self.logger.info(message, *args)

    def _warning(self, message: str, *args) -> None:
        self.logger.warning(message, *args)

    def _error(self, message: str, *args) -> None:
        self.logger.error(message, *args)
