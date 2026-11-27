import pytest

from games.balatro.env.actions import EnvAction
from games.balatro.env.pack import (
    choose_pack_option_exact,
    open_paid_buffoon_pack_exact,
    skip_pack_exact,
)
from games.balatro.env.ppo_campaign import make_ppo_training_environment
from games.balatro.env.serialization import restore_headless_run_state
from games.balatro.env.transition import HeadlessTransitionError


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
