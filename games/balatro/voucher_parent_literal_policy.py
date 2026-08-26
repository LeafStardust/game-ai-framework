from __future__ import annotations

"""Replace fixed D3 parent values for mechanically measurable vouchers.

D3 remains authoritative for voucher BUY/HOLD admission. D14 must not, however,
compare legacy fixed voucher numbers directly with literal Joker/consumable/booster
utility when the voucher's persistent mechanic can be measured from public state.

This adapter currently owns exact/publicly measurable effects:

* Antimatter: +1 Joker slot, valued as the marginal public future-Joker option at
  post-purchase cash using the same D11/D2/D14 expectation as Ectoplasm;
* Paint Brush / Palette: +1 permanent hand size, valued as the expected best literal
  one-hand score improvement from H to H+1 using the same public draw machinery and
  D2 direct-score scale used for Ouija/Ectoplasm hand-size cost;
* Observatory: literal representative whole-build score change from adding the
  voucher to the current public state, so only actually held matching Planets create
  immediate parent value through the installed Observatory X1.5 scoring mechanic.

Other vouchers remain under D3's persistent strategic model until their mechanics
have an equally grounded parent-scale evaluator. This module never changes D3
admission and never reads RNG state, pseudoseeds, or future draw/shop order.
"""

from dataclasses import replace

from games.balatro.build.hand_size_opportunity import HandSizeOpportunityEvaluator
from games.balatro.consumable_d14_literal_policy import PlanetD14OptionEvaluator
from games.balatro.reroll_joker_expectation_policy import RerollJokerExpectationEvaluator
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.shop_reroll_policy import VANILLA_SHOP_REROLL_PRIOR


_LITERAL_PARENT_VOUCHERS = frozenset(
    {"Antimatter", "Paint Brush", "Palette", "Observatory"}
)


def _label(item) -> str:
    return str(
        getattr(item, "label", None)
        or getattr(item, "name", None)
        or type(item).__name__
    )


def _price(item) -> int:
    value = getattr(item, "price", getattr(item, "cost", 0))
    if isinstance(value, dict):
        value = value.get("buy", 0)
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _future_joker_price_prior() -> int:
    for offer in VANILLA_SHOP_REROLL_PRIOR.offers:
        if str(offer.family).upper() == "JOKER":
            return int(offer.expected_price)
    return 5


class VoucherParentLiteralEvaluator:
    def __init__(self, *, shop_policy) -> None:
        self.shop_policy = shop_policy
        self.hand_size = HandSizeOpportunityEvaluator()
        self.joker_option = RerollJokerExpectationEvaluator(shop_policy=shop_policy)
        self.direct_score = PlanetD14OptionEvaluator()

    def evaluate(self, state, voucher) -> tuple[bool, float, tuple[str, ...]]:
        label = _label(voucher)
        price = _price(voucher)
        money_after = int(state.money) - price
        if money_after < 0:
            return False, 0.0, ("voucher is unaffordable",)

        if label == "Antimatter":
            return self._antimatter(state, money_after=money_after)
        if label in {"Paint Brush", "Palette"}:
            return self._hand_size_gain(state)
        if label == "Observatory":
            return self._observatory(state, voucher)
        return False, 0.0, ("voucher is outside literal parent authority",)

    def _antimatter(self, state, *, money_after: int):
        expected_price = _future_joker_price_prior()
        before = state.copy()
        before.money = int(money_after)
        after = before.copy()
        after.joker_slots = int(after.joker_slots) + 1

        current = self.joker_option.evaluate(
            before,
            money=int(money_after),
            expected_price=expected_price,
        )
        expanded = self.joker_option.evaluate(
            after,
            money=int(money_after),
            expected_price=expected_price,
        )
        if not current.complete or not expanded.complete:
            return False, 0.0, (
                "Antimatter parent value unavailable: public future-Joker expectation incomplete",
            )
        gain = max(0.0, float(expanded.expected_gain) - float(current.expected_gain))
        return True, gain, (
            "Antimatter parent value is marginal public future-Joker option from +1 slot",
            f"future Joker option before={float(current.expected_gain):.3f}",
            f"future Joker option after={float(expanded.expected_gain):.3f}",
            f"literal capacity gain={gain:.3f}",
            f"future unseen Joker price remains D11 prior=${expected_price}",
        )

    def _hand_size_gain(self, state):
        owned = getattr(state, "owned_deck", None)
        if owned is None or not list(owned):
            return False, 0.0, (
                "hand-size voucher parent value unavailable: authoritative owned_deck was not observed",
            )
        before_size = max(1, int(getattr(state, "hand_size", 0) or 0))
        from games.balatro.live.draw_model import PublicDeckComposition

        composition = PublicDeckComposition.from_cards(owned)
        before = self.hand_size._expected_best_score(state, composition, before_size)
        after = self.hand_size._expected_best_score(state, composition, before_size + 1)
        if before is None or after is None:
            return False, 0.0, (
                "hand-size voucher parent value failed closed on incomplete literal scoring",
            )
        before_score, before_exact = before
        after_score, after_exact = after
        relative = max(
            0.0,
            (float(after_score) - float(before_score))
            / max(abs(float(before_score)), 1.0),
        )
        gain = min(
            self.hand_size.weights.direct_scoring_cap,
            relative * self.hand_size.weights.direct_scoring_gain,
        )
        return True, gain, (
            f"permanent hand-size capacity {before_size}->{before_size + 1}",
            f"expected best literal play before={float(before_score):.3f}",
            f"expected best literal play after={float(after_score):.3f}",
            f"relative scoring-capacity gain={relative:.6f}",
            f"D2-scale hand-size parent gain={gain:.3f}",
            f"before distribution={'exact' if before_exact else 'deterministic sampled'}",
            f"after distribution={'exact' if after_exact else 'deterministic sampled'}",
        )

    def _observatory(self, state, voucher):
        after = state.copy()
        after.vouchers.append(voucher)
        value = self.direct_score._relative_direct_value(state, after)
        if value is None:
            return False, 0.0, (
                "Observatory parent value failed closed on incomplete literal scoring",
            )
        gain = max(0.0, float(value))
        matching_planets = sum(
            1
            for item in tuple(getattr(state, "consumables", ()) or ())
            if str(getattr(item, "category", "") or "").upper() == "PLANET"
        )
        return True, gain, (
            "Observatory parent value uses literal before/after scorer with voucher added",
            f"currently held Planet cards={matching_planets}",
            f"literal current-build gain={gain:.3f}",
            "future Planet acquisition/Perkeo infrastructure is omitted rather than assigned a synthetic premium",
        )


