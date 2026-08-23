from dataclasses import dataclass
from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.boss_trigger import boss_hand_is_debuffed
from games.balatro.mouth_hand_policy import apply_mouth_first_hand_policy


@dataclass(frozen=True)
class _Decision:
    mode: str; action: object; selected_plan: object; pace_target: float = 100.0
    selected_immediate_score: float | None = None; selected_pace_ratio: float | None = None
    selected_fallback_value: float | None = None; confidence: float = 0.5; rationale: tuple[str, ...] = ()


class _Action:
    def __init__(self, name, hand_type="", score=0.0):
        self.name=name; self.cards=[SimpleNamespace(hand_type=hand_type)] if hand_type else []; self.score=float(score)
class _Plan:
    def __init__(self, action): self.action=action
class _Evaluator:
    def project_play(self, state, action): return SimpleNamespace(expected_hand_score=action.score)
    def evaluate(self, state, action): return 1.0 if action.name == DISCARD_CARDS else action.score
class _HandEvaluator:
    def evaluate(self, cards): return SimpleNamespace(value=cards[0].hand_type)


class _Policy:
    def __init__(self, preferred=()):
        self.preferred=tuple(preferred); self.evaluator=_Evaluator(); self._hand_evaluator=_HandEvaluator()
    def _hand_bond_intents(self, state):
        del state
        return tuple((hand, 1.0, ("test Bond intent",)) for hand in self.preferred)
    def _strategy_fit(self, state, action):
        del state
        if action.name != PLAY_CARDS: return (2.0, ())
        return (5.0 if action.cards[0].hand_type in self.preferred else 0.0, ())
    def _within_type_key(self, plan): return (0.0,)


def _state(*, only_hand=None, discards=3, blind_score=1000, score=0):
    return SimpleNamespace(boss_name="The Mouth", boss_blind_only_hand=only_hand,
        boss_blind_state_observed=True, round_hand_play_counts={"PAIR":0,"HIGH_CARD":0},
        jokers=[], discards_remaining=discards, blind_score=blind_score, score=score)


def test_mouth_existing_lock_rejects_other_hand_types():
    state=_state(only_hand="PAIR")
    assert boss_hand_is_debuffed(state,"PAIR",[object()]).triggered is False
    assert boss_hand_is_debuffed(state,"HIGH_CARD",[object()]).triggered is True


def test_mouth_first_hand_locks_to_primary_strategy_hand_when_available():
    policy=_Policy(("PAIR",)); pair=_Plan(_Action(PLAY_CARDS,"PAIR",120)); high=_Plan(_Action(PLAY_CARDS,"HIGH_CARD",180))
    result=apply_mouth_first_hand_policy(policy,_state(blind_score=1000),(high,pair),_Decision("PACE_PLAY",high.action,high))
    assert result.action is pair.action; assert result.selected_plan is pair
    assert any("developed Bonds target PAIR" in note for note in result.rationale)


def test_mouth_discards_instead_of_locking_wrong_hand_when_primary_type_missing():
    policy=_Policy(("PAIR",)); high=_Plan(_Action(PLAY_CARDS,"HIGH_CARD",180)); discard=_Plan(_Action(DISCARD_CARDS))
    result=apply_mouth_first_hand_policy(policy,_state(discards=2,blind_score=1000),(high,discard),_Decision("PACE_PLAY",high.action,high))
    assert result.action is discard.action; assert result.mode == "PACE_RECOVERY"
    assert any("use a discard instead of locking" in note for note in result.rationale)


def test_mouth_immediate_one_hand_clear_overrides_strategy_lock_preference():
    policy=_Policy(("PAIR",)); pair=_Plan(_Action(PLAY_CARDS,"PAIR",400)); high=_Plan(_Action(PLAY_CARDS,"HIGH_CARD",1000))
    result=apply_mouth_first_hand_policy(policy,_state(blind_score=900),(pair,high),_Decision("PACE_PLAY",pair.action,pair))
    assert result.action is high.action; assert any("immediately clears the blind" in note for note in result.rationale)


def test_mouth_without_prescribed_hand_locks_highest_projected_scoring_hand():
    policy=_Policy(()); pair=_Plan(_Action(PLAY_CARDS,"PAIR",130)); high=_Plan(_Action(PLAY_CARDS,"HIGH_CARD",90))
    result=apply_mouth_first_hand_policy(policy,_state(blind_score=1000),(high,pair),_Decision("PACE_PLAY",high.action,high))
    assert result.action is pair.action; assert any("highest projected scoring legal hand" in note for note in result.rationale)
