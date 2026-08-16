from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


DECISION_LAYER_THRESHOLD_KEYS = {
    "D1": "hand_action",
    "D2": "joker_acquisition",
    "D3": "voucher_acquisition",
    "D4": "consumable_acquisition",
    "D5": "consumable_use",
    "D6": "consumable_target",
    "D7": "planet",
    "D8": "booster_acquisition",
    "D9": "pack_choice",
    "D10": "pack_target",
    "D11": "reroll",
    "D12": "shop_arbiter",
    "D13": "blind_skip",
    "D14": "resource_valuation",
}


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

    def thresholds_for(self, layer: str) -> dict[str, Any]:
        """Return an isolated threshold block for one stable decision-layer ID."""
        layer_id = str(layer).upper()
        try:
            threshold_key = DECISION_LAYER_THRESHOLD_KEYS[layer_id]
        except KeyError as error:
            allowed = ", ".join(DECISION_LAYER_THRESHOLD_KEYS)
            raise ValueError(
                f"unknown Balatro decision layer {layer!r}; expected one of {allowed}"
            ) from error

        configured = self.strategy.get("decision_thresholds", {})
        if not isinstance(configured, dict):
            raise TypeError("playbook decision_thresholds must be a mapping")

        block = configured.get(threshold_key, {})
        if not isinstance(block, dict):
            raise TypeError(
                f"playbook threshold block {threshold_key!r} for {layer_id} must be a mapping"
            )
        return dict(block)


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
            version="0.8",
            strategy={
                "risk_tolerance": "moderate",
                "planner": {
                    "max_horizon": 5,
                    "max_search_nodes": 5000,
                    "search_schedule_mode": "probe-deepest",
                },
                "decision_thresholds": {
                    "hand_action": {
                        "clear_path_probability_floor": 0.75,
                        "safe_clear_probability_tolerance": 0.01,
                        "pace_ratio_floor": 1.0,
                        "setup_discard_consensus_agreement": 3,
                        "low_discard_reserve": 1,
                        "low_discard_fallback_penalty": 10.0,
                        "low_hand_reserve": 1,
                        "low_hand_discard_fallback_bonus": 10.0,
                    },
                    "joker_acquisition": {
                        "minimum_purchase_build_gain": 0.0,
                        "minimum_purchase_advantage": 0.35,
                        "minimum_replacement_build_delta": 0.0,
                        "minimum_replacement_advantage": 0.75,
                        "price_weight": 0.35,
                        "interest_weight": 1.25,
                        "reserve_target": 5,
                        "reserve_weight": 0.45,
                        "last_joker_slot_penalty": 1.5,
                        "penultimate_joker_slot_penalty": 0.5,
                    },
                    "voucher_acquisition": {
                        "minimum_persistent_value": 1.0,
                        "minimum_purchase_advantage": 0.35,
                        "price_weight": 0.20,
                        "interest_weight": 1.0,
                        "reserve_target": 5,
                        "reserve_weight": 0.45,
                        "minimum_money_after": 5,
                        "target_ante": 8,
                        "remaining_ante_weight": 0.20,
                        "maximum_horizon_bonus": 1.40,
                    },
                    "consumable_acquisition": {
                        "minimum_purchase_build_gain": 0.0,
                        "minimum_purchase_advantage": 0.35,
                        "minimum_buy_and_use_advantage": 0.35,
                        "price_weight": 0.35,
                        "interest_weight": 1.25,
                        "reserve_target": 5,
                        "reserve_weight": 0.45,
                        "last_consumable_slot_penalty": 0.6,
                        "immediate_money_weight": 0.20,
                    },
                    "consumable_use": {
                        "minimum_clear_probability_gain": 0.0,
                        "minimum_pace_score_gain": 0.0,
                        "minimum_full_slot_contextual_delta": 0.0,
                        "minimum_final_hand_score_gain": 0.0,
                        "minimum_immediate_gain": 0.0,
                    },
                    "consumable_target": {
                        "minimum_total_gain": None,
                        "minimum_contextual_delta": None,
                    },
                },
            },
        )
    )
    return registry