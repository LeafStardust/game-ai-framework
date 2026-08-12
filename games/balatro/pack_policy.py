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
from games.balatro.live.consumable_factory import LiveConsumableFactory
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.live.pack import LivePackChoice
from games.balatro.live.shop import LiveShopItemFactory
from games.balatro.shop_policy import DefaultShopItemValueEstimator


@dataclass(frozen=True)
class PackActionScore:
    action: BalatroAction
    total: float
    notes: tuple[str, ...] = ()


class BalatroPackPolicy:
    """Conservative ranking for visible booster-pack choices.

    Joker, Planet, and enhanced/edition/sealed playing-card choices can be ranked
    immediately. Deterministic targeted Tarot transformations are admitted only
    when the public hand supplies a validated B6 target. Other Tarot/Spectral
    follow-up semantics remain below Skip until their targeting and stochastic
    consequences are modeled.
    """

    SAFE_IMMEDIATE_TAROTS = {
        "The Fool",
        "The High Priestess",
        "The Emperor",
        "The Hermit",
        "The Wheel of Fortune",
        "Temperance",
        "Judgement",
    }

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
        edition = str(choice.data.get("edition") or "").upper()
        bonus = self.EDITION_BONUS.get(edition, 0.0)
        combined = tuple(notes) + ((f"edition bonus={bonus:.2f}",) if bonus else ())
        return PackActionScore(action, float(utility) + bonus, combined)

    def _score_consumable(self, state, action, choice: LivePackChoice) -> PackActionScore:
        target = self.consumable_factory.create(choice.data, live_id=choice.live_id)
        if target is None:
            return PackActionScore(action, 0.0, ("unresolved consumable",))

        if choice.kind == "TAROT" and choice.label not in self.SAFE_IMMEDIATE_TAROTS:
            target_evaluation = self.consumable_target_evaluator.recommend(state, target)
            if target_evaluation is None:
                return PackActionScore(
                    action,
                    -1.0,
                    (
                        "Tarot requires unsupported follow-up selection or has no valid B6 target",
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
            )
            return PackActionScore(
                targeted_action,
                float(utility) + float(target_evaluation.total_gain),
                combined,
            )

        if choice.kind == "SPECTRAL":
            return PackActionScore(
                action,
                -1.0,
                ("Spectral follow-up semantics not yet automated",),
            )

        utility, notes = self.item_estimator.estimate(
            state,
            BalatroAction(BUY_CONSUMABLE, target=target),
        )
        return PackActionScore(action, float(utility), tuple(notes))

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

        if not enhancement and not edition_text and not seal_text:
            notes.append("vanilla playing card; small rank-only value before build context")
        return PackActionScore(action, score, tuple(notes))
