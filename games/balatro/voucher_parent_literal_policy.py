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
* Grabber / Nacho Tong: +1 hand per played blind, valued only across the boss rounds
  that are unavoidably required to win through the configured Ante-8 target;
* Wasteful / Recyclomancy: +1 discard per played blind on the same unavoidable
  victory-round lower bound; optional Small/Big blinds are deliberately omitted;
* Observatory: literal representative whole-build score change from adding the
  voucher to the current public state, so only actually held matching Planets create
  immediate parent value through the installed Observatory X1.5 scoring mechanic;
* Seed Money / Money Tree: conservative next-interest-payout improvement at the
  actual post-purchase cash level, expressed with D14's own interest weight;
* Blank: while Antimatter is observably locked, one real step toward its ten-Blank
  unlock is allowed to cover only Blank's direct sticker-price term plus a tiny
  bounded progression tie-break. Lost interest, reserve pressure and cash-scaling
  value remain fully charged. Once Antimatter is unlocked, Blank returns to zero
  current-run parent value.

Persistent effects whose payoff requires a future policy choice rather than an
unavoidable event fail closed at zero in D14 until that choice has a grounded
planning horizon. This includes future rerolls, purchases, Celestial packs, shop
playing-card opportunities, and the Hieroglyph/Petroglyph ante-resource trade. They
must not fall back to the old fixed cross-family voucher number merely because D3
admits them strategically.

