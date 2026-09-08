from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import (
    BUY_BOOSTER,
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_SHOP,
    SELECT_PACK_CARD,
    SELL_CONSUMABLE,
    SELL_JOKER,
    BalatroAction,
)
from games.balatro.build import ContextualConsumableTargetEvaluator
from games.balatro.discovery import is_undiscovered
from games.balatro.joker_edition import joker_has_negative_edition
from games.balatro.joker_sale_policy import JokerSalePolicy
from games.balatro.pack_policy import PackActionScore


COLLECTION_CRITICAL = "COLLECTION_CRITICAL"
COLLECTION_PROGRESS = "COLLECTION_PROGRESS"


@dataclass(frozen=True)
class CollectionFirstRecommendation:
    action: BalatroAction
    priority: str
    target_kind: str
    target_label: str
    rationale: tuple[str, ...]


class CollectionFirstPolicy:
    """Hard, opt-in profile-progression priority over ordinary run utility.

    Only an explicit public ``discovered=false`` bit creates critical priority.
    Missing collection state remains unknown and cannot authorize a destructive
    sale. Transactions remain one action per authoritative checkpoint: a required
    sale is emitted first, and the still-visible offer is bought only after a fresh
    settled SHOP/PACK observation.
    """

    _FAMILY_ORDER = {
        "JOKER": 0,
        "CONSUMABLE": 1,
        "VOUCHER": 2,
        "BOOSTER": 3,
    }
    _BOOSTER_OPPORTUNITY_ORDER = {
        "SPECTRAL": 0,
        "ARCANA": 1,
        "BUFFOON": 2,
        "CELESTIAL": 3,
        "STANDARD": 4,
    }

    def __init__(
        self,
        *,
        joker_sale_policy: JokerSalePolicy | None = None,
        item_estimator=None,
    ) -> None:
        self.joker_sale_policy = joker_sale_policy or JokerSalePolicy()
        self.item_estimator = item_estimator

    def recommend_shop(self, state) -> CollectionFirstRecommendation | None:
        if str(getattr(state, "phase", "")) != "SHOP":
            return None

        critical: list[tuple[tuple[int, int, int, int], CollectionFirstRecommendation]] = []
        observed_undiscovered = False

        for candidate in getattr(state, "shop_jokers", ()):
            if not is_undiscovered(candidate):
                continue
            observed_undiscovered = True
            price = self._price(candidate)
            if int(getattr(state, "money", 0)) < price:
                continue
            if (
                len(getattr(state, "jokers", ())) < int(getattr(state, "joker_slots", 0))
                or joker_has_negative_edition(candidate)
            ):
                recommendation = self._buy(
                    BUY_JOKER,
                    candidate,
                    kind="JOKER",
                    price=price,
                )
                sale_step = 0
            else:
                recommendation = self.joker_sale_for_collection(
                    state,
                    target_label=self._label(candidate),
                    phase="SHOP",
                )
                sale_step = 1
                if recommendation is None:
                    continue
            critical.append(
                (
                    self._critical_key(candidate, price=price, sale_step=sale_step),
                    recommendation,
                )
            )

        for candidate in getattr(state, "shop_consumables", ()):
            if not is_undiscovered(candidate):
                continue
            observed_undiscovered = True
            price = self._price(candidate)
            if int(getattr(state, "money", 0)) < price:
                continue
            if len(getattr(state, "consumables", ())) < int(
                getattr(state, "consumable_slots", 0)
            ):
                recommendation = self._buy(
                    BUY_CONSUMABLE,
                    candidate,
                    kind="CONSUMABLE",
                    price=price,
                )
                sale_step = 0
            else:
                recommendation = self.consumable_sale_for_collection(
                    state,
                    target_label=self._label(candidate),
                )
                sale_step = 1
                if recommendation is None:
                    continue
            critical.append(
                (
                    self._critical_key(candidate, price=price, sale_step=sale_step),
                    recommendation,
                )
            )

        for kind, action_name, candidates in (
            ("VOUCHER", BUY_VOUCHER, getattr(state, "shop_vouchers", ())),
            ("BOOSTER", BUY_BOOSTER, getattr(state, "shop_boosters", ())),
        ):
            for candidate in candidates:
                if not is_undiscovered(candidate):
                    continue
                observed_undiscovered = True
                price = self._price(candidate)
                if int(getattr(state, "money", 0)) < price:
                    continue
                recommendation = self._buy(
                    action_name,
                    candidate,
                    kind=kind,
                    price=price,
                )
                critical.append(
                    (
                        self._critical_key(candidate, price=price, sale_step=0),
                        recommendation,
                    )
                )

        if critical:
            return min(critical, key=lambda item: item[0])[1]

        if observed_undiscovered:
            return CollectionFirstRecommendation(
                action=BalatroAction(END_SHOP),
                priority=COLLECTION_CRITICAL,
                target_kind="COLLECTION",
                target_label="unaffordable or capacity-blocked discovery",
                rationale=(
                    "collection-first mode observed an explicitly undiscovered offer",
                    "no legal affordable discovery transaction is currently available",
                    "preserve the offer and remaining money instead of spending on lower-priority progress",
                ),
            )

        affordable_vouchers = [
            voucher
            for voucher in getattr(state, "shop_vouchers", ())
            if int(getattr(state, "money", 0)) >= self._price(voucher)
        ]
        if affordable_vouchers:
            voucher = min(
                affordable_vouchers,
                key=lambda item: (self._price(item), self._area_index(item)),
            )
            return CollectionFirstRecommendation(
                action=BalatroAction(BUY_VOUCHER, target=voucher),
                priority=COLLECTION_PROGRESS,
                target_kind="VOUCHER",
                target_label=self._label(voucher),
                rationale=(
                    "collection-first mode buys visible Vouchers after critical discoveries",
                    "redeeming base or repeated Vouchers can advance profile unlock requirements",
                    f"price=${self._price(voucher)}",
                ),
            )

        affordable_boosters = [
            booster
            for booster in getattr(state, "shop_boosters", ())
            if int(getattr(state, "money", 0)) >= self._price(booster)
        ]
        if affordable_boosters:
            booster = min(
                affordable_boosters,
                key=lambda item: (
                    self._booster_opportunity_rank(item),
                    self._price(item),
                    self._area_index(item),
                ),
            )
            return CollectionFirstRecommendation(
                action=BalatroAction(BUY_BOOSTER, target=booster),
                priority=COLLECTION_PROGRESS,
                target_kind="BOOSTER",
                target_label=self._label(booster),
                rationale=(
                    "collection-first mode opens available boosters to expose missing collection entries",
                    f"booster opportunity rank={self._booster_opportunity_rank(booster)}",
                    f"price=${self._price(booster)}",
                ),
            )

        return None

    def joker_sale_for_collection(
        self,
        state,
        *,
        target_label: str,
        phase: str,
    ) -> CollectionFirstRecommendation | None:
        decision = self.joker_sale_policy.decide(state)
        candidates = []
        for option in decision.options:
            index = int(option.joker_index)
            if not (0 <= index < len(getattr(state, "jokers", ()))):
                continue
            joker = state.jokers[index]
            if option.blocked_reason is not None or joker_has_negative_edition(joker):
                continue
            candidates.append(option)
        if not candidates:
            return None

        selected = min(
            candidates,
            key=lambda option: (
                float(option.build_loss) + float(option.edition_penalty),
                float(option.build_loss),
                int(option.joker_index),
            ),
        )
        return CollectionFirstRecommendation(
            action=BalatroAction(SELL_JOKER, target=int(selected.joker_index)),
            priority=COLLECTION_CRITICAL,
            target_kind="JOKER",
            target_label=target_label,
            rationale=(
                "collection-first discovery requires a free Joker slot",
                f"phase={phase}",
                f"sell slot {selected.joker_index} {selected.joker}",
                f"retained-value loss={selected.build_loss:.3f}",
                "Eternal and Negative Jokers are ineligible capacity targets",
                "buy is deferred until a fresh authoritative checkpoint after the sale",
            ),
        )

    def consumable_sale_for_collection(
        self,
        state,
        *,
        target_label: str,
    ) -> CollectionFirstRecommendation | None:
        consumables = list(getattr(state, "consumables", ()))
        if not consumables:
            return None

        def retention(index_item):
            index, item = index_item
            if self.item_estimator is None:
                value = 0.0
            else:
                try:
                    value, _ = self.item_estimator.estimate(
                        state,
                        BalatroAction(BUY_CONSUMABLE, target=item),
                    )
                except (RuntimeError, TypeError, ValueError):
                    value = 0.0
            return float(value), index

        index, item = min(enumerate(consumables), key=retention)
        return CollectionFirstRecommendation(
            action=BalatroAction(SELL_CONSUMABLE, target=index),
            priority=COLLECTION_CRITICAL,
            target_kind="CONSUMABLE",
            target_label=target_label,
            rationale=(
                "collection-first discovery requires a free consumable slot",
                f"sell slot {index} {self._label(item)}",
                "buy is deferred until a fresh authoritative checkpoint after the sale",
            ),
        )

    def _buy(self, action_name: str, target, *, kind: str, price: int):
        return CollectionFirstRecommendation(
            action=BalatroAction(action_name, target=target),
            priority=COLLECTION_CRITICAL,
            target_kind=kind,
            target_label=self._label(target),
            rationale=(
                "collection-first mode observed explicit discovered=false",
                "COLLECTION_CRITICAL outranks Bond/composition strategy, economy, and win probability",
                f"kind={kind}",
                f"price=${price}",
            ),
        )

    def _critical_key(self, item, *, price: int, sale_step: int):
        kind = self._kind(item)
        return (
            int(price),
            int(sale_step),
            self._FAMILY_ORDER.get(kind, 99),
            self._area_index(item),
        )

    @staticmethod
    def _price(item) -> int:
        value = getattr(item, "price", getattr(item, "cost", 0))
        if isinstance(value, dict):
            value = value.get("buy", 0)
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _area_index(item) -> int:
        value = getattr(item, "area_index", 10**9)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 10**9

    @staticmethod
    def _label(item) -> str:
        value = getattr(item, "label", getattr(item, "name", type(item).__name__))
        return str(value or type(item).__name__)

    @staticmethod
    def _kind(item) -> str:
        value = getattr(item, "kind", None)
        if value:
            return str(value).upper()
        name = type(item).__name__.upper()
        if "JOKER" in name:
            return "JOKER"
        if "VOUCHER" in name:
            return "VOUCHER"
        if "BOOSTER" in name or "PACK" in name:
            return "BOOSTER"
        return "CONSUMABLE"

    def _booster_opportunity_rank(self, item) -> int:
        label = self._label(item).upper()
        for family, rank in self._BOOSTER_OPPORTUNITY_ORDER.items():
            if family in label:
                return rank
        return 99


