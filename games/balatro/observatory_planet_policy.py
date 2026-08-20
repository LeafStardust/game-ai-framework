from __future__ import annotations

"""Observatory held-Planet scoring and D7 preservation policy.

Observatory (the Telescope upgrade) gives X1.5 Mult for each held Planet whose
specified poker hand is scored. The passive is public deterministic state, so D1
score projection, D3 voucher valuation and D7 Planet timing must all account for it.
"""

from dataclasses import replace

from games.balatro.live.planet_policy import HOLD, USE, LivePlanetPolicy
from games.balatro.scoring import BalatroScorer
from games.balatro.shop_policy import DefaultShopItemValueEstimator


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _voucher_token(voucher: object) -> str:
    values = (
        voucher if isinstance(voucher, str) else "",
        getattr(voucher, "name", ""),
        getattr(voucher, "label", ""),
        getattr(voucher, "key", ""),
        type(voucher).__name__,
    )
    return " ".join(_normalize(value) for value in values if value)


def _has_observatory(state) -> bool:
    return any(
        "observatory" in _voucher_token(voucher)
        for voucher in getattr(state, "vouchers", ()) or ()
    )


def _planet_matches_hand(planet: object, hand_value: str) -> bool:
    return (
        str(getattr(planet, "category", "")).upper() == "PLANET"
        and _normalize(getattr(planet, "hand_type", "")) == _normalize(hand_value)
    )


def _matching_held_planet_count(state, hand_value: str) -> int:
    return sum(
        1
        for planet in getattr(state, "consumables", ()) or ()
        if _planet_matches_hand(planet, hand_value)
    )


def _joker_token(joker: object) -> str:
    return _normalize(
        getattr(joker, "name", "")
        or getattr(joker, "label", "")
        or type(joker).__name__
    )


def install_observatory_planet_policy() -> None:
    if getattr(BalatroScorer, "_observatory_planet_policy_installed", False):
        return

    original_score = BalatroScorer.score

    def score(self, hand, state=None, cards=None, **kwargs):
        result = original_score(self, hand, state=state, cards=cards, **kwargs)
        if state is None or not _has_observatory(state):
            return result

        hand_value = str(getattr(hand, "value", hand))
        matching = _matching_held_planet_count(state, hand_value)
        if matching <= 0:
            return result

        # Observatory resolves after ordinary Joker scoring. Keep it as final XMult
        # so D1 projections preserve the exact multiplicative effect, including
        # multiple matching held Planets (1.5 ** count).
        result.x_mult *= 1.5 ** matching
        return result

    BalatroScorer.score = score
    BalatroScorer._observatory_planet_policy_installed = True

    original_recommend = LivePlanetPolicy.recommend

    def recommend(self, state, planet):
        decision = original_recommend(self, state, planet)
        if not _has_observatory(state):
            return decision
        if str(getattr(planet, "category", "")).upper() != "PLANET":
            return decision
        if not any(item is planet for item in getattr(state, "consumables", ()) or ()):
            return decision
        if decision.decision != USE:
            return decision

        before = decision.before_projection
        after = decision.after_projection
        if before is None or after is None:
            return decision

        clear_gain = float(decision.clear_probability_gain)
        before_score = float(before.expected_hand_score)
        after_score = float(after.expected_hand_score)
        required = float(decision.required_per_hand)
        final_hand = int(getattr(state, "hands_remaining", 0) or 0) <= 1

        # Spending the Planet is allowed only for a concrete survival improvement.
        # The before/after projections already include loss of Observatory X1.5
        # because the deterministic use simulation removes this Planet.
        survival_use = (
            clear_gain > float(self.thresholds.clear_probability_epsilon)
            or (
                before_score + float(self.thresholds.immediate_score_epsilon) < required
                <= after_score + float(self.thresholds.immediate_score_epsilon)
            )
            or (
                final_hand
                and after_score
                > before_score + float(self.thresholds.immediate_score_epsilon)
            )
        )
        if survival_use:
            return replace(
                decision,
                rationale=(
                    "USE: consuming this Observatory Planet materially improves current survival after accounting for loss of held X1.5",
                    *decision.rationale,
                ),
            )

        return replace(
            decision,
            decision=HOLD,
            rationale=(
                "HOLD: Observatory makes this held Planet a passive X1.5 Mult for its matching poker hand",
                "HOLD: preserve Observatory scaling unless consuming the Planet materially improves current survival",
                f"Observatory before expected score={before_score:.3f}",
                f"Observatory after-use expected score={after_score:.3f}",
                *decision.rationale,
            ),
        )

    LivePlanetPolicy.recommend = recommend
    LivePlanetPolicy._observatory_planet_policy_installed = True

    original_voucher_value = DefaultShopItemValueEstimator._voucher_value

    def voucher_value(self, state, target):
        label = str(getattr(target, "label", getattr(target, "name", "")))
        if _normalize(label) != "observatory":
            return original_voucher_value(self, state, target)

        held_planets = sum(
            str(getattr(item, "category", "")).upper() == "PLANET"
            for item in getattr(state, "consumables", ()) or ()
        )
        perkeo = any(
            token in {"perkeo", "perkeojoker"}
            for token in (_joker_token(joker) for joker in getattr(state, "jokers", ()) or ())
        )
        infrastructure_bonus = min(
            4.0,
            held_planets * 1.5 + (2.0 if perkeo else 0.0),
        )
        return (
            7.0 + infrastructure_bonus,
            (
                "Observatory: held matching Planets provide deterministic X1.5 Mult each",
                f"held Planet cards={held_planets}",
                f"Perkeo duplication infrastructure={perkeo}",
                f"Observatory infrastructure bonus={infrastructure_bonus:.3f}",
            ),
        )

    DefaultShopItemValueEstimator._voucher_value = voucher_value
    DefaultShopItemValueEstimator._observatory_planet_policy_installed = True
