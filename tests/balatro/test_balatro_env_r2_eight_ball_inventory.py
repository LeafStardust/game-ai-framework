import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.shop_consumable_generation_state import generate_held_eight_ball_tarot
from games.balatro.env.shop_repricing import reprice_exact_generated_shop
from games.balatro.env.transition import HeadlessTransitionError
from games.balatro.hand import PokerHand
from games.balatro.jokers.eight_ball import EightBallJoker
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _run():
    run = pristine_red_white_reset(48)
    run.public.phase = "SELECTING_HAND"
    run.public.ante = 2
    run.public.shop_inflation_observed = True
    return run


def test_env_r2_eight_ball_publishes_tarot_and_suppresses_held_center():
    run = _run()
    original_rng = run.rng_snapshot()
    first = generate_held_eight_ball_tarot(run)
    second = generate_held_eight_ball_tarot(first)

    assert run.public.consumables == []
    assert run.rng_snapshot() == original_rng
    strength, other = second.public.consumables
    assert (strength.center_key, strength.price, strength.discovered) == (
        "c_strength", 3, True,
    )
    assert other.center_key != strength.center_key
    eligible = {record["key"] for record in second.public.consumable_generation_pools["Tarot"]}
    for item in (strength, other):
        assert item.center_key not in eligible
        assert second.generated_center_discovered(item.center_key) is True
        assert item.center_key in second.tag_profile_state.discovered_center_keys
    assert "Tarot8ba2" in second.rng.nodes

    snapshot = second.rng_snapshot()
    with pytest.raises(HeadlessTransitionError, match="exact open inventory"):
        generate_held_eight_ball_tarot(second)
    assert second.rng_snapshot() == snapshot


def test_env_r2_eight_ball_rejects_inconsistent_pool_before_rng():
    run = _run()
    result = generate_held_eight_ball_tarot(run)
    result.public.consumable_generation_pools = run.public.consumable_generation_pools
    snapshot = result.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="visible duplicate"):
        generate_held_eight_ball_tarot(result)
    assert result.rng_snapshot() == snapshot


def test_env_r2_eight_ball_tarot_reprices_with_shop_discount():
    run = generate_held_eight_ball_tarot(_run())
    run.public.phase = "SHOP"
    run.public.shop_active = True
    result = reprice_exact_generated_shop(run, discount_percent=50)

    assert run.public.consumables[0].price == 3
    assert result.public.consumables[0].price == 1
    assert result.public.consumables[0].center_key == "c_strength"
    assert result.rng_snapshot() == run.rng_snapshot()


@pytest.mark.parametrize(
    "seed, indices, slots, joker_count, rolls, expected",
    [
        (5, (3,), 2, 1, 1, ["c_wheel_of_fortune"]),
        (5, (3,), 1, 2, 1, ["c_wheel_of_fortune"]),
        (5, (3,), 0, 1, 0, []),
        (5, (0, 3), 2, 1, 0, []),
        (0, (4,), 2, 1, 1, []),
    ],
)
def test_env_r4_eight_ball_rolls_for_scoring_eights_with_room(
    seed, indices, slots, joker_count, rolls, expected,
):
    run = pristine_red_white_reset(seed)
    run.public.phase = "DRAW_TO_HAND"
    run.public.blind = Blind(BlindType.SMALL, 9999)
    run.public.hands_remaining = 4
    run.public.shop_inflation_observed = True
    run.public.consumable_slots = slots
    run = deal_supported_round_start(run)
    for _ in range(joker_count):
        joker = EightBallJoker()
        joker.center = "j_8_ball"
        run.public.jokers.append(joker)
    expected_rng = run.copy().rng
    for _ in range(rolls):
        expected_rng.random("8ball")

    result = apply_supported_ordinary_play(run, indices)

    assert result.rng.nodes.get("8ball") == expected_rng.nodes.get("8ball")
    assert [item.center_key for item in result.public.consumables] == expected
    assert ("Tarot8ba1" in result.rng.nodes) is bool(expected)
    assert "8ball" not in run.rng.nodes


@pytest.mark.parametrize(
    "card_debuffed, joker_debuffed, attempts",
    [(False, False, 2), (True, False, 0), (False, True, 0)],
)
def test_eight_ball_scoring_callback_honors_retriggers_and_debuffs(
    card_debuffed, joker_debuffed, attempts,
):
    card = BalatroCard("8", "Hearts", seal="Red", debuffed=card_debuffed)
    joker = EightBallJoker()
    joker.debuffed = joker_debuffed
    state = BalatroState()
    state.jokers = [joker]
    reservations = []

    BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=state,
        cards=[card],
        include_card_chips=True,
        joker_data={"reserve_eight_ball_tarot": lambda: reservations.append(True)},
    )

    assert reservations == [True] * attempts
