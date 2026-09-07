from copy import deepcopy

import pytest

from games.balatro.env.actions import EnvAction
from games.balatro.env.shop_consumable_generation_state import (
    restore_removed_shop_consumables_to_generation_pool,
    suppress_visible_shop_consumables_from_generation_pool,
)
from games.balatro.env.shop_consumable_items import GeneratedShopConsumableItem
from games.balatro.env.shop_main_generation import generate_base_main_shop
from games.balatro.env.strategic_evidence import (
    PublicStrategicTransitionEvidence,
    build_public_strategic_transition_evidence,
    reroll_shop_with_public_evidence,
)
from games.balatro.env.transition import HeadlessRunState
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.reroll_parity_checkpoint import (
    LiveRerollParityCheckpoint,
    LiveRerollParityCheckpointError,
    compare_live_reroll_replay,
)
from games.balatro.live.runtime.live_memory_shop_terms import LiveShopRerollTerms
from games.balatro.state import BalatroState
from games.balatro.tarots import create_tarot


def _joker_record(rarity, key, cost):
    return {
        "rarity": rarity,
        "key": key,
        "cost": cost,
        "unlocked": True,
        "no_pool_flag": None,
        "yes_pool_flag": None,
    }


def _consumable_record(card_type, key, cost=3):
    return {
        "type": card_type,
        "key": key,
        "cost": cost,
        "unlocked": True,
        "no_pool_flag": None,
        "yes_pool_flag": None,
        "softlock": False,
        "hand_type": None,
    }


def _reroll_ready_run(seed="R5-REROLL-REPLAY", *, vouchers=None):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.ante = 1
    state.money = 20
    state.vouchers_observed = True
    state.vouchers = list(vouchers or [])
    state.shop_inflation_observed = True
    state.shop_inflation = 0
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = 0
    state.joker_generation_pool_observed = True
    state.joker_generation_pools = {
        "1": [_joker_record(1, "j_joker", 2)],
        "2": [_joker_record(2, "j_stencil", 8)],
        "3": [_joker_record(3, "j_dna", 8)],
        "4": [_joker_record(4, "j_caino", 20)],
    }
    state.consumable_generation_pool_observed = True
    state.consumable_generation_pools = {
        "Tarot": [_consumable_record("Tarot", "c_strength")],
        "Planet": [_consumable_record("Planet", "c_pluto")],
    }
    return generate_base_main_shop(HeadlessRunState(public=state, seed=seed)).run


def _snapshot(sequence, *, vouchers=None):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase="SHOP",
        state_complete=True,
        payload={"vouchers_observed": True, "vouchers": list(vouchers or [])},
    )


def _checkpoint(run, sequence, *, reroll_cost=None, rng_snapshot=None):
    return LiveRerollParityCheckpoint(
        public_snapshot=_snapshot(sequence, vouchers=run.public.vouchers),
        rng_snapshot=deepcopy(rng_snapshot or run.rng_snapshot()),
        reroll_terms=LiveShopRerollTerms(
            cost=run.reroll_cost if reroll_cost is None else reroll_cost,
            free_rerolls=0,
        ),
        active_tag_count=0,
    )


class _Translator:
    def __init__(self, states):
        self.states = states

    def translate(self, snapshot):
        return deepcopy(self.states[snapshot.sequence])


def _fixture():
    before = _reroll_ready_run()
    expected, live_evidence = reroll_shop_with_public_evidence(before)
    before_checkpoint = _checkpoint(before, 1)
    after_checkpoint = _checkpoint(expected.run, 2)
    translator = _Translator({1: before.public, 2: expected.run.public})
    return before, expected, live_evidence, before_checkpoint, after_checkpoint, translator


def test_env_r5_reroll_replay_matches_public_cost_and_private_rng_authority():
    before, expected, live_evidence, before_checkpoint, after_checkpoint, translator = _fixture()
    before_rng = before.rng_snapshot()

    comparison = compare_live_reroll_replay(
        before_checkpoint,
        after_checkpoint,
        live_evidence,
        translator=translator,
    )

    assert comparison.matches is True
    assert comparison.differences == ()
    assert comparison.public.matches is True
    assert comparison.simulator_evidence.action == EnvAction.from_alias("REROLL_SHOP")
    assert comparison.simulator_evidence.before.money == 20
    assert comparison.simulator_evidence.after.money == 15
    assert expected.previous_cost == 5
    assert expected.next_cost == 6
    assert before.rng_snapshot() == before_rng


def test_env_r5_reroll_replay_admits_partially_depleted_overstock_shop():
    before = _reroll_ready_run(
        "R5-REROLL-DEPLETED-OVERSTOCK",
        vouchers=["v_overstock_norm"],
    )
    assert len(before.public.shop_jokers) + len(before.public.shop_consumables) == 3
    if before.public.shop_jokers:
        before.public.shop_jokers.pop()
    else:
        before.public.shop_consumables.pop()
    assert len(before.public.shop_jokers) + len(before.public.shop_consumables) == 2

    expected, live_evidence = reroll_shop_with_public_evidence(before)
    before_checkpoint = _checkpoint(before, 1)
    after_checkpoint = _checkpoint(expected.run, 2)
    translator = _Translator({1: before.public, 2: expected.run.public})

    comparison = compare_live_reroll_replay(
        before_checkpoint,
        after_checkpoint,
        live_evidence,
        translator=translator,
    )

    assert comparison.matches is True
    assert comparison.differences == ()
    assert len(expected.run.public.shop_jokers) + len(expected.run.public.shop_consumables) == 3
    assert expected.previous_cost == 5
    assert expected.next_cost == 6
    assert expected.run.public.money == 15


