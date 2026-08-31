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
    """Deck/stake policy cartridge for the live Balatro agent.

    Canonical strategic direction comes from Bond development and composition.
    The playbook contains environment policy and stable decision-layer thresholds;
    it does not define categorical strategy tiers, strategy trees, or commitment
    shortlists.
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
            version="1.0",
            strategy={
                "risk_tolerance": "moderate",
                "planner": {
                    "max_horizon": 5,
                    "max_search_nodes": 5000,
                    "max_search_seconds": 8.0,
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
                        "minimum_replacement_advantage": 0.50,
                        "aligned_minimum_replacement_advantage": 0.25,
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
                        "minimum_money_after": 0,
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
                    "booster_acquisition": {
                        "minimum_buy_advantage": 0.35,
                        "minimum_pack_hit_probability": 0.45,
                        "price_weight": 0.35,
                        "interest_weight": 1.25,
                        "reserve_target": 5,
                        "reserve_weight": 0.45,
                        "celestial_per_offer_hit_probability": 0.40,
                        "buffoon_per_offer_hit_probability": 0.42,
                        "standard_per_offer_hit_probability": 0.32,
                        "arcana_per_offer_hit_probability": 0.30,
                        "spectral_per_offer_hit_probability": 0.22,
                        "celestial_hit_value": 4.5,
                        "buffoon_hit_value": 5.0,
                        "standard_hit_value": 4.0,
                        "arcana_hit_value": 4.2,
                        "spectral_hit_value": 5.0,
                        "need_hit_probability_bonus": 0.25,
                        "need_value_weight": 2.0,
                        "runway_value_weight": 0.75,
                        "second_selection_value_fraction": 0.55,
                    },
                    "pack_choice": {
                        "skip_bias": 0.0,
                    },
                    "pack_target": {
                        "minimum_total_gain": None,
                        "minimum_contextual_delta": 0.0,
                    },
                    "reroll": {
                        "minimum_margin": 0.25,
                        "full_joker_replacement_penalty": 1.5,
                        "maximum_paid_reroll_cost": 8,
                        "minimum_money_after_paid_reroll": 10,
                        "late_ante_start": 6,
                        "late_ante_minimum_money_after_paid_reroll": 20,
                    },
                    "blind_skip": {
                        "minimum_skip_advantage": 2.0,
                        "fallback_tag_value": 4.0,
                        "base_shop_opportunity_value": 1.5,
                        "build_development_shop_weight": 2.0,
                        "free_joker_slot_shop_weight": 0.4,
                        "cash_recovery_shop_weight": 0.25,
                        "late_ante_shop_weight": 0.2,
                        "pre_boss_shop_weight": 2.5,
                        "interest_cap": 5,
                        "tag_build_fit_weight": 2.0,
                        "max_tag_build_adjustment": 2.5,
                    },
                    "resource_valuation": {
                        "price_weight": 0.35,
                        "interest_weight": 1.25,
                        "reserve_target": 5,
                        "reserve_weight": 0.45,
                        "last_joker_slot_penalty": 1.5,
                        "penultimate_joker_slot_penalty": 0.5,
                        "last_consumable_slot_penalty": 0.6,
                    },
                },
            },
        )
    )
    return registry