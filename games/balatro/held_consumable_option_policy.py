from __future__ import annotations

"""Normalize held Tarot/Spectral shop value from public future-use mechanics.

D4 historically carries B4 structural/build-path units in ``selected.build_gain``.
Those units are useful for child admission but are not directly comparable with D2
literal build gain, D8 option EV, vouchers, or D11 rerolls at D14.  This policy keeps
D4 admission authoritative, then replaces the D14 value of a held Tarot/Spectral
BUY with the expected value of actually using that consumable on a representative
fresh public hand.

Future hands come only from the unordered authoritative permanent deck.  Small
spaces are exact and larger spaces use the same deterministic public-composition
sampling contract as D1; Balatro RNG state and future draw order are never read.
Each branch is scored by the fully installed opened-pack D9 mechanics with Skip=0,
so deterministic targets, Wheel, Aura/Sigil/Hex/Ankh, Soul, Wraith, Cryptid,
generated-card Spectrals, Ouija and Ectoplasm inherit their existing mechanical
expectation authorities rather than a generic Tarot/Spectral constant.

Held generation cards whose effect depends on consumable-area timing are excluded
here because direct pack selection does not reproduce their held-slot semantics.
They fail closed to zero D14 option value until a dedicated held-use transition is
modeled; B4 may still inform D4 child admission but cannot leak into cross-family
arbitration.
"""

from copy import deepcopy
from dataclasses import dataclass

from games.balatro.actions import SELECT_PACK_CARD, BalatroAction
from games.balatro.live.draw_model import PublicDeckComposition
from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.shop_utility_scale import ShopNormalizedUtility, ShopUtilityScale


@dataclass(frozen=True)
class HeldConsumableOptionExpectation:
    complete: bool
    expected_gain: float
    exact: bool
    rationale: tuple[str, ...] = ()


class HeldConsumableOptionEvaluator:
    """Expected best immediate use of one held Tarot/Spectral on a fresh hand."""

    EXACT_COMBINATION_LIMIT = 128
    SAMPLE_COUNT = 24

    # These cards create other consumables. Their held-use free-slot semantics are
    # not identical to choosing the same card directly from an opened pack, so the
    # generic D9 reuse below deliberately refuses them.
    HELD_SLOT_SENSITIVE = frozenset(
        {
            "The High Priestess",
            "The Emperor",
            "Judgement",
        }
    )

    def __init__(
        self,
        *,
        pack_policy: BalatroPackPolicy | None = None,
        draw_outcomes: PublicDrawOutcomeModel | None = None,
    ) -> None:
        self.pack_policy = pack_policy or BalatroPackPolicy(skip_bias=0.0)
        self.draw_outcomes = draw_outcomes or PublicDrawOutcomeModel(
            exact_combination_limit=self.EXACT_COMBINATION_LIMIT,
            sample_count=self.SAMPLE_COUNT,
            seed=0,
        )

    def evaluate(self, state, candidate) -> HeldConsumableOptionExpectation:
        category = str(getattr(candidate, "category", "") or "").upper()
        name = str(getattr(candidate, "name", "") or "")
        if category not in {"TAROT", "SPECTRAL"}:
            return self._incomplete("held option evaluator only owns Tarot/Spectral BUY value")
        if name in self.HELD_SLOT_SENSITIVE:
            return HeldConsumableOptionExpectation(
                complete=True,
                expected_gain=0.0,
                exact=True,
                rationale=(
                    f"{name} held-use generation depends on consumable-area timing; D14 fails closed",
                    "B4 structural utility is not substituted for run-winning option value",
                ),
            )

        owned = getattr(state, "owned_deck", None)
        if owned is None or not list(owned):
            return self._incomplete(
                "held consumable option unavailable: authoritative owned_deck was not observed"
            )

        hand_size = max(1, int(getattr(state, "hand_size", 0) or 0))
        composition = PublicDeckComposition.from_cards(owned)
        draws = min(hand_size, composition.total_cards)
        distribution = self.draw_outcomes.distribution(composition, draws)

        choice = LivePackChoice(
            area_index=0,
            address=0,
            data={
                "label": name,
                "ability_name": name,
                "ability_set": category,
            },
        )
        action = BalatroAction(SELECT_PACK_CARD, target=choice)

        expected = 0.0
        for outcome in distribution.outcomes:
            projected = deepcopy(state)
            self._neutralize_transient_round(projected)
            projected.phase = "ARCANA_PACK" if category == "TAROT" else "SPECTRAL_PACK"
            projected.score = 0
            projected.hand = [
                self.draw_outcomes.card_from_signature(signature)
                for signature in outcome.cards
            ]
            projected.deck = self.draw_outcomes.remaining_cards(composition, outcome)
            projected.hand_size = draws

            try:
                scored = self.pack_policy.score_action(projected, action)
            except (
                AttributeError,
                IndexError,
                KeyError,
                RuntimeError,
                TypeError,
                ValueError,
                ZeroDivisionError,
            ) as exc:
                return self._incomplete(
                    f"future held {name} D9 valuation failed: {type(exc).__name__}: {exc}"
                )
            # Opened-pack Skip is sunk-cost zero. Negative/unsupported branches are
            # therefore the honest no-use option for a held consumable as well.
            branch_gain = max(0.0, float(scored.total))
            expected += float(outcome.probability) * branch_gain

        return HeldConsumableOptionExpectation(
            complete=True,
            expected_gain=float(expected),
            exact=bool(distribution.exact),
            rationale=(
                f"held {category} option valued by future D9 use mechanics",
                f"future hand size={draws}",
                f"expected positive-use value={expected:.3f}",
                f"future draw distribution={'exact' if distribution.exact else 'deterministic sampled'}",
                "unusable/negative D9 branches contribute the true no-use baseline 0",
                "Balatro RNG state and future draw order are not observed",
            ),
        )

    @staticmethod
    def _neutralize_transient_round(state) -> None:
        state.blind = None
        state.boss_name = None
        state.boss_blind_state_observed = False
        state.boss_blind_hands = set()
        state.boss_blind_only_hand = None
        state.round_most_played_hand = None
        state.score = 0
        state.blind_score = 0
        state.last_played_hand = None
        state.round_hand_play_counts = {
            hand: 0 for hand in getattr(state, "round_hand_play_counts", {})
        }
        state.discards_used = 0

    @staticmethod
    def _incomplete(reason: str) -> HeldConsumableOptionExpectation:
        return HeldConsumableOptionExpectation(
            complete=False,
            expected_gain=0.0,
            exact=False,
            rationale=(
                reason,
                "held consumable D14 option fails closed instead of using B4 structural units",
            ),
        )


