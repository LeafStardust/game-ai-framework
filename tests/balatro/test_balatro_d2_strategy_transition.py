from types import SimpleNamespace

import pytest

from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.joker_policy import _strategy_transition_bonus


def _candidate(
    strategy_id: str,
    *,
    commitment: StrategyCommitment,
    strength: float,
):
    return SimpleNamespace(
        strategy_id=strategy_id,
        commitment=commitment,
        strength=strength,
    )


def _plan(
    strategy_id: str,
    *,
    commitment: StrategyCommitment,
    completion: float,
    missing_components=(),
    missing_features=(),
):
    return SimpleNamespace(
        strategy_id=strategy_id,
        commitment=commitment,
        completion=completion,
        missing_components=tuple(missing_components),
        missing_features=tuple(missing_features),
    )


def _composition(*, pinned=None, candidates=(), plan=None):
    return SimpleNamespace(
        pinned_strategy_id=pinned,
        strategy_candidates=tuple(candidates),
        strategy_plan=plan,
    )


def test_d2_strategy_transition_rewards_new_pinned_strategy():
    before = _composition(
        plan=_plan(
            "baron_mime_steel",
            commitment=StrategyCommitment.FORMING,
            completion=0.30,
            missing_components=("MIME", "STEEL"),
        )
    )
    after_candidate = _candidate(
        "baron_mime_steel",
        commitment=StrategyCommitment.PINNED,
        strength=8.0,
    )
    after = _composition(
        pinned="baron_mime_steel",
        candidates=(after_candidate,),
        plan=_plan(
            "baron_mime_steel",
            commitment=StrategyCommitment.PINNED,
            completion=0.55,
            missing_components=("STEEL",),
        ),
    )

    bonus, rationale = _strategy_transition_bonus(before, after)

    assert bonus > 0.0
    assert bonus <= 2.5
    assert any("strategy formed=baron_mime_steel" in note for note in rationale)
    assert any("strategy plan progress=" in note for note in rationale)


def test_d2_strategy_transition_rewards_same_strategy_commitment_and_strength_gain():
    before_candidate = _candidate(
        "baron_mime_steel",
        commitment=StrategyCommitment.PINNED,
        strength=8.0,
    )
    after_candidate = _candidate(
        "baron_mime_steel",
        commitment=StrategyCommitment.ESTABLISHED,
        strength=10.0,
    )
    before = _composition(
        pinned="baron_mime_steel",
        candidates=(before_candidate,),
        plan=_plan(
            "baron_mime_steel",
            commitment=StrategyCommitment.PINNED,
            completion=0.55,
            missing_features=("held:retrigger",),
        ),
    )
    after = _composition(
        pinned="baron_mime_steel",
        candidates=(after_candidate,),
        plan=_plan(
            "baron_mime_steel",
            commitment=StrategyCommitment.ESTABLISHED,
            completion=0.70,
            missing_features=(),
        ),
    )

    bonus, rationale = _strategy_transition_bonus(before, after)

    assert bonus > 0.0
    assert bonus <= 2.5
    assert any("strategy commitment=PINNED->ESTABLISHED" in note for note in rationale)
    assert any("same-strategy strength=8.000->10.000" in note for note in rationale)
    assert any("missing goals=1->0" in note for note in rationale)


def test_d2_strategy_transition_rewards_only_materially_stronger_pinned_pivot():
    before_candidate = _candidate(
        "old_engine",
        commitment=StrategyCommitment.PINNED,
        strength=8.0,
    )
    weak_pivot = _candidate(
        "new_engine",
        commitment=StrategyCommitment.PINNED,
        strength=9.5,
    )
    strong_pivot = _candidate(
        "new_engine",
        commitment=StrategyCommitment.PINNED,
        strength=10.5,
    )
    before = _composition(
        pinned="old_engine",
        candidates=(before_candidate,),
    )

    weak_bonus, weak_rationale = _strategy_transition_bonus(
        before,
        _composition(pinned="new_engine", candidates=(weak_pivot,)),
    )
    strong_bonus, strong_rationale = _strategy_transition_bonus(
        before,
        _composition(pinned="new_engine", candidates=(strong_pivot,)),
    )

    assert weak_bonus == 0.0
    assert weak_rationale == ()
    assert strong_bonus > 0.0
    assert any("materially stronger pinned pivot=" in note for note in strong_rationale)


def test_d2_strategy_transition_is_hard_capped():
    before_candidate = _candidate(
        "engine",
        commitment=StrategyCommitment.PINNED,
        strength=1.0,
    )
    after_candidate = _candidate(
        "engine",
        commitment=StrategyCommitment.DOMINANT,
        strength=100.0,
    )
    before = _composition(
        pinned="engine",
        candidates=(before_candidate,),
        plan=_plan(
            "engine",
            commitment=StrategyCommitment.PINNED,
            completion=0.0,
            missing_components=("A", "B"),
            missing_features=("x", "y"),
        ),
    )
    after = _composition(
        pinned="engine",
        candidates=(after_candidate,),
        plan=_plan(
            "engine",
            commitment=StrategyCommitment.DOMINANT,
            completion=1.0,
        ),
    )

    bonus, _ = _strategy_transition_bonus(before, after)

    assert bonus == pytest.approx(2.5)
