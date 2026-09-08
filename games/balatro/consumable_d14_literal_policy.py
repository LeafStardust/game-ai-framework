from __future__ import annotations

"""Keep D14 consumable comparison on mechanical parent-scale value.

D4 owns HOLD/BUY/BUY_AND_USE admission and may use B4 structural build-path units to
reason about strategic relevance.  Those B4 units are not literal/run-winning SHOP
utility and must not compete directly with D2 Joker gain, D8 option EV, D3 vouchers,
or D11 rerolls.

This policy finishes the parent normalization:

* held Tarot/Spectral BUY remains delegated to ``held_consumable_option_policy``;
* Planet BUY is the better literal score option of holding the Planet versus using
  it, with the normal consumable-slot cost charged only while held;
* Planet BUY_AND_USE uses the literal permanent Planet-use score delta;
* non-Planet BUY_AND_USE (currently Hermit/Temperance in D4) keeps only D4's explicit
  immediate-money value and shared purchase cost.

Planet use is simulated mechanically: the hand level is incremented by the Planet
and active Jokers receive their ``PLANET_USED`` trigger, so Constellation progression
is represented without a synthetic scaler bonus.  Representative score comparison
uses the same D2 probe catalogue, observed-hand weighting, literal stochastic score
projector, direct-score weight and cap.
"""

from copy import deepcopy
from dataclasses import dataclass

from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.build.literal_score_expectation import literal_expected_score
from games.balatro.consumable import ConsumableContext, PlanetCard
from games.balatro.joker import JokerContext
from games.balatro.shop_utility_scale import ShopNormalizedUtility, ShopUtilityScale


@dataclass(frozen=True)
class PlanetD14Option:
    complete: bool
    held_value: float
    use_value: float
    rationale: tuple[str, ...] = ()


class PlanetD14OptionEvaluator:
    def __init__(self, *, build_value: JokerBuildValueEvaluator | None = None) -> None:
        self.build_value = build_value or JokerBuildValueEvaluator()

    def evaluate(self, state, candidate) -> PlanetD14Option:
        if not isinstance(candidate, PlanetCard):
            return PlanetD14Option(False, 0.0, 0.0, ("candidate is not a modeled Planet",))

        held = deepcopy(state)
        held.consumables.append(deepcopy(candidate))

        used = deepcopy(state)
        planet = deepcopy(candidate)
        try:
            if not planet.can_use(ConsumableContext(state=used)):
                return PlanetD14Option(False, 0.0, 0.0, ("Planet cannot be used in projected state",))
            planet.use(ConsumableContext(state=used))
            for joker in tuple(getattr(used, "jokers", ()) or ()):
                if bool(getattr(joker, "debuffed", False)):
                    continue
                joker.apply(JokerContext(state=used, trigger="PLANET_USED"))
        except (AttributeError, KeyError, RuntimeError, TypeError, ValueError, ZeroDivisionError) as exc:
            return PlanetD14Option(
                False,
                0.0,
                0.0,
                (f"Planet mechanical transition failed: {type(exc).__name__}: {exc}",),
            )

        held_value = self._relative_direct_value(state, held)
        use_value = self._relative_direct_value(state, used)
        if held_value is None or use_value is None:
            return PlanetD14Option(
                False,
                0.0,
                0.0,
                ("Planet literal representative-score projection failed closed",),
            )
        return PlanetD14Option(
            True,
            max(0.0, held_value),
            max(0.0, use_value),
            (
                f"Planet held literal D14 value={max(0.0, held_value):.3f}",
                f"Planet use literal D14 value={max(0.0, use_value):.3f}",
                "Planet use includes hand-level transition and active PLANET_USED Joker triggers",
                "D2 representative hand weighting/direct-score scale is reused",
            ),
        )

    def _relative_direct_value(self, before_state, after_state) -> float | None:
        observed = self.build_value._probe_weights(before_state)
        weighted_gain = 0.0
        total_weight = 0.0

        for hand, template_cards in self.build_value._scoring_probes(before_state):
            cards = deepcopy(list(template_cards))
            before = deepcopy(before_state)
            after = deepcopy(after_state)
            before.hand = deepcopy(cards)
            after.hand = deepcopy(cards)
            try:
                before_score = literal_expected_score(
                    before,
                    hand,
                    cards,
                    scorer=self.build_value.scorer,
                )
                after_score = literal_expected_score(
                    after,
                    hand,
                    cards,
                    scorer=self.build_value.scorer,
                )
            except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
                return None

            gain = (
                float(after_score) - float(before_score)
            ) / max(abs(float(before_score)), 1.0)
            if observed is None:
                weight = 1.0
            else:
                weight = (
                    self.build_value._OBSERVED_HAND_PRIOR_WEIGHT
                    + observed.get(self.build_value._hand_key(hand.value), 0.0)
                )
            weighted_gain += gain * weight
            total_weight += weight

        if total_weight <= 0.0:
            return 0.0
        relative = weighted_gain / total_weight
        return max(
            -self.build_value.weights.direct_scoring_cap,
            min(
                self.build_value.weights.direct_scoring_cap,
                relative * self.build_value.weights.direct_scoring_gain,
            ),
        )


