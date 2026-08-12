from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS
from games.balatro.live.hand_action_policy import CLEAR_PATH
from games.balatro.live.external.live_memory_hand_action_execute_validation import (
    _decision_guard_errors,
    _parse_indices,
    _state_fingerprint,
    _wait_semantic_checkpoint,
)


def _card(live_id, rank="4", suit="Hearts"):
    return SimpleNamespace(
        live_id=live_id,
        rank=rank,
        suit=suit,
        enhancement=None,
        edition=None,
        seal=None,
    )


def _state(*, cards, score=0, hands=4, discards=4, phase="SELECTING_HAND"):
    return SimpleNamespace(
        phase=phase,
        hand=list(cards),
        score=score,
        hands_remaining=hands,
        discards_remaining=discards,
    )


def _decision(cards, *, confirmed=True, clear=0.75):
    action = SimpleNamespace(name=PLAY_CARDS, cards=list(cards))
    plan = SimpleNamespace(
        action=action,
        exact=False,
        value=SimpleNamespace(clear_probability=clear),
    )
    return SimpleNamespace(
        mode=CLEAR_PATH,
        action=action,
        selected_plan=plan,
        sampled_clear_path_confirmed=confirmed,
        selected_pace_ratio=0.48,
        confidence=0.75,
    )


def test_parse_indices_canonicalizes_order():
    assert _parse_indices("5, 3,4") == (3, 4, 5)


def test_matching_confirmed_sampled_clear_path_passes_execution_guard():
    hand = [_card(index, rank=str(index)) for index in range(8)]
    selected = [hand[3], hand[4], hand[5]]
    state = _state(cards=hand)
    decision = _decision(selected, confirmed=True, clear=0.75)

    errors = _decision_guard_errors(
        decision,
        state,
        expect_mode=CLEAR_PATH,
        expect_action=PLAY_CARDS,
        expect_indices=(3, 4, 5),
        min_clear_probability=0.75,
        min_pace_ratio=None,
    )

    assert errors == ()


def test_unconfirmed_sampled_clear_path_is_blocked():
    hand = [_card(index, rank=str(index)) for index in range(8)]
    decision = _decision([hand[3], hand[4], hand[5]], confirmed=False, clear=0.80)

    errors = _decision_guard_errors(
        decision,
        _state(cards=hand),
        expect_mode=CLEAR_PATH,
        expect_action=PLAY_CARDS,
        expect_indices=(3, 4, 5),
        min_clear_probability=0.75,
        min_pace_ratio=None,
    )

    assert any("not confirmed" in error for error in errors)


def test_clear_path_below_explicit_execution_floor_is_blocked():
    hand = [_card(index, rank=str(index)) for index in range(8)]
    decision = _decision([hand[3], hand[4], hand[5]], confirmed=True, clear=0.74)

    errors = _decision_guard_errors(
        decision,
        _state(cards=hand),
        expect_mode=CLEAR_PATH,
        expect_action=PLAY_CARDS,
        expect_indices=(3, 4, 5),
        min_clear_probability=0.75,
        min_pace_ratio=None,
    )

    assert any("fell below" in error for error in errors)


def test_state_fingerprint_detects_live_hand_identity_change():
    before = _state(cards=[_card(1), _card(2)])
    after = _state(cards=[_card(1), _card(3)])

    assert _state_fingerprint(before) != _state_fingerprint(after)


class _Observer:
    def __init__(self, snapshots):
        self.snapshots = iter(snapshots)

    def observe(self):
        return next(self.snapshots)


class _Translator:
    @staticmethod
    def translate(snapshot):
        return snapshot.state


def test_play_checkpoint_requires_one_fewer_hand_or_round_eval():
    cards = [_card(1), _card(2)]
    before_state = _state(cards=cards, hands=4, discards=4)
    before = SimpleNamespace(sequence=10, state=before_state)
    transient = SimpleNamespace(
        sequence=11,
        state=_state(cards=cards, hands=4, discards=4),
    )
    settled = SimpleNamespace(
        sequence=12,
        state=_state(cards=[_card(3), _card(4)], hands=3, discards=4),
    )

    snapshot, state = _wait_semantic_checkpoint(
        _Observer([transient, settled]),
        _Translator(),
        before_snapshot=before,
        before_state=before_state,
        action_name=PLAY_CARDS,
        timeout=0.1,
        poll_interval=0.0,
    )

    assert snapshot.sequence == 12
    assert state.hands_remaining == 3
