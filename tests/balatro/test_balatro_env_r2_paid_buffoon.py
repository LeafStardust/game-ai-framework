import pytest

from games.balatro.env.actions import EnvAction
from games.balatro.env.action_encoding import action_index, legal_action_mask
from games.balatro.env.observation_encoding import JOKER_CENTER_KEYS, PUBLIC_OBSERVATION_SCHEMA
from games.balatro.env.pack import (
    choose_pack_option_exact,
    open_paid_buffoon_pack_exact,
    skip_pack_exact,
)
from games.balatro.env.ppo_campaign import make_ppo_training_environment
from games.balatro.env.serialization import restore_headless_run_state
from games.balatro.env.state import EnvStateFrame
from games.balatro.env.transition import HeadlessTransitionError
from games.balatro.jokers.hallucination import HallucinationJoker


def test_paid_buffoon_opens_exact_choices_and_skip_restores_shop_pool():
    environment = make_ppo_training_environment(0)
    environment.reset(seed="B2189F31")
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    before = environment._backend.run
    snapshot = before.rng_snapshot()
    eligible = before.public.joker_generation_pools

    with pytest.raises(HeadlessTransitionError, match="ordinary generated Buffoon"):
        open_paid_buffoon_pack_exact(before, 1)
    opened = open_paid_buffoon_pack_exact(before, 0)
    assert opened.public.phase == "BUFFOON_PACK"
    assert opened.public.shop_active is False
    assert opened.public.money == 4
    assert opened.public.shop_boosters == before.public.shop_boosters[1:]
    assert opened.pack_choices_remaining == 1
    assert [item.center_key for item in opened.pack_choices] == [
        "j_red_card", "j_mystic_summit",
    ]
    assert opened.generated_center_discovered("p_buffoon_normal_1") is True
    frame = EnvStateFrame(
        opened.public, pack_choices=tuple(opened.pack_choices), pack_choices_remaining=1,
    )
    features = dict(zip(PUBLIC_OBSERVATION_SCHEMA.feature_names, frame.encoded_observation().values))
    assert features["pack.choices_remaining"] == 1
    assert features["pack.jokers.0.center"] == JOKER_CENTER_KEYS.index("j_red_card") + 1
    assert features["pack.jokers.1.center"] == JOKER_CENTER_KEYS.index("j_mystic_summit") + 1
    assert before.public.money == 8
    assert before.rng_snapshot() == snapshot
    assert len(opened.public.joker_generation_pools["1"]) == len(eligible["1"]) - 2

    restored = restore_headless_run_state(opened.serialize())
    assert restored.serialize() == opened.serialize()
    skipped = skip_pack_exact(restored)
    assert skipped.public.phase == "SHOP"
    assert skipped.public.shop_active is True
    assert skipped.public.money == 4
    assert skipped.pack_choices == []
    assert skipped.public.joker_generation_pools == eligible
    assert skipped.rng_snapshot() == opened.rng_snapshot()

    chosen = choose_pack_option_exact(restored, 1)
    assert chosen.public.phase == "SHOP"
    assert chosen.public.money == 4
    assert [joker.center for joker in chosen.public.jokers] == ["j_mystic_summit"]
    assert chosen.generated_center_discovered("j_mystic_summit") is True
    common = {record["key"] for record in chosen.public.joker_generation_pools["1"]}
    assert "j_red_card" in common
    assert "j_mystic_summit" not in common
    assert chosen.rng_snapshot() == opened.rng_snapshot()


@pytest.mark.parametrize(
    "seed, slots, debuffed, rolled, centers",
    [
        (4, 2, False, True, ["c_high_priestess"]),
        (0, 2, False, True, []),
        (4, 0, False, False, []),
        (4, 2, True, False, []),
    ],
)
def test_paid_buffoon_hallucination_rolls_only_with_an_active_joker_and_room(
    seed, slots, debuffed, rolled, centers,
):
    environment = make_ppo_training_environment(0)
    environment.reset(seed=seed)
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    run = environment._backend.run
    joker = HallucinationJoker()
    joker.center = "j_hallucination"
    joker.debuffed = debuffed
    run.public.jokers = [joker]
    run.public.consumable_slots = slots

    opened = open_paid_buffoon_pack_exact(run, 0)

    assert ("halu1" in opened.rng.nodes) is rolled
    assert ("Tarothal1" in opened.rng.nodes) is bool(centers)
    assert [item.center_key for item in opened.public.consumables] == centers
    assert "halu1" not in run.rng.nodes


def test_ppo_routes_paid_buffoon_open_and_choose_as_public_actions():
    environment = make_ppo_training_environment(0)
    environment.reset(seed="B2189F31")
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    opening = EnvAction.from_alias("OPEN_PACK", {"slot": 0})
    blocked = EnvAction.from_alias("OPEN_PACK", {"slot": 1})
    legal = environment.legal_actions()
    assert opening in legal
    assert blocked not in legal
    environment.step(opening)

    assert environment.frame.state.phase == "BUFFOON_PACK"
    assert environment.frame.pack_choices_remaining == 1
    assert [item.center_key for item in environment.frame.pack_choices] == [
        "j_red_card", "j_mystic_summit",
    ]
    choice = EnvAction.from_alias("CHOOSE_PACK_OPTION", {"option_index": 1})
    assert legal_action_mask(environment.legal_actions()).values[action_index(choice)]
    environment.step(choice)
    assert environment.frame.state.phase == "SHOP"
    assert environment.frame.pack_choices == ()
