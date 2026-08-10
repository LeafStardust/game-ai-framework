from games.balatro.actions import (
    BalatroAction,
    BUY_JOKER,
    END_SHOP,
    REFRESH_SHOP,
)
from games.balatro.live import (
    DefaultBalatroActionExecutor,
    LiveBalatroSnapshot,
)


def test_shop_buy_action_uses_live_target_id():
    executor = DefaultBalatroActionExecutor()
    snapshot = LiveBalatroSnapshot(
        sequence=9,
        phase="SHOP",
        state_complete=True,
    )

    command = executor.command_for(
        BalatroAction(
            BUY_JOKER,
            target={"id": "shop-joker-1"},
        ),
        snapshot,
    )

    assert command.action == BUY_JOKER
    assert command.payload == {
        "target": "shop-joker-1"
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