def install_held_consumable_option_policy() -> None:
    if getattr(ShopUtilityScale, "_held_consumable_option_installed", False):
        return

    original_init = ShopUtilityScale.__init__
    original_consumable_gain = ShopUtilityScale.consumable_gain

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.held_consumable_option_evaluator = HeldConsumableOptionEvaluator()

    def consumable_gain(self, state, executable):
        selected = executable.decision.selected
        candidate = getattr(executable, "candidate", None)
        category = str(getattr(candidate, "category", "") or "").upper()
        if selected is None or selected.mode != "BUY" or category not in {"TAROT", "SPECTRAL"}:
            return original_consumable_gain(self, state, executable)

        expectation = self.held_consumable_option_evaluator.evaluate(state, candidate)
        economics = selected.economics
        money_cost = self._money_spend_cost(state, int(economics.price))
        slot_cost = self.resource_valuator.slot_opportunity_cost(
            occupied=len(state.consumables),
            capacity=int(state.consumable_slots),
            last_slot_penalty=self.last_consumable_slot_penalty,
            resource="consumable",
        ).total
        resource_cost = float(money_cost.total) + float(slot_cost)
        option_gain = float(expectation.expected_gain) if expectation.complete else 0.0
        gain = option_gain - resource_cost
        return ShopNormalizedUtility(
            gain=gain,
            resource_cost=resource_cost,
            notes=(
                "D14 held consumable uses future public-mechanics option value",
                f"future held-use option value={option_gain:.3f}",
                f"shared resource cost={resource_cost:.3f}",
                "D4 B4 structural build_gain is admission-only and is not compared cross-family",
                *expectation.rationale,
            ),
        )

    ShopUtilityScale.__init__ = init
    ShopUtilityScale.consumable_gain = consumable_gain
    ShopUtilityScale._held_consumable_option_installed = True
