from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import fsum, isfinite

from games.balatro.actions import (
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_SHOP,
    REFRESH_SHOP,
    BalatroAction,
)
from games.balatro.build import BalatroBuildProfiler
from games.balatro.shop_policy import BalatroShopPolicy, ShopActionScore
from games.balatro.state import BalatroState


@dataclass(frozen=True)
class FutureShopOfferPrior:
    """One public/static future-shop offer archetype on the shop utility scale.

    ``weight`` is a relative public pool weight, not an RNG observation.
    ``gross_utility`` and ``expected_price`` are deterministic model priors for the
    archetype. They deliberately avoid pretending that the exact unseen card,
    rarity, edition, or price is known.
    """

    family: str
    weight: float
    gross_utility: float
    expected_price: int
    resource: str


@dataclass(frozen=True)
class ShopRerollPoolPrior:
    """Static distribution used to value the option set produced by a reroll."""

    card_slots: int
    offers: tuple[FutureShopOfferPrior, ...]

    def is_valid(self) -> bool:
        if self.card_slots <= 0 or not self.offers:
            return False
        total_weight = 0.0
        for offer in self.offers:
            if (
                not isfinite(float(offer.weight))
                or float(offer.weight) <= 0.0
                or not isfinite(float(offer.gross_utility))
                or int(offer.expected_price) < 0
                or offer.resource not in {"JOKER", "CONSUMABLE"}
            ):
                return False
            total_weight += float(offer.weight)
        return isfinite(total_weight) and total_weight > 0.0


# Public vanilla baseline: two random shop-card slots, with relative family
# weights Joker 20 / Tarot 4 / Planet 4. The utility/price values are explicit
# policy priors on the same scale already used by BalatroShopPolicy; they are not
# claims about the exact unseen card or its rarity. Deck/voucher-specific rate
# modifiers must replace this prior once those public modifiers are represented.
VANILLA_SHOP_REROLL_PRIOR = ShopRerollPoolPrior(
    card_slots=2,
    offers=(
        FutureShopOfferPrior(
            family="JOKER",
            weight=20.0,
            gross_utility=6.0,
            expected_price=5,
            resource="JOKER",
        ),
        FutureShopOfferPrior(
            family="TAROT",
            weight=4.0,
            gross_utility=3.2,
            expected_price=3,
            resource="CONSUMABLE",
        ),
        FutureShopOfferPrior(
            family="PLANET",
            weight=4.0,
            gross_utility=3.5,
            expected_price=3,
            resource="CONSUMABLE",
        ),
    ),
)


@dataclass(frozen=True)
class ShopRerollThresholds:
    """Decision margin for paid reroll EV versus the best visible shop option."""

    minimum_margin: float = 0.25


@dataclass(frozen=True)
class ShopRerollRecommendation:
    decision: str
    reroll_cost: int | None
    executable_action: BalatroAction | None
    current_best_score: float
    future_shop_ev: float
    reroll_resource_cost: float
    reroll_score: float
    unmet_requirements: tuple[str, ...] = ()
    rationale: tuple[str, ...] = ()


