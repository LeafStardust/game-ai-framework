import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_progression import activate_selected_blind_progression
from games.balatro.env.consumable_use import can_use_planet_exact
from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.observation_encoding import encode_public_observation
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.select_blind import select_blind_exact
from games.balatro.env.shop_repricing import reprice_exact_generated_shop
from games.balatro.env.spectral_inventory import GeneratedHeldSpectral, generate_held_spectral
from games.balatro.env.state import EnvStateFrame, RunStatus, TurnOwner
from games.balatro.env.transition import HeadlessTransitionError
from games.balatro.jokers.dna import DNAJoker
from games.balatro.jokers.seance import SeanceJoker
from games.balatro.jokers.sixth_sense import SixthSenseJoker


def _run():
    run = pristine_red_white_reset(15)
    run.public.phase = "SELECTING_HAND"
    run.public.shop_inflation_observed = True
    run.consumable_usage_observed = True
    return run


def test_env_r2_seance_inventory_discovers_cards_and_suppresses_held_duplicates():
    run = _run()
    assert run.generated_center_discovered("c_incantation") is False

    generate_held_spectral(run)
    generate_held_spectral(run)

    first, second = run.public.consumables
    assert type(first) is type(second) is GeneratedHeldSpectral
    assert (first.center_key, second.center_key) == ("c_cryptid", "c_medium")
    assert "Spectralsea1_resample2" in run.rng.nodes
    for item in (first, second):
        assert item.price == 4
        assert run.generated_center_discovered(item.center_key) is True
        assert item.center_key in run.tag_profile_state.discovered_center_keys
    snapshot = run.rng_snapshot()
    generate_held_spectral(run)
    assert run.public.consumables == [first, second]
    assert run.rng_snapshot() == snapshot

    assert not can_use_planet_exact(run, 0)
    assert not can_use_planet_exact(run, 1)
    frame = EnvStateFrame(run.public, RunStatus.RUNNING, TurnOwner.TACTICAL_POLICY)
    assert encode_public_observation(frame).shape == (3321,)


def test_env_r2_seance_missing_profile_authority_fails_before_draw():
    run = _run()
    del run.generation_discovery["c_incantation"]
    snapshot = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="Spectral authority"):
        generate_held_spectral(run)

    assert run.rng_snapshot() == snapshot
    assert run.public.consumables == []


def test_env_r2_held_spectral_reprices_with_canonical_discount():
    run = _run()
    generate_held_spectral(run)
    run.public.phase = "SHOP"
    run.public.shop_active = True
    original = run.public.consumables[0]

    for discount, expected in ((25, 3), (50, 2)):
        result = reprice_exact_generated_shop(run, discount_percent=discount)
        assert result.public.consumables == [GeneratedHeldSpectral(original.center_key, expected)]
        assert run.public.consumables == [original]
        assert result.rng_snapshot() == run.rng_snapshot()


_STRAIGHT_FLUSH_INDICES = (0, 1, 2, 4, 5)


def _seance_play_run(*, mouth_locked=False):
    run = pristine_red_white_reset(9)
    state = run.public
    state.phase = "DRAW_TO_HAND"
    state.shop_inflation_observed = True
    state.blind = Blind(BlindType.SMALL, requirement=99_999)
    state.blind_score = 99_999
    state.hands_remaining = 4
    state.discards_remaining = 3
    if mouth_locked:
        state.blind = Blind(BlindType.BOSS, requirement=99_999)
        state.blind_is_boss = True
        state.boss_name = "The Mouth"
        state.boss_blind_state_observed = True
        state.boss_blind_only_hand = "PAIR"
    joker = SeanceJoker()
    joker.center = "j_seance"
    state.jokers = [joker]
    return deal_supported_round_start(run)


def test_env_r4_seance_play_generates_from_scoring_callback_in_order():
    run = _seance_play_run()
    run.public.jokers.append(SeanceJoker())
    run.public.jokers[1].center = "j_seance"
    before = run.rng_snapshot()
    expected = run.copy()
    generate_held_spectral(expected)
    generate_held_spectral(expected)

    result = apply_supported_ordinary_play(run, _STRAIGHT_FLUSH_INDICES)

    assert result.public.last_played_hand == "STRAIGHT_FLUSH"
    assert result.public.score > 0
    assert len(result.public.consumables) == 2
    assert result.public.consumables == expected.public.consumables
    assert result.rng_snapshot() == expected.rng_snapshot()
    assert run.public.consumables == []
    assert run.rng_snapshot() == before