class CollectionFirstPackPolicy:
    """Lexicographically place legal discovery choices before ordinary scores."""

    _FREE_JOKER_SLOT_LABELS = frozenset(
        {"The Soul", "Judgement", "Wraith"}
    )
    _TARGETED_LABELS = frozenset(
        {
            *ContextualConsumableTargetEvaluator.SUPPORTED_TAROTS,
            *ContextualConsumableTargetEvaluator.SUPPORTED_SPECTRALS,
            "Aura",
            "Cryptid",
        }
    )

    def __init__(self, delegate, *, collection_policy: CollectionFirstPolicy) -> None:
        self.delegate = delegate
        self.collection_policy = collection_policy

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    def rank_actions(self, state, actions: list[BalatroAction]):
        full = len(getattr(state, "jokers", ())) >= int(
            getattr(state, "joker_slots", 0)
        )
        capacity_blocked = [
            action
            for action in actions
            if action.name == SELECT_PACK_CARD
            and self._collection_priority(action.target)
            and self._requires_free_joker_slot(action.target)
            and full
        ]
        if capacity_blocked:
            target = capacity_blocked[0].target
            sale = self.collection_policy.joker_sale_for_collection(
                state,
                target_label=CollectionFirstPolicy._label(target),
                phase=str(getattr(state, "phase", "PACK")),
            )
            if sale is not None:
                return [
                    PackActionScore(
                        action=sale.action,
                        total=0.0,
                        notes=sale.rationale,
                    )
                ]

        scoreable_actions = [
            action
            for action in actions
            if not (
                action.name == SELECT_PACK_CARD
                and (
                    (self._requires_free_joker_slot(action.target) and full)
                    or not self._is_executable_targeted_action(action)
                )
            )
        ]
        ranked = list(self.delegate.rank_actions(state, scoreable_actions))
        critical = []
        ordinary = []
        for score in ranked:
            action = score.action
            if (
                action.name == SELECT_PACK_CARD
                and self._collection_priority(action.target)
                and self._is_executable_targeted_action(action)
            ):
                critical.append(
                    PackActionScore(
                        action=action,
                        total=float(score.total),
                        notes=(
                            "COLLECTION_CRITICAL visible pack choice overrides ordinary pack utility",
                            *score.notes,
                        ),
                    )
                )
            else:
                ordinary.append(score)
        return critical + ordinary

    def _collection_priority(self, target) -> bool:
        return is_undiscovered(target) or CollectionFirstPolicy._label(target) == "The Soul"

    def _requires_free_joker_slot(self, target) -> bool:
        kind = str(getattr(target, "kind", "")).upper()
        label = CollectionFirstPolicy._label(target)
        return kind == "JOKER" or label in self._FREE_JOKER_SLOT_LABELS

    def _is_executable_targeted_action(self, action: BalatroAction) -> bool:
        label = CollectionFirstPolicy._label(action.target)
        return label not in self._TARGETED_LABELS or bool(action.cards)