class BuildAwareShopRerollPolicy:
    """Compare visible shop value with public-information future-shop EV.

    A reroll creates a choice among future card slots. This policy computes the
    exact expectation of the best immediately actionable offer under an explicit
    static pool prior, then subtracts reroll money/interest/reserve opportunity
    cost using the same :class:`RunResourceValuator` configuration as
    :class:`BalatroShopPolicy`.

    The model never reads RNG state, seed data, future pool ordering, or hidden
    card identities. If an applicable public prior is unavailable, rerolling fails
    closed instead of falling back to a free-form exploration bonus.
    """

    def __init__(
        self,
        *,
        shop_policy: BalatroShopPolicy | None = None,
        build_profiler: BalatroBuildProfiler | None = None,
        thresholds: ShopRerollThresholds | None = None,
        pool_prior: ShopRerollPoolPrior | None = VANILLA_SHOP_REROLL_PRIOR,
    ) -> None:
        self.shop_policy = shop_policy or BalatroShopPolicy()
        self.build_profiler = build_profiler or BalatroBuildProfiler()
        self.thresholds = thresholds or ShopRerollThresholds()
        self.pool_prior = pool_prior

    def recommend(
        self,
        state: BalatroState,
        visible_actions: list[BalatroAction],
        *,
        reroll_cost: int | None,
        visible_score_floor: float | None = None,
    ) -> ShopRerollRecommendation:
        if state.phase != "SHOP":
            raise ValueError("reroll policy requires SHOP phase")

        current_scores = self._visible_scores(state, visible_actions)
        current_best = (
            current_scores[0].total
            if current_scores
            else float(self.shop_policy.hold_bias)
        )
        if visible_score_floor is not None:
            current_best = max(current_best, float(visible_score_floor))

        unmet = self._unmet_requirements(state)

        if reroll_cost is None:
            return self._fail_closed(
                current_best=current_best,
                reroll_cost=None,
                unmet=unmet,
                reason="current reroll cost is not observed; reroll fails closed",
            )

        cost = int(reroll_cost)
        if cost < 0:
            raise ValueError("reroll cost cannot be negative")
        if cost > state.money:
            return self._fail_closed(
                current_best=current_best,
                reroll_cost=cost,
                unmet=unmet,
                reason=f"reroll costs ${cost} but only ${state.money} is available",
            )

        prior = self.pool_prior
        if prior is None or not prior.is_valid():
            return self._fail_closed(
                current_best=current_best,
                reroll_cost=cost,
                unmet=unmet,
                reason="public/static future-shop pool prior is unavailable; reroll fails closed",
            )

        reroll_resource = self.shop_policy.resource_valuator.money_spend_cost(
            money=state.money,
            spend=cost,
            price_weight=self.shop_policy.price_weight,
            interest_weight=self.shop_policy.interest_weight,
            reserve_target=self.shop_policy.reserve_target,
            reserve_weight=self.shop_policy.reserve_weight,
            vouchers=getattr(state, "vouchers", ()),
        )
        money_after_reroll = state.money - cost
        future_ev, offer_scores = self._future_shop_ev(
            state,
            prior,
            money_after_reroll=money_after_reroll,
        )
        reroll_score = future_ev - reroll_resource.total
        required = current_best + (
            0.0 if cost == 0 else self.thresholds.minimum_margin
        )

        rationale = (
            f"visible-shop best score={current_best:.3f}",
            f"future shop EV={future_ev:.3f} across {prior.card_slots} card slots",
            "public pool weights="
            + ", ".join(
                f"{offer.family}:{offer.weight:g}"
                for offer in prior.offers
            ),
            "actionable offer scores="
            + ", ".join(
                f"{family}:{score:.3f}"
                for family, score in offer_scores
            ),
            f"reroll cost=${cost} resource cost={reroll_resource.total:.3f}",
            f"reroll price penalty={reroll_resource.direct:.3f}",
            f"reroll interest penalty={reroll_resource.interest:.3f}",
            f"reroll reserve penalty={reroll_resource.reserve:.3f}",
            f"reroll score={reroll_score:.3f}; required={required:.3f}",
            "future-shop expectation uses static public priors only; no RNG state or future ordering",
        )

        hold = (
            reroll_score < required
            if cost == 0
            else reroll_score <= required
        )
        if hold:
            return ShopRerollRecommendation(
                decision="HOLD",
                reroll_cost=cost,
                executable_action=None,
                current_best_score=current_best,
                future_shop_ev=future_ev,
                reroll_resource_cost=reroll_resource.total,
                reroll_score=reroll_score,
                unmet_requirements=unmet,
                rationale=rationale,
            )

        return ShopRerollRecommendation(
            decision="REROLL",
            reroll_cost=cost,
            executable_action=BalatroAction(REFRESH_SHOP),
            current_best_score=current_best,
            future_shop_ev=future_ev,
            reroll_resource_cost=reroll_resource.total,
            reroll_score=reroll_score,
            unmet_requirements=unmet,
            rationale=rationale,
        )

    def _fail_closed(
        self,
        *,
        current_best: float,
        reroll_cost: int | None,
        unmet: tuple[str, ...],
        reason: str,
    ) -> ShopRerollRecommendation:
        return ShopRerollRecommendation(
            decision="HOLD",
            reroll_cost=reroll_cost,
            executable_action=None,
            current_best_score=current_best,
            future_shop_ev=float("-inf"),
            reroll_resource_cost=float("inf"),
            reroll_score=float("-inf"),
            unmet_requirements=unmet,
            rationale=(
                reason,
                "no heuristic exploration fallback is used",
            ),
        )

    def _future_shop_ev(
        self,
        state: BalatroState,
        prior: ShopRerollPoolPrior,
        *,
        money_after_reroll: int,
    ) -> tuple[float, tuple[tuple[str, float], ...]]:
        total_weight = sum(float(offer.weight) for offer in prior.offers)
        probabilities = tuple(
            float(offer.weight) / total_weight
            for offer in prior.offers
        )
        scores = tuple(
            self._future_offer_score(
                state,
                offer,
                money=money_after_reroll,
            )
            for offer in prior.offers
        )
        hold = float(self.shop_policy.hold_bias)
        offer_scores = tuple(
            (offer.family, score)
            for offer, score in zip(prior.offers, scores)
        )

        # If every family is currently unaffordable or capacity-blocked, the
        # rerolled option set is exactly equivalent to leaving the shop. Preserve
        # that baseline exactly instead of introducing probability-sum roundoff;
        # zero-cost rerolls may then safely win the intentional tie-break.
        if all(score == hold for score in scores):
            return hold, offer_scores

        expected_terms: list[float] = []
        indices = range(len(prior.offers))
        for outcome in product(indices, repeat=prior.card_slots):
            probability = 1.0
            best = hold
            for index in outcome:
                probability *= probabilities[index]
                best = max(best, scores[index])
            expected_terms.append(probability * best)

        return fsum(expected_terms), offer_scores

    def _future_offer_score(
        self,
        state: BalatroState,
        offer: FutureShopOfferPrior,
        *,
        money: int,
    ) -> float:
        hold = float(self.shop_policy.hold_bias)
        price = int(offer.expected_price)
        if price > money:
            return hold

        if offer.resource == "JOKER":
            if len(state.jokers) >= state.joker_slots:
                # Replacement EV requires a concrete candidate/incumbent comparison.
                # A family-level prior cannot safely invent that delta.
                return hold
            slot_cost = self.shop_policy.resource_valuator.slot_opportunity_cost(
                occupied=len(state.jokers),
                capacity=state.joker_slots,
                last_slot_penalty=self.shop_policy.last_joker_slot_penalty,
                penultimate_slot_penalty=self.shop_policy.penultimate_joker_slot_penalty,
                resource="joker",
            ).total
        elif offer.resource == "CONSUMABLE":
            if len(state.consumables) >= state.consumable_slots:
                return hold
            slot_cost = self.shop_policy.resource_valuator.slot_opportunity_cost(
                occupied=len(state.consumables),
                capacity=state.consumable_slots,
                last_slot_penalty=self.shop_policy.last_consumable_slot_penalty,
                penultimate_slot_penalty=0.0,
                resource="consumable",
            ).total
        else:
            return hold

        purchase_resource = self.shop_policy.resource_valuator.money_spend_cost(
            money=money,
            spend=price,
            price_weight=self.shop_policy.price_weight,
            interest_weight=self.shop_policy.interest_weight,
            reserve_target=self.shop_policy.reserve_target,
            reserve_weight=self.shop_policy.reserve_weight,
            vouchers=getattr(state, "vouchers", ()),
        )
        return max(
            hold,
            float(offer.gross_utility) - purchase_resource.total - slot_cost,
        )

    def _visible_scores(
        self,
        state: BalatroState,
        visible_actions: list[BalatroAction],
    ) -> list[ShopActionScore]:
        """Score only deterministic child-layer actions already supported by D12."""
        supported_names = {
            BUY_JOKER,
            BUY_CONSUMABLE,
            BUY_VOUCHER,
            END_SHOP,
        }
        supported = [
            action
            for action in visible_actions
            if action.name in supported_names
        ]

        # Random-state actions (e.g. booster opening) are intentionally absent:
        # the parent arbiter can supply their admitted child score as a floor without
        # making this reroll layer predict the pack's hidden contents itself.
        if not any(action.name == END_SHOP for action in supported):
            supported.append(BalatroAction(END_SHOP))

        return self.shop_policy.rank_actions(state, supported)

    def _unmet_requirements(self, state: BalatroState) -> tuple[str, ...]:
        profile = self.build_profiler.profile(state)
        requirements = {
            requirement
            for effect in profile.effects
            for requirement in effect.requires
        }
        return tuple(
            sorted(
                requirement
                for requirement in requirements
                if not profile.supports(requirement)
            )
        )
