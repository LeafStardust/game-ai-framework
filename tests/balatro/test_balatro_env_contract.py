from games.balatro.actions import (
    BUY_BOOSTER,
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_SHOP,
    REFRESH_SHOP,
    SELECT_BLIND,
    SELECT_PACK_CARD,
    SELL_JOKER,
    SKIP_BLIND,
    SKIP_BOOSTER,
    USE_CONSUMABLE,
)
from games.balatro.env_contract import (
    BALATRO_ENV_CONTRACT_VERSION,
    CapabilityStatus,
    contract_for,
    training_action_contracts,
    validate_env_contract,
)


def test_environment_contract_is_versioned_and_valid():
    assert BALATRO_ENV_CONTRACT_VERSION == "l3-v1"
    validate_env_contract()


def test_only_frozen_actions_are_training_exposed():
    exposed = {
        contract.alias: contract.action_id
        for contract in training_action_contracts()
    }
    assert exposed == {
        "END_SHOP": END_SHOP,
        "BUY_JOKER": BUY_JOKER,
        "BUY_VOUCHER": BUY_VOUCHER,
        "BUY_CONSUMABLE": BUY_CONSUMABLE,
        "OPEN_PACK": BUY_BOOSTER,
    }
    assert all(
        contract.legality_owner and contract.execution_owner
        for contract in training_action_contracts()
    )


def test_rl_aliases_preserve_canonical_production_action_ids():
    expected = {
        "REROLL_SHOP": REFRESH_SHOP,
        "SELL_JOKER": SELL_JOKER,
        "CHOOSE_PACK_OPTION": SELECT_PACK_CARD,
        "SKIP_PACK": SKIP_BOOSTER,
        "USE_CONSUMABLE": USE_CONSUMABLE,
        "SKIP_BLIND": SKIP_BLIND,
        "SELECT_BLIND": SELECT_BLIND,
    }
    for alias, action_id in expected.items():
        assert contract_for(alias).action_id == action_id


def test_unfrozen_and_unavailable_capabilities_never_enter_training_mask():
    exposed_aliases = {contract.alias for contract in training_action_contracts()}

    for alias in (
        "REROLL_SHOP",
        "SELL_JOKER",
        "BUY_CARD",
        "CHOOSE_PACK_OPTION",
        "SKIP_PACK",
        "USE_CONSUMABLE",
        "SKIP_BLIND",
        "SELECT_BLIND",
        "REROLL_BOSS",
    ):
        assert alias not in exposed_aliases

    assert contract_for("REROLL_BOSS").status is CapabilityStatus.UNAVAILABLE
    assert contract_for("REROLL_BOSS").action_id is None
    assert contract_for("BUY_CARD").status is CapabilityStatus.PLANNED
    assert contract_for("BUY_CARD").action_id is None
