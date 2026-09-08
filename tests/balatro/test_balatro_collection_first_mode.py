from types import SimpleNamespace

from games.balatro.actions import (
    BUY_BOOSTER,
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    SELECT_PACK_CARD,
    SELL_CONSUMABLE,
    SELL_JOKER,
    SKIP_BOOSTER,
    BalatroAction,
)
from games.balatro.collection_mode import (
    COLLECTION_CRITICAL,
    COLLECTION_PROGRESS,
    CollectionFirstPackPolicy,
    CollectionFirstPolicy,
)
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import PackActionScore
from games.balatro.state import BalatroState


def _item(label, *, cost=3, discovered=False, kind=None, edition=None):
    return SimpleNamespace(
        label=label,
        cost=cost,
        discovered=discovered,
        kind=kind,
        edition=edition,
        area_index=0,
    )


def _shop_state(*, money=20, ante=8):
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.ante = ante
    state.shop_jokers = []
    state.shop_consumables = []
    state.shop_vouchers = []
    state.shop_boosters = []
    return state


class _SalePolicy:
    def __init__(self, options):
        self.options = tuple(options)

    def decide(self, _state):
        return SimpleNamespace(options=self.options)


def _sale_option(index, *, loss, blocked=None, edition_penalty=0.0):
    return SimpleNamespace(
        joker_index=index,
        joker=f"joker-{index}",
        build_loss=loss,
        edition_penalty=edition_penalty,
        blocked_reason=blocked,
    )


def test_visible_undiscovered_joker_overrides_late_bond_strategy_commitment():
    state = _shop_state(ante=8)
    unknown = _item("Undiscovered", cost=6, kind="JOKER")
    state.shop_jokers = [unknown]

    recommendation = CollectionFirstPolicy().recommend_shop(state)

    assert recommendation is not None
    assert recommendation.priority == COLLECTION_CRITICAL
    assert recommendation.action.name == BUY_JOKER
    assert recommendation.action.target is unknown
    assert "Bond/composition strategy" in " ".join(recommendation.rationale)


def test_full_joker_area_sells_lowest_loss_eligible_nonnegative_joker_first():
    state = _shop_state()
    state.joker_slots = 3
    state.jokers = [
        _item("Eternal", edition=None),
        _item("Negative", edition="Negative"),
        _item("Ordinary", edition=None),
    ]
    state.shop_jokers = [_item("Undiscovered", cost=4, kind="JOKER")]
    sale_policy = _SalePolicy(
        (
            _sale_option(0, loss=0.0, blocked="Eternal Joker cannot be sold"),
            _sale_option(1, loss=0.0),
            _sale_option(2, loss=9.0),
        )
    )

    recommendation = CollectionFirstPolicy(
        joker_sale_policy=sale_policy,
    ).recommend_shop(state)

    assert recommendation is not None
    assert recommendation.action.name == SELL_JOKER
    assert recommendation.action.target == 2


def test_unknown_consumable_replaces_lowest_retention_consumable_when_full():
    state = _shop_state()
    state.consumable_slots = 2
    state.consumables = [_item("Keep"), _item("Discard")]
    state.shop_consumables = [_item("Unknown Tarot", cost=3)]

    class _Estimator:
        def estimate(self, _state, action):
            return ({"Keep": 5.0, "Discard": 1.0}[action.target.label], ())

    recommendation = CollectionFirstPolicy(
        item_estimator=_Estimator(),
    ).recommend_shop(state)

    assert recommendation is not None
    assert recommendation.action.name == SELL_CONSUMABLE
    assert recommendation.action.target == 1


def test_unknown_consumable_is_bought_after_capacity_is_available():
    state = _shop_state()
    unknown = _item("Unknown Tarot", cost=3)
    state.shop_consumables = [unknown]

    recommendation = CollectionFirstPolicy().recommend_shop(state)

    assert recommendation is not None
    assert recommendation.action.name == BUY_CONSUMABLE
    assert recommendation.action.target is unknown


def test_unknown_voucher_and_booster_override_ordinary_run_economy():
    state = _shop_state(money=10)
    voucher = _item("Unknown Voucher", cost=10, kind="VOUCHER")
    booster = _item("Unknown Pack", cost=4, kind="BOOSTER")
    state.shop_vouchers = [voucher]
    state.shop_boosters = [booster]

    recommendation = CollectionFirstPolicy().recommend_shop(state)

    assert recommendation is not None
    assert recommendation.priority == COLLECTION_CRITICAL
    assert recommendation.action.name == BUY_BOOSTER
    assert recommendation.action.target is booster


def test_known_voucher_and_booster_still_create_collection_progress():
    state = _shop_state()
    voucher = _item("Known Voucher", cost=10, discovered=True, kind="VOUCHER")
    state.shop_vouchers = [voucher]

    recommendation = CollectionFirstPolicy().recommend_shop(state)

    assert recommendation is not None
    assert recommendation.priority == COLLECTION_PROGRESS
    assert recommendation.action.name == BUY_VOUCHER

    state.shop_vouchers = []
    booster = _item("Arcana Pack", cost=4, discovered=True, kind="BOOSTER")
    state.shop_boosters = [booster]
    recommendation = CollectionFirstPolicy().recommend_shop(state)

    assert recommendation is not None
    assert recommendation.priority == COLLECTION_PROGRESS
    assert recommendation.action.name == BUY_BOOSTER


