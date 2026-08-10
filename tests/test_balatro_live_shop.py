from games.balatro.actions import (
    BalatroAction,
    BUY_BOOSTER,
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_SHOP,
    REFRESH_SHOP,
)
from games.balatro.jokers.rough_gem import RoughGemJoker
from games.balatro.live import (
    DefaultBalatroActionExecutor,
    DefaultBalatroStateTranslator,
    LiveBalatroSnapshot,
)
from games.balatro.live.shop import BalatroShopActionGenerator, LiveShopItem
from games.balatro.live.shop_sync import (
    BufferedShopTransaction,
    UnsupportedBufferedShopAction,
)


def test_shop_buy_action_uses_balatrobot_index():
    executor = DefaultBalatroActionExecutor()
    snapshot = LiveBalatroSnapshot(
        sequence=9,
        phase="SHOP",
        state_complete=True,
    )

    command = executor.command_for(
        BalatroAction(
            BUY_JOKER,
            target={"id": 1},
        ),
        snapshot,
    )

    assert command.action == BUY_JOKER
    assert command.payload == {
        "target": 1
    }


def test_shop_control_actions_require_no_target():
    executor = DefaultBalatroActionExecutor()
    snapshot = LiveBalatroSnapshot(
        sequence=10,
        phase="SHOP",
        state_complete=True,
    )

    reroll = executor.command_for(
        BalatroAction(REFRESH_SHOP),
        snapshot,
    )
    end_shop = executor.command_for(
        BalatroAction(END_SHOP),
        snapshot,
    )

    assert reroll.payload == {}
    assert end_shop.payload == {}


def _structured_shop_snapshot() -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=12,
        phase="SHOP",
        state_complete=False,
        payload={
            "money": 10,
            "jokers": {
                "count": 0,
                "limit": 5,
                "cards": [],
            },
            "consumables": {
                "count": 0,
                "limit": 2,
                "cards": [],
            },
            "shop_jokers": {
                "count": 2,
                "limit": 2,
                "cards": [
                    {
                        "live_id": 101,
                        "center": "j_rough_gem",
                        "label": "Rough Gem",
                        "ability_name": "Rough Gem",
                        "ability_set": "Joker",
                        "cost": 7,
                    },
                    {
                        "live_id": 102,
                        "center": "c_strength",
                        "label": "Strength",
                        "ability_name": "Strength",
                        "ability_set": "Tarot",
                        "cost": 3,
                    },
                ],
            },
            "shop_boosters": {
                "count": 1,
                "limit": 2,
                "cards": [
                    {
                        "live_id": 201,
                        "center": "p_celestial_normal_4",
                        "label": "Celestial Pack",
                        "ability_set": "Booster",
                        "cost": 4,
                    }
                ],
            },
            "shop_vouchers": {
                "count": 1,
                "limit": 1,
                "cards": [
                    {
                        "live_id": 301,
                        "center": "v_crystal_ball",
                        "label": "Crystal Ball",
                        "ability_set": "Voucher",
                        "cost": 10,
                    }
                ],
            },
        },
    )


def test_translator_maps_structured_save_shop_inventory():
    state = DefaultBalatroStateTranslator().translate(
        _structured_shop_snapshot()
    )

    assert state.shop_active
    assert state.joker_slots == 5

    assert len(state.shop_jokers) == 1
    assert isinstance(state.shop_jokers[0], RoughGemJoker)
    assert state.shop_jokers[0].live_id == 101
    assert state.shop_jokers[0].cost == 7

    assert len(state.shop_consumables) == 1
    assert state.shop_consumables[0].name == "Strength"
    assert state.shop_consumables[0].live_id == 102
    assert state.shop_consumables[0].price == 3

    assert state.shop_boosters == [
        LiveShopItem(
            kind="BOOSTER",
            label="Celestial Pack",
            price=4,
            live_id=201,
            center="p_celestial_normal_4",
        )
    ]
    assert state.shop_vouchers == [
        LiveShopItem(
            kind="VOUCHER",
            label="Crystal Ball",
            price=10,
            live_id=301,
            center="v_crystal_ball",
        )
    ]


