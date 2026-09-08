from copy import deepcopy
from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.env.parity import (
    canonical_public_state_signature,
    compare_public_tactical_evidence,
)
from games.balatro.env.shop_consumable_items import GeneratedShopConsumableItem
from games.balatro.env.shop_items import GeneratedShopJokerItem
from games.balatro.env.tactical_evidence import PublicTacticalTransitionEvidence
from games.balatro.state import BalatroState
from games.balatro.tarots import create_tarot


def _state(*, rank="A", live_id="live-card"):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.deck = []
    state.hand = [BalatroCard(rank, "Spades", live_id=live_id)]
    state.score = 10
    state.hands_remaining = 3
    return state


def _evidence(
    *,
    before=None,
    after=None,
    action_name=PLAY_CARDS,
    selected=(0,),
):
    before = before or _state()
    after = after or deepcopy(before)
    after.score += 11
    return PublicTacticalTransitionEvidence(
        before=before,
        action=BalatroAction(
            action_name,
            cards=[before.hand[index] for index in selected],
        ),
        selected_hand_indices=tuple(selected),
        after=after,
    )


def test_env_r5_public_state_signature_ignores_engine_local_card_identity():
    live = _state(live_id="lua-42")
    simulator = _state(live_id="headless-7")

    assert canonical_public_state_signature(live) == canonical_public_state_signature(simulator)


def test_env_r5_public_state_signature_masks_face_down_identity_before_compare():
    live = _state(rank="A", live_id="lua-hidden")
    simulator = _state(rank="2", live_id="sim-hidden")
    live.hand[0].face_down = True
    simulator.hand[0].face_down = True

    assert canonical_public_state_signature(live) == canonical_public_state_signature(simulator)


def test_env_r5_public_state_signature_normalizes_equivalent_shop_item_models():
    live = _state()
    simulator = deepcopy(live)
    live.phase = simulator.phase = "SHOP"
    live.shop_active = simulator.shop_active = True
    live.shop_jokers = [
        SimpleNamespace(
            center="j_joker",
            rarity="COMMON",
            edition=None,
            cost=2,
            live_id=101,
            area_index=0,
        )
    ]
    live_tarot = create_tarot("Temperance")
    live_tarot.price = 3
    live.shop_consumables = [live_tarot]
    simulator.shop_jokers = [GeneratedShopJokerItem("j_joker", 1, 2, None, 2)]
    simulator.shop_consumables = [
        GeneratedShopConsumableItem("Tarot", "c_temperance", 3, 3)
    ]

    assert canonical_public_state_signature(live) == canonical_public_state_signature(simulator)


def test_env_r5_tactical_parity_matches_equivalent_public_transition():
    live_before = _state(live_id="lua-1")
    simulator_before = _state(live_id="sim-99")
    live = _evidence(before=live_before)
    simulator = _evidence(before=simulator_before)

    comparison = compare_public_tactical_evidence(live, simulator)

    assert comparison.matches is True
    assert comparison.differences == ()
    assert comparison.live == comparison.simulator


def test_env_r5_tactical_parity_reports_public_post_state_difference():
    live = _evidence()
    simulator_after = deepcopy(live.after)
    simulator_after.money += 1
    simulator = _evidence(before=deepcopy(live.before), after=simulator_after)

    comparison = compare_public_tactical_evidence(live, simulator)

    assert comparison.matches is False
    assert comparison.differences == ("after",)


def test_env_r5_tactical_parity_reports_canonical_action_difference():
    before = _state()
    before.hand.append(BalatroCard("K", "Hearts", live_id="second"))
    after = deepcopy(before)
    live = _evidence(before=deepcopy(before), after=deepcopy(after), selected=(0,))
    simulator = _evidence(
        before=deepcopy(before),
        after=deepcopy(after),
        action_name=DISCARD_CARDS,
        selected=(1,),
    )

    comparison = compare_public_tactical_evidence(live, simulator)

    assert comparison.matches is False
    assert comparison.differences == (
        "action.name",
        "action.selected_hand_indices",
    )