def install_voucher_parent_literal_policy() -> None:
    if getattr(BalatroShopPolicy, "_literal_capacity_voucher_parent_installed", False):
        return

    original_init = BalatroShopPolicy.__init__
    original_rank_actions = BalatroShopPolicy.rank_actions

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.voucher_parent_literal = VoucherParentLiteralEvaluator(shop_policy=self)

    def rank_actions(self, state, actions):
        ranked = list(original_rank_actions(self, state, actions))
        if not ranked:
            return ranked

        rewritten = []
        for score in ranked:
            action = score.action
            if str(getattr(action, "name", "")) != "BUY_VOUCHER":
                rewritten.append(score)
                continue
            voucher = getattr(action, "target", None)
            label = _label(voucher)
            if label not in _LITERAL_PARENT_VOUCHERS:
                rewritten.append(score)
                continue

            complete, parent_value, notes = self.voucher_parent_literal.evaluate(state, voucher)
            if not complete:
                # D3 already admitted the voucher, but if literal parent value cannot
                # be established it must not inherit the old fixed cross-family number.
                parent_value = 0.0
            price = _price(voucher)
            resource = self.resource_valuator.money_spend_cost(
                money=int(state.money),
                spend=price,
                price_weight=float(self.price_weight),
                interest_weight=float(self.interest_weight),
                reserve_target=int(self.reserve_target),
                reserve_weight=float(self.reserve_weight),
                vouchers=getattr(state, "vouchers", ()),
                jokers=getattr(state, "jokers", ()),
            )
            normalized = float(parent_value) - float(resource.total)
            rewritten.append(
                replace(
                    score,
                    total=float(self.hold_bias) + normalized,
                    item_utility=float(parent_value),
                    price_penalty=float(resource.direct),
                    interest_penalty=float(resource.interest),
                    reserve_penalty=float(resource.reserve),
                    cash_scaling_penalty=float(resource.cash_scaling),
                    notes=(
                        "D14 literal voucher parent authority",
                        f"voucher={label}",
                        f"mechanical parent value={float(parent_value):.3f}",
                        f"shared resource cost={float(resource.total):.3f}",
                        f"normalized voucher gain={normalized:.3f}",
                        *notes,
                    ),
                )
            )

        return sorted(
            rewritten,
            key=lambda result: (
                float(result.total),
                result.action.name == "END_SHOP",
            ),
            reverse=True,
        )

    BalatroShopPolicy.__init__ = init
    BalatroShopPolicy.rank_actions = rank_actions
    BalatroShopPolicy._literal_capacity_voucher_parent_installed = True