def test_shop_action_generator_uses_observable_affordable_offers():
    state = DefaultBalatroStateTranslator().translate(
        _structured_shop_snapshot()
    )

    actions = BalatroShopActionGenerator().generate_actions(state)

    assert [action.name for action in actions] == [
        BUY_JOKER,
        BUY_CONSUMABLE,
        BUY_VOUCHER,
        BUY_BOOSTER,
        END_SHOP,
    ]
    assert [
        getattr(action.target, "live_id", None)
        for action in actions[:-1]
    ] == [101, 102, 301, 201]


def test_shop_action_generator_respects_inventory_slots_and_money():
    state = DefaultBalatroStateTranslator().translate(
        _structured_shop_snapshot()
    )
    state.money = 4
    state.jokers = [object()] * state.joker_slots
    state.consumables = [object()] * state.consumable_slots

    actions = BalatroShopActionGenerator().generate_actions(state)

    assert [action.name for action in actions] == [
        BUY_BOOSTER,
        END_SHOP,
    ]


def test_shop_action_generator_exposes_only_checkpoint_safe_external_actions():
    state = DefaultBalatroStateTranslator().translate(
        _structured_shop_snapshot()
    )

    actions = BalatroShopActionGenerator().generate_bufferable_actions(state)

    assert [action.name for action in actions] == [
        BUY_JOKER,
        BUY_CONSUMABLE,
        BUY_VOUCHER,
        END_SHOP,
    ]


def test_buffered_shop_transaction_projects_direct_purchase_until_checkpoint():
    state = DefaultBalatroStateTranslator().translate(
        _structured_shop_snapshot()
    )
    joker = state.shop_jokers[0]
    transaction = BufferedShopTransaction.begin(state)

    transaction.apply(
        state,
        BalatroAction(BUY_JOKER, target=joker),
    )

    assert state.money == 3
    assert joker in state.jokers
    assert joker not in state.shop_jokers
    assert transaction.expected_money == 3
    assert len(transaction.purchases) == 1

    persisted = DefaultBalatroStateTranslator().translate(
        LiveBalatroSnapshot(
            sequence=13,
            phase="BLIND_SELECT",
            state_complete=False,
            payload={"money": 3},
        )
    )
    transaction.assert_reconciled(persisted)


def test_buffered_shop_transaction_projects_consumable_and_voucher_purchases():
    state = DefaultBalatroStateTranslator().translate(
        _structured_shop_snapshot()
    )
    transaction = BufferedShopTransaction.begin(state)

    strength = state.shop_consumables[0]
    transaction.apply(
        state,
        BalatroAction(BUY_CONSUMABLE, target=strength),
    )

    assert state.money == 7
    assert strength in state.consumables
    assert strength not in state.shop_consumables

    state.money = 10
    voucher = state.shop_vouchers[0]
    transaction.expected_money = 10
    transaction.apply(
        state,
        BalatroAction(BUY_VOUCHER, target=voucher),
    )

    assert state.money == 0
    assert voucher in state.vouchers
    assert voucher not in state.shop_vouchers


def test_buffered_shop_transaction_rejects_random_state_actions():
    state = DefaultBalatroStateTranslator().translate(
        _structured_shop_snapshot()
    )
    transaction = BufferedShopTransaction.begin(state)

    for action in (
        BalatroAction(BUY_BOOSTER, target=state.shop_boosters[0]),
        BalatroAction(REFRESH_SHOP),
    ):
        try:
            transaction.apply(state, action)
        except UnsupportedBufferedShopAction:
            pass
        else:
            raise AssertionError(
                f"expected {action.name} to require immediate observation"
            )