def test_env_r5_consumable_pool_visibility_matches_live_reroll_shape():
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.consumable_generation_pool_observed = True
    state.consumable_generation_pools = {
        "Tarot": [
            {**_consumable_record("Tarot", "c_empress"), "unlocked": None},
        ],
        "Planet": [
            {**_consumable_record("Planet", "c_mars"), "unlocked": None},
            {**_consumable_record("Planet", "c_pluto"), "unlocked": None},
        ],
    }
    run = HeadlessRunState(public=state, seed="R5-LIVE-CONSUMABLE-POOL")

    removed = create_tarot("The Hanged Man")
    restored = restore_removed_shop_consumables_to_generation_pool(run, (removed,))
    assert [
        record["key"] for record in restored.public.consumable_generation_pools["Tarot"]
    ] == ["c_empress", "c_hanged_man"]
    hanged = restored.public.consumable_generation_pools["Tarot"][1]
    assert hanged == {
        "type": "Tarot",
        "key": "c_hanged_man",
        "cost": 3,
        "unlocked": None,
        "no_pool_flag": None,
        "yes_pool_flag": None,
        "softlock": False,
        "hand_type": None,
    }

    visible = (
        GeneratedShopConsumableItem("Tarot", "c_empress", 3, 3),
        GeneratedShopConsumableItem("Planet", "c_mars", 3, 3),
    )
    suppressed = suppress_visible_shop_consumables_from_generation_pool(
        restored,
        visible,
    )
    assert [
        record["key"] for record in suppressed.public.consumable_generation_pools["Tarot"]
    ] == ["c_hanged_man"]
    assert [
        record["key"] for record in suppressed.public.consumable_generation_pools["Planet"]
    ] == ["c_pluto"]


def test_env_r5_reroll_replay_reports_public_post_state_difference():
    before, expected, _, before_checkpoint, after_checkpoint, _ = _fixture()
    live_after = deepcopy(expected.run.public)
    live_after.money -= 1
    live_evidence = build_public_strategic_transition_evidence(
        before.public,
        EnvAction.from_alias("REROLL_SHOP"),
        live_after,
    )
    translator = _Translator({1: before.public, 2: live_after})

    comparison = compare_live_reroll_replay(
        before_checkpoint,
        after_checkpoint,
        live_evidence,
        translator=translator,
    )

    assert comparison.matches is False
    assert comparison.differences == ("public.after",)
    assert comparison.public.differences == ("after",)


def test_env_r5_reroll_replay_reports_next_cost_difference():
    before, expected, live_evidence, before_checkpoint, _, translator = _fixture()
    after_checkpoint = _checkpoint(
        expected.run,
        2,
        reroll_cost=expected.next_cost + 1,
    )

    comparison = compare_live_reroll_replay(
        before_checkpoint,
        after_checkpoint,
        live_evidence,
        translator=translator,
    )

    assert comparison.matches is False
    assert comparison.differences == ("reroll.next_cost",)
    assert comparison.public.matches is True


def test_env_r5_reroll_replay_reports_private_rng_post_state_difference():
    before, expected, live_evidence, before_checkpoint, _, translator = _fixture()
    after_checkpoint = _checkpoint(
        expected.run,
        2,
        rng_snapshot=before.rng_snapshot(),
    )

    comparison = compare_live_reroll_replay(
        before_checkpoint,
        after_checkpoint,
        live_evidence,
        translator=translator,
    )

    assert comparison.matches is False
    assert comparison.differences == ("rng.after",)
    assert comparison.public.matches is True


def test_env_r5_reroll_replay_rejects_parameterized_live_action_evidence():
    before, _, live_evidence, before_checkpoint, after_checkpoint, translator = _fixture()
    malformed = PublicStrategicTransitionEvidence(
        before=live_evidence.before,
        action=EnvAction.from_alias("REROLL_SHOP", {"target": 0}),
        after=live_evidence.after,
    )

    with pytest.raises(LiveRerollParityCheckpointError, match="parameterless REROLL_SHOP"):
        compare_live_reroll_replay(
            before_checkpoint,
            after_checkpoint,
            malformed,
            translator=translator,
        )

    assert before.public.money == 20


def test_env_r5_reroll_replay_rejects_live_evidence_from_different_checkpoint():
    before, expected, _, before_checkpoint, after_checkpoint, translator = _fixture()
    unrelated_after = deepcopy(expected.run.public)
    unrelated_after.money -= 1
    unrelated = build_public_strategic_transition_evidence(
        before.public,
        EnvAction.from_alias("REROLL_SHOP"),
        unrelated_after,
    )

    with pytest.raises(LiveRerollParityCheckpointError, match="does not match checkpoint public state"):
        compare_live_reroll_replay(
            before_checkpoint,
            after_checkpoint,
            unrelated,
            translator=translator,
        )