def install_consumable_d14_literal_policy() -> None:
    if getattr(ShopUtilityScale, "_consumable_literal_parent_installed", False):
        return

    original_init = ShopUtilityScale.__init__
    original_consumable_gain = ShopUtilityScale.consumable_gain

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.planet_d14_option_evaluator = PlanetD14OptionEvaluator()

    def consumable_gain(self, state, executable):
        selected = executable.decision.selected
        candidate = getattr(executable, "candidate", None)
        if selected is None:
            return original_consumable_gain(self, state, executable)

        category = str(getattr(candidate, "category", "") or "").upper()
        if category == "PLANET":
            expectation = self.planet_d14_option_evaluator.evaluate(state, candidate)
            money_cost = self._money_spend_cost(state, int(selected.economics.price))
            slot_cost = 0.0
            if selected.mode == "BUY":
                slot_cost = self.resource_valuator.slot_opportunity_cost(
                    occupied=len(state.consumables),
                    capacity=int(state.consumable_slots),
                    last_slot_penalty=self.last_consumable_slot_penalty,
                    resource="consumable",
                ).total
            resource_cost = float(money_cost.total) + float(slot_cost)
            if not expectation.complete:
                option_value = 0.0
            elif selected.mode == "BUY_AND_USE":
                option_value = float(expectation.use_value)
            else:
                option_value = max(
                    float(expectation.held_value),
                    float(expectation.use_value),
                )
            return ShopNormalizedUtility(
                gain=option_value - resource_cost,
                resource_cost=resource_cost,
                notes=(
                    "D14 Planet uses literal hold/use option value; B4 structural gain is admission-only",
                    f"Planet parent option value={option_value:.3f}",
                    f"shared resource cost={resource_cost:.3f}",
                    *expectation.rationale,
                ),
            )

        if selected.mode == "BUY_AND_USE":
            money_cost = self._money_spend_cost(state, int(selected.economics.price))
            immediate_weight = float(executable.decision.thresholds.immediate_money_weight)
            immediate_value = float(selected.immediate_gain) * immediate_weight
            return ShopNormalizedUtility(
                gain=immediate_value - float(money_cost.total),
                resource_cost=float(money_cost.total),
                notes=(
                    "D14 immediate consumable uses explicit immediate effect only",
                    f"D4 immediate value={immediate_value:.3f}",
                    f"shared resource cost={float(money_cost.total):.3f}",
                    "B4 structural build_gain is admission-only and is not compared cross-family",
                ),
            )

        return original_consumable_gain(self, state, executable)

    ShopUtilityScale.__init__ = init
    ShopUtilityScale.consumable_gain = consumable_gain
    ShopUtilityScale._consumable_literal_parent_installed = True
