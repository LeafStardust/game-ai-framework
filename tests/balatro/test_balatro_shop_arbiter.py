import games.balatro.shop_arbiter as shop_arbiter_module

from games.balatro.actions import (
    BUY_BOOSTER,
    BUY_VOUCHER,
    END_SHOP,
    REFRESH_SHOP,
    BalatroAction,
)
from games.balatro.joker import Joker, JokerContext
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


class InertJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        return context


def _state(*, money: int = 20) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.joker_slots = 5
    return state


def _with_public_consumable_pools(state: BalatroState) -> BalatroState:
    state.consumable_generation_pool_observed = True
    state.consumable_generation_pools = {
        "TAROT": (
            {
                "center": "c_hermit",
                "label": "The Hermit",
                "ability_name": "The Hermit",
                "ability_set": "TAROT",
            },
        ),
        "SPECTRAL": (
            {
                "center": "c_black_hole",
                "label": "Black Hole",
                "ability_name": "Black Hole",
                "ability_set": "SPECTRAL",
            },
        ),
    }
    return state


def _with_public_joker_pool(state: BalatroState) -> BalatroState:
    state.joker_generation_pool_observed = True
    state.joker_generation_pools = {
        rarity: (
            {
                "center": "j_joker",
                "label": "Joker",
                "ability_name": "Joker",
                "ability_set": "JOKER",
                "rarity": rarity,
            },
        )
        for rarity in ("COMMON", "UNCOMMON", "RARE")
    }
    state.joker_generation_edition_rate = 1.0
    state.visible_poker_hands = tuple(state.hand_levels)
    return state


def _booster(label: str, *, price: int = 0, center: str | None = None):
    return LiveShopItem(
        kind="BOOSTER",
        label=label,
        price=price,
        area_index=0,
        center=center,
    )


def test_unrecognized_boosters_fail_closed_while_publicly_modeled_families_can_buy():
    state = _with_public_consumable_pools(_state())
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
            target=_booster("Mega Spectral Pack", center="p_spectral_mega_1"),
        ),
    )

    assert unknown.decision == "HOLD"
    assert arcana.decision == "BUY"
    assert spectral.decision == "BUY"
    assert any("current public eligible Tarot pool" in note for note in arcana.rationale)
    assert any("current public eligible get_current_pool catalogue" in note for note in spectral.rationale)
    assert any("unrecognized booster family" in note for note in unknown.rationale)


def test_buffoon_full_roster_can_be_valued_through_d2_replacement():
    state = _with_public_joker_pool(_state())
    state.jokers = [InertJoker() for _ in range(state.joker_slots)]
    result = BuildAwareShopBoosterPolicy().recommend(
        state,
        BalatroAction(
            BUY_BOOSTER,
            target=_booster("Buffoon Pack", center="p_buffoon_normal_1"),
        ),
    )

    assert result.decision == "BUY"
    assert result.option_utility > 0.0
    assert any("full Joker roster remains valid" in note for note in result.rationale)
    assert any("sell -> reobserve -> select replacement" in note for note in result.rationale)


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

    assert level_only.build_need_score == base.build_need_score == 0.0
    assert repeated.build_need_score > base.build_need_score
    assert repeated.option_utility > 0.0
    assert any("expected best visible Planet literal value" in note for note in repeated.rationale)
    assert any("finite public Planet expectation" in note for note in repeated.rationale)


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


def test_whole_shop_arbiter_holds_unrecognized_booster_when_reroll_is_unknown():
    state = _state()
    booster = BalatroAction(BUY_BOOSTER, target=_booster("Mystery Pack"))
    decision = BuildAwareShopArbiter().decide(
        state,
        [booster, BalatroAction(END_SHOP)],
        reroll_cost=None,
    )

    assert decision.action.name == END_SHOP
    assert decision.source == "END_SHOP"
    assert decision.normalized_gain == 0


def test_strong_deterministic_purchase_beats_unrecognized_booster():
    # Antimatter's D14 parent value is the marginal value of the extra Joker slot
    # through the public eligible Joker catalogue. Supply that public catalogue so
    # this test exercises an actually admitted positive deterministic purchase.
    state = _with_public_joker_pool(_state())
    voucher_target = LiveShopItem(
        kind="VOUCHER",
        label="Antimatter",
        price=0,
        area_index=0,
    )
    voucher = BalatroAction(BUY_VOUCHER, target=voucher_target)
    booster = BalatroAction(BUY_BOOSTER, target=_booster("Mystery Pack"))
    decision = BuildAwareShopArbiter().decide(
        state,
        [voucher, booster, BalatroAction(END_SHOP)],
        reroll_cost=None,
    )

    # Deterministic policy wrappers may reconstruct the executable BalatroAction.
    # D14 identity is semantic: same action type and exact visible target.
    assert decision.action.name == BUY_VOUCHER
    assert decision.action.target is voucher_target
    assert decision.source == "DETERMINISTIC"


def test_unrecognized_visible_booster_does_not_suppress_reroll():
    state = _with_public_joker_pool(_state(money=21))
    booster = BalatroAction(BUY_BOOSTER, target=_booster("Mystery Pack"))
    decision = BuildAwareShopArbiter().decide(
        state,
        [booster, BalatroAction(END_SHOP)],
        reroll_cost=1,
    )

    assert decision.action.name == REFRESH_SHOP
    assert decision.source == "REROLL"
    assert decision.reroll is not None
    assert decision.reroll.decision == "REROLL"


def test_free_reroll_can_beat_weak_or_rejected_booster():
    state = _state()
    weak = BalatroAction(
        BUY_BOOSTER,
        target=_booster("Standard Pack", price=10, center="p_standard_normal_1"),
    )
    decision = BuildAwareShopArbiter().decide(
        state,
        [weak, BalatroAction(END_SHOP)],
        reroll_cost=0,
    )

    assert decision.action.name == REFRESH_SHOP
    assert decision.source == "REROLL"


def test_unknown_reroll_cost_and_unrecognized_booster_hold_shop():
    state = _state()
    booster = BalatroAction(BUY_BOOSTER, target=_booster("Mystery Pack"))
    decision = BuildAwareShopArbiter().decide(
        state,
        [booster, BalatroAction(END_SHOP)],
        reroll_cost=None,
    )

    assert decision.action.name == END_SHOP
    assert decision.source == "END_SHOP"
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
                    "booster_acquisition": {"minimum_buy_advantage": 9.0},
                    "reroll": {"minimum_margin": 4.0},
                }
            },
        )
    )
    monkeypatch.setattr(shop_arbiter_module, "default_balatro_playbooks", lambda: registry)
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
