from __future__ import annotations

"""Replace D11's fixed future-Planet utility with current eligible Planet EV."""

from dataclasses import dataclass
from types import SimpleNamespace

from games.balatro.build.high_priestess_expectation import _held_consumable_names, _showman_owned
from games.balatro.planets import create_planet, eligible_planet_names
from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks
from games.balatro.shop_consumable_policy import (
    ConsumableAcquisitionPolicy,
    ConsumableAcquisitionThresholds,
)
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.shop_utility_scale import ShopUtilityScale


@dataclass(frozen=True)
class RerollPlanetExpectation:
    complete: bool
    expected_gain: float
    outcome_count: int
    rationale: tuple[str, ...] = ()


class RerollPlanetExpectationEvaluator:
    def __init__(self, *, shop_policy) -> None:
        self.shop_policy = shop_policy
        self.utility_scale = ShopUtilityScale(shop_policy)

    @staticmethod
    def _policy_for_state(state) -> ConsumableAcquisitionPolicy:
        try:
            playbook = default_balatro_playbooks().for_state(state)
        except BalatroPlaybookNotFound:
            return ConsumableAcquisitionPolicy()
        thresholds = ConsumableAcquisitionThresholds.from_mapping(
            playbook.thresholds_for("D4")
        )
        return ConsumableAcquisitionPolicy(thresholds)

    def evaluate(self, state, *, money: int, expected_price: int) -> RerollPlanetExpectation:
        projected = state.copy()
        projected.money = max(0, int(money))
        policy = self._policy_for_state(projected)

        held = _held_consumable_names(projected)
        showman = _showman_owned(projected)
        names = tuple(eligible_planet_names(projected))
        gains: list[float] = []
        considered: list[str] = []

        for name in names:
            planet = create_planet(name)
            label = str(getattr(planet, "name", name))
            if not showman and label in held:
                continue
            planet.price = int(expected_price)
            planet.cost = int(expected_price)
            try:
                decision = policy.decide(projected, planet)
            except (AttributeError, KeyError, RuntimeError, TypeError, ValueError, ZeroDivisionError) as exc:
                return RerollPlanetExpectation(
                    complete=False,
                    expected_gain=0.0,
                    outcome_count=len(gains),
                    rationale=(
                        f"future Planet D4 valuation failed for {label}: {type(exc).__name__}: {exc}",
                        "future-Planet reroll expectation fails closed",
                    ),
                )

            selected = getattr(decision, "selected", None)
            if selected is None:
                gain = 0.0
            else:
                executable = SimpleNamespace(
                    decision=decision,
                    candidate=planet,
                )
                gain = max(
                    0.0,
                    float(self.utility_scale.consumable_gain(projected, executable).gain),
                )
            gains.append(gain)
            considered.append(label)

        if not gains:
            return RerollPlanetExpectation(
                complete=True,
                expected_gain=0.0,
                outcome_count=0,
                rationale=(
                    "no currently generatable future Planet remains after public duplicate exclusions",
                    f"Showman={'owned' if showman else 'absent'}",
                ),
            )

        expected = sum(gains) / len(gains)
        return RerollPlanetExpectation(
            complete=True,
            expected_gain=expected,
            outcome_count=len(gains),
            rationale=(
                "future Planet uses the current eligible Planet pool and D4/D14 normalized acquisition value",
                f"eligible future Planet outcomes={len(gains)}",
                f"unseen Planet expected-price prior=${int(expected_price)}",
                f"expected actionable Planet normalized gain={expected:.3f}",
                f"Showman={'owned; held duplicates allowed' if showman else 'absent; held duplicates excluded'}",
                "future exact Planet identity and shop price are not observed",
            ),
        )


def install_reroll_planet_expectation_policy() -> None:
    if getattr(BuildAwareShopRerollPolicy, "_public_planet_expectation_installed", False):
        return

    original_init = BuildAwareShopRerollPolicy.__init__
    original_future_offer_score = BuildAwareShopRerollPolicy._future_offer_score

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.reroll_planet_expectation = RerollPlanetExpectationEvaluator(
            shop_policy=self.shop_policy,
        )

    def future_offer_score(self, state, offer, *, money: int, thresholds):
        if str(getattr(offer, "family", "")).upper() != "PLANET":
            return original_future_offer_score(
                self,
                state,
                offer,
                money=money,
                thresholds=thresholds,
            )

        hold = float(self.shop_policy.hold_bias)
        price = int(getattr(offer, "expected_price", 0) or 0)
        if price > int(money):
            return hold
        expectation = self.reroll_planet_expectation.evaluate(
            state,
            money=int(money),
            expected_price=price,
        )
        if not expectation.complete:
            return hold
        return hold + max(0.0, float(expectation.expected_gain))

    BuildAwareShopRerollPolicy.__init__ = init
    BuildAwareShopRerollPolicy._future_offer_score = future_offer_score
    BuildAwareShopRerollPolicy._public_planet_expectation_installed = True