def test_missing_discovery_bit_cannot_authorize_a_destructive_replacement():
    state = _shop_state()
    state.joker_slots = 1
    state.jokers = [_item("Owned")]
    state.shop_jokers = [_item("Unobserved", discovered=None, kind="JOKER")]
    policy = CollectionFirstPolicy(
        joker_sale_policy=_SalePolicy((_sale_option(0, loss=0.0),)),
    )

    assert policy.recommend_shop(state) is None


class _PackDelegate:
    def rank_actions(self, _state, actions):
        scores = {
            "Known": 100.0,
            "Unknown": -10.0,
            "SKIP": 1.0,
        }
        return sorted(
            (
                PackActionScore(
                    action=action,
                    total=scores.get(
                        getattr(action.target, "label", None),
                        scores["SKIP"],
                    ),
                )
                for action in actions
            ),
            key=lambda score: -score.total,
        )


def _pack_choice(label, *, discovered, kind="JOKER"):
    return LivePackChoice(
        area_index=0,
        address=1,
        data={
            "label": label,
            "ability_set": kind,
            "discovered": discovered,
        },
    )


def test_unknown_pack_choice_outranks_a_much_stronger_known_choice():
    state = BalatroState()
    state.phase = "BUFFOON_PACK"
    unknown = _pack_choice("Unknown", discovered=False)
    known = _pack_choice("Known", discovered=True)
    actions = [
        BalatroAction(SELECT_PACK_CARD, target=known),
        BalatroAction(SELECT_PACK_CARD, target=unknown),
        BalatroAction(SKIP_BOOSTER),
    ]
    policy = CollectionFirstPackPolicy(
        _PackDelegate(),
        collection_policy=CollectionFirstPolicy(),
    )

    ranked = policy.rank_actions(state, actions)

    assert ranked[0].action.target is unknown
    assert "COLLECTION_CRITICAL" in " ".join(ranked[0].notes)


def test_full_pack_joker_choice_emits_a_sale_before_selection():
    state = BalatroState()
    state.phase = "BUFFOON_PACK"
    state.joker_slots = 1
    state.jokers = [_item("Owned")]
    unknown = _pack_choice("Unknown", discovered=False)
    sale_policy = _SalePolicy((_sale_option(0, loss=3.0),))
    policy = CollectionFirstPackPolicy(
        _PackDelegate(),
        collection_policy=CollectionFirstPolicy(joker_sale_policy=sale_policy),
    )

    ranked = policy.rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=unknown),
            BalatroAction(SKIP_BOOSTER),
        ],
    )

    assert len(ranked) == 1
    assert ranked[0].action.name == SELL_JOKER
    assert ranked[0].action.target == 0


def test_targeted_collection_tarot_without_hand_targets_is_not_ranked():
    state = BalatroState()
    state.phase = "TAROT_PACK"
    targeted = _pack_choice("The Devil", discovered=False, kind="Tarot")
    known = _pack_choice("Known", discovered=True, kind="Tarot")
    policy = CollectionFirstPackPolicy(
        _PackDelegate(),
        collection_policy=CollectionFirstPolicy(),
    )

    ranked = policy.rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=targeted),
            BalatroAction(SELECT_PACK_CARD, target=known),
            BalatroAction(SKIP_BOOSTER),
        ],
    )

    assert all(score.action.target is not targeted for score in ranked)
    assert ranked[0].action.target is known


def test_targeted_collection_tarot_with_hand_targets_remains_critical():
    state = BalatroState()
    state.phase = "TAROT_PACK"
    targeted = _pack_choice("The Devil", discovered=False, kind="Tarot")
    known = _pack_choice("Known", discovered=True, kind="Tarot")
    target_card = SimpleNamespace(rank="Ace", suit="Spades")
    policy = CollectionFirstPackPolicy(
        _PackDelegate(),
        collection_policy=CollectionFirstPolicy(),
    )

    ranked = policy.rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=targeted, cards=(target_card,)),
            BalatroAction(SELECT_PACK_CARD, target=known),
            BalatroAction(SKIP_BOOSTER),
        ],
    )

    assert ranked[0].action.target is targeted
    assert ranked[0].action.cards == (target_card,)
    assert "COLLECTION_CRITICAL" in " ".join(ranked[0].notes)


def test_undiscovered_cryptid_without_hand_target_is_never_collection_critical():
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    cryptid = _pack_choice("Cryptid", discovered=False, kind="Spectral")
    known = _pack_choice("Known", discovered=True, kind="Spectral")
    policy = CollectionFirstPackPolicy(
        _PackDelegate(),
        collection_policy=CollectionFirstPolicy(),
    )

    ranked = policy.rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=cryptid),
            BalatroAction(SELECT_PACK_CARD, target=known),
            BalatroAction(SKIP_BOOSTER),
        ],
    )

    assert all(score.action.target is not cryptid for score in ranked)
