from types import SimpleNamespace

import pytest

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.tactical_transition import (
    apply_planned_tactical_step,
    apply_supported_tactical_discard,
)
from games.balatro.env.shop_items import (
    GeneratedShopJokerItem,
    materialize_generated_shop_joker_for_acquisition,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _dealt_run(*, seed="R4-DISCARD"):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "DRAW_TO_HAND"
    state.discards_remaining = 3
    state.discards_used = 0
    run = HeadlessRunState(public=state, seed=seed)
    return deal_supported_round_start(run)


def _ordinary_play_run(*, seed="R4-PLAY-BRIDGE", requirement=9999):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "DRAW_TO_HAND"
    state.discards_remaining = 3
    state.discards_used = 0
    state.blind = Blind(BlindType.SMALL, requirement)
    run = HeadlessRunState(public=state, seed=seed)
    return deal_supported_round_start(run)


def _card_signature(card):
    return (
        card.rank,
        card.suit,
        card.enhancement,
        card.edition,
        card.seal,
        card.permanent_bonus,
    )


def _state_signature(run):
    return (
        tuple(_card_signature(card) for card in run.public.hand),
        tuple(_card_signature(card) for card in run.public.deck),
        tuple(_card_signature(card) for card in run.public.discard_pile),
        tuple(_card_signature(card) for card in run.draw_pile),
        tuple(_card_signature(card) for card in run.discard_pile),
        run.public.discards_remaining,
        run.public.discards_used,
        run.public.score,
        run.public.hands_remaining,
        run.public.phase,
        tuple(sorted(run.public.hand_play_counts.items())),
        tuple(sorted(run.public.round_hand_play_counts.items())),
        run.rng_snapshot(),
    )


def test_env_r4_baseline_discard_moves_in_visible_order_updates_counters_and_refills():
    run = _dealt_run()
    selected = [_card_signature(run.public.hand[index]) for index in (1, 3)]
    rng_before = run.rng_snapshot()

    result = apply_supported_tactical_discard(run, (3, 1))

    assert [_card_signature(card) for card in result.public.discard_pile[-2:]] == selected
    assert [_card_signature(card) for card in result.discard_pile[-2:]] == selected
    assert len(result.public.hand) == result.public.hand_size == 8
    assert len(result.public.deck) == 42
    assert len(result.draw_pile) == 42
    assert result.public.discards_remaining == 2
    assert result.public.discards_used == 1
    assert result.public.phase == "SELECTING_HAND"
    assert result.rng_snapshot() == rng_before

    assert len(run.public.hand) == 8
    assert len(run.public.deck) == 44
    assert run.public.discard_pile == []
    assert run.discard_pile == []
    assert run.public.discards_remaining == 3
    assert run.public.discards_used == 0


def test_env_r4_baseline_discard_is_replay_deterministic_for_same_seed():
    left = apply_supported_tactical_discard(_dealt_run(seed="REPLAY"), (0, 2, 4))
    right = apply_supported_tactical_discard(_dealt_run(seed="REPLAY"), (4, 0, 2))

    assert _state_signature(left) == _state_signature(right)


@pytest.mark.parametrize(
    "indices, message",
    [
        ((), "1 to 5"),
        ((0, 0), "distinct"),
        ((-1,), "outside"),
        ((8,), "outside"),
        ((True,), "exact integers"),
    ],
)
def test_env_r4_baseline_discard_rejects_invalid_visible_indices(indices, message):
    run = _dealt_run()
    before = _state_signature(run)

    with pytest.raises(HeadlessTransitionError, match=message):
        apply_supported_tactical_discard(run, indices)

    assert _state_signature(run) == before


def test_env_r4_baseline_discard_fails_closed_on_purple_seal_generation():
    run = _dealt_run()
    run.public.hand[0].seal = "Purple"
    before = _state_signature(run)

    with pytest.raises(HeadlessTransitionError, match="Purple Seal"):
        apply_supported_tactical_discard(run, (0,))

    assert _state_signature(run) == before


def test_env_r4_baseline_discard_fails_closed_on_boss_or_joker_callbacks():
    boss_run = _dealt_run()
    boss_run.public.boss_name = "The Water"
    with pytest.raises(HeadlessTransitionError, match="boss discard callbacks"):
        apply_supported_tactical_discard(boss_run, (0,))

    joker_run = _dealt_run()
    joker_run.public.jokers = [object()]
    with pytest.raises(HeadlessTransitionError, match="Joker discard callbacks"):
        apply_supported_tactical_discard(joker_run, (0,))


def test_env_r4_baseline_discard_admits_exact_materialized_droll_noop_callback():
    run = _dealt_run(seed="R4-DROLL-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_droll", 1, 4, None, 4, False)
        )
    ]
    before = _card_signature(run.public.hand[0])

    result = apply_supported_tactical_discard(run, (0,))

    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "DrollJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_even_steven_noop_callback():
    run = _dealt_run(seed="R4-EVEN-STEVEN-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_even_steven", 1, 4, None, 4, False)
        )
    ]
    before = _card_signature(run.public.hand[0])

    result = apply_supported_tactical_discard(run, (0,))

    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "EvenStevenJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_devious_noop_callback():
    run = _dealt_run(seed="R4-DEVIOUS-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_devious", 1, 4, None, 4, False)
        )
    ]
    before = _card_signature(run.public.hand[0])

    result = apply_supported_tactical_discard(run, (0,))

    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "DeviousJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_gluttonous_noop_callback():
    run = _dealt_run(seed="R4-GLUTTONOUS-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_gluttenous_joker", 1, 5, None, 5, False)
        )
    ]
    before = _card_signature(run.public.hand[0])

    result = apply_supported_tactical_discard(run, (0,))

    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "GluttonousJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_scholar_noop_callback():
    run = _dealt_run(seed="R4-SCHOLAR-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_scholar", 1, 4, None, 4, False)
        )
    ]
    before = _card_signature(run.public.hand[0])

    result = apply_supported_tactical_discard(run, (0,))

    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "ScholarJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_blue_joker_noop_callback():
    run = _dealt_run(seed="R4-BLUE-JOKER-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_blue_joker", 1, 5, None, 5, False)
        )
    ]
    before = _card_signature(run.public.hand[0])

    result = apply_supported_tactical_discard(run, (0,))

    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert len(result.public.deck) == len(run.public.deck) - 1
    assert type(result.public.jokers[0]).__name__ == "BlueJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_jolly_noop_callback():
    run = _dealt_run(seed="R4-JOLLY-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_jolly", 1, 3, None, 3, False)
        )
    ]
    before = _card_signature(run.public.hand[0])

    result = apply_supported_tactical_discard(run, (0,))

    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "JollyJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_sly_noop_callback():
    run = _dealt_run(seed="R4-SLY-DISCARD")
    run.public.jokers = [materialize_generated_shop_joker_for_acquisition(
        GeneratedShopJokerItem("j_sly", 1, 3, None, 3, False)
    )]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "SlyJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_wily_noop_callback():
    run = _dealt_run(seed="R4-WILY-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_wily", 1, 4, None, 4, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "WilyJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_abstract_noop_callback():
    run = _dealt_run(seed="R4-ABSTRACT-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_abstract", 1, 4, None, 4, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "AbstractJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_photograph_noop_callback():
    run = _dealt_run(seed="R4-PHOTOGRAPH-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_photograph", 1, 5, None, 5, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "PhotographJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_half_noop_callback():
    run = _dealt_run(seed="R4-HALF-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_half", 1, 5, None, 5, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "HalfJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_mystic_summit_noop_callback():
    run = _dealt_run(seed="R4-MYSTIC-SUMMIT-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_mystic_summit", 1, 5, None, 5, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "MysticSummitJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_banner_noop_callback():
    run = _dealt_run(seed="R4-BANNER-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_banner", 1, 5, None, 5, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "BannerJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_scary_face_noop_callback():
    run = _dealt_run(seed="R4-SCARY-FACE-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_scary_face", 1, 4, None, 4, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "ScaryFaceJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_walkie_talkie_noop_callback():
    run = _dealt_run(seed="R4-WALKIE-TALKIE-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_walkie_talkie", 1, 4, None, 4, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "WalkieTalkieJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_smiley_face_noop_callback():
    run = _dealt_run(seed="R4-SMILEY-FACE-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_smiley", 1, 4, None, 4, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "SmileyFaceJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_raised_fist_noop_callback():
    run = _dealt_run(seed="R4-RAISED-FIST-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_raised_fist", 1, 5, None, 5, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "RaisedFistJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_clever_joker_noop_callback():
    run = _dealt_run(seed="R4-CLEVER-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_clever", 1, 4, None, 4, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "CleverJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_mad_joker_noop_callback():
    run = _dealt_run(seed="R4-MAD-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_mad", 1, 4, None, 4, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "MadJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_zany_joker_noop_callback():
    run = _dealt_run(seed="R4-ZANY-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_zany", 1, 4, None, 4, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "ZanyJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_crafty_joker_noop_callback():
    run = _dealt_run(seed="R4-CRAFTY-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_crafty", 1, 4, None, 4, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "CraftyJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_crazy_joker_noop_callback():
    run = _dealt_run(seed="R4-CRAZY-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_crazy", 1, 4, None, 4, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "CrazyJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_greedy_joker_noop_callback():
    run = _dealt_run(seed="R4-GREEDY-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_greedy_joker", 1, 5, None, 5, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "GreedyJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_lusty_joker_noop_callback():
    run = _dealt_run(seed="R4-LUSTY-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_lusty_joker", 1, 5, None, 5, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "LustyJoker"


def test_env_r4_baseline_discard_admits_exact_materialized_wrathful_joker_noop_callback():
    run = _dealt_run(seed="R4-WRATHFUL-DISCARD")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_wrathful_joker", 1, 5, None, 5, False)
        )
    ]
    before = _card_signature(run.public.hand[0])
    result = apply_supported_tactical_discard(run, (0,))
    assert _card_signature(result.public.discard_pile[-1]) == before
    assert result.public.discards_remaining == 2
    assert type(result.public.jokers[0]).__name__ == "WrathfulJoker"


def test_env_r4_baseline_discard_requires_authoritative_private_draw_zone():
    run = _dealt_run()
    run.draw_pile.pop()

    with pytest.raises(HeadlessTransitionError, match="private/public draw zones"):
        apply_supported_tactical_discard(run, (0,))


class _DiscardDecisionEngine:
    def __init__(self, indices):
        self.indices = tuple(indices)
        self.observation = None

    def decide(self, state):
        self.observation = state
        return SimpleNamespace(
            action=BalatroAction(
                DISCARD_CARDS,
                cards=[state.hand[index] for index in self.indices],
            )
        )


class _PlayDecisionEngine:
    def __init__(self):
        self.observation = None

    def decide(self, state):
        self.observation = state
        return SimpleNamespace(action=BalatroAction(PLAY_CARDS, cards=[state.hand[0]]))


def test_env_r4_decision_engine_bridge_executes_discard_by_public_visible_positions():
    run = _dealt_run(seed="BRIDGE")
    selected = [_card_signature(run.public.hand[index]) for index in (0, 2)]
    decision_engine = _DiscardDecisionEngine((2, 0))

    result = apply_planned_tactical_step(run, decision_engine)

    assert [_card_signature(card) for card in result.public.discard_pile[-2:]] == selected
    assert result.public.discards_remaining == 2
    assert decision_engine.observation is not run.public


def test_env_r4_decision_engine_bridge_masks_face_down_identity_before_selection():
    run = _dealt_run(seed="MASK")
    hidden_signature = _card_signature(run.public.hand[0])
    run.public.hand[0].face_down = True
    decision_engine = _DiscardDecisionEngine((0,))

    result = apply_planned_tactical_step(run, decision_engine)

    observed = decision_engine.observation.hand[0]
    assert observed.face_down is True
    assert observed.rank == "?"
    assert observed.suit == "?"
    assert observed.live_id is None
    assert _card_signature(result.public.discard_pile[-1]) == hidden_signature


def test_env_r4_decision_engine_bridge_executes_supported_ordinary_play():
    run = _ordinary_play_run(seed="PLAY-OPEN")
    selected = _card_signature(run.public.hand[0])
    decision_engine = _PlayDecisionEngine()

    result = apply_planned_tactical_step(run, decision_engine)

    assert result.public.phase == "SELECTING_HAND"
    assert result.public.score > 0
    assert result.public.hands_remaining == 3
    assert _card_signature(result.public.discard_pile[-1]) == selected
    assert decision_engine.observation is not run.public


def test_env_r4_decision_engine_bridge_keeps_unsupported_play_effects_fail_closed():
    run = _ordinary_play_run(seed="PLAY-CLOSED")
    run.public.jokers = [object()]
    before = _state_signature(run)

    with pytest.raises(HeadlessTransitionError, match="Joker callbacks"):
        apply_planned_tactical_step(run, _PlayDecisionEngine())

    assert _state_signature(run) == before


def test_env_r4_decision_engine_bridge_rejects_selected_card_not_from_observation():
    run = _dealt_run(seed="FOREIGN")

    class ForeignDecisionEngine:
        def decide(self, state):
            foreign = state.hand[0].__class__("A", "Spades")
            return SimpleNamespace(action=BalatroAction(DISCARD_CARDS, cards=[foreign]))

    with pytest.raises(HeadlessTransitionError, match="outside its public observation"):
        apply_planned_tactical_step(run, ForeignDecisionEngine())


def test_env_r4_decision_engine_bridge_rejects_legacy_plan_only_shape():
    run = _dealt_run(seed="PLAN-ONLY")

    class PlanOnly:
        def plan(self, state):
            return SimpleNamespace(
                action=BalatroAction(DISCARD_CARDS, cards=[state.hand[0]])
            )

    with pytest.raises(TypeError, match=r"provide decide\(state\)"):
        apply_planned_tactical_step(run, PlanOnly())