This module never changes D3 admission and never reads RNG state, pseudoseeds, or
future draw/shop order.
"""

from dataclasses import replace

from games.balatro.antimatter_unlock_live_state_policy import (
    install_antimatter_unlock_live_state_policy,
)
from games.balatro.blank_antimatter_progression_policy import (
    install_blank_antimatter_progression_policy,
)
from games.balatro.build.hand_size_opportunity import HandSizeOpportunityEvaluator
from games.balatro.consumable_d14_literal_policy import PlanetD14OptionEvaluator
from games.balatro.discovery import DISCOVERY_TIEBREAK_CAP
from games.balatro.reroll_joker_expectation_policy import RerollJokerExpectationEvaluator
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.shop_reroll_policy import VANILLA_SHOP_REROLL_PRIOR
from games.balatro.shop_voucher_policy import VoucherAcquisitionThresholds


_LITERAL_PARENT_VOUCHERS = frozenset(
    {
        "Antimatter",
        "Paint Brush",
        "Palette",
        "Grabber",
        "Nacho Tong",
        "Wasteful",
        "Recyclomancy",
        "Telescope",
        "Observatory",
        "Seed Money",
        "Money Tree",
        "Blank",
        "Clearance Sale",
        "Liquidation",
        "Reroll Surplus",
        "Reroll Glut",
        "Hieroglyph",
        "Petroglyph",
        "Magic Trick",
        "Illusion",
    }
)

_POLICY_CONTINGENT_PARENT_VOUCHERS = frozenset(
    {
        "Telescope",
        "Clearance Sale",
        "Liquidation",
        "Reroll Surplus",
        "Reroll Glut",
        "Hieroglyph",
        "Petroglyph",
        "Magic Trick",
        "Illusion",
    }
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


def _mandatory_victory_rounds(state) -> tuple[int, int]:
    """Return the unavoidable played-blind lower bound through the run target.

    Winning a normal Red/White run requires clearing one Boss Blind in every
    remaining Ante. Small and Big Blinds may be skipped, so counting them would be a
    policy assumption. At any live SHOP before victory, ``target_ante - ante + 1``
    therefore counts only unavoidable future Boss rounds, including the current
    Ante's Boss when it has not yet been cleared. Live state advances ``ante`` after
    a cleared Boss before the next shop, so the same expression remains valid there.
    """
    target_ante = int(VoucherAcquisitionThresholds().target_ante)
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    return max(0, target_ante - ante + 1), target_ante


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
        if label in {"Grabber", "Nacho Tong"}:
            return self._round_resource_gain(state, resource="hand")
        if label in {"Wasteful", "Recyclomancy"}:
            return self._round_resource_gain(state, resource="discard")
        if label == "Observatory":
            return self._observatory(state, voucher)
        if label in {"Seed Money", "Money Tree"}:
            return self._interest_cap_gain(state, voucher, money_after=money_after)
        if label == "Blank":
            return self._blank(state, price=price)
        if label in _POLICY_CONTINGENT_PARENT_VOUCHERS:
            return self._policy_contingent_zero(label)
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

    def _round_resource_gain(self, state, *, resource: str):
        rounds, target_ante = _mandatory_victory_rounds(state)
        valuator = self.shop_policy.resource_valuator
        if resource == "hand":
            marginal = valuator.hand_value(state)
        elif resource == "discard":
            marginal = valuator.discard_value(state)
        else:
            raise ValueError(f"unsupported round resource: {resource}")

        # The survival component is current-blind pressure and is not valid to copy
        # across unseen future Bosses. Only the shared resource model's invariant
        # direct component is propagated across the mechanically unavoidable rounds.
        per_round = max(0.0, float(marginal.direct))
        gain = per_round * float(rounds)
        return True, gain, (
            f"permanent +1 {resource} per played blind",
            f"Red/White target Ante={target_ante}",
            f"unavoidable remaining Boss rounds={rounds}",
            "Small/Big blinds are omitted because skipping them is a future policy choice",
            f"shared marginal {resource} direct value per guaranteed round={per_round:.3f}",
            "current-blind survival premium is not projected onto unseen future Bosses",
            f"guaranteed-horizon parent gain={gain:.3f}",
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

    def _interest_cap_gain(self, state, voucher, *, money_after: int):
        valuator = self.shop_policy.resource_valuator
        before_vouchers = tuple(getattr(state, "vouchers", ()) or ())
        after_vouchers = (*before_vouchers, voucher)
        before_interest = valuator.interest_value(
            int(money_after),
            vouchers=before_vouchers,
        )
        after_interest = valuator.interest_value(
            int(money_after),
            vouchers=after_vouchers,
        )
        extra_dollars = max(0, int(after_interest) - int(before_interest))
        gain = float(self.shop_policy.interest_weight) * float(extra_dollars)
        return True, gain, (
            f"interest-cap voucher evaluated at post-purchase cash=${int(money_after)}",
            f"next interest payout before=${int(before_interest)} after=${int(after_interest)}",
            f"conservative next-payout improvement=${extra_dollars}",
            f"D14 interest weight={float(self.shop_policy.interest_weight):.3f}",
            f"mechanical parent gain={gain:.3f}",
            "later-round compounding/upside is omitted rather than assigned a synthetic horizon premium",
        )

    @staticmethod
    def _policy_contingent_zero(label: str):
        reason = {
            "Telescope": "requires choosing a future Celestial Pack",
            "Clearance Sale": "requires one or more future purchases",
            "Liquidation": "requires one or more future purchases",
            "Reroll Surplus": "requires choosing one or more future rerolls",
            "Reroll Glut": "requires choosing one or more future rerolls",
            "Hieroglyph": "requires a common-unit plan for the immediate Ante decrease versus persistent hand loss",
            "Petroglyph": "requires a common-unit plan for the immediate Ante decrease versus persistent discard loss",
            "Magic Trick": "requires valuing future generated playing-card shop opportunities",
            "Illusion": "requires valuing future generated enhanced/edition/seal playing-card shop opportunities",
        }.get(label, "requires an unresolved future policy choice")
        return True, 0.0, (
            f"{label} D14 parent fails closed: {reason}",
            "no arbitrary reroll/purchase/pack/shop count is assumed",
            "D3 admission remains authoritative; only the incompatible fixed cross-family parent value is removed",
        )

    def _blank(self, state, *, price: int):
        if not bool(getattr(state, "antimatter_unlock_observed", False)):
            return False, 0.0, (
                "Blank progression value unavailable: Antimatter unlock state was not observed",
            )
        if bool(getattr(state, "antimatter_unlocked", False)):
            return True, 0.0, (
                "Antimatter is already unlocked; Blank has no remaining unlock-progression parent value",
            )

        # Collection progression is a real secondary objective in this agent, but it
        # remains subordinate to winning the run. Cover only the direct sticker-price
        # term so Blank can be purchased in a comfortable shop; D14 still charges all
        # lost interest, reserve pressure and cash-scaling value. The tiny bounded
        # tie-break prevents an economically free progression step from tying
        # END_SHOP exactly.
        direct_budget = float(price) * float(self.shop_policy.price_weight)
        progression_tiebreak = float(DISCOVERY_TIEBREAK_CAP)
        gain = direct_budget + progression_tiebreak
        return True, gain, (
            "Blank advances the still-locked Antimatter unlock by one of ten required redemptions",
            f"progression covers direct purchase term={direct_budget:.3f}",
            f"bounded progression tie-break={progression_tiebreak:.3f}",
            "lost interest, reserve pressure and Bull/Bootstraps cash-scaling opportunity cost remain fully charged by D14",
            "once Antimatter unlocks, this progression value becomes zero",
        )


def install_voucher_parent_literal_policy() -> None:
    # These two authorities are part of Blank's parent contract. Installing them
    # here avoids a separate package-order dependency: this installer already runs
    # before any live SHOP observation, and later D3 wrappers continue to wrap the
    # progression admission normally.
    install_antimatter_unlock_live_state_policy()
    install_blank_antimatter_progression_policy()

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
                        f"mechanical/progression parent value={float(parent_value):.3f}",
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
