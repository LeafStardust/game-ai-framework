import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.env.select_blind import select_blind_exact
from games.balatro.env.serialization import serialize_headless_run_state
from games.balatro.env.tactical_transition import apply_supported_tactical_discard
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.joker import JokerContext
from games.balatro.jokers.faceless_joker import FacelessJoker
from games.balatro.jokers.pareidolia import PareidoliaJoker
from games.balatro.jokers.splash import SplashJoker
from games.balatro.state import BalatroState


ORDINARY_REDRAW_BOSSES = (
    "The Arm",
    "The Club",
    "The Eye",
    "Amber Acorn",
    "Crimson Heart",
    "Violet Vessel",
    "The Fish",
    "The Flint",
    "The Goad",
    "The Head",
    "The Hook",
    "The House",
    "The Mouth",
    "The Ox",
    "The Pillar",
    "The Plant",
    "The Tooth",
    "The Wall",
    "The Window",
    "Verdant Leaf",
)


def _boss_run(
    name: str,
    *,
    seed: str | None = None,
    vouchers: tuple[str, ...] = (),
) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 8 if name in {
        "Amber Acorn",
        "Crimson Heart",
        "Violet Vessel",
        "Verdant Leaf",
    } else 2
    state.round = 2
    state.blind = Blind(BlindType.BOSS, requirement=99_999, reward=5)
    state.boss_name = name
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.vouchers = list(vouchers)
    state.vouchers_observed = True
    state.hand_size = 8 + int("v_paint_brush" in vouchers) + int(
        "v_palette" in vouchers
    )
    run = HeadlessRunState(public=state, seed=seed or f"R4-DISCARD-{name}")
    if name == "The Pillar":
        for card in run.require_playing_card_order():
            card.played_this_ante_observed = True
    return select_blind_exact(run)


@pytest.mark.parametrize(
    ("indices", "debuff_card", "payout"),
    [
        ((1, 2), False, 0),
        ((1, 2, 3), False, 5),
        ((0, 1, 2, 3, 4), False, 5),
        ((1, 2, 3), True, 0),
    ],
)
def test_env_r4_faceless_pays_once_for_qualifying_discard(indices, debuff_card, payout):
    run = _boss_run("The Wall", seed="FACELESS")
    assert [card.rank for card in run.public.hand[:5]] == ["A", "K", "Q", "Q", "J"]
    run.public.hand[1].debuffed = debuff_card
    joker = FacelessJoker()
    joker.center = "j_faceless"
    run.public.jokers = [joker]
    before = run.public.money
    selected = [(run.public.hand[i].rank, run.public.hand[i].suit) for i in indices]

    result = apply_supported_tactical_discard(run, indices)

    assert run.public.money == before
    assert result.public.money == before + payout
    assert result.public.discards_used == run.public.discards_used + 1
    assert result.public.discards_remaining == run.public.discards_remaining - 1
    assert len(result.public.hand) == run.public.hand_size
    assert [(card.rank, card.suit) for card in result.discard_pile] == selected
    assert result.rng_snapshot() == run.rng_snapshot()
    assert apply_supported_tactical_discard(result, (0,)).public.money == before + payout


@pytest.mark.parametrize(
    ("pareidolia", "debuffed", "payout"),
    [(False, False, 0), (True, False, 5), (True, True, 0)],
)
def test_faceless_stone_face_status_uses_active_pareidolia(pareidolia, debuffed, payout):
    state = BalatroState()
    if pareidolia:
        joker = PareidoliaJoker()
        joker.debuffed = debuffed
        state.jokers = [joker]
    cards = [
        BalatroCard("Q", "Spades"),
        BalatroCard("J", "Hearts"),
        BalatroCard("K", "Clubs", enhancement="Stone"),
    ]
    before = state.money

    FacelessJoker().apply(JokerContext(
        state=state,
        trigger="DISCARD",
        cards=cards,
        data={"hand_rules": hand_rules_for_state(state)},
    ))

    assert state.money == before + payout


