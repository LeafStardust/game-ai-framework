from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class BalatroPlaybookNotFound(LookupError):
    pass


@dataclass(frozen=True)
class BalatroPlaybook:
    """Strategy cartridge selected from the live run's deck and stake.

    The playbook contains strategic preferences only. Poker rules, card/Joker
    mechanics, blind mechanics and stake/deck factual effects remain in the shared
    Balatro engine and must not be duplicated here.
    """

    deck: str
    stake: str
    name: str
    version: str = "0"
    strategy: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> tuple[str, str]:
        return self.deck.upper(), self.stake.upper()


class BalatroPlaybookRegistry:
    def __init__(self):
        self._playbooks: dict[tuple[str, str], BalatroPlaybook] = {}

    def register(self, playbook: BalatroPlaybook) -> None:
        key = playbook.key
        if key in self._playbooks:
            raise ValueError(
                f"Balatro playbook already registered for {key[0]} / {key[1]}"
            )
        self._playbooks[key] = playbook

    def get(self, deck: str, stake: str) -> BalatroPlaybook:
        key = str(deck).upper(), str(stake).upper()
        try:
            return self._playbooks[key]
        except KeyError as error:
            raise BalatroPlaybookNotFound(
                f"no Balatro playbook registered for {key[0]} / {key[1]}"
            ) from error

    def for_state(self, state) -> BalatroPlaybook:
        return self.get(
            getattr(state, "deck_name", ""),
            getattr(state, "stake_name", ""),
        )

    def keys(self) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(self._playbooks))


def default_balatro_playbooks() -> BalatroPlaybookRegistry:
    registry = BalatroPlaybookRegistry()
    registry.register(
        BalatroPlaybook(
            deck="RED",
            stake="WHITE",
            name="red-white",
            version="0.3",
            strategy={
                "risk_tolerance": "moderate",
                "planner": {
                    "min_clear_probability": 0.75,
                    "allow_consensus_discard": True,
                    "allow_pace_fallback": True,
                    "min_pace_ratio": 1.0,
                    "max_horizon": 8,
                    "max_search_nodes": 10000,
                },
                "decision_thresholds": {
                    "hand_action": {
                        "play_clear_probability_floor": 0.75,
                        "discard_clear_probability_advantage": 0.05,
                        "discard_progress_advantage": 0.08,
                        "low_discard_reserve": 1,
                        "low_discard_extra_clear_advantage": 0.05,
                        "low_discard_extra_progress_advantage": 0.04,
                        "low_hand_reserve": 1,
                        "low_hand_clear_advantage_discount": 0.03,
                        "low_hand_progress_advantage_discount": 0.03,
                    },
                },
            },
        )
    )
    return registry
