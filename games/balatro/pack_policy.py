from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import (
    BUY_CONSUMABLE,
    BUY_JOKER,
    SELECT_PACK_CARD,
    SKIP_BOOSTER,
    BalatroAction,
)
from games.balatro.build import (
    ContextualConsumableTargetEvaluator,
    ContextualPlayingCardSynergyEvaluator,
)
from games.balatro.build.ankh_expectation import AnkhExpectationEvaluator
from games.balatro.build.aura_expectation import AuraExpectationEvaluator
from games.balatro.build.hex_expectation import HexExpectationEvaluator
from games.balatro.build.sigil_expectation import SigilExpectationEvaluator
from games.balatro.build.wheel_expectation import WheelOfFortuneExpectationEvaluator
from games.balatro.consumable import ConsumableContext
from games.balatro.live.consumable_factory import LiveConsumableFactory
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.live.pack import LivePackChoice
from games.balatro.live.shop import LiveShopItemFactory
from games.balatro.pack_playstyle import PackPlaystyleEvaluator
from games.balatro.shop_policy import DefaultShopItemValueEstimator


@dataclass(frozen=True)
class PackActionScore:
    action: BalatroAction
    total: float
    notes: tuple[str, ...] = ()


class BalatroPackPolicy:
    """Conservative ranking for visible booster-pack choices.

    Joker, Planet, enhanced/edition/sealed playing-card, and deterministic immediate
    Spectral choices can be ranked immediately. The Soul receives a bounded
    Legendary-Joker option value with an early-Ante scaling premium. Deterministic
    targeted Tarot/Spectral transformations are admitted only when the public hand
    supplies a validated B6 target. Aura, Sigil, Hex, and Ankh are admitted through
    analytic public-state expectations over bounded outcomes. The Fool is valued
    from Balatro's public last-Tarot/Planet run history. Wheel of Fortune is valued
    from an analytic public-state edition distribution. Other stochastic,
    destructive, generation, or
    unsupported-target effects remain below Skip until their outcome models are explicit.

    An optional D4 playstyle evaluator can add bounded run-intent value for choices
    whose semantics are directly observable. Joker intent is deliberately not added
    here because D2 already contributes it through the shared item estimator.
    """

    DETERMINISTIC_IMMEDIATE_TAROTS = frozenset(
        {
            "The Hermit",
            "Temperance",
        }
    )
    STOCHASTIC_MODELED_TAROTS = frozenset(
        {
            "The Wheel of Fortune",
        }
    )
    STOCHASTIC_DEFERRED_TAROTS = frozenset(
        {
            "The High Priestess",
            "The Emperor",
            "Judgement",
        }
    )
    # Compatibility alias for older tests/callers. "Safe immediate" now means
    # deterministic immediate effect, not merely "does not ask for hand targets".
    SAFE_IMMEDIATE_TAROTS = DETERMINISTIC_IMMEDIATE_TAROTS

    # Black Hole is the only current Spectral whose complete modeled effect is both
    # deterministic and non-targeted. Four deterministic seal transforms remain on
    # the generic B6 target path. Aura, Sigil, Hex, Ankh, and The Soul have explicit
    # stochastic value models; every other current Spectral stays deferred until modeled.
    DETERMINISTIC_IMMEDIATE_SPECTRALS = frozenset(
        {
            "Black Hole",
        }
    )
    STOCHASTIC_MODELED_SPECTRALS = frozenset(
        {
            "Aura",
            "Sigil",
            "Hex",
            "Ankh",
            "The Soul",
        }
    )
    DEFERRED_SPECTRALS = frozenset(
        {
            "Familiar",
            "Grim",
            "Incantation",
            "Wraith",
            "Ouija",
            "Ectoplasm",
            "Immolate",
            "Cryptid",
        }
    )

    SOUL_BASE_VALUE = 8.0
    SOUL_EARLY_ANTE_CUTOFF = 5
    SOUL_EARLY_ANTE_BONUS = 1.5

    EDITION_BONUS = {
        "FOIL": 0.8,
        "HOLO": 1.5,
        "HOLOGRAPHIC": 1.5,
        "POLYCHROME": 2.5,
        "NEGATIVE": 4.0,
    }

    PLAYING_ENHANCEMENT_VALUE = {
        "m_bonus": 0.9,
        "m_mult": 1.2,
        "m_wild": 0.8,
        "m_glass": 1.8,
        "m_steel": 2.2,
        "m_stone": 0.7,
        "m_gold": 1.6,
        "m_lucky": 1.3,
    }

    PLAYING_SEAL_VALUE = {
        "RED": 2.0,
        "BLUE": 1.5,
        "GOLD": 1.4,
        "PURPLE": 1.2,
    }

    RANK_VALUE = {
        "A": 0.30,
        "Ace": 0.30,
        "K": 0.22,
        "King": 0.22,
        "Q": 0.18,
        "Queen": 0.18,
        "J": 0.14,
        "Jack": 0.14,
        "10": 0.10,
    }

    def __init__(
        self,
        *,
        skip_bias: float = 0.35,
        item_estimator=None,
        joker_factory=None,
        consumable_factory=None,
        fallback_factory=None,
        playing_card_build=None,
        consumable_target_evaluator=None,
        wheel_evaluator=None,
        aura_evaluator=None,
        sigil_evaluator=None,
        hex_evaluator=None,
        ankh_evaluator=None,
        playstyle_evaluator: PackPlaystyleEvaluator | None = None,
    ) -> None:
        self.skip_bias = float(skip_bias)
        self.item_estimator = item_estimator or DefaultShopItemValueEstimator()
        self.joker_factory = joker_factory or LiveJokerFactory()
        self.consumable_factory = consumable_factory or LiveConsumableFactory()
        self.fallback_factory = fallback_factory or LiveShopItemFactory()
        self.playing_card_build = (
            playing_card_build or ContextualPlayingCardSynergyEvaluator()
        )
        self.consumable_target_evaluator = (
            consumable_target_evaluator or ContextualConsumableTargetEvaluator()
        )
        self.wheel_evaluator = wheel_evaluator or WheelOfFortuneExpectationEvaluator()
        self.aura_evaluator = aura_evaluator or AuraExpectationEvaluator()
        self.sigil_evaluator = sigil_evaluator or SigilExpectationEvaluator()
        self.hex_evaluator = hex_evaluator or HexExpectationEvaluator()
        self.ankh_evaluator = ankh_evaluator or AnkhExpectationEvaluator()
        self.playstyle_evaluator = playstyle_evaluator

    @classmethod
    def classified_tarots(cls) -> frozenset[str]:
        """Return every Tarot explicitly classified by autonomous pack policy."""
        return (
            frozenset({"The Fool"})
            | cls.DETERMINISTIC_IMMEDIATE_TAROTS
            | cls.STOCHASTIC_MODELED_TAROTS
            | cls.STOCHASTIC_DEFERRED_TAROTS
            | ContextualConsumableTargetEvaluator.SUPPORTED_TAROTS
        )

    @classmethod
    def classified_spectrals(cls) -> frozenset[str]:
        """Return every Spectral explicitly classified by autonomous pack policy."""
        return (
            cls.DETERMINISTIC_IMMEDIATE_SPECTRALS
            | cls.STOCHASTIC_MODELED_SPECTRALS
            | cls.DEFERRED_SPECTRALS
            | ContextualConsumableTargetEvaluator.SUPPORTED_SPECTRALS
        )

    def choose_action(self, state, actions: list[BalatroAction]) -> BalatroAction:
        ranked = self.rank_actions(state, actions)
        if not ranked:
            raise ValueError("pack policy requires at least one action")
        return ranked[0].action

    def rank_actions(self, state, actions: list[BalatroAction]) -> list[PackActionScore]:
        if not str(getattr(state, "phase", "")).endswith("_PACK"):
            raise ValueError("pack policy requires *_PACK phase")
        scores = [self.score_action(state, action) for action in actions]
        return sorted(
            scores,
            key=lambda result: (
                result.total,
                result.action.name != SKIP_BOOSTER,
            ),
            reverse=True,
        )

    def score_action(self, state, action: BalatroAction) -> PackActionScore:
        if action.name == SKIP_BOOSTER:
            return PackActionScore(action, self.skip_bias, ("skip booster",))
        if action.name != SELECT_PACK_CARD or not isinstance(action.target, LivePackChoice):
            raise ValueError(f"pack policy cannot score action {action.name!r}")

        choice = action.target
        kind = choice.kind
        if kind == "JOKER":
            return self._score_joker(state, action, choice)
        if kind == "PLAYING_CARD":
            return self._score_playing_card(state, action, choice)
        if kind in {"PLANET", "TAROT", "SPECTRAL"}:
            return self._score_consumable(state, action, choice)
        return PackActionScore(action, 0.0, (f"unsupported pack kind={kind}",))

    def _playstyle(
        self,
        state,
        *,
        kind: str,
        target=None,
        rank=None,
        suit=None,
    ) -> tuple[float, tuple[str, ...]]:
        if self.playstyle_evaluator is None:
            return 0.0, ()
        evaluation = self.playstyle_evaluator.evaluate(
            state,
            kind=kind,
            target=target,
            rank=rank,
            suit=suit,
        )
        return float(evaluation.value), tuple(evaluation.rationale)

    def _score_joker(self, state, action, choice: LivePackChoice) -> PackActionScore:
        target = self.joker_factory.create(choice.data)
        if target is None:
            target = self.fallback_factory.create(choice.data, kind="JOKER")
        if target is None:
            utility, notes = 2.0, ("unresolved Joker fallback",)
        else:
            utility, notes = self.item_estimator.estimate(
                state,
                BalatroAction(BUY_JOKER, target=target),
            )
        # Resolve/log the shared intent lifecycle, but D4 returns zero for Jokers so
        # D2's JokerBuildValueEvaluator remains the single source of Joker intent.
        playstyle_value, playstyle_notes = self._playstyle(
            state,
            kind="JOKER",
            target=target,
        )
        edition = str(choice.data.get("edition") or "").upper()
        bonus = self.EDITION_BONUS.get(edition, 0.0)
        combined = (
            *tuple(notes),
            *playstyle_notes,
            *((f"edition bonus={bonus:.2f}",) if bonus else ()),
        )
        return PackActionScore(
            action,
            float(utility) + bonus + playstyle_value,
            combined,
        )

    def _score_consumable(self, state, action, choice: LivePackChoice) -> PackActionScore:
        target = self.consumable_factory.create(choice.data, live_id=choice.live_id)
        if target is None:
            return PackActionScore(action, 0.0, ("unresolved consumable",))

        playstyle_value, playstyle_notes = self._playstyle(
            state,
            kind=choice.kind,
            target=target,
        )

        if choice.kind == "TAROT" and choice.label == "The Fool":
            scored = self._score_fool(state, action, choice)
            return self._add_playstyle(scored, playstyle_value, playstyle_notes)

        if choice.kind == "TAROT" and choice.label == "The Wheel of Fortune":
            scored = self._score_wheel(state, action)
            return self._add_playstyle(scored, playstyle_value, playstyle_notes)

        if choice.kind == "SPECTRAL" and choice.label == "Aura":
            scored = self._score_aura(state, action, choice, target)
            return self._add_playstyle(scored, playstyle_value, playstyle_notes)

        if choice.kind == "SPECTRAL" and choice.label == "Sigil":
            scored = self._score_sigil(state, action, target)
            return self._add_playstyle(scored, playstyle_value, playstyle_notes)

        if choice.kind == "SPECTRAL" and choice.label == "Hex":
            scored = self._score_hex(state, action)
            return self._add_playstyle(scored, playstyle_value, playstyle_notes)

        if choice.kind == "SPECTRAL" and choice.label == "Ankh":
            scored = self._score_ankh(state, action)
            return self._add_playstyle(scored, playstyle_value, playstyle_notes)

        if choice.kind == "SPECTRAL" and choice.label == "The Soul":
            scored = self._score_soul(state, action, target)
            return self._add_playstyle(scored, playstyle_value, playstyle_notes)

        if (
            choice.kind == "TAROT"
            and choice.label in self.STOCHASTIC_DEFERRED_TAROTS
        ):
            return PackActionScore(
                action,
                -1.0 + playstyle_value,
                (
                    f"stochastic Tarot deferred: {choice.label} outcome model "
                    "is not yet autonomous-safe",
                    *playstyle_notes,
                ),
            )

        if (
            choice.kind == "TAROT"
            and choice.label in self.DETERMINISTIC_IMMEDIATE_TAROTS
        ):
            if not target.can_use(ConsumableContext(state=state)):
                return PackActionScore(
                    action,
                    -1.0 + playstyle_value,
                    (
                        f"deterministic immediate Tarot unavailable: {choice.label}",
                        *playstyle_notes,
                    ),
                )

        if choice.kind == "SPECTRAL":
            if choice.label in self.DEFERRED_SPECTRALS:
                return PackActionScore(
                    action,
                    -1.0 + playstyle_value,
                    (
                        f"Spectral deferred: {choice.label} outcome/target semantics "
                        "are not yet autonomous-safe",
                        *playstyle_notes,
                    ),
                )

            if choice.label in self.DETERMINISTIC_IMMEDIATE_SPECTRALS:
                if not target.can_use(ConsumableContext(state=state)):
                    return PackActionScore(
                        action,
                        -1.0 + playstyle_value,
                        (
                            f"deterministic immediate Spectral unavailable: {choice.label}",
                            *playstyle_notes,
                        ),
                    )
                utility, notes = self.item_estimator.estimate(
                    state,
                    BalatroAction(BUY_CONSUMABLE, target=target),
                )
                return PackActionScore(
                    action,
                    float(utility) + playstyle_value,
                    (
                        "deterministic immediate Spectral uses shared B4 item valuation",
                        *tuple(notes),
                        *playstyle_notes,
                    ),
                )

            if choice.label not in ContextualConsumableTargetEvaluator.SUPPORTED_SPECTRALS:
                return PackActionScore(
                    action,
                    -1.0 + playstyle_value,
                    (
                        f"unclassified Spectral fails closed: {choice.label}",
                        *playstyle_notes,
                    ),
                )

        requires_target = (
            (
                choice.kind == "SPECTRAL"
                and choice.label in ContextualConsumableTargetEvaluator.SUPPORTED_SPECTRALS
            )
            or (
                choice.kind == "TAROT"
                and choice.label not in self.SAFE_IMMEDIATE_TAROTS
            )
        )
        if requires_target:
            target_evaluation = self.consumable_target_evaluator.recommend(state, target)
            if target_evaluation is None or target_evaluation.total_gain <= 0.0:
                return PackActionScore(
                    action,
                    -1.0 + playstyle_value,
                    (
                        f"{choice.kind.title()} requires unsupported follow-up selection "
                        "or has no positive B6 target",
                        *playstyle_notes,
                    ),
                )

            utility, notes = self.item_estimator.estimate(
                state,
                BalatroAction(BUY_CONSUMABLE, target=target),
            )
            targeted_action = BalatroAction(
                SELECT_PACK_CARD,
                cards=list(target_evaluation.cards),
                target=choice,
            )
            combined = (
                *tuple(notes),
                f"B6 pack target gain={target_evaluation.total_gain:.3f}",
                f"target_indices={target_evaluation.target_indices}",
                *target_evaluation.rationale,
                *playstyle_notes,
            )
            return PackActionScore(
                targeted_action,
                float(utility) + float(target_evaluation.total_gain) + playstyle_value,
                combined,
            )

        utility, notes = self.item_estimator.estimate(
            state,
            BalatroAction(BUY_CONSUMABLE, target=target),
        )
        return PackActionScore(
            action,
            float(utility) + playstyle_value,
            (*tuple(notes), *playstyle_notes),
        )

    @staticmethod
    def _add_playstyle(
        scored: PackActionScore,
        value: float,
        notes: tuple[str, ...],
    ) -> PackActionScore:
        return PackActionScore(
            scored.action,
            float(scored.total) + float(value),
            (*scored.notes, *notes),
        )

    def _score_wheel(
        self,
        state,
        action: BalatroAction,
    ) -> PackActionScore:
        expectation = self.wheel_evaluator.evaluate(state)
        if not expectation.available:
            return PackActionScore(
                action,
                -1.0,
                ("Wheel unavailable: no editionless public Joker target",),
            )
        if not expectation.complete:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Wheel deferred: public stochastic outcome model could not "
                    "score every edition branch",
                    *expectation.rationale,
                ),
            )
        return PackActionScore(
            action,
            float(expectation.expected_build_gain),
            (
                "Wheel uses analytic public-state expectation; no RNG sample or seed read",
                *expectation.rationale,
            ),
        )

    def _score_soul(
        self,
        state,
        action: BalatroAction,
        target,
    ) -> PackActionScore:
        joker_slots = max(0, int(getattr(state, "joker_slots", 5) or 5))
        owned_jokers = len(getattr(state, "jokers", ()) or ())
        if owned_jokers >= joker_slots or not target.can_use(
            ConsumableContext(state=state)
        ):
            return PackActionScore(
                action,
                -1.0,
                (
                    "The Soul unavailable: no free Joker slot "
                    f"({owned_jokers}/{joker_slots})",
                ),
            )

        ante = max(1, int(getattr(state, "ante", 1) or 1))
        early_ante_bonus = max(
            0,
            self.SOUL_EARLY_ANTE_CUTOFF - ante,
        ) * self.SOUL_EARLY_ANTE_BONUS
        total = self.SOUL_BASE_VALUE + early_ante_bonus
        return PackActionScore(
            action,
            total,
            (
                "The Soul creates a random Legendary Joker in a free slot",
                f"Legendary Joker option value={self.SOUL_BASE_VALUE:.3f}",
                f"early-Ante scaling opportunity bonus={early_ante_bonus:.3f}",
                f"free Joker slots={joker_slots - owned_jokers}",
            ),
        )

    def _score_aura(
        self,
        state,
        action: BalatroAction,
        choice: LivePackChoice,
        target,
    ) -> PackActionScore:
        expectation = self.aura_evaluator.evaluate(state)
        if not expectation.available:
            return PackActionScore(
                action,
                -1.0,
                ("Aura unavailable: no editionless public hand target",),
            )
        if not expectation.complete or expectation.target_index is None:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Aura deferred: public stochastic outcome model could not "
                    "score every edition branch",
                    *expectation.rationale,
                ),
            )
        if expectation.expected_total_gain <= 0.0:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Aura has no positive analytic target value",
                    *expectation.rationale,
                ),
            )

        hand = list(getattr(state, "hand", ()))
        if not (0 <= expectation.target_index < len(hand)):
            return PackActionScore(
                action,
                -1.0,
                ("Aura target index is no longer present in public hand state",),
            )

        utility, notes = self.item_estimator.estimate(
            state,
            BalatroAction(BUY_CONSUMABLE, target=target),
        )
        targeted_action = BalatroAction(
            SELECT_PACK_CARD,
            cards=[hand[expectation.target_index]],
            target=choice,
        )
        return PackActionScore(
            targeted_action,
            float(utility) + float(expectation.expected_total_gain),
            (
                *tuple(notes),
                "Aura uses analytic public-state expectation; no RNG sample or seed read",
                f"B6 Aura expected target gain={expectation.expected_total_gain:.3f}",
                *expectation.rationale,
            ),
        )

    def _score_sigil(
        self,
        state,
        action: BalatroAction,
        target,
    ) -> PackActionScore:
        expectation = self.sigil_evaluator.evaluate(state)
        if not expectation.available:
            return PackActionScore(
                action,
                -1.0,
                ("Sigil unavailable: no public hand cards to rewrite",),
            )
        if not expectation.complete:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Sigil deferred: public stochastic outcome model could not "
                    "score every suit branch",
                    *expectation.rationale,
                ),
            )
        if expectation.expected_total_gain <= 0.0:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Sigil has no positive analytic rewrite value",
                    *expectation.rationale,
                ),
            )

        utility, notes = self.item_estimator.estimate(
            state,
            BalatroAction(BUY_CONSUMABLE, target=target),
        )
        return PackActionScore(
            action,
            float(utility) + float(expectation.expected_total_gain),
            (
                *tuple(notes),
                "Sigil uses analytic public-state expectation; no RNG sample or seed read",
                f"B6 Sigil expected rewrite gain={expectation.expected_total_gain:.3f}",
                *expectation.rationale,
            ),
        )

    def _score_hex(
        self,
        state,
        action: BalatroAction,
    ) -> PackActionScore:
        expectation = self.hex_evaluator.evaluate(state)
        if not expectation.available:
            return PackActionScore(
                action,
                -1.0,
                ("Hex unavailable: no public Joker target",),
            )
        if not expectation.complete:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Hex deferred: public stochastic outcome model could not "
                    "score every Joker branch",
                    *expectation.rationale,
                ),
            )
        if expectation.expected_build_gain <= 0.0:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Hex has no positive analytic whole-build value",
                    *expectation.rationale,
                ),
            )
        return PackActionScore(
            action,
            float(expectation.expected_build_gain),
            (
                "Hex uses analytic B3 whole-build expectation; no RNG sample or seed read",
                *expectation.rationale,
            ),
        )

    def _score_ankh(
        self,
        state,
        action: BalatroAction,
    ) -> PackActionScore:
        expectation = self.ankh_evaluator.evaluate(state)
        if not expectation.available:
            return PackActionScore(
                action,
                -1.0,
                ("Ankh unavailable: no public Joker target",),
            )
        if not expectation.complete:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Ankh deferred: public stochastic outcome model could not "
                    "score every Joker branch",
                    *expectation.rationale,
                ),
            )
        if expectation.expected_build_gain <= 0.0:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Ankh has no positive analytic whole-build value",
                    *expectation.rationale,
                ),
            )
        return PackActionScore(
            action,
            float(expectation.expected_build_gain),
            (
                "Ankh uses analytic B3 whole-build expectation; no RNG sample or seed read",
                *expectation.rationale,
            ),
        )

    def _score_fool(
        self,
        state,
        action: BalatroAction,
        choice: LivePackChoice,
    ) -> PackActionScore:
        last_key = str(choice.data.get("last_tarot_planet") or "")
        if not last_key:
            return PackActionScore(
                action,
                -1.0,
                ("Fool unavailable: no previous Tarot/Planet in public run history",),
            )
        if last_key == "c_fool":
            return PackActionScore(
                action,
                -1.0,
                ("Fool unavailable: previous Tarot/Planet is The Fool",),
            )

        slots = max(0, int(getattr(state, "consumable_slots", 0)))
        held = len(getattr(state, "consumables", ()))
        if held >= slots:
            return PackActionScore(
                action,
                -1.0,
                (
                    f"Fool unavailable from pack: consumable slots full ({held}/{slots})",
                ),
            )

        copied = self.consumable_factory.create({"key": last_key})
        if copied is None:
            return PackActionScore(
                action,
                -1.0,
                (f"Fool copy target {last_key!r} is not modeled",),
            )

        copied_name = str(getattr(copied, "name", type(copied).__name__))
        copied_category = str(getattr(copied, "category", "")).upper()
        if copied_name == "The Fool" or copied_category not in {"TAROT", "PLANET"}:
            return PackActionScore(
                action,
                -1.0,
                (f"Fool copy target {last_key!r} is invalid",),
            )

        utility, notes = self.item_estimator.estimate(
            state,
            BalatroAction(BUY_CONSUMABLE, target=copied),
        )
        return PackActionScore(
            action,
            float(utility),
            (
                f"Fool copies public last Tarot/Planet={copied_name}",
                f"last_tarot_planet={last_key}",
                *tuple(notes),
            ),
        )

    def _score_playing_card(self, state, action, choice: LivePackChoice) -> PackActionScore:
        value = choice.data.get("value") or {}
        modifier = choice.data.get("modifier") or {}
        rank = value.get("rank")
        suit = value.get("suit")
        enhancement = modifier.get("enhancement")
        edition = modifier.get("edition")
        seal = modifier.get("seal")

        score = self.RANK_VALUE.get(str(rank), 0.0)
        notes: list[str] = []

        if enhancement:
            amount = self.PLAYING_ENHANCEMENT_VALUE.get(str(enhancement), 0.0)
            score += amount
            notes.append(f"enhancement={enhancement} value={amount:.2f}")

        edition_text = str(edition or "").upper()
        if edition_text:
            amount = self.EDITION_BONUS.get(edition_text, 0.0)
            score += amount
            notes.append(f"edition={edition_text} value={amount:.2f}")

        seal_text = str(seal or "").upper()
        if seal_text:
            amount = self.PLAYING_SEAL_VALUE.get(seal_text, 0.0)
            score += amount
            notes.append(f"seal={seal_text} value={amount:.2f}")

        contextual = self.playing_card_build.evaluate(
            state,
            rank=rank,
            suit=suit,
            enhancement=enhancement,
            seal=seal,
            edition=edition,
        )
        context_gain = float(contextual.total_gain)
        score += context_gain
        notes.append(f"B6 playing-card build gain={context_gain:.3f}")
        notes.extend(contextual.rationale)

        playstyle_value, playstyle_notes = self._playstyle(
            state,
            kind="PLAYING_CARD",
            rank=rank,
            suit=suit,
        )
        score += playstyle_value
        notes.extend(playstyle_notes)

        if not enhancement and not edition_text and not seal_text:
            notes.append("vanilla playing card; small rank-only value before build context")
        return PackActionScore(action, score, tuple(notes))
