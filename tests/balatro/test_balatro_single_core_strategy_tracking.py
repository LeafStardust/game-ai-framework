import pytest

from games.balatro.bonds.composer import compose_build
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.state import BalatroState


class BurntJoker:
    pass


class VampireJoker:
    pass


class MidasMaskJoker:
    pass


class BaronJoker:
    pass


class MimeJoker:
    pass


class PhotographJoker:
    pass


class HangingChadJoker:
    pass


class HackJoker:
    pass


def test_burnt_core_alone_creates_forming_missing_piece_plan():
    state = BalatroState()
    state.jokers = [BurntJoker()]

    composition = compose_build(state, ())
    plan = composition.strategy_plan

    assert plan is not None
    assert plan.strategy_id == "burnt_target_level"
    assert plan.commitment == StrategyCommitment.FORMING
    assert composition.pinned_strategy_id is None
    assert "BURNT_JOKER" in plan.present_components
    assert "TARGET_HAND_LEVEL" in plan.missing_components
    assert "LEVELING_SUPPORT" in plan.missing_components
    assert "seek_component:TARGET_HAND_LEVEL" in plan.prescriptions
    assert "seek_component:LEVELING_SUPPORT" in plan.prescriptions


def test_vampire_core_alone_tracks_midas_and_feedstock_as_missing():
    state = BalatroState()
    state.jokers = [VampireJoker()]
    state.owned_deck = []

    composition = compose_build(state, ())
    plan = composition.strategy_plan

    assert plan is not None
    assert plan.strategy_id == "vampire_midas"
    assert plan.commitment == StrategyCommitment.FORMING
    assert composition.pinned_strategy_id is None
    assert plan.present_components == ("VAMPIRE",)
    assert "MIDAS_MASK" in plan.missing_components
    assert "ENHANCEMENT_FEEDSTOCK" in plan.missing_components
    assert "seek_component:MIDAS_MASK" in plan.prescriptions


@pytest.mark.parametrize(
    ("joker_type", "strategy_id", "present_component"),
    (
        (BaronJoker, "baron_mime_steel", "BARON"),
        (MimeJoker, "baron_mime_steel", "MIME"),
        (PhotographJoker, "photograph_hanging_chad", "PHOTOGRAPH"),
        (HangingChadJoker, "photograph_hanging_chad", "HANGING_CHAD"),
        (MidasMaskJoker, "vampire_midas", "MIDAS_MASK"),
        (HackJoker, "low_rank_hack_retrigger", "HACK"),
    ),
)
def test_every_other_defining_core_alone_creates_forming_plan(
    joker_type,
    strategy_id,
    present_component,
):
    state = BalatroState()
    state.jokers = [joker_type()]
    state.owned_deck = []

    composition = compose_build(state, ())
    plan = composition.strategy_plan

    assert plan is not None
    assert plan.strategy_id == strategy_id
    assert plan.commitment == StrategyCommitment.FORMING
    assert composition.pinned_strategy_id is None
    assert present_component in plan.present_components
    assert plan.missing_components
    assert any(
        prescription.startswith("seek_component:")
        for prescription in plan.prescriptions
    )


def test_ambient_infrastructure_without_defining_core_does_not_form_known_plan():
    state = BalatroState()
    state.jokers = []

    composition = compose_build(state, ())

    assert composition.pinned_strategy_id is None
    assert composition.strategy_plan is None
    assert all(
        candidate.commitment < StrategyCommitment.FORMING
        for candidate in composition.strategy_candidates
        if candidate.motif_ids
    )
