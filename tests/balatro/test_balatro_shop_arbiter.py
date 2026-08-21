import games.balatro.shop_arbiter as shop_arbiter_module

from games.balatro.actions import (
    BUY_BOOSTER,
    BUY_VOUCHER,
    END_SHOP,
    REFRESH_SHOP,
    BalatroAction,
)
from games.balatro.live.shop import LiveShopItem
from games.balatro.playbook import (
    BalatroPlaybook,
    BalatroPlaybookRegistry,
    default_balatro_playbooks,
)
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_booster_policy import (
    BoosterAcquisitionThresholds,
    BuildAwareShopBoosterPolicy,
)
from games.balatro.shop_reroll_policy import ShopRerollThresholds
from games.balatro.state import BalatroState


def _state(*, money: int = 20) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.joker_slots = 5
    return state


def _booster(label: str, *, price: int = 0, center: str | None = None):
    return LiveShopItem(
        kind="BOOSTER",
        label=label,
        price=price,
        area_index=0,
        center=center,
    )


def test_unrecognized_and_target_unsafe_boosters_fail_closed():
    state = _state()
    policy = BuildAwareShopBoosterPolicy()

    unknown = policy.recommend(
        state,
        BalatroAction(BUY_BOOSTER, target=_booster("Mystery Pack")),
    )
    arcana = policy.recommend(
        state,
        BalatroAction(
            BUY_BOOSTER,
            target=_booster("Arcana Pack", center="p_arcana_normal_1"),
        ),
    )
    spectral = policy.recommend(
        state,
        BalatroAction(
            BUY_BOOSTER,
            target=_booster("Spectral Pack", center="p_spectral_normal_1"),
        ),
    )

    assert unknown.decision == "HOLD"
    assert arcana.decision == "HOLD"
    assert spectral.decision == "HOLD"
    assert any("deferred to D9/D10" in note for note in arcana.rationale)
    assert all(
        any("contents are not predicted" in note for note in result.rationale)
        for result in (unknown, arcana, spectral)
    )


def test_buffoon_requires_currently_usable_joker_capacity():
    state = _state()
    state.jokers = [object()] * state.joker_slots
    result = BuildAwareShopBoosterPolicy().recommend(
        state,
        BalatroAction(
            BUY_BOOSTER,
            target=_booster("Buffoon Pack", center="p_buffoon_normal_1"),
        ),
    )

    assert result.decision == "HOLD"
    assert any("free Joker slot" in note for note in result.rationale)
    assert any("replacement" in note for note in result.rationale)


def test_celestial_option_value_uses_observed_hand_specialization_not_level_alone():
    base_state = _state()
    level_only_state = _state()
    level_only_state.hand_levels["PAIR"] = 5
    repeated_state = _state()
    repeated_state.hand_play_counts["PAIR"] = 8
    action = BalatroAction(
        BUY_BOOSTER,
        target=_booster("Celestial Pack", center="p_celestial_normal_4"),
    )
    policy = BuildAwareShopBoosterPolicy()

    base = policy.recommend(base_state, action)
    level_only = policy.recommend(level_only_state, action)
    repeated = policy.recommend(repeated_state, action)

    assert level_only.option_utility == base.option_utility
    assert repeated.option_utility > base.option_utility
    assert any("no observed poker-hand history" in note for note in level_only.rationale)
    assert any("most-played hand=PAIR plays=8/8" in note for note in repeated.rationale)
    assert any("contents are not predicted" in note for note in repeated.rationale)


def test_expensive_booster_can_lose_to_hold_after_shop_economics():
    state = _state(money=10)
    result = BuildAwareShopBoosterPolicy().recommend(
        state,
        BalatroAction(
            BUY_BOOSTER,
            target=_booster(
                "Standard Pack",
                price=10,
                center="p_standard_normal_1",
            ),
        ),
    )

    assert result.decision == "HOLD"
    assert result.total <= 0.35
    assert result.price_penalty > 0
    assert result.interest_penalty > 0


def test_whole_shop_arbiter_can_choose_booster_over_leave():
    state = _state()
    booster = BalatroAction(
        BUY_BOOSTER,
        target=_booster("Celestial Pack", center="p_celestial_normal_4"),
    )
    decision = BuildAwareShopArbiter().decide(
        state,
        [booster, BalatroAction(END_SHOP)],
        reroll_cost=5,
    )

    assert decision.action is booster
    assert decision.source == "BOOSTER"
    assert decision.normalized_gain > 0