@pytest.mark.parametrize("boundary", ["high_card", "full", "mouth"])
def test_env_r4_seance_play_consumes_no_spectral_rng_at_inert_boundaries(boundary):
    run = _seance_play_run(mouth_locked=boundary == "mouth")
    if boundary == "full":
        generate_held_spectral(run)
        generate_held_spectral(run)
    indices = (0,) if boundary == "high_card" else _STRAIGHT_FLUSH_INDICES

    result = apply_supported_ordinary_play(run, indices)

    assert result.public.last_played_hand == (
        "HIGH_CARD" if boundary == "high_card" else "STRAIGHT_FLUSH"
    )
    if boundary == "mouth":
        assert result.public.score == 0
    assert result.public.consumables == run.public.consumables
    assert result.rng_snapshot() == run.rng_snapshot()


def _sixth_sense_dealt_run():
    run = pristine_red_white_reset("RUNNER-4")
    run.public.shop_inflation_observed = True
    dealt = select_blind_exact(activate_selected_blind_progression(run))
    joker = SixthSenseJoker()
    joker.center = "j_sixth_sense"
    dealt.public.jokers = [joker]
    assert (dealt.public.hand[3].rank, dealt.public.hand[3].suit) == ("6", "Hearts")
    return dealt


@pytest.mark.parametrize(("full", "with_dna"), [(False, False), (True, False), (False, True)])
def test_env_r2_sixth_sense_scores_then_removes_six_and_respects_spectral_room(full, with_dna):
    run = _sixth_sense_dealt_run()
    if full:
        run.public.consumables = [GeneratedHeldSpectral("c_medium", 4), GeneratedHeldSpectral("c_wraith", 4)]
    if with_dna:
        dna = DNAJoker()
        dna.center = "j_dna"
        run.public.jokers.append(dna)
    before = run.rng_snapshot()

    result = apply_supported_ordinary_play(run, (3,))

    assert result.public.score == 11
    assert result.removed_base_six_suits == ("Hearts",)
    assert result.played_pile == result.discard_pile == []
    sixes = [
        card for card in result.require_playing_card_order()
        if (card.rank, card.suit) == ("6", "Hearts")
    ]
    assert len(result.public.owned_deck) == 51 + int(with_dna)
    assert len(sixes) == int(with_dna)
    if with_dna:
        assert any(card is sixes[0] for card in result.public.hand)
        assert result.require_playing_card_order()[-1] is sixes[0]
    if full:
        assert result.public.consumables == run.public.consumables
        assert result.rng_snapshot() == before
    else:
        assert result.public.consumables == [GeneratedHeldSpectral("c_ouija", 4)]
        assert result.generated_center_discovered("c_ouija") is True
        assert set(result.rng.nodes) - set(run.rng.nodes) == {"Spectralsixth1"}
    assert run.removed_base_six_suits == ()
    assert len(run.public.owned_deck) == 52


def test_env_r2_sixth_sense_leaves_multicard_or_later_six_in_discard():
    run = _sixth_sense_dealt_run()
    multicard = apply_supported_ordinary_play(run, (0, 3))
    later = apply_supported_ordinary_play(run, (0,))
    six_index = next(
        i for i, card in enumerate(later.public.hand)
        if (card.rank, card.suit) == ("6", "Hearts")
    )
    later = apply_supported_ordinary_play(later, (six_index,))

    for result in (multicard, later):
        assert result.removed_base_six_suits == ()
        assert result.public.consumables == []
        assert result.rng_snapshot() == run.rng_snapshot()
        assert any((card.rank, card.suit) == ("6", "Hearts") for card in result.discard_pile)


def test_env_r2_sixth_sense_spectral_domain_retries_held_center_independently():
    run = _run()

    generate_held_spectral(run, key_append="sixth")
    generate_held_spectral(run, key_append="sixth")

    assert [card.center_key for card in run.public.consumables] == ["c_medium", "c_wraith"]
    assert {key for key in run.rng.nodes if key.startswith("Spectral")} == {
        "Spectralsixth1", "Spectralsixth1_resample2",
    }
