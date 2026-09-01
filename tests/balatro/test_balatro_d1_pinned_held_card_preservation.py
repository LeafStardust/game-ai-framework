from types import SimpleNamespace

from games.balatro.actions import BalatroAction, DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def _candidate(*, pinned: bool):
    return SimpleNamespace(
        strategy_id="held_kings_engine",
        pinned=pinned,
        bond_ids=("held_cards", "held_retrigger", "kings"),
        prescriptions=("preserve held Kings",),
    )


def _composition(*, candidate, pinned_strategy_id):
    return SimpleNamespace(
        pinned_strategy_id=pinned_strategy_id,
        strategy_candidates=(candidate,),
    )


def _policy_with_composition(composition):
    policy = StrategyAwareLiveHandActionPolicy.__new__(StrategyAwareLiveHandActionPolicy)
    policy._composition = lambda state: ((), composition)
    return policy


def _card(rank, *, enhancement=None, seal=None):
    return SimpleNamespace(rank=rank, enhancement=enhancement, seal=seal)


def test_forming_strategy_has_no_held_card_preservation_authority():
    candidate = _candidate(pinned=False)
    policy = _policy_with_composition(
        _composition(candidate=candidate, pinned_strategy_id=candidate.strategy_id)
    )
    king = _card("K")

    value, rationale = policy._pinned_card_preservation(
        SimpleNamespace(),
        BalatroAction(DISCARD_CARDS, [king]),
    )

    assert value == 0.0
    assert rationale == ()


def test_pinned_strategy_preserves_held_engine_cards_within_d1_choice_class():
    candidate = _candidate(pinned=True)
    policy = _policy_with_composition(
        _composition(candidate=candidate, pinned_strategy_id=candidate.strategy_id)
    )
    red_seal_king = _card("K", seal="Red")
    unrelated_card = _card("7")

    discard_value, discard_rationale = policy._pinned_card_preservation(
        SimpleNamespace(),
        BalatroAction(DISCARD_CARDS, [red_seal_king]),
    )
    play_value, play_rationale = policy._pinned_card_preservation(
        SimpleNamespace(),
        BalatroAction(PLAY_CARDS, [red_seal_king]),
    )
    unrelated_value, unrelated_rationale = policy._pinned_card_preservation(
        SimpleNamespace(),
        BalatroAction(DISCARD_CARDS, [unrelated_card]),
    )

    assert discard_value == -1.65
    assert play_value == -1.65
    assert discard_rationale == play_rationale
    assert any("preserves held K" in note for note in discard_rationale)
    assert any("Red Seal amplifies pinned held engine" in note for note in discard_rationale)
    assert unrelated_value == 0.0
    assert unrelated_rationale == (
        "pinned strategy held_kings_engine sacrifices no held-engine card",
    )


def test_pinned_preservation_requires_the_candidate_to_be_the_pinned_strategy():
    candidate = _candidate(pinned=True)
    policy = _policy_with_composition(
        _composition(candidate=candidate, pinned_strategy_id="different_strategy")
    )

    value, rationale = policy._pinned_card_preservation(
        SimpleNamespace(),
        BalatroAction(DISCARD_CARDS, [_card("K")]),
    )

    assert value == 0.0
    assert rationale == ()
