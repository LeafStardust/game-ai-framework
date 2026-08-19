from games.balatro.strategy import COMMITTED, MATURE, StrategyAssessment
from games.balatro.strategy_commitment_hysteresis import choose_post_commit_dominant


def _assessment(
    strategy_id,
    score,
    *,
    gold=0,
    silver=0,
    bronze=0,
    banned=0,
    status=COMMITTED,
):
    return StrategyAssessment(
        strategy_id=strategy_id,
        name=strategy_id,
        score=float(score),
        effectiveness=1.0,
        base_score=0.0,
        status=status,
        gold_owned=int(gold),
        silver_owned=int(silver),
        bronze_owned=int(bronze),
        banned_owned=int(banned),
        rationale=(),
    )


def test_pre_commit_raw_score_leader_remains_authoritative():
    leader = _assessment("transient", 11.0, gold=0, silver=2)
    core = _assessment("core", 10.0, gold=1)
    assert choose_post_commit_dominant((leader, core), ante=5) is leader


def test_post_commit_near_tie_prefers_stronger_gold_core():
    transient = _assessment("transient", 11.0, gold=0, silver=3)
    established = _assessment("established", 9.5, gold=1, bronze=1)
    assert (
        choose_post_commit_dominant((transient, established), ante=6)
        is established
    )


def test_post_commit_clear_score_leader_can_pivot_immediately():
    challenger = _assessment("challenger", 13.0, gold=0, silver=2)
    incumbent = _assessment("incumbent", 10.0, gold=1)
    assert (
        choose_post_commit_dominant(
            (challenger, incumbent),
            ante=6,
            pivot_margin=3.0,
        )
        is challenger
    )


def test_post_commit_near_tie_uses_total_positive_support_after_gold():
    sparse = _assessment("sparse", 10.5, gold=1, silver=0, bronze=0)
    supported = _assessment("supported", 9.5, gold=1, silver=1, bronze=1)
    assert choose_post_commit_dominant((sparse, supported), ante=7) is supported


def test_maturity_is_only_tiebreak_after_concrete_component_evidence():
    mature = _assessment("mature", 9.0, gold=1, status=MATURE)
    committed = _assessment("committed", 9.5, gold=1, status=COMMITTED)
    assert choose_post_commit_dominant((committed, mature), ante=8) is mature