def test_faceless_debuff_disables_discard_payout():
    state = BalatroState()
    joker = FacelessJoker()
    joker.debuffed = True
    before = state.money

    joker.apply(JokerContext(
        state=state,
        trigger="DISCARD",
        cards=[BalatroCard(rank, "Hearts") for rank in ("J", "Q", "K")],
    ))

    assert state.money == before


@pytest.mark.parametrize("boss_name", ORDINARY_REDRAW_BOSSES)
def test_env_r4_audited_ordinary_boss_discard_refills_exactly(boss_name):
    run = _boss_run(boss_name)
    before_rng = run.rng_snapshot()

    result = apply_supported_tactical_discard(run, (0, 2))

    assert len(run.public.hand) == run.public.hand_size == 8
    assert run.public.discards_remaining == 3
    assert run.public.discards_used == 0
    assert len(result.public.hand) == result.public.hand_size == 8
    assert result.public.discards_remaining == 2
    assert result.public.discards_used == 1
    assert len(result.public.discard_pile) == 2
    assert len(result.draw_pile) == 42
    assert result.rng_snapshot() == before_rng
    if boss_name == "The Fish":
        assert all(card.facing_observed for card in result.public.hand)
        assert not any(card.face_down for card in result.public.hand)
    if boss_name == "The House":
        assert sum(card.face_down for card in result.public.hand) == 6
        assert all(card.facing_observed for card in result.public.hand)


@pytest.mark.parametrize(
    "boss_name",
    ("The Serpent", "Cerulean Bell"),
)
def test_env_r4_special_boss_redraws_remain_fail_closed_atomically(boss_name):
    run = _boss_run(boss_name)
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match=repr(boss_name)):
        apply_supported_tactical_discard(run, (0,))

    assert serialize_headless_run_state(run) == before


def test_env_r4_ordinary_boss_discard_rejects_inexact_resource_state():
    run = _boss_run("The Hook")
    run.public.hand_size = 9
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match="ordinary Red Deck resource"):
        apply_supported_tactical_discard(run, (0,))

    assert serialize_headless_run_state(run) == before


@pytest.mark.parametrize(
    ("vouchers", "hand_size"),
    [
        (("v_paint_brush",), 9),
        (("v_paint_brush", "v_palette"), 10),
    ],
)
def test_env_r4_ordinary_boss_discard_uses_exact_voucher_hand_size(
    vouchers,
    hand_size,
):
    run = _boss_run("The Goad", vouchers=vouchers)

    result = apply_supported_tactical_discard(run, (0, 2))

    assert len(run.public.hand) == run.public.hand_size == hand_size
    assert len(result.public.hand) == result.public.hand_size == hand_size
    assert result.public.vouchers == list(vouchers)


@pytest.mark.parametrize(
    ("vouchers", "hand_size"),
    [
        (("v_paint_brush",), 8),
        (("v_paint_brush",), 10),
        (("v_palette",), 9),
    ],
)
def test_env_r4_ordinary_boss_discard_rejects_inexact_voucher_hand_size(
    vouchers,
    hand_size,
):
    run = _boss_run("The Goad", vouchers=vouchers)
    run.public.hand_size = hand_size
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match="ordinary Red Deck resource"):
        apply_supported_tactical_discard(run, (0,))

    assert serialize_headless_run_state(run) == before


def test_env_r4_mutable_rule_boss_discard_requires_authoritative_state():
    run = _boss_run("The Mouth")
    run.public.boss_blind_state_observed = False
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match="authoritative Boss state"):
        apply_supported_tactical_discard(run, (0,))

    assert serialize_headless_run_state(run) == before


def test_env_r4_splash_does_not_score_the_heads_debuffed_kicker():
    from games.balatro.env.play_transition import apply_supported_ordinary_play

    run = _boss_run("The Head")
    indices = (0, 1, 2, 3)
    assert [(run.public.hand[i].rank, run.public.hand[i].debuffed) for i in indices] == [
        ("A", False), ("A", False), ("K", True), ("J", False),
    ]
    joker = SplashJoker()
    joker.center = "j_splash"
    run.public.jokers = [joker]

    result = apply_supported_ordinary_play(run, indices)

    assert result.public.last_played_hand == "PAIR"
    assert result.public.score == 84
    assert all(card.played_this_ante for card in result.discard_pile)