def test_strong_deterministic_purchase_beats_booster():
    state = _state()
    voucher = BalatroAction(
        BUY_VOUCHER,
        target=LiveShopItem(
            kind="VOUCHER",
            label="Antimatter",
            price=0,
            area_index=0,
        ),
    )
    booster = BalatroAction(
        BUY_BOOSTER,
        target=_booster("Celestial Pack", center="p_celestial_normal_4"),
    )
    decision = BuildAwareShopArbiter().decide(
        state,
        [voucher, booster, BalatroAction(END_SHOP)],
        reroll_cost=5,
    )

    assert decision.action is voucher
    assert decision.source == "DETERMINISTIC"


def test_visible_booster_quality_suppresses_reroll():
    state = _state()
    booster = BalatroAction(
        BUY_BOOSTER,
        target=_booster("Celestial Pack", center="p_celestial_normal_4"),
    )
    decision = BuildAwareShopArbiter().decide(
        state,
        [booster, BalatroAction(END_SHOP)],
        reroll_cost=1,
    )

    assert decision.action is booster
    assert decision.source == "BOOSTER"
    assert decision.reroll is not None
    assert decision.reroll.decision == "HOLD"
    assert decision.reroll.current_best_score >= decision.total


def test_free_reroll_can_beat_weak_or_rejected_booster():
    state = _state()
    weak = BalatroAction(
        BUY_BOOSTER,
        target=_booster(
            "Standard Pack",
            price=10,
            center="p_standard_normal_1",
        ),
    )
    decision = BuildAwareShopArbiter().decide(
        state,
        [weak, BalatroAction(END_SHOP)],
        reroll_cost=0,
    )

    assert decision.action.name == REFRESH_SHOP
    assert decision.source == "REROLL"


def test_unknown_reroll_cost_does_not_block_booster_arbitration():
    state = _state()
    booster = BalatroAction(
        BUY_BOOSTER,
        target=_booster("Celestial Pack", center="p_celestial_normal_4"),
    )
    decision = BuildAwareShopArbiter().decide(
        state,
        [booster, BalatroAction(END_SHOP)],
        reroll_cost=None,
    )

    assert decision.action is booster
    assert decision.source == "BOOSTER"
    assert decision.reroll is not None
    assert decision.reroll.decision == "HOLD"


def test_red_white_exposes_current_d8_and_d11_thresholds():
    playbook = default_balatro_playbooks().get("RED", "WHITE")

    d8 = BoosterAcquisitionThresholds.from_mapping(playbook.thresholds_for("D8"))
    d11 = ShopRerollThresholds(**playbook.thresholds_for("D11"))

    assert d8 == BoosterAcquisitionThresholds()
    assert d11 == ShopRerollThresholds()


def test_arbiter_resolves_d8_and_d11_from_active_playbook(monkeypatch):
    registry = BalatroPlaybookRegistry()
    registry.register(
        BalatroPlaybook(
            deck="RED",
            stake="WHITE",
            name="threshold-regression",
            strategy={
                "decision_thresholds": {
                    "booster_acquisition": {
                        "minimum_buy_advantage": 9.0,
                    },
                    "reroll": {
                        "minimum_margin": 4.0,
                    },
                }
            },
        )
    )
    monkeypatch.setattr(
        shop_arbiter_module,
        "default_balatro_playbooks",
        lambda: registry,
    )
    state = _state()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    arbiter = BuildAwareShopArbiter()

    booster_policy = arbiter._booster_policy_for_state(state)
    reroll_policy = arbiter._reroll_policy_for_state(state)

    assert booster_policy.thresholds.minimum_buy_advantage == 9.0
    assert reroll_policy.thresholds.minimum_margin == 4.0

    booster = BalatroAction(
        BUY_BOOSTER,
        target=_booster("Celestial Pack", center="p_celestial_normal_4"),
    )
    decision = arbiter.decide(
        state,
        [booster, BalatroAction(END_SHOP)],
        reroll_cost=None,
    )

    assert decision.source == "END_SHOP"
    assert decision.booster is None
