from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import (
    BUY_CONSUMABLE,
    BUY_JOKER,
    SELECT_PACK_CARD,
    SKIP_BOOSTER,
    BalatroAction,
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
    immediately. Tarot/Spectral cards that can require another selection step are
    deliberately scored below Skip until those follow-up UI actions are implemented.
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
    ) -> None:
        self.skip_bias = float(skip_bias)
        self.item_estimator = item_estimator or DefaultShopItemValueEstimator()
        self.joker_factory = joker_factory or LiveJokerFactory()
        self.consumable_factory = consumable_factory or LiveConsumableFactory()
        self.fallback_factory = fallback_factory or LiveShopItemFactory()

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
            return self._score_playing_card(action, choice)
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
            return PackActionScore(
                action,
                -1.0,
                ("Tarot requires unsupported follow-up selection or is not yet classified safe",),
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

    def _score_playing_card(self, action, choice: LivePackChoice) -> PackActionScore:
        value = choice.data.get("value") or {}
        modifier = choice.data.get("modifier") or {}
        score = self.RANK_VALUE.get(str(value.get("rank")), 0.0)
        notes: list[str] = []

        enhancement = str(modifier.get("enhancement") or "")
        if enhancement:
            amount = self.PLAYING_ENHANCEMENT_VALUE.get(enhancement, 0.0)
            score += amount
            notes.append(f"enhancement={enhancement} value={amount:.2f}")

        edition = str(modifier.get("edition") or "").upper()
        if edition:
            amount = self.EDITION_BONUS.get(edition, 0.0)
            score += amount
            notes.append(f"edition={edition} value={amount:.2f}")

        seal = str(modifier.get("seal") or "").upper()
        if seal:
            amount = self.PLAYING_SEAL_VALUE.get(seal, 0.0)
            score += amount
            notes.append(f"seal={seal} value={amount:.2f}")

        if not notes:
            notes.append("vanilla playing card; small rank-only value")
        return PackActionScore(action, score, tuple(notes))
