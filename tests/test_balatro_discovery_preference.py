from math import inf, nextafter
from types import SimpleNamespace

from games.balatro.actions import (
    BUY_VOUCHER,
    END_SHOP,
    SELECT_PACK_CARD,
    SKIP_BOOSTER,
    BalatroAction,
)
from games.balatro.discovery import (
    bounded_discovery_tiebreak,
    discovery_status,
    is_undiscovered,
)
from games.balatro.live.consumable_factory import LiveConsumableFactory
from games.balatro.live.external.live_memory_observer import _normalize_item
from games.balatro.live.external.luajit_memory import LuaValue
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.live.pack import LivePackChoice
from games.balatro.live.shop import LiveShopItem, LiveShopItemFactory
from games.balatro.pack_policy import PackActionScore
from games.balatro.playbook_pack_policy import PlaybookBalatroPackPolicy
from games.balatro.playbook_shop_policy import (
    PlaybookBuildAwareShopArbiter,
    PlaybookVoucherAwareBalatroShopPolicy,
)
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.shop_reroll_policy import ShopRerollRecommendation
from games.balatro.shop_utility_scale import ShopUtilityScale
from games.balatro.state import BalatroState


class _Decoder:
    def __init__(self, tables):
        self.tables = tables

    def string_fields(self, address):
        return self.tables[address]


def _table(address):
    return LuaValue("table", address, 0)


def _string(value):
    return LuaValue("string", value, 0)


def _integer(value):
    return LuaValue("integer", int(value), 0)


def _boolean(value):
    return LuaValue("boolean", bool(value), 0)


def _shop_state(*, money: int = 30) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.joker_slots = 5
    state.shop_jokers = []
    state.shop_consumables = []
    state.shop_boosters = []
    state.shop_vouchers = []
    return state


def test_live_memory_exposes_only_explicit_center_discovery_status():
    CARD = 100
    ABILITY = 101
    CONFIG = 102
    CENTER = 103
    decoder = _Decoder(
        {
            CARD: {
                "ability": _table(ABILITY),
                "config": _table(CONFIG),
                "sort_id": _integer(7),
                "cost": _integer(3),
            },
            ABILITY: {
                "name": _string("The Hermit"),
                "set": _string("Tarot"),
            },
            CONFIG: {"center": _table(CENTER)},
            CENTER: {
                "key": _string("c_hermit"),
                "name": _string("The Hermit"),
                "set": _string("Tarot"),
                "discovered": _boolean(False),
            },
        }
    )

    item = _normalize_item(decoder, CARD, area_index=0)

    assert item["discovered"] is False
    assert item["label"] == "The Hermit"

    decoder.tables[CENTER].pop("discovered")
    unknown = _normalize_item(decoder, CARD, area_index=0)
    assert "discovered" not in unknown


def test_live_factories_preserve_explicit_discovery_status():
    fallback = LiveShopItemFactory().create(
        {
            "label": "Paint Brush",
            "ability_set": "Voucher",
            "cost": 10,
            "discovered": False,
        },
        kind="VOUCHER",
    )
    joker = LiveJokerFactory().create(
        {
            "label": "Joker",
            "center": "j_joker",
            "discovered": False,
        }
    )
    consumable = LiveConsumableFactory().create(
        {
            "label": "The Hermit",
            "discovered": False,
        }
    )

    assert fallback is not None and fallback.discovered is False
    assert joker is not None and joker.discovered is False
    assert consumable is not None and consumable.discovered is False


def test_discovery_tiebreak_is_exactly_one_ulp_and_never_rescues_zero_gain():
    undiscovered = SimpleNamespace(discovered=False)
    known = SimpleNamespace(discovered=True)

    assert discovery_status(undiscovered) is False
    assert is_undiscovered(undiscovered) is True
    assert bounded_discovery_tiebreak(1.0, undiscovered) == nextafter(1.0, inf)
    assert bounded_discovery_tiebreak(1.0, known) == 1.0
    assert bounded_discovery_tiebreak(0.0, undiscovered) == 0.0
    assert bounded_discovery_tiebreak(-1.0, undiscovered) == -1.0


class _FixedJokerPolicy:
    def decide(self, state, candidate):
        del state
        gain = float(candidate.build_gain)
        selected = SimpleNamespace(
            total_advantage=gain,
            replace_index=None,
            build_gain=gain,
            economics=SimpleNamespace(
                net_spend=0,
                edition_delta=0.0,
            ),
            rationale=(),
        )
        return SimpleNamespace(
            action="BUY",
            selected=selected,
            rationale=(),
        )


class _HoldRerollPolicy:
    def recommend(
        self,
        state,
        visible_actions,
        *,
        reroll_cost,
        visible_score_floor=None,
    ):
        del state, visible_actions, visible_score_floor
        return ShopRerollRecommendation(
            decision="HOLD",
            reroll_cost=reroll_cost,
            executable_action=None,
            current_best_score=0.0,
            future_shop_ev=float("-inf"),
            reroll_resource_cost=float("inf"),
            reroll_score=float("-inf"),
        )


def _shop_arbiter() -> PlaybookBuildAwareShopArbiter:
    shop_policy = BalatroShopPolicy(
        price_weight=0.0,
        interest_weight=0.0,
        reserve_weight=0.0,
        last_joker_slot_penalty=0.0,
        penultimate_joker_slot_penalty=0.0,
    )
    return PlaybookBuildAwareShopArbiter(
        shop_policy=shop_policy,
        joker_policy=_FixedJokerPolicy(),
        reroll_policy=_HoldRerollPolicy(),
    )


def test_shop_prefers_undiscovered_joker_only_on_exact_positive_tie():
    state = _shop_state()
    known = SimpleNamespace(
        label="known",
        discovered=True,
        build_gain=1.0,
        edition=None,
    )
    undiscovered = SimpleNamespace(
        label="undiscovered",
        discovered=False,
        build_gain=1.0,
        edition=None,
    )
    state.shop_jokers = [known, undiscovered]

    decision = _shop_arbiter().decide(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=None,
    )

    assert decision.source == "JOKER_BUY"
    assert decision.action.target is undiscovered


def test_shop_discovery_preference_cannot_override_stronger_build_value():
    state = _shop_state()
    stronger_known = SimpleNamespace(
        label="stronger",
        discovered=True,
        build_gain=1.001,
        edition=None,
    )
    weaker_undiscovered = SimpleNamespace(
        label="weaker undiscovered",
        discovered=False,
        build_gain=1.0,
        edition=None,
    )
    state.shop_jokers = [weaker_undiscovered, stronger_known]

    decision = _shop_arbiter().decide(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=None,
    )

    assert decision.action.target is stronger_known


def test_shop_discovery_preference_cannot_turn_zero_gain_into_a_purchase():
    state = _shop_state()
    state.shop_jokers = [
        SimpleNamespace(
            label="zero gain",
            discovered=False,
            build_gain=0.0,
            edition=None,
        )
    ]

    decision = _shop_arbiter().decide(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=None,
    )

    assert decision.source == "END_SHOP"
    assert decision.action.name == END_SHOP


def test_discovery_preference_does_not_bias_destructive_replacement_step():
    state = _shop_state()
    candidate = SimpleNamespace(discovered=False, edition=None)
    selected = SimpleNamespace(
        build_gain=1.0,
        economics=SimpleNamespace(net_spend=0, edition_delta=0.0),
    )
    executable = SimpleNamespace(
        source="JOKER_REPLACE_SELL",
        candidate=candidate,
        decision=SimpleNamespace(selected=selected),
    )
    scale = ShopUtilityScale(
        BalatroShopPolicy(
            price_weight=0.0,
            interest_weight=0.0,
            reserve_weight=0.0,
        )
    )

    assert scale.joker_gain(state, executable).gain == 1.0


def test_undiscovered_voucher_cannot_rescue_a_rejected_d3_purchase():
    state = _shop_state(money=30)
    useful = LiveShopItem(
        kind="VOUCHER",
        label="Paint Brush",
        price=10,
        discovered=True,
    )
    blank = LiveShopItem(
        kind="VOUCHER",
        label="Blank",
        price=10,
        discovered=False,
    )
    ranked = PlaybookVoucherAwareBalatroShopPolicy().rank_actions(
        state,
        [
            BalatroAction(BUY_VOUCHER, target=blank),
            BalatroAction(BUY_VOUCHER, target=useful),
            BalatroAction(END_SHOP),
        ],
    )

    assert ranked[0].action.target is useful
    assert all(result.action.target is not blank for result in ranked)


class _FixedPackPolicy(PlaybookBalatroPackPolicy):
    def score_action(self, state, action):
        del state
        if action.name == SKIP_BOOSTER:
            return PackActionScore(action, 0.35, ("fixed skip",))
        return PackActionScore(
            action,
            float(action.target.data["test_score"]),
            ("fixed visible pack score",),
        )


def _choice(label: str, *, score: float, discovered: bool) -> LivePackChoice:
    return LivePackChoice(
        area_index=0,
        address=0x1000,
        data={
            "label": label,
            "ability_name": label,
            "ability_set": "Tarot",
            "discovered": discovered,
            "test_score": score,
        },
    )


def test_pack_prefers_undiscovered_choice_only_on_exact_value_tie():
    state = BalatroState()
    state.phase = "TAROT_PACK"
    known = _choice("known", score=1.0, discovered=True)
    undiscovered = _choice("undiscovered", score=1.0, discovered=False)

    ranked = _FixedPackPolicy().rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=known),
            BalatroAction(SELECT_PACK_CARD, target=undiscovered),
            BalatroAction(SKIP_BOOSTER),
        ],
    )

    assert ranked[0].action.target is undiscovered


def test_pack_discovery_preference_cannot_override_higher_choice_value():
    state = BalatroState()
    state.phase = "TAROT_PACK"
    stronger_known = _choice("stronger", score=1.001, discovered=True)
    weaker_undiscovered = _choice("weaker", score=1.0, discovered=False)

    ranked = _FixedPackPolicy().rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=weaker_undiscovered),
            BalatroAction(SELECT_PACK_CARD, target=stronger_known),
            BalatroAction(SKIP_BOOSTER),
        ],
    )

    assert ranked[0].action.target is stronger_known
